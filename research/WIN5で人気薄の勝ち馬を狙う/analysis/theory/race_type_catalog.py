"""人気薄が勝ちやすい「レースの側の型」。どれもレースの前に分かる値（単勝オッズ・重量種別・頭数）だけで決める。"""

from __future__ import annotations

from .flag_rule import FlagRule

#: 「市場が人気薄に票を残している」とみなす、10番人気以下のオッズから見た勝率の合計。
LONGSHOT_SHARE = 0.10
#: 「1番人気が抜けていない」とみなす1番人気の単勝オッズ。
WEAK_FAVORITE = 4.0
#: 多頭数とみなす頭数。
LARGE_FIELD = 15

#: レースの表（1行 = 1レース。列 longshot_market・favorite_odds・weight_type・field_size）に当てる型。
RACE_TYPES: tuple[FlagRule, ...] = (
    FlagRule("R1 人気薄に票が残る", "市場", "10番人気以下のオッズから見た勝率の合計が 0.10 以上",
             lambda r: r["longshot_market"] >= LONGSHOT_SHARE),
    FlagRule("R2 1番人気が抜けていない", "市場", "1番人気の単勝オッズが 4倍以上", lambda r: r["favorite_odds"] >= WEAK_FAVORITE),
    FlagRule("R3 ハンデ戦", "条件", "重量種別がハンデ", lambda r: r["weight_type"] == "ハンデ"),
    FlagRule("R4 多頭数", "条件", "出走 15頭以上", lambda r: r["field_size"] >= LARGE_FIELD),
    FlagRule("R1 かつ R3", "組み合わせ", "人気薄に票が残るハンデ戦",
             lambda r: (r["longshot_market"] >= LONGSHOT_SHARE) & (r["weight_type"] == "ハンデ")),
    FlagRule("R1 か R3", "組み合わせ", "人気薄に票が残るか、ハンデ戦",
             lambda r: (r["longshot_market"] >= LONGSHOT_SHARE) | (r["weight_type"] == "ハンデ")),
)
