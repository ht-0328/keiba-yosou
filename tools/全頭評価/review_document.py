"""全頭評価の文書の中身。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class HorseReview:
    """1頭の評価。``profile`` は基本情報の1行（性齢・父・母父・調教師・負担重量・交流）。確率はモデルの平均。

    ``strong``・``weak`` は強み・弱みの文（定型。根拠の数字付き）。``rank`` は 3着以内の確率の高い順の評価順。
    """

    horse_id: str
    name: str
    profile: str
    rank: int
    top3: float
    win: float
    sex_age: str
    trainer: str
    carried: float | None
    exchange: str
    strong: list[str] = field(default_factory=list)
    weak: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FieldReviewDocument:
    """1レースの全頭評価。``candidates`` は有力馬の候補（1着の確率の上位の馬名）。``notes`` は文書の末尾に添える注記。"""

    race_id: str
    race_date: date
    race_name: str
    venue: str
    surface: str
    distance_m: int | None
    grade: str
    entries: int
    candidates: list[str]
    horses: list[HorseReview]
    notes: list[str] = field(default_factory=list)
