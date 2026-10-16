"""馬1頭の近走の文をまとめる。"""

from __future__ import annotations

from collections.abc import Sequence

from .evaluation_words import EvaluationWords
from .horse_story import HorseStory
from .loss_reason import LossReason
from .past_run import PastRun
from .run_line import RunLine
from .run_sentence import RunSentence

#: 文にする走の数（新しい方から）。
RUNS_SHOWN = 5


class PastRunStory:
    """馬1頭の過去走（古い順）から、近 ``runs_shown`` 走の文と負けた走の敗因の候補、近走の評価のことばを作る。"""

    def __init__(self, runs_shown: int = RUNS_SHOWN) -> None:
        self._runs_shown = runs_shown
        self._sentence = RunSentence()
        self._reason = LossReason()
        self._words = EvaluationWords()

    def of(self, horse_id: str, name: str, history: Sequence[PastRun]) -> HorseStory:
        shown = list(history)[-self._runs_shown:] if self._runs_shown > 0 else list(history)
        lines = [RunLine(run, self._sentence.of(run), self._reason.of(run, history)) for run in shown]
        return HorseStory(horse_id=horse_id, name=name, lines=lines, career_runs=len(history), words=self._words.of(history))
