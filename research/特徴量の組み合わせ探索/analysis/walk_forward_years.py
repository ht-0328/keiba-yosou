"""年ごとのウォークフォワードの期間の区切り。"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date

from .search_periods import SearchPeriods

#: 最初に予測する年。学習に 2017年、早期終了と線の選択に 2018年を使うので、2019年から。
FIRST_TEST_YEAR = 2019


@dataclass(frozen=True)
class YearPeriods:
    """1年ぶんの区切り。``periods`` の見つける期間で学習し、確かめる期間（直前の1年）で早期終了と線の選択をし、
    ``year`` の1年（``periods.test_from`` から ``test_until`` の前日まで）を予測する。
    """

    year: int
    periods: SearchPeriods

    @property
    def test_until(self) -> date:
        return date(self.year + 1, 1, 1)


class WalkForwardYears:
    """「その年より前で学習し直して、その年を予測する」を、``first_year`` から ``last_year`` まで1年ずつくり返す。

    1回だけ期間を分けると、その1〜2年の当たり外れの偶然がそのまま結論になる。年ごとにくり返すと、
    同じ作り方が年をまたいで通じるかと、年を合わせた点数での回収率が分かる。
    """

    def __init__(self, last_year: int, first_year: int = FIRST_TEST_YEAR) -> None:
        self._first_year = first_year
        self._last_year = last_year

    def __iter__(self) -> Iterator[YearPeriods]:
        base = SearchPeriods()
        for year in range(self._first_year, self._last_year + 1):
            periods = SearchPeriods(base.warmup_from, base.discover_from, date(year - 1, 1, 1), date(year, 1, 1))
            yield YearPeriods(year, periods)
