"""券種ごとに、レースの中身で買うレースを絞る案を確かめる（docs/03 の手順5）。

    uv run python research/レースの種類ごとの買い方/race_filters.py traits    # レースの中身の表を作る（数分）
    uv run python research/レースの種類ごとの買い方/race_filters.py tables    # 券種ごとに、中身の帯 × 決まりの開催日の表を作る（十数分）
    uv run python research/レースの種類ごとの買い方/race_filters.py report    # 2019〜2026年の A（仮説の絞り方）と B（年ごとに選び直す）の成績と採否

組の確率の重みは案「今」（walk_forward.py value が作った ``valued/now/``）。出るものは全部 Git 対象外の ``reports/レースの種類ごとの買い方/``。
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

from yosou.shared.betting import TicketType  # noqa: E402

from レースの種類ごとの買い方.analysis.buy_rule import CURRENT_RULES, rules_of  # noqa: E402
from レースの種類ごとの買い方.analysis.filter_selector import FilterSelector  # noqa: E402
from レースの種類ごとの買い方.analysis.race_filter import HYPOTHESES  # noqa: E402
from レースの種類ごとの買い方.analysis.race_traits import TRAITS, RaceTraits  # noqa: E402
from レースの種類ごとの買い方.analysis.rule_day_table import RuleDayTable  # noqa: E402
from レースの種類ごとの買い方.analysis.trait_bins import TraitBins  # noqa: E402
from レースの種類ごとの買い方.analysis.walk_forward_report import WalkForwardReport  # noqa: E402

_REPORTS = Path(__file__).resolve().parents[2] / "reports"
OUT = _REPORTS / "レースの種類ごとの買い方"
MARKED = _REPORTS / "複勝以外の回収率100超" / "組の期待値" / "marked-2015から.parquet"
#: 帯の区切りを決める期間（仮説を立てた期間）と、数える年・前半後半（docs/03 の 3・4）。
REFERENCE_YEARS = (2016, 2018)
TEST_YEARS = tuple(range(2019, 2027))
HALVES = ((2019, 2022), (2023, 2026))
FIRST_DAY = "2016-01-01"
TICKET_TYPES = (TicketType.EXACTA, TicketType.WIDE, TicketType.TRIO, TicketType.TRIFECTA, TicketType.QUINELLA)
#: 仮説に合うかの列。
HYPOTHESIS = "hypothesis"
#: B の採用に要る、回収率 100% 超えの年の数（8年のうち）。A の採用に要る、絞ったほうが良かった年の数。
GOOD_YEARS = 5


def main() -> None:
    args = _parser().parse_args()
    {"traits": _traits, "tables": _tables, "report": _report}[args.step](args)


def _traits(args: argparse.Namespace) -> None:
    traits = RaceTraits().of(pd.read_parquet(MARKED))
    traits.to_parquet(OUT / "traits.parquet")
    print(f"{len(traits):,}レース → {OUT / 'traits.parquet'}", flush=True)


def _bins() -> tuple[TraitBins, pd.DataFrame, pd.DataFrame]:
    """（帯の区切り, 帯の表, 中身の表）。区切りは 2016〜2018年のレースの5分位。"""
    traits = pd.read_parquet(OUT / "traits.parquet")
    kinds = pd.read_parquet(OUT / "kinds.parquet", columns=["race_id", "race_date"])
    traits = traits.merge(kinds, on="race_id", how="inner")
    years = pd.to_datetime(traits["race_date"]).dt.year
    bins = TraitBins(traits[years.between(*REFERENCE_YEARS)])
    return bins, bins.of(traits), traits


def _days() -> pd.DatetimeIndex:
    dates = pd.to_datetime(pd.read_parquet(OUT / "kinds.parquet", columns=["race_date"])["race_date"])
    return pd.DatetimeIndex(sorted(dates[dates >= FIRST_DAY].unique()))


def _tables(args: argparse.Namespace) -> None:
    bins, labels, traits = _bins()
    days = _days()
    for ticket_type in TICKET_TYPES:
        path = OUT / "filters" / f"{ticket_type.spec.key}.npz"
        if path.exists() and not args.force:
            print(f"済み: {path}", flush=True)
            continue
        valued = pd.read_parquet(OUT / "valued" / "now" / f"{ticket_type.spec.key}.parquet")
        valued = valued[valued["race_date"] >= FIRST_DAY]
        passes = HYPOTHESES[ticket_type].passes(traits).astype(int).astype(str)
        flags = pd.DataFrame({"race_id": traits["race_id"], HYPOTHESIS: passes.to_numpy()})
        valued = valued.merge(labels, on="race_id", how="inner").merge(flags, on="race_id", how="inner")
        rules = rules_of(ticket_type)
        arrays = {trait: RuleDayTable(ticket_type, days, bins.labels(trait), f"bin_{trait}").build(valued, rules).astype(np.float32)
                  for trait in TRAITS}
        arrays[HYPOTHESIS] = RuleDayTable(ticket_type, days, ["0", "1"], HYPOTHESIS).build(valued, rules).astype(np.float32)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, **arrays)
        print(f"帯の表: {ticket_type.label} → {path}", flush=True)
    edges = {trait: [round(float(edge), 4) for edge in bins.edges(trait)] for trait in TRAITS if trait != "has_danger"}
    (OUT / "filters" / "帯の区切り.json").write_text(json.dumps(edges, ensure_ascii=False, indent=1), encoding="utf-8")


def _report(args: argparse.Namespace) -> None:
    days = _days()
    report = WalkForwardReport(days, TEST_YEARS, HALVES)
    edges = json.loads((OUT / "filters" / "帯の区切り.json").read_text(encoding="utf-8"))
    lines = ["# 券種ごとに向くレース（2019〜2026年・当日の予想・確定オッズ・1点 100円・トリガミ除く。docs/03）\n",
             "帯の区切り（2016〜2018年のレースの5分位。区切りちょうどの値は上の帯）: "
             + "・".join(f"{trait} {edges[trait]}" for trait in edges) + "\n"]
    choice_lines = ["# B で年ごとに選んだ決まりと絞り方\n"]
    for ticket_type in TICKET_TYPES:
        loaded = np.load(OUT / "filters" / f"{ticket_type.spec.key}.npz")
        rules = rules_of(ticket_type)
        at = rules.index(CURRENT_RULES[ticket_type])
        hypothesis = loaded[HYPOTHESIS]
        current = report.summary("今の決まり（絞らない）", hypothesis[at].sum(axis=0).astype(float))
        filtered = report.summary(f"A: 今の決まり ＋ {HYPOTHESES[ticket_type].text}", hypothesis[at, 1].astype(float))
        selector = FilterSelector({trait: loaded[trait] for trait in TRAITS}, days, rules)
        daily, choices = selector.run(TEST_YEARS)
        chosen = report.summary("B: 決まりと絞り方を年ごとに選び直す", daily)
        latest, _ = selector.choose(TEST_YEARS[-1] + 1)
        a_years = sum(1 for year in TEST_YEARS if filtered.yearly[year] >= current.yearly[year])
        adopt_a = filtered.payback > current.payback and filtered.low > 1.0 and a_years >= GOOD_YEARS
        adopt_b = chosen.payback > 1.0 and chosen.low > 1.0 and chosen.good_years >= GOOD_YEARS
        table = report.table([current, filtered, chosen], current, [current.name, filtered.name, chosen.name])
        lines += [f"\n## {ticket_type.label}\n", table.drop(columns=["基準1〜4", "候補"]).to_markdown(index=False),
                  "\n\n年ごとの回収率（%）\n", report.yearly([current, filtered, chosen]).to_markdown(),
                  f"\n\n- A の採用: {'満たす' if adopt_a else '満たさない'}（絞ったほうが良かった年 {a_years} / {len(TEST_YEARS)}）",
                  f"- B の採用: {'満たす' if adopt_b else '満たさない'}（100% 超えの年 {chosen.good_years} / {len(TEST_YEARS)}）",
                  f"- B を 2016〜2026年の全部で選んだもの（本番に入れるならこれ）: "
                  f"{latest.rule.text if latest.rule else '買わない'}・{latest.filter_text}（回収率の下の端 {100 * latest.lower_rate:.1f}%）"]
        choice_lines.append(f"\n## {ticket_type.label}\n")
        choice_lines += [f"- {choice.year}: {choice.rule.text if choice.rule else '買わない'}・{choice.filter_text}"
                         f"（回収率の下の端 {100 * choice.lower_rate:.1f}%）" for choice in choices]
        print("\n".join(lines[-7:]), flush=True)
    (OUT / "券種ごとに向くレース.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "券種ごとに向くレース-選んだもの.md").write_text("\n".join(choice_lines) + "\n", encoding="utf-8")
    print(f"\n保存先: {OUT / '券種ごとに向くレース.md'}", file=sys.stderr)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="券種ごとに、レースの中身で買うレースを絞る案を確かめる（docs/03）", allow_abbrev=False)
    parser.add_argument("step", choices=("traits", "tables", "report"))
    parser.add_argument("--force", action="store_true", help="済んだものも作り直す")
    return parser


if __name__ == "__main__":
    main()
