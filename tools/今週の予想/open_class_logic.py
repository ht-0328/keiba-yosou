"""AI＋ロジック予想のクラスのロジック: オープン以上のレース（オープン・L・G3・G2・G1）は、全レースの印の買い目を見送る。"""

from __future__ import annotations

#: 見送るクラス（予想の見出しの「クラス」の値）。
OPEN_CLASSES: tuple[str, ...] = ("オープン", "L", "G3", "G2", "G1")


class OpenClassLogic:
    """``class_name`` は予想の見出しのクラス（未勝利・1勝クラス・オープン・G1 など）。

    印の買い目は ◎ が1着のときだけ当たる形（単勝・馬連・馬単・3連単）。オープン以上のレースは、力の近い馬がそろって ◎ が勝ち切りにくく、
    過去のレースでは、印の買い目の的中率がほかのクラスより低かった。見送ると、回収率と的中率がどちらも上がった（研究「AIとロジックの予想」の docs/02）。
    """

    def skips(self, class_name: str) -> bool:
        """見送るか。"""
        return class_name in OPEN_CLASSES

    def reason(self, class_name: str) -> str:
        """見送る理由の文。例: ``オープン以上のレース（G3）で、◎ が勝ち切りにくい``。"""
        return f"オープン以上のレース（{class_name}）で、◎ が勝ち切りにくい"
