"""地方の万馬券: 1着・2着・3着を分けて市場に合わせる全券種の買い方（研究「地方の万馬券」の入口。段5）。

    uv run python research/地方の万馬券/positions.py                       # 2024〜2026年を、各年を残りの年で当てはめて評価（15〜25分）
    uv run python research/地方の万馬券/positions.py --protocol 前の年       # 前の年だけで当てはめる（2024→2025、2024+2025→2026）
    uv run python research/地方の万馬券/positions.py --trifecta-only --report-name 全券種の買い方-3連単の票だけ   # 馬単・3連複・複勝の票を足さない

全頭の予想（2023年前半までで学んだ当日の予測）の 1着・3着以内の確率（LightGBM と CatBoost を分ける）と、単勝・3連単・馬単・3連複・複勝の
確定オッズの見立てを材料に、1着・2着・3着の条件つきロジット（レース内の softmax）を当てはめ、3連単の全部の組の確率 P(a) P(b|a) P(c|a,b) を出す。
その確率を足し合わせて単勝・複勝・枠連・馬連・ワイド・馬単・3連複の組の確率にし、券種ごとの確定オッズで期待値を付けて、
オッズの帯と期待値の線で買う（``analysis/positions/ticket_plan.py`` の買い方）。
出るもの（Git 対象外）: ``reports/地方の万馬券/全券種の買い方.md``・``全券種の買い方の買い目.csv``。
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
from 地方の万馬券.analysis.positions.positions_study import LEAVE_ONE_OUT, PROTOCOLS, PositionsStudy, PositionsStudySettings  # noqa: E402

DEFAULT_OUT = _REPO_ROOT / "reports" / "地方の万馬券"
DEFAULT_PREDICTIONS = _REPO_ROOT / "reports" / "地方競馬の近走と適性から3着以内を予想" / "predictions-2024検証"


def main(args: argparse.Namespace) -> None:
    settings = PositionsStudySettings(test_from=args.test_from, predictions=args.predictions, protocol=args.protocol, min_heads=args.min_heads,
                                      trifecta_only=args.trifecta_only, report_name=args.report_name)
    with db.open_db(args.db, default=db.LOCAL) as con:
        path = PositionsStudy(con, settings).run(args.out_dir)
    print(f"書きました: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../nvdata-store/nvdata.duckdb か環境変数 YOSOU_LOCAL_DB）")
    parser.add_argument("--test-from", type=date.fromisoformat, default=date(2024, 1, 1), help="対象の最初の開催日（既定: 2024-01-01）")
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS, help="全頭の予想の当日の予測の表の置き場所（対象の期間を全部含むもの）")
    parser.add_argument("--protocol", choices=PROTOCOLS, default=LEAVE_ONE_OUT, help="当てはめ方（既定: 入れ替え。各年を残りの年で当てはめる）")
    parser.add_argument("--min-heads", type=int, default=11, help="対象にする最少の頭数（既定: 11）")
    parser.add_argument("--trifecta-only", action="store_true", help="馬単・3連複・複勝の票を材料に足さない（3連単の票だけ）")
    parser.add_argument("--report-name", default="全券種の買い方", help="書く Markdown と CSV の名前（既定: 全券種の買い方）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help=f"書く場所（既定: {DEFAULT_OUT}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
