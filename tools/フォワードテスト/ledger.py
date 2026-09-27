"""フォワードテストの記録（買ったつもりの買い目と、予想したレース）を CSV で読み書きする。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

#: 買い目の記録の列。精算の列（払戻・精算・精算時刻）は、結果が出てから埋める。
BUY_COLUMNS: tuple[str, ...] = (
    "記録時刻", "開催日", "race_id", "発走", "場", "R", "レース名", "馬番", "馬名", "人気", "単勝オッズ",
    "複勝オッズ（最低）", "3着以内の確率", "期待値", "線", "モデル", "オッズの発表時刻", "賭け金", "払戻", "精算", "精算時刻",
)
#: 予想したレースの記録の列。買い目が無かったレースや、予想できなかったレースも残す。
RACE_COLUMNS: tuple[str, ...] = (
    "記録時刻", "開催日", "race_id", "発走", "場", "R", "モデル", "オッズの発表時刻", "買い目の数", "予想できない理由",
)
#: 精算の状態。空は未精算。
SETTLED, REFUNDED = "済", "返還"
_BUYS, _RACES = "買い目.csv", "予想したレース.csv"


class Ledger:
    """``folder`` の下に、買い目（``買い目.csv``）と予想したレース（``予想したレース.csv``）を貯める。

    人が手で書き足すものは無い。フォワードテストの道具が追記し、結果が出たら精算の列を埋める。
    文字コードは Excel でも開けるよう BOM 付きの UTF-8。
    """

    def __init__(self, folder: Path) -> None:
        self._folder = Path(folder)

    @property
    def folder(self) -> Path:
        return self._folder

    def buys(self) -> pd.DataFrame:
        return self._read(_BUYS, BUY_COLUMNS)

    def races(self) -> pd.DataFrame:
        return self._read(_RACES, RACE_COLUMNS)

    def recorded_races(self) -> set[str]:
        """予想を記録済みのレースの鍵。同じレースを2回記録しないために使う。"""
        return set(self.races()["race_id"])

    def append(self, buys: list[dict[str, object]], race: dict[str, object]) -> None:
        """1レースぶんの買い目と、そのレースの記録を足す。"""
        self._write(_BUYS, pd.concat([self.buys(), self._frame(buys, BUY_COLUMNS)], ignore_index=True))
        self._write(_RACES, pd.concat([self.races(), self._frame([race], RACE_COLUMNS)], ignore_index=True))

    def replace_buys(self, buys: pd.DataFrame) -> None:
        """精算の列を埋めた買い目で置き換える。"""
        self._write(_BUYS, buys[list(BUY_COLUMNS)])

    def _read(self, name: str, columns: tuple[str, ...]) -> pd.DataFrame:
        path = self._folder / name
        if not path.is_file():
            return pd.DataFrame(columns=list(columns), dtype=object)
        return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")

    def _write(self, name: str, frame: pd.DataFrame) -> None:
        self._folder.mkdir(parents=True, exist_ok=True)
        frame.to_csv(self._folder / name, index=False, encoding="utf-8-sig")

    @staticmethod
    def _frame(rows: list[dict[str, object]], columns: tuple[str, ...]) -> pd.DataFrame:
        frame = pd.DataFrame(rows, columns=list(columns))
        return frame.astype(object).where(frame.notna(), "").astype(str)
