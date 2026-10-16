"""StoryAttacher（各馬の結果に近走の文を付ける）のテスト。合成DB の確定前のレースで確かめる。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from 共通 import db

from yosou.review import ReviewStore
from 今週の予想.story_attacher import STORY, StoryAttacher
from 近走の文.card_horse_repository import CardHorseRepository

#: 合成DB の確定前のレース（2025-04-19 東京 1R 出走馬名表）の rid。
CARD_RID = "2025041905010101"


def test_each_horse_gets_runs_words_and_lines(card_db: Path, tmp_path: Path):
    with db.open_db(card_db) as con:
        card = CardHorseRepository(con).read(CARD_RID)
        horses = [{"horse_id": row.horse_id, "horse_name": row.horse_name, "mark": "－"} for row in card.itertuples(index=False)]
        horses.append({"horse_id": "9999999999", "horse_name": "過去走の無い馬", "mark": "－"})
        StoryAttacher(ReviewStore(tmp_path / "no-review.duckdb")).attach(con, horses, date(2025, 4, 19))
    for horse in horses:
        story = horse[STORY]
        assert set(story) == {"career_runs", "runs", "words", "lines"}
        assert len(story["runs"]) <= 5 and story["career_runs"] >= len(story["runs"])
        assert all(set(run) == {"date", "text", "reasons"} and run["date"] < "2025-04-19" for run in story["runs"])
        assert story["lines"] and story["lines"][0].startswith("- ")
    # 合成DB の馬は 2024年に走っているので文がある。過去走の無い馬は「無い」の1行
    assert any(horse[STORY]["runs"] for horse in horses[:-1])
    assert horses[-1][STORY] == {"career_runs": 0, "runs": [], "words": [], "lines": ["- 中央での過去走が無い"]}
