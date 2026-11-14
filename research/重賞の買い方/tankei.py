"""研究「重賞の買い方」4回目の入口: 単系（単勝・馬単・3連単）で全部の重賞を買う形を 2015〜2020年で選び、2021〜2026年で確かめる（docs/05）。

    uv run python research/重賞の買い方/tankei.py extract   # 研究「複勝以外の回収率100超」の全部の組の表から、重賞の馬単・3連単の組を取り出す
    uv run python research/重賞の買い方/tankei.py fit       # 組の確率を作る（重賞だけで合わせ直す・本番の重み・直前1年の重み）
    uv run python research/重賞の買い方/tankei.py search    # 2015〜2020年だけで、券種と確率ごとに形を選ぶ（4回目/選んだ形.md）
    uv run python research/重賞の買い方/tankei.py check     # 選んだ形を 2021〜2026年で一度だけ数える（4回目/確かめ.md）

``fit`` の3連単は重賞だけでも組が数百万あり、20〜30分かかる。出るものは Git 対象外の ``reports/重賞の買い方/4回目/``。
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from 共通 import render  # noqa: E402
from 共通.render import Table  # noqa: E402

from 全レース全券種の買い方.materials import MARKED  # noqa: E402
from 重賞の買い方.analysis.race_logit import RaceLogit  # noqa: E402
from 重賞の買い方.stakes_bets import GRADED, OUT as STAKES_OUT  # noqa: E402

OUT = STAKES_OUT / "4回目"
VALUE_DIR = Path(__file__).resolve().parents[2] / "reports" / "複勝以外の回収率100超" / "組の期待値"
FILES = {"馬単": "exacta", "3連単": "trifecta"}
SELECT_YEARS, CONFIRM_YEARS = range(2015, 2021), range(2021, 2027)
#: 確率の作り方: 重賞だけで合わせ直す（選ぶ期間は年を1つずつ抜いて学ぶ）・本番の重み（combo_blend.json）・直前1年の重み（rolling_weights）。
SOURCES = ("重賞で合わせ直し", "本番の重み", "直前1年の重み")
#: 形の候補（docs/05 の 3）。どの形も、全部の重賞で最低1点は買う。
POINTS = (1, 2, 3, 5, 10, 20)
LINES = (0.0, 1.0, 1.2, 1.5)
CAPS = {"単勝": (None, 10, 20, 100), "馬単": (None, 20, 50, 100, 300), "3連単": (None, 100, 300, 1000, 3000)}
FLOORS = {"単勝": (0.0, 0.05, 0.1), "馬単": (0.0, 0.01, 0.03), "3連単": (0.0, 0.002, 0.005, 0.01)}
MIN_HITS = 30
_FLOOR = 1e-9
_WEIGHT_KEYS = ("own", "trifecta", "harville", "ratio")


def main() -> None:
    args = _parser().parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    {"extract": _extract, "fit": _fit, "search": _search, "check": _check}[args.command]()


def _graded_ids() -> list[int]:
    return pd.read_parquet(GRADED)["race_id"].astype("int64").tolist()


def _extract() -> None:
    ids = _graded_ids()
    for ticket, key in FILES.items():
        parts = [pq.read_table(VALUE_DIR / "combos" / f"{key}_{year}.parquet", filters=[("rid", "in", ids)]).to_pandas() for year in range(2015, 2027)]
        pd.concat(parts).to_parquet(OUT / f"組_{ticket}.parquet")
        print(f"{ticket}: {sum(len(part) for part in parts):,} 組", file=sys.stderr, flush=True)


def _features(ticket: str) -> pd.DataFrame:
    """1行 = 1組（単勝は1頭）。列 race_id・race_date・y・fold・odds・payout・hit と、もとの対数 f1〜。"""
    if ticket == "単勝":
        horses = pd.read_parquet(MARKED, columns=["race_id", "race_date", "fold", "horse_no", "win_odds", "win_payout", "market_win", "win_probability", "probability"])
        horses = horses[horses["race_id"].astype("int64").isin(set(_graded_ids())) & (horses["win_odds"] > 0)]
        table = pd.DataFrame({"race_id": horses["race_id"].astype(str), "race_date": pd.to_datetime(horses["race_date"]), "fold": horses["fold"],
                              "odds": horses["win_odds"].astype(float), "payout": horses["win_payout"].astype(float),
                              "f1": np.log(horses["market_win"].clip(lower=_FLOOR)), "f2": np.log(horses["win_probability"].clip(lower=_FLOOR)),
                              "f3": np.log(horses["probability"].clip(lower=_FLOOR))})
    else:
        raw = pd.read_parquet(OUT / f"組_{ticket}.parquet")
        count = 2 if ticket == "馬単" else 3
        ratio = np.log(raw["rw1"].astype(float)) + sum(np.log(raw[f"rt{at}"].astype(float)) for at in range(2, count + 1))
        table = pd.DataFrame({"race_id": raw["rid"].astype(str), "race_date": pd.to_datetime(raw["race_date"]), "fold": raw["fold"],
                              "odds": raw["odds"].astype(float), "payout": raw["payout"].astype(float),
                              "f1": np.log(raw["q"].astype(float).clip(lower=_FLOOR)), "f2": np.log(raw["t"].astype(float).clip(lower=_FLOOR)),
                              "f3": np.log(raw["hv"].astype(float).clip(lower=_FLOOR)), "f4": ratio})
    table = table.replace([np.inf, -np.inf], np.nan).dropna()
    table = table[table["odds"] > 0].sort_values("race_id", kind="stable").reset_index(drop=True)
    return table.assign(y=table["race_date"].dt.year, hit=(table["payout"] > 0).astype(float))


def _fit() -> None:
    blend = json.loads((VALUE_DIR / "combo_blend.json").read_text(encoding="utf-8"))
    rolling = json.loads((VALUE_DIR / "rolling_weights-2015から.json").read_text(encoding="utf-8"))
    logit = RaceLogit()
    for ticket in ("単勝", "馬単", "3連単"):
        table = _features(ticket)
        names = [column for column in ("f1", "f2", "f3", "f4") if column in table.columns]
        sources = {"重賞で合わせ直し": logit.cross_fitted(table, names, SELECT_YEARS, CONFIRM_YEARS)}
        if ticket != "単勝":
            fixed = np.array([blend[ticket][key] for key in _WEIGHT_KEYS])
            sources["本番の重み"] = logit.probability(table, table[names].to_numpy() @ fixed)
            by_fold = np.array([[rolling[fold][ticket][key] for key in _WEIGHT_KEYS] if fold in rolling else [np.nan] * 4 for fold in table["fold"]])
            sources["直前1年の重み"] = logit.probability(table, (table[names].to_numpy() * by_fold).sum(axis=1))
        for source, probability in sources.items():
            out = table[["race_id", "race_date", "y", "odds", "payout"]].assign(p=probability, ev=probability * table["odds"]).dropna(subset=["p"])
            out.to_parquet(OUT / f"確率_{ticket}_{source}.parquet")
            print(f"{ticket}・{source}: {len(out):,} 組", file=sys.stderr, flush=True)


def _picked(table: pd.DataFrame, points: int, line: float, cap: float | None, floor: float) -> pd.DataFrame:
    """オッズの上限と確率の下限に合う組を期待値の高い順に並べ、上から ``points`` 点のうち期待値が線以上の組（線に届かなくても1点は買う）。"""
    chosen = table[(table["p"] >= floor) & ((table["odds"] <= cap) if cap else True)].sort_values(["race_id", "ev"], ascending=[True, False])
    rank = chosen.groupby("race_id").cumcount() + 1
    return chosen[(rank <= points) & ((chosen["ev"] >= line) | (rank == 1))]


def _score(bought: pd.DataFrame, seed: int = 0) -> dict[str, float]:
    days = bought.groupby("race_date").agg(stake=("payout", "size"), back=("payout", "sum"))
    stake, back = days["stake"].to_numpy(), days["back"].to_numpy() / 100
    index = np.random.default_rng(seed).integers(0, len(stake), (2000, len(stake)))
    return {"点": len(bought), "レース": bought["race_id"].nunique(), "当たり": int((bought["payout"] > 0).sum()),
            "回収率": bought["payout"].sum() / len(bought) / 100, "下の端": float(np.quantile(back[index].sum(1) / stake[index].sum(1), 0.05))}


def _search() -> None:
    """選ぶ期間だけで、券種 × 確率の作り方ごとに、全部の重賞の 9割以上を買い当たりが 30 以上の形のうち、下の端がいちばん高い形を選ぶ。"""
    chosen, tables = [], []
    for ticket, source in itertools.product(("単勝", "馬単", "3連単"), SOURCES):
        path = OUT / f"確率_{ticket}_{source}.parquet"
        if not path.exists():
            continue
        table = pd.read_parquet(path)
        table = table[table["y"].isin(SELECT_YEARS)]
        races = table["race_id"].nunique()
        rows = []
        for points, line, cap, floor in itertools.product(POINTS, LINES, CAPS[ticket], FLOORS[ticket]):
            bought = _picked(table, points, line, cap, floor)
            if bought["race_id"].nunique() >= 0.9 * races and (bought["payout"] > 0).sum() >= MIN_HITS:
                rows.append(({"券種": ticket, "確率": source, "点数": points, "線": line, "上限": cap, "確率の下限": floor}, _score(bought)))
        if not rows:
            continue
        rows.sort(key=lambda row: -row[1]["下の端"])
        chosen.append(rows[0][0])
        tables.append(Table(["点数", "線", "上限", "確率の下限", "点", "当たり", "回収率", "下の端"],
                            [[shape["点数"], shape["線"], shape["上限"] or "なし", shape["確率の下限"], f"{score['点']:,}", score["当たり"],
                              _pct(score["回収率"]), _pct(score["下の端"])] for shape, score in rows[:5]],
                            title=f"{ticket}・{source}: 下の端の高い順に5つ（重賞の {SELECT_YEARS.start}〜{SELECT_YEARS.stop - 1}年）"))
    (OUT / "選んだ形.json").write_text(json.dumps(chosen, ensure_ascii=False, indent=1), encoding="utf-8")
    render.write(render.render(tables, "markdown"), OUT / "選んだ形.md", fmt="markdown")
    print(f"保存先: {OUT / '選んだ形.md'}", file=sys.stderr)


def _check() -> None:
    """選んだ形を、選ぶ期間と確かめる期間で数える（確かめる期間は一度だけ）。採用の線は docs/05 の 4。"""
    rows, yearly_rows = [], []
    for shape in json.loads((OUT / "選んだ形.json").read_text(encoding="utf-8")):
        table = pd.read_parquet(OUT / f"確率_{shape['券種']}_{shape['確率']}.parquet")
        bought = _picked(table, shape["点数"], shape["線"], shape["上限"], shape["確率の下限"])
        before, after = _score(bought[bought["y"].isin(SELECT_YEARS)]), _score(bought[bought["y"].isin(CONFIRM_YEARS)])
        late = bought[bought["y"].isin(CONFIRM_YEARS)]
        years = late.groupby("y")["payout"].agg(lambda s: s.sum() / len(s) / 100)
        name = f"{shape['券種']}・{shape['確率']}・{shape['点数']}点・線 {shape['線']}・上限 {shape['上限'] or 'なし'}・確率 {shape['確率の下限']} 以上"
        rows.append([name, _pct(before["回収率"]), _pct(after["回収率"]), _pct(after["下の端"]), f"{after['当たり']}", f"{after['レース']:,}",
                     f"{int((years > 1.0).sum())}/{len(years)}"])
        yearly_rows.append([name, *[_pct(years.get(year, np.nan)) for year in CONFIRM_YEARS]])
    tables = [Table(["形", "回収率（選ぶ期間）", "回収率（確かめる期間）", "下の端", "当たり", "レース", "100% 超えの年"], rows,
                    title="結果（1点 100円・確定オッズ）", note="採用の線（docs/05 の 4）: 確かめる期間で、全部の重賞を買って回収率 100% 超え。"),
              Table(["形", *map(str, CONFIRM_YEARS)], yearly_rows, title="確かめる期間の年ごとの回収率")]
    render.write(render.render(tables, "markdown"), OUT / "確かめ.md", fmt="markdown")
    print(f"保存先: {OUT / '確かめ.md'}", file=sys.stderr)


def _pct(value: float) -> str:
    return "―" if value is None or not np.isfinite(value) else f"{value:.1%}"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, text in (("extract", "重賞の馬単・3連単の組を取り出す"), ("fit", "組の確率を作る"), ("search", "選ぶ期間で形を選ぶ"),
                       ("check", "確かめる期間で一度だけ数える")):
        subparsers.add_parser(name, help=text)
    return parser


if __name__ == "__main__":
    main()
