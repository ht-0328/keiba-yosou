"""予想ごとの学習データ（全期間）を作り、保存し、読み込む。

期間ごとに学習し直す検証（ウォークフォワード）では、同じ学習データを何度も使う。元DB から特徴量を作るのは
時間がかかるので、予想ごとに1回だけ全期間ぶんを作り、Git 対象外の ``reports/既存モデルの改善/tables/`` に保存する。
学習データを作るのは予想のパッケージの ``dataset_builder`` そのもので、この研究は特徴量の作り方を持たない。

| 名前 | 仕事 |
|---|---|
| ``ModelTableSpec`` | 1つの予想の、学習データの作り方（``dataset_builder``）と特徴量の一覧 |
| ``MODEL_TABLES`` | 4つの予想の ``ModelTableSpec`` の並び。``spec_named`` で名前から引く（重賞の直す前の表と材料の実験の表も引ける） |
| ``TableStore`` | 学習データ（``TrainingData``）を pickle に書く・読む |
| ``TABLE_PERIOD`` | 学習データを作る期間（ウォームアップ 2016年・サンプル 2017年から） |
| ``STAKES_TABLE_PERIOD`` | 重賞の予想の学習データを作る期間（ウォームアップ 2011年・サンプル 2012年から） |
"""

from .model_table_spec import ModelTableSpec
from .model_tables import MODEL_TABLES, STAKES_TABLE_PERIOD, TABLE_PERIOD, spec_named
from .table_store import TableStore

__all__ = ["ModelTableSpec", "MODEL_TABLES", "TABLE_PERIOD", "STAKES_TABLE_PERIOD", "spec_named", "TableStore"]
