"""8券種で、回収率 100% 超えと的中率の向上を探す（docs/04 の手順6）。

    uv run python research/レースの種類ごとの買い方/all_tickets.py bracket   # 枠連の組の表を作り、区切りごとに重みを推定して期待値を付ける（十数分）
    uv run python research/レースの種類ごとの買い方/all_tickets.py horses    # 単勝・複勝の買い目の候補を作る
    uv run python research/レースの種類ごとの買い方/all_tickets.py tables    # 単勝・複勝・枠連の、中身の帯 × 決まりの開催日の表（ほかの券種は race_filters.py tables）
    uv run python research/レースの種類ごとの買い方/all_tickets.py subsets   # 4回目: 2モデル一致・3連単の支持ありのレースだけの表
    uv run python research/レースの種類ごとの買い方/all_tickets.py cross     # 5回目: ほかの券種の市場を足した組の確率で表を作る（1時間ほど）
    uv run python research/レースの種類ごとの買い方/all_tickets.py report --trial 1   # 手順6 の1〜4回目の選び方で選び、2019〜2026年で確かめる

出るものは全部 Git 対象外の ``reports/レースの種類ごとの買い方/``。
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from 共通 import db  # noqa: E402

from yosou.shared.betting import TicketType  # noqa: E402
from yosou.shared.repository import RaceDayRange  # noqa: E402

from レースの種類ごとの買い方.analysis.bracket_features import BRACKET_FEATURES, BracketFeatures  # noqa: E402
from レースの種類ごとの買い方.analysis.bracket_source import BracketSource  # noqa: E402
from レースの種類ごとの買い方.analysis.buy_rule import BuyRule, rules_of  # noqa: E402
from レースの種類ごとの買い方.analysis.combo_features import BASE_FEATURES, ComboFeatures  # noqa: E402
from レースの種類ごとの買い方.analysis.cross_pool_features import CROSS_FEATURES, CrossPoolFeatures  # noqa: E402
from レースの種類ごとの買い方.analysis.current_tickets import CurrentTickets  # noqa: E402
from レースの種類ごとの買い方.analysis.filter_selector import FilterSelector  # noqa: E402
from レースの種類ごとの買い方.analysis.fold_valuer import FoldValuer, frames_by_fold  # noqa: E402
from レースの種類ごとの買い方.analysis.hit_rate_selector import HitRatePick, HitRateSelector  # noqa: E402
from レースの種類ごとの買い方.analysis.horse_bets import HorseBets  # noqa: E402
from レースの種類ごとの買い方.analysis.race_traits import SUBSETS, TRAITS  # noqa: E402
from レースの種類ごとの買い方.analysis.rule_day_table import HIT_RACES, RACES, RuleDayTable  # noqa: E402
from レースの種類ごとの買い方.analysis.walk_forward_report import WalkForwardReport  # noqa: E402
from レースの種類ごとの買い方.analysis.weight_method import WeightMethod  # noqa: E402
from レースの種類ごとの買い方.race_filters import _bins, _days  # noqa: E402

_REPORTS = Path(__file__).resolve().parents[2] / "reports"
OUT = _REPORTS / "レースの種類ごとの買い方"
SOURCE = _REPORTS / "複勝以外の回収率100超" / "組の期待値"
MARKED = SOURCE / "marked-2015から.parquet"
CURRENT_CSV = OUT / "印の成績-2015から" / "買い目" / "dscore_race_day_top3-race_day.csv"
YEARS = range(2015, 2027)
FIRST_DAY = "2016-01-01"
SELECT_YEARS = (2016, 2017, 2018)
TEST_YEARS = tuple(range(2019, 2027))
HALVES = ((2019, 2022), (2023, 2026))
GOOD_YEARS = 5
#: 枠連は本番の部品に券種が無いので、ファイルの名前は bracket、組の扱い（2頭・順不同・トリガミ）は馬連と同じにする。
BRACKET_KEY = "bracket"
BRACKET_METHOD = WeightMethod("枠連", BRACKET_KEY, BRACKET_FEATURES, with_kinds=False)
#: 8券種（表に出す名前, ファイルの名前, 組の扱いの券種, 今の本番の買い方の名前, 期待度の絞り）。
TICKETS: tuple[tuple[str, str, TicketType, str | None, str | None], ...] = (
    ("単勝", "win", TicketType.WIN, "単勝", "高"),
    ("複勝", "place", TicketType.PLACE, "複勝", None),
    ("枠連", BRACKET_KEY, TicketType.QUINELLA, None, None),
    ("馬連", "quinella", TicketType.QUINELLA, "馬連（組の期待値）", None),
    ("ワイド", "wide", TicketType.WIDE, "ワイド（組の期待値）", None),
    ("馬単", "exacta", TicketType.EXACTA, "馬単（組の期待値）", None),
    ("3連複", "trio", TicketType.TRIO, "3連複（組の期待値）", None),
    ("3連単", "trifecta", TicketType.TRIFECTA, "3連単（組の期待値）", None),
)
#: 枠連の比べる相手（馬連の今の決まりと同じ形。docs/04 の 4）。
BRACKET_BASE = BuyRule("全", 1.1, 100, 0)
#: 2回目（docs/04 の 7）で選び直す券種と、オッズの上限（比べる相手の上限）。
SECOND_TRIAL_CAPS: dict[str, float] = {"単勝": 30, "馬連": 100, "ワイド": 300, "馬単": 30, "3連複": 1000}
#: 3回目（docs/04 の 8）で選び直す券種と、選ぶ期間の年のうち回収率 100% 以上が要る割合。
THIRD_TRIAL: tuple[str, ...] = ("馬連", "ワイド", "馬単", "3連複")
THIRD_GOOD_SHARE = 2 / 3
#: 6回目（docs/04 の 11）の決まりが1つの券種: 名前 → （組の確率の置き場所, 決まり, 買うレースの条件（中身, 下限, 上限））。
SIXTH_FIXED: dict[str, tuple[str, BuyRule, tuple[str, float | None, float | None]]] = {
    "ワイド": ("cross", BuyRule("高", 1.0, 300, 5), ("favorite_odds", 2.9, None)),
    "3連複": ("now", BuyRule("◎", 1.2, 1000, 5), ("has_danger", None, 0.0)),
}
#: 4回目（docs/04 の 9）で選び直す券種（ファイルの名前）。
FOURTH_TRIAL: dict[str, str] = {"ワイド": "wide", "馬単": "exacta", "3連複": "trio"}


def main() -> None:
    args = _parser().parse_args()
    {"bracket": _bracket, "horses": _horses, "tables": _tables, "subsets": _subsets, "cross": _cross, "report": _report}[args.step](args)


def _bracket(args: argparse.Namespace) -> None:
    kinds = pd.read_parquet(OUT / "kinds.parquet")
    features = BracketFeatures()
    with db.open_db(args.db) as con:
        source = BracketSource(con)

        def load(year: int) -> pd.DataFrame:
            days = RaceDayRange(pd.Timestamp(f"{year}-01-01").date(), pd.Timestamp(f"{year}-12-31").date())
            quinella = pd.read_parquet(SOURCE / "combos" / f"quinella_{year}.parquet",
                                       columns=["rid", "h1", "h2", "q", "t", "hv", "race_date", "expectation", "fold", "top"])
            table = features.build(quinella, source.frames(days), source.odds(days), source.payouts(days), kinds)
            print(f"枠連の組の表: {year} {len(table):,}組・{table['race_id'].nunique():,}レース", flush=True)
            return table

        valued, logs = FoldValuer(TicketType.QUINELLA, BRACKET_METHOD).run(frames_by_fold(load, YEARS))
    path = OUT / "valued" / "now" / f"{BRACKET_KEY}.parquet"
    valued.to_parquet(path)
    path.with_suffix(".json").write_text(json.dumps([asdict(log) for log in logs], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(valued):,}組 → {path}", flush=True)


def _horses(args: argparse.Namespace) -> None:
    kinds = pd.read_parquet(OUT / "kinds.parquet")
    marked = pd.read_parquet(MARKED)
    for ticket_type, key in ((TicketType.WIN, "win"), (TicketType.PLACE, "place")):
        table = HorseBets().of(ticket_type, marked, kinds)
        path = OUT / "valued" / "now" / f"{key}.parquet"
        table.to_parquet(path)
        print(f"{ticket_type.label}: {len(table):,}頭 → {path}", flush=True)


def _tables(args: argparse.Namespace) -> None:
    bins, labels, _ = _bins()
    days = _days()
    for _, key, ticket_type, _, _ in TICKETS:
        if key not in ("win", "place", BRACKET_KEY):
            continue
        path = OUT / "filters" / f"{key}.npz"
        if path.exists() and not args.force:
            print(f"済み: {path}", flush=True)
            continue
        valued = pd.read_parquet(OUT / "valued" / "now" / f"{key}.parquet")
        valued = valued[valued["race_date"] >= FIRST_DAY].merge(labels, on="race_id", how="inner")
        rules = rules_of(ticket_type)
        arrays = {trait: RuleDayTable(ticket_type, days, bins.labels(trait), f"bin_{trait}").build(valued, rules).astype(np.float32)
                  for trait in TRAITS}
        np.savez(path, **arrays)
        print(f"帯の表: {key} → {path}", flush=True)


def _subsets(args: argparse.Namespace) -> None:
    """4回目（docs/04 の 9）: 2モデル一致・3連単の支持ありのレースだけで、中身の帯 × 決まりの開催日の表を作る。
    ``--cross`` なら、5回目の組の確率で作る（8回目。docs/04 の 13。ワイドだけ）。"""
    bins, labels, traits = _bins()
    days = _days()
    folder, suffix = ("cross", "-cross") if args.cross else ("now", "")
    for name, key in FOURTH_TRIAL.items():
        if args.cross and name != "ワイド":
            continue
        ticket_type = next(item[2] for item in TICKETS if item[0] == name)
        valued = pd.read_parquet(OUT / "valued" / folder / f"{key}.parquet")
        valued = valued[valued["race_date"] >= FIRST_DAY].merge(labels, on="race_id", how="inner")
        rules = rules_of(ticket_type)
        for subset in SUBSETS:
            path = OUT / "filters" / f"{key}{suffix}-{subset}.npz"
            if path.exists() and not args.force:
                print(f"済み: {path}", flush=True)
                continue
            races = set(traits.loc[traits[subset] == 1, "race_id"])
            part = valued[valued["race_id"].isin(races)]
            arrays = {trait: RuleDayTable(ticket_type, days, bins.labels(trait), f"bin_{trait}").build(part, rules).astype(np.float32)
                      for trait in TRAITS}
            np.savez(path, **arrays)
            print(f"絞りの表: {name}・{SUBSETS[subset]} → {path}", flush=True)


def _cross(args: argparse.Namespace) -> None:
    """5回目（docs/04 の 10）: ほかの券種の市場を足した組の確率で期待値を付け、中身の帯 × 決まりの開催日の表を作る。"""
    kinds = pd.read_parquet(OUT / "kinds.parquet")
    combos, cross = ComboFeatures(SOURCE / "combos"), CrossPoolFeatures(SOURCE / "combos")
    bins, labels, _ = _bins()
    days = _days()
    for name, key in FOURTH_TRIAL.items():
        ticket_type = next(item[2] for item in TICKETS if item[0] == name)
        path = OUT / "filters" / f"{key}-cross.npz"
        if path.exists() and not args.force:
            print(f"済み: {path}", flush=True)
            continue
        method = WeightMethod("他の市場", "cross", (*BASE_FEATURES, *CROSS_FEATURES[ticket_type]), with_kinds=False)
        valued, logs = FoldValuer(ticket_type, method).run(
            frames_by_fold(lambda year: cross.add(ticket_type, combos.of(ticket_type, year, kinds), year), YEARS))
        saved = OUT / "valued" / "cross" / f"{key}.parquet"
        saved.parent.mkdir(parents=True, exist_ok=True)
        valued.to_parquet(saved)
        saved.with_suffix(".json").write_text(json.dumps([asdict(log) for log in logs], ensure_ascii=False, indent=1), encoding="utf-8")
        valued = valued[valued["race_date"] >= FIRST_DAY].merge(labels, on="race_id", how="inner")
        rules = rules_of(ticket_type)
        arrays = {trait: RuleDayTable(ticket_type, days, bins.labels(trait), f"bin_{trait}").build(valued, rules).astype(np.float32)
                  for trait in TRAITS}
        np.savez(path, **arrays)
        print(f"他の市場: {name} → {path}（重み: {[round(w, 3) for w in logs[-1].weights]}）", flush=True)


def _report(args: argparse.Namespace) -> None:
    days = _days()
    years = days.year.to_numpy()
    report = WalkForwardReport(days, TEST_YEARS, HALVES)
    current = CurrentTickets(CURRENT_CSV, days)
    second = args.trial >= 2
    lines = [f"# 8券種で回収率 100% 超えと的中率の向上（docs/04。2016〜2018年で選び、2019〜2026年で確かめる。手順6 の{args.trial}回目）\n"]
    verdicts = []
    for name, key, ticket_type, label, expectation in TICKETS:
        targets = {1: [item[0] for item in TICKETS], 2: list(SECOND_TRIAL_CAPS), 3: list(THIRD_TRIAL), 4: list(FOURTH_TRIAL),
                   5: list(FOURTH_TRIAL), 6: list(FOURTH_TRIAL), 7: ["ワイド"], 8: ["ワイド"]}[args.trial]
        if name not in targets:
            continue
        suffix = "-cross" if args.trial in (5, 8) else ""
        loaded = np.load(OUT / "filters" / f"{key}{suffix}.npz")
        rules = rules_of(ticket_type)
        tables = {trait: loaded[trait] for trait in TRAITS}
        if args.trial in (4, 6, 8):
            for subset in SUBSETS:
                part = np.load(OUT / "filters" / f"{key}{suffix}-{subset}.npz")
                tables.update({f"{subset}:{trait}": part[trait] for trait in TRAITS})
        selector = FilterSelector(tables, days, rules)
        if label is None:
            base_daily = selector.stack[0, rules.index(BRACKET_BASE)].astype(float)
        else:
            base_daily = current.rule(label, expectation)
        select = np.isin(years, SELECT_YEARS)
        base_hit = base_daily[select, HIT_RACES].sum() / max(base_daily[select, RACES].sum(), 1.0)
        if args.trial == 7:
            pick, cells = _wide_seventh(base_hit, days)
        elif args.trial == 6 and name in SIXTH_FIXED:
            pick, cells = _fixed(name, key, ticket_type, days)
        elif args.trial >= 3:
            pick, cells = _walk_forward(HitRateSelector(selector, days, rules), base_daily, years, SECOND_TRIAL_CAPS[name],
                                        fallback=args.trial in (6, 8))
        else:
            pick, cells = HitRateSelector(selector, days, rules).pick(SELECT_YEARS, base_hit, min_good_share=1.0 if second else None,
                                                                      max_cap=SECOND_TRIAL_CAPS[name] if second else None)
        base = report.summary(f"比べる相手（{label or '枠連・' + BRACKET_BASE.text}）", base_daily)
        rows = [base]
        passed = False
        if cells is not None:
            title = f"{pick.rule.text}・{pick.filter_text}" if pick is not None and pick.rule else "年ごとに選び直し（最後の年は選べず）"
            chosen = report.summary(f"選んだもの: {title}", cells)
            rows.append(chosen)
            passed = (chosen.payback > 1.0 and chosen.low > 1.0 and chosen.hit_rate > base.hit_rate and chosen.good_years >= GOOD_YEARS)
        verdicts.append((name, passed))
        table = report.table(rows, base, [row.name for row in rows]).drop(columns=["基準1〜4", "候補"])
        lines += [f"\n## {name}\n",
                  f"2016〜2018年: 比べる相手の的中率 {100 * base_hit:.2f}%・選んだものの回収率 {100 * pick.payback:.1f}%・幅の下の端 {100 * pick.lower:.1f}%"
                  f"・的中率 {100 * pick.hit_rate:.2f}%（条件を満たした候補 {pick.eligible}）\n",
                  table.to_markdown(index=False), "\n年ごとの回収率（%）\n", report.yearly(rows).to_markdown(),
                  f"\n- 採用の基準（docs/04 の 5）: {'満たす' if passed else '満たさない'}"]
        print("\n".join(lines[-5:]), flush=True)
    lines.append("\n## まとめ\n\n" + "\n".join(f"- {name}: {'満たす' if passed else '満たさない'}" for name, passed in verdicts))
    (OUT / "全券種-手順6.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(lines[-1], flush=True)


def _wide_seventh(base_hit: float, days: pd.DatetimeIndex) -> tuple[HitRatePick, np.ndarray | None]:
    """7回目（docs/04 の 12）: ワイドの点数 × 線の9つから、2016〜2018年だけで選ぶ。"""
    folder, rule, (trait, low, _) = SIXTH_FIXED["ワイド"]
    rules = [BuyRule(rule.scope, line, rule.cap, points) for points in (3, 4, 5) for line in (1.0, 1.1, 1.2)]
    _, _, traits = _bins()
    flags = pd.DataFrame({"race_id": traits["race_id"], "pass": np.where(traits[trait] >= low, "1", "0")})
    valued = pd.read_parquet(OUT / "valued" / folder / "wide.parquet")
    valued = valued[valued["race_date"] >= FIRST_DAY].merge(flags, on="race_id", how="inner")
    table = RuleDayTable(TicketType.WIDE, days, ["0", "1"], "pass").build(valued, rules)[:, 1]
    selector = FilterSelector({"pass": table[:, None, :, :]}, days, rules)
    pick, cells = HitRateSelector(selector, days, rules).pick(SELECT_YEARS, base_hit)
    if pick.rule is not None:
        pick = replace(pick, filter_text=f"1番人気が {low}倍以上（組の確率: 5回目。点数 × 線の9つから 2016〜2018年で選ぶ）")
    return pick, cells


def _fixed(name: str, key: str, ticket_type: TicketType, days: pd.DatetimeIndex):
    """6回目（docs/04 の 11）の決まりが1つの券種: その決まりと買うレースの条件の、開催日ごとの成績。"""
    folder, rule, (trait, low, high) = SIXTH_FIXED[name]
    _, _, traits = _bins()
    values = traits[trait]
    passes = values.notna() & (values >= low if low is not None else True) & (values <= high if high is not None else True)
    flags = pd.DataFrame({"race_id": traits["race_id"], "pass": np.where(passes, "1", "0")})
    valued = pd.read_parquet(OUT / "valued" / folder / f"{key}.parquet")
    valued = valued[valued["race_date"] >= FIRST_DAY].merge(flags, on="race_id", how="inner")
    cells = RuleDayTable(ticket_type, days, ["0", "1"], "pass").build(valued, [rule])[0, 1]
    text = {"favorite_odds": f"1番人気が {low}倍以上", "has_danger": "危険な人気馬がいない"}[trait]
    return HitRatePick(rule, f"{text}（組の確率: {'5回目' if folder == 'cross' else '今'}）", float("nan"), float("nan"), float("nan"), 1), cells


def _walk_forward(selector: HitRateSelector, base_daily: np.ndarray, years: np.ndarray, max_cap: float, fallback: bool = False):
    """3回目（docs/04 の 8）: 2019〜2026年の各年について、その年より前の全部で選び直し、その年の成績をつなぐ。
    ``fallback`` なら、選べない年は比べる相手（今の決まり）の成績を使う（6回目。docs/04 の 11）。
    （最後の年に選んだもの（成績の表の名前に使う）, つないだ開催日ごとの成績 [開催日, 4]）。"""
    result = np.zeros_like(base_daily)
    last = None
    texts = []
    for year in TEST_YEARS:
        window = tuple(range(SELECT_YEARS[0], year))
        inside = np.isin(years, window)
        base_hit = base_daily[inside, HIT_RACES].sum() / max(base_daily[inside, RACES].sum(), 1.0)
        pick, cells = selector.pick(window, base_hit, min_good_share=THIRD_GOOD_SHARE, max_cap=max_cap)
        texts.append(f"{year}: {pick.rule.text + '・' + pick.filter_text if pick.rule else '買わない'}")
        if cells is not None:
            result[years == year] = cells[years == year]
        elif fallback:
            result[years == year] = base_daily[years == year]
            texts[-1] = f"{year}: 今の決まり（選べない）"
        last = pick
    print("  " + " / ".join(texts), flush=True)
    return replace(last, filter_text=f"{last.filter_text}（年ごとに選び直し）") if last is not None and last.rule else last, result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="8券種で回収率 100% 超えと的中率の向上を探す（docs/04）", allow_abbrev=False)
    parser.add_argument("step", choices=("bracket", "horses", "tables", "subsets", "cross", "report"))
    parser.add_argument("--force", action="store_true", help="済んだものも作り直す")
    parser.add_argument("--cross", action="store_true", help="subsets で、5回目の組の確率で作る（8回目。ワイドだけ）")
    parser.add_argument("--trial", type=int, choices=tuple(range(1, 9)), default=1, help="report の何回目の選び方か（docs/04 の 4・7〜13）")
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    return parser


if __name__ == "__main__":
    main()
