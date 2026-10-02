"""この予想の7つの予想（と比べる基準）を表す値。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from yosou.shared.dataset import BINARY_LABELS
from yosou.shared.feature import FeatureCatalog, PredictionTiming

from ..dataset import label_names as names
from ..feature import (
    BACK_PROBABILITY,
    CLOSING_PREDICTION,
    CORNER4_PREDICTION,
    EARLY_HORSE_CATALOG,
    EARLY_RACE_CATALOG,
    EVEN_PROBABILITY,
    FINISH_CATALOG,
    FINISH_NO_EARLY_CATALOG,
    FINISH_NO_LATE_CATALOG,
    FINISH_PLAIN_CATALOG,
    FINISH_WITH_ODDS_CATALOG,
    FIRST_HALF_QUANTILES,
    FRONT_PROBABILITY,
    HIGH_PROBABILITY,
    LATE_HORSE_CATALOG,
    LATE_RACE_CATALOG,
    LEADER_PROBABILITY,
    MIDDLE_PROBABILITY,
    NO_EARLY_WIN_PROBABILITY,
    NO_LATE_WIN_PROBABILITY,
    ODDS_WIN_PROBABILITY,
    PLAIN_WIN_PROBABILITY,
    SECOND_HALF_QUANTILES,
    SLOW_PROBABILITY,
    WIN_PROBABILITY,
)
from .model_family import ModelFamily


@dataclass(frozen=True)
class KindSpec:
    """1つの予想の決めごと。

    - ``label``: 学習データの目的変数の列（``with_label`` で持ち替える）。
    - ``per_race``: 1行 = 1レースの予想か（False なら 1行 = 1頭）。
    - ``family``: モデルの種類。
    - ``catalog``: 使う特徴量の一覧（前の組の予測 S・T を含む）。
    - ``outputs``: 予測の列の名前（後の組の特徴量と、年ごとの確かめの元）。
    - ``class_labels``: 目的変数の値の並び（回帰と分位点回帰は使わないが、二値の並びを置いておく）。
    - ``label_text``: 表に出す名前。
    - ``for_prediction``: 予測に使うか（学習（train）で保存し、予測（predict）で読むか）。偽なら、年ごとの確かめで
      比べるためだけに学習する予想。
    - ``known_from``: この時点から学習する（オッズを足した ⑦ は、確定オッズの分かる当日だけ）。
    """

    label: str
    per_race: bool
    family: ModelFamily
    catalog: FeatureCatalog
    outputs: tuple[str, ...]
    class_labels: tuple[int, ...]
    label_text: str
    for_prediction: bool = True
    known_from: PredictionTiming = PredictionTiming.THURSDAY


class DevelopmentModelKind(Enum):
    """7つの予想と、⑦ の比べるためだけの予想（設計書 04 の「workflow/」・16 の 3）。

    比べるためだけの予想は、前半・後半の予想を入れない着順のモデル（``FINISH_PLAIN``）、⑦ から S を外したもの
    （``FINISH_NO_EARLY``）・T を外したもの（``FINISH_NO_LATE``）、⑦ にオッズを足したもの（``FINISH_WITH_ODDS``）。
    どれも年ごとの確かめでだけ学習し、保存も予測もしない（``KindSpec.for_prediction`` が偽）。

    値は、学習したモデルを保存するフォルダの名前と、``--kind`` の書き方になる。
    """

    LEADER = "leader"
    POSITION = "position"
    PACE_CLASS = "pace_class"
    PACE_TIME = "pace_time"
    CORNER4 = "corner4"
    CLOSING = "closing"
    LATE_PACE_TIME = "late_pace_time"
    FINISH = "finish"
    FINISH_PLAIN = "finish_plain"
    FINISH_NO_EARLY = "finish_no_early"
    FINISH_NO_LATE = "finish_no_late"
    FINISH_WITH_ODDS = "finish_with_odds"

    @property
    def spec(self) -> KindSpec:
        return _SPECS[self]

    @property
    def folder(self) -> str:
        return self.value

    @classmethod
    def parse(cls, text: str) -> DevelopmentModelKind:
        """``leader`` のような書き方から予想を返す。知らなければ ``ValueError``。"""
        for kind in cls:
            if kind.value == text.strip():
                return kind
        raise ValueError(f"知らない予想です: {text}（{' / '.join(kind.value for kind in cls)}）")


_THREE = names.THREE_CLASSES
_SPECS: dict[DevelopmentModelKind, KindSpec] = {
    DevelopmentModelKind.LEADER: KindSpec(
        names.LEADER, False, ModelFamily.WITHIN_RACE, EARLY_HORSE_CATALOG, (LEADER_PROBABILITY,), BINARY_LABELS,
        "① 先頭の馬"),
    DevelopmentModelKind.POSITION: KindSpec(
        names.EARLY_ZONE, False, ModelFamily.MULTICLASS, EARLY_HORSE_CATALOG,
        (FRONT_PROBABILITY, MIDDLE_PROBABILITY, BACK_PROBABILITY), _THREE, "② 序盤の位置"),
    DevelopmentModelKind.PACE_CLASS: KindSpec(
        names.PACE_CLASS, True, ModelFamily.MULTICLASS, EARLY_RACE_CATALOG,
        (SLOW_PROBABILITY, EVEN_PROBABILITY, HIGH_PROBABILITY), _THREE, "③ ペースの区分"),
    DevelopmentModelKind.PACE_TIME: KindSpec(
        names.FIRST_HALF_DIFF, True, ModelFamily.QUANTILE, EARLY_RACE_CATALOG, FIRST_HALF_QUANTILES, BINARY_LABELS,
        "③ 前半タイム"),
    DevelopmentModelKind.CORNER4: KindSpec(
        names.CORNER4_POSITION, False, ModelFamily.REGRESSION, LATE_HORSE_CATALOG, (CORNER4_PREDICTION,),
        BINARY_LABELS, "④ 4コーナーの位置"),
    DevelopmentModelKind.CLOSING: KindSpec(
        names.CLOSING_SPEED, False, ModelFamily.REGRESSION, LATE_HORSE_CATALOG, (CLOSING_PREDICTION,),
        BINARY_LABELS, "⑤ 上がりの速さ"),
    DevelopmentModelKind.LATE_PACE_TIME: KindSpec(
        names.SECOND_HALF_DIFF, True, ModelFamily.QUANTILE, LATE_RACE_CATALOG, SECOND_HALF_QUANTILES, BINARY_LABELS,
        "⑥ 後半タイム"),
    DevelopmentModelKind.FINISH: KindSpec(
        names.WINNER, False, ModelFamily.WITHIN_RACE, FINISH_CATALOG, (WIN_PROBABILITY,), BINARY_LABELS, "⑦ 着順"),
    DevelopmentModelKind.FINISH_PLAIN: KindSpec(
        names.WINNER, False, ModelFamily.WITHIN_RACE, FINISH_PLAIN_CATALOG, (PLAIN_WIN_PROBABILITY,), BINARY_LABELS,
        "⑦ の比べる基準（前半・後半を入れない）", for_prediction=False),
    DevelopmentModelKind.FINISH_NO_EARLY: KindSpec(
        names.WINNER, False, ModelFamily.WITHIN_RACE, FINISH_NO_EARLY_CATALOG, (NO_EARLY_WIN_PROBABILITY,), BINARY_LABELS,
        "⑦ から S を外したもの", for_prediction=False),
    DevelopmentModelKind.FINISH_NO_LATE: KindSpec(
        names.WINNER, False, ModelFamily.WITHIN_RACE, FINISH_NO_LATE_CATALOG, (NO_LATE_WIN_PROBABILITY,), BINARY_LABELS,
        "⑦ から T を外したもの", for_prediction=False),
    DevelopmentModelKind.FINISH_WITH_ODDS: KindSpec(
        names.WINNER, False, ModelFamily.WITHIN_RACE, FINISH_WITH_ODDS_CATALOG, (ODDS_WIN_PROBABILITY,), BINARY_LABELS,
        "⑦ にオッズを足したもの", for_prediction=False, known_from=PredictionTiming.RACE_DAY),
}
