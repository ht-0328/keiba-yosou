"""重賞に特化した予想の確かめで比べる作り方（重賞の予想の設計書 16 の 4 の「並べる行」）。当日の時点。"""

from __future__ import annotations

from yosou.shared.dataset import TOP3, WIN
from yosou.shared.feature import FINISH_POWER_NAMES, PredictionTiming
from yosou.development_score import DEVELOPMENT_SCORE_NAMES
from yosou.shared.feature.form_aptitude_catalog import ABILITY_CATALOG, RACE_DAY_CATALOG

from .day_bias_features import D_NAMES
from .graded_features import W_NAMES
from .graded_table_builder import K_NAMES
from .graded_variant import GradedVariant

_RACE_DAY, _DAY_BEFORE = PredictionTiming.RACE_DAY, PredictionTiming.DAY_BEFORE
#: 元の表（研究「既存モデルの改善」の tables/）。3着以内は今の本番の当日の3着以内の表、1着は勝ち切る材料 Q 入りの表。
TOP3_TABLE, WIN_TABLE = "dscore_race_day", "dscore_finish_race_day"
#: 前日の表（2012年から。今の本番の前日の3着以内と1着の列を全部持つ）。当日の表より前の年まで区切りを延ばして、形をまだ見ていない年で確かめるのに使う。
DAY_BEFORE_TABLE = "dscore_day_before"
#: 今の本番と同じ列（material_check の CURRENT_PRODUCTION と同じ）。
_TOP3_COLUMNS = RACE_DAY_CATALOG.columns_for(_RACE_DAY)
_WIN_COLUMNS = _TOP3_COLUMNS + FINISH_POWER_NAMES
#: オッズだけの基準に使う列（重賞の作り直しの確かめと同じ）。
_ODDS_ONLY = ("単勝オッズ", "人気順位", "オッズから見た勝率", "オッズから見た3着以内率", "出走頭数")
#: 予測を保存する表の名前（predictions/<名前>/）。
PREDICTION_TABLE = "graded_race_day"


def _pair(key: str, name: str, extra: tuple[str, ...], weight: float, odds_only: bool = False) -> tuple[GradedVariant, ...]:
    """3着以内と1着の2つの作り方。"""
    top3 = _ODDS_ONLY if odds_only else _TOP3_COLUMNS + extra
    win = _ODDS_ONLY if odds_only else _WIN_COLUMNS + extra
    return (
        GradedVariant(TOP3_TABLE, f"{key}-top3", f"{name}（3着以内）", top3, True, label=TOP3, graded_weight=weight),
        GradedVariant(WIN_TABLE, f"{key}-win", f"{name}（1着）", win, True, label=WIN, graded_weight=weight),
    )


#: 並べる行。回す順（本番の形と比べる相手を先に）。
GRADED_VARIANTS: tuple[GradedVariant, ...] = (
    *_pair("graded", "この予想（重み 5・W・K）", W_NAMES + K_NAMES, 5.0),
    *_pair("general", "手本を重賞だけに使ったとき", (), 1.0),
    *_pair("weight1", "重み 1（W・K は足す）", W_NAMES + K_NAMES, 1.0),
    *_pair("weight10", "重み 10（W・K）", W_NAMES + K_NAMES, 10.0),
    *_pair("without_k", "K を外す（重み 5・W）", W_NAMES, 5.0),
    *_pair("without_w", "W を外す（重み 5・K）", K_NAMES, 5.0),
    *_pair("odds_only", "オッズだけ", (), 1.0, odds_only=True),
    *_pair("daybias", "その日の馬場を足す（D）", D_NAMES, 1.0),
)


#: 前日の今の本番と同じ作り（重みなし・W と K なし）。研究「重賞の買い方」5回目の、まだ見ていない年（2015〜2019年）での形の確かめに使う。
DAY_BEFORE_VARIANTS: tuple[GradedVariant, ...] = (
    GradedVariant(DAY_BEFORE_TABLE, "dayb-top3", "今の本番の前日（3着以内）", ABILITY_CATALOG.columns_for(_DAY_BEFORE) + DEVELOPMENT_SCORE_NAMES,
                  True, timing=_DAY_BEFORE, label=TOP3),
    GradedVariant(DAY_BEFORE_TABLE, "dayb-win", "今の本番の前日（1着）", ABILITY_CATALOG.columns_for(_DAY_BEFORE), True,
                  timing=_DAY_BEFORE, label=WIN),
)


def graded_variant_keyed(key: str) -> GradedVariant:
    for variant in (*GRADED_VARIANTS, *DAY_BEFORE_VARIANTS):
        if variant.key == key:
            return variant
    raise ValueError(f"知らない作り方です: {key}（{' / '.join(variant.key for variant in GRADED_VARIANTS)}）")
