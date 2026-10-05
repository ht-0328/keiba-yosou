"""作ってある予想を、今の DB の材料と比べて判定する。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from 共通.race_signals import RaceSignals

from yosou.shared.feature import PredictionTiming
from 取得と予想の状況.forecast_verdict import ForecastVerdict
from 取得と予想の状況.verdict_kind import VerdictKind
from 今週の予想.forecast_store import ForecastStore
from 今週の予想.forecast_version import FORECAST_VERSION
from 今週の予想.timing_chooser import TimingChooser


class ForecastCheck:
    """1レースの ``RaceSignals`` と、``ForecastStore`` に書いてある予想から ``ForecastVerdict`` を出す。

    判定の順: 中止 → 未予想 → 終了 → 作り方が古い（版が今と違う。``forecast.py --skip-saved`` も作り直す）→
    時点が進んだ（今の DB で選ぶ時点が、予想した時点より後）→ オッズが新しい（予想したあとに新しい断面が入った）→ 最新。
    """

    def __init__(self, store: ForecastStore, chooser: TimingChooser | None = None, version: int = FORECAST_VERSION) -> None:
        self._store = store
        self._chooser = chooser or TimingChooser()
        self._version = version

    def check(self, signals: RaceSignals) -> ForecastVerdict:
        saved = self._store.load(signals.rid)
        current = self._chooser.choose_from(signals).timing.label
        kind, detail = self._judge(signals, saved, current)
        if saved is None:
            return ForecastVerdict(kind, detail, current)
        return ForecastVerdict(kind, detail, current, saved_timing=saved.get("timing"), made_at=_parse_iso(saved.get("made_at")),
                               marks=ForecastStore.marks_text(saved), expectation=saved.get("expectation"))

    def _judge(self, signals: RaceSignals, saved: dict[str, Any] | None, current: str) -> tuple[VerdictKind, str]:
        if signals.is_cancelled:
            return VerdictKind.CANCELLED, ""
        if saved is None:
            return VerdictKind.MISSING, "終了したレース" if signals.is_finished else ""
        if signals.is_finished:
            return VerdictKind.FINISHED, f"{saved.get('timing')}の予想あり"
        if saved.get("version") != self._version:
            return VerdictKind.VERSION_OLD, f"版 {saved.get('version')} → {self._version}。予想し直す"
        saved_timing = str(saved.get("timing", ""))
        if self._advanced(saved_timing, current):
            return VerdictKind.TIMING_ADVANCED, f"{saved_timing} → {current}。予想し直すと{current}のモデルになる"
        announced = signals.odds_announced_datetime()
        if self._odds_newer(announced, _parse_iso(saved.get("made_at"))):
            return VerdictKind.ODDS_NEWER, f"{announced:%H:%M} 発表のオッズが予想より新しい。予想し直すと反映される"
        if saved_timing != current:
            return VerdictKind.FRESH, f"予想は{saved_timing}の時点。今の DB の材料は{current}まで"
        return VerdictKind.FRESH, ""

    @staticmethod
    def _advanced(saved_timing: str, current: str) -> bool:
        """今の DB で選ぶ時点が、予想した時点より後か（``--timing`` で先の時点を指定して作った予想は、後ろに戻さない）。"""
        try:
            saved_at, current_at = PredictionTiming.parse(saved_timing), PredictionTiming.parse(current)
        except ValueError:
            return saved_timing != current
        return current_at != saved_at and current_at.is_at_or_after(saved_at)

    @staticmethod
    def _odds_newer(announced: datetime | None, made_at: datetime | None) -> bool:
        return announced is not None and made_at is not None and announced > made_at


def _parse_iso(text: Any) -> datetime | None:
    """``2026-10-04T11:44:26`` を日時に。無い・形が違えば None。"""
    if not isinstance(text, str) or not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None
