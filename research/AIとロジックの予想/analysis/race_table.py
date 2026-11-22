"""研究「AIとロジックの予想」: 1レースごとの、レースの前に分かる材料の表を作る（ロジックの決まりが読む）。

    uv run python research/AIとロジックの予想/analysis/race_table.py --start 2022-09-03 --end 2026-09-23

AI の材料（当日の予想の印の表 ``marked.pkl`` の ◎・消 の行）と、ロジックの材料（``logic_features.py`` の
その日の馬場の偏り・推定脚質・逃げ先行の数）を1行にまとめる。結果（着順・払戻）は入れない。
出るもの（Git 対象外）: ``reports/AIとロジックの予想/races_<start>_<end>.pkl``。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import race_outcomes as outcomes  # noqa: E402

#: ◎ の行から写す材料。
_TOP_COLUMNS = ("popularity", "win_odds", "probability", "market_top3", "win_probability", "market_win", "win_value", "place_value",
                "updown", "odds_move", "pool_support", "pool_win", "horse_id", "horse_no")


def build(marked: pd.DataFrame, logic: pd.DataFrame) -> pd.DataFrame:
    marked = marked.assign(race_id=marked["race_id"].astype(str), horse_id=marked["horse_id"].astype(str))
    logic = logic.assign(race_id=logic["race_id"].astype(str), horse_id=logic["horse_id"].astype(str))
    top = marked[marked["mark"] == "◎"].drop_duplicates("race_id").set_index("race_id")[list(_TOP_COLUMNS)].add_prefix("top_")
    out = marked[marked["mark"] == "消"].drop_duplicates("race_id").set_index("race_id")[["popularity", "win_odds"]].add_prefix("out_")
    races = marked.groupby("race_id").agg(day=("race_date", "first"), field_size=("field_size", "first"))
    races["day"] = pd.to_datetime(races["day"]).dt.strftime("%Y-%m-%d")
    first = marked[marked["popularity"] == 1].drop_duplicates("race_id").set_index("race_id")["win_odds"].rename("favorite_odds")
    table = races.join([top, out, first])
    styles = logic.set_index(["race_id", "horse_id"])["style_before"]
    table["top_style"] = [styles.get((race, horse)) for race, horse in zip(table.index, table["top_horse_id"])]
    table = table.join(logic.drop_duplicates("race_id").set_index("race_id")[["bias_z", "bias_races", "front_runners"]])
    table["top_win_ratio"] = table["top_win_probability"] / table["top_market_win"]
    table["top_top3_ratio"] = table["top_probability"] / table["top_market_top3"]
    return table.reset_index()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--logic", required=True, help="logic_features.py の出力（logic_horses_<start>_<end>.pkl）")
    parser.add_argument("--periods", nargs="+", required=True, help="書き出す期間（<start>_<end> の並び）")
    args = parser.parse_args()
    marked = pd.read_pickle(outcomes.fit.MARKED)
    table = build(marked[(marked["race_date"] >= args.start) & (marked["race_date"] < args.end)], pd.read_pickle(args.logic))
    for period in args.periods:
        start, end = period.split("_")
        part = table[(table["day"] >= start) & (table["day"] < end)]
        path = outcomes.OUT / f"races_{start}_{end}.pkl"
        part.to_pickle(path)
        print(f"{period}: {len(part):,} レース → {path}")


if __name__ == "__main__":
    main()
