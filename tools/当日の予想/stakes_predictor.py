"""重賞の日に、一般の予想「近走と適性から3着以内を予想」の当日の予測を、重賞のレースの下に並べる表にする。"""

from __future__ import annotations

import duckdb

from 共通.render import Table

from 当日の予想.form_race_day_table import FormRaceDayTable
from 当日の予想.repository import StakesGradeRepository

#: 表の下に添える、この表の扱い。
NOTE = ("一般の予想「近走と適性から3着以内を予想」の当日の予測。重賞の専用モデル（重賞の傾向と近走から3着以内を予想）は、"
        "7つの区切りで一般の予想に勝てなかったので引退し、重賞も一般の予想で予想する（重賞の設計書 15 の 9）。"
        "並べて見せるだけで、上の「買い」には使っていない。")


class StakesPredictor:
    """重賞のレースだけに、一般の予想（近走と適性）の当日の予測の表を出す。重賞でないレースには何も出さない。

    PR #43 で足した重賞の表の置き場所はそのままで、中身を専用モデルから一般の予想に替えた（2026-10-02）。
    ``table`` は1レースの表を作る部品（既定のモデルの置き場所は ``reports/近走と適性から3着以内を予想/models``）。
    モデルが無いときや予測できないときは、落ちずに理由の表を出す。
    """

    def __init__(self, table: FormRaceDayTable) -> None:
        self._table = table

    def tables(self, con: duckdb.DuckDBPyConnection, race: dict) -> list[Table]:
        """出馬表の一覧の1行（``rid``・``場``・``R``・``発走``・``レース名``）が重賞なら、その予測の表を1つ返す。"""
        grade = StakesGradeRepository(con).grade_of(race["rid"])
        if grade is None:
            return []
        title = (f"{race['場']}{race['R']}R {race['発走']} {race['レース名'] or ''}（{grade}）: "
                 "重賞の予想（一般の予想「近走と適性から3着以内を予想」の当日）")
        if not self._table.has_models():
            return [self._reason(title, "一般の予想の学習済みモデルがありません。"
                                        "先に uv run python -m yosou.form_aptitude_top3 train で学習してください。")]
        try:
            table = self._table.table(con, race["rid"])
        except (FileNotFoundError, LookupError, ValueError) as error:
            return [self._reason(title, str(error))]
        table.title = title
        table.note = f"{table.note} {NOTE}"
        return [table]

    def _reason(self, title: str, reason: str) -> Table:
        return Table(["理由"], [[reason]], title=f"{title}（予想できない）")
