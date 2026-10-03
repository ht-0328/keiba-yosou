"""1着のモデル（全頭の予想の目的変数「1着」）を、今の本番と同じ材料で時点ごとに7つの区切りで学ぶ部品（入口は ``win_check.py``）。

学習データの表は、対戦レーティングの確かめ（``head_to_head``）と展開の予想の確かめ（``pace_forecast``）が作った今の本番と同じ材料の表を
そのまま使い、予想のパッケージの ``WinTargetData`` で目的変数を「1着」に、基準を「オッズから見た勝率」に持ち替える。
区切り・区切りごとの学習はこの研究のもの。1着の予測は、道具「印の成績」（``tools/印の成績/mark_stats.py --win``）が
◎（単勝の期待値がいちばん高い馬）とレースの期待度を付けて、単勝の成績を数えるのに使う（設計書「近走と適性から3着以内を予想」の 15 の 14・16 の 6）。

| 名前 | 仕事 |
|---|---|
| ``WinVariantSpec``・``WIN_VARIANTS`` | 時点ごとの作り方（表の名前・特徴量の一覧・学ぶ列） |
| ``WinPredictionTruth`` | 保存した1着の予測に、答え（1着）・人気・オッズから見た勝率を付けて読む |
| ``WinComparison`` | 区切りごとに、1着のモデルの確率の誤差を「オッズから見た勝率そのまま」と比べる |
"""

from .win_comparison import WinComparison
from .win_prediction_truth import MARKET_WIN, SCORE, WinPredictionTruth
from .win_variants import WIN_VARIANTS, WinVariantSpec, spec_keyed

__all__ = ["WinVariantSpec", "WIN_VARIANTS", "spec_keyed", "WinPredictionTruth", "MARKET_WIN", "SCORE", "WinComparison"]
