"""直した予想から印を付け、印のルールで買う買い方を、過去のレースで確かめる。

1. ``RaceTicketProbabilities``: 1レースの勝率から、7つの券種の買い目が当たる確率を出す（Stern の補正つき Harville の式）。
2. ``MarkCandidateBuilder``: 印のルール（``marks/``）で買い目を作り、当たる確率・確定オッズ・見込みの倍率・期待値を付ける。
   複勝・ワイドは払戻が幅で決まるので、見込みの倍率は最低オッズ × 帯ごとの倍率（``yosou.shared.place_value.PlacePriceEstimator``）。
3. ``PayoutTable``: 払戻を読み、買い目に突き合わせる。
4. ``RaceTableBuilder``: 1行 = 1レースの表（開催日・重賞か・◎の自信・◎の危うさ）を作る。
5. ``RaceSelector``・``ShakyFavorite``: 勝負するレース（1開催日の上位 N と重賞）と、押さえを買うレース（◎が危うい）を決める。
6. ``MarkPlan``・``MarkPlanChooser``: 勝負するレースの数・押さえの線・券種ごとの期待値の線を、検証期間で決める。
7. ``WindowBacktest``: 1つの区切りで、上の手順を通して、テスト期間に買った買い目を返す。
8. ``BacktestSummary``・``CalibrationTable``: 買った買い目から、券種ごと・人気ごと・年ごと・重賞・押さえの表と、
   運用の目安・確率のずれの表を作る。

券種は研究「馬券の買い方の検証」の ``TicketType``（単勝・複勝・馬連・馬単・ワイド・3連複・3連単）をそのまま使う。
"""

from .backtest_summary import BacktestSummary
from .calibration_table import CalibrationTable
from .mark_candidate_builder import MarkCandidateBuilder
from .mark_plan import MarkPlan
from .mark_plan_chooser import MarkPlanChooser, TicketChoice
from .payout_table import PayoutTable
from .race_selector import RaceSelector
from .race_table_builder import RaceTableBuilder
from .race_ticket_probabilities import RaceTicketProbabilities
from .shaky_favorite import ShakyFavorite
from .window_backtest import WindowBacktest

__all__ = [
    "RaceTicketProbabilities", "MarkCandidateBuilder", "PayoutTable", "RaceTableBuilder", "RaceSelector", "ShakyFavorite",
    "MarkPlan", "MarkPlanChooser", "TicketChoice", "WindowBacktest", "BacktestSummary", "CalibrationTable",
]
