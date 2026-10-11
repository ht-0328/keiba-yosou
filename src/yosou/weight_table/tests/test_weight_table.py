"""馬体重の表（帯・表 W・割引・年ごとの付け方・判定）。DB を使わず、手で作った表で確かめる。"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_DATE, RACE_ID, TOP3, PredictionData, TrainingData
from yosou.shared.feature import BASE_FEATURES, FeatureCatalog, PredictionTiming

from .. import names
from ..race_weight_discount_attacher import RaceWeightDiscountAttacher
from ..weight_bands import WeightBands
from ..weight_discount_columns import AGE, INTERVAL_DAYS, WEIGHT_CHANGE
from ..weight_discount_free_data import WeightDiscountFreeData
from ..weight_judge import WeightJudge
from ..weight_runs import WeightRuns
from ..weight_table_builder import POOL_WEIGHT, WeightTableBuilder
from ..yearly_weight_discount import YearlyWeightDiscount

FIRST = BASE_FEATURES[0].name


def test_帯は_設計書の区切りで分け_無い値は欠損値():
    bands = WeightBands().of(pd.Series([-12, -9, -4, -3, 3, 4, 9, 10, np.nan]), pd.Series([28, 29, 70, 71, 7, 7, 7, 7, 7]),
                             pd.Series([3, 3, 4, 2, 5, 3, 3, 3, 3]))
    assert bands[names.CHANGE_BAND].tolist()[:8] == [names.CHANGE_BIG_LOSS, names.CHANGE_LOSS, names.CHANGE_LOSS, names.CHANGE_FLAT,
                                                     names.CHANGE_FLAT, names.CHANGE_GAIN, names.CHANGE_GAIN, names.CHANGE_BIG_GAIN]
    assert bands[names.INTERVAL_BAND].tolist()[:4] == [names.INTERVAL_SHORT, names.INTERVAL_MIDDLE, names.INTERVAL_MIDDLE, names.INTERVAL_LONG]
    assert bands[names.AGE_BAND].tolist()[:5] == [names.AGE_YOUNG, names.AGE_YOUNG, names.AGE_OLD, names.AGE_YOUNG, names.AGE_OLD]
    assert pd.isna(bands.loc[8, names.CHANGE_BAND]) and bands.loc[8, names.INTERVAL_BAND] == names.INTERVAL_SHORT


def _runs() -> pd.DataFrame:
    rows = []
    for i in range(400):
        day = pd.Timestamp("2023-01-01") + pd.Timedelta(days=i % 300)
        # 2頭立てのレース。1頭目は −12kg（3歳・中2週）で、市場は半々と見るが来ない。2頭目は +0kg で来る
        rows.append({"race_id": f"r{i}", "race_date": day, "horse_id": "a", "weight_change": -12, "interval_days": 14, "age": 3,
                     "finish": 2 if i % 4 else 1, "win_odds": 2.0})
        rows.append({"race_id": f"r{i}", "race_date": day, "horse_id": "b", "weight_change": 0, "interval_days": 14, "age": 3,
                     "finish": 1 if i % 4 else 2, "win_odds": 2.0})
    return pd.DataFrame(rows)


def test_表Wは_増減の帯ごとに市場の見立てとの差を数え_件数の少ないマスを帯の全体に寄せる():
    prepared = WeightRuns().build(_runs())
    assert set(prepared[names.TOP3].unique()) == {1.0}   # 2頭立てはどちらも3着以内（3着以内の定義は展開スコアと同じ）
    table = WeightTableBuilder().build(prepared)
    row = table.frame[table.frame[names.CHANGE_BAND] == names.CHANGE_BIG_LOSS].iloc[0]
    assert row[names.COUNT] == 400 and abs(row[names.RAW_GAP] - row[names.BAND_GAP]) < 1e-9
    assert abs(row[names.GAP] - (400 * row[names.RAW_GAP] + POOL_WEIGHT * row[names.BAND_GAP]) / (400 + POOL_WEIGHT)) < 1e-9
    assert table.as_of == date(2023, 10, 27)
    looked = table.lookup(pd.DataFrame({names.CHANGE_BAND: [names.CHANGE_BIG_LOSS, names.CHANGE_BIG_GAIN, None],
                                        names.INTERVAL_BAND: names.INTERVAL_SHORT, names.AGE_BAND: names.AGE_YOUNG}, index=[5, 6, 7]))
    assert abs(looked[5] - row[names.GAP]) < 1e-9 and np.isnan(looked[6]) and np.isnan(looked[7]) and list(looked.index) == [5, 6, 7]
    assert WeightTableBuilder().build(prepared, before=date(2023, 1, 1)).frame.empty


def _prediction_data() -> PredictionData:
    ids = pd.DataFrame({RACE_ID: ["r1", "r1"], HORSE_ID: [11, 12]}, index=[5, 6])
    features = pd.DataFrame({FIRST: [1.0, 1.0], WEIGHT_CHANGE: [-12.0, np.nan], INTERVAL_DAYS: [14.0, 14.0], AGE: [3.0, 3.0]}, index=[5, 6])
    return PredictionData(ids, features, PredictionTiming.RACE_DAY, FeatureCatalog(BASE_FEATURES[:1]))


def test_予測用データには表Wを引いて1列足し_外せば消える():
    table = WeightTableBuilder().build(WeightRuns().build(_runs()))
    data = RaceWeightDiscountAttacher(table).attach(_prediction_data(), "r1", PredictionTiming.RACE_DAY, None)
    assert list(data.features.columns)[-1] == names.DISCOUNT and data.catalog.names[-1] == names.DISCOUNT
    assert not np.isnan(data.features.loc[5, names.DISCOUNT]) and np.isnan(data.features.loc[6, names.DISCOUNT])
    freed = WeightDiscountFreeData().prediction(data)
    assert names.DISCOUNT not in freed.features.columns and names.DISCOUNT not in freed.catalog.names
    assert WeightJudge().of(pd.Series([-0.03, -0.01, np.nan])).tolist() == [names.DISCOUNTED, names.NEUTRAL, names.NEUTRAL]


def test_学習データには年ごとに_その年より前の表で付ける():
    prepared = WeightRuns().build(_runs())
    ids = pd.DataFrame({RACE_ID: ["x", "y"], RACE_DATE: [pd.Timestamp("2023-06-01"), pd.Timestamp("2024-06-01")], HORSE_ID: ["a", "b"]}, index=[3, 4])
    features = pd.DataFrame({FIRST: [1.0, 2.0], WEIGHT_CHANGE: [-12.0, -12.0], INTERVAL_DAYS: [14.0, 14.0], AGE: [3.0, 3.0]}, index=[3, 4])
    data = TrainingData(ids, features, pd.DataFrame({TOP3: [1, 0]}, index=ids.index), pd.DataFrame(index=ids.index), FeatureCatalog(BASE_FEATURES[:1]), TOP3)
    built = YearlyWeightDiscount().apply(data, prepared)
    # 2023年の行は 2023年より前の表（レースが無い）なので欠損値、2024年の行は 2023年の表で引ける
    assert np.isnan(built.features.loc[3, names.DISCOUNT]) and not np.isnan(built.features.loc[4, names.DISCOUNT])
    assert built.catalog.names == (FIRST, names.DISCOUNT) and built.targets is data.targets
    assert YearlyWeightDiscount().apply(built, prepared).features.shape == built.features.shape
