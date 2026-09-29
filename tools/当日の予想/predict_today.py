"""当日の予想: 発走前のレースを custom_binary のモデルで予想し、複勝の期待値が高い馬を「買い」として出す。

    uv run python tools/当日の予想/predict_today.py                       # 今日の、今より後に発走するレース
    uv run python tools/当日の予想/predict_today.py --after 00:00         # 今日の全レース（終わったレースも）
    uv run python tools/当日の予想/predict_today.py --date 2026-09-27     # 別の開催日
    uv run python tools/当日の予想/predict_today.py --line 1.3            # 印を付ける期待値の線を、どのモデルもこの値にして試す

先に jvdata-store の realtime_today.bat（jvstore realtime）で、その日の速報（馬体重・全券種のオッズ）を取り込んでおく。
モデルは settings/ の2つ（馬体重あり・馬体重なし）。馬体重が発表済みのレースは「馬体重あり」、まだなら「馬体重なし」で予想する。
「買い」を出すのは馬体重ありだけ。馬体重なしは、学習に使っていない期間で回収率の下限が 100% に届かなかったので、
期待値が線以上の馬に「参考」の印を付けるだけで、買いの一覧には入れない（確かめ方は line_check.py）。
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

#: 「馬体重あり」の買いの線（研究「特徴量の組み合わせ探索」で、確かめる期間の結果から選んだ値）。
#: フォワードテスト（tools/フォワードテスト/）が同じ線で記録しているので、結果の意味が途中で変わらないよう変えない。
DEFAULT_LINE = 1.2
#: 並べた順に試す。前のモデルで予想できない（馬体重が未発表など）ときは次を使う。
#: 線と買うかどうかは、line_check.py で、学習に使っていない期間を「線を選ぶ期間」と「確かめる期間」に分けて確かめる
#: （結果は reports/当日の予想/線の確かめ.md）。
MODELS = [
    SameDayModel("馬体重あり", HERE / "settings" / "馬体重あり.yml", line=DEFAULT_LINE, buys=True),
    # 馬体重なしは、線を 1.2 から上げても、選ぶ期間・確かめる期間のどちらでも回収率の下限が 100% に届かなかったので買わない。
    # 期待値が 1.2 以上の馬には「参考」の印だけを付ける。
    SameDayModel("馬体重なし", HERE / "settings" / "馬体重なし.yml", line=DEFAULT_LINE, buys=False),
]


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
    parser.add_argument("--line", type=float, default=None,
                        help="印を付ける期待値の線。指定すると、どのモデルの線もこの値にする（既定: モデルごとの線）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
