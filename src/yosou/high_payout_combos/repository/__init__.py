"""ファイルの読み書き。この予想だけの SQL は無い（元DB の確定オッズ・払戻は ``yosou.shared.repository`` で読む）。

| 名前 | 読む・書くもの |
|---|---|
| ``HorseTableRepository`` | 馬ごとの表（``horses/*.parquet``。読むだけ） |
| ``ComboTableRepository`` | 券種ごと・年ごとの組の表（``tables/<券種の英名>_<年>.parquet``） |
| ``ComboTableWriter`` | 組の表の1つのファイルを、月ごとに足して書く |
| ``PredictionStore`` | 年ごとの予測（``predictions/<券種の英名>_<年>.parquet``。``walk`` の出力） |
| ``TicketModelRepository`` | 券種ごとの学習済みモデル（``models/<券種の英名>/race_day/``。形は共有の ``ModelRepository``） |

馬ごとの表の列の名前は ``horse_table_columns.py``、既定の置き場所は ``report_folders.py``。
"""

from .combo_table_repository import ComboTableRepository
from .combo_table_writer import ComboTableWriter
from .horse_table_repository import HorseTableRepository
from .prediction_store import PredictionStore
from .report_folders import HORSES_FOLDER, PREDICTIONS_FOLDER, TABLES_FOLDER, report_folder
from .ticket_model_repository import TicketModelRepository

__all__ = [
    "HorseTableRepository", "ComboTableRepository", "ComboTableWriter", "PredictionStore", "TicketModelRepository",
    "report_folder", "HORSES_FOLDER", "TABLES_FOLDER", "PREDICTIONS_FOLDER",
]
