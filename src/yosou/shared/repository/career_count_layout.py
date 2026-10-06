"""出走別着度数の表の欄の決めごと（中央の ck と地方の nd で違うところ）。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from 共通 import codes

#: 芝ダ → 欄の名前での書き方。
SURFACE_PREFIXES: dict[str, str] = {"芝": "芝", "ダート": "ダ"}
#: 距離帯。（その距離帯のいちばん長い距離, 欄の名前での書き方）。最後の帯は上限なし。
DistanceBand = tuple[int | None, str]


@dataclass(frozen=True)
class CareerCountLayout:
    """出走別着度数の表（中央 ``ck``・地方 ``nd``）の、欄の決めごと（地方の設計書 04 の 3）。

    - ``table``: 表の名前。
    - ``total_item``: 通算の欄の名前（中央 ``中央合計着回数``、地方 ``総合着回数``。地方の総合は中央と地方の両方を含む）。
    - ``venues``: 競馬場別の欄がある競馬場の名前 → その競馬場の欄がある芝ダ。欄の名前は ``<競馬場><芝 か ダ>・着回数``。
    - ``distance_bands``: 芝ダ × 距離帯 の欄の、距離帯の区切り（短い順）。
    馬場状態の欄（芝良〜ダ不）はどちらの表も同じ。
    """

    table: str
    total_item: str
    venues: Mapping[str, tuple[str, ...]]
    distance_bands: tuple[DistanceBand, ...]


#: 中央の出走別着度数（``ck``）。競馬場は 10場 × 芝ダ、距離帯は 1200以下〜2801以上の9帯。
JRA_CAREER_LAYOUT = CareerCountLayout(
    table="ck", total_item="中央合計着回数",
    venues={name: ("芝", "ダート") for name in codes.VENUE_NAMES.values()},
    distance_bands=(
        (1200, "1200以下"), (1400, "1201-1400"), (1600, "1401-1600"), (1800, "1601-1800"),
        (2000, "1801-2000"), (2200, "2001-2200"), (2400, "2201-2400"), (2800, "2401-2800"),
        (None, "2801以上"),
    ),
)
