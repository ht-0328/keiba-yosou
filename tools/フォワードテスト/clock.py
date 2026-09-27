"""今の時刻と待ち方。テストで差し替える。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable


@dataclass
class Clock:
    """``now`` が今の時刻、``sleep`` が秒数だけ待つ関数。"""

    now: Callable[[], datetime] = field(default=datetime.now)
    sleep: Callable[[float], None] = field(default=time.sleep)
