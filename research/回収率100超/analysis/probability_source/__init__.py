"""確率の出どころを替えて、同じ複勝の買い方で比べる部品（docs/04-買い方.md の 8）。

元の確率（全券種のオッズから取り出したもの。``backtest.py`` が残した予測）と、予想「近走と適性から3着以内を予想」の
当日のモデルの確率（券種のオッズから見た支持 N を含む。その年より前だけで学習し直したもの）を、同じレース・同じ馬・
同じ買い方の決まりで比べる。学習は予想のパッケージのモデルのクラスと、研究「既存モデルの改善」の区切りごとの学習部品を
そのまま使う（この研究は、その予想の特徴量もモデルも持たない）。

| 名前 | 仕事 |
|---|---|
| ``YearlyWindows`` | 「その年より前で学習 → 直前の1年で木の本数を決める → その年を予測」の区切りを、年ごとに作る |
| ``RaceDayModelPredictions`` | 当日のモデルを区切りごとに学習し直し、その年の3着以内の確率を出す |
| ``ProbabilitySourceTable`` | 元の確率と新しい確率を同じ馬で突き合わせ、レース内でそろえ直し、2つの平均も足した表を作る |
| ``ProbabilitySourceBacktest`` | 1つの出どころの確率で、線を決まりどおりに選び、年ごとの回収率と幅を出す |
| ``SourceResult`` | 1つの出どころの成績（線・買った馬券・年ごとの表） |
| ``SourceAdoptionRule``・``SourceVerdict`` | 結果を見る前に決めた基準で、新しい確率を採用できるかを決める |
| ``SourceVerdicts`` | 元以外の出どころごとの判定の集まり |
| ``SourceLogLoss`` | 出どころごとの確率の当たり具合（ログ損失）を年ごとに出す |
| ``SourceComparisonReport`` | 比べた結果を1つの文書（Markdown）にする |
| ``PCoreAffinity`` | Windows で、このプロセスを P コアに絞る（学習のスレッドも従う） |
| ``TrainingThreads`` | 学習のスレッド数を、予想のハイパーパラメータの設定に入れる |
"""

from .p_core_affinity import PCoreAffinity
from .probability_source_backtest import ProbabilitySourceBacktest
from .probability_source_table import AVERAGE, MODEL, ORIGINAL, SOURCES, ProbabilitySourceTable
from .race_day_model_predictions import MODEL_PROBABILITY, RaceDayModelPredictions
from .source_adoption_rule import SourceAdoptionRule, SourceVerdict
from .source_comparison_report import SourceComparisonReport
from .source_log_loss import SourceLogLoss
from .source_result import SourceResult
from .source_verdicts import SourceVerdicts
from .training_threads import TrainingThreads
from .yearly_windows import YearlyWindows

__all__ = [
    "YearlyWindows", "RaceDayModelPredictions", "MODEL_PROBABILITY", "ProbabilitySourceTable", "ORIGINAL", "MODEL",
    "AVERAGE", "SOURCES", "ProbabilitySourceBacktest", "SourceResult", "SourceAdoptionRule", "SourceVerdict",
    "SourceVerdicts", "SourceLogLoss", "SourceComparisonReport", "PCoreAffinity", "TrainingThreads",
]
