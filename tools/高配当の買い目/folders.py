"""道具「高配当の買い目」が読み書きする場所（定数だけ）。"""

from __future__ import annotations

from pathlib import Path

from 今週の予想.model_folders import HIGH_PAYOUT_YOSOU_NAME

#: keiba-yosou のリポジトリ直下（tools/高配当の買い目/ から2つ上）。
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
#: 予想「高配当の組が当たるかを予想」の出力の置き場。
YOSOU_FOLDER = _PROJECT_ROOT / "reports" / HIGH_PAYOUT_YOSOU_NAME
#: 馬ごとの表の既定の置き場所（予想のパッケージがこのフォルダの parquet を全部読んでつなぐ）。
DEFAULT_HORSES_FOLDER = YOSOU_FOLDER / "horses"
#: 年ごとの予測（予想のパッケージの walk の出力）の既定の置き場所。
DEFAULT_PREDICTIONS_FOLDER = YOSOU_FOLDER / "predictions"
#: 成績の表を書く既定の場所。
DEFAULT_OUT_DIR = _PROJECT_ROOT / "reports" / "高配当の買い目"
#: 成績の表のファイル名。
STATS_FILE = "成績.md"
