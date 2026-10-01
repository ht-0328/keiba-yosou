"""年ごとと、年を合わせた複勝の回収率（点数・回収率・開催日単位の90%の幅の下限）。"""

import pandas as pd

from yosou.custom_binary.evaluation import BootstrapLowerBound
from yosou.custom_binary.evaluation.payback_rules import STAKE

#: 年を合わせた行の「年」の欄。
ALL_YEARS = "全年"


class YearlyPayback:
    """年ごとの買い目の候補（``tickets``: day・ev・payout）に、その年の線を当てて集計する。

    ``lines`` は年ごとの線。線が無い年（直前の1年で選べる線が無かった年）は買わない（点数 0）。
    年を合わせた行は、年ごとに買った買い目をそのまま足したもので、下限も合わせた買い目で出し直す。
    """

    def table(self, tickets: dict[int, pd.DataFrame], lines: dict[int, float | None]) -> pd.DataFrame:
        bought = {year: self._bought(frame, lines.get(year)) for year, frame in sorted(tickets.items())}
        rows = [self._row(year, lines.get(year), frame) for year, frame in bought.items()]
        everything = pd.concat(list(bought.values()), ignore_index=True) if bought else self._bought(pd.DataFrame(), None)
        rows.append(self._row(ALL_YEARS, None, everything))
        return pd.DataFrame(rows)

    def _bought(self, frame: pd.DataFrame, line: float | None) -> pd.DataFrame:
        if line is None or frame.empty:
            return pd.DataFrame({"day": pd.Series(dtype="datetime64[ns]"), "payout": pd.Series(dtype=float)})
        return frame.loc[frame["ev"] >= line, ["day", "payout"]]

    def _row(self, year, line: float | None, bought: pd.DataFrame) -> dict:
        bets = len(bought)
        rate = float(bought["payout"].sum() / (STAKE * bets)) if bets else None
        lower = BootstrapLowerBound().of(bought["day"].to_numpy(), bought["payout"].to_numpy()) if bets else None
        return {"年": year, "線": line, "点数": bets, "開催日数": int(bought["day"].nunique()),
                "回収率": rate, "回収率の下限": lower}
