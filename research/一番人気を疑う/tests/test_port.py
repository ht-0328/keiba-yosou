"""移したあとの確かめの部品のテスト。架空の値だけを使う。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import PredictionTiming

from 一番人気を疑う.analysis.port import PORT_COMPARISONS, PORT_VARIANTS, PortComparison


def _frame(scores: list[float], windows: list[str], horses: list[str]) -> pd.DataFrame:
    """1頭ずつの予測。答えは、どの区切りも1頭目が 1、2頭目が 0。"""
    return pd.DataFrame({"レースID": [f"r{index // 2}" for index in range(len(scores))], "馬ID": horses,
                         "score": scores, "3着以内": [1, 0] * (len(scores) // 2), "区切り": windows})


def test_比べるのは両方にある行だけ() -> None:
    current = _frame([0.6, 0.4, 0.6, 0.4], ["前半", "前半", "後半", "後半"], ["a", "b", "c", "d"])
    ported = _frame([0.7, 0.3], ["前半", "前半"], ["a", "b"])
    left, right = PortComparison().common(current, ported)
    assert left["馬ID"].tolist() == right["馬ID"].tolist() == ["a", "b"]


def test_区切りの過半で小さく全期間でも小さければ採用() -> None:
    windows = [name for name in ("1", "2", "3", "4", "5", "6", "7") for _ in range(2)]
    horses = [f"h{index}" for index in range(14)]
    current = _frame([0.6, 0.4] * 7, windows, horses)
    # 5つの区切りで当たり（1頭目を高く）、2つの区切りで外れ（低く）
    ported = _frame([0.8, 0.2] * 5 + [0.5, 0.5] * 2, windows, horses)
    comparison = PortComparison()
    table = comparison.by_window(current, ported)
    assert int(table.loc[table["区切り"] != "全期間", "小さい"].sum()) == 5
    assert comparison.adopted(table)
    worse = _frame([0.8, 0.2] * 4 + [0.5, 0.5] * 3, windows, horses)
    assert not comparison.adopted(comparison.by_window(current, worse))


def test_時点ごとに今の予想と移した作り方を比べる() -> None:
    assert [spec.timing for spec in PORT_COMPARISONS] == [*PredictionTiming, PredictionTiming.RACE_DAY]
    assert len({variant.key for variant in PORT_VARIANTS}) == len(PORT_VARIANTS) == 7
    # 木曜は基準（オッズ）を使わず、前日・当日は使う
    assert all(spec.current.uses_baseline == spec.ported.uses_baseline == (spec.timing is not PredictionTiming.THURSDAY)
               for spec in PORT_COMPARISONS)


def test_今の材料の表の行に足す材料の列をつなぐ() -> None:
    from yosou.shared.dataset import TrainingData
    from yosou.shared.feature import Feature, FeatureCatalog, FeatureKind

    from 一番人気を疑う.analysis.port import TableMerge

    def data(ids: list[str], features: dict[str, list[float]], names: tuple[str, ...]) -> TrainingData:
        catalog = FeatureCatalog(tuple(Feature(name, "X", FeatureKind.NUMERIC) for name in names))
        frame = pd.DataFrame({"レースID": ["r1"] * len(ids), "馬ID": ids})
        return TrainingData(frame, pd.DataFrame(features), pd.DataFrame({"3着以内": [0] * len(ids)}),
                            pd.DataFrame(index=frame.index), catalog, "3着以内")

    base = data(["a", "b"], {"距離": [1600.0, 1600.0], "単勝オッズ": [2.0, 5.0]}, ("距離", "単勝オッズ"))
    extra = data(["b", "c"], {"指数_前走": [80.0, 70.0], "単勝オッズ": [9.0, 9.0]}, ("指数_前走", "単勝オッズ"))
    names = ("距離", "単勝オッズ", "指数_前走")
    merged = TableMerge().merge(base, extra, FeatureCatalog(tuple(Feature(n, "X", FeatureKind.NUMERIC) for n in names)))
    # 今の材料の行のまま、同じ出走の M の列を足す。足す側にしか無い出走（c）は入らず、重なる列（単勝オッズ）は今の材料のまま
    assert merged.ids["馬ID"].tolist() == ["a", "b"]
    assert merged.features["指数_前走"].isna().tolist() == [True, False] and merged.features["単勝オッズ"].tolist() == [2.0, 5.0]
