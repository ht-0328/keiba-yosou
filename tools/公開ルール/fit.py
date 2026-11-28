"""公開ルール（学習）: 今の1着の確率を直すモデル（``yosou.shared.win_correction``）を学んで保存する。今週の予想の当日の予想が、公開ルールの ◎ と期待値に使う。

    uv run python tools/公開ルール/fit.py                            # 予測のある全部の期間で学ぶ（既定の置き場所 reports/公開ルール/models/ に書く）
    uv run python tools/公開ルール/fit.py --to 2025-12-31           # 学ぶ期間の終わりを決める
    uv run python tools/公開ルール/fit.py --out reports/公開ルール/試し  # 書く先を替える

材料は、学習に使っていない期間の予測（研究「既存モデルの改善」の predictions/graded_race_day/odds_move-win.pkl・odds_move-top3.pkl のテスト期間。
今の本番の当日の予想と同じ作り）と、元DB の確定オッズ（単勝・複勝・馬連）・単勝の払戻・事実表の列。元DB は読むだけで、事実表を作るので数分かかる。
開催中は --db に元DB の写しを渡す（発走前の通知の予想を止めないため）。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[0])]

from 共通 import db  # noqa: E402

from yosou.shared.repository import RaceDayRange  # noqa: E402
from yosou.shared.win_correction import WinCorrectionFeatures, WinCorrectionModel  # noqa: E402

from 印の成績.prediction_file import PredictionFile  # noqa: E402
from 公開ルール.folders import DEFAULT_MODELS, DEFAULT_TOP3, DEFAULT_WIN  # noqa: E402
from 公開ルール.repository.training_input_reader import TrainingInputReader  # noqa: E402
from 公開ルール.training_table import RACE_DATE, RACE_ID, WON, TrainingTable  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--to", help="学ぶ期間の最後の開催日 YYYY-MM-DD（省略すると予測のある最後の日まで）")
    parser.add_argument("--out", type=Path, default=DEFAULT_MODELS, help="モデルを書く置き場所")
    parser.add_argument("--db", help="元DB の場所（開催中は写しを渡す）")
    args = parser.parse_args()
    win, top3 = PredictionFile(DEFAULT_WIN).load(), PredictionFile(DEFAULT_TOP3).load()
    days = _days(win, args.to)
    with db.open_db(args.db) as con:
        inputs = TrainingInputReader().read(con, days)
    horses = TrainingTable(win, top3, inputs.win_odds, inputs.place_odds, inputs.quinella_odds, inputs.win_payouts, inputs.facts).build()
    horses = horses[horses[RACE_DATE] <= days.last_day.isoformat()]
    model = WinCorrectionModel.fit(WinCorrectionFeatures().frame(horses), horses[WON])
    paths = model.save(args.out)
    print(f"学んだ: {horses[RACE_ID].nunique()} レース・{len(horses)} 頭（{horses[RACE_DATE].min()}〜{horses[RACE_DATE].max()}）")
    print(f"書いた: {args.out}（{len(paths)} 本）")


def _days(win, last: str | None) -> RaceDayRange:
    """予測のテスト期間の範囲（``last`` があればそこまで）。"""
    tested = win[win["period"] == "テスト"]["race_date"].astype(str).str[:10]
    end = date.fromisoformat(last) if last else date.fromisoformat(tested.max())
    return RaceDayRange(date.fromisoformat(tested.min()), end)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
