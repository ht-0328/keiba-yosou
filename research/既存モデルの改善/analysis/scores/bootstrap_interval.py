"""回収率の推定幅（開催日を単位にしたブートストラップ）。中身は ``tools/共通/bootstrap_interval.py``（道具「印の成績」も使う）。"""

from __future__ import annotations

from 共通.bootstrap_interval import BootstrapInterval

__all__ = ["BootstrapInterval"]
