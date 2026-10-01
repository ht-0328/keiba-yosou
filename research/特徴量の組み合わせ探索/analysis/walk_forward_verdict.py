"""年ごとのウォークフォワードの結果を、採用の基準に当てる（基準は結果を見る前に決めた）。"""

import pandas as pd

from .yearly_payback import ALL_YEARS

#: 年を合わせた点数の下限。元の探索の採用の基準と同じ。
MIN_TOTAL_BETS = 300
#: 年を合わせた回収率と、開催日単位の90%の幅の下限の、どちらも超えてほしい値。
MIN_RATE = 1.0


class WalkForwardVerdict:
    """採用するのは、次の4つを全部満たすとき。

    1. 年を合わせて、点数が ``MIN_TOTAL_BETS`` 以上。
    2. 年を合わせて、複勝の回収率が 100% 以上。
    3. 年を合わせて、開催日単位の90%の幅の下限が 100% 以上（元の探索の採用の基準と同じ物差し）。
    4. 回収率が 100% 以上の年が、買った年の半分を超える（1〜2年の大当たりだけで合計が 100% を超えていない）。
    """

    def judge(self, table: pd.DataFrame) -> dict:
        total = table[table["年"] == ALL_YEARS].iloc[0]
        years = table[(table["年"] != ALL_YEARS) & (table["点数"] > 0)]
        good_years = int((years["回収率"] >= MIN_RATE).sum())
        checks = {
            "点数": bool(total["点数"] >= MIN_TOTAL_BETS),
            "回収率": bool(total["点数"] > 0 and total["回収率"] >= MIN_RATE),
            "下限": bool(pd.notna(total["回収率の下限"]) and total["回収率の下限"] >= MIN_RATE),
            "年ごと": bool(len(years) > 0 and good_years * 2 > len(years)),
        }
        return {"採用": all(checks.values()), "基準ごと": checks,
                "100%以上の年": good_years, "買った年": int(len(years))}
