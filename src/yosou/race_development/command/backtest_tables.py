"""年ごとの確かめの結果を、表にする。"""

from __future__ import annotations

import pandas as pd

from 共通.render import Table

from ..betting import TOTAL_YEAR
from ..betting import value_line_choice as line
from ..evaluation import KIND, METRIC, VALUE, YEAR
from ..evaluation import unlabeled_race_table as unlabeled
from ..workflow import BacktestReport

#: まとめの表の列（``ReturnSummary`` の見出し）。
_RULE, _TYPE, _YEAR = "買い方", "券種", "年"
_RATE_COLUMNS = ("的中率", "回収率", "最大の払戻を除いた回収率")
#: 期待値で買う買い方（モデル）の名前（``ExpectedValueTicketRule`` の既定の名前）。
_MODEL_VALUE_RULE = line.MODEL_VALUE_RULE
_NOTE = ("回収率 = 払戻の合計 ÷ 賭け金の合計。的中率 = 1点でも当たったレース ÷ 買ったレース。1点 100円。"
         "期待値で買う買い方は確定オッズで計算しているので、実際に買う時点のオッズより少し良く出るおそれがある。"
         "不成立・特払の券種は、そのレースでは買わない（見送り）。"
         "「（オッズ入り）」は、オッズを着順の段にだけ特徴量として入れた ⑦ で買ったもの（別の比べ。この設計の既定ではない）。")


