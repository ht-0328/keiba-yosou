"""1つの時点で、今の予想と移した作り方を、区切りごとのログ損失で比べて採否を決める。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 突き合わせる鍵。
_KEY = ["レースID", "馬ID"]
#: 確率をログにするときの端の丸め。
_EDGE = 1e-6
#: 採用の基準: 7つの区切りのうち、移した作り方のログ損失が小さい区切りの数の下限（研究「既存モデルの改善」と同じ）。
MIN_BETTER_WINDOWS = 5


class PortComparison:
    """今の予想（``current``）と移した作り方（``ported``）のテスト期間の予測を、両方にある行だけで比べる。

    採用の基準は研究「既存モデルの改善」の材料の実験と同じ: テスト期間のログ損失が今の予想より小さい区切りが
    7つのうち 5つ以上あり、全期間を合わせても小さいこと。ログ損失の差は小さいので 1000倍して出す。
    """

    def common(self, current: pd.DataFrame, ported: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """両方にある行だけにした2つの表（並びは同じ）。"""
        keys = current[_KEY].merge(ported[_KEY], on=_KEY)
        return (keys.merge(current, on=_KEY, how="left"), keys.merge(ported, on=_KEY, how="left"))

    def by_window(self, current: pd.DataFrame, ported: pd.DataFrame) -> pd.DataFrame:
        """区切りごとの行数・ログ損失・差（×1000）・移した作り方のほうが小さいか。最後の行は全期間。"""
        windows = list(dict.fromkeys(current["区切り"]))
        rows = [self._row(window, current[current["区切り"] == window], ported[ported["区切り"] == window])
                for window in windows]
        rows.append(self._row("全期間", current, ported))
        return pd.DataFrame(rows)

    def adopted(self, table: pd.DataFrame) -> bool:
        """採用の基準を満たすか（``by_window`` の表から）。"""
        windows = table[table["区切り"] != "全期間"]
        overall = table[table["区切り"] == "全期間"].iloc[0]
        return int(windows["小さい"].sum()) >= MIN_BETTER_WINDOWS and bool(overall["小さい"])

    def _row(self, window: str, current: pd.DataFrame, ported: pd.DataFrame) -> dict[str, object]:
        now, new = self._log_loss(current), self._log_loss(ported)
        return {"区切り": window, "行数": len(current), "今の予想のログ損失": round(now, 5),
                "移した作り方のログ損失": round(new, 5), "差（×1000）": round((new - now) * 1000, 3), "小さい": new < now}

    def _log_loss(self, frame: pd.DataFrame) -> float:
        probability = frame["score"].clip(_EDGE, 1 - _EDGE).to_numpy(dtype=float)
        label = frame["3着以内"].to_numpy(dtype=float)
        return float(-np.mean(label * np.log(probability) + (1 - label) * np.log(1 - probability)))
