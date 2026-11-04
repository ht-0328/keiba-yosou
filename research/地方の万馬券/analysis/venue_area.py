"""地区: 競馬場と、調教師・馬の所属（招待地域名）を、同じ主催者のまとまり（地区）に寄せる。遠征かどうかはこの地区で見る。"""

from __future__ import annotations

from dataclasses import dataclass

#: 地区 → その地区の競馬場と所属の名前（地方競馬DATA の 招待地域名 と、事実表の競馬場名）。
#: 小林は大井の調教場、西脇は兵庫（園田・姫路）の調教場、北海道は門別の所属。
AREA_MEMBERS: dict[str, tuple[str, ...]] = {
    "南関東": ("浦和", "船橋", "大井", "川崎", "小林"),
    "北海道": ("門別", "北海道"),
    "岩手": ("盛岡", "水沢"),
    "石川": ("金沢",),
    "東海": ("名古屋", "笠松"),
    "兵庫": ("園田", "姫路", "西脇"),
    "高知": ("高知",),
    "佐賀": ("佐賀",),
}
UNKNOWN_AREA = "不明"


@dataclass(frozen=True)
class VenueArea:
    """競馬場名か所属の名前 → 地区。どの地区にも無ければ 不明（廃止された場の所属など）。"""

    def area_of(self, name: str | None) -> str:
        """``name`` は事実表の競馬場名（大井 など）か 招待地域名（小林・西脇 など）。"""
        if not name:
            return UNKNOWN_AREA
        return _AREA_BY_NAME.get(str(name), UNKNOWN_AREA)


_AREA_BY_NAME: dict[str, str] = {
    member: area for area, members in AREA_MEMBERS.items() for member in members
}
