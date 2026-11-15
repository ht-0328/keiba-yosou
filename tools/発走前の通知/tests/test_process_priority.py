"""通知のプロセスの優先度を「通常」に上げる部品（``ProcessPriority``）のテスト。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from 発走前の通知.process_priority import NORMAL_PRIORITY_CLASS, ProcessPriority

#: 優先度「通常以下」で始めたプロセスの中で「通常」に上げ、子のプロセスを始めて、子の優先度を表示するスクリプト。
_PARENT = """\
import subprocess, sys
from 発走前の通知.process_priority import ProcessPriority
assert ProcessPriority().raise_to_normal()
print(subprocess.run([sys.executable, sys.argv[1]], capture_output=True, text=True, check=True).stdout.strip())
"""
#: 自分の優先度を表示するスクリプト。
_CHILD = """\
import ctypes
from ctypes import wintypes
kernel32 = ctypes.WinDLL("kernel32")
kernel32.GetCurrentProcess.restype = wintypes.HANDLE
kernel32.GetPriorityClass.argtypes = (wintypes.HANDLE,)
print(kernel32.GetPriorityClass(kernel32.GetCurrentProcess()))
"""
#: Windows の「通常以下」（タスクスケジューラのタスクの既定）。
_BELOW_NORMAL_PRIORITY_CLASS = 0x00004000


def test_上げられたら_True() -> None:
    assert ProcessPriority(lambda: True).raise_to_normal() is True


def test_上げられなくても例外を出さずに_False() -> None:
    def fail() -> bool:
        raise OSError("権限がない")

    assert ProcessPriority(fail).raise_to_normal() is False


@pytest.mark.skipif(sys.platform != "win32", reason="Windows の優先度を確かめる")
def test_Windows_では通常以下で始めても_上げたあとに始めたプロセスは通常になる(tmp_path: Path) -> None:
    parent, child = tmp_path / "parent.py", tmp_path / "child.py"
    parent.write_bytes(_PARENT.encode("utf-8"))
    child.write_bytes(_CHILD.encode("utf-8"))
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2]), "PYTHONUTF8": "1"}   # tools/ を読めるようにする
    result = subprocess.run([sys.executable, str(parent), str(child)], capture_output=True, text=True, check=True, env=env,
                            creationflags=_BELOW_NORMAL_PRIORITY_CLASS)   # タスクスケジューラと同じ「通常以下」で始める
    assert int(result.stdout.strip()) == NORMAL_PRIORITY_CLASS
