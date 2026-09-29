"""切り口ごとの成績7つと、基準とのずれの検定。純粋な計算だけ（DB を読まない）。

- 成績は keiba-yosou の決まりどおり7つ（着別度数・勝率・連対率・複勝率・馬券外率・単勝回収率・複勝回収率）。
- 「ずれ」は複勝率で測る。基準の取り方は2通り:
  - **外の基準**（同じグレードの重賞全体、同じコースの全クラス）: どのレースにも同じ切り口があるもの
    （人気・脚質・枠）に使う。検定は二項検定（両側・正確）。
  - **レースの中の比べ**: 出走馬の構成がレースごとに違うもの（年齢・性別・所属・間隔・経験）に使う。
    その値の馬と、それ以外の馬の複勝率を比べる（2標本の比率の z 検定・両側）。
    3歳限定戦の「3歳」のように、レース全員が同じ値なら比べられない（検定なし）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

#: 払戻は 100 円あたりの円。回収率（%）の分母。
STAKE_YEN = 100


@dataclass(frozen=True)
class BandResult:
    """切り口の1つの値（帯）の成績と、基準とのずれ。"""

    label: str
    runs: int
    finish_counts: str
    win_pct: float
    quinella_pct: float
    place_pct: float
    out_pct: float
    win_roi: float
    place_roi: float
    base_place_pct: float | None  # 基準の複勝率（%）。無ければ None
    diff_pt: float | None         # 複勝率 − 基準（ポイント）
    p_value: float | None         # 両側の p 値。検定できなければ None

    def row(self) -> list[object]:
        """表の1行（切り口 | 出走数 | 着別度数 | …）。"""
        return [
            self.label, self.runs, self.finish_counts,
            _pct(self.win_pct), _pct(self.quinella_pct), _pct(self.place_pct), _pct(self.out_pct),
            _pct(self.win_roi), _pct(self.place_roi),
            _pct(self.base_place_pct) if self.base_place_pct is not None else "―",
            _signed_pt(self.diff_pt) if self.diff_pt is not None else "―",
            mark(self.p_value),
        ]


#: 帯の表の列名。
BAND_COLUMNS: tuple[str, ...] = (
    "切り口", "出走数", "着別度数", "勝率", "連対率", "複勝率", "馬券外率",
    "単勝回収率", "複勝回収率", "基準の複勝率", "差", "判定",
)


def perf_of(rows: pd.DataFrame) -> dict[str, float]:
    """出走の行の束の成績7つ。``finish`` の欠損（競走中止・失格）は着外に数える。"""
    runs = len(rows)
    finish = rows["finish"]
    win = int((finish == 1).sum())
    second = int((finish == 2).sum())
    third = int((finish == 3).sum())
    out = runs - win - second - third
    return {
        "runs": runs, "finish_counts": f"{win}-{second}-{third}-{out}",
        "win_pct": _rate(win, runs), "quinella_pct": _rate(win + second, runs),
        "place_pct": _rate(win + second + third, runs), "out_pct": _rate(out, runs),
        "win_roi": _rate(float(rows["win_payout"].fillna(0).sum()) / STAKE_YEN, runs),
        "place_roi": _rate(float(rows["place_payout"].fillna(0).sum()) / STAKE_YEN, runs),
    }


def against_base(label: str, rows: pd.DataFrame, base_rate: float | None) -> BandResult:
    """外の基準（割合 0〜1）と比べた帯。基準が無ければずれ無しで返す。"""
    perf = perf_of(rows)
    hits = int((rows["finish"] <= 3).sum())
    if base_rate is None or perf["runs"] == 0:
        return BandResult(label=label, **perf, base_place_pct=None, diff_pt=None, p_value=None)
    return BandResult(
        label=label, **perf, base_place_pct=base_rate * 100,
        diff_pt=perf["place_pct"] - base_rate * 100,
        p_value=binomial_p(hits, perf["runs"], base_rate),
    )


def against_rest(label: str, rows: pd.DataFrame, rest: pd.DataFrame) -> BandResult:
    """レースの中の比べ（その値の馬 vs それ以外の馬）。``rest`` が空なら検定なし。"""
    perf = perf_of(rows)
    if len(rest) == 0 or perf["runs"] == 0:
        return BandResult(label=label, **perf, base_place_pct=None, diff_pt=None, p_value=None)
    rest_rate = float((rest["finish"] <= 3).mean())
    hits, rest_hits = int((rows["finish"] <= 3).sum()), int((rest["finish"] <= 3).sum())
    return BandResult(
        label=label, **perf, base_place_pct=rest_rate * 100,
        diff_pt=perf["place_pct"] - rest_rate * 100,
        p_value=two_proportion_p(hits, perf["runs"], rest_hits, len(rest)),
    )


def binomial_p(hits: int, runs: int, rate: float) -> float:
    """二項検定（両側・正確）。観測と同じかそれより起きにくい結果の確率の合計。"""
    if runs == 0 or not 0.0 < rate < 1.0:
        return 1.0
    probabilities = [math.comb(runs, k) * rate**k * (1.0 - rate) ** (runs - k) for k in range(runs + 1)]
    observed = probabilities[hits]
    return min(1.0, sum(p for p in probabilities if p <= observed * (1.0 + 1e-9)))


def two_proportion_p(hits_a: int, runs_a: int, hits_b: int, runs_b: int) -> float:
    """2標本の比率の z 検定（両側）。どちらかが 0 頭なら 1.0。"""
    if runs_a == 0 or runs_b == 0:
        return 1.0
    pooled = (hits_a + hits_b) / (runs_a + runs_b)
    variance = pooled * (1.0 - pooled) * (1.0 / runs_a + 1.0 / runs_b)
    if variance <= 0.0:
        return 1.0
    z = (hits_a / runs_a - hits_b / runs_b) / math.sqrt(variance)
    return math.erfc(abs(z) / math.sqrt(2.0))


def mark(p_value: float | None) -> str:
    """p 値の印。◎ = p<0.05、○ = p<0.10、空 = それ以外。"""
    if p_value is None:
        return "―"
    if p_value < 0.05:
        return "◎"
    if p_value < 0.10:
        return "○"
    return ""


def _rate(numerator: float, runs: int) -> float:
    return numerator / runs * 100 if runs else 0.0


def _pct(value: float) -> str:
    return f"{value:.1f}%"


def _signed_pt(value: float) -> str:
    return f"{value:+.1f}pt"
