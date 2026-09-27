"""出走の表から、1行 = 1レースの表を作る。"""

from __future__ import annotations

import pandas as pd

#: 1レースに1つの値の列（意味は ``tools/共通/facts.py`` の ``FACT_COLUMNS``）。
RACE_COLUMNS: tuple[str, ...] = (
    "race_id", "race_date", "year", "venue_code", "venue", "race_no", "race_name", "track_code", "surface", "course",
    "distance_m", "condition", "class_name", "class_order", "grade_code", "field_size", "lead_candidates",
    "first3f", "last3f_race",
)
#: 勝ち馬の脚質（結果）と推定脚質の列。
WINNER_STYLE, WINNER_STYLE_BEFORE = "勝ち馬の脚質", "勝ち馬の推定脚質"


class RaceTable:
    """出走の表（``PaceRunnerRepository`` が読んだもの）を、1行 = 1レースにまとめる。

    勝ち馬の脚質（結果）と推定脚質を足す。同着で勝ち馬が2頭いるときは、馬番の小さい方を取る。
    """

    def build(self, runners: pd.DataFrame) -> pd.DataFrame:
        races = runners.drop_duplicates("race_id")[list(RACE_COLUMNS)].reset_index(drop=True)
        winners = runners[runners["finish"] == 1].sort_values(["race_id", "horse_no"]).drop_duplicates("race_id")
        styles = winners.set_index("race_id")[["style", "style_before"]].rename(
            columns={"style": WINNER_STYLE, "style_before": WINNER_STYLE_BEFORE})
        return races.join(styles, on="race_id")
