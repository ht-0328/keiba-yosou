"""展開の予想の結果（まとまり P）を足す元の表と、足した表。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.form_aptitude_top3.feature import ABILITY_CATALOG, RACE_DAY_CATALOG
from yosou.shared.feature import HEAD_TO_HEAD_FEATURES, PACE_FORECAST_FEATURES, FeatureCatalog, PredictionTiming


@dataclass(frozen=True)
class PaceTable:
    """P を足した表1つ。``base`` は元の表（今の本番と同じ材料の表）の名前、``base_catalog`` はその特徴量の一覧、
    ``timing`` は P の元にする展開の予測の時点。"""

    name: str
    label: str
    base: str
    base_catalog: FeatureCatalog
    timing: PredictionTiming

    @property
    def catalog(self) -> FeatureCatalog:
        """P の 20個を足した特徴量の一覧。"""
        return FeatureCatalog(self.base_catalog.features + PACE_FORECAST_FEATURES)


#: 当日の元の表の一覧（今の当日の一覧に、対戦レーティングの確かめで足した O の7列。当日のモデルは O を使わない）。
_RACE_DAY_BASE_CATALOG = FeatureCatalog(RACE_DAY_CATALOG.features + HEAD_TO_HEAD_FEATURES)

#: 元の表は、対戦レーティングの確かめ（入口⑧ ``h2h_check.py``）が作った、今の本番と同じ材料の表。木曜・前日は
#: 馬の力の材料と対戦レーティングと市場の評価（2012年から）、当日は今の材料と券種の支持と馬の力の材料（2017年から）。
#: P は時点ごとに、その時点の展開のモデルの予測から作るので、表も時点ごとに作る。
PACE_TABLES: tuple[PaceTable, ...] = (
    PaceTable("pace_thursday", "今の予想の表 ＋ 展開の予想（木曜）", "h2h_ability", ABILITY_CATALOG, PredictionTiming.THURSDAY),
    PaceTable("pace_day_before", "今の予想の表 ＋ 展開の予想（前日）", "h2h_ability", ABILITY_CATALOG, PredictionTiming.DAY_BEFORE),
    PaceTable("pace_race_day", "今の予想の表 ＋ 展開の予想（当日）", "h2h_pool_ability", _RACE_DAY_BASE_CATALOG,
              PredictionTiming.RACE_DAY),
)


def pace_table_named(name: str) -> PaceTable:
    """名前から引く。知らなければ ``ValueError``。"""
    for table in PACE_TABLES:
        if table.name == name:
            return table
    raise ValueError(f"知らない表です: {name}（{' / '.join(table.name for table in PACE_TABLES)}）")
