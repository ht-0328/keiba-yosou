"""登録馬の確かめの結果を表にする。"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss, roc_auc_score

from 共通.render import Table

from yosou.shared.command.cell_format import rounded
from yosou.shared.dataset import RACE_ID
from yosou.shared.dataset.column_names import FINISH

from ..repository import EXCHANGE
from ..workflow import PROBABILITY, WIN_PROBABILITY, RAN, RegistrationCheckResult

#: 確率を 0・1 に張り付かせない幅。
_EPSILON = 1e-6
#: 中央以外の馬（交流区分が空でない）。
_FOREIGN = "外国"
_LOCAL = "地方"


class RegistrationCheckTables:
    """登録馬の確かめの結果（``RegistrationCheckResult``）を、「確かめた登録馬」「出走した登録馬だけでの当たり具合」「予測できなかったレース」
    「書いた表」の表にする（設計書 16 の 7）。出走するかどうかは当てない予想なので、出走しなかった馬の割合は出さない。"""

    def __init__(self, result: RegistrationCheckResult) -> None:
        self._result = result
        self._table = result.table

    def tables(self) -> list[Table]:
        tables = [self._registrations(), self._accuracy()]
        if self._result.skipped:
            tables.append(Table(["レースID", "理由"], [list(row) for row in self._result.skipped], title="予測できなかったレース"))
        tables.append(Table(["書いた表"], [[str(self._result.path)]], title="登録馬の予測の表（registrations.pkl）"))
        return tables

    def _registrations(self) -> Table:
        table = self._table
        finished = table[table[FINISH].notna() | table[RAN]]
        rows = [
            ["レース数", table[RACE_ID].nunique(), "確定成績のあるレースは " + str(int(finished[RACE_ID].nunique()))],
            ["登録馬の数", len(table), "出走して着順の付いた馬は " + str(int((table[RAN] & table[FINISH].notna()).sum()))],
            ["地方馬の行の数", int((table[EXCHANGE] == _LOCAL).sum()), None],
            ["外国馬の行の数", int((table[EXCHANGE] == _FOREIGN).sum()), None],
        ]
        return Table(["項目", "値", "備考"], rows, title="確かめた登録馬",
                     note="登録馬の全員に予測を出し、確定成績と突き合わせた。出走するかどうかは当てないので、出走しなかった馬の割合は出さない。")

    def _accuracy(self) -> Table:
        ran = self._table[self._table[RAN] & self._table[FINISH].notna()]
        rows = [
            *self._accuracy_rows("3着以内", ran, PROBABILITY, ran[FINISH].between(1, 3)),
            *self._accuracy_rows("1着", ran, WIN_PROBABILITY, ran[FINISH].eq(1)),
        ]
        others = ran[ran[EXCHANGE].isin((_LOCAL, _FOREIGN))]
        rows.append(["地方馬・外国馬の行（出走した）", len(others), rounded(self._log_loss(others, PROBABILITY, others[FINISH].between(1, 3))) if len(others) else None, None])
        return Table(["目的変数", "行数", "ログ損失", "AUC"], rows, title="出走した登録馬だけでの当たり具合",
                     note="登録馬の中で比べた材料のまま出した確率を、出走して着順の付いた馬だけで測った。4. の 2026年の区切りの値（出走馬の中で比べた材料）との差を見る。")

    def _accuracy_rows(self, label: str, ran: pd.DataFrame, column: str, hit: pd.Series) -> list[list[object]]:
        valid = ran[ran[column].notna()]
        if valid.empty:
            return [[label, 0, None, None]]
        target = hit.loc[valid.index].astype(float)
        auc = roc_auc_score(target, valid[column]) if 0 < target.sum() < len(target) else float("nan")
        top_rate = self._top_pick_rate(valid, column, hit.loc[valid.index])
        return [[label, len(valid), rounded(self._log_loss(valid, column, hit.loc[valid.index])), rounded(auc)],
                [f"{label}: 確率1位（出走馬の中）の{label}率", int(valid[RACE_ID].nunique()), rounded(top_rate), None]]

    def _log_loss(self, rows: pd.DataFrame, column: str, hit: pd.Series) -> float:
        probability = rows[column].clip(_EPSILON, 1 - _EPSILON).to_numpy(dtype=float)
        return float(log_loss(hit.astype(float).to_numpy(), probability, labels=[0, 1]))

    def _top_pick_rate(self, rows: pd.DataFrame, column: str, hit: pd.Series) -> float:
        """レースごとに、出走した馬の中で確率が1位の馬が当たった割合。"""
        picks = rows.groupby(rows[RACE_ID].astype(str))[column].idxmax()
        return float(np.mean(hit.loc[picks].to_numpy(dtype=float))) if len(picks) else float("nan")
