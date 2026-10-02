"""3回目の検証で事前に固定した数（docs/05-round3-protocol.md と同じ値）。結果を見てから変えない。"""

from __future__ import annotations

#: 区切りの名前（研究「既存モデルの改善」の ``WINDOWS`` の名前）。探索・確認・最後の1回に分ける。
SEARCH_WINDOW_NAMES: tuple[str, ...] = ("2023年前半", "2023年後半", "2024年前半", "2024年後半")
CONFIRM_WINDOW_NAMES: tuple[str, ...] = ("2025年前半", "2025年後半")
FINAL_WINDOW_NAMES: tuple[str, ...] = ("2026年",)

#: 期待値の線の候補（研究「回収率100超」と同じ）と、固定するときの線（設計書の値）。
LINE_CANDIDATES: tuple[float, ...] = (1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.4)
FIXED_LINE = 1.25
#: 線を選ぶのに要る、直前の1年で残る点数の下限。最初の区切りは直前が半年しか無いので半分。
MIN_LINE_POINTS_FULL_YEAR = 300
MIN_LINE_POINTS_HALF_YEAR = 150
#: 線を選ぶ条件の回収率（これを超える線だけ）。
MIN_LINE_RETURN_RATE = 1.0

#: 枠A: 1レースの点数の上限と、1点の賭け金（円）。
MAX_POINTS_PER_RACE = 3
STAKE_YEN = 100
#: 枠B: 1開催日に買うレース数の上限（平地の重賞は別枠）。
RACES_PER_DAY = 3

#: 探索の採否: 4区切り合計の回収率・点数・100% 以上の区切りの数の下限と、確認に回す数の上限。
SEARCH_MIN_RETURN_RATE = 1.0
SEARCH_MIN_POINTS = 600
SEARCH_MIN_GOOD_WINDOWS = 3
SEARCH_CANDIDATE_LIMIT = 3
#: 確認の採否: 2区切り合計の回収率（これを超える）と、90% の下限（これ以上）。
CONFIRM_MIN_RETURN_RATE = 1.0
CONFIRM_MIN_LOWER_BOUND = 1.0
#: 最後の1回: 回収率がこれを割らなければ提案へ。
FINAL_MIN_RETURN_RATE = 0.9
