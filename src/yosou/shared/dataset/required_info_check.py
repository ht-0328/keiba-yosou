"""予測に要る情報が DB にあるかを確かめる。"""

from __future__ import annotations

import pandas as pd

#: その時点で使うのに、DB にまだ無いと予測できない特徴量と、取り込み方の案内。
_GUIDANCE: dict[str, str] = {
    "馬番": "馬番がまだ決まっていません（出走馬名表の段階）。"
            "jvstore sync で出馬表を取り込むか、時点を木曜にしてください。",
    "馬場状態": "馬場状態がまだ DB にありません。jvstore realtime（開催日）で速報を取り込んでください。",
    "馬体重": "馬体重がまだ DB にありません。"
              "馬体重の発表のあとに jvstore realtime（開催日）で速報を取り込んでください。",
    "単勝オッズ": "単勝オッズがまだ DB にありません。--odds 馬番:オッズ で渡すか、"
                  "jvstore realtime（開催日）で締め切り前のオッズを取り込んでください。",
}


class RequiredInfoCheck:
    """その時点で使う特徴量のうち、馬番・馬場状態・馬体重・単勝オッズが、全頭で欠けていないかを確かめる。

    欠けたまま予測すると、学習のときと違う様子のデータをモデルに渡すことになる（設計書 07）。
    オッズを使わない予想では「単勝オッズ」の列が無いので、その確認は素通りする。
    """

    def check(self, features: pd.DataFrame) -> None:
        """欠けていれば、取り込み方の案内を付けて ``ValueError``。"""
        missing = [column for column in _GUIDANCE if self._is_missing(features, column)]
        if missing:
            raise ValueError(_GUIDANCE[missing[0]])

    def _is_missing(self, features: pd.DataFrame, column: str) -> bool:
        """その時点で使う列なのに、全頭で欠損値か。"""
        return column in features.columns and bool(features[column].isna().all())
