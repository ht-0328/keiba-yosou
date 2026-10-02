"""材料を1つずつ足して効果を見る実験（既存モデルの修正計画の 2・4）。全頭の予想（変更版）で試す。

どの材料も、予想するレースより前に分かる値だけで作る（当日の馬場傾向は、同じ日に先に終わったレースだけ）。
1頭ごとの表（``RunnerHistoryRepository`` で読んだ 2016年からの全出走）から作り、全頭の学習データの表に
（レースID, 馬ID）で並べる。

| クラス | 足す材料 | 計画の項目 |
|---|---|---|
| ``PoolSupportFeatures`` | 券種ごとのオッズから見た支持と、単勝から見た値との比 | 2「券種ごとのオッズ」 |
| ``TrackBiasFeatures`` | 当日の同じ競馬場・芝ダで先に終わったレースの、上位馬の4角の位置と馬番の位置 | 4「当日の馬場傾向」 |
| ``SpeedFigureFeatures`` | 条件（競馬場・芝ダ・距離・馬場状態）の標準タイムと比べた速さ（能力指数） | 4「条件を補正したタイムの能力指数」 |
| ``PastMarketExcessFeatures`` | 近走で、オッズから期待された3着以内率をどれだけ上回ったか（相手の強さを含めた評価） | 4「対戦相手の強さを考慮した評価」 |
| （予想のパッケージへ移した） | 騎手・調教師・父・母父が、オッズから期待された3着以内率をどれだけ上回ったか。採用し、2026-09-30 に ``yosou.shared`` のまとまり L（``PeopleMarketFeatures``）へ移した。列は全頭の学習データに入っている | 2「騎手・調教師・血統」 |
| ``GrandsireTop3Features`` | 父の父の産駒の、近1年の3着以内の割合（父・母の父の割合と同じ作り方） | PR #16 の残課題「共通の特徴量に足すか」 |
| ``ConditionColumns`` | レースの条件で学習データを分ける実験の、区分の列（芝ダ・競馬場の区分・距離帯・頭数帯） | 2「競馬場・距離などの違い」 |
| ``ExperimentTableBuilder`` | 上の材料を全頭の学習データに足した表（特徴量の一覧も広げる） | |
"""

from .condition_columns import CONDITION_COLUMNS, ConditionColumns
from .experiment_table_builder import ADOPTED_GROUPS, EXPERIMENT_GROUPS, ExperimentTableBuilder
from .grandsire_top3_features import GrandsireTop3Features
from .past_market_excess_features import PastMarketExcessFeatures
from .pool_support_features import PoolSupportFeatures
from .speed_figure_features import SpeedFigureFeatures
from .track_bias_features import TrackBiasFeatures

__all__ = [
    "PoolSupportFeatures", "TrackBiasFeatures", "SpeedFigureFeatures", "PastMarketExcessFeatures",
    "GrandsireTop3Features", "ConditionColumns", "CONDITION_COLUMNS", "ExperimentTableBuilder", "EXPERIMENT_GROUPS",
    "ADOPTED_GROUPS",
]
