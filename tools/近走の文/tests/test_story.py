"""近走の文: 1走の文・敗因の候補・苦手の傾向・まとめと、合成DB からの読み込み。"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from 共通 import db, facts

from yosou.review import names
from yosou.review.repository.review_store import ReviewStore
from 近走の文 import story
from 近走の文.card_horse_repository import CardHorseRepository
from 近走の文.evaluation_words import EvaluationWords
from 近走の文.horse_story import HorseStory
from 近走の文.loss_reason import LossReason
from 近走の文.past_run import PastRun
from 近走の文.past_run_reader import PastRunReader
from 近走の文.past_run_story import PastRunStory
from 近走の文.race_pace_repository import RacePaceRepository
from 近走の文.record import Record
from 近走の文.review_note_repository import ReviewNoteRepository
from 近走の文.run_line import RunLine
from 近走の文.run_sentence import RunSentence
from 近走の文.story_writer import StoryWriter

#: 合成DB の確定前のレース（2025-04-19 東京 1R 出走馬名表）の rid。
CARD_RID = "2025041905010101"


def _run(**over) -> PastRun:
    """文の材料がそろった1走（架空の値）。``over`` で一部を変える。"""
    values = dict(
        race_id="2026062109030611", race_date=date(2026, 6, 21), horse_id="2023100001", venue="阪神", race_name="テストステークス",
        class_name="G3", grade="G3", surface="芝", distance_m=1600, condition="稍重", field_size=18, frame_no=6, popularity=1,
        finish=3, time_diff=0.1, first_corner_rank=16, corner4=14, last3f=33.9, last3f_rank=2, last3f_count=18, jockey="騎手A",
        carried=53.0, body_weight=476, weight_change=-4, interval_days=42, class_order=8, pace=0.9, handicaps=(),
    )
    values.update(over)
    return PastRun(**values)


def _history(*finishes: int, **over) -> list[PastRun]:
    """月ごとに1走ずつ、着順だけ違う走の並び（古い順）。"""
    return [_run(race_id=f"20260{index + 1:02d}0109030611", race_date=date(2026, index + 1, 1), finish=finish, **over)
            for index, finish in enumerate(finishes)]


# ---- 型と言葉 ----

def test_record_counts_finishes_and_place_rate():
    record = Record.of([_run(finish=1), _run(finish=2), _run(finish=3), _run(finish=9), _run(finish=None)])
    assert record.text == "1-1-1-1" and record.count == 4 and record.place_rate == 0.75
    assert Record.of([]).place_rate == 0.0


def test_the_run_knows_its_words():
    run = _run()
    assert run.lost is False and run.label == "テストステークス" and run.qualifier == "G3"
    assert run.early_zone == "後方" and run.pace_name == "ハイ"
    assert _run(first_corner_rank=1).early_zone == "先頭" and _run(first_corner_rank=3).early_zone == "先団"
    assert _run(first_corner_rank=9).early_zone == "中団" and _run(first_corner_rank=None).early_zone is None
    assert _run(pace=-0.9).pace_name == "スロー" and _run(pace=0.1).pace_name == "ミドル" and _run(pace=None).pace_name is None
    plain = _run(race_name="", class_name="未勝利", grade="", finish=4)
    assert plain.lost and plain.label == "未勝利" and plain.qualifier == ""
    special = _run(race_name="三面川特別", class_name="2勝クラス", grade="")
    assert special.qualifier == "2勝クラス"


# ---- 1走の文 ----

def test_the_sentence_has_header_result_flow_and_people():
    assert RunSentence().of(_run()) == (
        "2026-06-21 テストステークス（G3 阪神 芝1600m 稍重 18頭）3着・1番人気・着差 +0.1秒。"
        "ハイペースを後方（最初のコーナー 16番手）で運び、4角 14番手から追い込んで、上がり 33.9秒（2位/18頭）。"
        "騎手A 53kg、馬体重 476kg（-4）。"
    )


def test_the_sentence_omits_missing_materials():
    text = RunSentence().of(_run(popularity=None, time_diff=None, pace=None, first_corner_rank=None, corner4=None, last3f=None,
                                 jockey="", body_weight=None, field_size=None))
    assert text == "2026-06-21 テストステークス（G3 阪神 芝1600m 稍重）3着。"
    stopped = RunSentence().of(_run(finish=None, pace=None, first_corner_rank=None, corner4=None, last3f=None))
    assert stopped.endswith("18頭）着順なし（競走中止など）。騎手A 53kg、馬体重 476kg（-4）。")
    pace_only = RunSentence().of(_run(finish=None, first_corner_rank=None, corner4=None, last3f=None))
    assert "着順なし（競走中止など）。ハイペースのレース。騎手A" in pace_only


def test_the_flow_words_follow_the_position_change():
    sentence = RunSentence()
    assert "4角 14番手から追い込んで" in sentence.of(_run(corner4=14, finish=3))
    assert "4角 2番手から順位を下げて" in sentence.of(_run(corner4=2, finish=13))
    assert "4角 5番手から、" in sentence.of(_run(corner4=5, finish=4))
    assert "上がり最速の 33.2秒" in sentence.of(_run(last3f=33.2, last3f_rank=1))
    assert "ハイペースの中、4角" in sentence.of(_run(first_corner_rank=None))
    assert "中団（最初のコーナー 9番手）で運び、4角" in sentence.of(_run(first_corner_rank=9, pace=None))


# ---- 敗因の候補 ----

def test_no_reason_for_a_top3_run_and_only_debut_for_the_first_run():
    reason = LossReason()
    assert reason.of(_run(finish=3), [_run(finish=3)]) == []
    first = _run(finish=5, condition="重", handicaps=("出遅れ（中）",))
    assert reason.of(first, [first]) == ["不利: 出遅れ（中）", "初出走"]


def test_first_time_conditions_are_facts_not_contrasts():
    earlier = _history(1, 2, condition="良", surface="ダート", distance_m=1400, class_order=4, class_name="2勝クラス")
    run = _run(race_date=date(2026, 6, 1), finish=8, condition="不良", surface="芝", distance_m=1600, class_order=8, class_name="G3")
    assert LossReason().of(run, [*earlier, run]) == [
        "初めての重・不良の馬場", "初めての芝", "初めての 1600m（前走 1400m から延長）", "前走より上のクラス（2勝クラス → G3）",
    ]


def test_contrasts_use_only_the_runs_up_to_that_run():
    heavy_losses = _history(9, 8, condition="重")
    firm_wins = _history(1, 1, 2, condition="良")
    firm_wins = [replace(run, race_id=run.race_id.replace("2026", "2025"), race_date=run.race_date.replace(year=2025)) for run in firm_wins]
    later = _run(race_id="2027010109030611", race_date=date(2027, 1, 1), finish=1, condition="重")
    history = [*firm_wins, *heavy_losses, later]
    second_heavy = heavy_losses[1]
    reasons = LossReason().of(second_heavy, history)
    # その走までの成績で対比する（後の重の1着は数えない）
    assert "重い馬場（重・不良では 0-0-0-2、良・稍重では 2-1-0-0）" in reasons
    # 最初の重の走は対比の材料が1走しか無いので「初めて」になる
    assert "初めての重・不良の馬場" in LossReason().of(heavy_losses[0], history)


def test_distance_class_rest_and_weight_reasons():
    earlier = [*_history(1, 1, distance_m=1600, class_order=6, class_name="オープン"),
               *[replace(run, race_id=run.race_id.replace("20260", "20261"), race_date=run.race_date.replace(month=run.race_date.month + 6),
                         distance_m=2000, finish=9) for run in _history(9, 8, class_order=6, class_name="オープン")]]
    run = _run(race_date=date(2026, 12, 1), finish=10, distance_m=2000, class_order=8, class_name="G3", interval_days=90, weight_change=12)
    reasons = LossReason().of(run, [*earlier, run])
    assert reasons == [
        "距離（2000m では 0-0-0-3、ほかの距離では 2-0-0-0）", "前走より上のクラス（オープン → G3）",
        "休み明け（前走から 90日）", "馬体重 +12kg",
    ]


def test_evaluation_words_improving_and_big_losses():
    words = EvaluationWords()
    improving = [replace(run, time_diff=gap) for run, gap in zip(_history(9, 6, 4), (0.9, 0.4, 0.1))]
    assert words.of(improving) == ["上向き（着差が +0.9 → +0.4 → +0.1秒と縮んでいる）"]
    # 縮みが途切れれば付かない。2走しか無くても付かない
    assert words.of([replace(run, time_diff=gap) for run, gap in zip(_history(9, 6, 4), (0.9, 0.5, 0.5))]) == []
    assert words.of(improving[-2:]) == []
    big = [replace(run, time_diff=gap) for run, gap in zip(_history(2, 9, 8), (0.0, 1.5, 1.2))]
    assert words.of(big) == ["大敗続き（近 2 走の着差 +1.5・+1.2秒）"]
    assert words.of([replace(run, time_diff=gap) for run, gap in zip(_history(9, 8), (1.5, 0.9))]) == []
    assert words.of([]) == []


# ---- まとめと Markdown ----

def test_the_story_keeps_the_last_runs_oldest_first_and_the_writer_lists_them():
    history = _history(1, 9, 2, 10, 3, 4, condition="良")
    history[3] = replace(history[3], handicaps=("出遅れ（大）",))
    story_of = PastRunStory(runs_shown=4).of("2023100001", "ウマA", history)
    assert [line.run.finish for line in story_of.lines] == [2, 10, 3, 4] and story_of.career_runs == 6
    assert story_of.lines[1].reasons and not story_of.lines[0].reasons
    text = "\n".join(StoryWriter().lines(story_of))
    assert text.startswith("### ウマA（中央 6 走のうち近 4 走）\n\n- 2026-03-01 テストステークス")
    assert "\n  - 敗因の候補: " in text and text.count("\n- ") == 4
    empty = StoryWriter().lines(HorseStory("x", "ウマB", [], 0))
    assert empty == ["### ウマB（中央 0 走）", "", "- 中央での過去走が無い", ""]
    with_words = HorseStory("x", "ウマC", [RunLine(_run(), "文。")], 1, words=["上向き（着差が +0.9 → +0.4 → +0.1秒と縮んでいる）"])
    assert StoryWriter().body(with_words) == ["- 文。", "- 評価: 上向き（着差が +0.9 → +0.4 → +0.1秒と縮んでいる）"]
    assert StoryWriter().lines(with_words)[2:] == [*StoryWriter().body(with_words), ""]


# ---- 合成DB からの読み込み ----

def _busiest_horse(con) -> tuple[str, int, date]:
    """いちばん多く走った馬の hid・出走数・最後の走の日。"""
    facts.ensure_facts(con)
    row = con.execute(
        f"SELECT horse_id, count(*), max(CAST(race_date AS DATE)) FROM {facts.FACTS_TABLE} WHERE ran GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 1"
    ).fetchone()
    return str(row[0]), int(row[1]), row[2]


def test_the_reader_returns_runs_before_the_day_in_order(season_db: Path, tmp_path: Path):
    with db.open_db(season_db) as con:
        hid, count, last_day = _busiest_horse(con)
        reader = PastRunReader(con, ReviewStore(tmp_path / "no-review.duckdb"))
        everything = reader.read([hid, "9999999999"], last_day.replace(year=last_day.year + 1))
        until_last = reader.read([hid], last_day)
    runs = everything[hid]
    assert len(runs) == count and len(until_last[hid]) == count - 1 and everything["9999999999"] == []
    assert [run.race_date for run in runs] == sorted(run.race_date for run in runs)
    assert all(run.horse_id == hid and run.venue and run.surface and run.distance_m > 0 for run in runs)
    # 回顧のファイルが無いので不利は付かない。着順の付いた走には4角の順位と上がりがある
    assert all(run.handicaps == () for run in runs)
    finished = [run for run in runs if run.finish is not None]
    assert finished and all(run.corner4 is not None and run.last3f is not None for run in finished)


def test_the_pace_repository_gives_a_number_only_with_enough_earlier_races(season_db: Path):
    with db.open_db(season_db) as con:
        facts.ensure_facts(con)
        race_ids = [str(row[0]) for row in con.execute(
            f"SELECT DISTINCT race_id FROM {facts.FACTS_TABLE} WHERE ran ORDER BY race_id"
        ).fetchall()]
        pace = RacePaceRepository(con).read(race_ids)
    assert list(pace.index) == sorted(race_ids) or set(pace.index) == set(race_ids)
    # 最初のレースには前の同じ条件のレースが無いので欠損値。前3F が全部同じ合成DB では、基準がそろったレースは 0（ミドル）
    assert pd.isna(pace[race_ids[0]])
    assert pace.notna().any() and (pace.dropna() == 0).all()


def test_review_notes_become_words(tmp_path: Path):
    store = ReviewStore(tmp_path / "review.duckdb")
    repository = ReviewNoteRepository(store)
    assert repository.read(["r1"], ["h1"]).empty
    store.write(names.HORSES_TABLE, pd.DataFrame([{
        names.RACE_ID: "r1", names.HORSE_ID: "h1", names.RACE_DATE: date(2026, 1, 1), names.HANDICAPS: "出遅れ・バイアスと逆",
        names.DEGREE: 2, names.NEXT_RUN: names.REVIEW, names.LATE_START_DEGREE: 2, names.PACE_DEGREE: 0, names.BIAS_DEGREE: 1,
    }]))
    notes = repository.read(["r1", "r2"], ["h1"])
    assert len(notes) == 1 and repository.words_of(notes.iloc[0]) == ("出遅れ（中）", "バイアスと逆（小）")


def test_the_card_repository_and_the_command_read_a_card(card_db: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    with db.open_db(card_db) as con:
        horses = CardHorseRepository(con).read(CARD_RID)
    assert len(horses) >= 2 and list(horses.columns) == ["horse_id", "horse_name", "horse_no"]
    args = story.build_parser().parse_args([
        "--rid", CARD_RID, "--db", str(card_db), "--review-db", str(tmp_path / "review.duckdb"), "--out", str(tmp_path / "story.md"),
    ])
    story.main(args)
    text = (tmp_path / "story.md").read_text(encoding="utf-8")
    assert text.startswith("## 2025-04-19") and text.count("\n### ") == len(horses)
    assert capsys.readouterr().out.startswith("## 2025-04-19")


def test_the_command_needs_a_target():
    with pytest.raises(ValueError):
        story.main(story.build_parser().parse_args([]))
