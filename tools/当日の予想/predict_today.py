"""当日の予想: 発走前のレースを custom_binary のモデルで予想し、複勝の期待値が高い馬を「買い」として出す。

    uv run python tools/当日の予想/predict_today.py                       # 今日の、今より後に発走するレース
    uv run python tools/当日の予想/predict_today.py --after 00:00         # 今日の全レース（終わったレースも）
    uv run python tools/当日の予想/predict_today.py --date 2026-09-27     # 別の開催日
    uv run python tools/当日の予想/predict_today.py --line 1.3            # 買いにする期待値の線を変える

先に jvdata-store の realtime_today.bat（jvstore realtime）で、その日の速報（馬体重・全券種のオッズ）を取り込んでおく。
モデルは settings/ の2つ（馬体重あり・馬体重なし）。馬体重が発表済みのレースは「馬体重あり」、まだなら「馬体重なし」で予想する。
モデルが保存されていなければ、はじめに学習する（1つ数分）。結果は reports/当日の予想/ にも書く。
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[0]), str(HERE)]

from 共通 import cli, render  # noqa: E402

from yosou.custom_binary import workflow  # noqa: E402
from yosou.custom_binary.feature.registrations import default_registry  # noqa: E402

from same_day_predictor import SameDayModel, SameDayPredictor  # noqa: E402

#: 並べた順に試す。前のモデルで予想できない（馬体重が未発表など）ときは次を使う。
MODELS = [
    SameDayModel("馬体重あり", HERE / "settings" / "馬体重あり.yml"),
    SameDayModel("馬体重なし", HERE / "settings" / "馬体重なし.yml"),
]
#: 買いにする期待値の線（研究「特徴量の組み合わせ探索」で、確かめる期間の結果から選んだ値）。
DEFAULT_LINE = 1.2


def main(args) -> None:
    day = args.date or date.today().isoformat()
    after = args.after or datetime.now().strftime("%H:%M")
    predictor = SameDayPredictor(MODELS, default_registry(), args.db, args.line)
    predictor.ensure_models()
    tables = predictor.run(day, after)
    cli.emit(tables, args)
    saved = workflow.PROJECT_ROOT / "reports" / "当日の予想" / f"{day}_{after.replace(':', '')}.md"
    saved.parent.mkdir(parents=True, exist_ok=True)
    render.write(render.render(tables, "markdown"), saved, fmt="markdown")
    print(f"\n保存先: {saved}")


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--date", help="開催日 YYYY-MM-DD（省略すると今日）")
    parser.add_argument("--after", help="この時刻 HH:MM 以降に発走するレースだけ（省略すると今の時刻）")
    parser.add_argument("--line", type=float, default=DEFAULT_LINE, help=f"買いにする期待値の線（既定: {DEFAULT_LINE}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
