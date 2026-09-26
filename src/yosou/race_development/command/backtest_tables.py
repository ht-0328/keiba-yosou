"""年ごとの確かめの結果を、表にする。"""

from __future__ import annotations

import pandas as pd

from 共通.render import Table

from ..betting import MODEL_MARK_RULE, POPULARITY_MARK_RULE, TOTAL_YEAR
from ..evaluation import KIND, METRIC, VALUE, YEAR
from ..workflow import BacktestReport

#: まとめの表の列（``ReturnSummary`` の見出し）。
_RULE, _TYPE, _YEAR = "買い方", "券種", "年"
_RATE_COLUMNS = ("的中率", "回収率", "最大の払戻を除いた回収率")
#: 期待値で買う買い方の名前の頭（``ExpectedValueTicketRule`` の既定の名前は「期待値 1.0 以上（モデル）」）。
_VALUE_RULE_PREFIX = "期待値"
_NOTE = ("回収率 = 払戻の合計 ÷ 賭け金の合計。的中率 = 1点でも当たったレース ÷ 買ったレース。1点 100円。"
         "期待値で買う買い方は確定オッズで計算しているので、実際に買う時点のオッズより少し良く出るおそれがある。"
         "不成立・特払の券種は、そのレースでは買わない（見送り）。")


class BacktestTables:
    """年ごとの確かめの結果（``BacktestReport``）を、設計書 16 の 7 の表1〜4 と、確率の当てはまりの表にする。"""

    def __init__(self, report: BacktestReport) -> None:
        self._report = report

    def tables(self) -> list[Table]:
        return [self._overview(), self._returns(), self._finish(), self._stages(), self._calibration(), self._conditions()]

    def _overview(self) -> Table:
        """表1. 券種ごとの的中率と回収率（全部の年の合計）。はじめに見る表。"""
        total = self._report.returns[self._report.returns[_YEAR] == TOTAL_YEAR]
        value_rules = [rule for rule in total[_RULE].unique() if str(rule).startswith(_VALUE_RULE_PREFIX)]
        rules = [MODEL_MARK_RULE, *value_rules, POPULARITY_MARK_RULE]
        rows = [self._overview_row(ticket_type, total[total[_TYPE] == ticket_type], rules)
                for ticket_type in total[_TYPE].unique()]
        columns = ["券種", *[f"{rule} の{name}" for rule in rules for name in ("的中率", "回収率")], "期待値で買ったレース"]
        years = "〜".join(str(year) for year in (self._report.years[0], self._report.years[-1]))
        return Table(columns, rows, title=f"表1. 券種ごとの的中率と回収率（{years}年の合計）", note=_NOTE)

    def _overview_row(self, ticket_type: str, rows: pd.DataFrame, rules: list[str]) -> list[object]:
        by_rule = rows.set_index(_RULE)
        cells: list[object] = [ticket_type]
        for rule in rules:
            cells += [self._percent(by_rule, rule, "的中率"), self._percent(by_rule, rule, "回収率")]
        value_rows = rows[rows[_RULE].astype(str).str.startswith(_VALUE_RULE_PREFIX)]
        cells.append(int(value_rows["買ったレース"].sum()) if not value_rows.empty else 0)
        return cells

    def _percent(self, by_rule: pd.DataFrame, rule: str, column: str) -> str:
        if rule not in by_rule.index:
            return "―"
        return f"{float(by_rule.loc[rule, column]) * 100:.1f}%"

    def _returns(self) -> Table:
        """表2. 券種ごとの的中率と回収率（買い方 × 券種 × 年）。"""
        table = self._report.returns.copy()
        for column in _RATE_COLUMNS:
            table[column] = table[column].map(lambda value: f"{value * 100:.1f}%")
        return Table(list(table.columns), table.values.tolist(), title="表2. 券種ごとの的中率と回収率（買い方 × 券種 × 年）", note=_NOTE)

    def _finish(self) -> Table:
        """表3. 着順の当たり具合（年ごと）。"""
        table = self._report.finish.copy()
        rate_columns = ["◎の勝率", "◎の3着以内率", "1番人気の勝率（参考）"]
        for column in rate_columns:
            table[column] = table[column].map(lambda value: f"{value * 100:.1f}%")
        loss_columns = [column for column in table.columns if "ログ損失" in column or column.startswith("同（")]
        for column in loss_columns:
            table[column] = table[column].map(lambda value: round(float(value), 4))
        return Table(list(table.columns), table.values.tolist(), title="表3. 着順（⑦）の当たり具合（年ごと）",
                     note="ログ損失は小さいほど良い。1着が1頭に決まるレースだけで測る。単勝オッズは参考（オッズはモデルの特徴量に入れていない）。")

    def _stages(self) -> Table:
        """表4. 前半と後半の予想の当たり具合（年ごと）。"""
        stages = self._report.stages
        order = list(dict.fromkeys(zip(stages[KIND], stages[METRIC])))
        pivot = stages.pivot_table(index=[KIND, METRIC], columns=YEAR, values=VALUE, dropna=False).reindex(order).round(4)
        rows = [[kind, metric, *values] for (kind, metric), values in zip(pivot.index, pivot.values.tolist())]
        return Table([KIND, METRIC, *[str(year) for year in pivot.columns]], rows,
                     title="表4. 前半と後半の予想（①〜⑥）の当たり具合（年ごと）",
                     note="どれも、その年より前だけで学習したモデルの予測で測った値。ログ損失と MAE は小さいほど良く、正解率・順位相関・幅に入った割合（80% に近いほど良い）は大きいほど良い。")

    def _calibration(self) -> Table:
        table = self._report.calibration.round(4)
        return Table(list(table.columns), table.values.tolist(), title="3着以内の確率の当てはまり（全部の年）",
                     note="出した確率の平均と、実際に3着以内だった割合が近いほど良い。")

    def _conditions(self) -> Table:
        """学習に使った設定と、年ごとのならしの指数 λ。"""
        rows = [[f"{year}年の λ（2着・3着の割り当てのならしの指数）", value] for year, value in self._report.order_lambdas.items()]
        settings = self._report.settings
        rows += [["LightGBM の設定", str(settings["lightgbm"])], ["CatBoost の設定", str(settings["catboost"])]]
        return Table(["項目", "値"], rows, title="確かめの条件")
