"""年ごとの予測の置き場（予想のパッケージの ``PredictionStore``）の偽物（テスト用）。"""

from __future__ import annotations

from pathlib import Path

from yosou.shared.betting import TicketType


class FakePredictionStore:
    """年ごとの予測の置き場の偽物（``<フォルダ>/<券種の英名>_<年>.parquet``）。"""

    def __init__(self, folder: Path) -> None:
        self._folder = folder

    def years(self, ticket_type: TicketType) -> list[int]:
        return sorted(int(path.stem.rsplit("_", 1)[1]) for path in self._folder.glob(f"{ticket_type.key}_*.parquet"))

    def path(self, ticket_type: TicketType, year: int) -> Path:
        return self._folder / f"{ticket_type.key}_{year}.parquet"
