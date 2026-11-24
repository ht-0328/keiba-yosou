"""この予想の出力の置き場所（``reports/<予想の名前>/`` の下のフォルダ）。"""

from __future__ import annotations

from pathlib import Path

#: keiba-yosou のリポジトリ直下（src/yosou/high_payout_combos/repository/ から4つ上）。
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
#: ``reports/<予想の名前>/`` の下のフォルダの名前。馬ごとの表・組の表・年ごとの予測。
HORSES_FOLDER = "horses"
TABLES_FOLDER = "tables"
PREDICTIONS_FOLDER = "predictions"


def report_folder(yosou_name: str, folder_name: str) -> Path:
    """既定の置き場所。JV-Data から作ったもので公開しないので、Git の対象外（``reports/``）に置く。

    例: ``report_folder("高配当の組が当たるかを予想", TABLES_FOLDER)`` → ``reports/高配当の組が当たるかを予想/tables``。
    """
    return _PROJECT_ROOT / "reports" / yosou_name / folder_name
