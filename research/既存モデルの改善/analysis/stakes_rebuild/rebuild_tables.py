"""重賞の予想の作り直しの確かめに使う、学習データの表。"""

from __future__ import annotations

from yosou.form_aptitude_top3.dataset import ability_dataset_builder as form_ability_builder
from yosou.form_aptitude_top3.dataset import race_day_dataset_builder as form_race_day_builder
from yosou.form_aptitude_top3.feature import ABILITY_CATALOG as FORM_ABILITY_CATALOG
from yosou.form_aptitude_top3.feature import RACE_DAY_CATALOG as FORM_RACE_DAY_CATALOG
from yosou.stakes_tendency_top3.dataset import ability_dataset_builder as stakes_ability_builder
from yosou.stakes_tendency_top3.dataset import race_day_dataset_builder as stakes_race_day_builder
from yosou.stakes_tendency_top3.feature import ABILITY_CATALOG as STAKES_ABILITY_CATALOG
from yosou.stakes_tendency_top3.feature import RACE_DAY_CATALOG as STAKES_RACE_DAY_CATALOG

from ..tables import STAKES_TABLE_PERIOD, ModelTableSpec

#: 表の名前。重賞だけの表（作り直した専用モデル）と、全レースの表（手本を重賞だけに使ったときの比べ先）。
STAKES_ABILITY, STAKES_RACE_DAY = "stakes_ability", "stakes_race_day"
FORM_ABILITY, FORM_RACE_DAY = "form_ability", "form_race_day"

#: 4つの表。どれも 2012年1月から（ウォームアップ 2011年。重賞の予想の設計と同じ期間で、手本の表も同じ期間にそろえる。
#: 券種ごとのオッズも 2011年からあることを確かめた）。学習データを作るのは予想のパッケージの組み立て関数そのもの。
REBUILD_TABLES: tuple[ModelTableSpec, ...] = (
    ModelTableSpec(STAKES_ABILITY, "重賞だけ: 馬の力の材料＋市場の評価＋重賞の傾向（木曜・前日）", stakes_ability_builder,
                   STAKES_ABILITY_CATALOG, period=STAKES_TABLE_PERIOD),
    ModelTableSpec(STAKES_RACE_DAY, "重賞だけ: 当日の材料＋重賞の傾向（当日）", stakes_race_day_builder,
                   STAKES_RACE_DAY_CATALOG, period=STAKES_TABLE_PERIOD),
    ModelTableSpec(FORM_ABILITY, "全レース: 手本の馬の力の材料＋市場の評価（木曜・前日）", form_ability_builder,
                   FORM_ABILITY_CATALOG, period=STAKES_TABLE_PERIOD),
    ModelTableSpec(FORM_RACE_DAY, "全レース: 手本の当日の材料（当日）", form_race_day_builder,
                   FORM_RACE_DAY_CATALOG, period=STAKES_TABLE_PERIOD),
)


def rebuild_table_named(name: str) -> ModelTableSpec:
    """名前から引く。知らなければ ``ValueError``。"""
    for table in REBUILD_TABLES:
        if table.name == name:
            return table
    raise ValueError(f"知らない表です: {name}（{' / '.join(table.name for table in REBUILD_TABLES)}）")
