"""年ごとのウォークフォワードの部品を、架空の値で確かめる（元DB に触らない）。"""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from yosou.custom_binary.feature.default_registry import DefaultRegistry
from yosou.custom_binary.setting import ModelSettings

from 特徴量の組み合わせ探索.analysis.model_configs import pool_configs
from 特徴量の組み合わせ探索.analysis.model_trial import VALUE_LINES
from 特徴量の組み合わせ探索.analysis.search_periods import SearchPeriods
from 特徴量の組み合わせ探索.analysis.walk_forward_trial import LINE_OF_NAME, LOWEST_LINE
from 特徴量の組み合わせ探索.analysis.walk_forward_verdict import WalkForwardVerdict
from 特徴量の組み合わせ探索.analysis.walk_forward_years import WalkForwardYears
from 特徴量の組み合わせ探索.analysis.yearly_payback import ALL_YEARS, YearlyPayback

TODAY_SETTINGS = Path(__file__).resolve().parents[3] / "tools" / "当日の予想" / "settings" / "馬体重あり.yml"


def test_each_year_trains_before_confirms_the_year_before_and_tests_the_year():
    splits = list(WalkForwardYears(last_year=2021))
    assert [split.year for split in splits] == [2019, 2020, 2021]
    last = splits[-1]
    assert last.periods.discover_from == date(2017, 1, 1)
    assert (last.periods.confirm_from, last.periods.test_from, last.test_until) == (
        date(2020, 1, 1), date(2021, 1, 1), date(2022, 1, 1))


def test_every_value_line_has_a_number():
    assert all(name in LINE_OF_NAME for name in VALUE_LINES)
    assert LOWEST_LINE == 1.0


def tickets(days: list[str], values: list[float], payouts: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"day": pd.to_datetime(days), "ev": values, "payout": payouts})


def test_yearly_payback_applies_each_years_line_and_adds_them_up():
    frames = {
        2019: tickets(["2019-01-05", "2019-01-05", "2019-01-06"], [1.3, 1.1, 1.25], [200.0, 500.0, 0.0]),
        2020: tickets(["2020-01-05"], [1.4], [300.0]),
        2021: tickets(["2021-01-05"], [1.4], [300.0]),
    }
    table = YearlyPayback().table(frames, {2019: 1.2, 2020: 1.3, 2021: None}).set_index("年")
    # 2019年は線 1.2 で2点（期待値 1.1 の馬は買わない）、2020年は1点、2021年は線が無いので買わない。
    assert table.loc[2019, ["点数", "開催日数"]].tolist() == [2, 2]
    assert table.loc[2019, "回収率"] == pytest.approx(1.0)
    assert table.loc[2021, "点数"] == 0
    assert table.loc[ALL_YEARS, "点数"] == 3
    assert table.loc[ALL_YEARS, "回収率"] == pytest.approx(500.0 / 300.0)
    assert table.loc[ALL_YEARS, "回収率の下限"] <= table.loc[ALL_YEARS, "回収率"]


def verdict_table(years: list[tuple[int, float]], total: tuple[int, float, float]) -> pd.DataFrame:
    rows = [{"年": 2019 + index, "点数": bets, "回収率": rate, "回収率の下限": None} for index, (bets, rate) in enumerate(years)]
    rows.append({"年": ALL_YEARS, "点数": total[0], "回収率": total[1], "回収率の下限": total[2]})
    return pd.DataFrame(rows)


def test_verdict_needs_all_four_checks():
    good = WalkForwardVerdict().judge(verdict_table([(200, 1.1), (200, 1.05), (200, 0.95)], (600, 1.03, 1.01)))
    assert good["採用"] and good["100%以上の年"] == 2 and good["買った年"] == 3
    low = WalkForwardVerdict().judge(verdict_table([(200, 1.1), (200, 1.05), (200, 0.95)], (600, 1.03, 0.97)))
    assert not low["採用"] and low["基準ごと"]["下限"] is False
    # 1年の大当たりで合計が 100% を超えても、100% 以上の年が半分に届かなければ採用しない。
    lucky = WalkForwardVerdict().judge(verdict_table([(200, 1.5), (200, 0.9), (200, 0.9), (0, None)], (600, 1.1, 1.02)))
    assert not lucky["採用"] and lucky["基準ごと"]["年ごと"] is False and lucky["買った年"] == 3


def test_pool_main_all_is_the_same_setting_as_todays_model_with_weight():
    registry = DefaultRegistry().build()
    today = ModelSettings.load(TODAY_SETTINGS, registry)
    main = next(config for config in pool_configs() if config.name == "pool_main_all").settings(registry, SearchPeriods())
    assert today.selected == main.selected
    assert (today.target, today.timing, today.odds_baseline) == (main.target, main.timing, main.odds_baseline)
    assert (today.popularity, today.conditions) == (main.popularity, main.conditions)
    assert today.period == main.period
