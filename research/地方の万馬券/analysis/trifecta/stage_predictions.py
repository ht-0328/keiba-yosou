"""段ごとの予想（②危険な人気馬・③穴馬・④荒れ具合）の予測の表を読み、走者の表に差と荒れ具合の列を足す。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ..payout_band import PAYOUT_BANDS

#: 走者の表に足す列。②③は「その段のモデルの確率 − オッズから見た同じ確率」（人気馬以外・穴馬以外は欠損値）。
DANGER_EDGE, LONGSHOT_EDGE = "danger_edge", "longshot_edge"
#: ④の列（券種の鍵 trifecta・trio ごと）。大荒れ以上の確率・中荒れ以上の確率・いちばん高いクラス（固い・中荒れ・大荒れ・超荒れ）。
BIG_OR_MORE, MID_OR_MORE, STAGE_UPSET = "big_or_more", "mid_or_more", "stage_upset"
TRIFECTA_KEY, TRIO_KEY = "trifecta", "trio"
#: ファイルの名前（``research/地方の万馬券/stages.py`` が書く）。
DANGER_FILE, LONGSHOT_FILE = "危険な人気馬.pkl", "穴馬.pkl"
UPSET_FILES: dict[str, str] = {TRIFECTA_KEY: "荒れ具合-trifecta.pkl", TRIO_KEY: "荒れ具合-trio.pkl"}
#: 予測の表の列（``band_study``・``upset_study`` が書く）。
_P_MODEL, _P_MARKET, _BIG, _MID = "p_model", "p_market", "大荒れ以上の確率", "中荒れ以上の確率"


def upset_column(name: str, key: str) -> str:
    """券種の鍵ごとの④の列の名前（例: ``big_or_more_trifecta``）。"""
    return f"{name}_{key}"


@dataclass(frozen=True)
class StagePredictions:
    """``folder`` の予測の表を読んで走者の表（``race_id``・``horse_no``）に列を足す。無いファイルの列は欠損値（その段を使う買い方は何も買わない）。"""

    folder: Path

    def attach(self, runners: pd.DataFrame) -> pd.DataFrame:
        table = runners.copy()
        race_id = table["race_id"].astype("int64")
        for column, file in ((DANGER_EDGE, DANGER_FILE), (LONGSHOT_EDGE, LONGSHOT_FILE)):
            table[column] = self._edge(file, race_id, table["horse_no"]).to_numpy()
        for key, file in UPSET_FILES.items():
            upset = self._upset(file)
            for name in (BIG_OR_MORE, MID_OR_MORE, STAGE_UPSET):
                table[upset_column(name, key)] = race_id.map(upset[name]).to_numpy() if upset is not None else np.nan
        return table

    def _edge(self, file: str, race_id: pd.Series, horse_no: pd.Series) -> pd.Series:
        path = self.folder / file
        if not path.exists():
            return pd.Series(np.nan, index=race_id.index, dtype="float64")
        frame = pd.read_pickle(path)
        keyed = pd.DataFrame({"race_id": frame["race_id"].astype("int64"), "horse_no": pd.to_numeric(frame["horse_no"], errors="coerce").astype("int64"),
                              "edge": pd.to_numeric(frame[_P_MODEL], errors="coerce") - pd.to_numeric(frame[_P_MARKET], errors="coerce")})
        keyed = keyed.drop_duplicates(["race_id", "horse_no"]).set_index(["race_id", "horse_no"])["edge"]
        index = pd.MultiIndex.from_arrays([race_id.to_numpy(), pd.to_numeric(horse_no, errors="coerce").astype("int64").to_numpy()])
        return pd.Series(keyed.reindex(index).to_numpy(), index=race_id.index, dtype="float64")

    def _upset(self, file: str) -> pd.DataFrame | None:
        path = self.folder / file
        if not path.exists():
            return None
        frame = pd.read_pickle(path)
        probabilities = frame[list(PAYOUT_BANDS)].to_numpy(dtype="float64")
        return pd.DataFrame({
            BIG_OR_MORE: pd.to_numeric(frame[_BIG], errors="coerce").to_numpy(), MID_OR_MORE: pd.to_numeric(frame[_MID], errors="coerce").to_numpy(),
            STAGE_UPSET: np.asarray(PAYOUT_BANDS)[probabilities.argmax(axis=1)],
        }, index=frame["race_id"].astype("int64").to_numpy()).loc[lambda t: ~t.index.duplicated()]
