"""事実表とスピード指数から、1行 = 1頭の出走の学習用の表を作る。オッズと人気は材料に入れない。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .ability_features import AbilityFeatures
from .past_run_features import PastRunFeatures
from .race_relative import RaceRelative
from .recent_record_rates import RecentRecordRates
from .track_record_rates import TrackRecordRates

#: 事実表から、そのまま材料にする列（レースの条件・今回の馬の条件・今回より前の累積）。
CONTEXT_COLUMNS: tuple[str, ...] = (
    "distance_m", "field_size", "class_order", "age", "sex_order", "carried", "body_weight", "weight_change",
    "frame_no", "interval_days", "condition_order", "surface_order", "month", "runs_before", "wins_before",
    "lead_runs_before", "course_runs_before", "course_wins_before", "course_places_before", "venue_wins_before",
    "dist_wins_before", "cond_places_before", "same_race_runs_before", "same_race_wins_before",
    "best_time_unit_rank", "best_time_dist_rank",
)
#: JRA-VAN のマイニング予想の列（オッズではないが、よその予想なので、入れるかどうかを分けて確かめる）。
MINING_COLUMNS: tuple[str, ...] = ("dm_rank", "tm_rank", "tm_score")
#: 成績を数える区分（作る列の名前の頭 → 区分の列）。
RECORD_GROUPS: dict[str, list[str]] = {
    "騎手": ["jockey_code"], "調教師": ["trainer_code"], "父": ["sire"], "母父": ["damsire"],
    "父×芝ダ": ["sire", "surface"], "騎手×競馬場": ["jockey_code", "venue_code"],
    "馬主": ["owner"], "生産者": ["breeder"], "母": ["dam"], "調教師×距離": ["trainer_code", "distance_m"],
    "枠の傾向": ["venue_code", "surface", "distance_m", "frame_no"], "父×距離": ["sire", "distance_m"],
    "騎手×調教師": ["jockey_code", "trainer_code"],
}
#: レース内の位置に直す列（True は大きいほど良い）。
RELATIVE_COLUMNS: dict[str, bool] = {
    "指数_条件の重み": True, "指数_新しさの重み": True, "指数_近5走の最高": True, "指数_前走": True,
    "相対着順_近5走の平均": False, "着差_近5走の最良": False, "末脚_近5走の平均": False,
    "序盤の位置_近5走の平均": False, "相手の強さ_近5走の平均": True, "騎手_勝率": True, "調教師_勝率": True,
    "父×芝ダ_3着内率": True, "carried": False, "馬主_勝率": True, "生産者_勝率": True, "母_3着内率": True,
    "坂路_4F最速14日": False, "坂路_1F最速14日": False, "ウッド_1F最速30日": False, "ウッド_5F最速30日": False,
    "騎手_1年_勝率": True, "調教師_60日_勝率": True,
}
#: 障害のトラックコードの範囲。
_JUMP_TRACKS = (51, 59)


class DatasetBuilder:
    """材料と答えの列をそろえた表を作る。

    行は、平地のレースで実際に出走した馬（5頭立て以上）。答えの列は won（1着）と placed（3着以内。7頭以下は2着以内）。
    比べる相手として、単勝オッズから見た勝率（market_win）も付けるが、材料の列には入れない。
    """

    def build(self, facts: pd.DataFrame, figures: pd.DataFrame, workouts: pd.DataFrame,
              connections: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        """``workouts``・``connections`` は ``extract_extra.py`` の中間データ（出走ごとの調教、馬主・生産者・母）。"""
        facts = facts.merge(connections, on=["race_id", "horse_no"], how="left")
        ability = AbilityFeatures().build(figures).rename(columns={"rid": "race_id"})
        strength = self._race_strength(facts, ability)
        past = PastRunFeatures().build(facts, strength)
        table = facts[facts["ran"]].copy()
        table = table.merge(ability, on=["race_id", "horse_no"], how="left")
        table = table.merge(past, on=["race_id", "horse_no"], how="left")
        table = table.merge(workouts, on=["race_id", "horse_no"], how="left")
        for name, keys in RECORD_GROUPS.items():
            table = table.merge(TrackRecordRates().build(facts, keys, name), on=["race_id", "horse_no"], how="left")
        table = self._recent_rates(table, facts)
        table = self._targets(self._flat_races(table))
        table = self._race_level(RaceRelative().add(table, RELATIVE_COLUMNS))
        features = self._feature_columns(table)
        # 元DB の整数の列は欠損を持てる型（Int64 など）なので、モデルに渡す前に小数の列にそろえる。
        table[features] = table[features].apply(lambda column: pd.to_numeric(column, errors="coerce")).astype(float)
        return table, features

    def _recent_rates(self, table: pd.DataFrame, facts: pd.DataFrame) -> pd.DataFrame:
        """騎手と調教師の直近の成績と、前走から騎手が格上げされたか（前走の騎手の、今日時点の1年の勝率との差）。"""
        jockey = RecentRecordRates(facts, "jockey_code", 365)
        trainer_year = RecentRecordRates(facts, "trainer_code", 365)
        trainer_recent = RecentRecordRates(facts, "trainer_code", 60)
        runs = facts[facts["ran"]].sort_values(["horse_id", "race_date", "race_id"])
        previous = runs.assign(prev_jockey=runs.groupby("horse_id")["jockey_code"].shift(1))
        table = table.merge(previous[["race_id", "horse_no", "prev_jockey"]], on=["race_id", "horse_no"], how="left")
        now = jockey.rate_on(table["jockey_code"], table["race_date"])
        before = jockey.rate_on(table["prev_jockey"], table["race_date"])
        return table.assign(**{
            "騎手_1年_勝率": now["win"].to_numpy(), "騎手_1年_3着内率": now["place"].to_numpy(),
            "騎手_格上げ": (now["win"] - before["win"]).where(table["prev_jockey"].notna().to_numpy()).to_numpy(),
            "調教師_1年_勝率": trainer_year.rate_on(table["trainer_code"], table["race_date"])["win"].to_numpy(),
            "調教師_60日_勝率": trainer_recent.rate_on(table["trainer_code"], table["race_date"])["win"].to_numpy(),
        })

    def _race_strength(self, facts: pd.DataFrame, ability: pd.DataFrame) -> pd.Series:
        """レースの強さ: 出走馬の「そのレースの時点の力」（指数_条件の重み）の上位 5頭の平均。"""
        runners = facts.loc[facts["ran"], ["race_id", "horse_no"]].merge(ability, on=["race_id", "horse_no"])
        top = runners.sort_values("指数_条件の重み", ascending=False).groupby("race_id").head(5)
        return top.groupby("race_id")["指数_条件の重み"].mean()

    def _flat_races(self, table: pd.DataFrame) -> pd.DataFrame:
        track = pd.to_numeric(table["track_code"], errors="coerce")
        table = table[~track.between(*_JUMP_TRACKS)]
        table = table.assign(runners=table.groupby("race_id")["horse_no"].transform("size"))
        return table[table["runners"] >= 5].sort_values(["race_id", "horse_no"]).reset_index(drop=True)

    def _targets(self, table: pd.DataFrame) -> pd.DataFrame:
        places = np.where(table["runners"] <= 7, 2, 3)
        finish = pd.to_numeric(table["finish"], errors="coerce").astype(float)
        odds = pd.to_numeric(table["win_odds"], errors="coerce").astype(float)
        inverse = 1.0 / odds.where(odds > 0)
        return table.assign(
            year=pd.to_datetime(table["race_date"]).dt.year, won=(finish == 1).astype(int),
            placed=((finish >= 1) & (finish <= places)).astype(int), places=places,
            market_win=inverse / inverse.groupby(table["race_id"]).transform("sum"))

    def _race_level(self, table: pd.DataFrame) -> pd.DataFrame:
        """レースの展開の手がかり: 先頭率の合計（逃げたい馬がどれだけいるか）と、自分以外の合計。"""
        lead = table["先頭率_近5走"].fillna(0)
        total = lead.groupby(table["race_id"]).transform("sum")
        return table.assign(**{"先頭率の合計": total, "ほかの馬の先頭率の合計": total - lead,
                               "馬番の位置": table["horse_no"] / table["runners"],
                               "ハンデ戦": (table["weight_type"] == "ハンデ").astype(float),
                               "競馬場": pd.to_numeric(table["venue_code"], errors="coerce"),
                               # 坂路のタイムは美浦と栗東でコースが違うので、所属を一緒に渡す。
                               "所属_栗東": (table["affiliation"] == "栗東").astype(float),
                               "ブリンカー": (table["blinker"] == "あり").astype(float),
                               "減量騎手": (table["apprentice"] == "減量あり").astype(float)})

    def _feature_columns(self, table: pd.DataFrame) -> list[str]:
        derived = [c for c in table.columns if any(c.startswith(p) for p in (
            "指数_", "着順_", "出走数", "前走からの日数", "距離の変化", "前走と芝ダ", "相対着順", "着差", "序盤の位置",
            "4角の位置", "末脚", "先頭", "相手の強さ", "クラス_", "斤量_", "騎手", "芝ダ替わり", "休み明け", "調教師",
            "父", "母", "carried_", "ほかの馬", "馬番の位置", "ハンデ戦", "競馬場", "馬主", "生産者",
            "坂路", "ウッド", "所属", "ブリンカー", "減量騎手", "ペース", "展開の不利", "末脚と着順", "体重_",
            "枠の傾向"))]
        return list(CONTEXT_COLUMNS) + derived
