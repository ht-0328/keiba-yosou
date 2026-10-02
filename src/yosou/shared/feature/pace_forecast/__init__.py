"""展開の予想の結果（まとまり P）を作る部品（近走と適性の予想の設計書 09 の P）。

予想「展開から着順を予想」（``yosou.race_development``）の前半・後半の展開の予想（先頭・序盤の位置・前半のペース・
4コーナーの位置・上がりの速さ・後半のペース）の予測から、1頭ごとの特徴量を作る。予測そのものは、呼ぶ側が渡す
（学習データには、そのレースより前だけで学習した展開のモデルの予測。設計書 11）。

| 名前 | 仕事 |
|---|---|
| ``PaceForecastTableBuilder`` | 元の予測の表から、対象の出走ごとの P の 20列を作る（レース内の順位・偏差も） |

列の名前は ``pace_forecast_columns.py``（``PACE_FORECAST_NAMES`` が特徴量、``SOURCE_COLUMNS`` が元の予測の列）。
"""

from .pace_forecast_columns import PACE_FORECAST_NAMES, SOURCE_COLUMNS
from .pace_forecast_table_builder import PaceForecastTableBuilder

__all__ = ["PACE_FORECAST_NAMES", "SOURCE_COLUMNS", "PaceForecastTableBuilder"]
