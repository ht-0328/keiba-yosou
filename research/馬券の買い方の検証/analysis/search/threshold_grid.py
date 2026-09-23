"""しきい値の格子（docs/03-protocol.md と同じ値）。探索の前に固定し、結果を見てから変えない。"""

from __future__ import annotations

#: 荒れ度の線。探索期間で「中荒れ以上の確率」が上位 x% に入る確率をしきい値にする（券種ごとに分布が違うため、分位で決める）。
UPSET_TOP_SHARES: tuple[float, ...] = (0.20, 0.35, 0.50)
#: 本命の「3着以内に入る確率」の線（以上）。
FORM_THRESHOLDS: tuple[float, ...] = (0.45, 0.50, 0.55)
#: 本命の「4着以下になる確率」の線（未満）。
DANGER_THRESHOLDS: tuple[float, ...] = (0.40, 0.50)
#: 週の上位 k。
TOP_KS: tuple[int, ...] = (3, 5, 10)
#: 確認期間で確かめる戦略の数の上限。
CHOSEN_LIMIT = 5
