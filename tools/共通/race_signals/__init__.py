"""レースごとに「レース前の材料が DB にどこまで入っているか」を読む部品。

出馬表（馬番が決まったか）・馬体重・馬場状態・締め切り前のオッズの有無を、1レースずつ（``read_race``）か
開催日の範囲でまとめて（``read_days``）読む。時点（木曜・前日・当日）を選ぶ ``今週の予想.TimingChooser`` と、
取得と予想の状況を見せる道具（``tools/取得と予想の状況``）が使う。事実表は作らない（取得中の DB を長く塞がないため）。

流れ: ``RaceScope``（どのレースを読むか）→ ``repository/`` の3つ（``ra``・``se``・``o1``）→ ``RaceSignalReader`` が rid でつなぐ → ``RaceSignals``。
"""

from .race_scope import RaceScope
from .race_signal_reader import RaceSignalReader
from .race_signals import RaceSignals

__all__ = ["RaceScope", "RaceSignalReader", "RaceSignals"]
