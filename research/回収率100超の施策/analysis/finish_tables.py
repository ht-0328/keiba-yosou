"""勝ち切る材料を足す元の表と、足した表の名前。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.shared.feature import FeatureCatalog, PredictionTiming

from 既存モデルの改善.analysis.head_to_head import base_table_rated

from .finish_columns import FINISH_FEATURES


@dataclass(frozen=True)
class FinishTable:
    """勝ち切る材料を足した表1つ。``base`` は元の表（今の本番と同じ材料の表。研究「既存モデルの改善」の ``tables/``）の名前。"""

    name: str
    label: str
    base: str
    base_catalog: FeatureCatalog
    timing: PredictionTiming

    @property
    def catalog(self) -> FeatureCatalog:
        """勝ち切る材料の 10個を足した特徴量の一覧。"""
        return FeatureCatalog(self.base_catalog.features + FINISH_FEATURES)


#: 前日のモデルの表（馬の力の材料 ＋ 対戦レーティング ＋ 市場の評価）と、当日のモデルの表（今の材料 ＋ 券種の支持 ＋ 馬の力 ＋ 対戦レーティング）。
#: どちらも研究「既存モデルの改善」の対戦レーティングの確かめ（``h2h_check.py tables``）が作ったもの。
FINISH_TABLES: tuple[FinishTable, ...] = (
    FinishTable("finish_ability", "馬の力の材料 ＋ 対戦レーティング ＋ 勝ち切る材料（前日）", "h2h_ability",
                base_table_rated("h2h_ability").rated_catalog, PredictionTiming.DAY_BEFORE),
    FinishTable("finish_pool_ability", "今の材料 ＋ 券種の支持 ＋ 馬の力の材料 ＋ 対戦レーティング ＋ 勝ち切る材料（当日）", "h2h_pool_ability",
                base_table_rated("h2h_pool_ability").rated_catalog, PredictionTiming.RACE_DAY),
)


def finish_table_named(name: str) -> FinishTable:
    """名前から引く。知らなければ ``ValueError``。"""
    for table in FINISH_TABLES:
        if table.name == name:
            return table
    raise ValueError(f"知らない表です: {name}（{' / '.join(table.name for table in FINISH_TABLES)}）")
