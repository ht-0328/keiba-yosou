"""基準のページの先頭と目次に置く、「延長と短縮のどちらが有利か」のまとめ。"""

from __future__ import annotations

import pandas as pd

from 共通 import distance_change
from 共通.distance_change_verdict import MIN_RUNS, SHOWN_CHANGES, DistanceChangeVerdict

TITLE = "延長と短縮のどちらが有利か"
#: まとめの見方（ページと目次で同じ文）。
EXPLANATION = (
    "前走より距離が短い馬（短縮）と長い馬（延長）を、コースの全馬場状態を合わせて比べたもの。"
    "**勝つ** は全馬の勝率、**穴馬の好走** は穴馬（"
    f"{distance_change.LONGSHOT_MIN_POPULARITY}番人気以下）の複勝率。"
    "かっこの中は **人気から見た差**（同じコースで同じ人気の馬がふつう出す率との差）。延長の馬は人気薄に偏るなど、"
    "組ごとに人気の混ざり方が違うので、有利なほうは実際の率ではなく人気から見た差で判定する。"
    "短縮と延長の差が検定で 5%（1%）の線を超えたときだけ「短縮が有利」「延長が有利」と書き、超えなければ「差なし」。"
    f"短縮・延長のどちらかの出走が {MIN_RUNS} 未満なら「標本が少ない」。"
    "**多くのコースで同じ検定をするので、本当は差が無くても 5% の線では 20 コースに1つほど「有利」と出る。**"
    "1つのコースの「有利（5%）」だけで決めず、1% の印や、同じ競馬場・近い距離のコースでも同じ向きかを合わせて見る。"
)


class DistanceChangeSummary:
    """コース（トラックコード）ごとの判定を、ページの表と目次の行にする。"""

    def __init__(self, verdict: DistanceChangeVerdict) -> None:
        self._verdict = verdict

    def page_lines(self, runs: pd.DataFrame) -> list[str]:
        """1ページ（競馬場×芝ダ×距離）の出走から、コースごとに「勝つ」「穴馬の好走」の2行の表を作る。"""
        lines = ["", f"## {TITLE}", "", EXPLANATION, "",
                 "| コース | 見るもの | " + " | ".join(SHOWN_CHANGES) + " | 有利なほう |",
                 "| :--- | :--- |" + " :--- |" * (len(SHOWN_CHANGES) + 1)]
        for course, course_runs in _courses(runs):
            for name, verdict in (("勝つ（勝率）", self._verdict.win(course_runs)),
                                  ("穴馬の好走（複勝率）", self._verdict.longshot(course_runs))):
                cells = [verdict.results[change].text() for change in SHOWN_CHANGES]
                lines.append(f"| {course} | {name} | " + " | ".join(cells) + f" | {verdict.winner} |")
        lines.extend(["", "馬場状態ごとの値は、各節の「距離の変更」「距離の変更の幅」「距離の変更（穴馬）」の表にある。"])
        return lines

    def index_rows(self, runs: pd.DataFrame) -> list[tuple[str, str, str]]:
        """1ページの出走から、コースごとに（コース・勝つ・穴馬の好走）の判定を返す。"""
        return [(course, self._verdict.win(course_runs).winner, self._verdict.longshot(course_runs).winner)
                for course, course_runs in _courses(runs)]


def _courses(runs: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    """コース（トラックコードの順）ごとの出走。"""
    return [(course, part) for (_, course), part in runs.groupby(["track_code", "course"], sort=True)]
