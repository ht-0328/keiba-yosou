"""買い目の成績: 買い目に払戻を当て、期間ごとに 投資・払戻・回収率（と 90% の幅）・的中・万馬券と10万馬券の的中・勝った日の割合・最大の落ち込み を数える。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

_YEN_PER_POINT = 100
_MAN, _JUMAN = 10_000, 100_000
_BOOTSTRAP_DRAWS = 1000
_SEED = 7
RESULT_COLUMNS: tuple[str, ...] = ("買い方", "期間", "対象レース", "買ったレース", "点数", "1レースの点数", "1日の投資", "投資", "払戻", "回収率",
                                   "回収率の90%の幅", "最高の1点を除く回収率", "的中レース", "的中率", "的中の実際÷見込み", "万馬券の的中", "10万馬券の的中", "最高配当",
                                   "勝った日の割合", "1日の損益の中央値", "最大の落ち込み", "最長の連敗（日）")
BREAKDOWN_COLUMNS: tuple[str, ...] = ("買い方", "期間", "軸", "値", "点数", "投資", "払戻", "回収率", "的中", "万馬券の的中", "10万馬券の的中")


@dataclass(frozen=True)
class TrifectaSimulator:
    """``tickets``（``race_id``・``first``・``second``・``third``）に ``results``（的中の組と ``payout``）を当てて成績にする。"""

    results: pd.DataFrame

    def settle(self, tickets: pd.DataFrame, races: pd.DataFrame) -> pd.DataFrame:
        """買い目に払戻（外れは 0）と開催日・期間を付ける。"""
        settled = tickets.merge(self.results, on=["race_id", "first", "second", "third"], how="left")
        settled["payout"] = settled["payout"].fillna(0).astype(int)
        return settled.merge(races[["race_id", "race_date", "period"]], on="race_id", how="left")

    def summarize(self, name: str, settled: pd.DataFrame, races: pd.DataFrame) -> list[dict]:
        """``races`` は対象レースの表（``race_id``・``race_date``・``period``）。期間ごとに1行。"""
        return [self._row(name, period, settled[settled["period"] == period], group) for period, group in races.groupby("period", sort=False)]

    def summarize_by_year(self, name: str, settled: pd.DataFrame, races: pd.DataFrame) -> list[dict]:
        """年ごとに1行（期間の列に「2024年」のように入れる）。年をまたいで同じ買い方が勝ち続けるかを見る。"""
        years = pd.to_datetime(races["race_date"]).dt.year
        rows = []
        for year, group in races.groupby(years, sort=True):
            chosen = settled[settled["race_id"].isin(group["race_id"])]
            rows.append(self._row(name, f"{year}年", chosen, group))
        return rows

    def breakdown(self, name: str, settled: pd.DataFrame, axis: str, values: pd.Series) -> list[dict]:
        """期間 × ``values``（買い目ごとの分け方の値。index は ``settled`` と同じ）ごとの点数・払戻・回収率。"""
        table = settled.assign(_value=values.to_numpy())
        rows = []
        for (period, value), group in table.groupby(["period", "_value"], sort=True):
            invested = len(group) * _YEN_PER_POINT
            returned = int(group["payout"].sum())
            rows.append({"買い方": name, "期間": period, "軸": axis, "値": value, "点数": len(group), "投資": f"{invested:,}円",
                         "払戻": f"{returned:,}円", "回収率": f"{returned / invested:.1%}", "的中": int((group["payout"] > 0).sum()),
                         "万馬券の的中": int((group["payout"] >= _MAN).sum()), "10万馬券の的中": int((group["payout"] >= _JUMAN).sum())})
        return rows

    def _row(self, name: str, period: str, settled: pd.DataFrame, races: pd.DataFrame) -> dict:
        points = len(settled)
        invested = points * _YEN_PER_POINT
        returned = int(settled["payout"].sum())
        per_race = settled.groupby("race_id")["payout"].sum()
        hit_races = int((per_race > 0).sum())
        bought = int(settled["race_id"].nunique())
        by_day = self._by_day(settled)
        low, high = self._bootstrap_range(by_day)
        best = int(settled["payout"].max()) if points else 0
        return {
            "買い方": name, "期間": period, "対象レース": len(races), "買ったレース": bought, "点数": points,
            "1レースの点数": round(points / bought, 1) if bought else 0.0,
            "1日の投資": f"{by_day['invest'].mean():,.0f}円" if len(by_day) else "—",
            "投資": f"{invested:,}円", "払戻": f"{returned:,}円", "回収率": f"{returned / invested:.1%}" if invested else "—",
            "回収率の90%の幅": f"{low:.1%}〜{high:.1%}" if invested else "—",
            "最高の1点を除く回収率": f"{(returned - best) / invested:.1%}" if invested else "—",
            "的中レース": hit_races, "的中率": f"{hit_races / bought:.1%}" if bought else "—",
            "的中の実際÷見込み": self._hits_vs_expected(settled),
            "万馬券の的中": int((settled["payout"] >= _MAN).sum()), "10万馬券の的中": int((settled["payout"] >= _JUMAN).sum()),
            "最高配当": f"{best:,}円" if points else "—",
            "勝った日の割合": f"{(by_day['profit'] > 0).mean():.0%}" if len(by_day) else "—",
            "1日の損益の中央値": f"{by_day['profit'].median():+,.0f}円" if len(by_day) else "—",
            "最大の落ち込み": f"{self._max_drawdown(by_day):+,.0f}円" if len(by_day) else "—",
            "最長の連敗（日）": self._longest_losing_days(by_day),
        }

    def _hits_vs_expected(self, settled: pd.DataFrame) -> str:
        """当たった点数 ÷ 買い目の確率の合計。1 なら組の確率は当たり具合と合っている。1 より小さいほど、選んだ組の確率が高く出すぎている。"""
        if settled.empty or "probability" not in settled.columns:
            return "—"
        expected = float(settled["probability"].sum())
        hits = int((settled["payout"] > 0).sum())
        return f"{hits / expected:.2f}" if expected > 0 else "—"

    def _by_day(self, settled: pd.DataFrame) -> pd.DataFrame:
        if settled.empty:
            return pd.DataFrame(columns=["points", "payout", "invest", "profit"])
        by_day = settled.groupby("race_date").agg(points=("payout", "size"), payout=("payout", "sum")).sort_index()
        by_day["invest"] = by_day["points"] * _YEN_PER_POINT
        by_day["profit"] = by_day["payout"] - by_day["invest"]
        return by_day

    def _bootstrap_range(self, by_day: pd.DataFrame) -> tuple[float, float]:
        """開催日を単位にしたブートストラップの 90% の幅（回収率）。"""
        if by_day.empty:
            return float("nan"), float("nan")
        rng = np.random.default_rng(_SEED)
        picks = rng.integers(0, len(by_day), size=(_BOOTSTRAP_DRAWS, len(by_day)))
        invested = by_day["invest"].to_numpy()[picks].sum(axis=1)
        returned = by_day["payout"].to_numpy()[picks].sum(axis=1)
        ratio = returned / np.clip(invested, 1, None)
        return float(np.percentile(ratio, 5)), float(np.percentile(ratio, 95))

    def _max_drawdown(self, by_day: pd.DataFrame) -> float:
        """累計の損益が、それまでの最高からいちばん落ち込んだ額（負の値）。"""
        cumulative = by_day["profit"].cumsum()
        return float((cumulative - cumulative.cummax()).min())

    def _longest_losing_days(self, by_day: pd.DataFrame) -> int:
        """1点も当たらなかった日が最長で何日続いたか。"""
        longest = current = 0
        for payout in by_day["payout"]:
            current = current + 1 if payout == 0 else 0
            longest = max(longest, current)
        return longest
