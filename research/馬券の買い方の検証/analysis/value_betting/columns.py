"""3回目の材料表・買い目の表の列の名前（英語。1回目・2回目の ``column_names.py`` と同じ流儀）。

1回目・2回目と同じ意味の列（レースID・馬番・確定着順・確率 など）は ``column_names.py`` の名前をそのまま使い、
3回目で足した列（区切り・期間・複勝の期待値・印 など）だけをここに置く。
"""

from __future__ import annotations

from yosou.upset_level.dataset import BetType

from ..column_names import (  # noqa: F401
    DANGER_PROB,
    FINISH,
    FORM_PROB,
    HORSE_NO,
    IS_GRADED,
    LONGSHOT_PROB,
    LONGSHOT_ZONE,
    PLACE_ODDS,
    PLACE_PAYOUT,
    POPULARITY,
    RACE_DATE,
    RACE_ID,
    WIN_ODDS,
    upset_column,
)

#: 区切り（例 2023年前半）と期間（検証・テスト）。同じレースが、ある区切りのテストと次の区切りの検証の両方に出るので、鍵に入れる。
WINDOW = "window"
PART = "part"
#: 1頭ごとの表に足す列。
HORSE_ID = "horse_id"
TOP3 = "top3"                        # 実際に3着以内に入ったか（1・0）
PLACE_ODDS_HIGH = "place_odds_high"  # 複勝の確定オッズの上限（倍）
FIELD_SIZE = "field_size"            # 確定の出走頭数
MARKET_TOP2 = "market_top2_rate"     # 単勝オッズから見た2着以内率（7頭以下の複勝的中の確率に使う）
MARKET_TOP3 = "market_top3_rate"     # 単勝オッズから見た3着以内率（危険度と「注」の上げ下げに使う）
#: 複勝の期待値（穴馬モデルの確率から）。
PLACE_PROB = "place_prob"    # 複勝的中の確率（7頭以下は2着まで）
PLACE_PRICE = "place_price"  # 見込みの払戻の倍率
PLACE_VALUE = "place_value"  # 期待値 = 複勝的中の確率 × 見込みの倍率
#: 危険な人気馬。
DANGER = "danger"      # 危険度 = 4着以下の確率 − オッズから見た4着以下の確率（人気馬だけ。ほかは欠損）
EXCLUDED = "excluded"  # 消（危険度が人気帯の線以上の人気馬）
#: 印（消・◎・○・▲・△・☆・注。無ければ空）。
MARK = "mark"
#: 買い目の表に足す列。
STAKE_YEN = "stake_yen"      # 賭け金（円。1点 100円）
PAYOUT_YEN = "payout_yen"    # 払戻（円。外れは 0）
LINE = "line"                # その区切りで使った期待値の線
RACE_PROFIT = "race_profit"  # 見込みの利益 E = Σ（期待値 − 1）× 賭け金（枠B の並べ方に使う）
#: 期間の値（研究「既存モデルの改善」の予測の表と同じ）。
PART_VALID = "検証"
PART_TEST = "テスト"


def upset_level_column(bet: BetType) -> str:
    """その券種の、いちばん確率の高い荒れ具合（固い・中荒れ・大荒れ・超荒れ）の列の名前（例 ``upset_level_trio``）。"""
    return f"upset_level_{bet.key}"
