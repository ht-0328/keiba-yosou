"""表（DataFrame）を Markdown の表の文字列にする（研究の報告用。小数は丸める）。"""

from __future__ import annotations

import numpy as np
import pandas as pd


def markdown_table(frame: pd.DataFrame, digits: int = 3) -> str:
    """列名の行・区切りの行・値の行。小数は ``digits`` 桁、整数はそのまま、欠損値は「—」。"""
    columns = [str(column) for column in frame.columns]
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join(" :--- " for _ in columns) + "|"]
    for row in frame.itertuples(index=False):
        lines.append("| " + " | ".join(_cell(value, digits) for value in row) + " |")
    return "\n".join(lines)


def _cell(value: object, digits: int) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "—"
    if isinstance(value, (bool, np.bool_)):
        return "はい" if value else "いいえ"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.{digits}f}"
    return str(value).replace("|", "｜")
