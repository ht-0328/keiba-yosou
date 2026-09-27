"""元DB から読む部品。1つのクラスが1つの SQL を持つ。"""

from .odds_snapshot_repository import OddsSnapshotRepository
from .place_result_repository import PlaceResultRepository

__all__ = ["OddsSnapshotRepository", "PlaceResultRepository"]
