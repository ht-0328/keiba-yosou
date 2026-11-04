"""人気の帯・配当の帯・地区の決めごとを、架空の値で確かめる。"""

from __future__ import annotations

import pandas as pd
import pytest

from 地方の万馬券.analysis.payout_band import BIG, HUGE, MEDIUM, SOLID, PayoutBand
from 地方の万馬券.analysis.popularity_band import FAVORITE, LONGSHOT, MIDDLE, PopularityBand
from 地方の万馬券.analysis.venue_area import UNKNOWN_AREA, VenueArea


def test_人気の帯は_1から3が人気馬_4から7が中穴_8以下が大穴():
    band = PopularityBand().band_of(pd.Series([1, 3, 4, 7, 8, 12, None]))
    assert list(band[:6]) == [FAVORITE, FAVORITE, MIDDLE, MIDDLE, LONGSHOT, LONGSHOT]
    assert pd.isna(band[6])


def test_中穴の範囲は変えられる():
    band = PopularityBand(4, 6).band_of(pd.Series([6, 7]))
    assert list(band) == [MIDDLE, LONGSHOT]
    assert "4〜6番人気" in PopularityBand(4, 6).label


def test_中穴の範囲が逆なら誤り():
    with pytest.raises(ValueError):
        PopularityBand(7, 4)


def test_配当の帯は_1万_10万_100万で切る():
    band = PayoutBand().band_of(pd.Series([9_990, 10_000, 99_990, 100_000, 999_990, 1_000_000]))
    assert list(band) == [SOLID, MEDIUM, MEDIUM, BIG, BIG, HUGE]


def test_配当の線の順が崩れていれば誤り():
    with pytest.raises(ValueError):
        PayoutBand(100_000, 10_000, 1_000_000)


def test_地区は競馬場名と所属の名前の両方から引ける():
    areas = VenueArea()
    assert areas.area_of("大井") == "南関東"
    assert areas.area_of("小林") == "南関東"
    assert areas.area_of("西脇") == "兵庫"
    assert areas.area_of("北海道") == areas.area_of("門別") == "北海道"
    assert areas.area_of("上山") == UNKNOWN_AREA
    assert areas.area_of(None) == UNKNOWN_AREA
