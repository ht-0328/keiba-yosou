"""3つの予想から馬の期待値と役割を決め、券種ごとに期待値を積んで買う買い方を、過去のレースで確かめる。

1. ``RaceTicketProbabilities``: 1レースの勝率から、7つの券種の買い目が当たる確率を出す（Stern の補正つき Harville の式）。
2. ``RaceUpsetProbability``: レースごとの荒れそうな確率（3連複の中荒れ以上の確率）を出す。
3. ``RaceCandidatePricer``: 券種ごとの買い目の候補（``ticket_combos/``）を作り、当たる確率・オッズ・期待値を付ける。
   複勝・ワイドの見込みの倍率は最低オッズ × 帯ごとの倍率。
   ``ProbabilityCalibrator``: 当たる確率のずれを、検証期間の券種 × オッズの帯ごとの比で直す。
   ``TicketSetBuilder``: 期待値の低い買い目を切り、点数を絞り、賭け金（``StakeAllocator``）・券種全体の期待値・合成オッズを付ける。
4. ``PayoutTable``: 払戻を読み、買い目に突き合わせる。
5. ``RaceTableBuilder``・``RaceSelector``: 1行 = 1レースの表（重賞か・1番人気を消したか・荒れそうか）と、勝負するレースの選び方。
6. ``BettingPlan``・``BettingPlanChooser``: 券種ごとの線と1開催日のレース数を検証期間で決め、1レース 5,000円の予算に、
   券種全体の期待値の高い券種から積む。
7. ``WindowBacktest``: 1つの区切りで、上の手順を通して、テスト期間に買った買い目を返す。
8. ``BacktestSummary``・``CalibrationTable``: 買った買い目から、金額で数えた表と、確率のずれの表を作る。

券種は研究「馬券の買い方の検証」の ``TicketType``（単勝・複勝・馬連・馬単・ワイド・3連複・3連単）をそのまま使う。
"""

from .backtest_summary import BacktestSummary
from .betting_plan import BettingPlan
from .betting_plan_chooser import BettingPlanChooser, TicketChoice
from .calibration_table import CalibrationTable
from .payout_table import PayoutTable
from .race_selector import RaceSelector
from .race_table_builder import RaceTableBuilder
from .probability_calibrator import ProbabilityCalibrator
from .race_candidate_pricer import RaceCandidatePricer
from .race_ticket_probabilities import RaceTicketProbabilities
from .race_upset_probability import RaceUpsetProbability
from .stake_allocator import StakeAllocator
from .ticket_set_builder import TicketSetBuilder
from .window_backtest import WindowBacktest

__all__ = [
    "RaceTicketProbabilities", "RaceUpsetProbability", "RaceCandidatePricer", "ProbabilityCalibrator", "TicketSetBuilder",
    "StakeAllocator", "PayoutTable",
    "RaceTableBuilder", "RaceSelector", "BettingPlan", "BettingPlanChooser", "TicketChoice", "WindowBacktest",
    "BacktestSummary", "CalibrationTable",
]
