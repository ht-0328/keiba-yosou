"""候補のことばを、各走の「その走までの材料」から付ける。"""

from __future__ import annotations

import pandas as pd

from 近走の文.evaluation_words import BIG_LOSS_GAP, BIG_LOSS_RUNS, BIG_LOSSES, IMPROVING, IMPROVING_RUNS
from 近走の文.past_run import LOST_FINISH

#: 見送った候補の線（本番には無いので、ここに持つ）。
#: 「負けて強し」: 前走が4着以下でも、着差がこの秒数以内で、不利があったか上がり3ハロンがこの順位以内。
CLOSE_GAP = 0.3
FAST_LAST3F_RANK = 3
#: 「人気薄で好走の実績」: 近この走数に、この人気以下で3着以内がある。
LONGSHOT_POPULARITY = 10
LONGSHOT_WINDOW = 5
STRONG_LOSS, LONGSHOT_RECORD = "負けて強し", "人気薄で好走の実績"

#: ことばの列と、その向き（True = 良いことば、False = 悪いことば、None = 参考）。
WORD_SIDES: dict[str, bool | None] = {
    f"{STRONG_LOSS}（不利あり）": True, f"{STRONG_LOSS}（上がり上位）": True, STRONG_LOSS: True,
    IMPROVING: True, f"{IMPROVING}（着順）": True, LONGSHOT_RECORD: True, BIG_LOSSES: False,
    "参考: 前走3着以内": None, "参考: 前走4着以下で着差が小さい（不利・末脚を問わない）": None,
}


class WordLabels:
    """馬ごと・日付順に並んだ走の表に、候補のことばの真偽の列を足す。各行のことばは、その行より前の走だけから決める。

    採ったことば（上向き・大敗続き）の線は ``tools/近走の文/evaluation_words.py`` の定数と同じ。見送った候補の線はこのファイルの定数。
    ``WORD_SIDES`` の列を返す。
    """

    def of(self, frame: pd.DataFrame) -> pd.DataFrame:
        by_horse = frame.groupby("horse_id", sort=False)
        prev = {k: {name: by_horse[name].shift(k) for name in ("finish", "time_diff", "last3f_rank", "popularity", "handicap")}
                for k in range(1, max(IMPROVING_RUNS, LONGSHOT_WINDOW, BIG_LOSS_RUNS) + 1)}
        lost_close = (prev[1]["finish"] >= LOST_FINISH) & (prev[1]["time_diff"] <= CLOSE_GAP)
        handicap = prev[1]["handicap"].fillna(False).astype(bool)
        fast = prev[1]["last3f_rank"] <= FAST_LAST3F_RANK
        labels = pd.DataFrame(index=frame.index)
        labels[f"{STRONG_LOSS}（不利あり）"] = lost_close & handicap
        labels[f"{STRONG_LOSS}（上がり上位）"] = lost_close & fast
        labels[STRONG_LOSS] = lost_close & (handicap | fast)
        labels[IMPROVING] = self._improving(prev, "time_diff")
        labels[f"{IMPROVING}（着順）"] = self._improving(prev, "finish")
        longshot = pd.Series(False, index=frame.index)
        for k in range(1, LONGSHOT_WINDOW + 1):
            longshot |= (prev[k]["popularity"] >= LONGSHOT_POPULARITY) & (prev[k]["finish"] <= 3)
        labels[LONGSHOT_RECORD] = longshot
        big = pd.Series(True, index=frame.index)
        for k in range(1, BIG_LOSS_RUNS + 1):
            big &= prev[k]["time_diff"] >= BIG_LOSS_GAP
        labels[BIG_LOSSES] = big
        labels["参考: 前走3着以内"] = prev[1]["finish"] <= 3
        labels["参考: 前走4着以下で着差が小さい（不利・末脚を問わない）"] = lost_close
        return labels.fillna(False).astype(bool)

    def _improving(self, prev: dict[int, dict[str, pd.Series]], name: str) -> pd.Series:
        """近 ``IMPROVING_RUNS`` 走の値が、古い走から新しい走へ続けて小さくなっているか。"""
        result = None
        for k in range(1, IMPROVING_RUNS):
            step = prev[k + 1][name] > prev[k][name]
            result = step if result is None else result & step
        return result
