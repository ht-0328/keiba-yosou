"""学習データの表を読む部品。

| 名前 | 仕事 |
|---|---|
| ``RunnerFrame`` | 読んだ表を、この研究の共通の形にそろえる（列の名前・カテゴリの型） |
| ``FormTableSource`` | 研究「既存モデルの改善」の表（今の予想の材料）を読む |
| ``AbilityTableSource`` | 研究「馬の力と展開でオッズに勝つ」の表（オッズを使わない197個の材料）を読む |
| ``MarketPredictionSource`` | 研究「既存モデルの改善」が保存した、オッズを使う作り方の予測を読む |
"""

from .ability_table_source import AbilityTableSource
from .form_table_source import FormTableSource
from .market_prediction_source import MarketPredictionSource
from .runner_frame import RunnerFrame

__all__ = ["AbilityTableSource", "FormTableSource", "MarketPredictionSource", "RunnerFrame"]
