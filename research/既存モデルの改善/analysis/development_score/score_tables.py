"""展開スコア（まとまり S）を足す元の表と、足した表の名前。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.development_score import DEVELOPMENT_SCORE_FEATURES
from yosou.shared.feature import FINISH_POWER_FEATURES, FeatureCatalog, PredictionTiming

from ..head_to_head import base_table_rated
from ..pace_forecast import pace_table_named

#: 元の表の置き場所（研究の名前）。今の本番の当日の1着のモデルの表（勝ち切る材料 Q 入り）は、研究「回収率100超の施策」が作ったもの。
THIS_RESEARCH = "既存モデルの改善"
PAYBACK_RESEARCH = "回収率100超の施策"


@dataclass(frozen=True)
class ScoreTable:
    """S を足した表1つ。``base`` は元の表の名前、``base_research`` はその置き場所の研究、``base_catalog`` はその特徴量の一覧、
    ``timing`` は S の元にする展開の予測の時点。``has_pace`` は元の表が P の列を持つか（持てば P の列から S を作り、
    持たなければ展開の年ごとの確かめの予測（``PaceForecastHistory``）から作る）。"""

    name: str
    label: str
    base: str
    base_research: str
    base_catalog: FeatureCatalog
    timing: PredictionTiming
    has_pace: bool = True

    @property
    def catalog(self) -> FeatureCatalog:
        """S の 5個を足した特徴量の一覧。"""
        return FeatureCatalog(self.base_catalog.features + DEVELOPMENT_SCORE_FEATURES)


def _pace_table(timing: PredictionTiming) -> ScoreTable:
    base = pace_table_named(f"pace_{timing.value}")
    return ScoreTable(f"dscore_{timing.value}", f"展開の予想を足した表 ＋ 展開スコア（{timing.label}）", base.name, THIS_RESEARCH, base.catalog, timing)


#: 元の表は、展開の予想の確かめ（入口⑩）が時点ごとに作った表（P の 20列を持つ。木曜・前日は 2012年から、当日は 2017年から）と、
#: 今の本番の当日の1着のモデルの表（研究「回収率100超の施策」の、勝ち切る材料 Q を足した当日の表。P は持たない）。
SCORE_TABLES: tuple[ScoreTable, ...] = (
    *(_pace_table(timing) for timing in PredictionTiming),
    ScoreTable("dscore_finish_race_day", "勝ち切る材料を足した当日の表 ＋ 展開スコア（当日の1着）", "finish_pool_ability", PAYBACK_RESEARCH,
               FeatureCatalog(base_table_rated("h2h_pool_ability").rated_catalog.features + FINISH_POWER_FEATURES),
               PredictionTiming.RACE_DAY, has_pace=False),
)


def score_table_named(name: str) -> ScoreTable:
    """名前から引く。知らなければ ``ValueError``。"""
    for table in SCORE_TABLES:
        if table.name == name:
            return table
    raise ValueError(f"知らない表です: {name}（{' / '.join(table.name for table in SCORE_TABLES)}）")
