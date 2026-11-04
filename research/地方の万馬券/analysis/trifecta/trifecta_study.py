"""3連単・3連複の買い方の研究の流れ（段3・段4）: 全頭の予想の確率と市場の見立てから買い目を組み、確定オッズと払戻で買い方ごとの成績を出す。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from 共通.render import Table

from ..case_report import CaseReport
from ..popularity_band import PopularityBand
from ..repository import TrifectaOddsRepository, TrifectaResultRepository, TrioOddsRepository, TrioResultRepository
from ..runner_enrichment import RunnerEnrichment
from .harville_combos import HarvilleCombos
from .prediction_repository import P1, P3, PredictionRepository
from .race_market import MARKET_UPSET, RaceMarket
from .simulator import BREAKDOWN_COLUMNS, RESULT_COLUMNS, TrifectaSimulator
from .stage_predictions import STAGE_UPSET, TRIFECTA_KEY, TRIO_KEY, StagePredictions, upset_column
from .fitted_strength import Top3FittedStrength
from .strategy import STRENGTH_TOP3, STRENGTH_TOP3_FIT, STRENGTH_WIN, STRENGTH_WIN_THEN_TOP3_FIT, TRIO, Strategy
from .strategy_catalog import STRATEGIES
from .ticket_plan import TicketPlan

TICKETS_CSV = "3連単の買い目.csv"
_HEADS_BINS = [0, 10, 12, 14, np.inf]
_HEADS_LABELS = ["〜10頭", "11〜12頭", "13〜14頭", "15頭〜"]
_ODDS_BINS = [0, 30, 100, 300, 1000, 3000, np.inf]
_ODDS_LABELS = ["〜30倍", "30〜100倍", "100〜300倍（万馬券）", "300〜1000倍", "1000〜3000倍（10万馬券）", "3000倍〜"]
_EV_BINS = [0, 1.2, 1.5, 2.0, 3.0, np.inf]
_EV_LABELS = ["1.0〜1.2", "1.2〜1.5", "1.5〜2.0", "2.0〜3.0", "3.0〜"]


@dataclass(frozen=True)
class TrifectaStudySettings:
    """期間と、全頭の予想の予測の表の置き場所。"""

    test_from: date
    unseen_from: date
    test_predictions: Path
    unseen_predictions: Path | None
    popularity: PopularityBand = PopularityBand()
    strategies: tuple[Strategy, ...] = STRATEGIES
    report_name: str = "3連単の買い方"
    #: 段ごとの予想（②③④）の予測の表の置き場所（``stages.py`` が書く ``reports/地方の万馬券/predictions/``）。None なら足さない。
    stage_predictions: Path | None = None

    def only(self, codes: tuple[str, ...]) -> "TrifectaStudySettings":
        """名前の先頭の記号（L・T2 など）がどれかに一致する買い方だけにする。``M*`` のように ``*`` で終わる記号は前方一致（M1〜M17 など）。空なら全部。"""
        if not codes:
            return self
        exact = tuple(c for c in codes if not c.endswith("*"))
        prefixes = tuple(c[:-1] for c in codes if c.endswith("*"))
        chosen = tuple(s for s in self.strategies
                       if s.name.split(" ", 1)[0] in exact or s.name.split(" ", 1)[0].startswith(prefixes))
        return TrifectaStudySettings(self.test_from, self.unseen_from, self.test_predictions, self.unseen_predictions,
                                     self.popularity, chosen, self.report_name, self.stage_predictions)


@dataclass(frozen=True)
class TrifectaStudy:
    con: duckdb.DuckDBPyConnection
    settings: TrifectaStudySettings

    def run(self, out_dir: Path) -> Path:
        runners = self._runners()
        races = self._races(runners)
        combos = {key: self._combos(runners, *key) for key in {(s.ticket, s.strength) for s in self.settings.strategies}}
        odds = {TRIO: TrioOddsRepository(self.con).load(races["race_id"])} if any(s.ticket == TRIO for s in self.settings.strategies) else {}
        if any(s.ticket != TRIO for s in self.settings.strategies):
            odds[_TRIFECTA] = TrifectaOddsRepository(self.con).load(races["race_id"])
        simulators = {_TRIFECTA: TrifectaSimulator(TrifectaResultRepository(self.con).load()), TRIO: TrifectaSimulator(TrioResultRepository(self.con).load())}
        rows, year_rows, breakdown_rows, tickets = [], [], [], []
        for strategy in self.settings.strategies:
            in_scope = races[races["field_size"] >= strategy.min_heads]
            scoped = runners[runners["race_id"].isin(in_scope["race_id"])]
            chosen = TicketPlan(strategy).build(scoped, combos[(strategy.ticket, strategy.strength)], odds[strategy.ticket])
            simulator = simulators[strategy.ticket]
            settled = simulator.settle(chosen, in_scope)
            rows.extend(simulator.summarize(strategy.name, settled, in_scope))
            year_rows.extend(simulator.summarize_by_year(strategy.name, settled, in_scope))
            breakdown_rows.extend(self._breakdowns(simulator, strategy, settled, in_scope))
            tickets.append(chosen.assign(買い方=strategy.name, 券種=strategy.ticket))
        out_dir.mkdir(parents=True, exist_ok=True)
        pd.concat(tickets).to_csv(out_dir / f"{self.settings.report_name}の買い目.csv", index=False, encoding="utf-8-sig")
        tables = [
            Table.from_records(rows, RESULT_COLUMNS, title="1. 買い方ごとの成績",
                               note="確定オッズ・確定払戻。1点 100円。組の確率は Harville の式。荒れ具合は市場の割れ方（1〜3番人気の支持率 70% 以上 固い・55〜70% 中荒れ・55% 未満 大荒れ）。90% の幅は開催日を単位にしたブートストラップ。最大の落ち込みは累計の損益のそれまでの最高からの下げ幅。"),
            Table.from_records(year_rows, RESULT_COLUMNS, title="2. 年ごとの成績",
                               note="同じ買い方が年をまたいで勝ち続けるか（安定して勝てるか）を見る。列は表1と同じ。"),
            Table.from_records(breakdown_rows, BREAKDOWN_COLUMNS, title="3. 内訳（型・荒れ具合・頭数・組のオッズ・期待値・競馬場ごと）"),
            self._upset_table(races),
        ]
        intro = (f"対象: {self.settings.test_from} 以降の地方の確定レース（全頭の予想の当日の予測があるもの）。"
                 f"テスト期間（〜{self.settings.unseen_from}の前日）と未見期間（{self.settings.unseen_from}〜）に分けて見る。人気の帯は {self.settings.popularity.label}。")
        return CaseReport(out_dir).write(self.settings.report_name, f"地方の万馬券: {self.settings.report_name}", intro, tables)

    def _runners(self) -> pd.DataFrame:
        s = self.settings
        rows = RunnerEnrichment(self.con, s.test_from, 1, s.popularity).load()
        folders = [s.test_predictions] + ([s.unseen_predictions] if s.unseen_predictions else [])
        predictions = pd.concat([PredictionRepository(folder / "race_day.pkl", folder / "race_day-1着.pkl").load() for folder in folders])
        predictions = predictions.drop_duplicates(["race_id", "horse_no"], keep="last")
        rows = rows.merge(predictions, on=["race_id", "horse_no"], how="inner")
        # 組の表（数千万行）を軽くするため、ここから先の race_id は 16桁の整数にする（払戻・オッズのリポジトリも整数で返す）
        rows = rows.assign(race_id=rows["race_id"].astype("int64"))
        table = RaceMarket().attach(rows)
        if s.stage_predictions is not None:
            table = StagePredictions(s.stage_predictions).attach(table)
        return table

    def _combos(self, runners: pd.DataFrame, ticket: str, strength: str) -> pd.DataFrame:
        columns = ["race_id", "horse_no", "strength"]
        if strength == STRENGTH_WIN:
            power = runners[P1]
        elif strength == STRENGTH_TOP3:
            power = runners[P3]
        elif strength in (STRENGTH_TOP3_FIT, STRENGTH_WIN_THEN_TOP3_FIT):
            power = Top3FittedStrength().fit(runners["race_id"], runners[P1], runners[P3])
        else:
            power = np.sqrt(runners[P1].clip(lower=1e-6) * runners[P3].clip(lower=1e-6))
        horses = runners.assign(strength=power)
        if strength == STRENGTH_WIN_THEN_TOP3_FIT:
            horses = horses.assign(first_strength=runners[P1])
            columns.append("first_strength")
        return HarvilleCombos().all_races(horses[columns], trio=(ticket == TRIO))

    def _races(self, runners: pd.DataFrame) -> pd.DataFrame:
        stage_columns = [upset_column(STAGE_UPSET, key) for key in (TRIFECTA_KEY, TRIO_KEY) if upset_column(STAGE_UPSET, key) in runners.columns]
        races = runners.groupby("race_id")[["race_date", "venue", "field_size", MARKET_UPSET, *stage_columns]].first().reset_index()
        unseen = pd.to_datetime(races["race_date"]) >= pd.Timestamp(self.settings.unseen_from)
        races["period"] = unseen.map({False: "テスト期間", True: "未見期間"})
        return races

    def _breakdowns(self, simulator: TrifectaSimulator, strategy: Strategy, settled: pd.DataFrame, races: pd.DataFrame) -> list[dict]:
        if not strategy.breakdown or settled.empty:
            return []
        by_race = races.set_index("race_id")
        upset = settled["race_id"].map(by_race[MARKET_UPSET])
        heads = pd.cut(settled["race_id"].map(by_race["field_size"]), _HEADS_BINS, labels=_HEADS_LABELS).astype(str)
        odds_band = pd.cut(settled["odds"], _ODDS_BINS, labels=_ODDS_LABELS).astype(str)
        ev_band = pd.cut(settled["ev"], _EV_BINS, labels=_EV_LABELS).astype(str)
        stage_column = upset_column(STAGE_UPSET, TRIO_KEY if strategy.ticket == TRIO else TRIFECTA_KEY)
        stage_rows = (simulator.breakdown(strategy.name, settled, "荒れ具合（④）", settled["race_id"].map(by_race[stage_column]).fillna("—"))
                      if stage_column in by_race.columns else [])
        return (simulator.breakdown(strategy.name, settled, "型", settled["pattern"])
                + simulator.breakdown(strategy.name, settled, "荒れ具合（市場）", upset)
                + stage_rows
                + simulator.breakdown(strategy.name, settled, "頭数", heads)
                + simulator.breakdown(strategy.name, settled, "組のオッズ", odds_band)
                + simulator.breakdown(strategy.name, settled, "組の期待値", ev_band)
                + simulator.breakdown(strategy.name, settled, "競馬場", settled["race_id"].map(by_race["venue"])))

    def _upset_table(self, races: pd.DataFrame) -> Table:
        counts = races.groupby(["period", MARKET_UPSET]).size().rename("レース数").reset_index()
        counts.columns = ["期間", "荒れ具合（市場の割れ方）", "レース数"]
        return Table.from_records(counts.to_dict("records"), title="4. 市場の割れ方で見た荒れ具合のレース数（全頭数）")


_TRIFECTA = "3連単"
