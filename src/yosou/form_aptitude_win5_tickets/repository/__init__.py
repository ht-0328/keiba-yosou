"""この予想だけの読み書き。SQL はこのフォルダだけに書き、1つの SQL につき 1つのリポジトリにする。元DB は読むだけ。

| クラス | 読む・書くもの |
|---|---|
| ``Win5Day`` | WIN5 の日を表す値（開催日・対象レース5つのレースID・キャリーオーバー金額初期・土曜か） |
| ``Win5DayRepository`` | 元DB の ``wf`` と子表 ``wf__重勝式対象レース情報`` から、1つの開催日の WIN5 を読んで ``Win5Day`` にする |
| ``Win5HistoryRepository`` | ある日より前の WIN5 の回ごとの当たり組・払戻・発売票数・キャリーオーバー・返還と的中無の印・当たり組の5頭の確定単勝オッズ（と、各対象レースの単勝オッズの逆数の合計） |
| ``Win5ScratchRepository`` | ある日より前の WIN5 の対象レースの、出走取消・競走除外の馬番（過去の WIN5 での精算の返還に使う） |
| ``Win5LegRunnerHistoryRepository`` | ある日より前の WIN5 の対象レースの出走馬（取消・除外を除く）の馬番・確定単勝オッズと、レースの発走時刻・障害か（過去の WIN5 での確かめで、対象レースの確率の表を作るのに使う） |
| ``LegRunnerRepository`` | 1レースの出走馬の馬番・馬名と、出走の行の単勝オッズ（障害の対象レースを、オッズから見た勝率で予想するのに使う） |
| ``Win5ForecastRecordRepository`` | 実際に予想した結果を ``記録/<開催日>.json`` に書く・読む（SQL は持たない） |
| ``PayoutEstimatorRepository`` | 配当の見積もりの式を ``payout_estimator.json`` に書く・読む（SQL は持たない） |

``win5_columns.py`` は、過去の WIN5 の表の列の名前。``LEG_COUNT`` は対象レースの数（5）。
"""

from .leg_runner_repository import LegRunnerRepository
from .payout_estimator_repository import PayoutEstimatorRepository
from .win5_day import Win5Day
from .win5_day_repository import LEG_COUNT, Win5DayRepository
from .win5_forecast_record_repository import Win5ForecastRecordRepository
from .win5_history_repository import Win5HistoryRepository
from .win5_leg_runner_history_repository import Win5LegRunnerHistoryRepository
from .win5_scratch_repository import Win5ScratchRepository

__all__ = [
    "Win5Day", "Win5DayRepository", "Win5HistoryRepository", "Win5ScratchRepository", "Win5LegRunnerHistoryRepository",
    "LegRunnerRepository",
    "Win5ForecastRecordRepository", "PayoutEstimatorRepository", "LEG_COUNT",
]
