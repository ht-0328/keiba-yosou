"""作り方ごとの道具「印の成績」の結果を、1つの表に並べる。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import pandas as pd

from 共通.render import Table

#: 並べる元の買い目（印のルールの買い方。設計書「買うレースと買い目を決める」08 の 2）。
ORIGINAL_BETS: tuple[str, ...] = (
    "単勝", "複勝", "ワイド", "馬連", "馬単", "3連複（◎−○▲☆−○▲△☆）", "3連単（◎→○▲☆→○▲△☆）",
)
#: 道具の表1 から拾う、消の行。
_DANGER_ROWS: tuple[str, ...] = ("消", "消のうち 1番人気", "消のうち 2〜5番人気")
_DANGER_HEADER = "### 1. 印ごとの成績"


class MarkSummary:
    """``<root>/<作り方>/`` にある道具「印の成績」の結果（買い目の CSV と Markdown）から、作り方ごとの
    元の買い目の券種ごとの回収率と合計、消の成績を並べる。``names`` は作り方 → 表に出す名前（並べる順）。
    """

    def tables(self, root: Path, names: Mapping[str, str]) -> list[Table]:
        made = {key: name for key, name in names.items() if (Path(root) / key).is_dir()}
        return [self._bets(root, made), self._dangers(root, made)]

    def _bets(self, root: Path, names: Mapping[str, str]) -> Table:
        records = []
        for key, name in names.items():
            tickets = pd.concat([pd.read_csv(path, encoding="utf-8-sig", dtype={"組番": str})
                                 for path in (Path(root) / key / "買い目").glob("*.csv")], ignore_index=True)
            original = tickets[tickets["買い方"].isin(ORIGINAL_BETS) & tickets["外した理由"].isna()]
            record = {"作り方": name}
            for bet in ORIGINAL_BETS:
                record[bet] = _roi(original[original["買い方"].eq(bet)])
            record["合計（元の買い目）"] = _roi(original)
            record["合計の投資（100円単位）"] = f"{int(original['単位'].sum()):,}"
            records.append(record)
        return Table.from_records(records, title="5. G1 のレースの、元の買い目の券種ごとの回収率（道具「印の成績」。1点 100円 × 単位）",
                                  note="作り方で変わるのは消（危険な人気馬）だけ。消の馬は ◎〜注 に入らないので、印と買い目が変わる。"
                                       "トリガミで外した点は数えない。")

    def _dangers(self, root: Path, names: Mapping[str, str]) -> Table:
        records = []
        for key, name in names.items():
            rows = _mark_rows(next((Path(root) / key).glob("*.md")))
            for label in _DANGER_ROWS:
                row = rows.get(label)
                if row is not None:
                    records.append({"作り方": name, "印": label, **row})
        return Table.from_records(records, title="6. 消（危険な人気馬）の成績（道具「印の成績」の表1）",
                                  note="消の馬の成績なので、複勝率・回収率が低いほど、危険な馬を当てている。")


def _roi(tickets: pd.DataFrame) -> str:
    stake = tickets["単位"].sum()
    if stake == 0:
        return "-"
    return f"{(tickets['払戻（100円あたり）'] * tickets['単位']).sum() / (100 * stake):.1%}"


def _mark_rows(path: Path) -> dict[str, dict[str, str]]:
    """道具の Markdown の表1 の、印 → 列 → 値。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = lines.index(_DANGER_HEADER)
    end =next((index for index, line in enumerate(lines[start + 3:], start + 3) if not line.startswith("|")), len(lines))
    table = [line for line in lines[start + 1:end] if line.startswith("|")]
    header = _cells(table[0])
    return {cells[0]: dict(zip(header[2:], cells[2:])) for cells in (_cells(line) for line in table[2:])}


def _cells(line: str) -> Sequence[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]
