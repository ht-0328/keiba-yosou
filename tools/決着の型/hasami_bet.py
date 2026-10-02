"""ハサミ目: 前のレース（既定 10R）の 1〜3着の馬番に挟まれた番号の単勝・複勝を、次のレース（既定 11R）で買う。"""

from __future__ import annotations

import pandas as pd

from 共通.render import Table

from 決着の型.pattern_settlement import STAKE_YEN, TOTAL_LABEL

DEFAULT_SOURCE_RACE, DEFAULT_TARGET_RACE = 10, 11
COLUMNS: tuple[str, ...] = ("開催年", "対象の日", "ハサミ目のあった日", "点数", "購入額",
                            "単勝的中", "単勝払戻", "単勝回収率", "複勝的中", "複勝払戻", "複勝回収率")
#: 「隣り合う2つに挟まれた」= 馬番の差が 2。
_GAP = 2
_TOP = 3


class HasamiBet:
    """同じ日・同じ競馬場の前のレースの 1〜3着の馬番を小さい順に並べ、差が 2 の2つに挟まれた番号を、次のレースで買う。

    挟まれた番号が無い日は買わない。次のレースにその馬番の馬が出走していなければ（取消・頭数が足りない）その点は買わない。
    単勝と複勝を同じ点数ずつ 1点 100円で買う。
    """

    def __init__(self, source_race: int = DEFAULT_SOURCE_RACE, target_race: int = DEFAULT_TARGET_RACE) -> None:
        if source_race == target_race:
            raise ValueError("前のレースと次のレースには違うレース番号を書いてください")
        self._source, self._target = source_race, target_race

    def settle(self, runners: pd.DataFrame) -> pd.DataFrame:
        """1行 = 1日1場: ``year``・``numbers``（ハサミ目の数）・``tickets``・``win_hits``・``win_yen``・``place_hits``・``place_yen``。"""
        day_keys = ["race_date", "venue"]
        source = runners[runners["race_no"].eq(self._source) & runners["finish"].le(_TOP)]
        placed = source.sort_values([*day_keys, "finish", "horse_no"]).groupby(day_keys)["horse_no"]
        # 次のレースの出走馬を日・場ごとに分けておく（日ごとに全体を絞り直すと遅い）
        targets = {key: group for key, group in runners[runners["race_no"].eq(self._target)].groupby(day_keys)}
        rows = []
        for (race_date, venue), numbers in placed:
            sandwiched = self._sandwiched([int(no) for no in numbers.head(_TOP)])
            target = targets.get((race_date, venue), runners.iloc[0:0])
            bought = target[target["horse_no"].isin(sandwiched)]
            rows.append((race_date, venue, int(race_date[:4]), len(sandwiched), len(bought),
                         int(bought["win_payout"].gt(0).sum()), int(bought["win_payout"].sum()),
                         int(bought["place_payout"].gt(0).sum()), int(bought["place_payout"].sum())))
        return pd.DataFrame(rows, columns=["race_date", "venue", "year", "numbers", "tickets",
                                           "win_hits", "win_yen", "place_hits", "place_yen"])

    def table(self, settled: pd.DataFrame, condition: str) -> Table:
        rows = [self._cells(str(year), group) for year, group in settled.groupby("year", sort=True)]
        rows.append(self._cells(TOTAL_LABEL, settled))
        table = Table(list(COLUMNS), rows, title=f"ハサミ目（{self._source}R の 1〜3着 → {self._target}R）— {condition}",
                      note="単勝・複勝をそれぞれ 1点 100円。次のレースにその馬番が出走していない点は買わない。")
        table.meta = {"source": self._source, "target": self._target, "days": int(len(settled)), "condition": condition}
        return table

    @staticmethod
    def _sandwiched(numbers: list[int]) -> list[int]:
        """小さい順に並べ、隣り合う2つの差が 2 ならその間の番号。"""
        ordered = sorted(numbers)
        return [low + 1 for low, high in zip(ordered, ordered[1:]) if high - low == _GAP]

    @staticmethod
    def _cells(label: str, settled: pd.DataFrame) -> list[str]:
        tickets = int(settled["tickets"].sum())
        stake = tickets * STAKE_YEN

        def recovery(yen: int) -> str:
            return f"{yen / stake * 100:.1f}%" if stake else "—"

        win_yen, place_yen = int(settled["win_yen"].sum()), int(settled["place_yen"].sum())
        return [label, str(len(settled)), str(int(settled["numbers"].gt(0).sum())), str(tickets), str(stake),
                str(int(settled["win_hits"].sum())), str(win_yen), recovery(win_yen),
                str(int(settled["place_hits"].sum())), str(place_yen), recovery(place_yen)]
