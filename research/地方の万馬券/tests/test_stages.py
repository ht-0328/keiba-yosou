"""段ごとの精度（人気帯の学習データ・消と穴の精度の表・地方の線引き・当日の馬場傾向のレースの値・Markdown の表）。手で作った表で確かめる。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.dataset import TOP3, WIN, BaselineLogit, TrainingData
from yosou.shared.dataset.column_names import POPULARITY
from yosou.shared.feature import FINISH_POWER_NAMES, Feature, FeatureCatalog, FeatureKind, PredictionTiming
from yosou.track_bias import names
from yosou.upset_level.dataset import BetType

from 地方の万馬券.analysis.stages import band_precision as cols
from 地方の万馬券.analysis.stages.band_data import OUT_OF_TOP3, BandData
from 地方の万馬券.analysis.stages.band_precision import DangerPrecision, LongshotPrecision
from 地方の万馬券.analysis.stages.local_upset_rule import LocalUpsetRule
from 地方の万馬券.analysis.stages.markdown_table import markdown_table
from 地方の万馬券.analysis.stages.used_slope_features import NAMES, UsedSlopeFeatures, race_slopes_table


def _training_data() -> TrainingData:
    n = 6
    features = pd.DataFrame({"距離": [1400.0] * n, FINISH_POWER_NAMES[0]: [1.0] * n})
    catalog = FeatureCatalog((Feature("距離", "A", FeatureKind.NUMERIC), Feature(FINISH_POWER_NAMES[0], "Q", FeatureKind.NUMERIC, PredictionTiming.RACE_DAY)))
    ids = pd.DataFrame({"レースID": ["r1"] * n, "開催日": pd.Timestamp("2024-01-01"), "馬ID": [f"h{i}" for i in range(n)], "馬番": range(1, n + 1)})
    targets = pd.DataFrame({TOP3: [1, 1, 0, 1, 0, 0], WIN: [1, 0, 0, 0, 0, 0]})
    evaluation = pd.DataFrame({POPULARITY: [1, 2, 3, 4, 5, 8]})
    baseline = BaselineLogit(pd.Series([1.0, 0.5, 0.0, -0.5, -1.0, -2.0]), PredictionTiming.DAY_BEFORE)
    return TrainingData(ids, features, targets, evaluation, catalog, TOP3, baseline=baseline)


def test_人気帯の学習データは_人気馬が4着以下で基準の符号が変わり_穴馬は4番人気以下で3着以内():
    data = _training_data()
    favorites = BandData().favorites(data)
    assert favorites.label_name == OUT_OF_TOP3 and favorites.label.tolist() == [0, 0, 1]
    assert favorites.evaluation[POPULARITY].tolist() == [1, 2, 3]
    assert favorites.baseline is not None and favorites.baseline.values.tolist() == [-1.0, -0.5, -0.0]
    assert FINISH_POWER_NAMES[0] not in favorites.features.columns          # Q は外す
    longshots = BandData().longshots(data)
    assert longshots.label_name == TOP3 and longshots.label.tolist() == [1, 0, 0]
    assert longshots.evaluation[POPULARITY].tolist() == [4, 5, 8] and longshots.baseline.values.tolist() == [-0.5, -1.0, -2.0]


def _predictions() -> pd.DataFrame:
    # 2レース × 1〜3番人気。r1 は 3番人気が馬券外、r2 は 1番人気が馬券外
    return pd.DataFrame({
        cols.RACE_ID: ["r1"] * 3 + ["r2"] * 3, cols.RACE_DATE: pd.Timestamp("2024-05-01"),
        cols.HORSE_ID: list("abcdef"), cols.HORSE_NO: [1, 2, 3, 1, 2, 3], cols.POPULARITY: [1, 2, 3, 1, 2, 3],
        cols.FINISH: [1, 2, 5, 6, 1, 2], cols.PLACE_PAYOUT: [110, 150, 0, 0, 130, 200], cols.WIN_ODDS: [2.0, 4.0, 6.0, 2.0, 4.0, 6.0],
        cols.P_MODEL: [0.3, 0.4, 0.8, 0.7, 0.3, 0.4], cols.P_MARKET: [0.3, 0.45, 0.6, 0.3, 0.45, 0.6],
        cols.P3_FORM: [0.75, 0.5, 0.3, 0.5, 0.6, 0.5], cols.MARKET_TOP3: [0.7, 0.55, 0.4, 0.7, 0.55, 0.4],
    })


def test_消の精度は_決め方ごとに消した馬の馬券外率と複勝回収率を帯全体と並べる():
    table = DangerPrecision(lines=(0.3,)).table(_predictions())
    by_rule = table.set_index(cols.RULE)
    # ②の差が最大: r1 は c（0.8−0.6）、r2 は d（0.7−0.3）。どちらも馬券外
    assert by_rule.loc[cols.MODEL_EDGE_MAX, cols.COUNT] == 2 and by_rule.loc[cols.MODEL_EDGE_MAX, cols.OUT_RATE] == 1.0
    assert by_rule.loc[cols.MODEL_EDGE_MAX, cols.PLACE_RETURN] == 0.0
    # ①の差が最低: r1 は c（0.3−0.4）、r2 は d（0.5−0.7）
    assert by_rule.loc[cols.FORM_EDGE_MIN, cols.OUT_RATE] == 1.0
    # 線 0.3 以上は r2 の d（差 0.4）だけ。r1 の c は差 0.2
    assert by_rule.loc[f"{cols.MODEL_EDGE_MAX}（差 0.30 以上）", cols.COUNT] == 1
    assert abs(by_rule.loc[cols.MODEL_EDGE_MAX, cols.ALL_OUT_RATE] - 2 / 6) < 1e-9
    assert abs(by_rule.loc[cols.MODEL_EDGE_MAX, cols.ALL_PLACE_RETURN] - 590 / 600) < 1e-9


def test_穴の精度は_帯ごとに上位3頭の3着以内率と複勝回収率を帯全体と並べる():
    table = pd.DataFrame({
        cols.RACE_ID: ["r1"] * 6, cols.RACE_DATE: pd.Timestamp("2025-03-03"), cols.HORSE_ID: list("abcdef"), cols.HORSE_NO: range(1, 7),
        cols.POPULARITY: [4, 5, 6, 7, 8, 9], cols.FINISH: [1, 4, 5, 6, 3, 7], cols.PLACE_PAYOUT: [300, 0, 0, 0, 900, 0], cols.WIN_ODDS: 10.0,
        cols.P_MODEL: [0.5, 0.2, 0.2, 0.1, 0.3, 0.05], cols.P_MARKET: [0.3, 0.25, 0.2, 0.15, 0.1, 0.05],
        cols.P3_FORM: [0.4, 0.3, 0.2, 0.1, 0.2, 0.05], cols.MARKET_TOP3: [0.3, 0.25, 0.2, 0.15, 0.1, 0.05],
    })
    result = LongshotPrecision(lines=(0.15,)).table(table).set_index([cols.BAND, cols.RULE])
    middle = result.loc[(cols.MIDDLE, cols.MODEL_EDGE_TOP3)]
    assert middle[cols.COUNT] == 3 and abs(middle[cols.PLACE_RATE] - 1 / 3) < 1e-9 and abs(middle[cols.PLACE_RETURN] - 1.0) < 1e-9
    big = result.loc[(cols.LONGSHOT, cols.MODEL_EDGE_TOP3)]
    assert big[cols.COUNT] == 2 and big[cols.PLACE_RATE] == 0.5 and abs(big[cols.PLACE_RETURN] - 4.5) < 1e-9
    assert result.loc[(cols.MIDDLE, f"{cols.MODEL_EDGE_TOP3}（差 0.15 以上）"), cols.COUNT] == 1   # 差 0.2 の a だけ
    assert abs(result.loc[(cols.LONGSHOT, cols.MODEL_EDGE_TOP3), cols.ALL_PLACE_RATE] - 0.5) < 1e-9


def test_地方の線引きは_3連単が1万_10万_100万():
    rule = LocalUpsetRule()
    levels = rule.levels_of(BetType.TRIFECTA, pd.Series([9_990.0, 10_000.0, 99_999.0, 100_000.0, 1_000_000.0, np.nan]))
    assert levels.tolist()[:5] == [0.0, 1.0, 1.0, 2.0, 3.0] and np.isnan(levels.iloc[5])
    assert rule.thresholds_of(BetType.WIN) == (300, 1_500, 5_000)


class _Records:
    def __init__(self, race_ids: list[str]) -> None:
        self.race_ids = pd.Index(race_ids)


def test_当日の馬場傾向のレースの値は_1頭ごとの表からレースごとに取り_無いレースは欠損値():
    history = pd.DataFrame({names.RACE_ID: ["r1", "r1", "r2"], names.INNER_SLOPE_FEATURE: [0.1, 0.1, -0.2], names.FRONT_SLOPE_FEATURE: [0.3, 0.3, 0.0]})
    table = race_slopes_table(history)
    assert list(table.columns) == list(NAMES) and table.loc["r2", NAMES[0]] == -0.2
    built = UsedSlopeFeatures(table).build(_Records(["r2", "r9", "r1"]))
    assert list(built.index) == ["r2", "r9", "r1"] and built.loc["r1", NAMES[1]] == 0.3 and np.isnan(built.loc["r9", NAMES[0]])


def test_Markdownの表は_小数を丸め_欠損値は横線():
    text = markdown_table(pd.DataFrame({"年": [2024], "率": [0.12345], "数": [1200], "空": [np.nan]}))
    assert text.splitlines()[2] == "| 2024 | 0.123 | 1200 | — |"
