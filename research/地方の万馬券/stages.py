"""地方の万馬券: 予想方法の段ごとの精度（研究「地方の万馬券」の入口。計画の 6.）。

    uv run python research/地方の万馬券/stages.py                      # ④荒れ具合・②危険な人気馬・③穴馬 の3つを順に（初回は学習データ作りに 30〜60分）
    uv run python research/地方の万馬券/stages.py --stage 危険な人気馬 穴馬   # ②③だけ

全頭の予想①の学習データ（当日の馬場傾向 U つき）を1回作ってとっておき、②は 1〜3番人気の行で「4着以下」、③は 4番人気以下の行で「3着以内」を
①と同じ材料から学ぶ。④は 1行 = 1レースの学習データで、券種ごとの4段階（固い・中荒れ・大荒れ・超荒れ）の確率を学ぶ。
どれも 2023年前半までで学び（学習 2019-01-01〜、検証 2023-07-01〜）、2024〜2026年を予測して、年ごとの精度を出す。
出るもの（Git 対象外）: ``reports/地方の万馬券/荒れ具合の精度.md``・``危険な人気馬の精度.md``・``穴馬の精度.md``、
``reports/地方の万馬券/predictions/`` の予測の表（段3 の買い目に渡す）。
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
from 地方の万馬券.analysis.stages.band_study import DANGER, LONGSHOT, BandStudy, BandStudySettings  # noqa: E402
from 地方の万馬券.analysis.stages.upset_study import UPSET, UpsetStudy, UpsetStudySettings  # noqa: E402

from yosou.shared.dataset import TrainingPeriod  # noqa: E402

DEFAULT_OUT = _REPO_ROOT / "reports" / "地方の万馬券"
DEFAULT_FORM_PREDICTIONS = _REPO_ROOT / "reports" / "地方競馬の近走と適性から3着以内を予想" / "predictions-2024検証" / "race_day.pkl"
STAGES: tuple[str, ...] = (UPSET, DANGER, LONGSHOT)


def main(args: argparse.Namespace) -> None:
    period = TrainingPeriod(args.warmup_from, args.train_from, args.valid_from, args.test_from)
    for stage in args.stage:
        if stage == UPSET:
            settings = UpsetStudySettings(period, lambda: db.open_db(args.db, default=db.LOCAL), args.cache_dir, args.models_dir)
            path = UpsetStudy(settings).run(args.out_dir)
        else:
            settings = BandStudySettings(stage, period, args.db, args.form_predictions, args.cache_dir, args.models_dir)
            path = BandStudy(settings).run(args.out_dir)
        print(f"書きました: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--stage", nargs="+", choices=STAGES, default=list(STAGES), help=f"確かめる段（既定: {' '.join(STAGES)} の順に全部）")
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../nvdata-store/nvdata.duckdb か環境変数 YOSOU_LOCAL_DB）")
    parser.add_argument("--warmup-from", type=date.fromisoformat, default=date(2016, 1, 1), help="ウォームアップの最初の開催日（既定: 2016-01-01）")
    parser.add_argument("--train-from", type=date.fromisoformat, default=date(2019, 1, 1), help="学習データの最初の開催日（既定: 2019-01-01）")
    parser.add_argument("--valid-from", type=date.fromisoformat, default=date(2023, 7, 1), help="検証データの最初の開催日（既定: 2023-07-01）")
    parser.add_argument("--test-from", type=date.fromisoformat, default=date(2024, 1, 1), help="テスト期間の最初の開催日（既定: 2024-01-01）")
    parser.add_argument("--form-predictions", type=Path, default=DEFAULT_FORM_PREDICTIONS,
                        help="全頭の予想①の当日の予測の pkl（決め方「①の差」に使う。既定: predictions-2024検証/race_day.pkl）")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_OUT / "cache", help=f"学習データの pickle の置き場所（既定: {DEFAULT_OUT / 'cache'}）")
    parser.add_argument("--models-dir", type=Path, default=DEFAULT_OUT / "models", help=f"学んだモデルの置き場所（既定: {DEFAULT_OUT / 'models'}）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help=f"書く場所（既定: {DEFAULT_OUT}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
