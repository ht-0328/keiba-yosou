"""ばんえいの1レースの、いま元DB にある最後の単勝オッズと複勝オッズ（低い方）を読む（表に見せるためだけ。予想と買い目には使わない）。"""

from __future__ import annotations

import duckdb

#: 馬番ごとに、発表の新しい行だけ。オッズは 10倍の整数の文字（発売前や取消は数字でない）。
_SQL = """
SELECT w.馬番, w.オッズ, p.最低オッズ
FROM "o1__単勝オッズ" w
LEFT JOIN "o1__複勝オッズ" p
  USING (開催年, 開催月日, 競馬場コード, "開催回[第N回]", "開催日目[N日目]", レース番号, 発表月日時分, 馬番)
WHERE w.開催年 = ? AND w.開催月日 = ? AND w.競馬場コード = ? AND w."開催回[第N回]" = ? AND w."開催日目[N日目]" = ? AND w.レース番号 = ?
QUALIFY row_number() OVER (PARTITION BY w.馬番 ORDER BY w.発表月日時分 DESC) = 1
"""


class BaneiOddsRepository:
    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, rid: str) -> dict[int, tuple[float | None, float | None]]:
        """馬番 →（単勝オッズ, 複勝オッズの低い方）。オッズの表がまだ無い・そのレースのオッズが無いときは空。"""
        keys = (rid[:4], rid[4:8], rid[8:10], rid[10:12], rid[12:14], rid[14:16])
        try:
            rows = self._con.execute(_SQL, keys).fetchall()
        except duckdb.CatalogException:
            return {}
        return {int(number): (self._odds(win), self._odds(place)) for number, win, place in rows if str(number).strip().isdigit()}

    @staticmethod
    def _odds(text: object) -> float | None:
        value = str(text or "").strip()
        return int(value) / 10.0 if value.isdigit() and int(value) > 0 else None
