"""直した確率の表から、レースごとに公開ルールの ◎・期待値・相手を決め、単勝と馬単の払戻を付ける。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 今週の予想.public_rule_picker import PublicRulePicker


@dataclass(frozen=True)
class PublicBets:
    """``horses`` は直した確率（列 ``corrected``）の付いた1頭1行の表、``win_payouts``・``exacta_payouts`` は単勝・馬単の払戻
    （``race_id``・``combo``・``yen``）。``races`` は1行 = 1レースで、列は ``race_id``・``race_date``・``year``・``value``（直した ◎ の期待値）・
    ``win_back``（◎ の単勝 100円の払戻）・``exacta_back``（馬単 ◎→相手 各 100円の払戻の合計）・``exacta_points``（馬単の点数）。
    ◎ と相手の決め方は本番と同じ（``PublicRulePicker.decide``）。"""

    horses: pd.DataFrame
    win_payouts: pd.DataFrame
    exacta_payouts: pd.DataFrame

    def races(self) -> pd.DataFrame:
        win = _lookup(self.win_payouts)
        exacta = _lookup(self.exacta_payouts)
        rows = []
        for race_id, race in self.horses.groupby("race_id", sort=False):
            judged = PublicRulePicker.decide(race.assign(unrated=False))
            if not judged["ready"]:
                continue
            top = f"{judged['top']:02d}"
            backs = [exacta.get((race_id, f"{top}{partner:02d}"), 0) for partner in judged["partners"]]
            rows.append({"race_id": race_id, "race_date": race["race_date"].iloc[0], "year": int(race["year"].iloc[0]), "value": judged["value"],
                         "win_back": win.get((race_id, top), 0), "exacta_back": sum(backs), "exacta_points": len(backs)})
        return pd.DataFrame(rows)


def _lookup(payouts: pd.DataFrame) -> dict[tuple[str, str], int]:
    """（レースID, 組番）→ 100円あたりの払戻（同着で同じ組が2行あれば足す）。"""
    keyed = payouts.assign(race_id=payouts["race_id"].astype(str), combo=payouts["combo"].astype(str))
    summed = keyed.groupby(["race_id", "combo"])["yen"].sum()
    return {key: int(value) for key, value in summed.items()}
