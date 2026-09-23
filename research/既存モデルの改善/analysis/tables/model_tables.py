"""4つの予想の学習データの作り方と、作る期間。"""

from __future__ import annotations

from datetime import date

from yosou.favorites_out_of_top3.dataset import dataset_builder as favorites_builder
from yosou.favorites_out_of_top3.feature import CATALOG as FAVORITES_CATALOG
from yosou.form_aptitude_top3.dataset import dataset_builder as form_builder
from yosou.form_aptitude_top3.feature import CATALOG as FORM_CATALOG
from yosou.longshots_in_top3.dataset import dataset_builder as longshots_builder
from yosou.longshots_in_top3.feature import CATALOG as LONGSHOTS_CATALOG
from yosou.shared.dataset import TrainingPeriod
from yosou.shared.feature import FeatureCatalog
from yosou.upset_level.dataset import UpsetLevel, race_dataset_builder
from yosou.upset_level.feature import CATALOG as UPSET_CATALOG

from ..experiments.experiment_table_builder import experiment_features
from .model_table_spec import ModelTableSpec

#: 学習データを作る期間。ウォームアップは 2016年（DB にある最初の年）、サンプルは 2017年1月から。
#: 使うのはウォームアップと学習の始まりだけで、検証・テストの始まりは期間の後のダミー（区切りは検証の側で決める）。
TABLE_PERIOD = TrainingPeriod(date(2016, 1, 1), date(2017, 1, 1), date(2027, 1, 1), date(2027, 1, 2))

MODEL_TABLES: tuple[ModelTableSpec, ...] = (
    ModelTableSpec("form_aptitude_top3", "近走と適性から3着以内を予想（全頭）", form_builder, FORM_CATALOG),
    ModelTableSpec("longshots_in_top3", "穴馬が3着以内に入るかを予想", longshots_builder, LONGSHOTS_CATALOG),
    ModelTableSpec("favorites_out_of_top3", "人気馬が4着以下になるかを予想", favorites_builder, FAVORITES_CATALOG),
    ModelTableSpec("upset_level", "レースの荒れ具合を4段階で予想", race_dataset_builder, UPSET_CATALOG,
                   UpsetLevel.class_labels()),
)


def _not_built_from_the_database(con):
    raise ValueError("form_experiments は build_experiments.py で作る（build_tables.py では作らない）")


#: 材料の実験の表（全頭の学習データに、実験の材料と区分の列を足したもの。build_experiments.py で作る）。
EXPERIMENT_TABLES: tuple[ModelTableSpec, ...] = (
    ModelTableSpec("form_experiments", "全頭の予想（材料を足す実験）", _not_built_from_the_database,
                   FeatureCatalog(FORM_CATALOG.features + experiment_features())),
)


def spec_named(name: str) -> ModelTableSpec:
    """名前から ``ModelTableSpec`` を引く（実験の表も）。知らなければ ``ValueError``。"""
    for spec in (*MODEL_TABLES, *EXPERIMENT_TABLES):
        if spec.name == name:
            return spec
    names = " / ".join(spec.name for spec in (*MODEL_TABLES, *EXPERIMENT_TABLES))
    raise ValueError(f"知らない予想です: {name}（{names}）")
