"""1着・2着・3着を分けて市場に合わせる研究の流れ（段5）: 出走の行と全頭の予想、全券種の確定オッズと払戻を読み、年を入れ替えて（または前の年だけで）
条件つきロジットを当てはめ、券種ごとの買い方の年ごとの成績と、全券種をまとめた成績を Markdown に書く。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from 共通.render import Table

from ..case_report import CaseReport
from ..repository import FactsRepository, LocalTicketOddsRepository, LocalTicketPayoutRepository, TrifectaOddsRepository, TrifectaResultRepository
from 地方の推奨買目.member_predictions import MemberPredictions
from 地方の推奨買目.pool_tables import PoolTables
from 地方の推奨買目.pool_tables_builder import PoolTablesBuilder
from 地方の推奨買目.position_features import FIRST_FEATURES_TRIFECTA_ONLY, SECOND_FEATURES_TRIFECTA_ONLY, THIRD_FEATURES_TRIFECTA_ONLY
from 地方の推奨買目.position_model import PositionModel
from 地方の推奨買目.ticket_plan import CANDIDATE_PLANS, DEFAULT_PLANS, TicketPlan
from 地方の推奨買目.ticket_probabilities import TICKET_KEYS, TICKETS, TicketProbabilities
from .ticket_summary import SUMMARY_COLUMNS, TicketSummary

#: 当てはめ方。入れ替え: 各年を残りの年で当てはめる。前の年: 前の年だけで当てはめる（最初の年は評価しない）。
LEAVE_ONE_OUT, FORWARD = "入れ替え", "前の年"
PROTOCOLS: tuple[str, ...] = (LEAVE_ONE_OUT, FORWARD)
_TOTAL = "合計"
_TRIFECTA = "3連単"
_POOL_TICKETS: tuple[str, ...] = ("馬単", "3連複", "複勝")


@dataclass(frozen=True)
class PositionsStudySettings:
    """期間・全頭の予想の予測の表の置き場所・当てはめ方・買い方。"""

    test_from: date
    predictions: Path
    protocol: str = LEAVE_ONE_OUT
    min_heads: int = 11
    trifecta_only: bool = False
    plans: tuple[TicketPlan, ...] = DEFAULT_PLANS
    candidates: tuple[TicketPlan, ...] = CANDIDATE_PLANS
    report_name: str = "全券種の買い方"


@dataclass(frozen=True)
class PositionsStudy:
    con: duckdb.DuckDBPyConnection
    settings: PositionsStudySettings

    def run(self, out_dir: Path) -> Path:
        s = self.settings
        runners = self._runners()
        races = runners.groupby("race_id")[["race_date"]].first().reset_index()
        races["year"] = pd.to_datetime(races["race_date"]).dt.year
        frames = runners[["race_id", "horse_no", "frame_no"]]
        years = sorted(races["year"].unique())
        pools = {year: self._pool_tables(runners[runners["race_id"].isin(races.loc[races["year"] == year, "race_id"])]) for year in years}
        model = self._model()
        summary = TicketSummary()
        candidate_rows, plan_rows, coefficient_rows, chosen_all = [], [], [], []
        for year in years:
            fit_years = [y for y in years if (y < year if s.protocol == FORWARD else y != year)]
            if not fit_years:
                continue
            coefficients = model.fit([pools[y] for y in fit_years])
            coefficient_rows.extend(coefficients.rows(f"{'・'.join(str(y) for y in fit_years)}年で当てはめ → {year}年"))
            combos = model.predict(pools[year], coefficients)
            year_races = races[races["year"] == year]
            tables = self._ticket_tables(combos, frames[frames["race_id"].isin(year_races["race_id"])], year_races["race_id"])
            period = f"{year}年"
            for plan in s.candidates:
                candidate_rows.append(summary.row(plan.ticket, plan.label, period, plan.choose(tables[plan.ticket]), year_races))
            year_chosen = []
            for plan in s.plans:
                chosen = plan.choose(tables[plan.ticket])
                plan_rows.append(summary.row(plan.ticket, plan.label, period, chosen, year_races))
                year_chosen.append(chosen.assign(券種=plan.ticket))
            total = pd.concat(year_chosen, ignore_index=True)
            plan_rows.append(summary.row(_TOTAL, "採った買い方の全部", period, total, year_races))
            chosen_all.append(total)
        all_chosen = pd.concat(chosen_all, ignore_index=True) if chosen_all else pd.DataFrame(columns=["race_id", "P", "payout", "券種"])
        evaluated = races[races["race_id"].isin(all_chosen["race_id"])] if len(all_chosen) else races.iloc[0:0]
        plan_rows.append(summary.row(_TOTAL, "採った買い方の全部", "全部の年", all_chosen, evaluated))
        monthly = summary.monthly(all_chosen, races) if len(all_chosen) else pd.DataFrame()
        out_dir.mkdir(parents=True, exist_ok=True)
        all_chosen.to_csv(out_dir / f"{s.report_name}の買い目.csv", index=False, encoding="utf-8-sig")
        tables_out = [
            Table.from_records(plan_rows, SUMMARY_COLUMNS, title="1. 採った買い方の券種ごと・年ごとの成績（最後は全券種の合計）",
                               note="確定オッズ・確定払戻。1点 100円。期待値は 直した確率 × 確定オッズ（複勝・ワイドはオッズの幅の真ん中）。"
                                    "90% の幅は開催日を単位にしたブートストラップ。最大の落ち込みは累計の損益のそれまでの最高からの下げ幅。"),
            self._monthly_table(monthly),
            self._candidate_table(candidate_rows, years),
            Table.from_records(coefficient_rows, ("当てはめ", "着", "特徴量", "係数"), title="4. 条件つきロジットの係数",
                               note="log_p1・log_p3 は全頭の予想の確率（_lgb・_cat はモデルごと）、log_s は単勝の支持率、log_m_a・log_m2・log_m3 は 3連単の票、"
                                    "log_m_ax・log_m2x は馬単の票、log_m1t・log_m2t・log_m3t は 3連複の票、log_px は複勝オッズの逆数。"),
        ]
        intro = (f"対象: {s.test_from} 以降の地方の確定レース（{s.min_heads}頭以上。全頭の予想の当日の予測があるもの）。当てはめ方は「{s.protocol}」"
                 f"（{'各年を残りの年で当てはめた未見の成績' if s.protocol == LEAVE_ONE_OUT else '前の年だけで当てはめた未見の成績'}）。"
                 f"材料は {'3連単の票だけ' if s.trifecta_only else '3連単・馬単・3連複・複勝の票'}。")
        return CaseReport(out_dir).write(s.report_name, f"地方の万馬券: {s.report_name}", intro, tables_out)

    def _model(self) -> PositionModel:
        if self.settings.trifecta_only:
            return PositionModel(FIRST_FEATURES_TRIFECTA_ONLY, SECOND_FEATURES_TRIFECTA_ONLY, THIRD_FEATURES_TRIFECTA_ONLY)
        return PositionModel()

    def _runners(self) -> pd.DataFrame:
        s = self.settings
        rows = FactsRepository(self.con).load(s.test_from)
        rows = rows[rows["field_size"] >= s.min_heads]
        rows = rows[["race_id", "race_date", "field_size", "frame_no", "horse_no", "popularity", "win_odds", "finish"]].assign(race_id=rows["race_id"].astype(str))
        rows = rows.merge(MemberPredictions(s.predictions).load(), on=["race_id", "horse_no"], how="inner")
        return rows.assign(race_id=rows["race_id"].astype("int64")).reset_index(drop=True)

    def _pool_tables(self, horses: pd.DataFrame) -> PoolTables:
        ids = horses["race_id"].drop_duplicates()
        trifecta = TrifectaOddsRepository(self.con).load(ids)
        results = TrifectaResultRepository(self.con).load()
        trifecta = trifecta.merge(results[["race_id", "first", "second", "third", "payout"]], on=["race_id", "first", "second", "third"], how="left")
        exacta, trio, place = (LocalTicketOddsRepository(self.con, ticket).load(ids) for ticket in _POOL_TICKETS)
        return PoolTablesBuilder().build(horses, trifecta, exacta, trio, place)

    def _ticket_tables(self, combos: pd.DataFrame, frames: pd.DataFrame, race_ids: pd.Series) -> dict[str, pd.DataFrame]:
        """券種ごとに、組の確率と確定オッズ・払戻（外れは 0）を付けた表。"""
        probabilities = TicketProbabilities().of(combos, frames)
        tables: dict[str, pd.DataFrame] = {}
        for ticket in TICKETS:
            if ticket == _TRIFECTA:
                tables[ticket] = combos.rename(columns={"first": "a", "second": "b", "third": "c"})
                continue
            key = ["race_id", *TICKET_KEYS[ticket]]
            odds = LocalTicketOddsRepository(self.con, ticket).load(race_ids)
            payouts = LocalTicketPayoutRepository(self.con, ticket).load(race_ids)
            table = probabilities[ticket].merge(odds, on=key, how="inner").merge(payouts, on=key, how="left")
            table["payout"] = table["payout"].fillna(0).astype(int)
            tables[ticket] = table
        return tables

    def _monthly_table(self, monthly: pd.DataFrame) -> Table:
        records = [{"月": row["月"], "点数": int(row["点数"]), "的中": int(row["的中"]), "投資": f"{int(row['投資']):,}円", "払戻": f"{int(row['払戻']):,}円",
                    "回収率": f"{row['回収率']:.1%}", "損益": f"{int(row['損益']):+,}円"} for row in monthly.to_dict("records")]
        above = sum(1 for row in monthly.to_dict("records") if row["回収率"] > 1.0) if len(monthly) else 0
        return Table.from_records(records, ("月", "点数", "的中", "投資", "払戻", "回収率", "損益"), title="2. 採った買い方の全部を月ごとに",
                                  note=f"100% を超えた月は {above} / {len(monthly)}。")

    def _candidate_table(self, rows: list[dict], years: list[int]) -> Table:
        """券種 × 買い方 を行、年を列にした回収率の表（点数は括弧の中）。"""
        by_key: dict[tuple[str, str], dict[str, str]] = {}
        for row in rows:
            by_key.setdefault((row["券種"], row["買い方"]), {})[row["期間"]] = f"{row['回収率']}（{row['点数']:,}点）"
        periods = [f"{year}年" for year in years]
        records = [{"券種": ticket, "買い方": plan, **{period: values.get(period, "—") for period in periods}} for (ticket, plan), values in by_key.items()]
        return Table.from_records(records, ("券種", "買い方", *periods), title="3. 比べる買い方の券種ごと・年ごとの回収率（括弧は点数）",
                                  note="同じ券種で、オッズの帯と期待値の線を変えて比べる。3年とも 100% を超える買い方を採る。")
