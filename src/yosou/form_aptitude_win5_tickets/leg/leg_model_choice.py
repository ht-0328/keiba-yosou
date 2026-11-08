"""対象レース1つで使う確率と、選んだ理由。"""

from __future__ import annotations

from dataclasses import dataclass

from .leg_model import LegModel


@dataclass(frozen=True)
class LegModelChoice:
    """選んだ確率（``LegModel``）と、その理由（表に出す1文）、使ったオッズの断面（締め切り前の単勝オッズのいちばん新しい
    発表月日時分 ``MMDDHHMM``。無ければ None。実際に予想した結果の記録に残す）。"""

    model: LegModel
    reason: str
    odds_announced_at: str | None
