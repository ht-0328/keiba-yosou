"""その日のその競馬場（芝かダート）の、終わったレースから見た馬場の傾向（前が残るのか、後ろから差せるのか）。"""

from __future__ import annotations

import math
from dataclasses import dataclass

from 発走前の通知.position_counts import PositionCounts

#: いつもとの差の大きさ z（二項分布の標準偏差で割ったもの）の線。強い線を超えたら言い切り、弱い線なら「気味」。
#: 過去3年（その日の先の 1〜4レースで判定）では、強い偏りが 開催日 × 競馬場 × 芝ダ の 1〜8%、弱い偏りが 1〜3割ほどに出る高さ。
STRONG_Z, WEAK_Z = 2.0, 1.0


@dataclass(frozen=True)
class TrackTendency:
    """``today`` はその日の先に終わったレース、``usual`` は同じ競馬場 × 芝ダの過去3年の、3着以内の馬の4コーナーの位置。

    前の割合と後ろの割合のそれぞれを、いつもの割合と比べた z = （頭数 − 3着以内の数 × いつもの割合）÷ √（3着以内の数 × p × (1 − p)）。
    前寄りの強さは「前の z」と「後ろの z の符号を変えたもの（後ろが少ない）」の大きいほう、後ろ寄りはその逆。
    大きいほうの向きで言う（どちらも弱い線に届かなければ「偏りは目立たない」）。例（架空）: いつもの前の割合 50% で、
    今日 3レースの3着以内 9頭のうち前が 8頭なら z = (8 − 4.5) ÷ 1.5 = 2.3 で「前が止まらない」。
    過去の確かめでは、中央の後ろ寄りの日は残りのレースでも少し続くが、前寄りの日と地方は続かないので、文は「ここまで」の事実として書く。

    ``waiting`` は、先に走ったのに通過順の速報がまだ届いていない同じ芝ダのレースの番号（速報は 3着まで → 5着まで → 全馬の着順と
    通過順 の順に届き、通過順は発走の 10〜30 分後。発走10分前の通知のときは、直前のレースがまだのことが多い）。
    """

    venue: str
    surface: str
    today: PositionCounts
    usual: PositionCounts
    waiting: tuple[int, ...] = ()

    def verdict(self) -> str:
        front_z = self._z(self.today.front, self.usual.front_share)
        back_z = self._z(self.today.back, self.usual.back_share)
        front, back = max(front_z, -back_z), max(back_z, -front_z)   # 後ろが少ないのは前寄り、前が少ないのは後ろ寄り
        if max(front, back) < WEAK_Z:
            return "前後の偏りは目立たない"
        strong = max(front, back) >= STRONG_Z
        if front >= back:
            return "前が止まらない" if strong else "前が残り気味"
        return "後ろから差せる" if strong else "差しが届き気味"

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

    def _z(self, count: int, share: float) -> float:
        spread = math.sqrt(self.today.top3 * share * (1 - share))
        return (count - self.today.top3 * share) / spread if spread > 0 else 0.0
