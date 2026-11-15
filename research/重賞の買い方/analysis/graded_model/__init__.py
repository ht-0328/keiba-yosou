"""研究「重賞の買い方」5回目（重賞に特化した予想の印で全部の重賞を買う。設計書「重賞に特化して3着以内と1着を予想」16 の 6）の部品。

| 名前 | 仕事 |
|---|---|
| ``GradedRaceMarker`` | 重賞の予測（7つの区切りのテストの年）に、今週の予想と同じ決め方で印と期待度を付ける |
| ``RaceHorses`` | 1つの重賞の、印ごとの馬と、相手の範囲（○▲・印・無印に流す など）の馬 |
| ``TicketShape`` | 券種ごとの買い目の形1つ（軸と並び・相手・オッズと期待値の線） |
| ``SHAPES``・``CURRENT_RULE_SHAPES`` | 形の候補（16 の 6.3）と、今の印の買い目の形 |
| ``ComboUniverse`` | 形の候補に出てくる全部の組の確定オッズ・払戻・組の期待値 |
| ``ShapeCounter`` | 形ごと・重賞ごとに買い目を組んで数える（上限 24点・トリガミを外す） |
| ``ShapeChooser`` | 券種ごとに、選ぶ年の回収率の 90% の幅の下の端がいちばん高い形を選ぶ（16 の 6.4） |
| ``TopValueRule`` | レースごとに、券種ごとの買い目の期待値が高い上位 k 券種を買う（16 の 6.5 のア） |
"""

from .combo_universe import ComboUniverse
from .graded_race_marker import GRADE, RACE_GRADE, GradedRaceMarker
from .race_horses import RaceHorses
from .shape_catalog import CURRENT_RULE_SHAPES, SHAPES
from .shape_chooser import UNIT, ShapeChooser
from .shape_counter import MEAN_VALUE, POINTS, RETURN, SHAPE, ShapeCounter
from .ticket_shape import TICKETS, TicketShape
from .top_value_rule import TopValueRule

__all__ = ["ComboUniverse", "GRADE", "RACE_GRADE", "GradedRaceMarker", "RaceHorses", "CURRENT_RULE_SHAPES", "SHAPES", "UNIT",
           "ShapeChooser", "MEAN_VALUE", "POINTS", "RETURN", "SHAPE", "ShapeCounter", "TICKETS", "TicketShape", "TopValueRule"]
