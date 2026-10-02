"""元DB から読む部品。1つのクラスが1つの SQL を持つ。"""

from .pace_runner_repository import COLUMNS, PaceRunnerRepository

__all__ = ["COLUMNS", "PaceRunnerRepository"]
