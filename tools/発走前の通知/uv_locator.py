"""uv の場所と、別のプロジェクトの uv を呼ぶ子プロセスの環境。"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

#: WinGet が uv を入れる場所（%LOCALAPPDATA% から下）。jvdata-store の realtime_today.bat と同じ。
_WINGET_UV = Path("Microsoft") / "WinGet" / "Packages" / "astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe" / "uv.exe"


def uv_command() -> str:
    """uv の場所。PATH に無ければ WinGet が入れる場所を探す。"""
    found = shutil.which("uv")
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA")
    candidate = Path(local) / _WINGET_UV if local else None
    if candidate is not None and candidate.exists():
        return str(candidate)
    raise FileNotFoundError("uv が見つかりません。uv を入れるか PATH に通してください")


def child_env() -> dict[str, str]:
    """子プロセスの環境。別のプロジェクトの uv を呼ぶので VIRTUAL_ENV は渡さない。文字コードは UTF-8。"""
    env = {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}
    env["PYTHONIOENCODING"] = "utf-8"
    return env
