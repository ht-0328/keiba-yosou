"""直した予想を組み合わせた買い方を、過去のレースで確かめる。

1. ``RaceTicketProbabilities``: 1レースの勝率から、7つの券種の買い目が当たる確率を出す（Stern の補正つき Harville の式）。
2. ``RaceCandidateBuilder``: 1レースの買い目ごとに「当たる確率 × 見込みの倍率」（期待値）を出し、期待値の低い買い目を落とす。
   複勝・ワイドは払戻が幅で決まるので、見込みの倍率は最低オッズ × 帯ごとの倍率（``yosou.shared.place_value.PlacePriceEstimator``）。
3. ``CandidateBuilder``: 期間の全レースの買い目の候補をまとめ、払戻（``PayoutTable``）を突き合わせる。
4. ``BettingRule``: 券種ごとの買い方（期待値の線・オッズの上限・1レースの点数の上限）。``RULE_GRID`` が候補の並び。
5. ``RuleChooser``: 検証期間の回収率で、券種ごとの買い方を決める。回収率が 100% に届かない券種は買わない。
6. ``WindowBacktest``: 1つの区切りで、上の手順を通して、テスト期間に買った買い目を返す。
7. ``BacktestSummary``: 買った買い目から、券種ごと・人気ごと・年ごとの表と、運用の目安の表を作る。

券種は研究「馬券の買い方の検証」の ``TicketType``（単勝・複勝・馬連・馬単・ワイド・3連複・3連単）をそのまま使う。
"""

from .backtest_summary import BacktestSummary
from .betting_rule import BettingRule
from .candidate_builder import CandidateBuilder
from .payout_table import PayoutTable
from .race_candidate_builder import RaceCandidateBuilder
from .race_ticket_probabilities import RaceTicketProbabilities
from .rule_chooser import RuleChooser
from .rule_grid import RULE_GRID
from .window_backtest import WindowBacktest

__all__ = [
    "RaceTicketProbabilities", "RaceCandidateBuilder", "CandidateBuilder", "PayoutTable",
    "BettingRule", "RULE_GRID", "RuleChooser", "WindowBacktest", "BacktestSummary",
]
