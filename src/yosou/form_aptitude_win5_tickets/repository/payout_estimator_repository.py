"""配当の見積もりの式を、ファイルに書く・読む。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: 置き場所のファイル名（``--models`` の直下）。
FILE_NAME = "payout_estimator.json"
#: ファイルの中の、式と使った期間の鍵。
_ESTIMATOR_KEY = "式"
_PERIOD_KEY = "使った期間"


class PayoutEstimatorRepository:
    """配当の見積もりの式（``PayoutEstimator.to_dict()`` の形の辞書）と、使った期間を ``<root>/payout_estimator.json`` に書く・読む。

    SQL ではなくファイルに読み書きする。JV-Data から作ったもので公開しないので、Git の対象外の ``reports/`` の下に置く。
    """

    def __init__(self, root: Path) -> None:
        self._path = Path(root) / FILE_NAME

    @property
    def path(self) -> Path:
        return self._path

    def save(self, estimator: dict[str, Any], period: dict[str, str]) -> Path:
        """``period`` は使った期間（最初の開催日・最後の開催日・この日より前）。"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        body = json.dumps({_ESTIMATOR_KEY: estimator, _PERIOD_KEY: period}, ensure_ascii=False, indent=2) + "\n"
        self._path.write_bytes(body.encode("utf-8"))
        return self._path

    def load(self) -> dict[str, Any]:
        """保存した式。まだ無ければ ``FileNotFoundError``（``fit-payout`` を案内する）。"""
        if not self._path.exists():
            raise FileNotFoundError(
                f"配当の見積もりの式がありません: {self._path}\n"
                "先に `uv run python -m yosou.form_aptitude_win5_tickets fit-payout` で式を作ってください"
            )
        return json.loads(self._path.read_bytes().decode("utf-8"))[_ESTIMATOR_KEY]
