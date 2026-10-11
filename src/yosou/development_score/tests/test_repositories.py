"""展開スコアのリポジトリと材料の契約。合成DB（架空の1シーズン）だけを使う。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from 共通 import db

from .. import names
from ..advantage_runs import AdvantageRuns
from ..advantage_table_builder import AdvantageTableBuilder
from ..advantage_table_store import AdvantageTableStore
from ..development_run_repository import COLUMNS, DevelopmentRunRepository
from ..entry_name_repository import HORSE_NAME, HORSE_NO, EntryNameRepository
from ..race_course_repository import RaceCourseRepository
from ..yearly_scorer import YearlyScorer


@pytest.fixture(scope="module")
def runs(season_db: Path) -> pd.DataFrame:
    with db.open_db(season_db) as con:
        return DevelopmentRunRepository(con).read()


def test_全出走は平地の出走した馬だけを開催日の順に読む(runs: pd.DataFrame):
    assert list(runs.columns) == [*COLUMNS, "race_date"] and len(runs) > 0
    assert set(runs["surface"]) <= {"芝", "ダート"} and runs["race_date"].is_monotonic_increasing
    assert pd.api.types.is_datetime64_any_dtype(runs["race_date"])


def test_材料の表と表Gと年ごとの展開スコアが作れる(runs: pd.DataFrame):
    prepared = AdvantageRuns().build(runs)
    for column in (names.STYLE, names.PACE, names.MARKET_TOP3, names.TOP3, names.VENUE_CODE, names.SURFACE):
        assert column in prepared.columns
    assert prepared[names.MARKET_TOP3].dropna().between(0, 1).all() and set(prepared[names.TOP3].dropna()) <= {0.0, 1.0}
    table = AdvantageTableBuilder().build(prepared)
    assert len(table.pool) == 12 and (table.frame.groupby([names.VENUE_CODE, names.SURFACE]).size() == 12).all()
    # 予測の表（架空）に、年ごとの表 G で展開スコアを付ける。材料に無いレースは欠損値
    first = prepared.iloc[0]
    forecasts = pd.DataFrame({"race_id": [first["race_id"], "none"], "horse_id": [first["horse_id"], "x"],
                              "p_leader": [0.3, 0.3], "p_front": [0.6, 0.6], "p_middle": [0.3, 0.3], "p_back": [0.1, 0.1],
                              "p_slow": [0.2, 0.2], "p_high": [0.4, 0.4]}, index=[5, 6])
    scored = YearlyScorer().of(forecasts, prepared)
    assert list(scored.index) == [5, 6] and scored[names.SCORE].notna().tolist() == [True, False]
    assert scored["race_date"].iloc[0] == first["race_date"]


def test_表Gはとっておき_元DBが同じなら読み直さない(season_db: Path, tmp_path: Path):
    store = AdvantageTableStore(tmp_path / "cache")
    with db.open_db(season_db) as con:
        built = store.load(con, season_db)
        assert store.is_fresh(season_db)
        again = store.load(con, season_db)
    pd.testing.assert_frame_equal(built.frame, again.frame)
    assert (tmp_path / "cache" / "stamp.json").exists()


def test_レースの競馬場と芝ダ_出走馬の馬番と馬名を読む(season_db: Path, runs: pd.DataFrame):
    race_id = runs["race_id"].iloc[0]
    with db.open_db(season_db) as con:
        course = RaceCourseRepository(con).read(race_id)
        entries = EntryNameRepository(con).read(race_id)
        with pytest.raises(LookupError):
            RaceCourseRepository(con).read("0000000000000000")
    assert course[names.VENUE_CODE].iloc[0] == runs["venue_code"].iloc[0] and course[names.SURFACE].iloc[0] in ("芝", "ダート")
    assert {HORSE_NO, HORSE_NAME, "horse_id"} <= set(entries.columns) and len(entries) >= len(runs[runs["race_id"] == race_id])
