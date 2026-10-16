"""1走の事実。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

#: 序盤の位置（最初のコーナーの順位 ÷ 頭数）を先団・中団・後方に分ける線（展開の予想の設計書 10 の 3 と同じ）。
FRONT_LIMIT = 1 / 3
MIDDLE_LIMIT = 2 / 3
#: ペース（z）をハイ・スローとみなす線（馬の力の材料の「展開の不利」と同じ）。
PACE_LINE = 0.5
#: 4着以下を「負けた走」とみなす（回顧の不利判定と同じ）。
LOST_FINISH = 4
#: グレードコード → 表示。
GRADES: dict[str, str] = {"A": "G1", "B": "G2", "C": "G3", "L": "L"}


@dataclass(frozen=True)
class PastRun:
    """中央の1走の、レース前後に分かる事実。欠けている値は None。

    ``pace`` はそのレースの前半の速さ（前3F の z。正がハイ）。``handicaps`` は回顧の不利（``出遅れ（中）`` の形。4着以下の走だけ）。
    """

    race_id: str
    race_date: date
    horse_id: str
    venue: str
    race_name: str
    class_name: str
    grade: str
    surface: str
    distance_m: int
    condition: str
    field_size: int | None
    frame_no: int | None
    popularity: int | None
    finish: int | None
    time_diff: float | None
    first_corner_rank: int | None
    corner4: int | None
    last3f: float | None
    last3f_rank: int | None
    last3f_count: int | None
    jockey: str
    carried: float | None
    body_weight: int | None
    weight_change: int | None
    interval_days: int | None
    class_order: int | None
    pace: float | None
    handicaps: tuple[str, ...] = ()

    @property
    def lost(self) -> bool:
        """4着以下か（着順が無ければ負けとみなさない）。"""
        return self.finish is not None and self.finish >= LOST_FINISH

    @property
    def label(self) -> str:
        """レースの呼び名。特別競走はレース名、平場はクラス名。"""
        return self.race_name or self.class_name

    @property
    def qualifier(self) -> str:
        """レース名に添える格。重賞・リステッドはグレード、特別競走はクラス名、平場は無し（クラス名が呼び名になる）。"""
        if self.grade:
            return self.grade
        return self.class_name if self.race_name else ""

    @property
    def early_zone(self) -> str | None:
        """序盤の位置の言葉（先頭・先団・中団・後方）。最初のコーナーの順位が無ければ None。"""
        if self.first_corner_rank is None or not self.field_size:
            return None
        if self.first_corner_rank == 1:
            return "先頭"
        position = (self.first_corner_rank - 1) / (self.field_size - 1) if self.field_size > 1 else 0.0
        if position <= FRONT_LIMIT:
            return "先団"
        return "中団" if position <= MIDDLE_LIMIT else "後方"

    @property
    def pace_name(self) -> str | None:
        """ペースの言葉（ハイ・ミドル・スロー）。ペースが無ければ None。"""
        if self.pace is None:
            return None
        if self.pace > PACE_LINE:
            return "ハイ"
        return "スロー" if self.pace < -PACE_LINE else "ミドル"
