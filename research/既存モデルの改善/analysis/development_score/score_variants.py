"""展開スコアの確かめで比べる作り方（時点と目的変数ごとに、今の予想と、展開スコアを足したもの）。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.development_score import DEVELOPMENT_SCORE_NAMES
from yosou.form_aptitude_top3.feature import ABILITY_CATALOG, RACE_DAY_CATALOG
from yosou.shared.dataset import TOP3, WIN
from yosou.shared.feature import FINISH_POWER_NAMES, PredictionTiming

from ..pace_forecast import PACE_NAMES
from ..variants import ModelVariant
from .score_tables import PAYBACK_RESEARCH, THIS_RESEARCH

_THURSDAY, _DAY_BEFORE, _RACE_DAY = PredictionTiming.THURSDAY, PredictionTiming.DAY_BEFORE, PredictionTiming.RACE_DAY


@dataclass(frozen=True)
class ScoreComparisonSpec:
    """1つの時点・1つの目的変数の比べ方。``current`` は今の予想（``current_research`` の ``current_table`` に保存した予測）、
    ``scored`` はそれに S を足した作り方、``label`` は目的変数（3着以内・1着）。

    列は今の本番と同じ（木曜は M・O・P、前日は M・O・J、当日は A〜L・N・M。当日の1着はそれに Q）に、S の 5個を足したもの。
    オッズの分かる前日・当日は、今の予想と同じく、オッズから作った基準を出発点にして学ぶ。
    """

    timing: PredictionTiming
    current: ModelVariant
    current_table: str
    scored: ModelVariant
    label: str = TOP3
    current_research: str = THIS_RESEARCH

    @property
    def key(self) -> str:
        return self.scored.key

    @property
    def target(self) -> str:
        return "3着以内" if self.label == TOP3 else "1着"


def _spec(timing: PredictionTiming, current_table: str, current_key: str, columns: tuple[str, ...], label: str = TOP3,
          scored_table: str | None = None, scored_key: str | None = None, current_research: str = THIS_RESEARCH) -> ScoreComparisonSpec:
    uses_baseline = timing is not _THURSDAY
    target = "3着以内" if label == TOP3 else "1着"
    prefix = "dscore" if label == TOP3 else "dscore-win"
    current = ModelVariant(current_table, current_key, f"今の予想（{target}・{timing.label}）", columns, uses_baseline=uses_baseline, timing=timing)
    scored = ModelVariant(scored_table or f"dscore_{timing.value}", scored_key or f"{prefix}-{timing.value}",
                          f"今の予想 ＋ 展開スコア（{target}・{timing.label}）", columns + DEVELOPMENT_SCORE_NAMES,
                          uses_baseline=uses_baseline, timing=timing)
    return ScoreComparisonSpec(timing, current, current_table, scored, label, current_research)


_THURSDAY_COLUMNS = ABILITY_CATALOG.columns_for(_THURSDAY) + PACE_NAMES
_DAY_BEFORE_COLUMNS = ABILITY_CATALOG.columns_for(_DAY_BEFORE)
_RACE_DAY_COLUMNS = RACE_DAY_CATALOG.columns_for(_RACE_DAY)

#: 時点ごと・目的変数ごとの比べ方。今の予想の予測は、木曜は展開の予想を足した作り方（入口⑩。本番）、前日は対戦レーティングを足した作り方（入口⑧。本番）、
#: 当日は今の作り方（入口⑧）。1着のモデルの今の予想は、木曜・前日は入口⑪の予測、当日は勝ち切る材料（Q）を足した本番の作り方
#: （研究「回収率100超の施策」の ``finish-win-race_day``）。前日が道具「印の成績」の既定なので先に回し、3着以内を先に、1着をあとに回す。
SCORE_COMPARISONS: tuple[ScoreComparisonSpec, ...] = (
    _spec(_DAY_BEFORE, "h2h_ability", "h2h-day_before", _DAY_BEFORE_COLUMNS),
    _spec(_RACE_DAY, "h2h_pool_ability", "current-race_day", _RACE_DAY_COLUMNS),
    _spec(_THURSDAY, "pace_thursday", "pace-thursday", _THURSDAY_COLUMNS),
    _spec(_DAY_BEFORE, "h2h_ability", "win-day_before", _DAY_BEFORE_COLUMNS, WIN),
    _spec(_RACE_DAY, "finish_pool_ability", "finish-win-race_day", _RACE_DAY_COLUMNS + FINISH_POWER_NAMES, WIN,
          scored_table="dscore_finish_race_day", scored_key="dscore-finish-win-race_day", current_research=PAYBACK_RESEARCH),
    _spec(_THURSDAY, "pace_thursday", "win-thursday", _THURSDAY_COLUMNS, WIN),
)
#: 回す作り方（S を足したものだけ。今の予想は学習済み）。
SCORE_VARIANTS: tuple[ScoreComparisonSpec, ...] = SCORE_COMPARISONS
