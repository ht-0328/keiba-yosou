"""組の確率の重みと買う決まりを、レースの種類ごとに変える案を、ウォークフォワードで確かめる（docs/01 の手順2・3）。

    uv run python research/レースの種類ごとの買い方/walk_forward.py kinds                              # レースの種類を元DB から読む（数分）
    uv run python research/レースの種類ごとの買い方/walk_forward.py value --ticket 3連単 --method 種類   # 区切りごとに重みを推定し、期待値を付ける
    uv run python research/レースの種類ごとの買い方/walk_forward.py table --ticket 3連単 --method 種類   # 決まりの候補ごとの開催日の表
    uv run python research/レースの種類ごとの買い方/walk_forward.py check-weights                      # 案「今」の重みが本番の直前1年の重みと同じか
    uv run python research/レースの種類ごとの買い方/walk_forward.py report                              # 年ごとに決まりを選び、2018〜2026年の成績と採否を出す

``--ticket``・``--method`` を省くと全部の券種・全部の案を順に回す。組の表は研究「複勝以外の回収率100超」の
``reports/複勝以外の回収率100超/組の期待値/combos/``、比べる相手の今の本番の買い目は同じ研究の ``印の成績-2015から/買い目/`` の CSV を読む。
出るものは全部 Git 対象外の ``reports/レースの種類ごとの買い方/``。
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from 共通 import db  # noqa: E402

from yosou.shared.betting import TicketType  # noqa: E402

from レースの種類ごとの買い方.analysis.buy_rule import CURRENT_RULES, rules_of  # noqa: E402
from レースの種類ごとの買い方.analysis.combo_features import ComboFeatures  # noqa: E402
from レースの種類ごとの買い方.analysis.current_tickets import CurrentTickets  # noqa: E402
from レースの種類ごとの買い方.analysis.fold_valuer import FoldValuer, frames_by_fold  # noqa: E402
from レースの種類ごとの買い方.analysis.race_kinds import KIND_GROUPS, RaceKinds  # noqa: E402
from レースの種類ごとの買い方.analysis.rule_day_table import RuleDayTable  # noqa: E402
from レースの種類ごとの買い方.analysis.walk_forward_report import TEST_YEARS, WalkForwardReport  # noqa: E402
from レースの種類ごとの買い方.analysis.walk_forward_selector import BY_KIND, RATE, UNIFORM, WalkForwardSelector  # noqa: E402
from レースの種類ごとの買い方.analysis.weight_method import METHODS, WeightMethod  # noqa: E402

_REPORTS = Path(__file__).resolve().parents[2] / "reports"
OUT = _REPORTS / "レースの種類ごとの買い方"
SOURCE = _REPORTS / "複勝以外の回収率100超"
COMBOS = SOURCE / "組の期待値" / "combos"
CURRENT_CSV = SOURCE / "印の成績-2015から" / "買い目" / "dscore_race_day_top3-race_day.csv"
PRODUCTION_ROLLING = SOURCE / "組の期待値" / "rolling_weights-2015から.json"
#: 組の表のある年（2015年は 2016年前半の重みを推定するためだけに使う）。
YEARS = range(2015, 2027)
#: 数える開催日の始まり（決まりを選ぶ期間の始まり）。
FIRST_DAY = "2016-01-01"
#: 券種の順（docs/01）。3連単は組が多いので、重みは3つに1つのレースで推定する（本番と同じ）。
TICKET_TYPES = (TicketType.EXACTA, TicketType.WIDE, TicketType.TRIO, TicketType.TRIFECTA, TicketType.QUINELLA)
SAMPLE = {TicketType.TRIFECTA: 3}


def main() -> None:
    args = _parser().parse_args()
    {"kinds": _kinds, "value": _value, "table": _table, "check-weights": _check_weights, "report": _report}[args.step](args)


def _kinds(args: argparse.Namespace) -> None:
    with db.open_db(args.db) as con:
        kinds = RaceKinds().read(con, "2015-01-01")
    OUT.mkdir(parents=True, exist_ok=True)
    kinds.to_parquet(OUT / "kinds.parquet")
    print(f"{len(kinds):,}レース → {OUT / 'kinds.parquet'}", flush=True)


def _value(args: argparse.Namespace) -> None:
    kinds = pd.read_parquet(OUT / "kinds.parquet")
    features = ComboFeatures(COMBOS)
    for ticket_type in _tickets(args):
        for method in _methods(args):
            path = OUT / "valued" / method.key / f"{ticket_type.spec.key}.parquet"
            if path.exists() and not args.force:
                print(f"済み: {path}", flush=True)
                continue
            print(f"期待値: {ticket_type.label}・{method.name}", flush=True)
            valuer = FoldValuer(ticket_type, method, SAMPLE.get(ticket_type, 1))
            valued, logs = valuer.run(frames_by_fold(lambda year: features.of(ticket_type, year, kinds), YEARS))
            path.parent.mkdir(parents=True, exist_ok=True)
            valued.to_parquet(path)
            path.with_suffix(".json").write_text(json.dumps([asdict(log) for log in logs], ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"  {len(valued):,}組 → {path}（罰則: {' '.join(f'{log.fold}={log.penalty:g}' for log in logs)}）", flush=True)


def _table(args: argparse.Namespace) -> None:
    days = _days()
    for ticket_type in _tickets(args):
        rules = rules_of(ticket_type)
        for method in _methods(args):
            path = OUT / "tables" / f"{method.key}_{ticket_type.spec.key}.npy"
            if path.exists() and not args.force:
                print(f"済み: {path}", flush=True)
                continue
            valued = pd.read_parquet(OUT / "valued" / method.key / f"{ticket_type.spec.key}.parquet")
            valued = valued[valued["race_date"] >= FIRST_DAY]
            table = RuleDayTable(ticket_type, days).build(valued, rules)
            path.parent.mkdir(parents=True, exist_ok=True)
            np.save(path, table.astype(np.float32))
            print(f"決まりの表: {ticket_type.label}・{method.name} → {path}", flush=True)


def _check_weights(args: argparse.Namespace) -> None:
    """案「今」の区切りごとの重みが、本番の直前1年の重み（研究「複勝以外の回収率100超」の手順6）と同じかを確かめる。"""
    production = json.loads(PRODUCTION_ROLLING.read_text(encoding="utf-8"))
    for ticket_type in TICKET_TYPES:
        logs = json.loads((OUT / "valued" / "now" / f"{ticket_type.spec.key}.json").read_text(encoding="utf-8"))
        gaps = [max(abs(a - b) for a, b in zip(log["weights"], production[log["fold"]][ticket_type.label].values()))
                for log in logs if log["fold"] in production]
        print(f"{ticket_type.label}: {len(gaps)}区切り・重みの差の最大 {max(gaps):.2e}", flush=True)


def _report(args: argparse.Namespace) -> None:
    days = _days()
    report = WalkForwardReport(days)
    current_daily = CurrentTickets(CURRENT_CSV, days).read()
    lines = ["# レースの種類ごとの買い方（2018〜2026年のウォークフォワード・当日の予想・確定オッズ・1点 100円・トリガミ除く）\n",
             "基準1〜4 は docs/01 の 6（1: 回収率と幅の下の端が 100% 超え、2: 回収率・レース・的中率が今の本番以上、"
             "3: 前半・後半とも回収率が今の本番以上、4: 100% 超えの年が5年以上）。「候補」は4つとも満たした案。\n",
             "「今の本番の選び方で年ごとに選び直し」は、今の本番の決まりを選んだのと同じ基準（回収率の 90% の幅の下の端・当たり 200回以上・"
             "重み「今」・一律）で年ごとに選び直した、比べる目安の行（結果を見たあとに足した。採否には使わない）。\n"]
    choices_lines = ["# 年ごとに選んだ決まり\n"]
    for ticket_type in _tickets(args):
        rules = rules_of(ticket_type)
        current = report.summary("今の本番", current_daily[ticket_type])
        fixed_table = np.load(OUT / "tables" / f"now_{ticket_type.spec.key}.npy")
        fixed = report.summary("今の決まりのまま・重み「今」（数え方の確かめ）", fixed_table[rules.index(CURRENT_RULES[ticket_type])].sum(axis=0))
        now_table = np.load(OUT / "tables" / f"now_{ticket_type.spec.key}.npy")
        reselected, _ = WalkForwardSelector(now_table, days, rules, KIND_GROUPS).run(UNIFORM, TEST_YEARS, RATE)
        honest = report.summary("今の本番の選び方で年ごとに選び直し（比べる目安）", reselected)
        summaries = [current, fixed, honest]
        references = [fixed.name, honest.name]
        for method in METHODS:
            table = np.load(OUT / "tables" / f"{method.key}_{ticket_type.spec.key}.npy")
            selector = WalkForwardSelector(table, days, rules, KIND_GROUPS)
            for mode in (UNIFORM, BY_KIND):
                daily, choices = selector.run(mode, TEST_YEARS)
                summaries.append(report.summary(f"重み「{method.name}」× 決まり「{mode}」", daily))
                choices_lines.append(f"\n## {ticket_type.label}・重み「{method.name}」× 決まり「{mode}」\n")
                choices_lines += [f"- {choice.year} {choice.group}: {choice.rule.text if choice.rule else '買わない'}"
                                  f"（利益の下の端 {choice.lower_profit:,.0f}円）" for choice in choices]
        lines += [f"\n## {ticket_type.label}\n", report.table(summaries, current, references).to_markdown(index=False),
                  "\n\n年ごとの回収率（%）\n", report.yearly(summaries).to_markdown()]
        print(f"\n## {ticket_type.label}\n" + report.table(summaries, current, references).to_markdown(index=False), flush=True)
    (OUT / "結果.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "選んだ決まり.md").write_text("\n".join(choices_lines) + "\n", encoding="utf-8")
    print(f"\n保存先: {OUT / '結果.md'}・{OUT / '選んだ決まり.md'}", file=sys.stderr)


def _days() -> pd.DatetimeIndex:
    dates = pd.to_datetime(pd.read_parquet(OUT / "kinds.parquet", columns=["race_date"])["race_date"])
    return pd.DatetimeIndex(sorted(dates[dates >= FIRST_DAY].unique()))


def _tickets(args: argparse.Namespace) -> tuple[TicketType, ...]:
    return (TicketType.parse(args.ticket),) if args.ticket else TICKET_TYPES


def _methods(args: argparse.Namespace) -> tuple[WeightMethod, ...]:
    return tuple(method for method in METHODS if method.name == args.method) if args.method else METHODS


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="重みと決まりをレースの種類ごとに変える案を確かめる（docs/01）", allow_abbrev=False)
    parser.add_argument("step", choices=("kinds", "value", "table", "check-weights", "report"))
    parser.add_argument("--ticket", default=None, help="券種（馬単・ワイド・3連複・3連単・馬連）。省くと全部")
    parser.add_argument("--method", default=None, help="重みの案（今・種類・材料・種類＋材料）。省くと全部")
    parser.add_argument("--force", action="store_true", help="済んだものも作り直す")
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    return parser


if __name__ == "__main__":
    main()
