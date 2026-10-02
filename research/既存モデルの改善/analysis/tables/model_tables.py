"""4つの予想の学習データの作り方と、作る期間（と、読むだけの重賞の直す前の表・材料の実験の表）。"""

from __future__ import annotations

from datetime import date

from yosou.favorites_out_of_top3.dataset import dataset_builder as favorites_builder
from yosou.favorites_out_of_top3.feature import CATALOG as FAVORITES_CATALOG
from yosou.form_aptitude_top3.dataset import dataset_builder as form_builder
from yosou.form_aptitude_top3.feature import CATALOG as FORM_CATALOG
from yosou.longshots_in_top3.dataset import dataset_builder as longshots_builder
from yosou.longshots_in_top3.feature import CATALOG as LONGSHOTS_CATALOG
from yosou.shared.dataset import TrainingPeriod
from yosou.shared.feature import BASE_FEATURES, MARKET_FEATURES, FeatureCatalog
from yosou.stakes_tendency_top3.feature import K_FEATURES as STAKES_TENDENCY_FEATURES
from yosou.upset_level.dataset import UpsetLevel, race_dataset_builder
from yosou.upset_level.feature import CATALOG as UPSET_CATALOG

from ..experiments.experiment_table_builder import experiment_features
from .model_table_spec import ModelTableSpec

#: 学習データを作る期間。ウォームアップは 2016年（DB にある最初の年）、サンプルは 2017年1月から。
#: 使うのはウォームアップと学習の始まりだけで、検証・テストの始まりは期間の後のダミー（区切りは検証の側で決める）。
TABLE_PERIOD = TrainingPeriod(date(2016, 1, 1), date(2017, 1, 1), date(2027, 1, 1), date(2027, 1, 2))
#: 重賞の予想の学習データを作る期間。重賞は1年に約125レースしかないので、予想の設計（設計書 08 の 4）と同じく、
#: ウォームアップは 2011年（特別競走番号でレースを同定できると確かめた最初の年）、サンプルは 2012年1月から。
STAKES_TABLE_PERIOD = TrainingPeriod(date(2011, 1, 1), date(2012, 1, 1), date(2027, 1, 1), date(2027, 1, 2))
#: 荒れ具合の予想の学習データを作る期間。予想の学習の既定（2026-09-30 に 2017年から延ばした。荒れ具合の設計書 15 の 5）と同じく、
#: ウォームアップは 2011年、サンプルは 2012年1月から。
UPSET_TABLE_PERIOD = TrainingPeriod(date(2011, 1, 1), date(2012, 1, 1), date(2027, 1, 1), date(2027, 1, 2))

MODEL_TABLES: tuple[ModelTableSpec, ...] = (
    ModelTableSpec("form_aptitude_top3", "近走と適性から3着以内を予想（全頭）", form_builder, FORM_CATALOG),
    ModelTableSpec("longshots_in_top3", "穴馬が3着以内に入るかを予想", longshots_builder, LONGSHOTS_CATALOG),
    ModelTableSpec("favorites_out_of_top3", "人気馬が4着以下になるかを予想", favorites_builder, FAVORITES_CATALOG),
    ModelTableSpec("upset_level", "レースの荒れ具合を4段階で予想", race_dataset_builder, UPSET_CATALOG,
                   UpsetLevel.class_labels(), period=UPSET_TABLE_PERIOD),
)


def _not_built_from_the_database(con):
    raise ValueError("form_experiments は build_experiments.py で作る（build_tables.py では作らない）")


def _stakes_before_the_rebuild(con):
    raise ValueError("重賞の直す前の作り方（85個）の表は、作り直したあとは作れない。"
                     "作り直した表は stakes_rebuild.py tables で作る（stakes_ability・stakes_race_day）")


#: 材料の実験の表（全頭の学習データに、実験の材料と区分の列を足したもの。build_experiments.py で作る）。
EXPERIMENT_TABLES: tuple[ModelTableSpec, ...] = (
    ModelTableSpec("form_experiments", "全頭の予想（材料を足す実験）", _not_built_from_the_database,
                   FeatureCatalog(FORM_CATALOG.features + experiment_features())),
)
#: 重賞の予想の、直す前の作り方（A〜J の 75個に K の10個を足した 85個。2026-09-30 に作った表）。予想のパッケージは
#: 2026-10-02 に手本の新しい材料で作り直したので、この表は作り直せない（保存してある表を比べ方の表に読むためだけに残す）。
#: 作り直した表と作り方は ``analysis/stakes_rebuild/``。
STAKES_BEFORE_REBUILD_TABLES: tuple[ModelTableSpec, ...] = (
    ModelTableSpec("stakes_tendency_top3", "重賞の傾向と近走から3着以内を予想（直す前の作り方）", _stakes_before_the_rebuild,
                   FeatureCatalog(BASE_FEATURES + MARKET_FEATURES + STAKES_TENDENCY_FEATURES), period=STAKES_TABLE_PERIOD),
)


def spec_named(name: str) -> ModelTableSpec:
    """名前から ``ModelTableSpec`` を引く（実験の表・重賞の直す前の表も）。知らなければ ``ValueError``。"""
    known = (*MODEL_TABLES, *EXPERIMENT_TABLES, *STAKES_BEFORE_REBUILD_TABLES)
    for spec in known:
        if spec.name == name:
            return spec
    names = " / ".join(spec.name for spec in known)
    raise ValueError(f"知らない予想です: {name}（{names}）")
