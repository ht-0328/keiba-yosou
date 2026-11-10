"""地方の期待度: 地方の発走前の通知に添える「期待度」（◎ の当たりやすさと買って得かを1つにした S・A・B・C）の点数の式と線を、未見の予測で決める。

    uv run python research/地方の期待度/expectation.py                      # 当日の時点。2024年で線を決め、2025・2026年で確かめる
    uv run python research/地方の期待度/expectation.py --timing 前日          # 前日の時点
    uv run python research/地方の期待度/expectation.py --rebuild             # ◎ の行を元DB から作り直す（十数分）

◎ の行は地方の予想モデルの backtest の予測（既定 reports/地方競馬の近走と適性から3着以内を予想/predictions-2024検証。2023年前半までで学んだモデルの
2024年以降の未見の予測）に、印の成績と同じ決め方で印を付けて作り、reports/地方の期待度/cache/ にとっておく。
出るものは Git 対象外の reports/地方の期待度/期待度の候補-<時点>.md（候補ごとの年 × 等級の ◎ の単勝・複勝の成績と推奨買目の成績、まとめ）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from yosou.shared.feature import PredictionTiming  # noqa: E402

from 地方の期待度.analysis.expectation_study import ExpectationStudy, ExpectationStudySettings  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PREDICTIONS_ROOT = ROOT / "reports" / "地方競馬の近走と適性から3着以内を予想"
DEFAULT_PREDICTIONS = "predictions-2024検証"
OUT = ROOT / "reports" / "地方の期待度"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--predictions", default=DEFAULT_PREDICTIONS,
                        help=f"backtest の予測の置き場所の名前（reports/地方競馬の近走と適性から3着以内を予想/ の下。既定: {DEFAULT_PREDICTIONS}）")
    parser.add_argument("--timing", type=PredictionTiming.parse, default=PredictionTiming.RACE_DAY, help="時点: 前日・当日（既定: 当日）")
    parser.add_argument("--decide-year", type=int, default=2024, help="線を決める年（既定: 2024。ほかの年で確かめる）")
    parser.add_argument("--db", type=Path, default=None, help="地方の元DB のパス（省略すると nvdata-store の既定）")
    parser.add_argument("--rebuild", action="store_true", help="◎ の行を元DB から作り直す")
    parser.add_argument("--out-dir", type=Path, default=OUT, help=f"結果を書く場所（既定: {OUT}）")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.timing is PredictionTiming.THURSDAY:
        raise SystemExit("出馬表の時点にはオッズ（期待値）が無いので、期待度は出せません")
    settings = ExpectationStudySettings(PREDICTIONS_ROOT / args.predictions, PREDICTIONS_ROOT / "models", args.timing, args.decide_year,
                                        args.out_dir, args.db, args.rebuild)
    ExpectationStudy(settings).run()


if __name__ == "__main__":
    main()
