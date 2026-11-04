"""買い方（戦略）: 券種、荒れ具合ごとに買う型、帯ごとに選ぶ頭数、期待値と配当の線、1レースの点数の上限。"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..payout_band import BIG, HUGE, MEDIUM, SOLID

#: 券種。
TRIFECTA, TRIO = "3連単", "3連複"
#: 型の書き方: 3連単は 1着→2着→3着 の帯（人・中・大）、3連複は 人→中→大 の順に並べた帯。``ANY_PATTERN`` は型を問わない。
Pattern = str
ANY_PATTERN: Pattern = "全"
#: 組の確率に使う勝つ力。``STRENGTH_WIN`` は 1着の確率、``STRENGTH_TOP3`` は 3着以内の確率、``STRENGTH_MIX`` は両方の相乗平均。
#: ``STRENGTH_TOP3_FIT`` は Harville の 3着以内率が 3着以内の確率に一致するよう解いた勝つ力、
#: ``STRENGTH_WIN_THEN_TOP3_FIT`` は 1着だけ 1着の確率で、2着・3着を ``STRENGTH_TOP3_FIT`` で。
STRENGTH_WIN, STRENGTH_TOP3, STRENGTH_MIX = "p1", "p3", "mix"
STRENGTH_TOP3_FIT, STRENGTH_WIN_THEN_TOP3_FIT = "p3fit", "p1→p3fit"
#: 消・穴の決め方。``EDGE_FORM`` は全頭の予想①の確率と市場の差、``EDGE_DANGER``・``EDGE_LONGSHOT`` は②③の予想の確率と市場の差（``stage_predictions``）。
EDGE_FORM, EDGE_DANGER, EDGE_LONGSHOT = "①差", "②差", "③差"
#: 型を決める荒れ具合の元。``UPSET_MARKET`` は市場の割れ方、``UPSET_STAGE`` は④の予想のいちばん高いクラス（固い・中荒れ・大荒れ・超荒れ）。
UPSET_MARKET, UPSET_STAGE = "市場", "④"


@dataclass(frozen=True)
class Strategy:
    """1つの買い方。

    - ``ticket``: 券種（3連単・3連複）。
    - ``patterns``: 荒れ具合（市場の割れ方）→ 買う型の並び。無い荒れ具合は買わない。``ANY_PATTERN`` なら型を問わない。
    - ``favorites``: 人気馬（1〜3番人気）から使う頭数。``eliminate`` が真なら、予想と市場の差がいちばん低い1頭を消してから数える。
    - ``middles``・``longshots``: 中穴・大穴から、予想と市場の差の高い順に使う頭数。
    - ``ev_min``: 組の期待値（Harville の確率 × 確定オッズ）の線。
    - ``odds_min``・``odds_max``: 組のオッズの範囲。
    - ``max_points``: 1レースの点数の上限（期待値の高い順に残す）。
    - ``race_hit_min``: レース単位の線。残した買い目の確率の合計（そのレースでどれかが当たる見込み）がこれ未満のレースは買わない。
    - ``race_ev_min``: レース単位の線。残した買い目の期待値の平均（払戻の見込み ÷ 投資）がこれ未満のレースは買わない。
    - ``min_heads``: 対象にする最少の頭数。
    - ``strength``: 組の確率に使う勝つ力。
    - ``shrink``: 組の確率を市場の組の確率（券種のオッズから）に寄せる割合。``p ^ shrink × m ^ (1 − shrink)`` をレース内で合計 1 に
      そろえる（1.0 なら寄せない）。選んだ組の確率が高く出すぎる（選び取りの偏り）のを抑える。
    - ``danger``: 消す人気馬の決め方。``EDGE_FORM`` は①の差がいちばん低い1頭、``EDGE_DANGER`` は②の差（4着以下の確率 − 市場）がいちばん高い1頭。
    - ``longshot``: 中穴・大穴の選び方。``EDGE_FORM`` は①の差の高い順、``EDGE_LONGSHOT`` は③の差の高い順。
    - ``upset_source``: ``patterns`` の鍵にする荒れ具合。``UPSET_MARKET`` は市場の割れ方、``UPSET_STAGE`` は④の予想。
    - ``big_min``・``mid_min``: レース単位の線。④の「大荒れ以上の確率」「中荒れ以上の確率」がこれ未満のレースは買わない（0 なら使わない）。
    - ``danger_min``: 消の線。消す馬の差（①なら −差、②なら②の差）がこれ未満のレースでは消さない（人気馬を全部使う。0 なら必ず消す）。
    - ``longshot_min``: 穴の線。差（①か③）がこれ未満の中穴・大穴は使わない（0 なら頭数ぶん使う）。
    - ``breakdown``: 型・荒れ具合・頭数などの内訳の表も出すか。
    """

    name: str
    patterns: dict[str, tuple[Pattern, ...]] = field(default_factory=dict)
    ticket: str = TRIFECTA
    favorites: int = 3
    eliminate: bool = True
    middles: int = 3
    longshots: int = 3
    ev_min: float = 1.0
    odds_min: float = 0.0
    odds_max: float = float("inf")
    max_points: int = 30
    race_hit_min: float = 0.0
    race_ev_min: float = 0.0
    min_heads: int = 11
    strength: str = STRENGTH_WIN
    shrink: float = 1.0
    danger: str = EDGE_FORM
    longshot: str = EDGE_FORM
    upset_source: str = UPSET_MARKET
    big_min: float = 0.0
    mid_min: float = 0.0
    danger_min: float = 0.0
    longshot_min: float = 0.0
    breakdown: bool = False


#: 段1 の表3（配当の帯 × 1着→3着の型）で、帯の中の割合が 3% 以上だった型。
MEDIUM_PATTERNS: tuple[Pattern, ...] = ("人中中", "人中人", "人人中", "中人人", "人人大", "中人中", "人中大", "人大人", "中中人", "人大中")
BIG_PATTERNS: tuple[Pattern, ...] = ("中人大", "人中大", "人大中", "大人中", "中大人", "人大大", "中中大", "大中人", "中中人", "中人中",
                                     "大人人", "中中中", "中大中", "大人大")
HUGE_PATTERNS: tuple[Pattern, ...] = ("中大大", "大中大", "大大中", "大大人", "大人大", "大中中", "人大大", "中中大", "大大大")
SOLID_PATTERNS: tuple[Pattern, ...] = ("人人中", "人人人", "人中人", "人中中", "人人大")
#: 荒れ具合ごとの型の既定（固いレースは買わない）。
DEFAULT_PATTERNS: dict[str, tuple[Pattern, ...]] = {MEDIUM: MEDIUM_PATTERNS, BIG: BIG_PATTERNS, HUGE: BIG_PATTERNS + HUGE_PATTERNS}
ALL_PATTERNS: dict[str, tuple[Pattern, ...]] = {SOLID: SOLID_PATTERNS, **DEFAULT_PATTERNS}
#: 荒れ具合を問わず、型も問わない。
ANY_EVERYWHERE: dict[str, tuple[Pattern, ...]] = {SOLID: (ANY_PATTERN,), MEDIUM: (ANY_PATTERN,), BIG: (ANY_PATTERN,), HUGE: (ANY_PATTERN,)}
#: 3連複の型（人→中→大 の順。段1 の表2 の順不同の型）。
TRIO_MEDIUM_PATTERNS: tuple[Pattern, ...] = ("人人中", "人中中", "人人大", "人中大")
TRIO_BIG_PATTERNS: tuple[Pattern, ...] = ("人中大", "中中大", "人中中", "人大大", "人人大", "中大大", "中中中")
TRIO_DEFAULT_PATTERNS: dict[str, tuple[Pattern, ...]] = {MEDIUM: TRIO_MEDIUM_PATTERNS, BIG: TRIO_BIG_PATTERNS, HUGE: TRIO_BIG_PATTERNS}