class BacktestTables:
    """年ごとの確かめの結果（``BacktestReport``）を、設計書 16 の 7 の表1〜5 と、確率の当てはまりの表、
    16 の 4 の正解を作らなかったレースの表にする。"""

    def __init__(self, report: BacktestReport) -> None:
        self._report = report

    def tables(self) -> list[Table]:
        return [
            self._overview(), self._returns(), self._finish(), self._stages(), self._calibration(),
            *self._line_tables(), self._unlabeled(), self._unlabeled_examples(), self._conditions(),
        ]

    def _years_text(self) -> str:
        return "〜".join(str(year) for year in (self._report.years[0], self._report.years[-1]))

    def _overview(self) -> Table:
        """表1. 券種ごとの的中率と回収率（全部の年の合計）。はじめに見る表。"""
        total = self._report.returns[self._report.returns[_YEAR] == TOTAL_YEAR]
        rules = list(total[_RULE].unique())
        rows = [self._overview_row(ticket_type, total[total[_TYPE] == ticket_type], rules)
                for ticket_type in total[_TYPE].unique()]
        columns = ["券種", *[f"{rule} の{name}" for rule in rules for name in ("的中率", "回収率")],
                   f"{_MODEL_VALUE_RULE} で買ったレース"]
        timing = self._report.timing.label
        return Table(columns, rows, title=f"表1. 券種ごとの的中率と回収率（{self._years_text()}年の合計・{timing}の時点）", note=_NOTE)

    def _overview_row(self, ticket_type: str, rows: pd.DataFrame, rules: list[str]) -> list[object]:
        by_rule = rows.set_index(_RULE)
        cells: list[object] = [ticket_type]
        for rule in rules:
            cells += [self._percent(by_rule, rule, "的中率"), self._percent(by_rule, rule, "回収率")]
        value_rows = rows[rows[_RULE] == _MODEL_VALUE_RULE]
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
            table[column] = table[column].map(self._rate)
        return Table(list(table.columns), table.values.tolist(), title="表2. 券種ごとの的中率と回収率（買い方 × 券種 × 年）", note=_NOTE)

    def _finish(self) -> Table:
        """表3. 着順の当たり具合（年ごと）。"""
        table = self._report.finish.copy()
        rate_columns = ["◎の勝率", "◎の3着以内率", "1番人気の勝率（参考）"]
        for column in rate_columns:
            table[column] = table[column].map(self._rate)
        loss_columns = [column for column in table.columns if "ログ損失" in column or column.startswith("同（")]
        for column in loss_columns:
            table[column] = table[column].map(self._loss)
        return Table(list(table.columns), table.values.tolist(), title="表3. 着順（⑦）の当たり具合（年ごと）",
                     note="ログ損失は小さいほど良い。1着が1頭に決まるレースだけで測る。単勝オッズは参考（オッズはモデルの特徴量に入れていない）。"
                          "S を外したモデル・T を外したモデルは、⑦ から前半の予想の結果（S）・後半の予想の結果（T）を1つずつ外して学習したもの"
                          "（どちらも ⑦ と同じ行で学習する）。オッズを足したモデルは、オッズを着順の段にだけ入れた参考（確定オッズを使う。当日の時点だけ）。")

    def _stages(self) -> Table:
        """表4. 前半と後半の予想の当たり具合（年ごと）。"""
        stages = self._report.stages
        order = list(dict.fromkeys(zip(stages[KIND], stages[METRIC])))
        pivot = stages.pivot_table(index=[KIND, METRIC], columns=YEAR, values=VALUE, dropna=False).reindex(order).round(4)
        rows = [[kind, metric, *values] for (kind, metric), values in zip(pivot.index, pivot.values.tolist())]
        return Table([KIND, METRIC, *[str(year) for year in pivot.columns]], rows,
                     title="表4. 前半と後半の予想（①〜⑥）の当たり具合（年ごと）",
                     note="どれも、その年より前だけで学習したモデルの予測で測った値。ログ損失と MAE は小さいほど良く、正解率・順位相関・幅に入った割合（80% に近いほど良い）は大きいほど良い。"
                          "80% の幅は、検証データの後半で決めた倍率で広げた（狭めた）もの。")

    def _calibration(self) -> Table:
        table = self._report.calibration.round(4)
        return Table(list(table.columns), table.values.tolist(), title="3着以内の確率の当てはまり（全部の年）",
                     note="出した確率の平均と、実際に3着以内だった割合が近いほど良い。")

    def _line_tables(self) -> list[Table]:
        """表5. 期待値の線と券種の配分（買い方ごとに3つ）。"""
        tables: list[Table] = []
        for label in self._report.line_totals:
            tables += [self._line_totals(label), self._chosen_lines(label), self._allocation(label)]
        return tables

    def _line_totals(self, label: str) -> Table:
        table = self._report.line_totals[label].copy()
        table[line.RETURN_RATE] = table[line.RETURN_RATE].map(self._rate)
        return Table(list(table.columns), table.values.tolist(),
                     title=f"表5a. 期待値の線ごとの回収率（{label}。{self._years_text()}年の合計。参考）",
                     note="この表を見て線を選ぶと、確かめる年に合わせることになる。線は表5b のように、確かめる年より前の年だけで選ぶ。")

    def _chosen_lines(self, label: str) -> Table:
        table = self._report.chosen_lines[label].copy()
        for column in (line.PRIOR_RATE, line.RETURN_RATE):
            table[column] = table[column].map(self._rate)
        return Table(list(table.columns), table.values.tolist(),
                     title=f"表5b. 期待値の線を、確かめる年より前の年だけで選んだ場合（{label}。券種 × 年）",
                     note=f"各年の線は、その年より前の年の回収率がいちばん高い線（前の年までに {line.MIN_PRIOR_POINTS}点以上買った線だけ）。"
                          "最初の年は選べないので出さない。")

    def _allocation(self, label: str) -> Table:
        table = self._report.allocation[label].copy()
        table[line.RETURN_RATE] = table[line.RETURN_RATE].map(self._rate)
        return Table(list(table.columns), table.values.tolist(),
                     title=f"表5c. 券種の配分を、確かめる年より前の年だけで決めた場合（{label}。年ごと）",
                     note=f"候補は、券種ごとの印どおりと、期待値が線以上（{', '.join(str(value) for value in line.VALUE_LINES)}）。"
                          f"「{line.BEST_ONE}」は前の年までの回収率がいちばん高い（候補・券種）を1つだけ、"
                          f"「{line.OVER_BREAK_EVEN}」は前の年までの回収率が 100% 以上の（候補・券種）を全部、1点100円で買う。")

    def _unlabeled(self) -> Table:
        """正解を作らなかったレースの割合（設計書 16 の 4）。"""
        table = self._report.unlabeled.copy()
        for column in table.columns[3:]:
            table[column] = table[column].map(self._rate)
        return Table(list(table.columns), table.values.tolist(),
                     title="表6. 正解を作らなかったレースの割合（学習データの全部の年。理由ごと・条件ごと）",
                     note=f"①② は先頭と序盤の位置、③ は前半タイム（ペースの区分も）、⑥ は後半タイムの正解。1つのレースには、"
                          f"{'・'.join(unlabeled.LEADER_REASONS)}（①②）、{'・'.join(unlabeled.HALF_REASONS)}（③⑥）の順で最初に当てはまった理由を付ける。"
                          "ペースの区分の切り口の「区分なし」は、③ の正解を作らなかったレース。")

    def _unlabeled_examples(self) -> Table:
        examples = self._report.unlabeled_examples
        rows = [[race_id] for race_id in examples] or [["（先頭が決まらないレースは無かった）"]]
        return Table(["レースID"], rows, title="先頭が決まらないレース（新しい順に最大20）",
                     note="`uv run python tools/レース詳細/race.py <レースID>` の通過順と照らし合わせて、決まらない理由を目で見る。")

    def _conditions(self) -> Table:
        """学習に使った設定と、年ごとのならしの指数 λ。"""
        rows = [["予測した時点", self._report.timing.label]]
        rows += [[f"{year}年の λ（2着・3着の割り当てのならしの指数）", value] for year, value in self._report.order_lambdas.items()]
        settings = self._report.settings
        rows += [["LightGBM の設定", str(settings["lightgbm"])], ["CatBoost の設定", str(settings["catboost"])]]
        return Table(["項目", "値"], rows, title="確かめの条件")

    def _rate(self, value: object) -> str:
        """0〜1 の割合を「12.3%」の形にする。欠損値は「―」。"""
        number = float(value) if value is not None else float("nan")
        return "―" if pd.isna(number) else f"{number * 100:.1f}%"

    def _loss(self, value: object) -> object:
        """ログ損失を小数 4桁に丸める。欠損値（前日の時点のオッズを足したモデルなど）は「―」。"""
        number = float(value) if value is not None else float("nan")
        return "―" if pd.isna(number) else round(number, 4)
