"""この予想の、学習データの決めごと（設計書 08）。

学習データそのものは、手本の予想（``yosou.form_aptitude_top3``）の組み立てで作る。ここには、この予想だけの決めごとを置く。

| 名前 | 仕事 |
|---|---|
| ``WildRaceRows`` | 手本の予想の学習データから、荒れたレース（3連単の払戻が 10万円以上）の行だけを残す。``TrainingRows`` を守る |
| ``obi_rules.py`` | 荒れたレースと帯の線（定数だけ） |
"""

from .obi_rules import OBI_YEN, WILD_LINE_YEN
from .wild_race_rows import WildRaceRows

__all__ = ["WildRaceRows", "OBI_YEN", "WILD_LINE_YEN"]
