"""単勝オッズの4個と、馬連・複勝の支持の比を、締め切り前のオッズで作り直す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.feature.odds import TOP2_RATE, TOP3_RATE, WIN_RATE, MarketPlaces

#: 作り直す列（研究「既存モデルの改善」の表と同じ名前・同じ作り）。
QUINELLA_RATIO = "馬連から見た2着以内率と単勝の比（log）"
PLACE_RATIO = "複勝から見た3着以内率と単勝の比（log）"
ODDS_COLUMNS: tuple[str, ...] = ("単勝オッズ", "人気順位", "オッズから見た勝率", "オッズから見た3着以内率")
#: log を取るときの下限。
_FLOOR = 1e-6


class PreDeadlineOddsFeatures:
    """確定オッズで作った表の行の、オッズから作る列を、締め切り前の断面の値に置き換える。

    ``win_place`` は ``rid``・``horse_no``・``win_odds``・``place_odds_low``・``place_odds_high``、
    ``quinella`` は ``rid``・``horse_no``・``馬連から見た2着以内率``（研究「回収率100超」の締め切り前の読み出し）。
    1頭でも値が欠けるレースは、比べられないので落とす。3連単などは締め切り前の値が過去に無いので、作り直さない。
    """

    def rebuild(self, rows: pd.DataFrame, win_place: pd.DataFrame, quinella: pd.DataFrame) -> pd.DataFrame:
        snapshot = win_place.merge(quinella, on=["rid", "horse_no"], how="left")
        snapshot = snapshot.rename(columns={"rid": "レースID", "horse_no": "馬番"})
        frame = rows.drop(columns=[*ODDS_COLUMNS, QUINELLA_RATIO, PLACE_RATIO], errors="ignore")
        frame = frame.merge(snapshot, on=["レースID", "馬番"], how="left")
        frame = frame[~frame["レースID"].isin(self._incomplete(frame))].reset_index(drop=True)
        places = MarketPlaces().of(frame.rename(columns={"レースID": "race_id"})[["race_id", "win_odds"]])
        frame["単勝オッズ"] = frame["win_odds"]
        frame["人気順位"] = frame.groupby("レースID")["win_odds"].rank(method="min")
        frame["オッズから見た勝率"] = places[WIN_RATE].to_numpy()
        frame["オッズから見た3着以内率"] = places[TOP3_RATE].to_numpy()
        middle = 2.0 / (frame["place_odds_low"] + frame["place_odds_high"])
        place_share = middle / middle.groupby(frame["レースID"]).transform("sum")
        frame[PLACE_RATIO] = self._log_ratio(place_share, frame["オッズから見た3着以内率"])
        frame[QUINELLA_RATIO] = self._log_ratio(frame["馬連から見た2着以内率"], pd.Series(places[TOP2_RATE].to_numpy()))
        return frame

    @staticmethod
    def _incomplete(frame: pd.DataFrame) -> np.ndarray:
        needed = frame[["win_odds", "place_odds_low", "place_odds_high", "馬連から見た2着以内率"]]
        return frame.loc[needed.isna().any(axis=1) | (frame["win_odds"] <= 0), "レースID"].unique()

    @staticmethod
    def _log_ratio(support: pd.Series, base: pd.Series) -> np.ndarray:
        return np.log(support.clip(lower=_FLOOR).to_numpy() / base.clip(lower=_FLOOR).to_numpy())
