"""研究「AIとロジックの予想」: 消のロジック（1着の予想が市場の見立て以上の消は取り消す）で、残る消と取り消す消の成績を期間ごとに出す。

    uv run python research/AIとロジックの予想/analysis/danger_cancel.py            # 期間ごとの成績
    uv run python research/AIとロジックの予想/analysis/danger_cancel.py --flags    # 道具「印の成績」に渡す消の表も書く

読むのは研究「裏目を買うかの予想」の印の表（``reports/裏目を買うかの予想/marked.pkl``。1行 = 1頭）。消があるのは 2022年9月3日から。
``--flags`` は ``reports/AIとロジックの予想/消/flags_now.pkl``（今の消）と ``flags_cancel.pkl``（取り消したあとの消）を書く。
道具「印の成績」の ``--danger-flags`` に渡すと、その消で印を付け直した全券種の買い目の成績が出る（``danger_tickets.py`` で比べる）。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[3]
MARKED = _ROOT / "reports" / "裏目を買うかの予想" / "marked.pkl"
OUT = _ROOT / "reports" / "AIとロジックの予想" / "消"
#: 期間（名前・初日・最終日の次の日）。参考1・参考2・作る で探し、確かめる は一度だけ数える。
PERIODS: tuple[tuple[str, str, str], ...] = (("参考1", "2022-09-03", "2024-09-07"), ("参考2", "2024-09-07", "2025-09-06"),
                                              ("作る", "2025-09-06", "2026-03-08"), ("確かめる", "2026-03-08", "2026-09-23"))
_FLAG_COLUMNS = ["race_id", "horse_id", "favorite_band", "is_danger"]
_RATES = ("勝率", "3着以内率", "単勝の回収率")


def cancelled(table: pd.DataFrame) -> pd.Series:
    """取り消す消（本番の ``DangerCancelLogic`` と同じ決まり。1着の予想が市場の見立て以上）。"""
    return table["is_danger"].astype(bool) & (table["win_probability"] >= table["market_win"])


def stats(horses: pd.DataFrame) -> dict[str, float]:
    """頭数・勝率・3着以内率・単勝の回収率。"""
    if horses.empty:
        return {"頭数": 0, **dict.fromkeys(_RATES, float("nan"))}
    return {"頭数": len(horses), "勝率": (horses["finish"] == 1).mean(), "3着以内率": (horses["finish"] <= 3).mean(),
            "単勝の回収率": horses["win_payout"].fillna(0).mean() / 100}


def summary(dangers: pd.DataFrame) -> pd.DataFrame:
    """期間 × （今の消・残る消・取り消す消）の成績。``dangers`` は消の馬だけ（列 ``race_date``・``finish``・``win_payout`` と決まりの列）。"""
    days = pd.to_datetime(dangers["race_date"])
    off = cancelled(dangers)
    rows = []
    for name, start, end in PERIODS:
        inside = (days >= start) & (days < end)
        rows += [{"期間": name, "消": kind, **stats(dangers[chosen])}
                 for kind, chosen in (("今の消", inside), ("残る消", inside & ~off), ("取り消す消", inside & off))]
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--flags", action="store_true", help="道具「印の成績」に渡す消の表も書く")
    args = parser.parse_args()
    marked = pd.read_pickle(MARKED)
    dangers = marked[marked["is_danger"].astype(bool)]
    print(summary(dangers).to_string(index=False, formatters=dict.fromkeys(_RATES, "{:.1%}".format)))
    if args.flags:
        OUT.mkdir(parents=True, exist_ok=True)
        dangers.assign(is_danger=True)[_FLAG_COLUMNS].to_pickle(OUT / "flags_now.pkl")
        dangers.assign(is_danger=~cancelled(dangers))[_FLAG_COLUMNS].to_pickle(OUT / "flags_cancel.pkl")
        print(f"消の表を {OUT} に書いた")


if __name__ == "__main__":
    main()
