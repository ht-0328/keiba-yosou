"""買い目の表から、券種ごとの成績の表を作る。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.win_value import HIGH

from 共通.bootstrap_interval import BootstrapInterval
from 共通.perf import percent
from 共通.render import Table

from 今週の予想.forecast_columns import EXPECTATION

from 印の成績.ticket_payouts import PAYOUT
from 印の成績.ticket_rules import POINT_YEN, TICKET_ORDER, UNIT_YEN, rule_label, stake_units_of
from 印の成績.torigami_filter import DROPPED, NO_ODDS, TORIGAMI

#: 対象の名前（全レースと、期待度が高のレースだけ）。
ALL_RACES, HIGH_RACES = "全レース", f"期待度 {HIGH}"
TARGETS: tuple[str, ...] = (ALL_RACES, HIGH_RACES)
TOTAL_LABEL = "合計（08 の単位の配分）"


class TicketReport:
    """買い目の表（``TicketPayouts.attach`` → ``TorigamiFilter.apply`` のあと）から、次の表を作る。

    7. 券種ごとの買い目の成績（1点 100円。全レースと期待度「高」のレースのそれぞれ。合計は 08 の 2 の単位の配分で 1単位 = 1,000円）。
    8. 券種ごとの年ごとの回収率。
    回収率は確定の払戻 ÷ 投資。90% の幅は、開催日を単位にしたブートストラップ。トリガミとオッズ無しで外した買い目は数えない。
    """

    def tables(self, tickets: pd.DataFrame, races: int, days: int) -> list[Table]:
        bought = tickets[tickets[DROPPED] == ""]
        return [self._by_type(tickets, bought, races, days), self._yearly(bought)]

    def _by_type(self, tickets: pd.DataFrame, bought: pd.DataFrame, races: int, days: int) -> Table:
        headers = ["券種", "対象", "買ったレース", "点数", "1レースの点数", "投資", "払戻", "回収率", "回収率の90%の幅", "的中レース", "的中率",
                   "トリガミで外した点数", "オッズ無しで外した点数"]
        rows = []
        for target in TARGETS:
            for ticket_type in TICKET_ORDER:
                chosen = self._select(bought, ticket_type, target)
                dropped = self._select(tickets, ticket_type, target)
                rows.append(self._row(rule_label(ticket_type), target, chosen, dropped))
            rows.append(self._total_row(target, self._select(bought, None, target)))
        note = (f"レース数 {races:,}・開催日 {days:,}日。買い目は設計書「買うレースと買い目を決める」08 の 2 の印のルール（◎ は単勝 30倍以下の馬の中で単勝の期待値が1位。"
                "複勝は期待値 1.25 以上を高い順に最大3点）。馬単と3連単は設計書に無く、◎ を1着に固定した形で全券種にそろえた。"
                "「3連複（荒れそう）」は荒れ具合の判定が要るので出さない。1点 100円で数え、合計の行だけ 08 の単位の配分（1単位 = 1,000円。単勝・複勝・ワイド 1、"
                "馬連・馬単 0.5、3連複 0.3、3連単 0.1）。トリガミ（どれが当たっても券種の投資より少なく戻る買い目）と、確定オッズの無い組（無投票・取消）は外して数えない。"
                "払戻は確定オッズのもので、実際に買うときより良く出る。")
        return Table(headers, rows, title="7. 券種ごとの買い目の成績（印のルール）", note=note)

    def _row(self, label: str, target: str, chosen: pd.DataFrame, all_rows: pd.DataFrame) -> list[str]:
        torigami = int((all_rows[DROPPED] == TORIGAMI).sum())
        no_odds = int((all_rows[DROPPED] == NO_ODDS).sum())
        if chosen.empty:
            return [label, target, "0", "0", "—", "0円", "0円", "—", "—", "0", "—", f"{torigami:,}", f"{no_odds:,}"]
        races = chosen["race_id"].nunique()
        stake = POINT_YEN * len(chosen)
        payout = float(chosen[PAYOUT].sum())
        low, high = BootstrapInterval().of(chosen["race_date"], pd.Series(float(POINT_YEN), index=chosen.index), chosen[PAYOUT])
        hits = chosen[chosen[PAYOUT] > 0]["race_id"].nunique()
        return [label, target, f"{races:,}", f"{len(chosen):,}", f"{len(chosen) / races:.1f}", f"{stake:,.0f}円", f"{payout:,.0f}円",
                percent(payout / stake), f"{percent(low)}〜{percent(high)}", f"{hits:,}", percent(hits / races), f"{torigami:,}", f"{no_odds:,}"]

    def _total_row(self, target: str, chosen: pd.DataFrame) -> list[str]:
        """08 の単位の配分で、券種をまたいだ合計（1単位 = 1,000円）。"""
        if chosen.empty:
            return [TOTAL_LABEL, target, "0", "0", "—", "0円", "0円", "—", "—", "0", "—", "", ""]
        stakes = chosen["stake_units"].astype(float) * UNIT_YEN
        payouts = chosen[PAYOUT].astype(float) * stakes / POINT_YEN
        races = chosen["race_id"].nunique()
        low, high = BootstrapInterval().of(chosen["race_date"], stakes, payouts)
        hits = chosen[chosen[PAYOUT] > 0]["race_id"].nunique()
        return [TOTAL_LABEL, target, f"{races:,}", f"{len(chosen):,}", f"{len(chosen) / races:.1f}", f"{stakes.sum():,.0f}円",
                f"{payouts.sum():,.0f}円", percent(payouts.sum() / stakes.sum()), f"{percent(low)}〜{percent(high)}", f"{hits:,}",
                percent(hits / races), "", ""]

    def _yearly(self, bought: pd.DataFrame) -> Table:
        years = sorted(bought["race_date"].astype(str).str[:4].unique())
        rows = []
        for target in TARGETS:
            for ticket_type in TICKET_ORDER:
                chosen = self._select(bought, ticket_type, target)
                by_year = chosen.groupby(chosen["race_date"].astype(str).str[:4])[PAYOUT].agg(["sum", "size"])
                cells = [(percent(by_year.loc[year, "sum"] / (POINT_YEN * by_year.loc[year, "size"])) if year in by_year.index else "—")
                         for year in years]
                rows.append([rule_label(ticket_type), target, *cells])
        return Table(["券種", "対象", *years], rows, title="8. 券種ごとの年ごとの回収率（1点 100円）",
                     note="表7 と同じ買い目を、年ごとに数えたもの。")

    def _select(self, table: pd.DataFrame, ticket_type: TicketType | None, target: str) -> pd.DataFrame:
        chosen = table if ticket_type is None else table[table["ticket_type"] == ticket_type.label]
        if target == HIGH_RACES:
            chosen = chosen[chosen[EXPECTATION] == HIGH]
        return chosen

    def csv_frame(self, tickets: pd.DataFrame) -> pd.DataFrame:
        """買い目の CSV（1行 = 1点）。列は日本語。"""
        return pd.DataFrame({
            "レースID": tickets["race_id"], "開催日": tickets["race_date"].dt.strftime("%Y-%m-%d"), "区切り": tickets["fold"],
            "期待度": tickets[EXPECTATION], "券種": tickets["ticket_type"], "組番": tickets["combo"], "単位": tickets["stake_units"],
            "確定オッズ": tickets["odds"], "払戻（100円あたり）": tickets[PAYOUT], "外した理由": tickets[DROPPED],
        })


def stake_units_note() -> str:
    """08 の単位の配分の説明（券種 → 単位）。"""
    return "・".join(f"{ticket_type.label} {stake_units_of(ticket_type):g}" for ticket_type in TICKET_ORDER)
