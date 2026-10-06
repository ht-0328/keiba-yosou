"""出走別着度数地方（nd）の欄の決めごと。"""

from __future__ import annotations

from 共通.local_codes import ACTIVE_LOCAL_VENUE_CODES, LOCAL_VENUE_NAMES, TURF_LOCAL_VENUE_CODES

from yosou.shared.repository import CareerCountLayout

#: 地方の距離帯（その帯のいちばん長い距離, 欄の名前での書き方）。中央の ck（1200以下〜2801以上の9帯）より短い距離を細かく分ける
#: （nvdata-store の ``docs/reference/ND.md``）。
LOCAL_DISTANCE_BANDS: tuple[tuple[int | None, str], ...] = (
    (1000, "1000以下"), (1200, "1001-1200"), (1300, "1201-1300"), (1400, "1301-1400"), (1500, "1401-1500"),
    (1600, "1501-1600"), (1700, "1601-1700"), (1800, "1701-1800"), (2000, "1801-2000"), (2200, "2001-2200"),
    (None, "2201以上"),
)


def _surfaces_of(venue_code: str) -> tuple[str, ...]:
    """その競馬場の欄がある芝ダ。芝のコースは盛岡だけ。"""
    return ("芝", "ダート") if venue_code in TURF_LOCAL_VENUE_CODES else ("ダート",)


#: 出走別着度数地方（``nd``）の欄の決めごと（設計書 09 の E・F、04 の 3）。
#: 通算は総合着回数（中央と地方の両方の出走を含む）。競馬場別の欄は今も開催のある 14場（``<競馬場><ダ か 芝>・着回数``）。
LOCAL_CAREER_LAYOUT = CareerCountLayout(
    table="nd", total_item="総合着回数",
    venues={LOCAL_VENUE_NAMES[code]: _surfaces_of(code) for code in ACTIVE_LOCAL_VENUE_CODES},
    distance_bands=LOCAL_DISTANCE_BANDS,
)
