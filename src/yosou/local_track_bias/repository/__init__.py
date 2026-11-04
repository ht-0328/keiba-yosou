"""地方の当日の馬場傾向のデータの読み込み。元DB を読む SQL はこのフォルダだけに書き、1つの SQL につき 1つのリポジトリにする。

| リポジトリ | 読むもの |
|---|---|
| ``PastPositionRepository`` | これから走る1レースの出走馬の、直近3走の4コーナーの位置の平均（事実表から） |

傾きの元になる全出走は、中央と同じ ``yosou.track_bias.BiasRunRepository`` で読む（事実表の元を見分けるので、地方の元DB ではそのまま地方の出走になる）。
"""

from .past_position_repository import PastPositionRepository

__all__ = ["PastPositionRepository"]
