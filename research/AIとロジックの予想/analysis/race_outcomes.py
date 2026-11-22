"""研究「AIとロジックの予想」: 今の本番（AI だけの予想）の全レースの印の買い目を、本番と同じ配り方で1レースずつ再現し、負け方を付ける。

    uv run python research/AIとロジックの予想/analysis/race_outcomes.py --learn-until 2024-09-07 --start 2024-09-07 --end 2025-09-06

買い目は研究「裏目を買うかの予想」の ``compare.py`` と同じ（表 = 単勝 ◎・馬連 ◎−○▲☆・馬単 ◎→○▲☆・3連単 ◎→○▲☆→○▲△☆、
裏の当たる確率が 0.30 以上のレースだけ馬単の裏 ○▲☆→◎）。どの組が当たっても同じ額が戻るように配り、見込みの回収率 100% 以上のレースだけ買う。
1レースごとに、買ったか・投資・払戻と、印の付いた馬の着順（負け方を分けるため）を書く。
出るもの（Git 対象外）: ``reports/AIとロジックの予想/outcomes_<start>_<end>.pkl``。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[2]
_REVERSE = _ROOT / "research" / "裏目を買うかの予想"
sys.path[:0] = [str(_ROOT / "tools"), str(_REVERSE), str(_REVERSE / "analysis")]

import compare  # noqa: E402
import fit  # noqa: E402
import 今週の予想.mark_return as mark_return  # noqa: E402
from 今週の予想.equal_payout_stakes import EqualPayoutStakes  # noqa: E402
from 今週の予想.mark_return import BUY_LINE  # noqa: E402

OUT = _ROOT / "reports" / "AIとロジックの予想"
#: 本番の裏の線（設計書「買うレースと買い目を決める」09 の 26）。
REVERSE_LINE = 0.30


def pool(learn_until: str, start: str, end: str) -> pd.DataFrame:
    """表と裏の候補の組（列 race_id・day・kind・value・odds・pay・p）。"""
    table = compare._pool(compare._front(compare.TICKETS, start, end), pd.read_pickle(compare.OUT / f"candidates_{start}_{end}.pkl"))
    return table.assign(p=table["race_id"].map(compare._probabilities(learn_until, start, end)))


def settle(race: pd.DataFrame, add_back: bool) -> dict:
    """1レースを本番と同じ配り方で買う。戻り値は 買ったか・投資・払戻・点数。"""
    tickets = race[(race["kind"] == "表") | ((race["kind"] == compare.EXACTA_BACK) & add_back)].to_dict("records")
    chosen, _ = EqualPayoutStakes().allocate(tickets)
    expected = sum(share * ticket["value"] for ticket, share in chosen if ticket["value"] == ticket["value"]) if chosen else 0.0
    if not chosen or expected < BUY_LINE:
        return {"bought": False, "stake": 0, "back": 0.0, "points": 0, "expected": expected}
    yen = mark_return._amounts(chosen)
    back = sum(amount * ticket["pay"] / 100 for amount, (ticket, _) in zip(yen, chosen, strict=True))
    return {"bought": True, "stake": sum(yen), "back": back, "points": len(chosen), "expected": expected}


def finishes(marked: pd.DataFrame) -> pd.DataFrame:
    """レースごとの、印の付いた馬の着順と、1〜3着の馬の印（1行 = 1レース）。"""
    rows = []
    for race_id, race in marked.groupby("race_id", sort=False):
        row = {"race_id": str(race_id), "field_size": int(race["field_size"].iloc[0])}
        for mark, name in (("◎", "top"), ("○", "second"), ("▲", "third"), ("消", "out"), ("☆", "star"), ("注", "note")):
            chosen = race[race["mark"] == mark]
            row[f"{name}_finish"] = float(chosen["finish"].iloc[0]) if len(chosen) else float("nan")
            row[f"{name}_pop"] = float(chosen["popularity"].iloc[0]) if len(chosen) else float("nan")
        ordered = race.dropna(subset=["finish"]).sort_values("finish")
        for place in (1, 2, 3):
            hit = ordered[ordered["finish"] == place]
            row[f"mark_{place}"] = str(hit["mark"].iloc[0]) if len(hit) else ""
            row[f"pop_{place}"] = float(hit["popularity"].iloc[0]) if len(hit) else float("nan")
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--learn-until", required=True, help="この開催日の前までで、裏の当たる確率のモデルを学ぶ")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args()
    table = pool(args.learn_until, args.start, args.end)
    settled = pd.DataFrame([{"race_id": race_id, "day": race["day"].iloc[0], "p": race["p"].iloc[0],
                             **settle(race, race["p"].iloc[0] >= REVERSE_LINE)} for race_id, race in table.groupby("race_id", sort=False)])
    marked = pd.read_pickle(fit.MARKED)
    marked = marked[marked["race_id"].astype(str).isin(set(settled["race_id"]))]
    out = settled.merge(finishes(marked), on="race_id", how="left")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"outcomes_{args.start}_{args.end}.pkl"
    out.to_pickle(path)
    bought = out[out["bought"]]
    print(f"{len(out):,} レース・買った {len(bought):,} レース・回収率 {bought['back'].sum() / bought['stake'].sum():.1%}・"
          f"的中 {(bought['back'] > 0).mean():.1%} → {path}")


if __name__ == "__main__":
    main()
