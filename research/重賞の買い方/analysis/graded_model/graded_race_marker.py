"""重賞の予測（7つの区切りのテストの年）に、今週の予想と同じ決め方で印と期待度を付ける。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts

from yosou.shared.race_grade import TopRankScale

from 今週の予想.forecast_columns import MARK, WIN_PROBABILITY, WIN_VALUE
from 今週の予想.mark_rule import TOP_MARK
from 印の成績.backtest_marker import BacktestMarker
from 印の成績.favorite_danger_judge import COLUMNS as DANGER_COLUMNS
from 印の成績.prediction_file import TEST
from 印の成績.race_results import RaceResults
from 印の成績.win_value_attacher import WinValueAttacher

#: 平地の重賞のグレードコード。
_GRADED = ("A", "B", "C")
#: 足す列。期待度（S・A・B・C・見送り）・枠番・格（G1〜G3）。
GRADE, FRAME_NO, RACE_GRADE = "expectation", "frame_no", "race_grade"
_GRADE_NAMES = {"A": "G1", "B": "G2", "C": "G3"}


class GradedRaceMarker:
    """3着以内の予測（``top3``）と1着の予測（``win``）のテストの行のうち、平地の重賞のレースだけに印を付ける。

    印は ``BacktestMarker``（道具「印の成績」と同じ決め方）。危険な人気馬（消）は使わない（人気馬の予想の区切りは半年ずつで、
    1年ずつの区切りの 2020〜2022年の予測が無いため。研究「既存モデルの改善」の重賞の作り直しの確かめと同じ扱い）。
    期待度は ◎ の1着の確率と単勝の期待値から ``TopRankScale``（今週の予想と同じ線）で付ける。
    """

    def __init__(self, marker: BacktestMarker) -> None:
        self._marker = marker

    def mark(self, con: duckdb.DuckDBPyConnection, top3: pd.DataFrame, win: pd.DataFrame) -> pd.DataFrame:
        graded = self._graded_races(con)
        tested = top3[(top3["period"] == TEST) & top3["race_id"].isin(graded["race_id"])]
        wins = win[win["race_id"].isin(set(tested["race_id"]))]
        places = self._marker.places(RaceResults().read(con, tested["race_id"]))
        dangers = pd.DataFrame(columns=list(DANGER_COLUMNS))
        marked = self._marker.mark(tested, places, dangers, WinValueAttacher().attach(wins, places))
        marked = marked.merge(self._frames(con, tested["race_id"]), on=["race_id", "horse_no"], how="left")
        marked = marked.merge(graded, on="race_id", how="left")
        return marked.merge(self._grades(marked), on="race_id", how="left")

    def _graded_races(self, con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
        table = facts.ensure_facts(con)
        frame = con.execute(f"""
            SELECT DISTINCT race_id, grade_code FROM {table}
            WHERE grade_code IN {tuple(_GRADED)} AND surface <> '障害'
        """).df()
        return pd.DataFrame({"race_id": frame["race_id"].astype(str), RACE_GRADE: frame["grade_code"].map(_GRADE_NAMES)})

    def _frames(self, con: duckdb.DuckDBPyConnection, race_ids: pd.Series) -> pd.DataFrame:
        table = facts.ensure_facts(con)
        con.register("graded_marker_ids", pd.DataFrame({"race_id": race_ids.astype(str).drop_duplicates()}))
        frame = con.execute(f"""
            SELECT f.race_id, f.horse_no, f.frame_no FROM {table} AS f JOIN graded_marker_ids USING (race_id) WHERE f.ran
        """).df()
        return frame.astype({"race_id": str, "horse_no": int})

    def _grades(self, marked: pd.DataFrame) -> pd.DataFrame:
        """レースごとの期待度（◎ の1着の確率と単勝の期待値から）。"""
        scale = TopRankScale()
        tops = marked[marked[MARK] == TOP_MARK].drop_duplicates("race_id")
        grades = [scale.grade(float(row[WIN_PROBABILITY]), float(row[WIN_VALUE])) for _, row in tops.iterrows()]
        return pd.DataFrame({"race_id": tops["race_id"].to_numpy(), GRADE: grades})
