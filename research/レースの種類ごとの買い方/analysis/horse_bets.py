"""印を付けた表から、単勝・複勝の買い目の候補（1行 = 1頭）を作る（docs/04 の 2）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.betting import TicketType

from .race_kinds import KIND_GROUP

#: 券種 → （期待値の列, オッズの列, 100円あたりの払戻の列）。複勝のオッズは最低オッズ（トリガミの確かめも最低で数える）。
_COLUMNS: dict[TicketType, tuple[str, str, str]] = {
    TicketType.WIN: ("win_value", "win_odds", "win_payout"),
    TicketType.PLACE: ("place_value", "place_odds_low", "place_payout"),
}
#: 残す期待値の下限と、券種ごとのオッズの上限（決まりの候補のいちばん下と上。複勝の 200倍は、上限の無い今の本番を含めるため）。
MIN_VALUE = 1.0
MAX_ODDS: dict[TicketType, float] = {TicketType.WIN: 50.0, TicketType.PLACE: 200.0}


class HorseBets:
    """印を付けた表（``marked-<年>から.parquet``）から、単勝か複勝の、期待値が ``MIN_VALUE`` 以上でオッズが ``MAX_ODDS`` の券種の上限以下の馬を、
    組の期待値の券種と同じ列（``race_id``・``race_date``・``expectation``・``top``・``h1``・``odds``・``payout``・``hit``・``value``・種類）にする。

    ``h1`` は馬番、``top`` は ◎ の馬番。決まりの「◎ を含む」は ◎ の馬だけを買うことになる。例: ◎ が 3番で単勝の期待値 1.08・6.0倍なら、
    h1 3・top 3・value 1.08・odds 6.0。
    """

    def of(self, ticket_type: TicketType, marked: pd.DataFrame, kinds: pd.DataFrame) -> pd.DataFrame:
        value, odds, payout = _COLUMNS[ticket_type]
        frame = marked.assign(race_id=marked["race_id"].astype(str))
        tops = frame[frame["mark"] == "◎"].groupby("race_id")["horse_no"].first()
        table = pd.DataFrame({"race_id": frame["race_id"], "race_date": pd.to_datetime(frame["race_date"]), "fold": frame["fold"],
                              "expectation": frame["expectation"], "top": frame["race_id"].map(tops), "h1": frame["horse_no"].astype(int),
                              "odds": frame[odds].astype(float), "payout": frame[payout].astype(float), "value": frame[value].astype(float)})
        table = table.dropna(subset=["value", "odds"])
        table = table[(table["value"] >= MIN_VALUE) & (table["odds"] <= MAX_ODDS[ticket_type])]
        table["payout"] = table["payout"].fillna(0.0)
        table["hit"] = table["payout"] > 0
        table = table.merge(kinds[["race_id", KIND_GROUP]], on="race_id", how="inner")
        return table.sort_values("race_id", kind="stable").reset_index(drop=True)
