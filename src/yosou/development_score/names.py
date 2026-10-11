"""展開スコアの、脚質・ペースの区分の名前と、表の列の名前。"""

from __future__ import annotations

#: 脚質（レース前に分かる脚質と、①② の予測から出す位置の確率の名前。前から後ろの順）。
LEAD, FRONT, MIDDLE, BACK = "逃げ", "先行", "差し", "追込"
STYLES: tuple[str, ...] = (LEAD, FRONT, MIDDLE, BACK)
#: ペース（展開の予想③の区分と同じ名前。遅い順）。
SLOW, EVEN, HIGH = "スロー", "平均", "ハイ"
PACES: tuple[str, ...] = (SLOW, EVEN, HIGH)

#: 表 G と材料の列。
STYLE, PACE = "脚質", "ペース"
VENUE_CODE, SURFACE = "競馬場コード", "芝ダ"
TOP3 = "3着以内"
MARKET_TOP3 = "市場から見た3着以内率"
COUNT, RAW_GAP, POOL_GAP, GAP = "件数", "差", "全競馬場の差", "縮めた差"

#: 展開スコアと、その脚質ごとの内訳の列。
SCORE = "展開スコア"


def contribution(style: str) -> str:
    """脚質ごとの内訳の列の名前（例 ``展開スコア_逃げ``）。"""
    return f"{SCORE}_{style}"


CONTRIBUTIONS: tuple[str, ...] = tuple(contribution(style) for style in STYLES)

#: 判定の列と値。
VERDICT = "判定"
FAVORED, UNFAVORED, NEUTRAL = "展開有利", "展開不利", "－"
