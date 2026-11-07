"""1レースの出走馬の推定脚質（馬番 → 逃げ・先行・差し・追込）を元DB から作る（表の画像の脚質の列）。中央と地方。"""

from __future__ import annotations

from pathlib import Path

from 共通 import db
from 共通.local_codes import LOCAL_VENUE_RANGE

from 発走前の通知.estimated_styles import EstimatedStyles
from 発走前の通知.past_style_repository import JRA_VENUES, PastStyleRepository


class RaceStyles:
    """DB は読むたびに開いてすぐ閉じる（取り込みの邪魔をしない）。数える走は、中央は中央の競馬場、地方（``local()``）は地方の競馬場の走。
    地方はレース後の脚質の判定が無いので、コーナーの順位と頭数から1走の脚質を作る。"""

    def __init__(self, db_path: str | Path | None = None, default: db.DatabaseDefault = db.JRA,
                 styles: EstimatedStyles | None = None, venues: tuple[str, str] = JRA_VENUES) -> None:
        self._db_path = db_path
        self._default = default
        self._styles = styles or EstimatedStyles()
        self._venues = venues

    @classmethod
    def local(cls, db_path: str | Path | None = None) -> RaceStyles:
        return cls(db_path, db.LOCAL, EstimatedStyles(from_corners=True), LOCAL_VENUE_RANGE)

    def read(self, rid: str) -> dict[int, str]:
        with db.open_db(self._db_path, default=self._default) as con:
            return self._styles.of(PastStyleRepository(con, self._venues).read(rid))
