"""1つの時点の、作り直した専用モデルの比べ方の表。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from 共通.render import Table

from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData
from yosou.shared.dataset.column_names import PLACE_PAYOUT, POPULARITY, WIN_PAYOUT

from ..comparison.prediction_join import LABEL, PredictionJoin
from ..comparison.table_formatter import TableFormatter
from ..scores import BinaryScores
from ..variants import ModelVariant
from ..walk_forward import PART_TEST, PREDICTION_COLUMN, WINDOW
from ..windows import TestWindow
from .adoption_rule import MIN_BETTER_WINDOWS, AdoptionRule, Verdict
from .rebuild_variants import RebuildComparisonSpec

#: 行を突き合わせる鍵（区切りも含める。同じ出走が隣り合う区切りの検証とテストの両方に出るため）。
_KEY = [RACE_ID, HORSE_ID, WINDOW]
#: ログ損失の差の列の倍率（差がごく小さいので 1000倍して出す）。
_DIFFERENCE_SCALE = 1000


class StakesRebuildComparison:
    """作り直した専用モデルを、オッズだけ・手本を重賞だけに使ったとき・K を外したものと、1つの時点で比べる表を作る
    （重賞の設計書 15 の 9・16 の 3）。

    ``predictions`` は作り方の鍵 → 予測の表（手本は ``StakesRowFilter`` で重賞の行にしたもの）。
    比べるのは、テスト期間の行のうち、4つの作り方すべてにある行だけ。
    """

    def __init__(self, spec: RebuildComparisonSpec, data: TrainingData, predictions: Mapping[str, pd.DataFrame],
                 windows: tuple[TestWindow, ...]) -> None:
        join = PredictionJoin(data)
        joined = {variant.key: join.of(predictions[variant.key], PART_TEST) for variant in spec.variants}
        self._tests = self._common_rows(joined)
        self._spec = spec
        self._windows = windows
        self._format = TableFormatter()
        self._rule = AdoptionRule()
        self._subject = f"重賞の作り直し（{spec.timing.label}）"

    def tables(self) -> list[Table]:
        losses = self._losses_by_window()
        return [self._by_window(losses), self._verdict(losses), self._pooled(), self._top_pick()]

    def verdicts(self, losses: pd.DataFrame | None = None) -> tuple[Verdict, Verdict]:
        """（オッズだけに対する判定, 手本に対する判定）。"""
        table = self._losses_by_window() if losses is None else losses
        spec = self._spec
        return (self._verdict_against(table, spec.odds_reference), self._verdict_against(table, spec.general))

    def _common_rows(self, joined: Mapping[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        """4つの作り方すべてにある行（レースID・馬ID・区切り）だけにし、並びをそろえる。"""
        frames = {key: frame.assign(**{column: frame[column].astype(str) for column in _KEY[:2]}) for key, frame in joined.items()}
        keys = None
        for frame in frames.values():
            part = frame[_KEY].drop_duplicates()
            keys = part if keys is None else keys.merge(part, on=_KEY)
        return {key: keys.merge(frame.drop_duplicates(_KEY), on=_KEY, how="left") for key, frame in frames.items()}

    def _loss(self, frame: pd.DataFrame) -> float:
        if frame.empty:
            return float("nan")
        return BinaryScores().of(frame[LABEL], frame[PREDICTION_COLUMN], frame[POPULARITY])["ログ損失"]

    def _losses_by_window(self) -> pd.DataFrame:
        """区切り × 作り方 のテスト期間のログ損失（index は区切りの名前、列は作り方の鍵）。"""
        rows = {window.name: {key: self._loss(test[test[WINDOW] == window.name]) for key, test in self._tests.items()}
                for window in self._windows}
        return pd.DataFrame.from_dict(rows, orient="index")

    def _verdict_against(self, losses: pd.DataFrame, reference: ModelVariant) -> Verdict:
        candidate = self._spec.candidate.key
        return self._rule.verdict(losses[candidate], losses[reference.key],
                                  self._loss(self._tests[candidate]), self._loss(self._tests[reference.key]))

    def _by_window(self, losses: pd.DataFrame) -> Table:
        spec = self._spec
        frame = losses.rename(columns={variant.key: f"{variant.name}: ログ損失" for variant in spec.variants})
        frame = frame.rename_axis("区切り").reset_index()
        candidate = losses[spec.candidate.key]
        frame["作り直しがオッズだけより小さい"] = np.where(candidate < losses[spec.odds_reference.key], "はい", "いいえ")
        frame["作り直しが手本より小さい"] = np.where(candidate < losses[spec.general.key], "はい", "いいえ")
        against_odds, against_general = self.verdicts(losses)
        return self._format.table(
            frame, f"{self._subject}: 区切りごとの確率の誤差（テスト期間）",
            note=f"ログ損失は小さいほど良い。作り直しが小さい区切り: オッズだけに対して {against_odds.better_windows} / {len(frame)}、"
                 f"手本に対して {against_general.better_windows} / {len(frame)}（採用の基準はどちらも {MIN_BETTER_WINDOWS} / 7 以上で、"
                 "全期間でも小さいこと）。手本は全レースで学び、重賞の行だけで測った。",
        )

    def _verdict(self, losses: pd.DataFrame) -> Table:
        against_odds, against_general = self.verdicts(losses)
        spec = self._spec
        rows = [self._verdict_row(spec.odds_reference, against_odds), self._verdict_row(spec.general, against_general)]
        adopted = self._rule.adopted(against_odds, against_general)
        rows.append({"比べ先": "両方（採用の判断）", "作り直しが小さい区切り": None, "作り直しのログ損失（全期間）": None,
                     "比べ先のログ損失（全期間）": None, "差（×1000）": None, "基準を満たす": "採用" if adopted else "採用しない（引退）"})
        return self._format.table(
            pd.DataFrame(rows), f"{self._subject}: 採用の基準に照らした判定",
            note="差は、作り直しのログ損失 − 比べ先のログ損失 を 1000倍した値で、負なら作り直しのほうが良い。"
                 "両方の比べ先に合格した時点だけ、専用モデルを採用する（設計書 15 の 9）。",
        )

    def _verdict_row(self, reference: ModelVariant, verdict: Verdict) -> dict[str, object]:
        return {
            "比べ先": reference.name, "作り直しが小さい区切り": f"{verdict.better_windows} / {verdict.windows}",
            "作り直しのログ損失（全期間）": verdict.candidate_overall, "比べ先のログ損失（全期間）": verdict.reference_overall,
            "差（×1000）": (verdict.candidate_overall - verdict.reference_overall) * _DIFFERENCE_SCALE,
            "基準を満たす": "はい" if verdict.passes else "いいえ",
        }

    def _pooled(self) -> Table:
        scores = BinaryScores()
        rows = [{"作り方": variant.name, **scores.of(test[LABEL], test[PREDICTION_COLUMN], test[POPULARITY])}
                for variant in self._spec.variants for test in (self._tests[variant.key],)]
        return self._format.table(pd.DataFrame(rows), f"{self._subject}: {len(self._windows)}つの区切りのテスト期間を合わせた当たり具合")

    def _top_pick(self) -> Table:
        """各レースで確率がいちばん高い馬（◎）の成績と、◎の3着以内率が1番人気を上回った区切りの数。"""
        rows = [self._top_row(variant.name, self._tests[variant.key], PREDICTION_COLUMN) for variant in self._spec.variants]
        favorite = self._tests[self._spec.candidate.key].assign(人気の逆=lambda frame: -frame[POPULARITY].fillna(99))
        rows.append(self._top_row("1番人気（比べる目安）", favorite, "人気の逆"))
        return self._format.table(pd.DataFrame(rows), f"{self._subject}: 各レースで確率がいちばん高い馬（◎。テスト期間）",
                                  note="回収率は 100円ずつ買ったときの払戻の合計 ÷ 賭け金。"
                                       "「1番人気を上回った区切り」は、その区切りの◎の3着以内率が1番人気の3着以内率より高かった区切りの数。")

    def _top_row(self, name: str, test: pd.DataFrame, column: str) -> dict[str, object]:
        picked = test.loc[test.groupby(RACE_ID)[column].idxmax()]
        favorite = test.loc[test.groupby(RACE_ID)[POPULARITY].idxmin()]
        better = sum(self._place_rate(picked, window.name) > self._place_rate(favorite, window.name) for window in self._windows)
        return {
            "選び方": name, "レース数": len(picked), "3着以内率": float(picked[LABEL].mean()),
            "単勝回収率": float(picked[WIN_PAYOUT].fillna(0).sum() / (100 * len(picked))),
            "複勝回収率": float(picked[PLACE_PAYOUT].fillna(0).sum() / (100 * len(picked))),
            "1番人気を上回った区切り": f"{better} / {len(self._windows)}",
        }

    def _place_rate(self, picked: pd.DataFrame, window: str) -> float:
        chosen = picked[picked[WINDOW] == window]
        return float(chosen[LABEL].mean()) if len(chosen) else float("nan")
