"""展開スコアの部品の契約。DB を使わず、手で作った表で確かめる（値は架空）。"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.pace_forecast import pace_forecast_columns as source

from .. import names
from ..advantage_judge import AdvantageJudge
from ..advantage_table import CELLS, AdvantageTable, cell
from ..advantage_table_builder import PRIOR_WEIGHT, AdvantageTableBuilder
from ..development_score import COLUMNS, DevelopmentScore
from ..features import DEVELOPMENT_SCORE_FEATURES, DEVELOPMENT_SCORE_NAMES
from ..pre_race_style import PreRaceStyle
from ..result_pace import ResultPace
from ..style_probabilities import StyleProbabilities


def _run(horse: str, day: str, rank, race: str | None = None, field_size: int = 10) -> dict:
    return {"horse_id": horse, "race_date": pd.Timestamp(day), "race_id": race or day.replace("-", "") + horse,
            "first_corner_rank": rank, "field_size": field_size}


def test_レース前の脚質は近5走の先頭率と序盤の位置の平均で決まる():
    runs = pd.DataFrame([
        # A: 先頭 2回・先団 1回・後方 1回 → 先頭率 0.5 で逃げ
        _run("A", "2024-01-06", 1), _run("A", "2024-02-03", 1), _run("A", "2024-03-02", 5), _run("A", "2024-04-06", 9),
        _run("A", "2024-05-04", 3),
        # B: 2番手・3番手 → 位置の平均 (1/9 + 2/9) / 2 ≒ 0.17 で先行
        _run("B", "2024-01-06", 2), _run("B", "2024-02-03", 3), _run("B", "2024-05-04", 7),
        # C: 5番手・6番手 → 0.5 で差し。D: 最後方 → 追込。E: 初出走 → 欠損。F: 前走に最初のコーナーの記録が無い → 欠損
        _run("C", "2024-01-06", 5), _run("C", "2024-02-03", 6), _run("C", "2024-05-04", 1),
        _run("D", "2024-01-06", 10), _run("D", "2024-05-04", 1),
        _run("E", "2024-05-04", 1),
        _run("F", "2024-01-06", np.nan), _run("F", "2024-05-04", 2),
    ])
    today = runs[runs["race_date"] == "2024-05-04"].set_index("horse_id")
    style = PreRaceStyle().of(runs)
    assert style.loc[today.index.map(lambda horse: runs.index[(runs["horse_id"] == horse) & (runs["race_date"] == "2024-05-04")][0])].tolist() == [
        names.LEAD, names.FRONT, names.MIDDLE, names.BACK, None, None]
    # 今回の走は数えない: A の最初の走は過去走が無いので欠損値
    assert style.iloc[0] is None or pd.isna(style.iloc[0])


def _races(count: int, first3f_values, venue: str = "05", track: str = "11", distance: int = 1600) -> list[dict]:
    rows = []
    for number, first3f in enumerate(first3f_values[:count]):
        day = pd.Timestamp("2022-01-01") + pd.Timedelta(days=7 * number)
        rows.append({"race_id": f"{venue}{track}{number:04d}", "race_date": day, "venue_code": venue, "track_code": track,
                     "distance_m": distance, "class_order": 3, "first3f": first3f, "last3f_race": 35.0, "horse_id": "x"})
    return rows


def test_結果のペースは展開の予想と同じ基準と線で分ける():
    history = _races(40, [35.0 + (0.3 if number % 2 else -0.3) for number in range(40)])
    targets = _races(3, [33.0, 37.0, 35.0])
    for number, row in enumerate(targets):
        row["race_id"], row["race_date"] = f"target{number}", pd.Timestamp("2023-06-01") + pd.Timedelta(days=number)
    other_course = _races(1, [33.0], venue="06")
    other_course[0]["race_id"], other_course[0]["race_date"] = "elsewhere", pd.Timestamp("2023-06-10")
    pace = ResultPace().of(pd.DataFrame(history + targets + other_course))
    assert [pace["target0"], pace["target1"], pace["target2"]] == [names.HIGH, names.SLOW, names.EVEN]
    assert pace["elsewhere"] is None or pd.isna(pace["elsewhere"])      # 基準の無いコースは欠損値


def _prepared(rows: list[tuple[str, str, str, str, float, float, str]]) -> pd.DataFrame:
    """(脚質, ペース, 競馬場, 芝ダ, 3着以内, 市場, 開催日) の並び。"""
    return pd.DataFrame(rows, columns=[names.STYLE, names.PACE, names.VENUE_CODE, names.SURFACE, names.TOP3, names.MARKET_TOP3, "race_date"]).assign(
        race_date=lambda frame: pd.to_datetime(frame["race_date"]))


def test_表Gは件数の少ないマスを全競馬場の値に寄せる():
    rows = [(names.LEAD, names.SLOW, "05", "芝", 1.0, 0.3, "2024-01-06")] * 10 + [(names.LEAD, names.SLOW, "05", "芝", 0.0, 0.3, "2024-01-06")] * 0
    rows += [(names.LEAD, names.SLOW, "06", "芝", 0.0, 0.3, "2024-01-06")] * 10
    rows += [(names.BACK, names.HIGH, "05", "芝", 0.0, 0.5, "2025-01-06")]
    table = AdvantageTableBuilder().build(_prepared(rows))
    tokyo = table.frame[(table.frame[names.VENUE_CODE] == "05") & (table.frame[names.SURFACE] == "芝")]
    assert len(tokyo) == 12 and set(table.frame[names.VENUE_CODE]) == {"05", "06"}      # 競馬場ごとに 4 × 3 がそろう
    lead_slow = tokyo[(tokyo[names.STYLE] == names.LEAD) & (tokyo[names.PACE] == names.SLOW)].iloc[0]
    # 東京の逃げ×スローは差 +0.7（10件）、全競馬場は 0.2（20件）。縮めた差 = (10 × 0.7 + 500 × 0.2) ÷ 510
    assert lead_slow[names.COUNT] == 10 and lead_slow[names.RAW_GAP] == pytest.approx(0.7)
    assert lead_slow[names.GAP] == pytest.approx((10 * 0.7 + PRIOR_WEIGHT * 0.2) / (10 + PRIOR_WEIGHT))
    # 件数 0 のマスは全競馬場の値そのもの（全競馬場にも無ければ 0）
    empty = tokyo[(tokyo[names.STYLE] == names.FRONT) & (tokyo[names.PACE] == names.EVEN)].iloc[0]
    assert empty[names.COUNT] == 0 and empty[names.GAP] == 0.0 and np.isnan(empty[names.RAW_GAP])
    assert table.as_of == pd.Timestamp("2025-01-06")
    # before で、その日より前のレースだけにする
    earlier = AdvantageTableBuilder().build(_prepared(rows), before=date(2025, 1, 1))
    assert earlier.as_of == pd.Timestamp("2024-01-06") and set(earlier.frame[names.VENUE_CODE]) == {"05", "06"}


def _design_table() -> AdvantageTable:
    """設計書 05 の 2 の例の表 G（東京・芝）。"""
    values = {names.LEAD: (0.01, 0.06, 0.10), names.FRONT: (0.02, 0.03, 0.04), names.MIDDLE: (0.00, -0.02, -0.03), names.BACK: (-0.01, -0.04, -0.06)}
    rows = [(style, pace, "05", "芝", 1000, gap, gap, gap)
            for style, gaps in values.items() for pace, gap in zip((names.HIGH, names.EVEN, names.SLOW), gaps)]
    frame = pd.DataFrame(rows, columns=[names.STYLE, names.PACE, names.VENUE_CODE, names.SURFACE, names.COUNT, names.RAW_GAP, names.POOL_GAP, names.GAP])
    pool = frame[[names.STYLE, names.PACE, names.COUNT, names.GAP]].assign(**{names.GAP: 0.0})
    return AdvantageTable(frame, pool, pd.Timestamp("2025-12-28"))


def test_表Gの引き方と_材料に無い競馬場は全競馬場の値():
    table = _design_table()
    matrix = table.matrix("05", "芝")
    assert list(matrix.index) == list(names.STYLES) and list(matrix.columns) == list(names.PACES)
    assert matrix.loc[names.LEAD, names.SLOW] == pytest.approx(0.10)
    cells = table.cells_for(pd.Series(["05", "09"], index=[7, 8]), pd.Series(["芝", "芝"], index=[7, 8]))
    assert list(cells.columns) == list(CELLS) and list(cells.index) == [7, 8]
    assert cells.loc[7, cell(names.BACK, names.SLOW)] == pytest.approx(-0.06) and cells.loc[8].eq(0.0).all()


def _forecast(**over) -> pd.DataFrame:
    row = {"race_id": "r", "horse_id": "h", source.LEADER: 0.31, source.FRONT: 0.72, source.MIDDLE: 0.21, source.BACK: 0.07,
           source.SLOW: 0.17, source.HIGH: 0.45, source.FIRST_LOW: -1.0, source.FIRST_MIDDLE: 0.0, source.FIRST_HIGH: 1.0,
           source.CORNER4: 0.2, source.CLOSING: 0.4, source.SECOND_MIDDLE: 0.1}
    row.update(over)
    return pd.DataFrame([row])


def test_脚質の確率は先団から逃げを引き_合計1にそろえる():
    probabilities = StyleProbabilities().of(_forecast())
    assert probabilities[[*names.STYLES]].iloc[0].tolist() == pytest.approx([0.31, 0.41, 0.21, 0.07])
    assert probabilities[[*names.PACES]].iloc[0].tolist() == pytest.approx([0.17, 0.38, 0.45])
    # 先頭の確率が先団の確率より大きいときは先行を 0 にして、合計 1 にそろえる
    odd = StyleProbabilities().of(_forecast(**{source.LEADER: 0.9, source.FRONT: 0.8, source.MIDDLE: 0.15, source.BACK: 0.05}))
    assert odd[names.FRONT].iloc[0] == 0.0 and odd[[*names.STYLES]].iloc[0].sum() == pytest.approx(1.0)
    assert odd[names.LEAD].iloc[0] == pytest.approx(0.9 / 1.1)


def test_展開スコアは設計書の例と同じ値になる():
    courses = pd.DataFrame({"race_id": ["r"], names.VENUE_CODE: ["05"], names.SURFACE: ["芝"]})
    scored = DevelopmentScore().of(_forecast(), courses, _design_table())
    assert list(scored.columns) == list(COLUMNS)
    row = scored.iloc[0]
    assert row[names.contribution(names.LEAD)] == pytest.approx(0.31 * (0.45 * 0.01 + 0.38 * 0.06 + 0.17 * 0.10))
    assert row[names.SCORE] == pytest.approx(0.020, abs=0.001)
    # 競馬場の分からないレースは欠損値
    unknown = DevelopmentScore().of(_forecast(race_id="q"), courses, _design_table())
    assert np.isnan(unknown[names.SCORE].iloc[0])


def test_判定は線で3つに分ける():
    judge = AdvantageJudge(0.02)
    verdict = judge.of(pd.Series([0.03, 0.02, 0.0, -0.02, -0.05, np.nan]))
    assert verdict.tolist()[:5] == [names.FAVORED, names.FAVORED, names.NEUTRAL, names.UNFAVORED, names.UNFAVORED]
    assert verdict.iloc[5] is None
    with pytest.raises(ValueError):
        AdvantageJudge(0.0)


def test_特徴量の一覧は5個の数値で木曜から分かる():
    assert len(DEVELOPMENT_SCORE_FEATURES) == 5 and DEVELOPMENT_SCORE_NAMES[0] == names.SCORE
    assert all(feature.group == "S" and not feature.is_categorical and feature.is_known_at(PredictionTiming.THURSDAY)
               for feature in DEVELOPMENT_SCORE_FEATURES)
