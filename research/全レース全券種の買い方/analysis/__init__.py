"""研究「全レース全券種の買い方」の部品（1ファイル1クラス）。

| 名前 | 仕事 |
|---|---|
| ``Fold``・``half_year_folds()`` | 半年ごとの区切り（印を付けた表と同じ名前）と、その区切りを予測するモデルの検証データの始まり |
| ``UpsetWalkForward`` | 荒れ具合の予想（当日）を区切りごとに学び直し、過去のレースの券種ごとの荒れ具合の確率と配当率を出す |
| ``GradesTable`` | レースごとの的中率・配当率とその等級（セル） |
| ``HorseSlots`` | 馬ごとの位置（◎ は 0、ほかは確率の順、消は無し） |
| ``Formation``・``candidates()`` | 買い目の型（軸・相手・2列目・期待値の線）と券種ごとの候補 |
| ``FormationMask`` | 組が型の買い目に入るかの判定 |
| ``TicketPicker`` | 型の中の組から、期待値の線・1点残し・トリガミで買う組を決める |
| ``DayTable`` | セル × 開催日ごとの点数・払戻・レース数・当たったレース数 |
| ``RecoveryBootstrap`` | 開催日を選び直して回収率の 90% の幅の下の端を出す（候補をまとめて） |
| ``CombosSource`` | 券種ごと・年ごとに、組の表・印を付けた表・枠連の表から標準の形の表を作る |
| ``CandidateCounter`` | 1券種の型の候補を全部、年ごとの組の表で数え上げる（候補 × セル × 開催日） |
| ``CellSelector``・``CellChoice`` | セルごとに、選ぶ期間の成績で型を1つ選ぶ |
| ``ChoiceSummary`` | 選んだ型で買ったときの成績（期間・年・セルごと）と採用の基準の判定 |
| ``BaselineTickets`` | 比べる相手（今の印の買い目）を道具「印の成績」の買い目の CSV からまとめる |
| ``CasesReport`` | セルごとの決着の型の表（手順3） |
"""

from .baseline_tickets import BASELINE_RULES, BaselineTickets
from .candidate_counter import CandidateCounter
from .cases_report import CasesReport
from .cell_selector import MIN_HITS, CellChoice, CellSelector
from .choice_summary import ChoiceSummary
from .combos_source import BRACKET_LABEL, TICKET_LABELS, CombosSource, horse_count
from .day_table import DayTable
from .formation import Formation, candidates
from .formation_mask import FormationMask
from .grades_table import CELL, NO_GRADE, GradesTable
from .half_year_folds import Fold, half_year_folds
from .horse_slots import HorseSlots
from .recovery_bootstrap import RecoveryBootstrap
from .ticket_picker import TicketPicker
from .upset_walk_forward import COLUMNS as UPSET_COLUMNS, PAYOUT_RATE, UpsetWalkForward

__all__ = ["Fold", "half_year_folds", "UpsetWalkForward", "UPSET_COLUMNS", "PAYOUT_RATE", "GradesTable", "CELL", "NO_GRADE", "HorseSlots",
           "Formation", "candidates", "FormationMask", "TicketPicker", "DayTable", "RecoveryBootstrap", "CombosSource", "TICKET_LABELS",
           "BRACKET_LABEL", "horse_count", "CandidateCounter", "CellSelector", "CellChoice", "MIN_HITS", "ChoiceSummary",
           "BaselineTickets", "BASELINE_RULES", "CasesReport"]
