"""今の本番のモデル（時点 × 目的変数ごと）の列と、7つの区切りで学んだ予測の置き場所。材料を足す確かめの「比べる相手」。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.ability_score import ABILITY_SCORE_NAMES
from yosou.development_score import DEVELOPMENT_SCORE_NAMES
from yosou.form_aptitude_top3.feature import ABILITY_CATALOG, RACE_DAY_CATALOG
from yosou.shared.dataset import TOP3, WIN
from yosou.shared.feature import FINISH_POWER_NAMES, PredictionTiming

from ..pace_forecast import PACE_NAMES

#: 元の表と今の本番の予測の置き場所（研究の名前）。当日の1着のモデルの表（勝ち切る材料 Q 入り）は、研究「回収率100超の施策」が作ったもの。
THIS_RESEARCH = "既存モデルの改善"
PAYBACK_RESEARCH = "回収率100超の施策"


@dataclass(frozen=True)
class CurrentProduction:
    """今の本番のモデル1つ（``timing`` の時点の、``label`` の目的変数のモデル）。

    ``columns`` は今の本番と同じ列、``research``・``table``・``key`` はそのモデルを7つの区切りで学んだ予測（``reports/<research>/predictions/<table>/<key>.pkl``）。
    ``base_table`` は、材料を足す元にする表（この研究の ``tables/``。今の本番の列を全部持つ表）。
    """

    timing: PredictionTiming
    label: str
    columns: tuple[str, ...]
    research: str
    table: str
    key: str
    base_table: str

    @property
    def target(self) -> str:
        return "3着以内" if self.label == TOP3 else "1着"

    @property
    def uses_baseline(self) -> bool:
        """オッズから作った基準を出発点にして学ぶか（オッズの無い木曜は基準なし）。"""
        return self.timing is not PredictionTiming.THURSDAY


_THURSDAY, _DAY_BEFORE, _RACE_DAY = PredictionTiming.THURSDAY, PredictionTiming.DAY_BEFORE, PredictionTiming.RACE_DAY
_THURSDAY_COLUMNS = ABILITY_CATALOG.columns_for(_THURSDAY) + PACE_NAMES + ABILITY_SCORE_NAMES
_DAY_BEFORE_COLUMNS = ABILITY_CATALOG.columns_for(_DAY_BEFORE)
_RACE_DAY_COLUMNS = RACE_DAY_CATALOG.columns_for(_RACE_DAY)

#: 今の本番の6つのモデル（設計書「近走と適性から3着以内を予想」07 の表）。木曜は M・O・J・P・T（入口⑭の能力スコアの予測）、前日の3着以内は M・O・J・S
#: （入口⑬の予測）、前日の1着は M・O・J（入口⑪の予測）、当日の3着以内は A〜L・N・M（入口⑧の予測）、当日の1着はそれに Q（研究「回収率100超の施策」の予測）。
#: 元の表は入口⑬が作った表（P と S の列を持つ。当日の1着は Q も）に、入口⑭の ``tables`` が T を付けたもの。
#: **材料を本番に足したら、ここも直す**（列に足し、予測をその材料の確かめのものにする）。
CURRENT_PRODUCTION: tuple[CurrentProduction, ...] = (
    CurrentProduction(_DAY_BEFORE, TOP3, _DAY_BEFORE_COLUMNS + DEVELOPMENT_SCORE_NAMES, THIS_RESEARCH, "dscore_day_before", "dscore-day_before", "dscore_day_before"),
    CurrentProduction(_RACE_DAY, TOP3, _RACE_DAY_COLUMNS, THIS_RESEARCH, "h2h_pool_ability", "current-race_day", "dscore_race_day"),
    CurrentProduction(_THURSDAY, TOP3, _THURSDAY_COLUMNS, THIS_RESEARCH, "ascore_thursday", "ascore-thursday", "dscore_thursday"),
    CurrentProduction(_DAY_BEFORE, WIN, _DAY_BEFORE_COLUMNS, THIS_RESEARCH, "h2h_ability", "win-day_before", "dscore_day_before"),
    CurrentProduction(_RACE_DAY, WIN, _RACE_DAY_COLUMNS + FINISH_POWER_NAMES, PAYBACK_RESEARCH, "finish_pool_ability", "finish-win-race_day", "dscore_finish_race_day"),
    CurrentProduction(_THURSDAY, WIN, _THURSDAY_COLUMNS, THIS_RESEARCH, "ascore_thursday", "ascore-win-thursday", "dscore_thursday"),
)


def current_production(timing: PredictionTiming, label: str) -> CurrentProduction:
    """時点と目的変数から引く。知らなければ ``ValueError``。"""
    for current in CURRENT_PRODUCTION:
        if current.timing is timing and current.label == label:
            return current
    raise ValueError(f"今の本番のモデルがありません: {timing.label}・{label}")
