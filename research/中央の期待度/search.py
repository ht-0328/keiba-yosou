"""全レースに ◎ を付ける形のまま、◎ の選び方（確率の寄せ方・オッズの効かせ方・オッズの上下限・1番人気を外すか）× 重み × 等級の割合を広く変えて、
全等級で ◎ の単勝回収率が 100% を超える組があるかを探す（約 2,000 の選び方 × 14 = 約 2万4千の組。数分）。

    uv run python research/中央の期待度/search.py

全頭の行は expectation.py が reports/中央の期待度/cache/ にとっておいたもの。元DB は開かない。
出るものは Git 対象外の reports/中央の期待度/全レースの選び方-当日.md（◎ の全体の単勝回収率の上位と、等級のいちばん低い回収率の上位）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from 共通 import render  # noqa: E402
from 共通.render import Table  # noqa: E402

from 中央の期待度.analysis.rule_search import Combo, RuleSearch  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "reports" / "中央の期待度"


def main() -> None:
    rows = pd.read_pickle(OUT / "cache" / "全頭-h2h_pool_ability_h2h-race_day.pkl")
    rows["year"] = pd.to_datetime(rows["race_date"]).dt.year
    search = RuleSearch(rows, [2023, 2024])
    combos = [combo for rule in search.rules() for combo in search.combos(rule)]
    by_rule = {combo.rule: combo for combo in combos}
    overall = sorted(by_rule.values(), key=lambda combo: -combo.search_all)[:20]
    lowest = sorted(combos, key=lambda combo: -Combo.lowest(combo.search))[:20]

    def cells(rates: dict) -> str:
        return " ".join(f"{grade}{rates[grade][1] * 100:.0f}/{rates[grade][0] * 100:.0f}" for grade in "SABC" if grade in rates)

    tables = [
        Table(["◎ の選び方", "◎ が付いたレース", "探す期間の単勝回収率", "確かめる期間の単勝回収率"],
              [[combo.rule.label, f"{combo.coverage:.1%}", f"{combo.search_all:.1%}", f"{combo.check_all:.1%}"] for combo in overall],
              title="1. ◎ の全体の単勝回収率の上位（探す期間 2023〜2024年）"),
        Table(["◎ の選び方", "重み", "割合", "探す期間 単勝回収率/勝率", "確かめる期間 単勝回収率/勝率", "探す期間の条件"],
              [[combo.rule.label, f"{combo.weight:g}", "・".join(f"{share:.0%}" for share in combo.shares), cells(combo.search), cells(combo.check),
                "満たす" if Combo.passes(combo.search) else "—"] for combo in lowest],
              title="2. 等級のいちばん低い単勝回収率の上位", note=f"調べた組 {len(combos):,}。探す期間で条件を満たした組 {sum(Combo.passes(c.search) for c in combos)}。"),
    ]
    path = OUT / "全レースの選び方-当日.md"
    render.write(render.render(tables, "markdown"), path, fmt="markdown")
    print(f"保存先: {path}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
