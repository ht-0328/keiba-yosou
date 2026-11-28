"""1頭1行の表（予想の1着の確率・確定の単勝オッズ・確定の単勝の払戻・締め切り前の単勝オッズ）を作る。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 的中実績の公開ルール.analysis.snapshot_probability import SnapshotProbability


@dataclass(frozen=True)
class HorseTable:
    """``predictions`` は今の本番の当日の予想と同じ作りの、学習に使っていない期間の1着の予測（研究「既存モデルの改善」の
    ``graded_race_day/odds_move-win.pkl``。列 ``レースID``・``開催日``・``馬番``・``確率``・``期間``）。
    ``final_odds`` は確定の単勝オッズ（``race_id``・``combo``・``odds``）、``payouts`` は単勝の払戻（``race_id``・``combo``・``yen``）、
    ``snapshot_odds`` は締め切り前の単勝オッズ（``race_id``・``horse_no``・``odds``）。

    ``final`` は確定オッズの時点の表（``p`` は予測の確率をレースで合計 1 にそろえたもの）、``snapshot`` は締め切り前のオッズのあるレースだけの、
    その時点の表（``p`` は ``SnapshotProbability`` で近づけた確率、``odds`` は締め切り前の単勝オッズ）。どちらも列は
    ``race_id``・``day``・``year``・``horse_no``・``p``・``odds``・``win_pay``（確定の単勝の払戻。外れは 0）。
    """

    predictions: pd.DataFrame
    final_odds: pd.DataFrame
    payouts: pd.DataFrame
    snapshot_odds: pd.DataFrame

    def final(self) -> pd.DataFrame:
        test = self.predictions[self.predictions["期間"] == "テスト"]
        horses = pd.DataFrame({"race_id": test["レースID"].astype(str), "day": pd.to_datetime(test["開催日"]).dt.strftime("%Y-%m-%d"),
                               "horse_no": test["馬番"].astype(int), "p": test["確率"].astype(float)})
        horses = horses.merge(_by_horse(self.final_odds, "odds", "odds"), on=["race_id", "horse_no"])
        horses = horses.merge(_by_horse(self.payouts, "yen", "win_pay"), on=["race_id", "horse_no"], how="left").fillna({"win_pay": 0.0})
        horses["p"] = horses["p"] / horses.groupby("race_id")["p"].transform("sum")
        return horses.assign(year=horses["day"].str[:4].astype(int))

    def snapshot(self) -> pd.DataFrame:
        snapshot = self.snapshot_odds.assign(race_id=self.snapshot_odds["race_id"].astype(str)).rename(columns={"odds": "snapshot_odds"})
        horses = self.final().merge(snapshot[["race_id", "horse_no", "snapshot_odds"]], on=["race_id", "horse_no"], how="left")
        complete = horses.groupby("race_id")["snapshot_odds"].transform(lambda odds: odds.notna().all())
        horses = horses[complete].copy()
        horses["p"] = SnapshotProbability().of(horses)
        return horses.drop(columns="odds").rename(columns={"snapshot_odds": "odds"})


def _by_horse(frame: pd.DataFrame, value: str, name: str) -> pd.DataFrame:
    """組番（馬番の2桁）の表を、馬番ごとの1行にする（同着で同じ馬番が2行あれば足す）。"""
    keyed = pd.DataFrame({"race_id": frame["race_id"].astype(str), "horse_no": frame["combo"].astype(int), name: frame[value].astype(float)})
    return keyed.groupby(["race_id", "horse_no"], as_index=False)[name].sum()
