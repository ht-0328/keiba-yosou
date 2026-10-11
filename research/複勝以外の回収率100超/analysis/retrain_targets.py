"""前の年の区切りで学習し直すモデルの並び（印の成績に要る5つ）。"""

from __future__ import annotations

from yosou.favorites_out_of_top3.setting import DEFAULT_SETTINGS_PATH as FAVORITES_SETTINGS
from yosou.form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH as FORM_SETTINGS
from yosou.shared.dataset import WIN
from yosou.shared.feature import PredictionTiming

from 既存モデルの改善.analysis.development_score import score_table_named
from 既存モデルの改善.analysis.material_check.current_production import CURRENT_PRODUCTION, CurrentProduction
from 既存モデルの改善.analysis.tables import spec_named
from 既存モデルの改善.analysis.variants import ModelVariant, variant_named

from .retrain_target import RetrainTarget

#: 道具「印の成績」で印を付けるのに要る時点（オッズを使う前日と当日。木曜は期待度も複勝の期待値も付かないので確かめない）。
TIMINGS: tuple[PredictionTiming, ...] = (PredictionTiming.DAY_BEFORE, PredictionTiming.RACE_DAY)
#: 危険な人気馬の今の本番（道具「印の成績」の既定 ``favorites_out_of_top3/people_market``）。
_FAVORITES, _FAVORITES_KEY = "favorites_out_of_top3", "people_market"


def _production_target(current: CurrentProduction) -> RetrainTarget:
    """今の本番の全頭の予想1つ（研究「既存モデルの改善」の入口⑭が「今の予想」として持つ列と表）を、そのまま学び直す形にする。"""
    table = score_table_named(current.base_table)
    target = "win" if current.label == WIN else "top3"
    variant = ModelVariant(table.name, f"{target}-{current.timing.value}", f"今の本番（{current.target}・{current.timing.label}）",
                           current.columns, uses_baseline=current.uses_baseline, timing=current.timing)
    return RetrainTarget(f"{current.timing.label}・{current.target}", variant, table.catalog, current.label == WIN, FORM_SETTINGS,
                         f"{current.research}/{current.table}/{current.key}")


def _favorites_target() -> RetrainTarget:
    spec = spec_named(_FAVORITES)
    variant = variant_named(_FAVORITES, _FAVORITES_KEY)
    return RetrainTarget("危険な人気馬", variant, spec.catalog, False, FAVORITES_SETTINGS,
                         f"既存モデルの改善/{_FAVORITES}/{_FAVORITES_KEY}")


#: 前日・当日の 3着以内と1着（今の本番の4つ）と、危険な人気馬。
RETRAIN_TARGETS: tuple[RetrainTarget, ...] = (
    *(_production_target(current) for current in CURRENT_PRODUCTION if current.timing in TIMINGS),
    _favorites_target(),
)


def retrain_target_named(label: str) -> RetrainTarget:
    """表に出す名前から引く。知らなければ ``ValueError``。"""
    for target in RETRAIN_TARGETS:
        if target.label == label:
            return target
    raise ValueError(f"知らないモデルです: {label}（{' / '.join(target.label for target in RETRAIN_TARGETS)}）")
