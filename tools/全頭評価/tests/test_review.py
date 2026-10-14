"""全頭評価の組み立てと文書。合成DB の特別登録（4R: 登録だけの 8頭、2R: 出走馬名表 + 地方馬 1頭）で確かめる。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from 共通 import db

from yosou.shared.tests import synthetic_season as season
from 全頭評価.horse_points import HorsePoints
from 全頭評価.review_document import FieldReviewDocument, HorseReview
from 全頭評価.review_writer import ReviewWriter
from 全頭評価.stakes_tendency_points import MIN_RUNS, StakesTendencyPoints
from 全頭評価.field_review import FieldReview
from 全頭評価 import review


def _document(path: Path, models: Path, figure_cache: Path, race_id: str) -> FieldReviewDocument:
    with db.open_db(path) as con:
        return FieldReview(con, models, figure_cache).build(race_id)


def test_the_review_covers_every_registered_horse_with_points(season_db: Path, review_models: Path, figure_cache: Path):
    document = _document(season_db, review_models, figure_cache, season.REGISTRATION_ONLY_RACE_ID)
    assert document.entries == len(document.horses) == season.REGISTRATION_ONLY_FIELD_SIZE
    assert document.race_name == season.REGISTRATION_RACE_NAME and document.grade == "特別" and document.distance_m == 1800
    assert [horse.rank for horse in document.horses] == list(range(1, season.REGISTRATION_ONLY_FIELD_SIZE + 1))
    assert all(0 <= horse.top3 <= 1 and 0 <= horse.win <= 1 for horse in document.horses)
    # 評価順は 3着以内の確率の高い順。有力馬の候補は 1着の確率の上位3頭
    assert [horse.top3 for horse in document.horses] == sorted((horse.top3 for horse in document.horses), reverse=True)
    assert len(document.candidates) == 3 and set(document.candidates) <= {horse.name for horse in document.horses}
    # 全頭に基本情報と、強みか弱みの文が付く。シーズンを走った馬なので前走の文がある
    for horse in document.horses:
        assert "父:" in horse.profile and "調教師:" in horse.profile and "負担重量: 57kg" in horse.profile
        assert horse.strong or horse.weak
        assert any(text.startswith("前走 ") for text in horse.strong + horse.weak)
    # 重賞ではないので、過去の同じレースの傾向は出さない
    assert any("重賞ではない" in note for note in document.notes)


def test_the_entry_list_race_is_reviewed_from_the_registration(season_db: Path, review_models: Path, figure_cache: Path):
    document = _document(season_db, review_models, figure_cache, season.ENTRY_LIST_RACE_ID)
    assert document.entries == season.FUTURE_FIELD_SIZE + 1
    local = [horse for horse in document.horses if horse.exchange == "地方"]
    assert len(local) == 1 and "地方馬" in local[0].profile


def test_the_markdown_has_the_table_and_a_section_per_horse(season_db: Path, review_models: Path, figure_cache: Path):
    document = _document(season_db, review_models, figure_cache, season.REGISTRATION_ONLY_RACE_ID)
    text = ReviewWriter().markdown(document)
    assert text.startswith(f"# {season.REGISTRATION_RACE_NAME}（{season.FUTURE_DAY.isoformat()} ")
    assert "**有力馬の候補**" in text and "| 評価順 | 馬名 |" in text
    assert text.count("\n## ") == season.REGISTRATION_ONLY_FIELD_SIZE and "**強み**" in text and "**弱み**" in text
    for word in ("◎", "印", "期待度", "買い目"):
        assert word not in text


def test_the_command_writes_one_file_per_race(season_db: Path, review_models: Path, figure_cache: Path, tmp_path: Path, capsys):
    with pytest.raises(SystemExit) as stopped:
        review.cli.run(review.build_parser(), review.main, [
            "--date", season.FUTURE_DAY.isoformat(), "--all", "--models", str(review_models), "--figure-cache", str(figure_cache),
            "--db", str(season_db), "--out-dir", str(tmp_path),
        ])
    assert stopped.value.code == 0
    written = sorted((tmp_path / season.FUTURE_DAY.isoformat()).glob("*.md"))
    assert [path.stem for path in written] == [season.ENTRY_LIST_RACE_ID, season.REGISTRATION_ONLY_RACE_ID]
    assert "全頭評価" in capsys.readouterr().out


def test_horse_points_name_the_facts_on_both_sides():
    facts = pd.Series({
        "runs_before": 5, "venue": "東京", "surface": "芝", "distance_m": 1800, "race_name": "合成特別", "course_runs_before": 2,
        "course_wins_before": 1, "course_places_before": 2, "same_race_runs_before": 0, "same_race_places_before": 0, "dist_wins_before": 0,
        "distance_change": "延長", "prev_distance_m": 1600, "surface_change": "同じ", "interval_days": 90, "class_change": "昇級",
        "style_before": "逃げ", "lead_runs_before": 3, "prev_last3f_rank": 1,
    })
    features = pd.Series({
        "指数_条件の重み": 82.0, "能力スコア_順位": 1, "対戦レーティング": 1612.0, "対戦レーティングのレース内順位": 2,
        "調教師_1年_勝率": 0.12, "父×芝ダ_3着内率": 0.27, "父×距離_3着内率": 0.21, "母父_3着内率": 0.16,
        "坂路_本数30日": 2, "ウッド_本数30日": 0, "坂路_4F最速14日_順位": 1, "指数_前走": 80.0, "休み明け_2走目": 0,
    })
    contributions = pd.Series({"指数_条件の重み": 0.3, "指数_前走": 0.1, "調教師_1年_勝率": -0.02, "母父_3着内率": -0.2, "distance_m": 0.5})
    previous = pd.Series({"prev_race_name": "合成記念", "prev_class_name": "G3", "prev_venue": "中山", "prev_surface": "芝",
                          "prev_distance_m": 1600, "prev_finish": 2, "prev_popularity": 4, "prev_time_diff": 0.1})
    result = HorsePoints().of(facts, features, contributions, entries=10, previous=previous)
    strong, weak = "\n".join(result.strong), "\n".join(result.weak)
    assert "能力指数がメンバー中 1位" in strong and "対戦レーティング" in strong and "前走 合成記念（G3）" in strong
    assert "同じコース（東京 芝1800m）で 2戦 1勝" in strong and "先行力" in strong and "父の産駒の同じ芝ダ" in strong
    assert "調教師の近1年の勝率 12.0%" in strong and "坂路の4ハロン最速" in strong and "モデルは「能力」で押し上げ" in strong
    assert "休み明け（前走から 90日）" in weak and "昇級" in weak and "距離延長（1600m → 1800m）" in weak and "母父の産駒" in weak
    assert "モデルは「血統」で割り引き" in weak
    # レースの条件（距離）はレースの全馬に同じなので、寄与の文に出ない
    assert "レースの条件" not in strong + weak


def test_horse_points_mark_a_horse_without_a_career_as_weak():
    facts = pd.Series({"runs_before": 0, "venue": "東京", "surface": "芝", "distance_m": 1600, "race_name": "", "course_runs_before": 0,
                       "same_race_runs_before": 0, "interval_days": None, "class_change": "前走なし", "style_before": None})
    features = pd.Series({"坂路_本数30日": 0, "ウッド_本数30日": 0})
    result = HorsePoints().of(facts, features, pd.Series(dtype=float), entries=8, previous=None)
    assert any("中央での出走が無い" in text for text in result.weak) and any("スピード指数が無い" in text for text in result.weak)
    assert any("調教の記録が無い" in text for text in result.weak)


def test_tendency_lines_compare_the_condition_with_the_whole():
    rows = []
    for edition in range(3):
        for number in range(MIN_RUNS):
            rows.append({"race_id": f"r{edition}", "finish": 1 if number == 0 else 10, "prev_race_name": f"冠{edition}前哨戦", "prev_stakes_no": "9001",
                         "prev_popularity": 1, "interval_days": 90, "affiliation": "栗東", "same_race_places_before": 0,
                         "win_payout": 300 if number == 0 else 0, "place_payout": 150 if number == 0 else 0, "field_size": MIN_RUNS})
        for number in range(MIN_RUNS):
            rows.append({"race_id": f"r{edition}", "finish": 2 if number < 3 else 10, "prev_race_name": "別のレース", "prev_stakes_no": None,
                         "prev_popularity": 6, "interval_days": 30, "affiliation": "美浦", "same_race_places_before": 1, "win_payout": 0,
                         "place_payout": 200 if number < 3 else 0, "field_size": MIN_RUNS})
    editions = pd.DataFrame(rows)
    horse = pd.Series({"prev_popularity": 1, "interval_days": 90, "affiliation": "栗東", "same_race_places_before": 0})
    # 前走が重賞なら特別競走番号で突き合わせる（レース名は年ごとに冠が違ってもよい）
    lines = StakesTendencyPoints().lines_of(editions, horse, "前哨戦", "9001")
    texts = {line.text.split("は ")[0]: line for line in lines}
    assert "過去 3 開催で前走が前哨戦だった馬" in texts and texts["過去 3 開催で前走が前哨戦だった馬"].side is False
    assert "3-0-0-21" in texts["過去 3 開催で前走が前哨戦だった馬"].text and "単勝回収率" in texts["過去 3 開催で前走が前哨戦だった馬"].text
    # 重賞でなければレース名で突き合わせる
    by_name = StakesTendencyPoints().lines_of(editions, horse, "別のレース")
    assert any("前走が別のレース" in line.text and line.side is True for line in by_name)
    assert texts["過去 3 開催で関西馬（栗東）"].side is False and texts["過去 3 開催で休み明け（中9週以上）の馬"].side is False
    assert StakesTendencyPoints().lines_of(pd.DataFrame(), horse, "前哨戦") == []


def test_writer_shows_a_placeholder_when_a_horse_has_no_points():
    horse = HorseReview("1", "ウマ", "牡3　父: 父A　母父: 母父A　調教師: 調教師A（美浦）　負担重量: 57kg", 1, 0.5, 0.2, "牡3", "調教師A", 57.0, "")
    document = FieldReviewDocument("2025011105010104", season.FUTURE_DAY, "合成登録特別", "東京", "芝", 1800, "特別", 1, ["ウマ"], [horse])
    text = ReviewWriter().markdown(document)
    assert "- （目立つ強みは無い）" in text and "- （目立つ弱みは無い）" in text and "| 1 | ウマ | 牡3 | 調教師A | 57 |" in text
