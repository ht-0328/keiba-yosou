"""人気薄の1着の予想の作り方1つ（学ぶ行・学び方）。"""

from __future__ import annotations

from dataclasses import dataclass

#: 予測を人気薄の確率として使う人気（この人気より下の馬の確率を置き換える）。
LONGSHOT_FROM = 10
#: 出発点（基準）の元。オッズから見た勝率か、今のモデルのそろえた1着の確率（区切りごとの予測。その半年より前で学んだもの）。
MARKET_BASELINE, CURRENT_BASELINE = "オッズ", "今のモデル"


@dataclass(frozen=True)
class LongshotVariant:
    """``key`` はファイル名、``label`` は表に出す名前、``min_popularity`` は学ぶ行の人気の下限（10 なら10番人気以下）、
    ``ranker`` は並べ替え（人気薄が勝ったレースだけで学ぶ）か、二値分類（人気薄の全部の行で学ぶ）か。
    ``baseline`` は出発点の元、``weighted`` はレースごとに重みの合計をそろえるか（二値分類だけ）。"""

    key: str
    label: str
    min_popularity: int
    ranker: bool = False
    baseline: str = MARKET_BASELINE
    weighted: bool = True
