"""予想ごとに、現行・オッズだけ・変更版を比べる表を作る（既存モデルの修正計画の 3）。

| 名前 | 仕事 |
|---|---|
| ``PredictionJoin`` | 予測の表に、学習データの表（評価用の列・目的変数・基準）を突き合わせる |
| ``TableFormatter`` | pandas の表を、出力の表（``共通.render.Table``）にする（小数を丸める） |
| ``PlaceValueStrategy`` | 複勝を期待値で買う（線は検証期間で決める）。全頭と穴馬の比べ方で使う |
| ``FormComparison`` | 全頭の3着以内の比べ方の表 |
| ``LongshotComparison`` | 穴馬の3着以内の比べ方の表（中穴・大穴ごと） |
| ``FavoriteComparison`` | 人気馬の4着以下の比べ方の表（人気帯ごと・危険の判定） |
| ``UpsetComparison`` | 荒れ具合の比べ方の表（現行と計算） |
| ``ExperimentComparison`` | 材料の実験の比べ方の表（全頭の変更版に材料を足す・条件で分ける。base と比べて採否） |
"""

from .experiment_comparison import ExperimentComparison
from .favorite_comparison import FavoriteComparison
from .form_comparison import FormComparison
from .longshot_comparison import LongshotComparison
from .place_value_strategy import PlaceValueStrategy
from .prediction_join import LABEL, PredictionJoin
from .table_formatter import TableFormatter
from .upset_comparison import UpsetComparison

__all__ = [
    "PredictionJoin", "LABEL", "TableFormatter", "PlaceValueStrategy",
    "FormComparison", "LongshotComparison", "FavoriteComparison", "UpsetComparison", "ExperimentComparison",
]
