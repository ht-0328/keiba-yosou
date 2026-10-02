"""3回目の検証の部品: 期待値の高い穴馬の複勝を、枠A「馬を選ぶ」→ 枠B「レースを選ぶ」の2段で評価する（docs/05-round3-protocol.md）。

入口は ``backtest_round3.py``。決まり（期間・線・採否の数）は ``protocol.py``、列の名前は ``columns.py``。

| 名前 | 仕事 |
|---|---|
| ``MaterialSources``・``PredictionSource``・``default_sources`` | 7つの区切りの予測の出どころ（どの研究の、どのファイルか） |
| ``TruthTableReader`` | 学習データの表から、答え・人気・複勝オッズ・払戻を読む |
| ``RunnerTableBuilder``・``RaceTableBuilder`` | 予測と答えを、1頭ごと・1レースごとの材料表にする（区切り × 期間が鍵） |
| ``MaterialsBuilder``・``Round3Materials``・``MaterialsStore`` | 材料表を組み立てる（元DB は重賞かを読む間だけ）・持つ・ファイルに書く読む |
| ``PlacePriceFitter``・``PlaceValueCalculator`` | 区切りごとに見込みの倍率を学び、穴馬モデルの確率から複勝の期待値を出す |
| ``DangerExclusion``・``MarkAssigner`` | 危険な人気馬（消）と、印（消・◎・○・▲・△・☆・注） |
| ``HorseSelection``・``LineRule``・``RaceRule``・``Round3Strategy``・``STRATEGIES`` | 戦略の軸（3 × 2 × 2 = 12）と戦略1つ |
| ``CandidatePicker`` | 枠A: 期待値が線以上の複勝を、レースごとに最大3点 |
| ``DailyRaceCap`` | 枠B: 見込みの利益の大きい順に 1日3レースまで（平地の重賞は別枠） |
| ``ValidationLineChooser`` | 線を直前の1年で選ぶ |
| ``WindowPreparer``・``PreparedWindow``・``StrategyEvaluator``・``StrategyResult``・``TicketSummary`` | 区切りごとの準備と、戦略の評価（回収率・90% の幅・控えめな見積もり） |
| ``SearchAdoptionRule``・``ConfirmAdoptionRule``・``FinalRule`` | 探索・確認・最後の1回の採否（事前に固定） |
| ``BaselineBets`` | 比べる目安（全穴馬・1番人気・全頭の複勝） |
| ``UpsetBreakdown``・``OperationalSummary``・``ResultTables`` | 荒れ具合の切り口の表・運用の数値・結果の表 |
| ``StrategyListFile``・``Stage`` | 段階の間で渡す戦略の JSON と、段階（探索・確認・最後の1回） |
"""

from .baselines import BASELINES, BaselineBets
from .candidate_picker import CandidatePicker
from .chosen_file import StrategyListFile
from .confirm_rule import ConfirmAdoptionRule
from .daily_race_cap import DailyRaceCap
from .danger_exclusion import DangerExclusion
from .final_rule import FinalRule
from .horse_selection import HorseSelection
from .line_chooser import ValidationLineChooser
from .line_rule import LineRule
from .mark_assigner import MarkAssigner
from .material_sources import MaterialSources, PredictionSource, default_sources
from .materials import Round3Materials
from .materials_builder import MaterialsBuilder
from .materials_store import MaterialsStore
from .operational_summary import OperationalSummary
from .place_price_fitter import PlacePriceFitter
from .place_value_calculator import PlaceValueCalculator
from .prepared_window import PreparedWindow
from .race_rule import RaceRule
from .race_table_builder import RaceTableBuilder
from .result_tables import ResultTables
from .runner_table_builder import RunnerTableBuilder
from .search_rule import SearchAdoptionRule
from .stage import Stage
from .strategy import Round3Strategy
from .strategy_evaluator import StrategyEvaluator
from .strategy_grid import STRATEGIES, strategy_keyed
from .strategy_result import StrategyResult
from .ticket_summary import TicketSummary
from .truth_table_reader import TruthTableReader
from .upset_breakdown import UpsetBreakdown
from .window_preparer import WindowPreparer

__all__ = [
    "MaterialSources", "PredictionSource", "default_sources", "TruthTableReader", "RunnerTableBuilder", "RaceTableBuilder",
    "MaterialsBuilder", "Round3Materials", "MaterialsStore", "PlacePriceFitter", "PlaceValueCalculator", "DangerExclusion",
    "MarkAssigner", "HorseSelection", "LineRule", "RaceRule", "Round3Strategy", "STRATEGIES", "strategy_keyed",
    "CandidatePicker", "DailyRaceCap", "ValidationLineChooser", "WindowPreparer", "PreparedWindow", "StrategyEvaluator",
    "StrategyResult", "TicketSummary", "SearchAdoptionRule", "ConfirmAdoptionRule", "FinalRule", "BaselineBets", "BASELINES",
    "UpsetBreakdown", "OperationalSummary", "ResultTables", "StrategyListFile", "Stage",
]
