"""対象レース1つで、今のモデルのどの時点の1着の確率を使うかを選ぶ。"""

from __future__ import annotations

import duckdb

from 共通.race_signals import RaceSignalReader, RaceSignals

from yosou.shared.feature import PredictionTiming
from yosou.shared.workflow import TimingChooser

from .leg_model import LegModel
from .leg_model_choice import LegModelChoice

#: 障害のトラックの名前の頭（``codes.TRACK_NAMES`` の「障害・芝」など）。
_JUMP_PREFIX = "障害"
_JUMP_REASON = "障害のレース（今のモデルは障害を予想しない）なので、オッズから見た勝率をそのまま使う"


class LegModelChooser:
    """設計書 06 の図1。障害のレースなら「オッズだけ」。平地なら、道具「今週の予想」と同じ ``TimingChooser`` で時点を選び、
    当日なら今のモデルの当日、前日なら今のモデルの前日にする。木曜（締め切り前のオッズか馬番が無い）なら止める
    （配当の見積もりにも、その日の期待値にも単勝オッズが要るため）。
    """

    def __init__(self) -> None:
        self._timing = TimingChooser()

    def choose(self, con: duckdb.DuckDBPyConnection, race_id: str) -> LegModelChoice:
        """使う確率と理由。木曜しか選べなければ ``LookupError``（速報の取り込みの案内つき）。"""
        signals = RaceSignalReader(con).read_race(race_id)
        if signals.course.startswith(_JUMP_PREFIX):
            return LegModelChoice(LegModel.ODDS_ONLY, _JUMP_REASON, signals.odds_announced_at)
        timing = self._timing.choose_from(signals)
        if timing.timing is PredictionTiming.THURSDAY:
            raise LookupError(self._stop_message(signals, timing.reason))
        model = LegModel.RACE_DAY if timing.timing is PredictionTiming.RACE_DAY else LegModel.DAY_BEFORE
        return LegModelChoice(model, timing.reason, signals.odds_announced_at)

    def _stop_message(self, signals: RaceSignals, reason: str) -> str:
        return (
            f"{signals.race_date} {signals.venue}{signals.race_no}R（{signals.rid}）は、今のモデルの木曜の時点しか選べない"
            f"（{reason}）ので、WIN5 の予想を出せません。"
            f"jvdata-store で `jvstore realtime --date {signals.race_date}` を実行して、締め切り前のオッズを取り込んでください"
        )
