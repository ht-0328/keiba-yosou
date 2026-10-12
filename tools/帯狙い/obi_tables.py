"""1日の帯狙いの結果を、表にする。"""

from __future__ import annotations

from typing import Any

from 共通.render import Table


class ObiTables:
    """``obi.py`` の1日の結果（辞書）から、3つの表を作る: 荒れそうなレースの上位、選んだレースの出走馬、買い目。"""

    def tables(self, result: dict[str, Any]) -> list[Table]:
        day = result["day"]
        ranking = Table(["順位", "レース", "時点", "3連単の超荒れの確率"],
                        [[number, row["title"], row["timing"], row["probability"]] for number, row in enumerate(result["ranking"], start=1)],
                        title=f"{day} 荒れそうなレースの上位", note="荒れ具合の予想の3連単の超荒れ（50万円以上）の確率。いちばん上のレースを「荒れる」と決めて買う（1日1レース）。")
        pick = result.get("pick")
        if pick is None:
            return [ranking]
        horses = Table(["馬番", "馬名", "印", "人気", "単勝オッズ", "荒れる前提の3着以内の確率", "荒れる前提の1着の確率"],
                       [[horse["馬番"], horse["馬名"], horse["印"], horse["人気"], horse["単勝オッズ"], horse["3着以内の確率"], horse["1着の確率"]]
                        for horse in pick["horses"]],
                       title=f"選んだレース: {pick['title']}（{pick['timing']}）")
        tickets = Table(["組", "掛け金", "オッズ", "当たったときの払戻"],
                        [[ticket["組"], ticket["掛け金"], ticket["オッズ"], ticket["払戻の見込み"]] for ticket in pick["tickets"]],
                        title=f"買い目（{result['plan']}・計 {pick['total_yen']:,}円）", note=pick["note"])
        return [ranking, horses, tickets]
