"""重賞の日に、予想モデル「重賞の傾向と近走から3着以内を予想」の当日の予測を表にする。"""

from __future__ import annotations

from pathlib import Path

import duckdb

from 共通.render import Table

from yosou.shared.feature import PredictionTiming
from yosou.stakes_tendency_top3.command import PredictCommand

from 当日の予想.repository import StakesGradeRepository

#: 当日の予想は発走の前に出すので、重賞の予想も「当日」の時点のモデルを使う（設計書 07）。
TIMING = PredictionTiming.RACE_DAY
#: 表の下に添える、この表の扱い。
NOTE = ("予想モデル「重賞の傾向と近走から3着以内を予想」の当日の予測。並べて見せるだけで、上の「買い」には使っていない"
        "（買う線はこの予想では決めていない。設計書 16 の「今はしないこと」）。")


class StakesPredictor:
    """重賞のレースだけを、予想モデル「重賞の傾向と近走から3着以内を予想」で予測する。重賞でないレースには何も出さない。

    ``models`` は学習済みのモデルの置き場所（既定は ``reports/重賞の傾向と近走から3着以内を予想/models``）。
    モデルが無いときや予測できないときは、落ちずに理由の表を出す。
    """

    def __init__(self, models: Path, command: PredictCommand | None = None) -> None:
        self._models = Path(models)
        self._command = command or PredictCommand()

    def tables(self, con: duckdb.DuckDBPyConnection, race: dict) -> list[Table]:
        """出馬表の一覧の1行（``rid``・``場``・``R``・``発走``・``レース名``）が重賞なら、その予測の表を1つ返す。"""
        grade = StakesGradeRepository(con).grade_of(race["rid"])
        if grade is None:
            return []
        title = f"{race['場']}{race['R']}R {race['発走']} {race['レース名'] or ''}（{grade}）: 重賞の予想"
        if not (self._models / TIMING.value).is_dir():
            return [self._reason(title, f"学習済みのモデルがありません（{self._models}）。"
                                        "先に uv run python -m yosou.stakes_tendency_top3 train で学習してください。")]
        try:
            table = self._command.predict_table(con, race["rid"], TIMING, self._models)
        except (FileNotFoundError, LookupError, ValueError) as error:
            return [self._reason(title, str(error))]
        table.title = title
        table.note = f"{table.note} {NOTE}"
        return [table]

    def _reason(self, title: str, reason: str) -> Table:
        return Table(["理由"], [[reason]], title=f"{title}（予想できない）")
