"""騎手と調教師の直近の成績と、前走から騎手が格上げされたかの列を作る。"""

from __future__ import annotations

import pandas as pd

from .recent_record_rates import RecentRecordRates

#: 直近の期間（日）。
_YEAR, _RECENT = 365, 60


class RecentPeopleRates:
    """騎手の近1年の勝率・3着内率、騎手の格上げ、調教師の近1年と近60日の勝率（``RECENT_COLUMNS``）。

    騎手の格上げ = 今回の騎手の近1年の勝率 − 前走の騎手の（今回の日付の時点の）近1年の勝率。前走が無ければ欠損値。
    例: 今回の騎手が 0.15、前走の騎手が 0.06 なら +0.09（上手な騎手に乗り替わった）。
    ``runs`` は出走した馬の行、``rows`` は列を作る行（race_id・horse_id・race_date・jockey_code・trainer_code）。
    """

    def build(self, runs: pd.DataFrame, rows: pd.DataFrame) -> pd.DataFrame:
        """列は race_id・horse_id と ``RECENT_COLUMNS``。行の並びは ``rows`` と同じ。"""
        jockey = RecentRecordRates(runs, "jockey_code", _YEAR)
        trainer_year = RecentRecordRates(runs, "trainer_code", _YEAR)
        trainer_recent = RecentRecordRates(runs, "trainer_code", _RECENT)
        ordered = runs.sort_values(["horse_id", "race_date", "race_id"])
        previous = ordered.assign(prev_jockey=ordered.groupby("horse_id")["jockey_code"].shift(1))
        table = rows[["race_id", "horse_id", "race_date", "jockey_code", "trainer_code"]].merge(
            previous[["race_id", "horse_id", "prev_jockey"]], on=["race_id", "horse_id"], how="left")
        now = jockey.rate_on(table["jockey_code"], table["race_date"])
        before = jockey.rate_on(table["prev_jockey"], table["race_date"])
        return pd.DataFrame({
            "race_id": table["race_id"].to_numpy(), "horse_id": table["horse_id"].to_numpy(),
            "騎手_1年_勝率": now["win"].to_numpy(), "騎手_1年_3着内率": now["place"].to_numpy(),
            "騎手_格上げ": (now["win"] - before["win"]).where(table["prev_jockey"].notna().to_numpy()).to_numpy(),
            "調教師_1年_勝率": trainer_year.rate_on(table["trainer_code"], table["race_date"])["win"].to_numpy(),
            "調教師_60日_勝率": trainer_recent.rate_on(table["trainer_code"], table["race_date"])["win"].to_numpy(),
        })
