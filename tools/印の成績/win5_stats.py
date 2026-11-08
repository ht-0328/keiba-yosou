"""道具「印の成績」の ``--win5``: 過去の WIN5 で、40 通りの買い方と比べる相手を確かめ、表にする（流れを進めるだけ）。"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from 共通 import cli, db, render
from 共通.render import Table

from yosou.form_aptitude_win5_tickets.command.yosou_name import YOSOU_NAME as WIN5_YOSOU_NAME
from yosou.form_aptitude_win5_tickets.repository import (
    Win5HistoryRepository,
    Win5LegRunnerHistoryRepository,
    Win5ScratchRepository,
)
from yosou.form_aptitude_win5_tickets.repository.win5_columns import RACE_ID
from yosou.form_aptitude_win5_tickets.payout import PayoutEstimator
from yosou.form_aptitude_win5_tickets.settlement import (
    PERIOD,
    RACE_DATE,
    SETTLED_COLUMNS,
    STRATEGY,
    Win5BacktestTables,
    Win5Outcome,
    Win5Outcomes,
)

from 印の成績.race_results import RaceResults
from 印の成績.win5_adoption_judge import NOT_REACHED, Win5AdoptionJudge
from 印の成績.win5_backtest_day import Win5BacktestDay
from 印の成績.win5_backtest_days import Win5BacktestDays
from 印の成績.win5_confirmation_report import Win5ConfirmationReport
from 印の成績.win5_coverage_report import Win5CoverageReport
from 印の成績.win5_day_bets import CARRY_DAY, KIND, OURS, RULE, RULE_CARRY, STRATEGIES, Win5DayBets, popularity_label
from 印の成績.win5_fold_estimators import Win5FoldEstimators
from 印の成績.win5_payout_report import Win5PayoutReport
from 印の成績.win5_periods import CONFIRM, EXPLORE, Win5Periods
from 印の成績.win5_prediction_files import Win5PredictionFiles
from 印の成績.win5_probability_report import Win5ProbabilityReport
from 印の成績.win5_record_bets import RECORDED, Win5RecordBets
from 印の成績.win5_selection_report import Win5SelectionReport
from 印の成績.win5_strategy_choice import Win5StrategyChoice
from 印の成績.win5_strategy_summary import Win5StrategySummary

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
#: WIN5 の予想の置き場所（実際の予想の記録 ``記録/`` がある）と、結果を書く場所の既定。
WIN5_ROOT = _PROJECT_ROOT / "reports" / WIN5_YOSOU_NAME
DEFAULT_WIN5_OUT_DIR = WIN5_ROOT / "成績"
#: 結果のファイル名。
REPORT_NAME = "WIN5の成績.md"
SETTLED_NAME = "WIN5の精算.csv"
#: 過去の WIN5 を全部読むための「この日より前」。
_ALL_DAYS = date(9999, 12, 31)
#: 途中経過を出す間隔（日数）。
_PROGRESS_EVERY = 50
#: キャリーオーバーの日だけの表の期間の名前。
_CARRY_PERIOD = "キャリーオーバーの日（2019年から）"


class Win5Stats:
    """設計書「近走と適性からWIN5の買い目を決める」16 の 7.。区切りごとの予測と元DB の ``wf`` から、40 通りの買い方と比べる相手を精算し、
    探索期間で決まりどおりに1つ選んで、確認期間で採用の基準に照らす。精算・組み方・配当の見積もりは、この予想のパッケージの部品を呼ぶ
    （``Win5DayBets`` など）。数値は Git の対象外の ``reports/`` に出す。``records_root`` は実際の予想の記録（``記録/``）のある場所。

    引数 ``--win5-budget`` で予算（点数）を渡すと、探索期間で選ぶ候補をその予算の買い方だけにする（利用者が予算を決めたとき、
    その予算の中で同じ決まりで選び直し、確認期間で1回だけ確かめる）。"""

    def __init__(self, records_root: Path = WIN5_ROOT) -> None:
        self._records_root = Path(records_root)

    def run(self, args: argparse.Namespace) -> None:
        if len(args.win5) not in (0, 2):
            raise ValueError(f"--win5 には当日と前日の予測の pkl を2つ渡すか、何も渡さないでください（{len(args.win5)} つ）")
        files = Win5PredictionFiles(*args.win5) if args.win5 else Win5PredictionFiles()
        out_dir = Path(args.out_dir) if args.out_dir else DEFAULT_WIN5_OUT_DIR
        self._log(f"区切りごとの予測を読みます: {' / '.join(files.names)}")
        predictions = files.load()
        with db.open_db(args.db, default=db.JRA) as con:
            history = Win5HistoryRepository(con).read(_ALL_DAYS)
            scratches = Win5ScratchRepository(con).read(_ALL_DAYS)
            runners = Win5LegRunnerHistoryRepository(con).read(_ALL_DAYS)
            self._log("1着の確率の当たり具合（参考）のために、テスト期間のレースの結果を読みます（数分かかる）")
            race_ids = pd.concat([predictions.race_day["race_id"], predictions.day_before["race_id"]])
            results = RaceResults().read(con, race_ids)
        outcomes = Win5Outcomes().of(history, scratches)
        days, skipped = Win5BacktestDays().of(history, runners, predictions)
        estimators = Win5FoldEstimators().of(history, predictions.folds)
        settled = self._settle(days, history, estimators, outcomes)
        record_rows, record_note = Win5RecordBets(self._records_root).rows(outcomes)
        if record_rows:
            settled = pd.concat([settled, self._with_period(pd.DataFrame(record_rows))], ignore_index=True)
        tables = self._tables(settled, days, skipped, files, record_note, getattr(args, "win5_budget", None))
        tables += Win5ProbabilityReport().tables(predictions, results, set(runners[RACE_ID]))
        tables += Win5PayoutReport().tables(history, estimators, predictions.folds)
        cli.emit(tables, args)
        out_dir.mkdir(parents=True, exist_ok=True)
        saved = out_dir / REPORT_NAME
        render.write(render.render(tables, "markdown"), saved, fmt="markdown")
        settled.to_csv(out_dir / SETTLED_NAME, index=False, encoding="utf-8-sig")
        self._log(f"\n保存先: {saved}\n精算の結果: {out_dir / SETTLED_NAME}")

    def _settle(self, days: list[Win5BacktestDay], history: pd.DataFrame, estimators: dict[str, PayoutEstimator],
                outcomes: dict[str, Win5Outcome]) -> pd.DataFrame:
        """確かめる日ごとに、40 通りと比べる相手を精算した行（買った日だけ）。"""
        bets = Win5DayBets(history)
        rows: list[dict[str, object]] = []
        for count, day in enumerate(days, start=1):
            rows.extend(bets.settle(day, estimators[day.fold], outcomes[day.race_date]))
            if count % _PROGRESS_EVERY == 0 or count == len(days):
                self._log(f"WIN5 の {count}/{len(days)} 日を精算しました（{day.race_date}）")
        return self._with_period(pd.DataFrame(rows))

    def _with_period(self, rows: pd.DataFrame) -> pd.DataFrame:
        periods = Win5Periods()
        return rows.assign(**{PERIOD: rows[RACE_DATE].map(periods.label_of)})

    def _tables(self, settled: pd.DataFrame, days: list[Win5BacktestDay], skipped: pd.DataFrame, files: Win5PredictionFiles,
                record_note: str, budget_only: int | None = None) -> list[Table]:
        summary = Win5StrategySummary()
        choice = Win5StrategyChoice()
        ours = settled.loc[settled[KIND] == OURS]
        explore_ours = summary.of(ours.loc[ours[PERIOD] == EXPLORE])
        candidates = self._within_budget(explore_ours, budget_only)
        chosen = choice.choose(candidates)
        shown = chosen or choice.best(candidates) or STRATEGIES[0].label
        budget = next(strategy.budget for strategy in STRATEGIES if strategy.label == shown)
        labels = [shown, RULE, RULE_CARRY, popularity_label(budget)]
        if (settled[STRATEGY] == RECORDED).any():
            labels.append(RECORDED)
        summaries = {period: summary.of(settled.loc[settled[PERIOD] == period]) for period in (EXPLORE, CONFIRM)}
        verdict = self._verdict(summaries[CONFIRM], chosen, budget) if chosen else None
        compared = settled.loc[settled[STRATEGY].isin(labels)]
        carry = compared.loc[compared[CARRY_DAY].astype(bool)].assign(**{PERIOD: _CARRY_PERIOD})
        tables = [self._conditions(files, chosen, shown, record_note, budget_only), Win5CoverageReport().table(days, skipped)]
        tables += Win5SelectionReport().tables(explore_ours, chosen)
        tables += Win5ConfirmationReport().tables(summaries, labels, chosen, verdict)
        tables += Win5BacktestTables().tables(compared[list(SETTLED_COLUMNS)])
        if not carry.empty:
            carry_table = Win5BacktestTables().tables(carry[list(SETTLED_COLUMNS)])[0]
            carry_table.title = "WIN5 のキャリーオーバーの日だけの成績（参考）"
            tables.append(carry_table)
        return tables

    @staticmethod
    def _within_budget(summary: pd.DataFrame, budget: int | None) -> pd.DataFrame:
        """選ぶ候補（``budget`` を渡したら、その予算の買い方だけ）。"""
        if budget is None:
            return summary
        labels = {strategy.label for strategy in STRATEGIES if strategy.budget == budget}
        if not labels:
            raise ValueError(f"--win5-budget は {sorted({strategy.budget for strategy in STRATEGIES})} のどれかにしてください（{budget}）")
        return summary.loc[summary[STRATEGY].isin(labels)]

    def _verdict(self, confirm: pd.DataFrame, chosen: str, budget: int) -> tuple[str, str]:
        by_label = confirm.set_index(STRATEGY)
        if chosen not in by_label.index:
            return NOT_REACHED, "確認期間に、日の期待値が線以上の日が無く、1日も買わなかった"
        return Win5AdoptionJudge().judge(by_label.loc[chosen], by_label.loc[RULE], by_label.loc[popularity_label(budget)])

    def _conditions(self, files: Win5PredictionFiles, chosen: str | None, shown: str, record_note: str, budget_only: int | None) -> Table:
        race_day, day_before = files.names
        rows = [
            ["1着の確率", f"区切りごとの予測（その半年より前だけで学び直した今のモデルと同じ作り）。当日: {race_day}。前日: {day_before}"],
            ["期間", f"{EXPLORE}で買い方を選び、{CONFIRM}で1回だけ確かめる（区切りごとの予測のある日まで）"],
            ["時点のまね方", "1レース目の発走から 60分以上あとのレースは前日の予測。障害のレースはオッズから見た勝率。オッズは確定オッズ"],
            ["配当の見積もり", "区切りごとに、テスト期間の始まりより前の WIN5 だけで作った式。発売票数はその日より前の回から見積もる"],
            ["選んだ買い方", (chosen or f"選べる買い方なし（表には探索期間でいちばん良かった {shown} を並べる）")
             + (f"（予算 {budget_only}点の買い方の中から選んだ）" if budget_only else "")],
            ["実際の予想", record_note],
        ]
        return Table(["項目", "内容"], rows, title="WIN5 の確かめの条件",
                     note="確定オッズで確かめた値は、実際に買うとき（締め切り前のオッズ）より良く出ることがある（設計書 11 の 7）。")

    def _log(self, message: str) -> None:
        print(message, file=sys.stderr, flush=True)
