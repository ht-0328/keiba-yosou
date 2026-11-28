"""確率を直すモデルの学習に使う、1頭1行の表を作る（予測・確定オッズ・払戻・事実表をつなぐ）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from yosou.shared.win_correction import FACT_COLUMNS, QUINELLA_TOP2, QuinellaTop2

#: 表の列。
RACE_ID, RACE_DATE, YEAR, HORSE_NO, WON = "race_id", "race_date", "year", "horse_no", "won"


@dataclass(frozen=True)
class TrainingTable:
    """``win`` と ``top3`` は学習に使っていない期間の予測（``PredictionFile.load`` の形。列 ``race_id``・``race_date``・``horse_no``・``probability``・
    ``period``。テスト期間の行だけ使う）。``win_odds``・``place_odds``・``quinella_odds`` は確定オッズ（``FinalOddsRepository`` の形。列 ``race_id``・
    ``combo``・``odds``、複勝は ``odds_high`` も）、``win_payouts`` は単勝の払戻（``race_id``・``combo``・``yen``）、``facts`` は事実表の行
    （``race_id``・``horse_no`` と ``FACT_COLUMNS``）。

    ``build`` は、1着の予測があり、単勝・複勝のオッズと馬連から見た率がそろう馬だけの表（列は ``WinCorrectionFeatures`` の入力の列と
    ``race_date``・``year``・``won``（1着か））。単勝・複勝のオッズが欠ける馬がいるレースは丸ごと外す（レースで合計をそろえる率が狂うため）。
    """

    win: pd.DataFrame
    top3: pd.DataFrame
    win_odds: pd.DataFrame
    place_odds: pd.DataFrame
    quinella_odds: pd.DataFrame
    win_payouts: pd.DataFrame
    facts: pd.DataFrame

    def build(self) -> pd.DataFrame:
        horses = _tested(self.win, "win_probability").merge(_tested(self.top3, "probability").drop(columns=RACE_DATE), on=[RACE_ID, HORSE_NO])
        horses = horses.merge(_by_horse(self.win_odds, {"odds": "win_odds"}), on=[RACE_ID, HORSE_NO], how="left")
        horses = horses.merge(_by_horse(self.place_odds, {"odds": "place_odds_low", "odds_high": "place_odds_high"}), on=[RACE_ID, HORSE_NO], how="left")
        horses = horses.merge(QuinellaTop2().of(self.quinella_odds.assign(race_id=self.quinella_odds[RACE_ID].astype(str))),
                              on=[RACE_ID, HORSE_NO], how="left")
        winners = _by_horse(self.win_payouts, {"yen": "win_yen"})
        horses = horses.merge(winners, on=[RACE_ID, HORSE_NO], how="left")
        facts = self.facts.assign(race_id=self.facts[RACE_ID].astype(str), horse_no=self.facts[HORSE_NO].astype(int))
        horses = horses.merge(facts[[RACE_ID, HORSE_NO, *[c for c in FACT_COLUMNS if c in facts.columns]]], on=[RACE_ID, HORSE_NO], how="left")
        incomplete = horses.loc[horses[["win_odds", "place_odds_low", QUINELLA_TOP2]].isna().any(axis=1), RACE_ID].unique()
        horses = horses[~horses[RACE_ID].isin(incomplete)]
        horses = horses.assign(**{WON: (horses["win_yen"].fillna(0) > 0).astype(int), YEAR: horses[RACE_DATE].str[:4].astype(int)})
        return horses.drop(columns="win_yen").sort_values([RACE_ID, HORSE_NO]).reset_index(drop=True)


def _tested(predictions: pd.DataFrame, name: str) -> pd.DataFrame:
    """テスト期間の行の、レースID・開催日・馬番・確率（列の名前は ``name``）。"""
    tested = predictions[predictions["period"] == "テスト"]
    return pd.DataFrame({RACE_ID: tested[RACE_ID].astype(str), RACE_DATE: pd.to_datetime(tested[RACE_DATE]).dt.strftime("%Y-%m-%d"),
                         HORSE_NO: tested[HORSE_NO].astype(int), name: tested["probability"].astype(float)})


def _by_horse(frame: pd.DataFrame, renames: dict[str, str]) -> pd.DataFrame:
    """組番（馬番の2桁）の表を、馬番ごとの1行にする（同着で同じ馬番が2行あれば大きいほう）。"""
    keyed = frame.assign(race_id=frame[RACE_ID].astype(str), horse_no=frame["combo"].astype(int))
    return keyed.groupby([RACE_ID, HORSE_NO], as_index=False)[list(renames)].max().rename(columns=renames)
