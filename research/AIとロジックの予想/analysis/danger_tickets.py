"""研究「AIとロジックの予想」: 消を取り消して印を付け直したときの買い目の成績を、今の消のときと期間ごとに比べる。

    uv run python research/AIとロジックの予想/analysis/danger_tickets.py
    uv run python research/AIとロジックの予想/analysis/danger_tickets.py --kinds 本番の線 1番人気だけ   # 消の線の組どうしを比べる（danger_lines.py --flags の名前）

先に ``danger_cancel.py --flags`` で消の表を書き、道具「印の成績」を、消の表 ``flags_now.pkl``・``flags_cancel.pkl`` のそれぞれで動かしておく
（``--form graded_race_day/odds_move-top3 --win graded_race_day/odds_move-win --timing 当日 --danger-flags <消の表> --out-dir <出す先>``。
出す先は ``reports/AIとロジックの予想/消/now`` と ``.../cancel``。1回 10〜15分。同時には動かさない）。

出すもの: (1) 買い方ごと（1点 100円）の回収率と的中率、(2) 全レースの印の買い目（表だけ。本番と同じ配り方・見込みの回収率 100% 以上だけ買う）の
AI だけ・AI＋ロジック（展開とクラスで見送る）の成績。(2) の見送りは今の ◎ で決めたもの（◎ が替わったレースも同じ扱い）。
``--kinds`` には、道具「印の成績」の出す先のフォルダ名（``reports/AIとロジックの予想/消/<名前>``）を並べる。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import danger_cancel  # noqa: E402
import logic_candidates  # noqa: E402
import logic_rules  # noqa: E402
import race_materials  # noqa: E402
import race_outcomes  # noqa: E402

#: 比べる消（名前, 道具「印の成績」の出す先のフォルダ名）。
KINDS: tuple[tuple[str, str], ...] = (("今", "now"), ("取り消す", "cancel"))
_CSV = "買い目/graded_race_day_odds_move-top3.csv"


def flat(tickets: pd.DataFrame) -> pd.DataFrame:
    """買い方 × 券種ごとの、買ったレース・回収率・的中率（1点 100円 × 単位）。``tickets`` は道具「印の成績」の買い目の表（外していない組）。"""
    rows = tickets.assign(stake=tickets["単位"] * 100, back=tickets["単位"] * tickets["払戻（100円あたり）"])
    races = rows.groupby(["買い方", "券種", "レースID"], as_index=False)[["stake", "back"]].sum()
    total = races.groupby(["買い方", "券種"]).agg(レース=("レースID", "count"), stake=("stake", "sum"), back=("back", "sum"),
                                              hits=("back", lambda back: (back > 0).sum()))
    return total.assign(回収率=total["back"] / total["stake"], 的中率=total["hits"] / total["レース"])[["レース", "回収率", "的中率"]]


def settled(front: pd.DataFrame) -> pd.DataFrame:
    """1レースごとの印の買い目（表だけ）の精算。``front`` は ``compare._front`` の表。索引は race_id。"""
    front = front.astype({"value": float, "odds": float, "pay": float}).fillna({"pay": 0.0})
    rows = [{"race_id": str(race_id), "day": race["day"].iloc[0], **race_outcomes.settle(race, False)}
            for race_id, race in front.groupby("race_id", sort=False)]
    return pd.DataFrame(rows).set_index("race_id")


def line(races: pd.DataFrame) -> str:
    """買ったレースの数・回収率・的中率・1日の儲け。"""
    bought, days = races[races["bought"]], max(races["day"].nunique(), 1)
    if bought.empty:
        return "買う 0"
    return (f"買う {len(bought)} 回収率 {bought['back'].sum() / bought['stake'].sum():.1%} 的中率 {(bought['back'] > 0).mean():.1%} "
            f"1日の儲け {(bought['back'].sum() - bought['stake'].sum()) / days:,.0f}円")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kinds", nargs="+", default=None, metavar="名前",
                        help="比べる消（道具「印の成績」の出す先のフォルダ名。省くと 今の消 と 取り消したあとの消）")
    args = parser.parse_args()
    kinds = tuple((name, name) for name in args.kinds) if args.kinds else KINDS
    materials = pd.read_pickle(race_materials.PATH)
    start, end = danger_cancel.PERIODS[0][1], danger_cancel.PERIODS[-1][2]
    tickets, marks = {}, {}
    for name, folder in kinds:
        path = danger_cancel.OUT / folder / _CSV
        table = pd.read_csv(path, dtype={"レースID": str, "組番": str})
        tickets[name] = table[table["外した理由"].isna() & (table["開催日"] >= start)]
        marks[name] = settled(race_outcomes.compare._front(path, start, end))
    pd.set_option("display.width", 250, "display.max_rows", 500)
    for period, first, last in danger_cancel.PERIODS:
        print(f"== {period}（買い方ごと。1点 100円）")
        parts = {name: flat(table[(table["開催日"] >= first) & (table["開催日"] < last)]) for name, table in tickets.items()}
        print(pd.concat(parts, axis=1).to_string(float_format=lambda value: f"{value:.3f}"))
        table = materials[period]
        skip = pd.Series(~logic_rules.slow_pace(table).to_numpy() | table["class_name"].isin(logic_candidates.OPEN_CLASSES).to_numpy(),
                         index=table.index.astype(str))
        for name, races in marks.items():
            races = races[(races["day"] >= first) & (races["day"] < last)]
            kept = races[~races.index.map(skip).fillna(False).astype(bool)]
            print(f"{period} 印の買い目 消は{name}: AI だけ {line(races)} ｜ AI＋ロジック {line(kept)}")


if __name__ == "__main__":
    main()
