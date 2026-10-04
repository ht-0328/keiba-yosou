"""印を付けた表に足す、絞り込みのための列の名前（研究「回収率100超の施策」の施策 1-A・2・5。買い目の部品と道具「印の成績」が使う）。"""

from __future__ import annotations

#: 2つのモデルの名前（予測のファイルの列 → この道具の列の後ろに付ける名前）。
MEMBER_SOURCES: dict[str, str] = {"LightGBM": "lightgbm", "CatBoost": "catboost"}
MEMBERS: tuple[str, ...] = tuple(MEMBER_SOURCES.values())


def member_column(base: str, member: str) -> str:
    """モデルごとの列の名前。例: ``member_column("win_value", "lightgbm")`` → ``win_value_lightgbm``。"""
    return f"{base}_{member}"


def member_columns(base: str) -> tuple[str, ...]:
    """2つのモデルぶんの列の名前。"""
    return tuple(member_column(base, member) for member in MEMBERS)


#: レースの絞り込みの旗（レースの全頭に同じ値が入る）。
#: 2モデル一致: ◎ の単勝の期待値が、LightGBM と CatBoost のそれぞれの確率で出しても線（1.00）以上。
AGREEMENT = "agreement"
#: 3連単の支持あり: ◎ の「3連単から見た勝率 ÷ 単勝から見た勝率」が線以上。
POOL_BACKED = "pool_backed"
#: 馬ごとの列。3連単のオッズから取り出した勝率と、単勝オッズから見た勝率との比。
POOL_WIN = "pool_win"
POOL_SUPPORT = "pool_support"
#: 3連単の支持ありとみなす比の下限（固定。検証期間では決めない）。
POOL_SUPPORT_LINE = 1.0
#: 前日夜 → 当日朝の単勝オッズの動き（馬ごと）。前日の最後の断面と当日 9時30分までの最後の断面のオッズと、その対数の差。
ODDS_EVENING = "odds_evening"
ODDS_MORNING = "odds_morning"
ODDS_MOVE = "odds_move"
