"""地方の万馬券: 馬連と3連複で回収率 100% 超の買い方を探す（研究「地方の万馬券」の入口。docs/06）。

    uv run python research/地方の万馬券/quinella_trio.py --build            # 組の表を作る（5頭以上・2024年以降。20〜30分）。そのあと段1 を評価
    uv run python research/地方の万馬券/quinella_trio.py --stage 1          # 段1: 帯 × 線 × 頭数 × 点数の上限（表は作ってある前提。数分）
    uv run python research/地方の万馬券/quinella_trio.py --stage 2 --base "3連複|1.0|20|300|8|3"   # 段2: 段1 で選んだ買い方に組の形を重ねる
    uv run python research/地方の万馬券/quinella_trio.py --stage 3 --base "3連複|1.0|20|300|8|3"   # 段3: 荒れ具合の条件を重ねる
    uv run python research/地方の万馬券/quinella_trio.py --build --pool-free                       # 段4: 票の見立てを使わない確率で表を作り直し、段1 を評価

組の確率は段5（1着・2着・3着を分けて市場に合わせる）。各年を残りの年で当てはめた未見の成績で、前の年だけで当てはめた成績も添える。
出るもの（Git 対象外）: ``reports/地方の万馬券/馬連と3連複/<券種>.pkl``（組の表）・``馬連と3連複の買い方-段N.md``。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

_RESEARCH = Path(__file__).resolve().parents[1]
_REPO_ROOT = _RESEARCH.parent
sys.path[:0] = [str(_RESEARCH), str(_REPO_ROOT / "tools")]

from 共通 import cli, db  # noqa: E402
from 地方の推奨買目.position_model import EV, PROBABILITY  # noqa: E402
from 地方の万馬券.analysis.quinella_trio.rule import QuinellaTrioRule  # noqa: E402
from 地方の万馬券.analysis.quinella_trio.rule_catalog import stage1, stage1_by_ev, stage2, stage3  # noqa: E402
from 地方の万馬券.analysis.quinella_trio.rule_study import RuleStudy  # noqa: E402
from 地方の万馬券.analysis.quinella_trio.ticket_tables_builder import TICKETS, QuinellaTrioSettings, QuinellaTrioTablesBuilder  # noqa: E402
from 地方の万馬券.analysis.quinella_trio.ticket_tables_store import QuinellaTrioTablesStore  # noqa: E402

DEFAULT_OUT = _REPO_ROOT / "reports" / "地方の万馬券"
DEFAULT_PREDICTIONS = _REPO_ROOT / "reports" / "地方競馬の近走と適性から3着以内を予想" / "predictions-2024検証"
TABLES_FOLDER = "馬連と3連複"
REPORT = "馬連と3連複の買い方"
_UPSET_FILES = {"馬連": "荒れ具合-quinella.pkl", "3連複": "荒れ具合-trio.pkl"}


def main(args: argparse.Namespace) -> None:
    suffix = "-票なし" if args.pool_free else ""
    store = QuinellaTrioTablesStore(args.out_dir / (TABLES_FOLDER + suffix))
    if args.build:
        settings = QuinellaTrioSettings(date_from=args.test_from, predictions=args.predictions, min_heads=args.min_heads, pool_free=args.pool_free)
        with db.open_db(args.db, default=db.LOCAL) as con:
            tables = QuinellaTrioTablesBuilder(con, settings).build()
        store.save(tables)
        print(f"組の表を書きました: {store.path(TICKETS[0]).parent}")
    tables = store.load()
    study = RuleStudy(tables, _upsets(args.out_dir))
    rules = _rules(args)
    results = study.evaluate(rules)
    name = f"{REPORT}-段{args.stage}{suffix}" if args.stage == 1 else f"{REPORT}-段{args.stage}{suffix}-{_parse_base(args.base).ticket}"
    study.write(args.out_dir, name, f"地方の万馬券: {name}", _intro(args), results)
    passed = [result for result in results if result.passed]
    print(f"書きました: {args.out_dir / (name + '.md')}（候補 {len(results)} 件、採用候補 {len(passed)} 件）")
    for result in passed:
        print("  採用候補:", result.rule.ticket, result.rule.label)


def _rules(args: argparse.Namespace) -> list[QuinellaTrioRule]:
    if args.stage == 1:
        return [rule for ticket in TICKETS for rule in (*stage1(ticket), *stage1_by_ev(ticket))]
    base = _parse_base(args.base)
    return stage2(base) if args.stage == 2 else stage3(base)


def _parse_base(text: str | None) -> QuinellaTrioRule:
    """``券種|期待値|オッズ下限|オッズ上限|頭数|上限の点数[|P か ev][|型]``。"""
    if not text:
        raise ValueError("段2・段3 は --base で段1 の買い方を渡してください（例 3連複|1.0|20|300|8|3）")
    parts = text.split("|")
    if len(parts) < 6:
        raise ValueError(f"--base の形が違います: {text}")
    order = {"P": PROBABILITY, "ev": EV}.get(parts[6], PROBABILITY) if len(parts) > 6 else PROBABILITY
    form = parts[7] if len(parts) > 7 else ""
    return QuinellaTrioRule(parts[0], float(parts[1]), float(parts[2]), float(parts[3]), int(parts[4]), int(parts[5]), order, form)


def _upsets(out_dir: Path) -> dict[str, pd.DataFrame]:
    found = {}
    for ticket, file_name in _UPSET_FILES.items():
        path = out_dir / "predictions" / file_name
        if path.is_file():
            found[ticket] = pd.read_pickle(path)
    return found


def _intro(args: argparse.Namespace) -> str:
    stage_text = {1: "段1: オッズの帯 × 期待値の線 × 頭数 × 点数の上限（確率の順と期待値の順）",
                  2: f"段2: 段1 の買い方（{args.base}）に組の形（◎ を含む・人気の帯の型）を重ねる",
                  3: f"段3: 段1 の買い方（{args.base}）に荒れ具合の条件（段④の予測）を重ねる"}[args.stage]
    return f"{stage_text}。対象は 2024-01-01 以降の地方の確定レース（5頭以上。頭数の線は買い方で引く）。組の確率は段5 の条件つきロジット。"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--build", action="store_true", help="組の表を作り直す（20〜30分）")
    parser.add_argument("--stage", type=int, choices=(1, 2, 3), default=1, help="評価する段（既定: 1）")
    parser.add_argument("--base", default=None, help="段2・段3 の元にする段1 の買い方（券種|期待値|オッズ下限|オッズ上限|頭数|上限の点数[|P か ev][|型]）")
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../nvdata-store/nvdata.duckdb か環境変数 YOSOU_LOCAL_DB）")
    parser.add_argument("--test-from", type=date.fromisoformat, default=date(2024, 1, 1), help="対象の最初の開催日（既定: 2024-01-01）")
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS, help="全頭の予想の当日の予測の表の置き場所")
    parser.add_argument("--min-heads", type=int, default=5, help="表に入れる最少の頭数（既定: 5。頭数の線は買い方で引く）")
    parser.add_argument("--pool-free", action="store_true", help="段4: 票の見立て（単勝の支持率・各券種の票・複勝オッズ）を使わず、全頭の予想の確率だけで組の確率を作る（表は 馬連と3連複-票なし に別に置く）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help=f"書く場所（既定: {DEFAULT_OUT}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
