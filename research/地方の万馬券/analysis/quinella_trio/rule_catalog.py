"""試す買い方の一覧（結果を見る前に決める。段ごとに候補を足し、偶然 100% を超えたものを採らないよう候補の数も記録する）。"""

from __future__ import annotations

from itertools import product

from 地方の推奨買目.position_model import EV, PROBABILITY

from .rule import TOP_FORM, QuinellaTrioRule

#: 荒れ具合の予測の列（段④）。
MID_OR_MORE, BIG_OR_MORE = "中荒れ以上の確率", "大荒れ以上の確率"

#: 段1: オッズの帯 × 期待値の線 × 頭数 × 点数の上限。
_BANDS: dict[str, tuple[tuple[float, float], ...]] = {
    "馬連": ((0.0, 20.0), (0.0, 30.0), (0.0, 50.0), (10.0, 50.0)),
    "3連複": ((20.0, 300.0), (0.0, 30.0), (10.0, 100.0), (30.0, 300.0)),
}
_EV_LINES: tuple[float, ...] = (1.0, 1.05, 1.1)
_HEADS: tuple[int, ...] = (8, 11)
_TOP_KS: dict[str, tuple[int, ...]] = {"馬連": (0, 1, 2, 3), "3連複": (0, 2, 3, 5)}
#: 段2: 組の形（◎ を含む、人気の帯の型）。段1 で最も良かった帯と線に重ねる。
_FORMS: dict[str, tuple[str, ...]] = {
    "馬連": (TOP_FORM, "人人", "人中", "人大", "中中", "人中|人大", "人中|中中"),
    "3連複": (TOP_FORM, "人人中", "人中中", "人中大", "人人大", "中中大", "人中中|人中大", "人人中|人中中", "人中大|中中大"),
}
#: 段3: 荒れ具合の条件（中荒れ以上・大荒れ以上の確率の線、固いレースだけ）。
_UPSETS: tuple[tuple[str, float, float], ...] = (
    (MID_OR_MORE, 0.4, float("inf")), (MID_OR_MORE, 0.5, float("inf")), (MID_OR_MORE, 0.6, float("inf")),
    (BIG_OR_MORE, 0.1, float("inf")), (BIG_OR_MORE, 0.15, float("inf")), (BIG_OR_MORE, 0.2, float("inf")),
    (MID_OR_MORE, 0.0, 0.4), (MID_OR_MORE, 0.0, 0.5),
)


def stage1(ticket: str) -> list[QuinellaTrioRule]:
    return [QuinellaTrioRule(ticket, ev, lo, hi, heads, top_k, PROBABILITY)
            for (lo, hi), ev, heads, top_k in product(_BANDS[ticket], _EV_LINES, _HEADS, _TOP_KS[ticket])]


def stage1_by_ev(ticket: str) -> list[QuinellaTrioRule]:
    """点数の上限を期待値の高い順にしたもの（確率の順と比べる）。"""
    return [QuinellaTrioRule(ticket, ev, lo, hi, heads, top_k, EV)
            for (lo, hi), ev, heads, top_k in product(_BANDS[ticket], _EV_LINES, _HEADS, _TOP_KS[ticket]) if top_k]


def stage2(base: QuinellaTrioRule) -> list[QuinellaTrioRule]:
    """``base``（段1 で選んだ買い方）に組の形を重ねる。"""
    return [QuinellaTrioRule(base.ticket, base.ev_min, base.odds_min, base.odds_max, base.min_heads, base.top_k, base.order, form)
            for form in _FORMS[base.ticket]]


def stage3(base: QuinellaTrioRule) -> list[QuinellaTrioRule]:
    """``base`` に荒れ具合の条件を重ねる。"""
    return [QuinellaTrioRule(base.ticket, base.ev_min, base.odds_min, base.odds_max, base.min_heads, base.top_k, base.order, base.form,
                             column, low, high) for column, low, high in _UPSETS]
