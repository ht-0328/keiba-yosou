"""順位で学ぶ予想の、点数から確率への直し方（架空の値だけ）。"""

from __future__ import annotations

from itertools import permutations

import numpy as np

from 既存モデルの改善.analysis.graded_rank import PlackettLuce


def _brute_top3(strength: np.ndarray) -> np.ndarray:
    """全部の 1〜3着の並びを数えた、3着以内の確率。"""
    result = np.zeros(len(strength))
    for first, second, third in permutations(range(len(strength)), 3):
        rest1, rest2 = 1 - strength[first], 1 - strength[first] - strength[second]
        probability = strength[first] * strength[second] / rest1 * strength[third] / rest2
        result[[first, second, third]] += probability
    return result


def test_win_sums_to_one_and_top3_matches_the_full_count():
    score = np.array([1.0, 0.2, -0.5, 0.0, 0.7, -1.0, 0.3])
    groups = np.array([0, 0, 0, 0, 1, 1, 1])
    converter = PlackettLuce()
    win = converter.win(score, groups, 1.0)
    assert np.isclose(win[:4].sum(), 1.0) and np.isclose(win[4:].sum(), 1.0)
    top3 = converter.top3(score, groups, 1.0)
    np.testing.assert_allclose(top3[:4], _brute_top3(win[:4]), rtol=1e-9)
    # 3頭立ては全頭が3着以内
    np.testing.assert_allclose(top3[4:], 1.0)
    assert np.isclose(top3[:4].sum(), 3.0)


def test_temperature_is_fitted_to_the_results():
    rng = np.random.default_rng(1)
    groups = np.repeat(np.arange(400), 8)
    score = rng.normal(size=len(groups))
    # 本当の温度 2 で着順を作る
    converter = PlackettLuce()
    truth = converter.win(score, groups, 2.0)
    win = np.zeros(len(groups))
    for race in range(400):
        rows = np.flatnonzero(groups == race)
        win[rng.choice(rows, p=truth[rows] / truth[rows].sum())] = 1.0
    converter.fit(score, groups, win, win)
    assert 1.4 < converter.win_temperature < 2.8
