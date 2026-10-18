"""組の確率の作り方の案（docs/01 の 4 の重みの4案）。"""

from __future__ import annotations

from dataclasses import dataclass

from .combo_features import BASE_FEATURES, EXTRA_FEATURES

#: 種類ごとの差の罰則の強さの候補。差を使わない案は 0 だけ。
PENALTIES: tuple[float, ...] = (1.0, 10.0, 100.0, 1000.0)
#: 比べる成績がまだ無い最初の区切りで使う罰則の強さ。
FIRST_PENALTY = 100.0


@dataclass(frozen=True)
class WeightMethod:
    """``features`` のもとに重みを掛け、``with_kinds`` なら種類ごとの差も足す作り方。``key`` はファイル名に使う英字の名前。

    例: 案「種類」は、4つのもと × （共通の重み 1つ + 6つの種類の差）= 28 個の重みを持つ。
    """

    name: str
    key: str
    features: tuple[str, ...]
    with_kinds: bool

    @property
    def penalties(self) -> tuple[float, ...]:
        return PENALTIES if self.with_kinds else (0.0,)


#: 試す4案（docs/01 の 4 の表の順）。
METHODS: tuple[WeightMethod, ...] = (
    WeightMethod("今", "now", BASE_FEATURES, with_kinds=False),
    WeightMethod("種類", "kinds", BASE_FEATURES, with_kinds=True),
    WeightMethod("材料", "extra", (*BASE_FEATURES, *EXTRA_FEATURES), with_kinds=False),
    WeightMethod("種類＋材料", "kinds_extra", (*BASE_FEATURES, *EXTRA_FEATURES), with_kinds=True),
)
