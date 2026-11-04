"""地方の万馬券: 3連単の買い方を確かめる（研究「地方の万馬券」の入口。段3・段4）。

    uv run python research/地方の万馬券/trifecta.py          # テスト期間（2026-01〜10-04）と未見期間（10-05〜）で、買い方ごとの 3連単・3連複の成績
    uv run python research/地方の万馬券/trifecta.py --test-from 2024-01-01 --unseen-from 2026-01-01 --predictions reports/地方競馬の近走と適性から3着以内を予想/predictions-2024検証 --unseen-predictions reports/地方競馬の近走と適性から3着以内を予想/predictions-2024検証 --report-name 3連単の買い方-2024検証
                                                            # 2023年前半までで学んだモデルで、2024〜2025年（テスト）と 2026年（未見）

全頭の予想（地方競馬の近走と適性から3着以内を予想）の当日の予測の表（backtest が書いた pkl）を読み、
1着の確率から Harville の式で 3連単の全部の組の確率を出し、市場の割れ方で決めた荒れ具合 → 型 → 消を外した人気馬と差の高い穴馬 →
組の期待値（確率 × 確定オッズ）で買い目を組んで、確定払戻で成績を出す。買い方の一覧は ``analysis/trifecta/strategy_catalog.py``。
出るもの（Git 対象外）: ``reports/地方の万馬券/3連単の買い方.md``・``3連単の買い目.csv``。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
_REPO_ROOT = _RESEARCH.parent
sys.path[:0] = [str(_RESEARCH), str(_REPO_ROOT / "tools")]

from 共通 import cli, db  # noqa: E402
from 地方の万馬券.analysis.trifecta.trifecta_study import TrifectaStudy, TrifectaStudySettings  # noqa: E402

DEFAULT_OUT = _REPO_ROOT / "reports" / "地方の万馬券"
_YOSOU = _REPO_ROOT / "reports" / "地方競馬の近走と適性から3着以内を予想"
DEFAULT_TEST_PREDICTIONS = _YOSOU / "predictions"
DEFAULT_UNSEEN_PREDICTIONS = _YOSOU / "predictions-未見-20261005"


def main(args: argparse.Namespace) -> None:
    settings = TrifectaStudySettings(test_from=args.test_from, unseen_from=args.unseen_from,
                                     test_predictions=args.predictions, unseen_predictions=args.unseen_predictions,
                                     report_name=args.report_name, stage_predictions=args.stage_predictions).only(tuple(args.only))
    with db.open_db(args.db, default=db.LOCAL) as con:
        path = TrifectaStudy(con, settings).run(args.out_dir)
    print(f"書きました: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../nvdata-store/nvdata.duckdb か環境変数 YOSOU_LOCAL_DB）")
    parser.add_argument("--test-from", type=date.fromisoformat, default=date(2026, 1, 1), help="テスト期間の最初の開催日（既定: 2026-01-01）")
    parser.add_argument("--unseen-from", type=date.fromisoformat, default=date(2026, 10, 5), help="未見期間の最初の開催日（既定: 2026-10-05）")
    parser.add_argument("--predictions", type=Path, default=DEFAULT_TEST_PREDICTIONS, help="テスト期間の予測の表の置き場所")
    parser.add_argument("--unseen-predictions", type=Path, default=DEFAULT_UNSEEN_PREDICTIONS,
                        help="未見期間の予測の表の置き場所（--predictions の表が未見期間も含むなら同じ場所でよい）")
    parser.add_argument("--report-name", default="3連単の買い方", help="書く Markdown と CSV の名前（既定: 3連単の買い方）")
    parser.add_argument("--only", nargs="*", default=(), help="比べる買い方を名前の先頭の記号で絞る（例: L T2 S1。M* のように * で終わる記号は前方一致。省略すると全部）")
    parser.add_argument("--stage-predictions", type=Path, default=None,
                        help="段ごとの予想（②危険な人気馬・③穴馬・④荒れ具合）の予測の表の置き場所（stages.py が書く reports/地方の万馬券/predictions）。"
                             "渡すと、M・TM の買い方がそれで消・穴・レース・型を決める")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help=f"書く場所（既定: {DEFAULT_OUT}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
