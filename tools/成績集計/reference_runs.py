"""基準のページを数える、1行 = 1出走の表を作る（出走に数える馬を選び、結果・払戻・レースの属性・前走・予想を付ける）。"""

from __future__ import annotations

import pandas as pd

from 共通 import codes

from 成績集計.reference_history import ReferenceHistory
from 成績集計.repository.payout_repository import PLACE, WIN

#: 出走に数えない異常区分（1 出走取消・2 発走除外・3 競走除外）。JV-Data コード表 2101。
NOT_STARTED: tuple[str, ...] = ("1", "2", "3")
#: 出走したが着順が付かない異常区分（4 競走中止・5 失格）。出走して馬券外と数える。
NO_PLACING: tuple[str, ...] = ("4", "5")
#: 馬体重・上がり3F の「無し」の値（仕様書の桁のまま 000・999）。
_MISSING_MEASURES: tuple[int, ...] = (0, 999)
#: 馬場状態が分からないときの表示。
UNKNOWN_GOING = "不明"
#: 血統の記録が無いときの名前。
UNKNOWN_PEDIGREE = "不明"
_PEDIGREE_COLUMNS = ("sire", "grandsire", "damsire")
_RUN_KEY = ["rid", "horse_no"]


class ReferenceRuns:
    """元DB から読んだ出走・払戻・血統・対戦型スコアを、数える形に並べる。期間 ``date_from``〜``date_to`` の出走だけを返す。

    付ける列（値。表の行の名前は ``ReferenceLabels`` が付ける）:
    ``placing``（確定着順。中止・失格は無し）、``first``・``second``・``third``、``win_yen``・``place_yen``（100円あたりの払戻）、
    ``surface``・``course``・``going``（馬場状態は、ダートのコースならダートの、芝と障害なら芝の。芝が空ならダート）、
    ``race_date``・``month``・``class_name``・``field_size``、``win_odds``・``last3f``・``last3f_rank``（レース内で速い順）、
    ``body_weight``・``weight_change``、``prev_finish``・``prev_popularity``・``interval_days``、
    ``sire``・``grandsire``・``damsire``、``dm_rank``（タイム型の順位）、``tm_score``・``tm_rank``（対戦型のスコアと、
    予想のある馬の中でスコアの高い順の順位）、``mixed_sex``・``mixed_age``（牡牝・年齢が混ざったレースか）。
    """

    def build(self, runners: pd.DataFrame, payouts: pd.DataFrame, pedigrees: pd.DataFrame, scores: pd.DataFrame,
              date_from: str | None, date_to: str | None) -> pd.DataFrame:
        started = self._started(runners)
        days = started["race_date"]
        in_period = days.ge(date_from or "") & days.le(date_to or "9999-99-99")
        runs = ReferenceHistory().add(started)[in_period].reset_index(drop=True)
        runs = runs.merge(pedigrees, on="horse_id", how="left").merge(self._ranked_scores(scores), on=_RUN_KEY, how="left")
        # 血統の記録が無い馬の父・父の父・母父は「不明」として1つの値に数える（騎手などと同じく、空の値も表に出す）
        runs = runs.fillna({name: UNKNOWN_PEDIGREE for name in _PEDIGREE_COLUMNS})
        return self._race_columns(runs.assign(win_yen=self._paid(runs, payouts, WIN), place_yen=self._paid(runs, payouts, PLACE)))

    def _started(self, runners: pd.DataFrame) -> pd.DataFrame:
        runs = runners[~runners["abnormal"].isin(NOT_STARTED)].reset_index(drop=True)
        runs = runs.assign(**{name: runs[name].where(runs[name].gt(0)) for name in ("horse_no", "frame_no", "popularity")})
        placing = runs["finish"].where(~runs["abnormal"].isin(NO_PLACING) & runs["finish"].gt(0))
        race_date = runs["race_day"].str[:4] + "-" + runs["race_day"].str[4:6] + "-" + runs["race_day"].str[6:]
        return runs.assign(placing=placing, race_date=race_date, day=pd.to_datetime(runs["race_day"], format="%Y%m%d"))

    @staticmethod
    def _ranked_scores(scores: pd.DataFrame) -> pd.DataFrame:
        """対戦型の順位: 予想のある馬の中で、スコアの高い順（同じスコアは同じ順位）。"""
        return scores.assign(tm_rank=scores.groupby("rid")["tm_score"].rank(method="min", ascending=False))

    @staticmethod
    def _paid(runs: pd.DataFrame, payouts: pd.DataFrame, kind: str) -> pd.Series:
        """券種 ``kind`` の、出走ごとの払戻（円）。同じ馬番の払戻が2行あれば足す。"""
        rows = payouts[payouts["kind"].eq(kind) & payouts["horse_no"].gt(0) & payouts["yen"].gt(0)]
        paid = rows.groupby(_RUN_KEY, as_index=False)["yen"].sum()
        joined = runs[_RUN_KEY].merge(paid, on=_RUN_KEY, how="left")
        return joined["yen"].fillna(0).astype("int64").to_numpy()

    @staticmethod
    def _race_columns(runs: pd.DataFrame) -> pd.DataFrame:
        surface = runs["track_code"].map(codes.surface_of)
        going_code = runs["dirt_going"].where(surface.eq("ダート") | runs["turf_going"].eq("0"), runs["turf_going"])
        body_weight = runs["body_weight_raw"].where(~runs["body_weight_raw"].isin(_MISSING_MEASURES))
        last3f = (runs["last3f_tenths"].where(~runs["last3f_tenths"].isin(_MISSING_MEASURES)) / 10)
        is_filly = runs["sex_code"].eq("2")
        by_race = runs["rid"]
        return runs.assign(
            first=runs["placing"].eq(1), second=runs["placing"].eq(2), third=runs["placing"].eq(3),
            surface=surface, course=runs["track_code"].map(codes.TRACK_NAMES), going=going_code.map(codes.TRACK_CONDITION).fillna(UNKNOWN_GOING),
            month=runs["race_day"].str[4:6].astype(int),
            class_name=[codes.class_name(c, g) for c, g in zip(runs["condition_code"], runs["grade_code"])],
            field_size=runs["starters"].where(runs["starters"].gt(0), runs["entries"].where(runs["entries"].gt(0))),
            win_odds=runs["odds_tenths"].where(runs["odds_tenths"].gt(0)) / 10,
            last3f=last3f, last3f_rank=last3f.groupby(by_race).rank(method="min"),
            body_weight=body_weight, weight_change=_weight_change(runs, body_weight),
            dm_rank=runs["dm_rank_raw"].where(runs["dm_rank_raw"].gt(0)),
            mixed_sex=is_filly.groupby(by_race).transform("any") & (~is_filly).groupby(by_race).transform("any"),
            mixed_age=runs["age"].groupby(by_race).transform("nunique").gt(1),
        )


def _weight_change(runs: pd.DataFrame, body_weight: pd.Series) -> pd.Series:
    """馬体重の増減（kg）。符号が + なら増、- なら減。符号が無く差が 0 で馬体重があれば 0。ほかは無し。"""
    diff = runs["weight_diff"]
    unsigned_zero = diff.eq(0) & body_weight.notna()
    signed = diff.where(runs["weight_sign"].eq("+"), -diff.where(runs["weight_sign"].eq("-")))
    return signed.where(signed.notna(), diff.where(unsigned_zero))
