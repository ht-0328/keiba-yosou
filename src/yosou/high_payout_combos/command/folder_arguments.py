"""出力の置き場所の引数（``--horses``・``--tables``・``--predictions``）。"""

from __future__ import annotations

import argparse
from pathlib import Path

from ..repository import HORSES_FOLDER, PREDICTIONS_FOLDER, TABLES_FOLDER, report_folder
from .yosou_name import YOSOU_NAME

#: 引数の名前 → （``reports/<予想の名前>/`` の下のフォルダの名前、説明）。
_FOLDERS: dict[str, tuple[str, str]] = {
    "horses": (HORSES_FOLDER, "馬ごとの表（1頭1行。*.parquet）の置き場所"),
    "tables": (TABLES_FOLDER, "組の表（<券種の英名>_<年>.parquet）の置き場所"),
    "predictions": (PREDICTIONS_FOLDER, "年ごとの予測（<券種の英名>_<年>.parquet）の置き場所"),
}


def add_folder_argument(parser: argparse.ArgumentParser, name: str) -> None:
    """``--horses``・``--tables``・``--predictions`` のどれかを足す。既定は ``reports/<予想の名前>/<フォルダ>``。"""
    folder_name, description = _FOLDERS[name]
    parser.add_argument(
        f"--{name}", type=Path, default=report_folder(YOSOU_NAME, folder_name),
        help=f"{description}（既定: reports/{YOSOU_NAME}/{folder_name}）",
    )
