"""地方の期待度を推奨買目の見込みで付け直せるかを確かめる（研究「地方の期待度」の入口）。

    uv run python research/地方の期待度/grade.py --build                      # 過去のレースの推奨買目を本番と同じ決まりで作り直す（元DB を読む。20〜30分）
    uv run python research/地方の期待度/grade.py                              # レースの見込みで等級を付け、等級ごとの成績を年ごとに書く（数十秒）
    uv run python research/地方の期待度/grade.py --build --protocol 前の年    # 前の年だけで当てはめた推奨買目（2025・2026年）
    uv run python research/地方の期待度/grade.py --protocol 前の年
    uv run python research/地方の期待度/grade.py --build --protocol 本番 --test-from 2026-01-01   # 本番の予想モデルの予測と本番の係数で（本番の予測は 2026年だけ）

出るもの（Git 対象外）: reports/地方の期待度/推奨買目[-前の年].pkl・レース[-前の年].pkl・推奨買目の見込みの期待度[-前の年].md。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
_REPO_ROOT = _RESEARCH.parent
sys.path[:0] = [str(_RESEARCH), str(_REPO_ROOT / "tools")]

import pandas as pd  # noqa: E402

from 共通 import cli, db  # noqa: E402
from 地方の期待度.analysis.grade_study import GradeStudy  # noqa: E402
from 地方の推奨買目.coefficient_store import CoefficientStore  # noqa: E402
from 地方の期待度.analysis.recommended_bets_builder import LEAVE_ONE_OUT, PRODUCTION, PROTOCOLS, RecommendedBetsBuilder, RecommendedBetsSettings  # noqa: E402

DEFAULT_OUT = _REPO_ROOT / "reports" / "地方の期待度"
_PREDICTIONS = _REPO_ROOT / "reports" / "地方競馬の近走と適性から3着以内を予想" / "predictions-2024検証"
#: 本番の予想モデルの予測（テスト期間の 2026年だけ）。当てはめ方が「本番」のときに使う。
_PRODUCTION_PREDICTIONS = _REPO_ROOT / "reports" / "地方競馬の近走と適性から3着以内を予想" / "predictions"
_TRIO_UPSETS = _REPO_ROOT / "reports" / "地方の万馬券" / "predictions" / "荒れ具合-trio.pkl"
#: ◎ の行（``expectation.py`` が作る。今の期待度と比べるのに使う）。
_TOPS = DEFAULT_OUT / "cache" / "◎-predictions-2024検証-race_day.pkl"


def main(args: argparse.Namespace) -> None:
    suffix = "" if args.protocol == LEAVE_ONE_OUT else f"-{args.protocol}"
    bets_path, races_path = args.out_dir / f"推奨買目{suffix}.pkl", args.out_dir / f"レース{suffix}.pkl"
    if args.build:
        production = args.protocol == PRODUCTION
        settings = RecommendedBetsSettings(date_from=args.test_from, predictions=_PRODUCTION_PREDICTIONS if production else _PREDICTIONS,
                                           trio_upsets=_TRIO_UPSETS, protocol=args.protocol,
                                           coefficients=CoefficientStore().load() if production else None)
        with db.open_db(args.db, default=db.LOCAL) as con:
            bets, races = RecommendedBetsBuilder(con, settings).build()
        args.out_dir.mkdir(parents=True, exist_ok=True)
        bets.to_pickle(bets_path)
        races.to_pickle(races_path)
        print(f"書きました: {bets_path}")
    path = GradeStudy(pd.read_pickle(bets_path), pd.read_pickle(races_path), pd.read_pickle(_TOPS), args.protocol).write(args.out_dir)
    print(f"書きました: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--build", action="store_true", help="過去のレースの推奨買目を作り直す（元DB を読む）")
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: 地方の元DB か環境変数 YOSOU_LOCAL_DB。写しを渡せる）")
    parser.add_argument("--test-from", type=date.fromisoformat, default=date(2024, 1, 1), help="対象の最初の開催日（既定: 2024-01-01）")
    parser.add_argument("--protocol", choices=PROTOCOLS, default=LEAVE_ONE_OUT, help="当てはめ方（既定: 入れ替え）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help=f"書く場所（既定: {DEFAULT_OUT}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
