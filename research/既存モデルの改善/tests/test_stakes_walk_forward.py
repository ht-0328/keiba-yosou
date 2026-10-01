"""重賞の予想のウォークフォワード（1年ずつの区切り・作り方・比べ方の表）。合成データだけを使う。"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from yosou.shared.dataset import HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, TOP3, BaselineLogit, TrainingData
from yosou.shared.dataset.column_names import FIELD_SIZE, PLACE_ODDS_LOW, PLACE_PAYOUT, POPULARITY, WIN_PAYOUT
from yosou.shared.feature import Feature, FeatureCatalog, FeatureKind, PredictionTiming
from yosou.shared.feature.odds import TOP2_RATE, TOP3_RATE
from yosou.stakes_tendency_top3.feature import CATALOG as STAKES_CATALOG

from 既存モデルの改善.analysis.comparison import FormComparison
from 既存モデルの改善.analysis.tables import STAKES_TABLE_PERIOD, spec_named
from 既存モデルの改善.analysis.variants import variants_of
from 既存モデルの改善.analysis.walk_forward import PART, PART_TEST, PART_VALID, PREDICTION_COLUMN, SEGMENT, WINDOW
from 既存モデルの改善.analysis.windows import STAKES_WINDOWS, WINDOWS, window_named, windows_of

_STAKES = "stakes_tendency_top3"


def test_stakes_use_seven_yearly_windows_and_the_others_keep_half_years():
    assert windows_of(_STAKES) == STAKES_WINDOWS and windows_of("form_aptitude_top3") == WINDOWS
    assert [window.name for window in STAKES_WINDOWS] == [f"{year}年" for year in range(2020, 2027)]
    first = STAKES_WINDOWS[0]
    # 2020年の区切り: 検証は 2019年、テストは 2020年。学習は 2012年1月から 2018年末まで
    assert (first.valid_first_day, first.test_first_day, first.test_last_day) == (date(2019, 1, 1), date(2020, 1, 1),
                                                                                  date(2020, 12, 31))
    assert all(earlier.test_first_day == later.valid_first_day for earlier, later in zip(STAKES_WINDOWS, STAKES_WINDOWS[1:]))
    assert window_named("2025年", STAKES_WINDOWS).test_first_day == date(2025, 1, 1)
    assert spec_named(_STAKES).period == STAKES_TABLE_PERIOD and STAKES_TABLE_PERIOD.train_first_day == date(2012, 1, 1)


def test_stakes_variants_use_columns_known_on_race_day():
    variants = {variant.key: variant for variant in variants_of(_STAKES)}
    assert set(variants) == {"odds_only", "default", "without_tendency"}
    race_day = set(STAKES_CATALOG.columns_for(PredictionTiming.RACE_DAY))
    assert all(set(variant.columns) <= race_day and variant.uses_baseline for variant in variants.values())
    # 既定は今の設計の作り方そのもの（当日の 85個）。傾向を外すと、重賞の傾向の10個だけが減る
    assert set(variants["default"].columns) == race_day and len(variants["default"].columns) == 85
    assert len(set(variants["default"].columns) - set(variants["without_tendency"].columns)) == 10


def _synthetic_stakes(rng: np.random.Generator) -> TrainingData:
    """2018〜2021年、1年 30レース × 12頭。人気順に来やすく、基準（オッズから見た3着以内率）は人気から作る。"""
    rows = []
    for year in range(2018, 2022):
        rows.extend(_race_rows(rng, year, race) for race in range(30))
    frame = pd.concat(rows, ignore_index=True)
    ids = frame[[RACE_ID, RACE_DATE, HORSE_ID, HORSE_NO]]
    evaluation = frame[[POPULARITY, FIELD_SIZE, PLACE_ODDS_LOW, TOP2_RATE, TOP3_RATE, WIN_PAYOUT, PLACE_PAYOUT]]
    catalog = FeatureCatalog((Feature("x", "A", FeatureKind.NUMERIC),))
    base = frame[TOP3_RATE]
    baseline = BaselineLogit(np.log(base / (1 - base)), PredictionTiming.DAY_BEFORE)
    return TrainingData(ids, frame[["x"]], frame[[TOP3]], evaluation, catalog, TOP3, baseline=baseline)


def _race_rows(rng: np.random.Generator, year: int, race: int) -> pd.DataFrame:
    popularity = np.arange(1, 13)
    rate = np.clip(0.75 - 0.06 * (popularity - 1), 0.05, 0.9)
    order = np.argsort(-(rate + rng.normal(0, 0.2, 12)))
    label = np.zeros(12, dtype=int)
    label[order[:3]] = 1
    odds = 1.1 + 0.4 * (popularity - 1)
    return pd.DataFrame({
        RACE_ID: f"{year}{race:04d}", RACE_DATE: pd.Timestamp(year, 1 + race % 12, 5), HORSE_ID: [f"h{n}" for n in popularity],
        HORSE_NO: popularity, POPULARITY: popularity.astype(float), FIELD_SIZE: 12, PLACE_ODDS_LOW: odds,
        TOP2_RATE: rate * 0.7, TOP3_RATE: rate, WIN_PAYOUT: 0.0, PLACE_PAYOUT: np.where(label == 1, 100 * odds * 1.1, 0.0),
        "x": 0.0, TOP3: label,
    })


def _predictions(data: TrainingData, probability: pd.Series) -> pd.DataFrame:
    """2020年・2021年の区切りの、検証とテストの予測の表。"""
    parts = [(window.name, PART_VALID, window.valid_first_day, window.test_first_day) for window in STAKES_WINDOWS[:2]]
    parts += [(window.name, PART_TEST, window.test_first_day, date(window.test_first_day.year + 1, 1, 1))
              for window in STAKES_WINDOWS[:2]]
    return pd.concat([_part(data, probability, *part) for part in parts], ignore_index=True)


def _part(data: TrainingData, probability: pd.Series, window: str, part: str, first: date, last: date) -> pd.DataFrame:
    days = data.ids[RACE_DATE]
    rows = (days >= pd.Timestamp(first)) & (days < pd.Timestamp(last))
    return data.ids[rows].assign(**{PREDICTION_COLUMN: probability[rows], WINDOW: window, PART: part, SEGMENT: "全体"})


def test_form_comparison_counts_the_stakes_default_against_odds_only():
    data = _synthetic_stakes(np.random.default_rng(0))
    base = data.evaluation[TOP3_RATE]
    sharper = base * 0.5 + data.label * 0.5
    predictions = {"odds_only": _predictions(data, base), "default": _predictions(data, sharper),
                   "without_tendency": _predictions(data, base)}
    names = {"odds_only": "オッズだけ", "default": "既定", "without_tendency": "既定から重賞の傾向を外す"}
    tables = FormComparison(data, predictions, names, STAKES_WINDOWS[:2], subject="重賞", candidate="default",
                            candidate_label="既定", value_keys=("default", "without_tendency", "odds_only")).tables()
    by_window = tables[0]
    assert by_window.title.startswith("重賞: 区切りごと") and "既定がオッズだけより小さい区切り: 2 / 2" in by_window.note
    assert "既定がオッズだけより小さい" in by_window.columns
    # 複勝を期待値で買う表は、3つの作り方ごとに2つずつ（区切りごとと人気帯ごと）
    value_titles = [table.title for table in tables if "複勝を期待値で買ったとき（テスト期間）" in table.title]
    assert value_titles == [f"重賞（{names[key]}）: 複勝を期待値で買ったとき（テスト期間）"
                            for key in ("default", "without_tendency", "odds_only")]


def test_form_comparison_can_compare_the_thursday_default_with_the_race_day_odds():
    data = _synthetic_stakes(np.random.default_rng(1))
    base = data.evaluation[TOP3_RATE]
    predictions = {"odds_only": _predictions(data, base), "default-thursday": _predictions(data, base * 0.9 + 0.02)}
    names = {"odds_only": "オッズだけ（当日）", "default-thursday": "既定（木曜）"}
    tables = FormComparison(data, predictions, names, STAKES_WINDOWS[:2], subject="重賞（木曜）", candidate="default-thursday",
                            candidate_label="既定", value_keys=("default-thursday",), reference="odds_only").tables()
    assert tables[0].title.startswith("重賞（木曜）: 区切りごと") and "既定がオッズだけ（当日）より小さい" in tables[0].columns
