"""元DB のレースの鍵6列を SQL の断片にする。すべてのリポジトリがこれを使う。"""

from __future__ import annotations

#: レースの鍵6列を連結した16桁（rid）を作る式。
RID = '開催年 || 開催月日 || 競馬場コード || "開催回[第N回]" || "開催日目[N日目]" || レース番号'
#: 同じ6列をカンマで並べたもの（``partition by`` に使う）。
RACE_KEYS = '開催年, 開催月日, 競馬場コード, "開催回[第N回]", "開催日目[N日目]", レース番号'
#: 中央競馬の競馬場コードだけに絞る条件。
JRA_ONLY = "競馬場コード between '01' and '10'"
#: 確定成績のデータ区分（速報・確定）。
FINAL_STAGES = "('5', '6', '7')"
#: 確定オッズのデータ区分（4 確定・5 確定(月曜)）。締め切り前の断面（1 中間・2 前日売最終・3 最終）と中止（9）は読まない。
FINAL_ODDS_STAGES = "('4', '5')"
#: オッズの子の表と、その断面を選ぶ表を結ぶ列（レースの鍵 ＋ 発表時刻）。
_SNAPSHOT_KEYS = RACE_KEYS + ", 発表月日時分"


def final_odds_rows(child_table: str) -> str:
    """オッズの子の表（``o6__3連単オッズ`` など）のうち、レースごとの確定の断面1つぶんの行だけを残す ``from`` の中身。

    オッズの表には、確定オッズのほかに、締め切り前の断面（時系列オッズ・速報オッズ）がレースごとに何百行も入りうる。
    絞らずに足し合わせると、断面をまたいで混ざった値になる。親の表（``o6``）で確定の断面を1つ選び、それと結ぶ。
    """
    parent = child_table.split("__")[0]
    return f"""{child_table} semi join (
        select {_SNAPSHOT_KEYS} from {parent}
        where データ区分 in {FINAL_ODDS_STAGES}
        qualify row_number() over (partition by {RACE_KEYS} order by データ区分 desc, 発表月日時分 desc) = 1
    ) as 確定の断面 using ({_SNAPSHOT_KEYS})"""
