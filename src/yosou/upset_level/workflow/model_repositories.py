"""券種ごとのモデルの置き場所。"""

from __future__ import annotations

from pathlib import Path

from yosou.shared.ml_model import CLASS_MEMBER_TYPES
from yosou.shared.repository import ModelRepository

from ..dataset import BetType


def model_repositories(root: Path) -> dict[BetType, ModelRepository]:
    """券種ごとの ``ModelRepository``。置き場所は ``<root>/<券種の鍵>/<時点>/``（設計書 04 の 4）。

    共通の ``ModelRepository`` は時点までしか知らないので、券種ごとに1つずつ作って置き場所を変える。
    """
    return {bet: ModelRepository(Path(root) / bet.key, CLASS_MEMBER_TYPES) for bet in BetType}
