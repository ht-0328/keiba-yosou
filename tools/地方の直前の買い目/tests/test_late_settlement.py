"""LateSettlement（払戻を当てる）・LateSummary（期間ごとの回収率）・SavedLateBets（通知が書いたファイルを集める）のテスト。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from 地方の直前の買い目.late_bet_file import LateBetFile
from 地方の直前の買い目.late_bets import LateBets
from 地方の直前の買い目.late_pick import LatePick
from 地方の直前の買い目.late_settlement import LateSettlement
from 地方の直前の買い目.late_summary import LateSummary
from 地方の直前の買い目.saved_late_bets import SavedLateBets

A, B, C = "2026111844120105", "2026111844120106", "2026122044120107"
PICK = LatePick(6, 12.0, 0.5, 1.2, (1, 2, 3, 4, 5), (2, 7))


def _settlement() -> LateSettlement:
    wins = pd.DataFrame({"race_id": [A, B, C], "horse_no": [6, 1, 6], "payout": [1200, 150, 900]})
    trifectas = pd.DataFrame({"race_id": [A, B, C], "first": [6, 1, 6], "second": [2, 6, 7], "third": [1, 2, 1], "payout": [50000, 3000, 80000]})
    exactas = pd.DataFrame({"race_id": [A, B, C], "first": [6, 1, 6], "second": [2, 6, 1], "payout": [4000, 600, 2500]})
    return LateSettlement(wins, exactas, trifectas)


def test_単勝と馬単と3連単の払戻を当てる_相手に無い馬が来た組は外れ() -> None:
    settled = _settlement().settle([(A, PICK), (B, PICK), (C, PICK)])
    assert settled["win_back"].tolist() == [1200.0, 0.0, 900.0]
    assert settled["trifecta_back"].tolist() == [50000.0, 0.0, 0.0]      # C は 2着が 7番（相手の外）
    assert settled["trifecta_cost"].tolist() == [2000, 2000, 2000] and settled["win_cost"].tolist() == [100, 100, 100]
    assert settled["exacta_back"].tolist() == [4000.0, 0.0, 0.0]         # C は 2着が 1番（馬単の相手の外）
    assert settled["exacta_cost"].tolist() == [200, 200, 200]
    old = LatePick(6, 12.0, 0.5, 1.2, (1, 2, 3, 4, 5))                   # 馬単を足す前の買い目は、馬単を買っていない
    assert _settlement().settle([(A, old)])[["exacta_cost", "exacta_back"]].iloc[0].tolist() == [0, 0.0]


def test_結果のまだ無いレースは数えない() -> None:
    settled = _settlement().settle([("2026123144120101", PICK), (A, PICK)])
    assert settled["race_id"].tolist() == [A]


def test_まとめは_全体_年_四半期ごとの回収率() -> None:
    table = LateSummary().table(_settlement().settle([(A, PICK), (B, PICK), (C, PICK)]), "題")
    rows = {(row[0], row[1]): row for row in table.rows}
    assert rows[("全体", "単勝")][2:6] == [3, 3, 2, "66.7%"] and rows[("全体", "単勝")][8] == "700.0%"
    assert rows[("全体", "馬単（1着固定）")][3] == 6 and rows[("全体", "馬単（1着固定）")][8] == "666.7%"
    assert rows[("全体", "3連単（1着固定）")][3] == 60 and rows[("全体", "3連単（1着固定）")][8] == "833.3%"
    assert rows[("全体", "単勝")][9] == "0.0%"                           # 上位5本を除くと何も残らない
    assert ("2026年", "単勝") in rows and ("2026Q4", "単勝") in rows


def test_通知が書いたファイルを_期間で集める(tmp_path: Path) -> None:
    file = LateBetFile()
    file.write(tmp_path / "2026-11-18" / f"{A}.直前.json", LateBets((PICK,), "", "11181530"))
    file.write(tmp_path / "2026-11-18" / f"{B}.直前.json", LateBets.none("線以上の馬がいない"))
    file.write(tmp_path / "2026-12-20" / f"{C}.直前.json", LateBets((PICK,)))
    (tmp_path / "2026-11-18" / f"{A}.json").write_text("{}", encoding="utf-8")   # 予想の JSON は読まない
    saved = SavedLateBets(tmp_path)
    assert [rid for rid, _ in saved.read("2026-11-01", "2026-11-30")] == [A, B]
    assert [rid for rid, _ in saved.read("0000-00-00", "9999-99-99")] == [A, B, C]
    assert saved.read("2026-11-01", "2026-11-30")[0][1].picks == (PICK,)
