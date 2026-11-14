"""研究「重賞の買い方」の部品（1ファイル1クラス）。型の候補・数え上げ・選び方・まとめ方は研究「全レース全券種の買い方」の部品を使う。

| 名前 | 仕事 |
|---|---|
| ``GradedCells`` | 等級の表を重賞だけに絞り、セルを ◎ランクだけにする |
| ``WinningTickets`` | 案2: セルごとに、選ぶ期間の回収率が 100% 以上だった券種を決める |
| ``PlaceBaseline`` | 比べる相手（今の重賞の買い方。複勝の期待値の上位2点）をセル × 開催日に数える |
| ``TicketChooser``・``TicketChoice`` | 2回目: セル（レースの型）ごとに、8券種の中から券種と買い方を1つ選ぶ |
| ``SingleTicketGrid``・``SingleRule`` | 3回目: 単勝・複勝の買い方の候補を数える（``single_ticket_grid``） |
| ``RaceLogit`` | 4回目: レースの中の組の確率を重賞だけで学ぶ（``race_logit``） |
"""

from .graded_cells import RANKS, GradedCells
from .place_baseline import PlaceBaseline
from .ticket_chooser import TicketChoice, TicketChooser
from .winning_tickets import WinningTickets

__all__ = ["GradedCells", "RANKS", "PlaceBaseline", "TicketChoice", "TicketChooser", "WinningTickets"]
