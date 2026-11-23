"""研究「AIとロジックの予想」の、騎手の暗黙の了解の材料と候補のテスト（合成データだけ）。"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))

import convention_candidates  # noqa: E402
import convention_facts  # noqa: E402
import convention_materials  # noqa: E402


def _run(**values: object) -> dict[str, object]:
    base = {"race_id": "r1", "horse_id": "h1", "year": 2021, "jockey_code": "J1", "finish": 5.0, "style": "差し", "style_before": "差し",
            "first_corner_rank": 8.0, "corner4": 8.0, "field_size": 10.0, "popularity": 5.0, "apprentice": "減量なし"}
    return {**base, **values}


def test_騎手の格は前の年の勝ち数の順位で付き前の年に勝ちが無ければ順位なし() -> None:
    runs = pd.DataFrame([_run(year=2020, jockey_code="J1", finish=1.0), _run(year=2020, jockey_code="J1", finish=1.0),
                         _run(year=2020, jockey_code="J2", finish=1.0), _run(year=2021, jockey_code="J1"),
                         _run(year=2021, jockey_code="J2"), _run(year=2021, jockey_code="J3")])
    ranked = convention_facts.with_jockey_rank(runs)
    this_year = ranked[ranked["year"] == 2021].set_index("jockey_code")
    assert this_year.loc["J1", "jockey_rank"] == 1 and this_year.loc["J2", "jockey_rank"] == 2
    assert this_year.loc["J3", "jockey_rank"] == convention_facts.NO_RANK and this_year.loc["J3", "jockey_class"] == "61-"
    assert (ranked.loc[ranked["year"] == 2020, "jockey_rank"] == convention_facts.NO_RANK).all()


def test_位置を上げる割合は後ろ半分で回った騎乗だけで数え騎乗が少なければ欠損値() -> None:
    rides = [_run(first_corner_rank=8.0, corner4=4.0)] * 10 + [_run(first_corner_rank=8.0, corner4=8.0)] * 30
    rides += [_run(first_corner_rank=2.0, corner4=2.0, style="先行")] * 40 + [_run(jockey_code="J2", first_corner_rank=8.0, corner4=1.0)] * 5
    habits = convention_facts.jockey_habits(pd.DataFrame(rides)).set_index("jockey_code")
    assert habits.loc["J1", "year"] == 2022
    assert habits.loc["J1", "move_rate"] == pytest.approx(0.25) and habits.loc["J1", "front_rate"] == pytest.approx(0.5)
    assert pd.isna(habits.loc["J2", "move_rate"])


def test_レースの材料は逃げの候補の一番人気と人気の前の馬の頭数を数える() -> None:
    runs = pd.DataFrame([_run(horse_id="a", style_before="逃げ", popularity=4.0, apprentice="減量あり"),
                         _run(horse_id="b", style_before="逃げ", popularity=2.0), _run(horse_id="c", style_before="先行", popularity=1.0),
                         _run(horse_id="d", style_before="差し", popularity=3.0), _run(race_id="r2", horse_id="e", style_before="差し", popularity=1.0)])
    features = convention_materials.race_features(runs)
    first = features.loc["r1"]
    assert (first["best_lead_pop"], first["lead_count"], first["lead_apprentices"], first["front_popular"]) == (2.0, 2, 1, 2)
    assert pd.isna(features.loc["r2", "best_lead_pop"]) and features.loc["r2", "lead_count"] == 0


def _races() -> pd.DataFrame:
    """今の AI＋ロジックが買う2レース（a・b）と、買わない2レース（c・d）。"""
    rows = {"a": dict(bought=True, stake=5000, back=10000.0, top_style="差し", top_move_rate=0.05, top_popularity=2.0, best_lead_pop=1.0),
            "b": dict(bought=True, stake=5000, back=0.0, top_style="先行", top_move_rate=0.05, top_popularity=1.0, best_lead_pop=3.0),
            "c": dict(bought=False, stake=0, back=0.0, top_style="逃げ", top_move_rate=0.20, top_popularity=1.0, best_lead_pop=1.0),
            "d": dict(bought=False, stake=0, back=0.0, top_style="逃げ", top_move_rate=0.20, top_popularity=4.0, best_lead_pop=2.0)}
    table = pd.DataFrame.from_dict(rows, orient="index")
    return table.assign(day="2026-01-04", class_name="1勝クラス", front_runners=5, field_size=10, front_popular=1, lead_apprentices=0,
                        top_jockey_class="11-30", f_expected=0.95, f_stake=5000, f_back=[0.0, 0.0, 15000.0, 0.0])


def test_見送りは今買うレースのうち条件に当たるレースだけを外す() -> None:
    after, part = convention_candidates.skipped(_races(), convention_candidates.SKIPS["◎が差し・追込で、騎手が途中で動かない"])
    assert (part["買う"], after["買う"]) == (1, 1)
    assert after["回収率"] == 0.0 and part["回収率"] == pytest.approx(2.0)


def test_買い足しは今買わないレースのうちより人気の逃げの候補がいないレースだけを足す() -> None:
    after, part = convention_candidates.added(_races(), convention_candidates.top_leads_unchallenged)
    assert (part["買う"], after["買う"]) == (1, 3)
    assert after["回収率"] == pytest.approx(25000 / 15000) and after["的中率"] == pytest.approx(2 / 3)
