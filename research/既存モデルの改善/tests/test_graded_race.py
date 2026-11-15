"""重賞に特化した予想の確かめの部品（W の SQL・W と K の付け方・重みを付けた作り方）。合成データだけを使う。"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import numpy as np
import pandas as pd
import pytest

from 合成DB import synth
from 共通 import db

from yosou.shared.dataset import HORSE_ID, RACE_ID, TOP3, WIN, TrainingData
from yosou.shared.dataset.column_names import WIN_ODDS
from yosou.shared.feature import Feature, FeatureCatalog, FeatureKind

from 既存モデルの改善.analysis.graded_race import (
    GRADED_VARIANTS,
    IS_GRADED,
    K_NAMES,
    W_NAMES,
    GradedMaterialReader,
    GradedTableBuilder,
    GradedVariant,
)

_HORSE = "2020000001"


def _graded_db(path):
    """同じ重賞（特別競走番号 0123・G2）の 2024年と 2025年の開催と、その間の条件戦。馬 ``_HORSE`` は 3つとも馬番1で走る。"""
    rows = synth.Sample()
    first = synth.race("20240406", "11", grade="B", stakes_no="0123", name="合成ステークス")
    between = synth.race("20240505", "05")
    second = synth.race("20250405", "11", grade="B", stakes_no="0123", name="合成ステークス")
    for race_row, finish in ((first, 2), (between, 1), (second, 4)):
        rows.ra.append(race_row)
        rows.se.append(synth.runner(race_row, 1, 1, finish, hid=_HORSE))
        for num in range(2, 6):
            rows.se.append(synth.runner(race_row, num, num, num if num > finish else num - 1, hid=f"{race_row['開催年']}{race_row['開催月日']}{num:02d}"))
    return synth.build_db(path, rows)


def test_w_counts_only_the_runs_before_the_race_day(tmp_path):
    with db.open_db(_graded_db(tmp_path / "g.duckdb")) as con:
        materials = GradedMaterialReader(con).read(date(2024, 1, 1))
    mine = materials[materials["horse_id"] == _HORSE].sort_values("race_id").reset_index(drop=True)
    assert mine["格"].tolist() == ["G2", "条件", "G2"]
    assert mine[IS_GRADED].tolist() == [1.0, 0.0, 1.0]
    # 1回目の重賞: それより前の出走が無いので、数は 0、着順は欠損値。同じ重賞の経験は 0（前の開催が無い）
    first = mine.iloc[0]
    assert first["前走の格"] == "前走なし" and first["重賞の出走数"] == 0 and pd.isna(first["直近の重賞の着順"])
    assert first["同じ重賞の出走数"] == 0 and pd.isna(first["前年の同じ重賞の着順"])
    # 間の条件戦: 前走は G2。同じ重賞の経験は、重賞でない行なので欠損値
    between = mine.iloc[1]
    assert between["前走の格"] == "G2" and between["重賞の3着以内の数"] == 1 and pd.isna(between["同じ重賞の出走数"])
    # 2回目の重賞: 前走は条件戦、重賞は1戦（2着）。同じ重賞の前の開催で 2着。G2 以上での3着以内は G2 の 2着だけ（条件戦の1着は数えない）
    second = mine.iloc[2]
    assert second["前走の格"] == "条件"
    assert (second["重賞の出走数"], second["重賞の3着以内の数"], second["重賞の勝利数"], second["G1の3着以内の数"]) == (1, 1, 0, 0)
    assert second["今回の格以上での3着以内の数"] == 1 and second["直近の重賞の着順"] == 2
    assert (second["同じ重賞の出走数"], second["同じ重賞の3着以内の数"], second["前年の同じ重賞の着順"]) == (1, 1, 2)
    # 自分の斤量がいちばん重い（合成の出走はみな 57kg）
    assert (mine["トップハンデとの差"] == 0).all()


def _base() -> TrainingData:
    ids = pd.DataFrame({RACE_ID: ["r1", "r1", "r2", "r2"], HORSE_ID: ["a", "b", "a", "c"],
                        "開催日": pd.to_datetime(["2024-01-06"] * 2 + ["2024-01-07"] * 2)})
    features = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0]})
    targets = pd.DataFrame({TOP3: [1, 0, 0, 1], WIN: [1, 0, 0, 0]})
    evaluation = pd.DataFrame({WIN_ODDS: [2.0, 5.0, 3.0, 4.0]})
    catalog = FeatureCatalog((Feature("x", "A", FeatureKind.NUMERIC),))
    return TrainingData(ids, features, targets, evaluation, catalog, TOP3)


def _materials() -> pd.DataFrame:
    rows = []
    for race_id, horse_id, graded in (("r1", "a", 1.0), ("r1", "b", 1.0), ("r2", "a", 0.0), ("r2", "c", 0.0)):
        row = {name: 0.0 for name in W_NAMES}
        row.update({"race_id": race_id, "horse_id": horse_id, IS_GRADED: graded, "格": "G1" if graded else "条件",
                    "重量種別": "定量", "前走の格": "前走なし"})
        rows.append(row)
    return pd.DataFrame(rows)


def test_table_builder_adds_w_and_k_on_the_same_rows():
    base = _base()
    tendency = pd.DataFrame({"race_id": ["r1", "r1"], "horse_id": ["a", "b"], **{name: [0.5, 0.25] for name in K_NAMES}})
    extra = GradedTableBuilder().extra(base, _materials(), tendency)
    assert list(extra.columns) == [*W_NAMES, *K_NAMES] and extra.index.equals(base.features.index)
    # 重賞でない行の K は欠損値
    assert extra[K_NAMES[0]].tolist()[:2] == [0.5, 0.25] and extra[K_NAMES[0]].iloc[2:].isna().all()
    attached = GradedTableBuilder().attach(base, extra)
    assert attached.features.shape[1] == 1 + len(W_NAMES) + len(K_NAMES)
    assert attached.features["格"].dtype == "category" and "格" in attached.categorical_columns


def test_table_builder_stops_when_w_is_missing():
    with pytest.raises(ValueError, match="W の無い行"):
        GradedTableBuilder().extra(_base(), _materials().iloc[:3], pd.DataFrame(columns=["race_id", "horse_id", *K_NAMES]))


def test_variant_weights_the_graded_rows_and_switches_the_label():
    data = replace(_base(), features=_base().features.assign(**{IS_GRADED: [1.0, 1.0, 0.0, 0.0]}))
    top3 = GradedVariant("t", "k", "名前", ("x",), False, label=TOP3, graded_weight=5.0).prepare(data)
    assert top3.weight.tolist() == [5.0, 5.0, 1.0, 1.0] and top3.label_name == TOP3
    assert list(top3.features.columns) == ["x"]
    win = GradedVariant("t", "k", "名前", ("x",), False, label=WIN, graded_weight=5.0).prepare(data)
    assert win.label_name == WIN and win.weight.tolist() == [5.0, 5.0, 1.0, 1.0]
    # 重み 1 は、重みを付けない（今の予想と同じ学び方）
    assert GradedVariant("t", "k", "名前", ("x",), False, graded_weight=1.0).prepare(data).weight is None


def test_the_variants_cover_both_labels_and_the_comparisons():
    keys = [variant.key for variant in GRADED_VARIANTS]
    assert len(set(keys)) == len(keys) == 16
    assert {variant.label for variant in GRADED_VARIANTS} == {TOP3, WIN}
    graded = next(variant for variant in GRADED_VARIANTS if variant.key == "graded-top3")
    general = next(variant for variant in GRADED_VARIANTS if variant.key == "general-top3")
    assert graded.graded_weight == 5.0 and general.graded_weight == 1.0
    assert set(graded.columns) - set(general.columns) == set(W_NAMES) | set(K_NAMES)
    assert np.isclose(next(variant for variant in GRADED_VARIANTS if variant.key == "weight10-win").graded_weight, 10.0)
