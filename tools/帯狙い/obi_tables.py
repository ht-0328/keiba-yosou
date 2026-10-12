"""1日の帯狙いの結果を、表にする。"""

from __future__ import annotations

from typing import Any

from 共通.render import Table


class ObiTables:
    """``obi.py`` の1日の結果（辞書）から表を作る: 荒れそうなレースの上位（1つ）と、選んだレースごとの出走馬と買い目（2つずつ）。"""

    def tables(self, result: dict[str, Any]) -> list[Table]:
        day, line, score = result["day"], result["line"], result.get("score", "平均")
        ranking = Table(["順位", "レース", "時点", "荒れ具合の予想", "予想が見た確率", "点数", "買う"],
                        [[number, row["title"], row["timing"], row["upset_probability"], row.get("chance"), row["probability"],
                          "買う" if row["chosen"] else ""] for number, row in enumerate(result["ranking"], start=1)],
                        title=f"{day} 荒れそうなレースの上位（点数: {score}・線 {line}）",
                        note="点数 = 荒れ具合の予想の3連単が 1,000倍以上になる確率（大荒れ＋超荒れ）と、予想が見た 1,000倍以上になる確率"
                             "（今の予想の1着の確率と3連単のオッズから）の平均。予想が見た確率が無いレース（点数が大荒れ＋超荒れのときも）は荒れ具合の予想だけ。"
                             f"{line} 以上のレースを全部「荒れる」と決めて買う。")
        tables = [ranking]
        for pick in result["picks"]:
            tables += self._pick_tables(result["plan"], pick)
        return tables

    @staticmethod
    def _pick_tables(plan: str, pick: dict[str, Any]) -> list[Table]:
        horses = Table(["馬番", "馬名", "印", "人気", "単勝オッズ", "荒れる前提の3着以内の確率", "荒れる前提の1着の確率", "今の予想の3着以内の確率"],
                       [[horse["馬番"], horse["馬名"], horse["印"], horse["人気"], horse["単勝オッズ"], horse["3着以内の確率"], horse["1着の確率"],
                         horse.get("今の予想の3着以内の確率")] for horse in pick["horses"]],
                       title=f"選んだレース: {pick['title']}（{pick['timing']}・点数 {pick['probability']}）")
        tickets = Table(["組", "掛け金", "オッズ", "当たったときの払戻"],
                        [[ticket["組"], ticket["掛け金"], ticket["オッズ"], ticket["払戻の見込み"]] for ticket in pick["tickets"]],
                        title=f"買い目（{plan}・計 {pick['total_yen']:,}円）", note=pick["note"])
        return [horses, tickets]
