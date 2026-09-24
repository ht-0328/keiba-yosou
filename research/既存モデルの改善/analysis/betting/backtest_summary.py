"""買った買い目から、券種ごと・条件ごと・人気ごと・年ごとの表と、運用の目安の表を作る（金額で数える）。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 共通.render import Table

from yosou.shared.dataset import HORSE_NO, RACE_DATE, RACE_ID
from yosou.shared.dataset.column_names import PLACE_PAYOUT, POPULARITY, WIN_PAYOUT

from 馬券の買い方の検証.analysis.ticket import TicketType

from ..comparison.table_formatter import TableFormatter
from ..scores import BootstrapInterval
from ..walk_forward import WINDOW
from .calibration_table import CalibrationTable
from .candidate_columns import FIRST_HORSE, GROUP, ODDS, RACE, RETURN, STAKE, TICKET
from .race_columns import FAVORITE_EXCLUDED, GRADED, UPSET

#: 比べる目安（1番人気を全部買う）の1点の金額（円）。
_BASELINE_STAKE = 100.0
#: 買い目のオッズの帯。
_ODDS_BANDS = [0, 2, 5, 10, 30, 100, 300, 1000, 10_000, 1e9]
#: 当たったか（払戻が 0 より大きいか）の列の名前。
_HIT = "的中"


class BacktestSummary:
    """買った買い目（全区切りのテスト期間）から、利用者が知りたい表を作る。金額（賭け金と払戻）で数える。

    - ``bought``: テスト期間に買った買い目（``WindowResult.bought`` を全区切りぶん並べたもの）。
    - ``reference``: 参考（検証で回収率 100% に届かなかった券種も買ったとき）。
    - ``choices``: 区切り × 券種 の選んだ線。``fits``: 区切りごとの勝率の出し方と線。
    - ``races``: テスト期間の全出走（1行 = 1頭。レースID・開催日・馬番・確定の単勝人気・払戻）。対象レース数や人気を引くのに使う。
    - ``race_tables``: テスト期間のレース単位の表（重賞か・1番人気を消したか・荒れそうか。``WindowResult.races``）。
    - ``candidates``: テスト期間の全部の買い目の候補（確率を補正したもの。期待値のカットの前。確率のずれの表に使う）。
    """

    def __init__(self, bought: pd.DataFrame, reference: pd.DataFrame, choices: pd.DataFrame, fits: pd.DataFrame,
                 races: pd.DataFrame, race_tables: pd.DataFrame, candidates: pd.DataFrame) -> None:
        self._races = races
        self._race_tables = race_tables
        self._candidates = candidates
        self._bought = self._with_race_info(bought)
        self._reference = self._with_race_info(reference)
        self._choices = choices
        self._fits = fits
        self._format = TableFormatter()

    def tables(self) -> list[Table]:
        return [
            self._overall(),
            self._by_ticket(self._bought, "券種ごとの成績（7つの区切りのテスト期間の合計）"),
            self._by_group(), self._by_condition(), self._tickets_per_race(),
            self._by_ticket(self._bought[self._bought[GRADED]], "重賞だけの券種ごとの成績"),
            self._by_popularity(TicketType.WIN), self._by_popularity(TicketType.PLACE),
            self._by_year(), self._by_year_and_ticket(), self._operation(), self._by_odds_band(),
            CalibrationTable().table(self._candidates), self._choices_table(), self._fits_table(),
            self._by_ticket(self._reference, "参考: 検証で回収率 100% に届かなかった券種も、選んだ線で買ったとき"),
            self._favorite_baseline(),
        ]

    def _with_race_info(self, bought: pd.DataFrame) -> pd.DataFrame:
        """買い目に、開催日・年・1頭目の馬の確定の単勝人気・レースの条件（重賞・1番人気を消した・荒れそう）を付ける。"""
        dates = self._races.drop_duplicates(RACE_ID)[[RACE_ID, RACE_DATE]].rename(columns={RACE_ID: RACE})
        popularity = self._races[[RACE_ID, HORSE_NO, POPULARITY]].rename(columns={RACE_ID: RACE, HORSE_NO: FIRST_HORSE})
        popularity = popularity.assign(**{FIRST_HORSE: popularity[FIRST_HORSE].astype(int)})
        conditions = self._race_tables[[RACE, GRADED, FAVORITE_EXCLUDED, UPSET]]
        merged = bought.assign(**{FIRST_HORSE: bought[FIRST_HORSE].astype(int)}).merge(dates, on=RACE, how="left")
        merged = merged.merge(popularity, on=[RACE, FIRST_HORSE], how="left").merge(conditions, on=RACE, how="left")
        return merged.assign(年=merged[RACE_DATE].dt.year, **{_HIT: merged[RETURN] > 0})

    def _summary_row(self, rows: pd.DataFrame, races_total: int | None = None) -> dict[str, object]:
        """勝負したレース数・点数・的中数・的中率・投資・払戻・回収率と、回収率の推定幅。"""
        points = len(rows)
        stake, payout = float(rows[STAKE].sum()), float(rows[RETURN].sum())
        races = rows.groupby(RACE)[RETURN].sum()
        low, high = BootstrapInterval().of(rows[RACE_DATE], rows[STAKE], rows[RETURN]) if points else (np.nan, np.nan)
        result = {
            "勝負したレース数": int(races.size), "点数": points, "的中数": int(rows[_HIT].sum()),
            "的中率（点）": float(rows[_HIT].mean()) if points else np.nan,
            "的中レース数": int((races > 0).sum()), "的中率（レース）": float((races > 0).mean()) if points else np.nan,
            "投資（円）": int(stake), "払戻（円）": int(payout), "回収率": payout / stake if stake else np.nan,
            "回収率の90%の下限": low, "回収率の90%の上限": high,
            "1レースあたりの点数": points / races.size if points else np.nan,
            "1レースあたりの投資（円）": stake / races.size if points else np.nan,
        }
        return result if races_total is None else {"対象レース数": races_total, **result}

    def _overall(self) -> Table:
        total_races = int(self._races[RACE_ID].nunique())
        frame = pd.DataFrame([{"まとめ": "全券種の合計", **self._summary_row(self._bought, total_races)}])
        return self._format.table(frame, "全体の成績（7つの区切りのテスト期間 = 2023年1月〜2026年9月の合計）",
                                  note="1レースの予算は 5,000円。券種は、券種全体の期待値の高い順に予算に入るところまで買う。"
                                       "回収率 = 払戻 ÷ 投資。90%の幅は開催日を単位にしたブートストラップ。"
                                       "確定オッズで期待値を見積もっているので、実際に買う時点（締め切り前のオッズ）より楽観側。")

    def _by_ticket(self, bought: pd.DataFrame, title: str) -> Table:
        windows = self._choices[self._choices["テストで買うか"] == "買う"].groupby(TICKET)[WINDOW].nunique()
        rows = [{"券種": ticket.label, "買った区切りの数": f"{int(windows.get(ticket.label, 0))} / 7",
                 **self._summary_row(bought[bought[TICKET] == ticket.label])} for ticket in TicketType]
        return self._format.table(pd.DataFrame(rows), title, note="的中率（点）= 的中数 ÷ 点数。")

    def _by_group(self) -> Table:
        """券種 × 組み合わせの種類（人気-穴・人気-人気・穴-穴・1頭軸・2頭軸・1着固定・1頭）の成績。"""
        rows = [{"券種": ticket, "組み合わせの種類": group, **self._summary_row(part)}
                for (ticket, group), part in self._bought.groupby([TICKET, GROUP])]
        frame = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["券種"])
        return self._format.table(frame, "券種 × 組み合わせの種類の成績")

    def _by_condition(self) -> Table:
        """レースの条件（1番人気を消したか・荒れそうか・重賞か）ごとの成績。"""
        conditions = [
            (FAVORITE_EXCLUDED, True, "1番人気を消したレース"), (FAVORITE_EXCLUDED, False, "1番人気を消さなかったレース"),
            (UPSET, True, "荒れそうと判定したレース"), (UPSET, False, "荒れそうでないレース"),
            (GRADED, True, "重賞"), (GRADED, False, "重賞以外"),
        ]
        rows = [{"条件": label, **self._summary_row(self._bought[self._bought[column].fillna(False) == flag])}
                for column, flag, label in conditions]
        return self._format.table(pd.DataFrame(rows), "レースの条件ごとの成績")

    def _tickets_per_race(self) -> Table:
        """1レースで買った券種の数の分布（券種で期待値を積んだ結果、いくつの券種を買ったか）。"""
        per_race = self._bought.groupby(RACE).agg(券種の数=(TICKET, "nunique"), 投資=(STAKE, "sum"), 払戻=(RETURN, "sum"))
        summary = per_race.groupby("券種の数").agg(レース数=("投資", "size"), 投資の平均=("投資", "mean"),
                                                 投資=("投資", "sum"), 払戻=("払戻", "sum"))
        summary["回収率"] = summary["払戻"] / summary["投資"]
        return self._format.table(summary.reset_index()[["券種の数", "レース数", "投資の平均", "回収率"]],
                                  "1レースで買った券種の数ごとの成績", note="投資の平均は1レースあたり（円）。")

    def _by_popularity(self, ticket: TicketType) -> Table:
        rows = self._bought[self._bought[TICKET] == ticket.label]
        grouped = [{"人気": f"{int(popularity)}番人気", **self._short_row(group)}
                   for popularity, group in rows.groupby(POPULARITY) if not np.isnan(popularity)]
        frame = pd.DataFrame(grouped) if grouped else pd.DataFrame(columns=["人気"])
        return self._format.table(frame, f"{ticket.label}: 人気ごとの点数・的中率・回収率（テスト期間の合計）",
                                  note="人気は確定の単勝人気。")

    def _short_row(self, rows: pd.DataFrame) -> dict[str, object]:
        points, stake, payout = len(rows), float(rows[STAKE].sum()), float(rows[RETURN].sum())
        return {
            "勝負したレース数": int(rows[RACE].nunique()), "点数": points, "的中数": int(rows[_HIT].sum()),
            "的中率": float(rows[_HIT].mean()) if points else np.nan,
            "投資（円）": int(stake), "払戻（円）": int(payout), "回収率": payout / stake if stake else np.nan,
        }

    def _by_year(self) -> Table:
        race_years = self._races.drop_duplicates(RACE_ID).assign(年=lambda frame: frame[RACE_DATE].dt.year)
        totals = race_years.groupby("年")[RACE_ID].nunique()
        rows = [{"年": int(year), **self._summary_row(self._bought[self._bought["年"] == year], int(totals[year]))}
                for year in totals.index]
        return self._format.table(pd.DataFrame(rows), "年ごとの成績（全券種の合計）",
                                  note="勝負したレース = 1点でも買ったレース。的中率（レース）= 勝負したレースのうち、1点でも当たったレースの割合。"
                                       "2026年は 9月まで。")

    def _by_year_and_ticket(self) -> Table:
        rows = [{"年": int(year), "券種": ticket, **self._short_row(group)}
                for (year, ticket), group in self._bought.groupby(["年", TICKET])]
        return self._format.table(pd.DataFrame(rows), "年 × 券種の成績")

    def _operation(self) -> Table:
        bought = self._bought
        per_race = bought.groupby(RACE).agg(点数=(STAKE, "size"), 投資=(STAKE, "sum"), 払戻=(RETURN, "sum"),
                                            開催日=(RACE_DATE, "first")).sort_values("開催日", kind="stable")
        balance = (per_race["払戻"] - per_race["投資"]).cumsum()
        drawdown = float((balance.cummax().clip(lower=0) - balance).max()) if len(balance) else np.nan
        days = per_race.groupby("開催日").agg(レース=("投資", "size"), 投資=("投資", "sum"))
        years = bought["年"].nunique()
        rows = [
            ("勝負するレースの数（1年あたり）", len(per_race) / years if years else np.nan),
            ("勝負するレースの数（1開催日あたり・平均）", float(days["レース"].mean()) if len(days) else np.nan),
            ("勝負するレースの数（1開催日あたり・最大）", float(days["レース"].max()) if len(days) else np.nan),
            ("1レースあたりの点数（平均）", float(per_race["点数"].mean()) if len(per_race) else np.nan),
            ("1レースあたりの投資（平均・円）", float(per_race["投資"].mean()) if len(per_race) else np.nan),
            ("1レースあたりの投資（最大・円）", float(per_race["投資"].max()) if len(per_race) else np.nan),
            ("1開催日あたりの投資（平均・円）", float(days["投資"].mean()) if len(days) else np.nan),
            ("1年あたりの投資（円）", float(bought[STAKE].sum() / years) if years else np.nan),
            ("1年あたりの払戻（円）", float(bought[RETURN].sum() / years) if years else np.nan),
            ("通算の損益（円）", float(bought[RETURN].sum() - bought[STAKE].sum())),
            ("いちばん深い落ち込み（円）= 用意しておきたい資金の目安", drawdown),
            ("いちばん長い連敗（勝負したレースの数）", float(self._longest_losing_streak(per_race["払戻"]))),
        ]
        return self._format.table(pd.DataFrame(rows, columns=["項目", "値"]), "運用の目安（1レースの予算 5,000円のとき）",
                                  note="落ち込み = 通算の損益が、それまでのいちばん高いところから下がった幅。")

    def _longest_losing_streak(self, payouts: pd.Series) -> int:
        losing = (payouts.to_numpy() <= 0).astype(int)
        if len(losing) == 0:
            return 0
        breaks = np.flatnonzero(np.r_[1, np.diff(losing) != 0, 1])
        runs = np.diff(breaks)
        values = losing[breaks[:-1]]
        return int(runs[values == 1].max()) if (values == 1).any() else 0

    def _by_odds_band(self) -> Table:
        band = pd.cut(self._bought[ODDS], _ODDS_BANDS, right=False)
        rows = [{"券種": ticket, "オッズの帯": f"{interval.left:g}〜{interval.right:g}倍", **self._short_row(group)}
                for (ticket, interval), group in self._bought.groupby([TICKET, band], observed=True)]
        return self._format.table(pd.DataFrame(rows), "買い目のオッズの帯ごとの成績（どんな買い目を買うことになるか）",
                                  note="複勝・ワイドのオッズは最低オッズ。")

    def _choices_table(self) -> Table:
        return self._format.table(self._choices, "区切りごとに検証期間で選んだ線",
                                  note="検証期間 = テストの直前の1年（最初の区切りだけ半年）。券種全体の期待値の線は、当たりが30回以上ある線の中で、"
                                       "回収率の控えめな見積もりがいちばん高いもの。検証期間の回収率が 100% 以上の券種だけ、テスト期間で買う。")

    def _fits_table(self) -> Table:
        return self._format.table(self._fits, "区切りごとの勝率の出し方と線（検証期間で決めた）",
                                  note="log(オッズから見た勝率) の重みが 1 で、ほかが 0 なら、市場の勝率そのまま。"
                                       "消の線 = 検証期間の1番人気の危険度の上位1割の境目。荒れそうの線 = 検証期間のレースの荒れそうな確率の上位3割の境目。")

    def _favorite_baseline(self) -> Table:
        favorites = self._races[self._races[POPULARITY] == 1]
        rows = [
            {"買い方": "1番人気の単勝を全レース（100円ずつ）", "点数": len(favorites),
             "回収率": float(favorites[WIN_PAYOUT].fillna(0).sum() / (_BASELINE_STAKE * len(favorites)))},
            {"買い方": "1番人気の複勝を全レース（100円ずつ）", "点数": len(favorites),
             "回収率": float(favorites[PLACE_PAYOUT].fillna(0).sum() / (_BASELINE_STAKE * len(favorites)))},
        ]
        return self._format.table(pd.DataFrame(rows), "比べる目安: 同じテスト期間に1番人気を全部買ったとき")
