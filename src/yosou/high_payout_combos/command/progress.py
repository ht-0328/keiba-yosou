"""途中経過を標準エラーに出す。"""

from __future__ import annotations

import sys
from datetime import datetime


def print_progress(message: str) -> None:
    """時刻を付けて、標準エラーに1行出す（結果の表は標準出力か ``--out`` に出るので、混ざらない）。"""
    print(f"{datetime.now():%H:%M:%S} {message}", file=sys.stderr, flush=True)
