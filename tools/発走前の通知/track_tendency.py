"""その日のその競馬場（芝かダート）の、終わったレースから見た馬場の傾向（前が残るのか、後ろから差せるのか）。"""

from __future__ import annotations

import math
from dataclasses import dataclass

from 発走前の通知.position_counts import PositionCounts

#: いつもとの差の大きさ z の線。強い線を超えたら言い切り、弱い線なら「気味」。過去3年（その日の先の 1〜4レースで判定）では、
#: 強い偏りが 判定の 2〜3%、弱い偏りが 2〜3割ほどに出る高さ（中央も地方も）。
STRONG_Z, WEAK_Z = 2.0, 1.0
#: 4コーナーの位置の点数。前 0・中 1・後ろ 2。
_SCORES = (0, 1, 2)


@dataclass(frozen=True)
class TrackTendency:
    """``today`` はその日の先に終わったレース、``usual`` は同じ競馬場 × 芝ダの過去3年の、3着以内の馬の4コーナーの位置。

    3着以内の馬の位置の点数（前 0・中 1・後ろ 2）の平均を、いつもの平均と比べた
    z = （今日の平均 − いつもの平均）÷（いつもの点数の標準偏差 ÷ √3着以内の数）で言う。マイナスなら前寄り、プラスなら後ろ寄り。
    前・中・後ろを1つの物差しにするので、前が多いのに「差し」、後ろが多いのに「前」と逆向きに言うことがほぼ無い
    （前と後ろの割合を別々に比べると、地方のように後ろがいつも数%しか来ない競馬場では、後ろの2頭だけで「後ろから差せる」と出ていた）。
    例（架空）: いつもが 前 50%・中 33%・後ろ 17%（平均 0.67、標準偏差 0.75）で、今日 3レースの3着以内 9頭が 前 8・中 1・後ろ 0 なら、
    平均 0.11 で z = (0.11 − 0.67) ÷ (0.75 ÷ 3) = −2.2 で「前が止まらない」。
    過去の確かめでは、中央の後ろ寄りの日は残りのレースでも少し続くが、前寄りの日と地方は続かないので、文は「ここまで」の事実として書く。

    ``waiting`` は、先に走ったのに通過順の速報がまだ届いていない同じ芝ダのレースの番号（速報は 3着まで → 5着まで → 全馬の着順と
    通過順 の順に届き、通過順は発走の 10〜30 分後。地方は着順の確定と一緒に届くので、もう少し遅い。発走10分前の通知のときは、
    直前のレースがまだのことが多い）。
    """

    venue: str
    surface: str
    today: PositionCounts
    usual: PositionCounts
    waiting: tuple[int, ...] = ()

    def verdict(self) -> str:
        z = self.z()
        if abs(z) < WEAK_Z:
            return "前後の偏りは目立たない"
        strong = abs(z) >= STRONG_Z
        if z < 0:
            return "前が止まらない" if strong else "前が残り気味"
        return "後ろから差せる" if strong else "差しが届き気味"

    def z(self) -> float:
        """3着以内の馬の位置の点数の平均の、いつもとの差の大きさ（マイナスが前寄り）。いつもの点数がばらつかなければ 0。"""
        usual_mean = self._mean(self.usual)
        usual_square = sum(score * score * count for score, count in zip(_SCORES, self._counts(self.usual))) / self.usual.top3
        spread = math.sqrt((usual_square - usual_mean ** 2) / self.today.top3)
        return (self._mean(self.today) - usual_mean) / spread if spread > 0 else 0.0

    def text(self) -> str:
        """例 ``馬場 京都・芝（ここまで3R）: 前が残り気味。3着以内9頭の4角は 前 6・中 2・後ろ 1（過去3年の京都・芝は 前 52%・中 31%・後ろ 17%）``。
        通過順を待っているレースがあれば ``。5R は通過順の速報待ちで数えていない`` を足す。数えたレースが無ければ、その事情だけ
        （``馬場 京都・芝: 5R の通過順の速報がまだ届いていないので、まだ出せない`` か ``馬場 京都・芝: 今日の芝はこのレースが最初``）。"""
        head = f"馬場 {self.venue}・{self.surface}"
        waiting = "・".join(f"{race_no}R" for race_no in self.waiting)
        today, usual = self.today, self.usual
        if today.top3 == 0:
            if waiting:
                return f"{head}: {waiting} の通過順の速報がまだ届いていないので、まだ出せない"
            return f"{head}: 今日の{self.surface}はこのレースが最初"
        return (f"{head}（ここまで{today.races}R）: {self.verdict()}。"
                f"3着以内{today.top3}頭の4角は 前 {today.front}・中 {today.middle}・後ろ {today.back}"
                f"（過去3年の{self.venue}・{self.surface}は 前 {usual.front_share:.0%}・中 {usual.middle_share:.0%}・後ろ {usual.back_share:.0%}）"
                + (f"。{waiting} は通過順の速報待ちで数えていない" if waiting else ""))

    @staticmethod
    def _counts(counts: PositionCounts) -> tuple[int, int, int]:
        return counts.front, counts.middle, counts.back

    @classmethod
    def _mean(cls, counts: PositionCounts) -> float:
        return sum(score * count for score, count in zip(_SCORES, cls._counts(counts))) / counts.top3
