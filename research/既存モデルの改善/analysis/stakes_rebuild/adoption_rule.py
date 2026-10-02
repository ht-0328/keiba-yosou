"""採用の基準を、区切りごとのログ損失に当てる。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: 採用の基準: 7つの区切りのうち、作り直しのログ損失が比べ先より小さい区切りの数の下限（研究「既存モデルの改善」と同じ）。
MIN_BETTER_WINDOWS = 5


@dataclass(frozen=True)
class Verdict:
    """1つの比べ先に対する判定。

    - ``better_windows``: 作り直しのログ損失が比べ先より小さかった区切りの数。``windows`` は区切りの数。
    - ``candidate_overall``・``reference_overall``: 7つの区切りのテスト期間を合わせたログ損失。
    """

    better_windows: int
    windows: int
    candidate_overall: float
    reference_overall: float

    @property
    def overall_better(self) -> bool:
        """全期間を合わせても、作り直しのほうが小さいか。"""
        return self.candidate_overall < self.reference_overall

    @property
    def passes(self) -> bool:
        """この比べ先に対して、採用の基準を満たすか。"""
        return self.better_windows >= MIN_BETTER_WINDOWS and self.overall_better


class AdoptionRule:
    """採用の基準（重賞の設計書 15 の 9。結果を見る前に決めたもの）を当てる。

    1つの比べ先に対して「ログ損失が小さい区切りが ``MIN_BETTER_WINDOWS`` 以上、かつ全期間でも小さい」なら合格。
    専用モデルを採用するのは、オッズだけと「手本を重賞だけに使ったとき」の**両方**に合格した時点だけ。
    """

    def verdict(self, candidate: pd.Series, reference: pd.Series,
                candidate_overall: float, reference_overall: float) -> Verdict:
        """``candidate``・``reference`` は区切りの名前 → テスト期間のログ損失。"""
        aligned = reference.reindex(candidate.index)
        better = int((candidate < aligned).sum())
        return Verdict(better, len(candidate), float(candidate_overall), float(reference_overall))

    def adopted(self, against_odds: Verdict, against_general: Verdict) -> bool:
        """両方の比べ先に合格したときだけ採用。"""
        return against_odds.passes and against_general.passes
