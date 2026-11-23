"""ばんえいの出走の表（確定した成績＋予想するレースの出馬表）から、レース前に分かる材料だけの特徴量を作る。

材料にするのは、そりの重さ・馬体重・馬場水分・近走の着順とタイム・過去走のときの人気とオッズ・騎手と調教師の直近1年の成績・クラス（賞金）。
今回のレースのオッズと人気は材料にしない（買い目を決める発走10分前のオッズは、確定までに大きく動くため）。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 過去走から作る値（1走ごと）。近走の1〜3走前の値と、近3・5・10走の平均にする。
_PAST = ("fin_ratio", "tdiff", "spd", "pop", "logodds", "top3", "win", "pop_gap")
#: レースの中での順位と、レースの平均との差も材料にする値。
_RELATIVE = ("spd_m3", "spd_m5", "spd_max5", "spd_l1", "fin_ratio_m3", "fin_ratio_m5", "tdiff_m3", "logodds_m3", "logodds_l1", "pop_m3",
             "load", "bw", "load_per_bw", "career_top3_rate", "jockey_top3", "jockey_beat", "trainer_top3", "prize1_prev", "spd_band",
             "load_change", "days_since", "age")
_BASE = ("load", "bw", "bw_change", "bw_vs_m5", "load_per_bw", "water", "age", "sex_code", "umaban", "gate_ratio", "heads", "race_no", "month",
         "prize_log", "weight_rule_code", "kind_code", "grade_code", "weather", "starts", "career_win_rate", "career_top3_rate", "days_since",
         "days_since2", "load_change", "load_change2", "water_change", "water_prev", "prize_ratio", "jockey_changed", "pair_n", "pair_top3",
         "fin_ratio_band", "spd_band", "n_band", "fin_ratio_wet", "fin_ratio_dry", "spd_wet", "spd_dry", "spd_max5", "spd_max10", "spd_sd10",
         "heads_prev", "jockey_n", "jockey_win", "jockey_top3", "jockey_beat", "trainer_n", "trainer_win", "trainer_top3", "trainer_beat")
#: 出走しなかった馬の異常区分（取消・発走除外・競走除外）と、読めない区分。
_NOT_STARTED = (1, 2, 3, 7)
#: 馬場の軽い・重いを分ける馬場水分（%）。
_WET_WATER = 2.0
#: 勝ち馬との差（秒）の上限。完走しなかった馬もこの値にする。
_MAX_TIME_DIFF = 120.0
#: そりの重さ 1kg あたりの対数タイムの傾きを決める期間の終わり（それより後の年の答えを使わない）。
_SLOPE_UNTIL_YEAR = 2018
#: 人の成績を見る期間。
_PERSON_WINDOW = "365D"


class BaneiFeatureBuilder:
    @staticmethod
    def names() -> list[str]:
        """予想のモデルに渡す材料の名前（順番も決まり）。"""
        names = list(_BASE)
        for column in _PAST:
            names += [f"{column}_l1", f"{column}_l2", f"{column}_l3", f"{column}_m3", f"{column}_m5", f"{column}_m10"]
        for column in _RELATIVE:
            names += [f"{column}_rk", f"{column}_df"]
        return names

    def build(self, runs: pd.DataFrame) -> pd.DataFrame:
        """1行 = 1頭の出走。材料の列（``names()``）と、答えの列（win・top3 など。出馬表の行では意味を持たない）を足す。"""
        frame = self._race_values(runs)
        frame = self._history(frame)
        frame = self._person_form(frame, "jockey")
        frame = self._person_form(frame, "trainer")
        frame = self._race_context(frame)
        return frame.sort_values(["date", "race_no", "umaban"]).reset_index(drop=True)

    @staticmethod
    def _race_values(runs: pd.DataFrame) -> pd.DataFrame:
        """1走ごとの結果の値（着順の割合・勝ち馬との差・その日の中での速さ）。"""
        frame = runs[~runs["abnormal"].isin(_NOT_STARTED)].copy()
        frame["heads"] = frame.groupby("rid")["umaban"].transform("count")
        finished = frame["abnormal"].eq(0) & frame["finish"].gt(0)
        frame["finish_use"] = np.where(finished, frame["finish"], frame["heads"])
        frame["fin_ratio"] = (frame["finish_use"] - 1) / (frame["heads"] - 1).clip(lower=1)
        frame["win"] = (finished & frame["finish"].eq(1)).astype(float)
        frame["top3"] = (finished & frame["finish"].le(3)).astype(float)
        frame.loc[~finished, "time"] = np.nan
        best = frame.groupby("rid")["time"].transform("min")
        frame["tdiff"] = (frame["time"] - best).clip(upper=_MAX_TIME_DIFF).fillna(_MAX_TIME_DIFF)
        log_time = np.log(frame["time"])
        day = frame.groupby("date")
        time_gap = log_time - log_time.groupby(frame["date"]).transform("mean")
        load_gap = frame["load"] - day["load"].transform("mean")
        old = frame["date"].dt.year.le(_SLOPE_UNTIL_YEAR) & time_gap.notna()
        slope = float((time_gap[old] * load_gap[old]).sum() / (load_gap[old] ** 2).sum())
        speed = -(time_gap - slope * load_gap)
        frame["spd"] = speed.fillna(speed[old].quantile(0.02))
        frame["logodds"] = np.log(frame["win_odds"].where(frame["win_odds"] > 0))
        frame["pop_gap"] = (frame["pop"] - frame["finish_use"]) / frame["heads"]
        return frame

    @staticmethod
    def _history(frame: pd.DataFrame) -> pd.DataFrame:
        """馬ごとの過去走から近走の値を作る（今回の走は入れない）。"""
        frame = frame.sort_values(["hid", "date", "race_no"]).reset_index(drop=True)
        key = frame["hid"]
        horse = frame.groupby("hid", sort=False)
        new: dict[str, pd.Series] = {}

        def rolled(series: pd.Series, window: int, how: str, minimum: int = 1) -> pd.Series:
            rolling = series.groupby(key, sort=False).rolling(window, min_periods=minimum)
            return getattr(rolling, how)().reset_index(level=0, drop=True)

        for column in _PAST:
            last = horse[column].shift(1)
            new[f"{column}_l1"] = last
            new[f"{column}_l2"] = horse[column].shift(2)
            new[f"{column}_l3"] = horse[column].shift(3)
            for window in (3, 5, 10):
                new[f"{column}_m{window}"] = rolled(last, window, "mean")
        last_speed = horse["spd"].shift(1)
        new["spd_max5"] = rolled(last_speed, 5, "max")
        new["spd_max10"] = rolled(last_speed, 10, "max")
        new["spd_sd10"] = rolled(last_speed, 10, "std", 3)
        new["starts"] = horse.cumcount()
        new["career_win"] = horse["win"].cumsum() - frame["win"]
        new["career_top3"] = horse["top3"].cumsum() - frame["top3"]
        new["days_since"] = (frame["date"] - horse["date"].shift(1)).dt.days
        new["days_since2"] = (horse["date"].shift(1) - horse["date"].shift(2)).dt.days
        for column in ("load", "water", "prize1", "jockey", "heads"):
            new[f"{column}_prev"] = horse[column].shift(1)
        new["load_prev2"] = horse["load"].shift(2)
        new["bw_m5"] = rolled(horse["bw"].shift(1), 5, "mean")
        for name, mask in (("wet", frame["water"] >= _WET_WATER), ("dry", frame["water"] < _WET_WATER)):
            count = mask.astype(float).groupby(key, sort=False).cumsum() - mask.astype(float)
            new[f"n_{name}"] = count
            for column in ("fin_ratio", "spd"):
                value = frame[column].where(mask).fillna(0)
                total = value.groupby(key, sort=False).cumsum() - value
                new[f"{column}_{name}"] = total / count.where(count > 0)
        pair = frame.groupby(["hid", "jockey"], sort=False)
        new["pair_n"] = pair.cumcount()
        new["pair_top3"] = (pair["top3"].cumsum() - frame["top3"]) / new["pair_n"].where(new["pair_n"] > 0)
        frame = pd.concat([frame, pd.DataFrame(new)], axis=1)
        starts = frame["starts"].where(frame["starts"] > 0)
        frame["career_win_rate"] = frame["career_win"] / starts
        frame["career_top3_rate"] = frame["career_top3"] / starts
        frame["load_change"] = frame["load"] - frame["load_prev"]
        frame["load_change2"] = frame["load_prev"] - frame["load_prev2"]
        frame["water_change"] = frame["water"] - frame["water_prev"]
        frame["prize_ratio"] = np.log(frame["prize1"].clip(lower=1) / frame["prize1_prev"].clip(lower=1))
        frame["jockey_changed"] = (frame["jockey"] != frame["jockey_prev"]).astype(float).where(frame["jockey_prev"].notna())
        frame["bw_vs_m5"] = frame["bw"] - frame["bw_m5"]
        frame["load_per_bw"] = frame["load"] / frame["bw"]
        wet_now = frame["water"] >= _WET_WATER
        frame["fin_ratio_band"] = np.where(wet_now, frame["fin_ratio_wet"], frame["fin_ratio_dry"])
        frame["spd_band"] = np.where(wet_now, frame["spd_wet"], frame["spd_dry"])
        frame["n_band"] = np.where(wet_now, frame["n_wet"], frame["n_dry"])
        return frame.drop(columns=["jockey_prev"])

    @staticmethod
    def _person_form(frame: pd.DataFrame, person: str) -> pd.DataFrame:
        """騎手・調教師の直近1年（今日より前）の成績。``beat`` は、勝った数が確定オッズから見た見込みをどれだけ上回ったか。"""
        expected = (0.8 / frame["win_odds"].where(frame["win_odds"] > 0)).fillna(0)
        work = frame.assign(_beat=frame["win"] - expected)
        daily = work.groupby([person, "date"]).agg(n=("win", "size"), w=("win", "sum"), t=("top3", "sum"), b=("_beat", "sum")).reset_index()
        daily = daily.sort_values([person, "date"])
        rolled = daily.set_index("date").groupby(person)[["n", "w", "t", "b"]].rolling(_PERSON_WINDOW, closed="left").sum().reset_index()
        count = rolled["n"].where(rolled["n"] > 0)
        rolled[f"{person}_n"] = rolled["n"]
        rolled[f"{person}_win"] = rolled["w"] / count
        rolled[f"{person}_top3"] = rolled["t"] / count
        rolled[f"{person}_beat"] = rolled["b"] / count
        keep = [person, "date", f"{person}_n", f"{person}_win", f"{person}_top3", f"{person}_beat"]
        return frame.merge(rolled[keep], on=[person, "date"], how="left")

    @classmethod
    def _race_context(cls, frame: pd.DataFrame) -> pd.DataFrame:
        frame["month"] = frame["date"].dt.month
        frame["gate_ratio"] = (frame["umaban"] - 1) / (frame["heads"] - 1).clip(lower=1)
        frame["prize_log"] = np.log(frame["prize1"].clip(lower=1))
        for column in ("sex", "weight_rule", "kind", "grade"):
            frame[f"{column}_code"] = frame[column].map(cls._code)
        race = frame.groupby("rid")
        extra: dict[str, pd.Series] = {}
        for column in _RELATIVE:
            extra[f"{column}_rk"] = race[column].rank(pct=True)
            extra[f"{column}_df"] = frame[column] - race[column].transform("mean")
        return pd.concat([frame, pd.DataFrame(extra)], axis=1)

    @staticmethod
    def _code(text: object) -> float:
        """コードの文字列を数にする（数字はその数、英字は文字の番号、空は −1）。データが増えても同じ値になる。"""
        value = str(text or "").strip()
        if not value:
            return -1.0
        return float(int(value)) if value.isdigit() else float(ord(value[0]))
