"""基準のページを数える、1行 = 1出走の表を作る（出走に数える馬を選び、着順・払戻・コースの単位を付ける）。"""

from __future__ import annotations

import pandas as pd

from 共通 import codes

from 成績集計.repository.payout_repository import PLACE, WIN

#: 出走に数えない異常区分（1 出走取消・2 発走除外・3 競走除外）。JV-Data コード表 2101。
NOT_STARTED: tuple[str, ...] = ("1", "2", "3")
#: 出走したが着順が付かない異常区分（4 競走中止・5 失格）。出走して馬券外と数える。
NO_PLACING: tuple[str, ...] = ("4", "5")
#: 馬場状態が分からないときの表示。
UNKNOWN_GOING = "不明"
#: 単勝オッズの帯（倍）。各値を「その値未満」の境目にする。見やすさで決めた区切り。
ODDS_EDGES: tuple[float, ...] = (1.5, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0, 100.0)
ODDS_LABELS: tuple[str, ...] = ("1.0〜1.4倍", "1.5〜1.9倍", "2.0〜2.9倍", "3.0〜4.9倍", "5.0〜9.9倍", "10〜19.9倍",
                                "20〜49.9倍", "50〜99.9倍", "100倍以上")
SEX_ORDER: tuple[str, ...] = ("牡", "牝", "セン")
_RUN_KEY = ["rid", "horse_no"]


class ReferenceRuns:
    """元DB から読んだ出走（``FinalRunnerRepository``）と払戻（``PayoutRepository``）を、数える形に並べる。

    付ける列: ``first``・``second``・``third``（確定着順が 1・2・3 か）、``win_yen``・``place_yen``（100円あたりの払戻。
    外れは 0）、``surface``（芝・ダート・障害）、``course``（トラックコードの名前）、``going``（良〜不良）、``race_date``、
    ``odds_band``（単勝オッズの帯）、``mixed_sex``（牡・セン と牝が混ざったレースだけの性別。ほかは空）、
    ``mixed_age``（年齢が混ざったレースだけの馬齢。ほかは空）。
    馬場状態は、ダートのコースならダートの、芝と障害なら芝の馬場状態（芝が空ならダート）。
    """

    def build(self, runners: pd.DataFrame, payouts: pd.DataFrame) -> pd.DataFrame:
        runs = runners[~runners["abnormal"].isin(NOT_STARTED)].reset_index(drop=True)
        placing = runs["finish"].where(~runs["abnormal"].isin(NO_PLACING))
        surface = runs["track_code"].map(codes.surface_of)
        going_code = runs["dirt_going"].where(surface.eq("ダート") | runs["turf_going"].eq("0"), runs["turf_going"])
        return runs.assign(
            first=placing.eq(1).fillna(False), second=placing.eq(2).fillna(False), third=placing.eq(3).fillna(False),
            win_yen=self._paid(runs, payouts, WIN), place_yen=self._paid(runs, payouts, PLACE),
            surface=surface, course=runs["track_code"].map(codes.TRACK_NAMES),
            going=going_code.map(codes.TRACK_CONDITION).fillna(UNKNOWN_GOING),
            race_date=runs["race_day"].str[:4] + "-" + runs["race_day"].str[4:6] + "-" + runs["race_day"].str[6:],
            odds_band=self._odds_band(runs["odds_tenths"]),
            mixed_sex=self._mixed_sex(runs), mixed_age=self._mixed_age(runs),
        )

    @staticmethod
    def _odds_band(tenths: pd.Series) -> pd.Series:
        """単勝オッズ（10倍の整数。0 は無し）の帯。順序付きのカテゴリにして、表を帯の順に並べる。"""
        odds = tenths.where(tenths.gt(0)) / 10
        edges = [0.0, *ODDS_EDGES, float("inf")]
        return pd.cut(odds, bins=edges, labels=list(ODDS_LABELS), right=False)

    @staticmethod
    def _mixed_sex(runs: pd.DataFrame) -> pd.Series:
        """牡・セン と牝が同じレースにいるときだけ性別の名前。牝馬限定戦などは比べる相手がいないので空にする。"""
        sex = runs["sex_code"].map(codes.SEX_NAMES)
        is_filly = sex.eq("牝")
        mixed = is_filly.groupby(runs["rid"]).transform("any") & (~is_filly).groupby(runs["rid"]).transform("any")
        return pd.Categorical(sex.where(mixed), categories=list(SEX_ORDER), ordered=True)

    @staticmethod
    def _mixed_age(runs: pd.DataFrame) -> pd.Series:
        """年齢が2つ以上あるレースだけの馬齢。2歳戦・3歳限定戦は全馬が同じ年齢なので空にする。"""
        mixed = runs["age"].groupby(runs["rid"]).transform("nunique").gt(1)
        return runs["age"].where(mixed)

    @staticmethod
    def _paid(runs: pd.DataFrame, payouts: pd.DataFrame, kind: str) -> pd.Series:
        """券種 ``kind`` の、出走ごとの払戻（円）。同じ馬番の払戻が2行あれば足す。"""
        rows = payouts[payouts["kind"].eq(kind) & payouts["horse_no"].gt(0) & payouts["yen"].gt(0)]
        paid = rows.groupby(_RUN_KEY, as_index=False)["yen"].sum()
        joined = runs[_RUN_KEY].merge(paid, on=_RUN_KEY, how="left")
        return joined["yen"].fillna(0).astype("int64")
