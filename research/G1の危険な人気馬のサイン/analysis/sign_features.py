"""サインの材料とサインを、学習データの特徴量にするときの一覧。"""

from __future__ import annotations

from yosou.shared.feature import Feature, FeatureKind, PredictionTiming

from .sign_columns import COURSE_GATE_EDGE, MATERIAL_COLUMNS, MEETING_GATE_EDGE, SIGN_COLUMNS, SIGN_COUNT, TOP_FAVORITE_ODDS

#: 特徴量のまとまりの名前（設計書 09 のまとまりの文字の代わり）。
SIGN_GROUP = "危険サイン"
#: 前日（出馬表とオッズ）から分かる列。ほかは木曜から分かる。
_DAY_BEFORE_COLUMNS: tuple[str, ...] = (
    MEETING_GATE_EDGE, COURSE_GATE_EDGE, TOP_FAVORITE_ODDS, "サイン2 馬場・枠の不利", "サイン10 断然人気の陰の2・3番人気",
    SIGN_COUNT,
)


def _feature(name: str) -> Feature:
    known_from = PredictionTiming.DAY_BEFORE if name in _DAY_BEFORE_COLUMNS else PredictionTiming.THURSDAY
    return Feature(name, SIGN_GROUP, FeatureKind.NUMERIC, known_from)


#: サインの材料（19個）・サイン（10個）・サインの数（1個）の30個。
SIGN_FEATURES: tuple[Feature, ...] = tuple(_feature(name) for name in (*MATERIAL_COLUMNS, *SIGN_COLUMNS, SIGN_COUNT))
