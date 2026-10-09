"""距離の変更の傾向（まとまり R）を足す元の表と、足した表の名前。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.shared.feature import DISTANCE_CHANGE_FEATURES, FINISH_POWER_FEATURES, FeatureCatalog

from ..head_to_head import base_table_rated
from ..pace_forecast import pace_table_named

#: 元の表の置き場所（研究の名前）。今の本番の当日の1着のモデルの表は、研究「回収率100超の施策」が作ったもの。
THIS_RESEARCH = "既存モデルの改善"
PAYBACK_RESEARCH = "回収率100超の施策"


@dataclass(frozen=True)
class DistanceTable:
    """R を足した表1つ。``base`` は元の表（今の本番と同じ材料の表）の名前、``base_research`` はその置き場所の研究、
    ``base_catalog`` はその特徴量の一覧。"""

    name: str
    label: str
    base: str
    base_research: str
    base_catalog: FeatureCatalog

    @property
    def catalog(self) -> FeatureCatalog:
        """R の 7個を足した特徴量の一覧。"""
        return FeatureCatalog(self.base_catalog.features + DISTANCE_CHANGE_FEATURES)


#: 元の表は、今の本番のモデルを7つの区切りで学んだときの表。木曜は展開の予想（P）を足した表、前日は対戦レーティング（O）を足した表、
#: 当日は今の材料の表（3着以内のモデル）と、それに勝ち切る材料（Q）を足した表（1着のモデル）。
DISTANCE_TABLES: tuple[DistanceTable, ...] = (
    DistanceTable("dist_thursday", "展開の予想を足した表 ＋ 距離の変更の傾向（木曜）", "pace_thursday", THIS_RESEARCH,
                  pace_table_named("pace_thursday").catalog),
    DistanceTable("dist_ability", "対戦レーティングを足した表 ＋ 距離の変更の傾向（前日）", "h2h_ability", THIS_RESEARCH,
                  base_table_rated("h2h_ability").rated_catalog),
    DistanceTable("dist_pool_ability", "今の当日の表 ＋ 距離の変更の傾向（当日の3着以内）", "h2h_pool_ability", THIS_RESEARCH,
                  base_table_rated("h2h_pool_ability").rated_catalog),
    DistanceTable("dist_finish_pool_ability", "勝ち切る材料を足した当日の表 ＋ 距離の変更の傾向（当日の1着）", "finish_pool_ability",
                  PAYBACK_RESEARCH, FeatureCatalog(base_table_rated("h2h_pool_ability").rated_catalog.features + FINISH_POWER_FEATURES)),
)


def distance_table_named(name: str) -> DistanceTable:
    """名前から引く。知らなければ ``ValueError``。"""
    for table in DISTANCE_TABLES:
        if table.name == name:
            return table
    raise ValueError(f"知らない表です: {name}（{' / '.join(table.name for table in DISTANCE_TABLES)}）")
