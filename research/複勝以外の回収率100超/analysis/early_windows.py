"""まだ見ていない年で確かめる区切り（手順4 の 2021〜2022年、手順5 の 2019〜2020年、手順6 の 2015〜2018年）。"""

from __future__ import annotations

from datetime import date

from 既存モデルの改善.analysis.windows import TestWindow

#: 研究「既存モデルの改善」の7つの区切り（2023年前半〜2026年）より前の、半年ずつの4つの区切り。
#: 印の買い目の成績は、これまで 2023年〜2026年のテスト期間でしか数えておらず、その数字はもう何度も見ている。
#: この4つは、印のルールも買い目の決まりも決めたあとで初めて数える期間で、決まりを確かめるのに使う。
#: 当日の表は 2017年1月から始まるので、いちばん早い 2021年前半の区切りでも学習は 3年半（2017年1月〜2020年6月）ある。
EARLY_WINDOWS: tuple[TestWindow, ...] = (
    TestWindow("2021年前半", date(2020, 7, 1), date(2021, 1, 1), date(2021, 6, 30)),
    TestWindow("2021年後半", date(2021, 1, 1), date(2021, 7, 1), date(2021, 12, 31)),
    TestWindow("2022年前半", date(2021, 7, 1), date(2022, 1, 1), date(2022, 6, 30)),
    TestWindow("2022年後半", date(2022, 1, 1), date(2022, 7, 1), date(2022, 12, 31)),
)
#: 手順5（docs/04）で、組の期待値で選ぶ買い方を確かめる、さらに前の4つの区切り。2021〜2022年は手順4 で数えて見てしまったので、
#: 一度も数えていないのはこの2年だけである。当日の表は 2017年1月から始まるので、学習は 1年半（2019年前半）〜3年（2020年後半）と短く、
#: モデルは 2021年以降の区切りより弱い。その分は割り引かずに判定する。
EARLIEST_WINDOWS: tuple[TestWindow, ...] = (
    TestWindow("2019年前半", date(2018, 7, 1), date(2019, 1, 1), date(2019, 6, 30)),
    TestWindow("2019年後半", date(2019, 1, 1), date(2019, 7, 1), date(2019, 12, 31)),
    TestWindow("2020年前半", date(2019, 7, 1), date(2020, 1, 1), date(2020, 6, 30)),
    TestWindow("2020年後半", date(2020, 1, 1), date(2020, 7, 1), date(2020, 12, 31)),
)
#: 手順6（docs/05）で確かめる、さらに前の8つの区切り。2019〜2026年はどれも結果を見てしまったので、一度も数えていないのはこの4年だけである。
#: 2017年1月からの表では学習が足りないので、2012年1月からの表（``TABLES_2012``）で学ぶ。学習は 2年半（2015年前半）〜6年（2018年後半）。
OLDEST_WINDOWS: tuple[TestWindow, ...] = tuple(
    window
    for year in range(2015, 2019)
    for window in (
        TestWindow(f"{year}年前半", date(year - 1, 7, 1), date(year, 1, 1), date(year, 6, 30)),
        TestWindow(f"{year}年後半", date(year, 1, 1), date(year, 7, 1), date(year, 12, 31)),
    )
)
#: 区切りの組の名前（最初の年）→（区切り、予測の置き場所のフォルダ名）。
WINDOW_SETS: dict[str, tuple[tuple[TestWindow, ...], str]] = {
    "2021": (EARLY_WINDOWS, "predictions"),
    "2019": (EARLIEST_WINDOWS, "predictions-2019"),
    "2015": (OLDEST_WINDOWS, "predictions-2015"),
}
