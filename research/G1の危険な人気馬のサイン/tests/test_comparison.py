"""G1の人気馬で作り方どうしを比べる表。合成データだけを使う。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.favorites_out_of_top3.dataset import FAVORITE_BAND
from yosou.shared.dataset import HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, TrainingData
from yosou.shared.feature import Feature, FeatureCatalog, FeatureKind
from yosou.shared.feature.odds import TOP3_RATE

from 既存モデルの改善.analysis.walk_forward import PART, PART_TEST, PREDICTION_COLUMN, SEGMENT, WINDOW

from G1の危険な人気馬のサイン.analysis.race_scope import G1_RACES, LOWER_STAKES
from G1の危険な人気馬のサイン.analysis.scope_comparison import ScopeComparison
from G1の危険な人気馬のサイン.analysis.scope_test_rows import ScopeTestRows
from G1の危険な人気馬のサイン.analysis.sign_columns import SIGN_COUNT
from G1の危険な人気馬のサイン.analysis.sign_training_table import GRADE

_LABEL = "4着以下"


def _data(rng: np.random.Generator) -> TrainingData:
    """2020・2021年、1年 20レース × 人気馬5頭。半分のレースが G1、残りは G3。"""
    rows = []
    for year in (2020, 2021):
        for race in range(20):
            popularity = np.arange(1, 6)
            out = np.clip(0.35 + 0.08 * (popularity - 1), 0.05, 0.95)
            rows.append(pd.DataFrame({
                RACE_ID: f"{year}{race:04d}", RACE_DATE: pd.Timestamp(year, 1 + race % 12, 5),
                HORSE_ID: [f"h{n}" for n in popularity], HORSE_NO: popularity, "確定の単勝人気": popularity,
                FAVORITE_BAND: ["1番人気", "2〜3番人気", "2〜3番人気", "4〜5番人気", "4〜5番人気"],
                GRADE: "A" if race % 2 == 0 else "C", TOP3_RATE: 1 - out, "単勝の払戻": 0, "複勝の払戻": 0,
                SIGN_COUNT: popularity % 3, _LABEL: (rng.random(5) < out).astype(int),
            }))
    frame = pd.concat(rows, ignore_index=True)
    catalog = FeatureCatalog((Feature(SIGN_COUNT, "危険サイン", FeatureKind.NUMERIC),))
    evaluation = frame[["確定の単勝人気", FAVORITE_BAND, GRADE, TOP3_RATE, "単勝の払戻", "複勝の払戻"]]
    return TrainingData(frame[[RACE_ID, RACE_DATE, HORSE_ID, HORSE_NO]], frame[[SIGN_COUNT]], frame[[_LABEL]], evaluation,
                        catalog, _LABEL)


def _predictions(data: TrainingData, probability: pd.Series, only_g1: bool = False) -> pd.DataFrame:
    rows = data.evaluation[GRADE].eq("A") if only_g1 else pd.Series(True, index=data.ids.index)
    window = data.ids[RACE_DATE].dt.year.map(lambda year: f"{year}年")
    return data.ids[rows].assign(**{PREDICTION_COLUMN: probability[rows], WINDOW: window[rows], PART: PART_TEST,
                                    SEGMENT: "全体"})


def test_rows_keep_only_g1_favorites_shared_by_every_variant():
    data = _data(np.random.default_rng(0))
    market = 1 - data.evaluation[TOP3_RATE]
    predictions = {"odds_only": _predictions(data, market), "g1-signs": _predictions(data, market, only_g1=True)}
    rows = ScopeTestRows(G1_RACES).build(data, predictions)
    assert set(rows["variant"]) == {"odds_only", "g1-signs"}
    # G1 は 2年 × 10レース × 5頭
    assert rows.groupby("variant").size().tolist() == [100, 100]


def test_comparison_counts_windows_against_odds_only_and_the_current_model():
    data = _data(np.random.default_rng(1))
    market = 1 - data.evaluation[TOP3_RATE]
    label = data.label.astype(float)
    predictions = {
        "odds_only": _predictions(data, market),
        "all-current": _predictions(data, market * 0.98 + 0.01),
        "g1-signs": _predictions(data, (market * 0.5 + label * 0.5).clip(0.01, 0.99), only_g1=True),  # 答えを混ぜた作り方
    }
    tables = ScopeComparison(G1_RACES).tables(data, predictions)
    assert [table.title[:6] for table in tables] == ["G1: 1.", "G1: 2.", "G1: 3.", "G1: 4."]
    scores = {row[0]: row for row in tables[0].rows}
    signs = scores["G1だけで学ぶ・今の材料 ＋ サイン"]
    assert signs[tables[0].columns.index("オッズだけより小さい区切り")] == "2/2（不合格）"  # 区切りが2つしかないので5つに届かない
    assert len(tables[1].rows) == 2


def test_rows_of_another_scope_use_the_g1_model_predictions_there_too():
    data = _data(np.random.default_rng(2))
    market = 1 - data.evaluation[TOP3_RATE]
    # G1 で学んだモデルも、全部の行に予測がある（ScopedWindowTrainer の出力）
    predictions = {"odds_only": _predictions(data, market), "g1-signs": _predictions(data, market)}
    rows = ScopeTestRows(LOWER_STAKES).build(data, predictions)
    assert rows.groupby("variant").size().tolist() == [100, 100]
