"""買った買い目から、券種ごと・人気ごと・年ごとの表と、運用の目安の表を作る。"""

from __future__ import annotations

from itertools import product

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
from .candidate_columns import COVER, FIRST_HORSE, ODDS, RACE, TICKET
from .payout_table import PAYOUT
from .race_columns import GRADED

#: 1点の賭け金（円）。
STAKE = 100.0
#: 1レースの点数の分布の区切り。
_POINT_BANDS = [(1, 1, "1点"), (2, 3, "2〜3点"), (4, 5, "4〜5点"), (6, 10, "6〜10点"), (11, 10_000, "11点以上")]
#: 買い目のオッズの帯。
_ODDS_BANDS = [0, 2, 5, 10, 30, 100, 300, 1000, 10_000, 1e9]


class BacktestSummary:
    """買った買い目（全区切りのテスト期間）から、利用者が知りたい表を作る。

    - ``bought``: テスト期間に買った買い目（``WindowResult.bought`` を全区切りぶん並べたもの）。
    - ``reference``: 参考（検証で回収率 100% に届かなかった券種も買ったとき）。
    - ``choices``: 区切り × 券種 の選んだ買い方。``fits``: 区切りごとの勝率の出し方。
    - ``races``: テスト期間の全出走（1行 = 1頭。レースID・開催日・馬番・確定の単勝人気・払戻）。対象レース数や人気を引くのに使う。
    - ``race_tables``: テスト期間のレース単位の表（重賞か など。``WindowResult.races``）。
    - ``candidates``: テスト期間の、印のルールで作った全部の買い目（カットの前。確率のずれの表に使う）。
    """

    def __init__(self, bought: pd.DataFrame, reference: pd.DataFrame, choices: pd.DataFrame, fits: pd.DataFrame,
                 races: pd.DataFrame, race_tables: pd.DataFrame, candidates: pd.DataFrame) -> None:
        self._races = races
        self._graded = set(race_tables.loc[race_tables[GRADED], RACE])
        self._candidates = candidates
        self._bought = self._with_race_info(bought)
        self._reference = self._with_race_info(reference)
        self._choices = choices
        self._fits = fits
        self._format = TableFormatter()

    def tables(self) -> list[Table]:
        return [
            self._overall(), self._by_ticket(self._bought, "券種ごとの成績（買うと決めた券種だけ。7つの区切りのテスト期間の合計）"),
            self._by_kind(), self._cover_hits(),
            self._by_ticket(self._bought[self._bought[RACE].isin(self._graded)], "重賞だけの券種ごとの成績"),
            self._by_popularity(TicketType.WIN), self._by_popularity(TicketType.PLACE),
            self._by_year(), self._by_year_and_ticket(), self._operation(), self._points_per_race(),
            self._by_odds_band(), CalibrationTable().table(self._candidates), self._choices_table(), self._fits_table(),
            self._by_ticket(self._reference, "参考: 検証で回収率 100% に届かなかった券種も、選んだ買い方で買ったとき"),
            self._favorite_baseline(),
        ]

    def _with_race_info(self, bought: pd.DataFrame) -> pd.DataFrame:
        """買い目に、開催日・年と、1頭目の馬の確定の単勝人気を付ける。"""
        dates = self._races.drop_duplicates(RACE_ID)[[RACE_ID, RACE_DATE]].rename(columns={RACE_ID: RACE})
        popularity = self._races[[RACE_ID, HORSE_NO, POPULARITY]].rename(columns={RACE_ID: RACE, HORSE_NO: FIRST_HORSE})
        popularity = popularity.assign(**{FIRST_HORSE: popularity[FIRST_HORSE].astype(int)})
        merged = bought.assign(**{FIRST_HORSE: bought[FIRST_HORSE].astype(int)}).merge(dates, on=RACE, how="left")
        merged = merged.merge(popularity, on=[RACE, FIRST_HORSE], how="left")
        return merged.assign(年=merged[RACE_DATE].dt.year, 賭け金=STAKE, 的中=merged[PAYOUT] > 0)

    def _summary_row(self, rows: pd.DataFrame, races_total: int | None = None) -> dict[str, object]:
        """点数・投資・払戻・回収率・的中の数と、回収率の推定幅。"""
        points = len(rows)
        races = rows.groupby(RACE)[PAYOUT].sum()
        low, high = BootstrapInterval().of(rows[RACE_DATE], rows["賭け金"], rows[PAYOUT]) if points else (np.nan, np.nan)
        result = {
            "勝負したレース数": int(races.size), "点数": points, "的中点数": int(rows["的中"].sum()),
            "的中率（点）": float(rows["的中"].mean()) if points else np.nan,
            "的中レース数": int((races > 0).sum()), "的中率（レース）": float((races > 0).mean()) if points else np.nan,
            "投資（円）": int(points * STAKE), "払戻（円）": int(rows[PAYOUT].sum()),
            "回収率": float(rows[PAYOUT].sum() / (points * STAKE)) if points else np.nan,
            "回収率の90%の下限": low, "回収率の90%の上限": high,
        }
        result["1レースあたりの点数"] = points / result["勝負したレース数"] if points else np.nan
        return result if races_total is None else {"対象レース数": races_total, **result}

    def _overall(self) -> Table:
        total_races = int(self._races[RACE_ID].nunique())
        frame = pd.DataFrame([{"まとめ": "全券種の合計", **self._summary_row(self._bought, total_races)}])
        return self._format.table(frame, "全体の成績（7つの区切りのテスト期間 = 2023年1月〜2026年9月の合計）",
                                  note="1点 100円。回収率 = 払戻 ÷ 投資。90%の幅は開催日を単位にしたブートストラップ。"
                                       "確定オッズで期待値を見積もっているので、実際に買う時点（締め切り前のオッズ）より楽観側。")

    def _by_ticket(self, bought: pd.DataFrame, title: str) -> Table:
        windows = self._choices[self._choices["テストで買うか"] == "買う"].groupby(TICKET)[WINDOW].nunique()
        rows = [{"券種": ticket.label, "買った区切りの数": f"{int(windows.get(ticket.label, 0))} / 7",
                 **self._summary_row(bought[bought[TICKET] == ticket.label])} for ticket in TicketType]
        return self._format.table(pd.DataFrame(rows), title)

    def _by_kind(self) -> Table:
        """券種ごとに、いつも買う（◎から）買い目と、押さえ（◎が危ういときの相手同士）の買い目を分けた成績。"""
        rows = [{"券種": ticket.label, "種類": "押さえ" if cover else "いつも買う（◎から）",
                 **self._summary_row(self._bought[(self._bought[TICKET] == ticket.label) & (self._bought[COVER] == cover)])}
                for ticket, cover in product(TicketType, (False, True))]
        frame = pd.DataFrame(rows)
        return self._format.table(frame[frame["点数"] > 0], "券種 × 種類（いつも買う・押さえ）の成績")

    def _cover_hits(self) -> Table:
        """押さえを買ったレースのうち、押さえが当たったレースと、◎からの買い目は外れて押さえだけが当たったレースの数。"""
        hits = self._bought.assign(当たり=self._bought[PAYOUT] > 0)
        covered = hits[hits[RACE].isin(set(hits.loc[hits[COVER], RACE]))]
        by_race = covered.groupby([RACE, COVER])["当たり"].any().unstack(fill_value=False)             .reindex(columns=[False, True], fill_value=False)
        rows = [
            ("押さえを買ったレース", len(by_race)),
            ("押さえが当たったレース", int(by_race[True].sum())),
            ("そのうち、◎からの買い目は外れて押さえだけが当たったレース", int((by_race[True] & ~by_race[False]).sum())),
        ]
        return self._format.table(pd.DataFrame(rows, columns=["項目", "レース数"]), "押さえで拾えたレース")

    def _by_popularity(self, ticket: TicketType) -> Table:
        rows = self._bought[self._bought[TICKET] == ticket.label]
        grouped = [{"人気": f"{int(popularity)}番人気", **self._short_row(group)}
                   for popularity, group in rows.groupby(POPULARITY) if not np.isnan(popularity)]
        frame = pd.DataFrame(grouped) if grouped else pd.DataFrame(columns=["人気"])
        return self._format.table(frame, f"{ticket.label}: 人気ごとの点数・的中率・回収率（テスト期間の合計）",
                                  note="人気は確定の単勝人気。")

    def _short_row(self, rows: pd.DataFrame) -> dict[str, object]:
        points = len(rows)
        return {
            "点数": points, "的中点数": int(rows["的中"].sum()),
            "的中率": float(rows["的中"].mean()) if points else np.nan,
            "払戻（円）": int(rows[PAYOUT].sum()),
            "回収率": float(rows[PAYOUT].sum() / (points * STAKE)) if points else np.nan,
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
        per_race = bought.groupby(RACE).agg(点数=(PAYOUT, "size"), 払戻=(PAYOUT, "sum"), 開催日=(RACE_DATE, "first"))
        per_race = per_race.sort_values("開催日", kind="stable")
        balance = (per_race["払戻"] - per_race["点数"] * STAKE).cumsum()
        drawdown = float((balance.cummax().clip(lower=0) - balance).max()) if len(balance) else np.nan
        days = per_race.groupby("開催日").size()
        years = bought["年"].nunique()
        rows = [
            ("勝負するレースの数（1年あたり）", len(per_race) / years if years else np.nan),
            ("勝負するレースの数（1開催日あたり・平均）", float(days.mean()) if len(days) else np.nan),
            ("勝負するレースの数（1開催日あたり・最大）", float(days.max()) if len(days) else np.nan),
            ("1レースあたりの点数（平均）", float(per_race["点数"].mean()) if len(per_race) else np.nan),
            ("1レースあたりの点数（最大）", float(per_race["点数"].max()) if len(per_race) else np.nan),
            ("1レースあたりの投資（平均・円）", float(per_race["点数"].mean() * STAKE) if len(per_race) else np.nan),
            ("1開催日あたりの投資（平均・円）", float((per_race.groupby("開催日")["点数"].sum() * STAKE).mean()) if len(per_race) else np.nan),
            ("1年あたりの投資（円）", float(len(bought) * STAKE / years) if years else np.nan),
            ("1年あたりの払戻（円）", float(bought[PAYOUT].sum() / years) if years else np.nan),
            ("通算の損益（円）", float(bought[PAYOUT].sum() - len(bought) * STAKE)),
            ("いちばん深い落ち込み（円）= 用意しておきたい資金の目安", drawdown),
            ("いちばん長い連敗（勝負したレースの数）", float(self._longest_losing_streak(per_race["払戻"]))),
        ]
        return self._format.table(pd.DataFrame(rows, columns=["項目", "値"]), "運用の目安（1点 100円のとき）",
                                  note="落ち込み = 通算の損益が、それまでのいちばん高いところから下がった幅。1点の金額を上げると、比例して大きくなる。")

    def _longest_losing_streak(self, payouts: pd.Series) -> int:
        losing = (payouts.to_numpy() <= 0).astype(int)
        if len(losing) == 0:
            return 0
        breaks = np.flatnonzero(np.r_[1, np.diff(losing) != 0, 1])
        runs = np.diff(breaks)
        values = losing[breaks[:-1]]
        return int(runs[values == 1].max()) if (values == 1).any() else 0

    def _points_per_race(self) -> Table:
        per_race = self._bought.groupby([RACE, TICKET]).size().rename("点数").reset_index()
        rows = [self._point_band_row(ticket.label, per_race[per_race[TICKET] == ticket.label]["点数"]) for ticket in TicketType]
        return self._format.table(pd.DataFrame(rows), "1レースあたりの点数の分布（券種ごと。その券種を買ったレースのうちの割合）")

    def _point_band_row(self, ticket: str, points: pd.Series) -> dict[str, object]:
        shares = {label: float(points.between(low, high).mean()) if len(points) else np.nan for low, high, label in _POINT_BANDS}
        return {"券種": ticket, "買ったレース数": len(points), **shares}

    def _by_odds_band(self) -> Table:
        band = pd.cut(self._bought[ODDS], _ODDS_BANDS, right=False)
        rows = [{"券種": ticket, "オッズの帯": f"{interval.left:g}〜{interval.right:g}倍", **self._short_row(group)}
                for (ticket, interval), group in self._bought.groupby([TICKET, band], observed=True)]
        return self._format.table(pd.DataFrame(rows), "買い目のオッズの帯ごとの成績（どんな買い目を買うことになるか）",
                                  note="複勝・ワイドのオッズは最低オッズ。")

    def _choices_table(self) -> Table:
        return self._format.table(self._choices, "区切りごとに検証期間で選んだ買い方",
                                  note="検証期間 = テストの直前の1年（最初の区切りだけ半年）。期待値の線は、当たりが30回以上ある線の中で、"
                                       "回収率の控えめな見積もりがいちばん高いもの。検証期間の回収率が 100% 以上の券種だけ、テスト期間で買う。")

    def _fits_table(self) -> Table:
        return self._format.table(self._fits, "区切りごとの勝率の出し方（検証期間で決めた重みと Stern の補正）",
                                  note="log(オッズから見た勝率) の重みが 1 で、ほかが 0 なら、市場の勝率そのまま。"
                                       "上げ下げの重みが大きいほど、その予想の上げ下げを効かせている。")

    def _favorite_baseline(self) -> Table:
        favorites = self._races[self._races[POPULARITY] == 1]
        rows = [
            {"買い方": "1番人気の単勝を全レース", "点数": len(favorites),
             "回収率": float(favorites[WIN_PAYOUT].fillna(0).sum() / (STAKE * len(favorites)))},
            {"買い方": "1番人気の複勝を全レース", "点数": len(favorites),
             "回収率": float(favorites[PLACE_PAYOUT].fillna(0).sum() / (STAKE * len(favorites)))},
        ]
        return self._format.table(pd.DataFrame(rows), "比べる目安: 同じテスト期間に1番人気を全部買ったとき")
