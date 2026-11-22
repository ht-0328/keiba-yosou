"""研究「AIとロジックの予想」: 期間ごとのレースの表に、レースと ◎ の馬の材料（クラス・距離・馬場・前走・乗り替わりなど）を足す。

    uv run python research/AIとロジックの予想/analysis/race_materials.py

``logic_rules.parts()`` の4つの期間の表（1行 = 1レース。今の本番の買い目の結果つき）と、追加の確かめの期間（2021年1月5日〜2022年9月2日。
``race_table.py`` の ``races_<start>_<end>.pkl`` と ``race_outcomes.py`` の ``outcomes_<start>_<end>.pkl`` から作る）の表に、事実表からレースの材料と、◎ の馬の材料（列名の頭に ``h_``）を足す。
どれもレースの前に分かること（オッズは確定のもの。検証はどの研究も確定オッズ）。
出るもの（Git 対象外）: ``reports/AIとロジックの予想/materials.pkl``（期間の名前 → 表）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(_HERE.parents[2] / "tools"), str(_HERE)]

import logic_rules  # noqa: E402
from 共通 import db, facts  # noqa: E402

PATH = logic_rules.outcomes.OUT / "materials.pkl"
#: 追加の確かめの期間（名前・初日・最終日の次の日）。ロジックを探すときに一度も見ていない期間。オッズの動きで直す前の予想。
EXTRA: tuple[str, str, str] = ("追加の確かめ", "2021-01-05", "2022-09-03")
_RACE = ("venue", "surface", "distance_m", "condition", "grade_code", "class_name", "race_no", "month", "weight_type", "mixed_sex")
_HORSE = ("frame_no", "sex", "age", "weight_change", "prev_finish", "prev_popularity", "interval_days", "runs_before", "wins_before",
          "course_runs_before", "best_time_dist_rank", "prev_last3f_rank", "surface_change", "distance_change", "class_change",
          "jockey_change", "venue_change", "apprentice", "blinker", "tm_rank", "dm_rank", "trainer_area")


def read() -> pd.DataFrame:
    """事実表の 1行 = 1頭（race_id・horse_id は文字列）。"""
    with db.open_db() as con:
        table = facts.ensure_facts(con)
        runs = con.execute(f"""
            SELECT race_id, horse_id, win_odds, lead_candidates, {", ".join(_RACE + _HORSE)}
            FROM {table} WHERE race_date >= '{EXTRA[1]}' AND race_date < '2026-09-23'
        """).df()
    return runs.assign(race_id=runs["race_id"].astype(str), horse_id=runs["horse_id"].astype(str))


def _second_odds(odds: pd.Series) -> float:
    """2番目に低い単勝オッズ（2番人気の単勝）。"""
    return odds.nsmallest(2).iloc[-1] if odds.notna().sum() >= 2 else float("nan")


def attach(table: pd.DataFrame, runs: pd.DataFrame) -> pd.DataFrame:
    """1つの期間の表（索引は race_id）に、レースの材料と ◎ の馬の材料を足す。"""
    race = runs.drop_duplicates("race_id").set_index("race_id")[list(_RACE)]
    grouped = runs.groupby("race_id")
    race = race.assign(n_first=grouped["runs_before"].apply(lambda runs_before: (runs_before.fillna(0) == 0).sum()),
                       n_lead=grouped["lead_candidates"].first(), odds2=grouped["win_odds"].apply(_second_odds))
    table = table.set_axis(table.index.astype(str)).join(race)
    keys = pd.MultiIndex.from_arrays([table.index, table["top_horse_id"].astype(str)])
    horse = runs.set_index(["race_id", "horse_id"])[list(_HORSE)].reindex(keys).add_prefix("h_")
    return table.join(horse.set_axis(table.index))


def extra_part() -> pd.DataFrame:
    """追加の確かめの期間の表（索引は race_id。今の本番の買い目の結果つき）。"""
    _, start, end = EXTRA
    out = logic_rules.outcomes.OUT
    races = pd.read_pickle(out / f"races_{start}_{end}.pkl").set_index("race_id")
    settled = pd.read_pickle(out / f"outcomes_{start}_{end}.pkl").set_index("race_id")[["p", "bought", "stake", "back", "points", "expected"]]
    return races.set_axis(races.index.astype(str)).join(settled.set_axis(settled.index.astype(str)), how="inner")


def main() -> None:
    runs = read()
    out = {name: attach(table, runs) for name, table in {**logic_rules.parts(), EXTRA[0]: extra_part()}.items()}
    pd.to_pickle(out, PATH)
    print("・".join(f"{name} {len(table):,} レース" for name, table in out.items()), "→", PATH)


if __name__ == "__main__":
    main()
