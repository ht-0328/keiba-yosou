"""WIN5 の予想の記録の、対象レース1つ（選んだ馬番と馬名）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from 共通 import codes

from yosou.shared.dataset import HORSE_NAME, HORSE_NO

#: rid の中の競馬場コードとレース番号の位置。
_VENUE = slice(8, 10)
_RACE_NO = slice(14, 16)


@dataclass(frozen=True)
class Win5Leg:
    """対象レースのレース ID・使った確率（当日・前日・オッズだけ）・選んだ馬（馬番と馬名。予想の記録の並び = 選んだ順）。"""

    race_id: str
    model: str
    picks: tuple[tuple[int, str], ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Win5Leg:
        """予想の記録の「対象レース」の1つ（``LegForecast.to_dict`` の形）から作る。"""
        names = {int(horse[HORSE_NO]): str(horse.get(HORSE_NAME) or "") for horse in data.get("馬", [])}
        picks = tuple((int(number), names.get(int(number), "")) for number in data["買い目"])
        return cls(str(data["レースID"]), str(data.get("使った確率", "")), picks)

    @property
    def label(self) -> str:
        """``東京10R`` の形。"""
        return f"{codes.venue_name(self.race_id[_VENUE])}{int(self.race_id[_RACE_NO])}R"

    @property
    def numbers(self) -> tuple[int, ...]:
        return tuple(number for number, _ in self.picks)

    def pick_text(self) -> str:
        """選んだ馬を「3 馬名・5 馬名」の形で（馬名が無ければ馬番だけ）。"""
        return "・".join(f"{number} {name}".rstrip() for number, name in self.picks)
