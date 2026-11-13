"""展開の型で混ぜる着順の予想の作り方1つ（目的変数・展開の型を持つか）。"""

from __future__ import annotations

from dataclasses import dataclass

#: 目的変数。
TOP3, WIN = "top3", "win"


@dataclass(frozen=True)
class ScenarioVariant:
    """``key`` はファイル名、``label`` は表に出す名前、``target`` は 3着以内（``TOP3``）か1着（``WIN``）、
    ``mixed`` が真なら展開の型を材料に入れて学び、予想するときは予想のペースの確率で混ぜる。偽なら展開の型を材料から外す（比べる作り）。"""

    key: str
    label: str
    target: str
    mixed: bool = True


#: おすすめ（3着以内・1着）と、比べる作り（展開の型を混ぜない 3着以内）。
VARIANTS: tuple[ScenarioVariant, ...] = (
    ScenarioVariant("mixed-top3", "展開の型で混ぜる（3着以内）", TOP3),
    ScenarioVariant("mixed-win", "展開の型で混ぜる（1着）", WIN),
    ScenarioVariant("plain-top3", "展開の型を混ぜない（3着以内・比べる作り）", TOP3, mixed=False),
)


def variant_named(key: str) -> ScenarioVariant:
    for variant in VARIANTS:
        if variant.key == key:
            return variant
    raise ValueError(f"知らない作り方です: {key}（{' / '.join(variant.key for variant in VARIANTS)}）")
