"""ComboForms（組の馬の人気の帯から組の形を付ける）と PopularityBand のテスト。"""

from __future__ import annotations

import pandas as pd

from 地方の推奨買目.combo_forms import FORM, ComboForms
from 地方の推奨買目.popularity_band import FAVORITE, LONGSHOT, MIDDLE, PopularityBand


def test_人気の帯は_1から3が人気馬_4から7が中穴_8以下が大穴():
    bands = PopularityBand().band_of(pd.Series([1, 3, 4, 7, 8, 12]))
    assert list(bands) == [FAVORITE, FAVORITE, MIDDLE, MIDDLE, LONGSHOT, LONGSHOT]


def test_組の形は_帯を人中大の順に並べた文字():
    horses = pd.DataFrame({"horse_no": [1, 2, 3, 4, 5, 6, 7, 8, 9], "popularity": [3, 1, 9, 5, 2, 8, 4, 7, 6]})
    forms = ComboForms(horses)
    pairs = pd.DataFrame({"race_id": [1] * 3, "a": [1, 3, 4], "b": [2, 4, 5]})
    assert list(forms.attach(pairs, ("a", "b"))[FORM]) == ["人人", "中大", "人中"]
    trios = pd.DataFrame({"race_id": [1], "a": [2], "b": [6], "c": [7]})
    assert list(forms.attach(trios, ("a", "b", "c"))[FORM]) == ["人中大"]
    assert list(forms.attach(pairs.iloc[0:0], ("a", "b"))[FORM]) == []
