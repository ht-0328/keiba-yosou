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
#: 展開スコア（まとまり S。設計書「買うレースと買い目を決める」05）を足して学ぶ時点。3着以内のモデルと1着のモデルで別々に、
#: 研究「既存モデルの改善」の7つの区切りで S を足すと今の予想より確率の誤差が小さくなり、採用の基準を満たした時点だけ（設計書 15 の 17）。
#: 当日の1着は確率の誤差の基準を満たしたが、道具「印の成績」で ◎の期待値 1.00 以上の ◎ の単勝回収率が下がったので足していない。
#: 予測には、その時点の展開のモデル（``reports/展開から着順を予想/models/``）と表 G（``reports/展開スコア/cache/``）が要る。
SCORE_TOP3_TIMINGS: tuple[PredictionTiming, ...] = (PredictionTiming.DAY_BEFORE,)
SCORE_WIN_TIMINGS: tuple[PredictionTiming, ...] = ()
#: S を学習データに足す時点（どちらかのモデルが使う時点。学習データは時点ごとに1つで、使わないモデルには渡す前に外す）。
SCORE_TIMINGS: tuple[PredictionTiming, ...] = tuple(timing for timing in TIMINGS if timing in SCORE_TOP3_TIMINGS or timing in SCORE_WIN_TIMINGS)
#: 能力スコア（まとまり T。能力指数を今回の斤量で直し、レース内の偏差・2位との差・順位にしたもの。設計書「買うレースと買い目を決める」04）を
#: 足して学ぶ時点。3着以内のモデルと1着のモデルで別々に、研究「既存モデルの改善」の入口⑭で7つの区切りで T を足すと今の予想より確率の誤差が
#: 小さくなり、採用の基準を満たし、道具「印の成績」で印の成績と全券種の回収率が悪くなっていない時点だけ（設計書 15 の 18）。
#: 木曜は両方のモデルで基準を満たし、◎ の成績も上がったので足す。前日の3着以内は誤差の基準は満たしたが、実際に買う複勝の回収率が下がったので足さない。
#: T は予測用データの能力指数と斤量から作るので、予測に追加のモデルや表は要らない。
ABILITY_SCORE_TOP3_TIMINGS: tuple[PredictionTiming, ...] = (PredictionTiming.THURSDAY,)
ABILITY_SCORE_WIN_TIMINGS: tuple[PredictionTiming, ...] = (PredictionTiming.THURSDAY,)
#: T を学習データに足す時点（どちらかのモデルが使う時点。使わないモデルには渡す前に外す）。
ABILITY_SCORE_TIMINGS: tuple[PredictionTiming, ...] = tuple(
    timing for timing in TIMINGS if timing in ABILITY_SCORE_TOP3_TIMINGS or timing in ABILITY_SCORE_WIN_TIMINGS)
#: トラックバイアスの補正（まとまり U。当日の先に終わったレースで「市場の見立てより来た馬が内か外か・前か後ろか」を数えたもの。
#: 設計書「買うレースと買い目を決める」06 の 1）を足して学ぶ時点。T と同じ決め方（設計書 15 の 19）。馬番が要るので前日から。
#: 予測には、その時点の展開のモデル（④ 4コーナーの位置）と、元DB の終わったレースの傾き（``reports/トラックバイアス/cache/``）が要る。
TRACK_BIAS_TOP3_TIMINGS: tuple[PredictionTiming, ...] = ()
TRACK_BIAS_WIN_TIMINGS: tuple[PredictionTiming, ...] = ()
#: U を学習データに足す時点（どちらかのモデルが使う時点。使わないモデルには渡す前に外す）。
TRACK_BIAS_TIMINGS: tuple[PredictionTiming, ...] = tuple(
    timing for timing in TIMINGS if timing in TRACK_BIAS_TOP3_TIMINGS or timing in TRACK_BIAS_WIN_TIMINGS)
#: 馬体重の表の割引（まとまり V。増減の帯 × 前走からの間隔 × 馬齢ごとの市場の見立てとの差。設計書「買うレースと買い目を決める」06 の 2）を
#: 足して学ぶ時点。T と同じ決め方（設計書 15 の 20）。馬体重の発表は当日なので当日だけ。予測には表 W（``reports/馬体重の表/cache/``）が要る。
WEIGHT_DISCOUNT_TOP3_TIMINGS: tuple[PredictionTiming, ...] = ()
WEIGHT_DISCOUNT_WIN_TIMINGS: tuple[PredictionTiming, ...] = ()
#: V を学習データに足す時点（どちらかのモデルが使う時点。使わないモデルには渡す前に外す）。
WEIGHT_DISCOUNT_TIMINGS: tuple[PredictionTiming, ...] = tuple(
    timing for timing in TIMINGS if timing in WEIGHT_DISCOUNT_TOP3_TIMINGS or timing in WEIGHT_DISCOUNT_WIN_TIMINGS)
#: 当日に券種のオッズが無いときに使う、N を使わないモデルの置き場所（モデルの置き場所の下のフォルダの名前）。
POOL_FREE_FOLDER = "券種オッズなし"
#: 1着のモデル（目的変数「1着」。設計書 10・15 の 14）の置き場所（3着以内のモデルの置き場所の下のフォルダの名前。
#: 券種オッズなしの1着のモデルは ``券種オッズなし/1着/``）。
WIN_FOLDER = "1着"
