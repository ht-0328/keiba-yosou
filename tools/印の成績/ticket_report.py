"""買い目の表から、買い方ごとの成績の表を作る。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.combo_value import ComboExpectedValue

from 共通.bootstrap_interval import BootstrapInterval
from 共通.perf import percent
from 共通.render import Table

from 今週の予想.forecast_columns import EXPECTATION

from 印の成績.mark_tickets import RULE, VALUE
from 印の成績.race_filters import TARGETS, RaceFilter
from 印の成績.ticket_payouts import ODDS, PAYOUT
from 印の成績.ticket_rules import COMBO_VALUE_LINE, POINT_YEN, RULE_LABELS, TOTAL_GROUPS, TOTAL_MEMBERS, UNIT_YEN
from 印の成績.torigami_filter import DROPPED, NO_ODDS, TORIGAMI


def total_label(group: str) -> str:
    """合計の行の名前（軸のパターンごと）。"""
    return f"合計（{group}。08 の単位の配分）"


class TicketReport:
    """買い目の表（``TicketPayouts.attach`` → ``TorigamiFilter.apply`` のあと）から、次の表を作る。

    7. 買い方ごとの買い目の成績（1点 100円。レースの絞り込み（``TARGETS``: 全レース・期待度「高」・高で2モデル一致・高で3連単の支持あり・
       その両方）ごと。合計は軸のパターンごとに、08 の 2 の単位の配分で 1単位 = 1,000円）。
    8. 買い方ごとの年ごとの回収率。
    回収率は確定の払戻 ÷ 投資。90% の幅は、開催日を単位にしたブートストラップ。トリガミとオッズ無しで外した買い目は数えない。
    """

    def tables(self, tickets: pd.DataFrame, races: int, days: int) -> list[Table]:
        bought = tickets[tickets[DROPPED] == ""]
        return [self._by_rule(tickets, bought, races, days), self._yearly(bought)]

    def _by_rule(self, tickets: pd.DataFrame, bought: pd.DataFrame, races: int, days: int) -> Table:
        headers = ["買い方", "対象", "買ったレース", "点数", "1レースの点数", "投資", "払戻", "回収率", "回収率の90%の幅", "的中レース", "的中率",
                   "トリガミで外した点数", "オッズ無しで外した点数"]
        rows = []
        for target in TARGETS:
            for label in RULE_LABELS:
                rows.append(self._row(label, target.label, self._select(bought, label, target), self._select(tickets, label, target)))
            for group in TOTAL_GROUPS:
                rows.append(self._total_row(group, target.label, self._select(bought, TOTAL_MEMBERS[group], target)))
        note = (f"レース数 {races:,}・開催日 {days:,}日。買い目は設計書「買うレースと買い目を決める」08 の 2 の印のルール（◎ は単勝 30倍以下の馬の中で単勝の期待値が1位。"
                "複勝は期待値 1.25 以上を高い順に最大3点）。3連複・3連単は、元の買い目（◎−○▲☆−○▲△☆ と ◎→○▲☆→○▲△☆）を必ず買い、"
                "軸の1頭から ○▲△☆ への流し（3連複。最大 15点）とマルチ（3連単。最大 90点）を足す。"
                "軸は「◎軸」（◎）と「軸馬」（◎○▲のうち3着以内の確率が1位。◎ と違えば ◎ は相手に回る）の2パターン。"
                f"「期待値 {COMBO_VALUE_LINE:.1f} 以上」の行は、組の期待値（券種の払戻率 × 3頭の「モデル ÷ 市場」の比の積。07 の 2）が線以上の買い目だけで、線は固定。"
                "「2モデル一致」の行（複勝・期待値で絞った3連複・3連単）は、LightGBM と CatBoost のそれぞれの確率で出した期待値も線以上の買い目だけ"
                "（研究「回収率100超の施策」の施策2。比べるための行で、合計には入らない）。"
                "馬単は設計書に無く、◎ を1着に固定した形で全券種にそろえた。「3連複（荒れそう）」は荒れ具合の判定が要るので出さない。"
                "1点 100円で数え、合計の行だけ 08 の単位の配分（1単位 = 1,000円。単勝・複勝・ワイド 1、馬連・馬単 0.5、3連複 0.3、3連単 0.1）。"
                "合計は3つ: 「元の買い目だけ」は単勝・複勝・ワイド・馬連・馬単・元の3連複・元の3連単、「◎軸」「軸馬」はそれに"
                "そのパターンの 3連複（流し・全点）と 3連単（マルチ・期待値が線以上）を足したもの（元の買い目は必ず買うので、どの合計にも入る）。"
                "対象の「2モデル一致」は、◎ の単勝の期待値が2つのモデルのそれぞれの確率でも 1.00 以上のレース、「3連単の支持あり」は、"
                "◎ の 3連単から見た勝率が単勝から見た勝率以上（比 1.0 以上）のレース（施策 1-A。3連単の確定オッズから出す）。"
                "トリガミ（どれが当たっても買い方の投資より少なく戻る買い目）と、確定オッズの無い組（無投票・取消）は外して数えない。"
                "払戻は確定オッズのもので、実際に買うときより良く出る。")
        return Table(headers, rows, title="7. 買い方ごとの買い目の成績（印のルール）", note=note)

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

    def _total_row(self, group: str, target: str, chosen: pd.DataFrame) -> list[str]:
        """08 の単位の配分で、買い方をまたいだ合計（1単位 = 1,000円）。"""
        label = total_label(group)
        if chosen.empty:
            return [label, target, "0", "0", "—", "0円", "0円", "—", "—", "0", "—", "", ""]
        stakes = chosen["stake_units"].astype(float) * UNIT_YEN
        payouts = chosen[PAYOUT].astype(float) * stakes / POINT_YEN
        races = chosen["race_id"].nunique()
        low, high = BootstrapInterval().of(chosen["race_date"], stakes, payouts)
        hits = chosen[chosen[PAYOUT] > 0]["race_id"].nunique()
        return [label, target, f"{races:,}", f"{len(chosen):,}", f"{len(chosen) / races:.1f}", f"{stakes.sum():,.0f}円",
                f"{payouts.sum():,.0f}円", percent(payouts.sum() / stakes.sum()), f"{percent(low)}〜{percent(high)}", f"{hits:,}",
                percent(hits / races), "", ""]

    def _yearly(self, bought: pd.DataFrame) -> Table:
        years = sorted(bought["race_date"].astype(str).str[:4].unique())
        rows = []
        for target in TARGETS:
            for label in RULE_LABELS:
                chosen = self._select(bought, label, target)
                by_year = chosen.groupby(chosen["race_date"].astype(str).str[:4])[PAYOUT].agg(["sum", "size"])
                cells = [(percent(by_year.loc[year, "sum"] / (POINT_YEN * by_year.loc[year, "size"])) if year in by_year.index else "—")
                         for year in years]
                rows.append([label, target.label, *cells])
        return Table(["買い方", "対象", *years], rows, title="8. 買い方ごとの年ごとの回収率（1点 100円）",
                     note="表7 と同じ買い目を、年ごとに数えたもの。")

    def _select(self, table: pd.DataFrame, labels: str | tuple[str, ...], target: RaceFilter) -> pd.DataFrame:
        chosen = table[table[RULE].isin((labels,) if isinstance(labels, str) else labels)]
        return chosen[target.select(chosen)]

    def csv_frame(self, tickets: pd.DataFrame) -> pd.DataFrame:
        """買い目の CSV（1行 = 1点）。列は日本語。組の確率は、期待値 ÷ 確定オッズ（3連複・3連単だけ）。"""
        return pd.DataFrame({
            "レースID": tickets["race_id"], "開催日": tickets["race_date"].dt.strftime("%Y-%m-%d"), "区切り": tickets["fold"],
            "期待度": tickets[EXPECTATION], "買い方": tickets[RULE], "券種": tickets["ticket_type"], "組番": tickets["combo"],
            "単位": tickets["stake_units"], "期待値": tickets[VALUE], "組の確率": ComboExpectedValue().probability(tickets[VALUE], tickets[ODDS]),
            "確定オッズ": tickets[ODDS], "払戻（100円あたり）": tickets[PAYOUT], "外した理由": tickets[DROPPED],
        })
