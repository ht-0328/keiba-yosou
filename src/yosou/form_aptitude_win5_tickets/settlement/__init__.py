"""過去の WIN5 での精算と、比べる相手の買い目（設計書 16 の 1.・2.・5.）。道具「印の成績」の ``--win5`` が呼ぶ。

| クラス | 仕事 |
|---|---|
| ``Win5Outcome`` | 過去の WIN5 の1回の結果を表す値（当たり組と払戻・的中無の印・取消と除外の馬番・発売票数・キャリーオーバー） |
| ``Win5Outcomes`` | 過去の WIN5 の表と取消・除外の表から、開催日ごとの ``Win5Outcome`` を作る |
| ``Win5Settlement`` | 買い目が当たったか、返還があったかを当たり組と照らし、払戻（返還の代金を含む）を出す |
| ``Win5Settled`` | 1回の精算の結果を表す値（点数・代金・払戻・当たり・返還の点数） |
| ``RuleFormations`` | 比べる相手 (1)。ルール集の WIN5 のルール（48点 × 5セット = 240点）の買い目を、人気の順から作る |
| ``PopularityFormation`` | 比べる相手 (2)。各レースの人気の上位から、予算に収まるいちばん大きいフォーメーションを作る |
| ``Win5BacktestTables`` | 買い方ごと・期間ごと・年ごとの、買った日数・投資・払戻・回収率・的中率・90% の幅の表 |
"""

from .popularity_formation import PopularityFormation
from .rule_formations import RuleFormations
from .win5_backtest_tables import HIT, PAYOUT, PERIOD, RACE_DATE, SETTLED_COLUMNS, STAKE, STRATEGY, Win5BacktestTables
from .win5_outcome import Win5Outcome
from .win5_outcomes import Win5Outcomes
from .win5_settled import Win5Settled
from .win5_settlement import Win5Settlement

__all__ = [
    "Win5Outcome", "Win5Outcomes", "Win5Settlement", "Win5Settled", "RuleFormations", "PopularityFormation", "Win5BacktestTables",
    "SETTLED_COLUMNS", "STRATEGY", "PERIOD", "RACE_DATE", "STAKE", "PAYOUT", "HIT",
]
