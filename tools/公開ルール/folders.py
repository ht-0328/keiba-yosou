"""道具「公開ルール」が読み書きする場所（定数だけ）。"""

from __future__ import annotations

from pathlib import Path

from 今週の予想.model_folders import DEFAULT_PUBLIC_RULE_MODELS

#: keiba-yosou のリポジトリ直下（tools/公開ルール/ から2つ上）。
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
#: 公開ルールの出力の置き場。
OUT_FOLDER = _PROJECT_ROOT / "reports" / "公開ルール"
#: 確率を直すモデル（``WinCorrectionModel``）の既定の置き場所。今週の予想の当日の予想がここを読む。
DEFAULT_MODELS = DEFAULT_PUBLIC_RULE_MODELS
#: 学習に使う既定の予測（今の本番の当日の予想と同じ作りの、学習に使っていない期間の予測。研究「既存モデルの改善」の
#: predictions/<予想>/<作り方>.pkl）。1着の予想と全頭（3着以内）の予想。
DEFAULT_WIN = "graded_race_day/odds_move-win"
DEFAULT_TOP3 = "graded_race_day/odds_move-top3"
