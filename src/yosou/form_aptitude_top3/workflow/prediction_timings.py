"""この予想が予測を出す時点と、時点ごとに使うモデル（設計書 07）。"""

from __future__ import annotations

from yosou.shared.feature import PredictionTiming

#: この予想が学習し、予測を出す時点（木曜・前日・当日の3つ全部）。
TIMINGS: tuple[PredictionTiming, ...] = tuple(PredictionTiming)
#: 馬の力の材料（まとまり M。``ability_dataset_builder``）のモデルで予測する時点。研究「一番人気を疑う」の直し方を移し、
#: 7つの区切りで今の予想と比べて採用の基準を満たした時点だけ（設計書 15 の 11）。
ABILITY_TIMINGS: tuple[PredictionTiming, ...] = (PredictionTiming.THURSDAY, PredictionTiming.DAY_BEFORE)
#: 今の材料（A〜L・J と N。``pool_dataset_builder``）のモデルで予測する時点（当日）。
FORM_TIMINGS: tuple[PredictionTiming, ...] = tuple(timing for timing in TIMINGS if timing not in ABILITY_TIMINGS)
#: 展開の予想の結果（まとまり P）を足して学ぶ時点。研究「既存モデルの改善」の7つの区切りで、P を足すと今の予想より確率の誤差が
#: 小さくなり、採用の基準を満たした時点だけ（設計書 15 の 13。前日・当日は満たさなかった）。
PACE_TIMINGS: tuple[PredictionTiming, ...] = (PredictionTiming.THURSDAY,)
#: 当日に券種のオッズが無いときに使う、N を使わないモデルの置き場所（モデルの置き場所の下のフォルダの名前）。
POOL_FREE_FOLDER = "券種オッズなし"
#: 1着のモデル（目的変数「1着」。設計書 10・15 の 14）の置き場所（3着以内のモデルの置き場所の下のフォルダの名前。
#: 券種オッズなしの1着のモデルは ``券種オッズなし/1着/``）。
WIN_FOLDER = "1着"
