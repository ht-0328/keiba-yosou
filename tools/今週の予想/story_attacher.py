"""各馬の結果に近走の文を付ける。"""

from __future__ import annotations

from datetime import date
from typing import Any

import duckdb

from yosou.review import ReviewStore
from 近走の文.past_run_reader import PastRunReader
from 近走の文.past_run_story import RUNS_SHOWN, PastRunStory
from 近走の文.story_writer import StoryWriter
from 今週の予想.forecast_columns import HORSE_ID, HORSE_NAME

#: 各馬の結果に足す鍵。
STORY = "story"


class StoryAttacher:
    """今週の予想の各馬の結果（辞書）に、近走の文（``近走の文/``）を ``story`` として付ける。

    ``story`` は ``career_runs``（中央の出走数）・``runs``（古い順。``date``・``text``・``reasons``）・``words``（評価のことば）・
    ``lines``（人が読む箇条書き。CLI と次のレースの予想がそのまま出す）。基準日はレースの日（その日より前の走だけ）。
    回顧の不利は ``store``（既定は ``reports/回顧/review.duckdb``）から。
    """

    def __init__(self, store: ReviewStore | None = None, runs_shown: int = RUNS_SHOWN) -> None:
        self._store = store
        self._story = PastRunStory(runs_shown)
        self._writer = StoryWriter()

    def attach(self, con: duckdb.DuckDBPyConnection, horses: list[dict[str, Any]], race_date: date) -> None:
        history = PastRunReader(con, self._store).read([str(horse[HORSE_ID]) for horse in horses], race_date)
        for horse in horses:
            horse_id = str(horse[HORSE_ID])
            story = self._story.of(horse_id, str(horse.get(HORSE_NAME) or ""), history.get(horse_id, []))
            horse[STORY] = {
                "career_runs": story.career_runs,
                "runs": [{"date": line.run.race_date.isoformat(), "text": line.sentence, "reasons": list(line.reasons)} for line in story.lines],
                "words": list(story.words),
                "lines": self._writer.body(story),
            }
