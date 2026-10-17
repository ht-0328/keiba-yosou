"""決まりで決めた消（危険な人気馬）の表を読む。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from 印の成績.favorite_danger_judge import COLUMNS

#: ファイルに要る列（人気馬1頭 = 1行）。
REQUIRED: tuple[str, ...] = ("race_id", "horse_id", "favorite_band", "is_danger")


class DangerFlagFile:
    """モデルの確率でなく、決まり（サインに当てはまったら消 など）で決めた消の表を、``FavoriteDangerJudge.judge`` の戻り値と
    同じ形（列は ``COLUMNS``）にして読む。

    ファイルは pickle で、列は ``REQUIRED``（race_id・horse_id・人気帯・消にするか）。1レースに消が何頭いてもよい
    （人気帯や1レース1頭の決まりは当てない）。確率と線の列（``out_probability``・``market_out``・``danger_score``・``danger_line``）は
    無いので空にし、``over_line``（人気帯ごとの表で「線以上」に数える）は消にするかと同じにする。
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> pd.DataFrame:
        if not self.path.is_file():
            raise FileNotFoundError(f"消の表がありません: {self.path}")
        table = pd.read_pickle(self.path)
        missing = [column for column in REQUIRED if column not in table.columns]
        if missing:
            raise ValueError(f"消の表の形が違います（無い列: {', '.join(missing)}）: {self.path}")
        flags = table[list(REQUIRED)].astype({"race_id": str, "horse_id": str})
        flags["is_danger"] = flags["is_danger"].astype(bool)
        blank = {column: np.nan for column in ("out_probability", "market_out", "danger_score", "danger_line")}
        return flags.assign(**blank, over_line=flags["is_danger"])[list(COLUMNS)].reset_index(drop=True)
