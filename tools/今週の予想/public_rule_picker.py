"""当日の予想で、1着の確率を直して、公開ルールの ◎・期待値・相手と、勝負にするかを決める。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from 共通 import facts

from yosou.shared.betting import TicketType
from yosou.shared.win_correction import FACT_COLUMNS, QUINELLA_TOP2, QuinellaTop2, WinCorrectionFeatures, WinCorrectionModel

from 今週の予想.forecast_columns import HORSE_ID, HORSE_NO, PLACE_ODDS_HIGH, PLACE_ODDS_LOW, PROBABILITY, UNRATED, WIN_ODDS, WIN_PROBABILITY
from 今週の予想.race_boards import RaceBoards

#: ◎ の候補にする単勝オッズの上限（倍。印の ◎ と同じ）。
TOP_ODDS_CAP = 30.0
#: 勝負にする、直した ◎ の期待値（直した1着の確率 × 単勝オッズ）の線。
SHOBU_LINE = 1.25
#: 勝負で馬単の相手にする頭数（直した1着の確率の高い順。◎ を除く）。
PARTNERS = 3
#: 出走馬の事実表の一時表の名前。
_ENTRY_TABLE = "public_rule_entries"


class PublicRulePicker:
    """当日の予想の印を付けた表（``MarkRule.assign`` の戻り値）と、締め切り前の馬連の板と複勝オッズ（``RaceBoards``）と、出走馬の事実表
    （``共通.facts.build_entry_facts``。馬IDでつなぐ）から、今の1着の確率を直し（``WinCorrectionModel``）、公開ルールの判定を返す。

    直した ◎ は、単勝 ``TOP_ODDS_CAP`` 倍以下で評価できる馬（列 ``unrated`` が偽）のうち、直した1着の確率 × 単勝オッズ（期待値）が最大の馬。
    相手は ◎ を除いた直した1着の確率の上位 ``PARTNERS`` 頭。期待値が ``SHOBU_LINE`` 以上なら勝負。
    結果は予想の結果の JSON に残す辞書（``ready``・``top``・``value``・``probability``・``odds``・``partners``・``line``・``shobu``・``reason``）。
    モデルが無い・材料がそろわないときは ``ready`` が偽で、``reason`` に理由。
    """

    def __init__(self, model: WinCorrectionModel | None) -> None:
        self._model = model

    @classmethod
    def load(cls, models: Path | None) -> PublicRulePicker:
        return cls(WinCorrectionModel.load(Path(models)) if models is not None else None)

    def judge(self, con: duckdb.DuckDBPyConnection, race_id: str, marked: pd.DataFrame) -> dict[str, Any]:
        if self._model is None:
            return _not_ready("確率を直すモデルが無い（道具「公開ルール」の fit.py で作る）")
        boards = RaceBoards(con, race_id)
        horses = self._horses(con, race_id, marked, boards)
        if horses is None:
            return _not_ready("単勝・複勝・馬連のオッズがそろわない")
        corrected = self._model.probabilities(WinCorrectionFeatures().frame(horses), horses["race_id"])
        return self.decide(horses.assign(corrected=corrected))

    def _horses(self, con: duckdb.DuckDBPyConnection, race_id: str, marked: pd.DataFrame, boards: RaceBoards) -> pd.DataFrame | None:
        """確率を直す材料の表（1頭1行）。単勝・複勝の最低オッズ・馬連から見た率の欠ける馬がいれば None。"""
        horses = marked.reindex(columns=[HORSE_ID, HORSE_NO, WIN_PROBABILITY, PROBABILITY, WIN_ODDS, PLACE_ODDS_LOW, PLACE_ODDS_HIGH, UNRATED])
        horses = horses.assign(race_id=race_id, **{HORSE_NO: horses[HORSE_NO].astype(int), HORSE_ID: horses[HORSE_ID].astype(str)}).reset_index(drop=True)
        horses = _fill_place_high(horses, boards.place_odds())
        quinella = QuinellaTop2().of(boards.of(TicketType.QUINELLA))
        horses = horses.merge(quinella[["horse_no", QUINELLA_TOP2]], on="horse_no", how="left")
        horses = horses.merge(_entry_facts(con, race_id), on=HORSE_ID, how="left")
        needed = horses[[WIN_PROBABILITY, PROBABILITY, WIN_ODDS, PLACE_ODDS_LOW, QUINELLA_TOP2]]
        return None if horses.empty or needed.isna().any().any() else horses

    @staticmethod
    def decide(horses: pd.DataFrame) -> dict[str, Any]:
        """1レースの表（列 ``horse_no``・``win_odds``・``unrated``・``corrected``（直した1着の確率））から、判定の辞書を作る。研究の確かめも同じものを使う。"""
        rated = horses[~horses[UNRATED].fillna(False).astype(bool) & (horses[WIN_ODDS].astype(float) <= TOP_ODDS_CAP)]
        if rated.empty:
            return _not_ready(f"単勝 {TOP_ODDS_CAP:g}倍以下の評価できる馬がいない")
        values = rated["corrected"] * rated[WIN_ODDS].astype(float)
        top = rated.loc[values.idxmax()]
        partners = horses[horses[HORSE_NO] != top[HORSE_NO]].sort_values("corrected", ascending=False)[HORSE_NO].head(PARTNERS)
        value = float(values.max())
        return {"ready": True, "top": int(top[HORSE_NO]), "value": value, "probability": float(top["corrected"]), "odds": float(top[WIN_ODDS]),
                "partners": [int(number) for number in partners], "line": SHOBU_LINE, "shobu": value >= SHOBU_LINE, "reason": ""}


def _not_ready(reason: str) -> dict[str, Any]:
    return {"ready": False, "top": None, "value": None, "probability": None, "odds": None, "partners": [], "line": SHOBU_LINE, "shobu": False,
            "reason": reason}


def _fill_place_high(horses: pd.DataFrame, place_odds: pd.DataFrame) -> pd.DataFrame:
    """複勝オッズ（最低・最高）の欠けを、締め切り前の複勝オッズで埋める（当日の予想の表には最高の列が無いことがある）。"""
    if place_odds is None or place_odds.empty:
        return horses
    board = place_odds.dropna(subset=["horse_no"]).drop_duplicates("horse_no").set_index("horse_no")
    filled = {column: pd.to_numeric(horses[column], errors="coerce").fillna(horses[HORSE_NO].map(board[column]))
              for column in (PLACE_ODDS_LOW, PLACE_ODDS_HIGH) if column in board.columns}
    return horses.assign(**filled)


def _entry_facts(con: duckdb.DuckDBPyConnection, race_id: str) -> pd.DataFrame:
    """出走馬の事実表の ``FACT_COLUMNS``（馬IDごと）。レースが事実表に無ければ空の表（材料は欠損値のまま予測する）。"""
    try:
        table = facts.build_entry_facts(con, facts.EntryScope(race_id), name=_ENTRY_TABLE)
    except LookupError:
        return pd.DataFrame(columns=[HORSE_ID, *FACT_COLUMNS])
    columns = ", ".join(["horse_id", *FACT_COLUMNS])
    entries = con.execute(f"SELECT {columns} FROM {table}").df()
    return entries.assign(**{HORSE_ID: entries["horse_id"].astype(str)}).drop_duplicates(HORSE_ID)
