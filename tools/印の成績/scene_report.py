"""場面（クラス・競馬場・頭数・売上・芝ダ）ごとの、◎ の成績と上乗せの表を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.win_value import HIGH

from 共通.bootstrap_interval import BootstrapInterval
from 共通.perf import STAKE_YEN, percent
from 共通.render import Table

from 今週の予想.forecast_columns import EXPECTATION, MARK, MARKET_TOP3, MARKET_WIN, PROBABILITY, WIN_PROBABILITY
from 今週の予想.mark_rule import TOP_MARK

from 今週の予想.mark_tickets import RULE
from 印の成績.scene_bands import AXES, BANDS, UNKNOWN
from 印の成績.ticket_payouts import PAYOUT
from 今週の予想.ticket_rules import PLACE_LABEL, POINT_YEN
from 今週の予想.torigami_filter import DROPPED

#: 確率の端の丸め（ログ損失が無限大にならないように）。
_EDGE = 1e-6


class SceneReport:
    """印を付けた表（``BacktestMarker.mark``）と買い目の表（``TicketPayouts.attach`` → ``TorigamiFilter.apply`` のあと）と、
    レースの場面の帯（``SceneBands.build``）から、場面ごとの表（表10）を作る（研究「回収率100超の施策」の施策4）。

    軸（クラス・競馬場・頭数・単勝の売上・芝ダ）ごとに帯で分け、帯ごとに、レース数、◎ の単勝回収率と 90% の幅（全体と期待度「高」）、
    複勝（期待値 1.25 以上）の点数と回収率、上乗せ（3着以内と1着の、市場の見立てのログ損失 − モデルのログ損失。×1000。正ならモデルが市場より正しい）を出す。
    場面で絞る決まりを決めるための表ではなく、上乗せが場面でどう違うかを測る表（決まりはテスト期間の結果からは選ばない）。
    """

    def table(self, marked: pd.DataFrame, tickets: pd.DataFrame, bands: pd.DataFrame) -> Table:
        horses = marked.merge(bands, on="race_id", how="left")
        place = tickets[(tickets[RULE] == PLACE_LABEL) & (tickets[DROPPED] == "")].merge(bands, on="race_id", how="left")
        headers = ["軸", "帯", "レース数", "◎の単勝回収率", "90%の幅", "期待度 高のレース", "高の◎の単勝回収率", "90%の幅",
                   "複勝の点数", "複勝の回収率", "上乗せ（3着以内）", "上乗せ（1着）"]
        rows = []
        for axis in AXES:
            names = [*BANDS[axis], UNKNOWN]
            present = set(horses[axis].fillna(UNKNOWN).unique())
            for band in [name for name in names if name in present]:
                rows.append(self._row(axis, band, horses[horses[axis].fillna(UNKNOWN) == band], place[place[axis].fillna(UNKNOWN) == band]))
        note = ("場面はレースの条件（事実表）と確定の単勝の票数合計から付けた。単勝の売上の帯は、この表のレースの中での四分位。"
                "◎の単勝回収率は 1点 100円、90% の幅は開催日を単位にしたブートストラップ。複勝は表7 の「複勝」（期待値 1.25 以上を高い順に最大3点。トリガミは外す）。"
                "上乗せは、市場の見立て（オッズから見た3着以内率・勝率）のログ損失からモデル（3着以内の確率・1着になる確率）のログ損失を引いて 1000倍した値。"
                "正ならモデルのほうが市場より確率が正しく、大きいほど上乗せが大きい。"
                "この表は上乗せが場面でどう違うかを測るもので、場面で買うレースを絞る決まりはここからは決めない（結果に合わせた選び方になるため）。"
                "確定オッズでの検証なので、実際に買うときより良く出る。")
        return Table(headers, rows, title="10. 場面ごとの ◎ の成績と上乗せ（参考）", note=note)

    def _row(self, axis: str, band: str, horses: pd.DataFrame, place: pd.DataFrame) -> list[str]:
        tops = horses[horses[MARK] == TOP_MARK]
        high = tops[tops[EXPECTATION] == HIGH]
        return [axis, band, f"{horses['race_id'].nunique():,}", *self._win_cells(tops), f"{len(high):,}", *self._win_cells(high),
                f"{len(place):,}", self._place_rate(place),
                self._uplift(horses, PROBABILITY, MARKET_TOP3, horses["finish"] <= 3), self._uplift(horses, WIN_PROBABILITY, MARKET_WIN, horses["finish"] == 1)]

    def _win_cells(self, tops: pd.DataFrame) -> list[str]:
        """◎ の単勝回収率と 90% の幅。"""
        if tops.empty:
            return ["—", "—"]
        stake = STAKE_YEN * len(tops)
        low, high = BootstrapInterval().of(tops["race_date"], pd.Series(float(STAKE_YEN), index=tops.index), tops["win_payout"].astype(float))
        return [percent(float(tops["win_payout"].sum()) / stake), f"{percent(low)}〜{percent(high)}"]

    def _place_rate(self, place: pd.DataFrame) -> str:
        if place.empty:
            return "—"
        return percent(float(place[PAYOUT].sum()) / (POINT_YEN * len(place)))

    def _uplift(self, horses: pd.DataFrame, model: str, market: str, label: pd.Series) -> str:
        """市場のログ損失 − モデルのログ損失（×1000）。どちらかの列が無い・値が無ければ「—」。"""
        if model not in horses.columns or market not in horses.columns:
            return "—"
        frame = pd.DataFrame({"p": pd.to_numeric(horses[model], errors="coerce"), "q": pd.to_numeric(horses[market], errors="coerce"),
                              "y": label.fillna(False).astype(int)}).dropna()
        if frame.empty:
            return "—"
        return f"{(_log_loss(frame['y'], frame['q']) - _log_loss(frame['y'], frame['p'])) * 1000:+.2f}"


def _log_loss(label: pd.Series, probability: pd.Series) -> float:
    y = label.to_numpy(dtype=float)
    p = np.clip(probability.to_numpy(dtype=float), _EDGE, 1.0 - _EDGE)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))
