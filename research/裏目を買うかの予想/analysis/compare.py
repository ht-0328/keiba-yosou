"""研究「裏目を買うかの予想」: 全レースの印の買い目（表）に、裏の当たる確率が線以上のレースだけ裏を足したときと、今のまま（表だけ）を比べる。

    uv run python research/裏目を買うかの予想/analysis/compare.py --learn-until 2025-09-06 --start 2025-09-06 --end 2026-11-15 --split 2026-03-08
    uv run python research/裏目を買うかの予想/analysis/compare.py --learn-until 2024-09-07 --start 2024-09-07 --end 2025-09-06

裏の当たる確率は、``--learn-until`` より前のレースだけで学んだモデル（本番と同じ ``ReverseExactaModel``）で出す。
表は道具「印の成績」の買い目の CSV（オッズの動きで直した当日の予想。``--tickets``）の 単勝・馬連・馬単・3連単、
裏は ``candidates.py`` が書いた組（``candidates_<start>_<end>.pkl``）のうち、表の相手と同じ馬で ◎ の位置だけ違う組
（馬単 ○▲☆→◎、3連単 ○▲☆→◎→○▲△☆ と ○▲☆→○▲△☆→◎）。
買い方は本番と同じ（どれが当たっても同じ額が戻るように配る・当たったときに購入額の 1.1倍に届かなければ期待値の低い組から外す・1レース 5,000円・
見込みの回収率 100% 以上のレースだけ買う）。``--split`` を渡すと、その日の前（線を決める期間）と後（確かめる期間）に分けて出す。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[2]
sys.path[:0] = [str(_ROOT / "tools"), str(_HERE.parent)]

import fit  # noqa: E402
import 今週の予想.mark_return as mark_return  # noqa: E402
from 今週の予想.equal_payout_stakes import EqualPayoutStakes  # noqa: E402
from 今週の予想.mark_return import BUY_LINE  # noqa: E402
from 今週の予想.reverse_exacta_features import ReverseExactaFeatures  # noqa: E402
from 今週の予想.reverse_exacta_model import ReverseExactaModel  # noqa: E402

OUT = _ROOT / "reports" / "裏目を買うかの予想"
#: 道具「印の成績」の買い目の CSV（オッズの動きで直した当日の予想）。
TICKETS = _ROOT / "reports" / "印の成績" / "全レースとオッズの動き" / "odds_move_value" / "買い目" / "graded_race_day_odds_move-top3.csv"
#: 表の買い方。
_FRONT_RULES = ("単勝", "馬連", "馬単", "3連単（◎→○▲☆→○▲△☆）")
#: 裏の種類。
EXACTA_BACK, TRIFECTA_SECOND, TRIFECTA_THIRD = "馬単の裏", "3連単 ◎2着", "3連単 ◎3着"
#: 比べる形（名前, 足す裏の種類）。
_SHAPES = (("馬単の裏", (EXACTA_BACK,)), ("3連単の裏", (TRIFECTA_SECOND, TRIFECTA_THIRD)), ("裏全部", (EXACTA_BACK, TRIFECTA_SECOND, TRIFECTA_THIRD)))
#: 学ぶときのスレッドの数。
THREADS = 6


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--learn-until", required=True, help="この開催日の前までで、裏の当たる確率のモデルを学ぶ")
    parser.add_argument("--start", required=True, help="比べる期間の初め（この開催日から）")
    parser.add_argument("--end", required=True, help="比べる期間の終わり（この開催日の前まで）")
    parser.add_argument("--split", help="この開催日の前と後に分けて出す")
    parser.add_argument("--lines", type=float, nargs="+", default=[0.25, 0.30, 0.35], help="裏を足す、裏の当たる確率の線")
    parser.add_argument("--tickets", type=Path, default=TICKETS, help="道具「印の成績」の買い目の CSV")
    args = parser.parse_args()
    pool = _pool(_front(args.tickets, args.start, args.end), pd.read_pickle(OUT / f"candidates_{args.start}_{args.end}.pkl"))
    pool["p"] = pool["race_id"].map(_probabilities(args.learn_until, args.start, args.end))
    parts = {"全体": pool} if not args.split else {"前": pool[pool["day"] < args.split], "後": pool[pool["day"] >= args.split]}
    print(f"{args.start}〜{args.end} の前日まで（モデルは {args.learn_until} の前日までで学んだ）")
    shapes = [("今のまま（表だけ）", None, ())] + [(f"裏の確率 {line:.2f} 以上 → {name}", line, kinds)
                                                  for line in args.lines for name, kinds in _SHAPES]
    for name, line, kinds in shapes:
        print(f"{name:<28}" + " | ".join(f"{part} {_summary(table, line, kinds)}" for part, table in parts.items()), flush=True)


def _front(path: Path, start: str, end: str) -> pd.DataFrame:
    """表の買い目（外していない組）と、確定オッズ・100円あたりの払戻。"""
    rules = ", ".join(f"'{rule}'" for rule in _FRONT_RULES)
    front = duckdb.connect().execute(f"""
        SELECT レースID AS race_id, 開催日 AS day, 買い方 AS rule, 組番 AS combo, TRY_CAST(期待値 AS DOUBLE) AS value,
               TRY_CAST(確定オッズ AS DOUBLE) AS odds, TRY_CAST("払戻（100円あたり）" AS DOUBLE) AS pay
        FROM read_csv_auto('{path.as_posix()}', header = true, all_varchar = true)
        WHERE coalesce(外した理由, '') = '' AND 開催日 >= '{start}' AND 開催日 < '{end}' AND 買い方 IN ({rules})""").df()
    return front.assign(kind="表")


def _numbers(combo: str) -> list[int]:
    return [int(combo[at:at + 2]) for at in range(0, len(combo), 2)]


def _pool(front: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    """表と裏の買い目を1つの表にする（列 race_id・day・kind・value・odds・pay）。裏は、表の相手と同じ馬で ◎ の位置だけ違う組。"""
    top, second, third = {}, {}, {}
    for race, rule, combo in zip(front["race_id"], front["rule"], front["combo"]):
        horses = _numbers(combo)
        if rule == "単勝":
            top[race] = horses[0]
        elif rule == "馬単":
            second.setdefault(race, set()).add(horses[1])
        elif rule.startswith("3連単"):
            second.setdefault(race, set()).add(horses[1])
            third.setdefault(race, set()).add(horses[2])
    combos = candidates.assign(race_id=candidates["race_id"].astype(str), top=candidates["race_id"].astype(str).map(top))

    def among(races: pd.Series, horses: pd.Series, chosen: dict[str, set[int]]) -> np.ndarray:
        return np.array([horse in chosen.get(race, ()) for race, horse in zip(races, horses)], dtype=bool)

    exacta = combos[combos["ticket_type"] == "馬単"]
    trifecta = combos[combos["ticket_type"] == "3連単"]
    first_ok = among(trifecta["race_id"], trifecta["h1"], second)
    backs = pd.concat([
        exacta[(exacta["h2"] == exacta["top"]).to_numpy() & among(exacta["race_id"], exacta["h1"], second)].assign(kind=EXACTA_BACK),
        trifecta[(trifecta["h2"] == trifecta["top"]).to_numpy() & first_ok & among(trifecta["race_id"], trifecta["h3"], third)]
        .assign(kind=TRIFECTA_SECOND),
        trifecta[(trifecta["h3"] == trifecta["top"]).to_numpy() & first_ok & among(trifecta["race_id"], trifecta["h2"], third)]
        .assign(kind=TRIFECTA_THIRD),
    ])
    days = dict(zip(front["race_id"], front["day"]))
    backs = backs.rename(columns={"payout": "pay"}).assign(pay=lambda table: table["pay"].fillna(0.0), day=lambda table: table["race_id"].map(days))
    columns = ["race_id", "day", "kind", "value", "odds", "pay"]
    return pd.concat([front[columns], backs[columns]], ignore_index=True).astype({"value": float, "odds": float, "pay": float})


def _probabilities(learn_until: str, start: str, end: str) -> pd.Series:
    """レース → 裏の当たる確率（``learn_until`` の前までで学んだモデル）。"""
    rows = fit.race_rows(pd.read_pickle(fit.MARKED))
    features = ReverseExactaFeatures().frame(rows["features"].tolist())
    learn = (rows["day"] < learn_until).to_numpy()
    model = ReverseExactaModel.fit(features[learn], rows["y"][learn], THREADS)
    period = ((rows["day"] >= start) & (rows["day"] < end)).to_numpy()
    return pd.Series(model.predict(features[period]), index=rows["race_id"][period].to_numpy())


def _summary(pool: pd.DataFrame, line: float | None, kinds: tuple[str, ...]) -> str:
    """本番と同じ配り方で、買ったレースの割合・回収率・的中率・1日の儲け。"""
    stakes = EqualPayoutStakes()
    bought = []
    for _, race in pool.groupby("race_id", sort=False):
        add = line is not None and race["p"].iloc[0] >= line
        tickets = race[(race["kind"] == "表") | (race["kind"].isin(kinds) if add else False)].to_dict("records")
        chosen, _ = stakes.allocate(tickets)
        if not chosen or sum(share * ticket["value"] for ticket, share in chosen if ticket["value"] == ticket["value"]) < BUY_LINE:
            continue
        yen = mark_return._amounts(chosen)
        bought.append((sum(yen), sum(amount * ticket["pay"] / 100 for amount, (ticket, _) in zip(yen, chosen, strict=True))))
    paid = sum(spent for spent, _ in bought)
    back = sum(returned for _, returned in bought)
    races, days = pool["race_id"].nunique(), pool["day"].nunique()
    return (f"買う {len(bought) / races:6.1%} 回収率 {back / paid:7.1%} 的中 {sum(returned > 0 for _, returned in bought) / len(bought):6.1%} "
            f"1日 {(back - paid) / days:>8,.0f}円")


if __name__ == "__main__":
    main()
