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


def test_danger_threshold_measures_losses_beyond_the_market():
    rng = np.random.default_rng(1)
    n = 4000
    # 2〜3番人気のように、人気帯の中でオッズから見た4着以下の確率に幅がある。危険度の高い馬ほど市場からは強いと見られているが、
    # 実際の4着以下率はどの馬も 0.53 で同じ（危険度 0.05 以上の馬は、市場の見立てより大きく負ける）
    danger = pd.Series(rng.uniform(0.0, 0.1, n))
    market = pd.Series(np.where(danger >= 0.05, 0.43, 0.56))
    lost = pd.Series((rng.uniform(size=n) < 0.53).astype(int))
    assert DangerThreshold().choose(danger, lost, market) == 0.05
    # 前の物差し（4着以下率そのもの）では差が出ず、線が決まる根拠が無い
    assert DangerThreshold().choose(danger, lost) != 0.05


def test_danger_threshold_uses_the_loss_rate_for_the_favorite_and_the_market_for_the_others():
    rng = np.random.default_rng(1)  # 上の市場の見立てとの差のテストと同じ値
    n = 4000
    danger = pd.Series(rng.uniform(0.0, 0.1, n))
    market = pd.Series(np.where(danger >= 0.05, 0.43, 0.56))
    lost = pd.Series((rng.uniform(size=n) < 0.53).astype(int))
    chooser = DangerThreshold()
    assert chooser.choose_for("2〜3番人気", danger, lost, market) == chooser.choose(danger, lost, market) == 0.05
    # 1番人気は4着以下率そのもので比べる。この値では4着以下率に差が無いので、線を決めない
    assert np.isnan(chooser.choose_for("1番人気", danger, lost, market))


def test_danger_threshold_for_a_band_needs_a_score_beyond_chance():
    rng = np.random.default_rng(3)
    n = 3000
    # 危険度と実際の負け方に関係が無い人気帯は、点の高い線があっても偶然の範囲なので、線を決めない
    danger = pd.Series(rng.uniform(0.0, 0.1, n))
    market = pd.Series(np.full(n, 0.5))
    lost = pd.Series((rng.uniform(size=n) < 0.5).astype(int))
    chooser = DangerThreshold()
    assert not np.isnan(chooser.choose(danger, lost, market))  # 確かめをしない選び方では、どれかの線が選ばれる
    assert np.isnan(chooser.choose_for("2〜3番人気", danger, lost, market))


def test_danger_threshold_needs_enough_flagged_horses():
    assert np.isnan(DangerThreshold().choose(pd.Series([-0.5] * 50), pd.Series([1] * 50)))


def test_danger_judge_uses_the_line_of_each_band():
    judged = DangerJudge({"1番人気": 0.05, "2〜3番人気": 0.1}).judge(
        pd.Series([0.40, 0.55, 0.70]), pd.Series([0.33, 0.50, 0.55]), pd.Series(["1番人気", "2〜3番人気", "4〜5番人気"]),
    )
    np.testing.assert_allclose(judged[DANGER], [0.07, 0.05, 0.15])
    # 4〜5番人気は線が無いので、危険度が高くても危険にしない
    assert judged[IS_DANGER].tolist() == ["危険", "", ""]
