"""フォワードテスト: 開催日の間ずっと動き、各レースの発走の約10分前に当日の予想で予想して「買ったつもり」で記録する。

    uv run python tools/フォワードテスト/follow.py                    # 今日の開催日を追う
    uv run python tools/フォワードテスト/follow.py --date 2026-10-03  # 別の開催日（発走を過ぎたレースは予想しない）

実際のお金を使う前に、締め切りの約10分前のオッズでも回収率が 100% を超えるかを、約1か月（8開催日ほど）確かめる。
予想は当日の予想（tools/当日の予想/）と同じモデル・同じ線（馬体重ありのモデルで期待値 1.2 以上の複勝を1点100円）。
馬体重なしのモデルは当日の予想で「参考」（買わない）なので、買い目を記録しない。
オッズは jvdata-store の ``jvstore realtime --follow``（realtime_follow.bat）が発走の12分前に取り直したものを使う。
最後のレースの発走から40分たったら、結果が出たものから精算して、reports/フォワードテスト/成績.md を書き直す。
記録は reports/フォワードテスト/買い目.csv と 予想したレース.csv（Git 対象外）。人が書き足すものは無い。
動いた記録（何時にどのレースを予想したか・DB を待ったか）は、画面と同じものを 動作の記録.log にも足す。
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[0]), str(HERE.parents[1] / "src")]

from 共通 import cli, db  # noqa: E402

from yosou.custom_binary.feature.default_registry import DefaultRegistry  # noqa: E402
from yosou.custom_binary.store import PROJECT_ROOT  # noqa: E402

from 当日の予想.predict_today import MODELS, SameDayPredictor  # noqa: E402
from フォワードテスト.forward_follower import ForwardFollower  # noqa: E402
from フォワードテスト.ledger import Ledger  # noqa: E402

LEDGER = PROJECT_ROOT / "reports" / "フォワードテスト"
LOG_FILE = LEDGER / "動作の記録.log"


def main(args) -> None:
    day = args.date or date.today().isoformat()
    predictor = SameDayPredictor(MODELS, DefaultRegistry().build(), args.db, args.line)
    predictor.ensure_models()
    follower = ForwardFollower(predictor, Ledger(LEDGER), lambda: db.open_db(args.db),
                               minutes_before=args.minutes_before, log=_log)
    lines = "・".join(f"{model.label} {predictor.line_of(model.label):g} 以上" for model in MODELS
                      if predictor.buys_with(model.label))
    _log(f"{day} のフォワードテストを始めます（発走の {args.minutes_before} 分前に予想・期待値 {lines}）")
    follower.run(day)
    _log(f"{day} のフォワードテストを終えました")


def _log(message: str) -> None:
    """画面に出し、動作の記録.log にも足す。"""
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {message}"
    print(line, flush=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--date", help="開催日 YYYY-MM-DD（省略すると今日）")
    parser.add_argument("--minutes-before", type=int, default=10, help="発走の何分前に予想するか（既定: 10）")
    parser.add_argument("--line", type=float, default=None,
                        help="買いにする期待値の線。指定すると、どのモデルの線もこの値にする（既定: 当日の予想のモデルごとの線）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
