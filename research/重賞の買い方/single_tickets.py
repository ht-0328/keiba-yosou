"""研究「重賞の買い方」3回目の入口: 重賞の単勝・複勝（単系）の買い方を 2015〜2020年で選び、2021〜2026年で一度だけ確かめる（docs/04）。

    uv run python research/重賞の買い方/single_tickets.py pick    # 2015〜2020年の重賞だけで、単勝・複勝の候補から1つずつ選ぶ（3回目/選んだ買い方.md・.json）
    uv run python research/重賞の買い方/single_tickets.py check   # 2021〜2026年の重賞で一度だけ数える（3回目/確かめ.md）

先に ``stakes_bets.py races``（重賞.parquet）と、研究「複勝以外の回収率100超」の印を付けた表が要る。出るものは Git 対象外の ``reports/重賞の買い方/3回目/``。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from 共通 import render  # noqa: E402
from 共通.render import Table  # noqa: E402

from 全レース全券種の買い方.materials import MARKED  # noqa: E402
from 重賞の買い方.analysis.single_ticket_grid import MIN_HITS, SingleRule, SingleTicketGrid  # noqa: E402
from 重賞の買い方.stakes_bets import GRADED, OUT as STAKES_OUT  # noqa: E402

OUT = STAKES_OUT / "3回目"
SELECT_YEARS = range(2015, 2021)
CONFIRM_YEARS = range(2021, 2027)
_COLUMNS = ["race_id", "race_date", "horse_no", "mark", "popularity", "field_size", "win_value", "win_odds", "win_payout",
            "place_value", "place_odds_low", "place_payout"]


def main() -> None:
    args = _parser().parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    {"pick": _pick, "check": _check}[args.command]()


def _horses(years: range) -> pd.DataFrame:
    """平地の重賞の馬（印を付けた表 × 重賞の一覧）。"""
    marked = pd.read_parquet(MARKED, columns=_COLUMNS).assign(race_id=lambda frame: frame["race_id"].astype(str))
    graded = pd.read_parquet(GRADED)[["race_id", "grade"]].assign(race_id=lambda frame: frame["race_id"].astype(str))
    horses = marked.merge(graded, on="race_id", how="inner")
    return horses[pd.to_datetime(horses["race_date"]).dt.year.isin(years)].reset_index(drop=True)


def _pick() -> None:
    """選ぶ期間（2015〜2020年の重賞）だけを見て、券種ごとに、当たりが ``MIN_HITS`` 以上の候補のうち下の端がいちばん高いものを選ぶ（docs/04 の 3）。"""
    grid, horses = SingleTicketGrid(), _horses(SELECT_YEARS)
    scored = [(rule, grid.score(horses, rule)) for rule in grid.rules()]
    chosen, tables = {}, []
    for ticket in ("単勝", "複勝"):
        enough = sorted([(rule, score) for rule, score in scored if rule.ticket == ticket and score["当たり"] >= MIN_HITS],
                        key=lambda item: -item[1]["下の端"])
        if enough:
            chosen[ticket] = enough[0][0]
        tables.append(Table(["買い方", "点", "レース", "当たり", "回収率", "下の端", "的中率"],
                            [[rule.label, f"{score['点']:,}", f"{score['レース']:,}", f"{score['当たり']:,}", _pct(score["回収率"]), _pct(score["下の端"]),
                              _pct(score["的中率"])] for rule, score in enough[:10]],
                            title=f"{ticket}: 下の端の高い順に10個（重賞の {SELECT_YEARS.start}〜{SELECT_YEARS.stop - 1}年。当たり {MIN_HITS} 以上）"))
    (OUT / "選んだ買い方.json").write_text(json.dumps({ticket: rule.__dict__ for ticket, rule in chosen.items()}, ensure_ascii=False, indent=1), encoding="utf-8")
    render.write(render.render(tables, "markdown"), OUT / "選んだ買い方.md", fmt="markdown")
    print(f"保存先: {OUT / '選んだ買い方.md'}", file=sys.stderr)
    for ticket, rule in chosen.items():
        print(f"{ticket}: {rule.label}", file=sys.stderr)


def _check() -> None:
    """確かめる期間（2021〜2026年の重賞）で、選んだ買い方を一度だけ数える。採用の線は docs/04 の 4。"""
    chosen = {ticket: SingleRule(**values) for ticket, values in json.loads((OUT / "選んだ買い方.json").read_text(encoding="utf-8")).items()}
    grid, horses = SingleTicketGrid(), _horses(CONFIRM_YEARS)
    rows, tables, verdicts = [], [], []
    for ticket, rule in chosen.items():
        score = grid.score(horses, rule)
        yearly = grid.yearly(horses, rule)
        passed = score["回収率"] > 1.0
        verdicts.append(f"{ticket}: {'満たす' if passed else '満たさない'}")
        rows.append([rule.label, f"{score['点']:,}", f"{score['レース']:,}", _pct(score["回収率"]), _pct(score["下の端"]), _pct(score["的中率"]),
                     f"{int((yearly['回収率'] > 1.0).sum())}/{len(yearly)}", "満たす" if passed else "満たさない"])
        tables.append(Table(["年", "点", "回収率", "的中率"], [[int(row["年"]), f"{row['点']:,}", _pct(row["回収率"]), _pct(row["的中率"])]
                                                        for _, row in yearly.iterrows()], title=f"{rule.label}: 年ごと"))
        by_grade = [[grade, *_brief(grid.score(horses[horses["grade"] == grade], rule))] for grade in ("G1", "G2", "G3")]
        tables.append(Table(["格", "点", "回収率", "的中率"], by_grade, title=f"{rule.label}: 格ごと"))
    head = Table(["買い方", "点", "レース", "回収率", "下の端", "的中率", "100% 超えの年", "採用の線"], rows,
                 title=f"結果（重賞の {CONFIRM_YEARS.start}〜{CONFIRM_YEARS.stop - 1}年。1点 100円・確定オッズ）",
                 note="採用の線（docs/04 の 4）: 確かめる期間の重賞で回収率 100% 超え。")
    render.write(render.render([head, *tables], "markdown"), OUT / "確かめ.md", fmt="markdown")
    print(f"保存先: {OUT / '確かめ.md'}\n" + "\n".join(verdicts), file=sys.stderr)


def _brief(score: dict[str, float]) -> list[str]:
    return [f"{score['点']:,}", _pct(score["回収率"]), _pct(score["的中率"])]


def _pct(value: float) -> str:
    return "―" if value is None or not np.isfinite(value) else f"{value:.1%}"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("pick", help="2015〜2020年の重賞だけで、単勝・複勝の候補から1つずつ選ぶ")
    subparsers.add_parser("check", help="2021〜2026年の重賞で一度だけ数える")
    return parser


if __name__ == "__main__":
    main()
