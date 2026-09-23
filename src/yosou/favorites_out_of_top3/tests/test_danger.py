"""人気馬の「普段より危ない」の判定（既存モデルの修正計画の 1「人気馬の4着以下」）。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..danger import DANGER, IS_DANGER, DangerJudge, DangerThreshold


def test_danger_threshold_prefers_a_line_that_separates_the_losers():
    rng = np.random.default_rng(0)
    danger = pd.Series(rng.uniform(-0.1, 0.2, 2000))
    # 危険度が 0.08 以上の馬だけ、実際に負けやすい
    lost = pd.Series((rng.uniform(size=2000) < np.where(danger >= 0.08, 0.75, 0.40)).astype(int))
    assert DangerThreshold().choose(danger, lost) == 0.08


def test_danger_threshold_needs_enough_flagged_horses():
    assert np.isnan(DangerThreshold().choose(pd.Series([-0.5] * 50), pd.Series([1] * 50)))


def test_danger_judge_uses_the_line_of_each_band():
    judged = DangerJudge({"1番人気": 0.05, "2〜3番人気": 0.1}).judge(
        pd.Series([0.40, 0.55, 0.70]), pd.Series([0.33, 0.50, 0.55]), pd.Series(["1番人気", "2〜3番人気", "4〜5番人気"]),
    )
    np.testing.assert_allclose(judged[DANGER], [0.07, 0.05, 0.15])
    # 4〜5番人気は線が無いので、危険度が高くても危険にしない
    assert judged[IS_DANGER].tolist() == ["危険", "", ""]
