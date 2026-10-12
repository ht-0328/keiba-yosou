"""1日の帯狙いの結果を、表にする。"""

from __future__ import annotations

from typing import Any

from 共通.render import Table


class ObiTables:
    """``obi.py`` の1日の結果（辞書）から表を作る: 荒れそうなレースの上位（1つ）と、選んだレースごとの出走馬と買い目（2つずつ）。"""

    def tables(self, result: dict[str, Any]) -> list[Table]:
        day, line = result["day"], result["line"]
        ranking = Table(["順位", "レース", "時点", "1,000倍以上になる確率", "買う"],
                        [[number, row["title"], row["timing"], row["probability"], "買う" if row["chosen"] else ""]
                         for number, row in enumerate(result["ranking"], start=1)],
                        title=f"{day} 荒れそうなレースの上位（線 {line}）",
                        note=f"荒れ具合の予想の3連単の大荒れ＋超荒れ（10万円以上 = 1,000倍以上）の確率。{line} 以上のレースを全部「荒れる」と決めて買う。")
        tables = [ranking]
        for pick in result["picks"]:
            tables += self._pick_tables(result["plan"], pick)
        return tables

    @staticmethod
    def _pick_tables(plan: str, pick: dict[str, Any]) -> list[Table]:
        horses = Table(["馬番", "馬名", "印", "人気", "単勝オッズ", "荒れる前提の3着以内の確率", "荒れる前提の1着の確率", "今の予想の3着以内の確率"],
                       [[horse["馬番"], horse["馬名"], horse["印"], horse["人気"], horse["単勝オッズ"], horse["3着以内の確率"], horse["1着の確率"],
                         horse.get("今の予想の3着以内の確率")] for horse in pick["horses"]],
                       title=f"選んだレース: {pick['title']}（{pick['timing']}・1,000倍以上になる確率 {pick['probability']}）")
        tickets = Table(["組", "掛け金", "オッズ", "当たったときの払戻"],
                        [[ticket["組"], ticket["掛け金"], ticket["オッズ"], ticket["払戻の見込み"]] for ticket in pick["tickets"]],
                        title=f"買い目（{plan}・計 {pick['total_yen']:,}円）", note=pick["note"])
        return [horses, tickets]
