"""予測の表の CSV の読み書き。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_DATE, RACE_ID

#: Excel でも文字化けしないよう BOM 付きの UTF-8。
ENCODING = "utf-8-sig"
#: 読むときに文字列のままにする列（数値にすると桁が落ちる）。無い列（レース単位の表の馬ID）は無視される。
_TEXT_COLUMNS: dict[str, type] = {RACE_ID: str, HORSE_ID: str}


class PredictionFile:
    """予測の表を CSV に書き、同じ形で読み戻す。JV-Data 由来の値を含むので、置き場は ``reports/``（Git 対象外）。"""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def write(self, table: pd.DataFrame) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(self._path, index=False, encoding=ENCODING)

    def read(self) -> pd.DataFrame:
        """レースID・馬ID は文字列、開催日は日付にして読む。無ければ ``FileNotFoundError``。"""
        if not self._path.exists():
            raise FileNotFoundError(f"予測の CSV がありません: {self._path}（先に predict_all.py を実行してください）")
        return pd.read_csv(self._path, encoding=ENCODING, dtype=_TEXT_COLUMNS, parse_dates=[RACE_DATE])
