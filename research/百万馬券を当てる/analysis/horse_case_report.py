"""手順5: 荒れたレースで「1〜3着に来た人気薄」と「来なかった人気薄」を比べる表を、Markdown の行にする。"""

from __future__ import annotations

import pandas as pd

from .horse_frame import IN_TOP3, POPULARITY
from .lift_table import COUNT, LIFT, RATE, LiftTable
from .obi_rules import BIG, LONGSHOT_FROM_POPULARITY, OBI
from .race_frame import PAYOUT_CLASS

#: 比べる切り口（docs/01 の 5.1 の候補）。
LIFT_COLUMNS: dict[str, tuple[str, ...]] = {
    "展開で残る・届く": ("推定脚質", "前走の4コーナーの位置", "序盤の位置_近5走の平均_順位", "末脚_近5走の平均_順位", "逃げそうな馬の数"),
    "馬場の偏り": ("馬番の位置", "枠番"),
    "条件替わり": ("距離の変更", "芝ダ替わり", "クラスの変更", "前走と同じ競馬場か", "前走からの日数", "休み明け_2走目"),
    "巻き返し": ("前走の着順", "前走の人気", "前走の着差", "展開の不利_前走", "末脚と着順のずれ_前走"),
    "斤量と騎手": ("斤量とレースの平均との差", "減量騎手", "乗り替わり", "騎手_1年_勝率_順位"),
    "力": ("指数_条件の重み_順位", "指数_前走_順位", "相対着順_近5走の平均_順位", "近5走の平均着順"),
    "人気": ("人気順位", "単勝オッズ"),
    "馬": ("馬齢", "性別", "馬体重の増減", "通算の出走数"),
}
#: 比べる表の列の名前。
WILD_COUNT, WILD_RATE, WILD_LIFT, USUAL_RATE, USUAL_LIFT, GAP = (
    "荒れたレースの頭数", "荒れたレースの3着以内率", "荒れたレースの集まり方",
    "それ以外のレースの3着以内率", "それ以外のレースの集まり方", "集まり方の差",
)


class HorseCaseReport:
    """人気薄（6番人気以下）だけを取り出し、切り口の値ごとに3着以内率と集まり方を、荒れたレースとそれ以外のレースで並べる。

    荒れたレース = 3連単の払戻が 10万円以上（帯と大荒れ）。「集まり方の差」が大きい値ほど、荒れたレースでだけ来やすい人気薄の型である。
    """

    def __init__(self, lift: LiftTable | None = None) -> None:
        self._lift = lift or LiftTable(IN_TOP3)

    def lines(self, frame: pd.DataFrame) -> list[str]:
        longshots = frame[frame[POPULARITY].ge(LONGSHOT_FROM_POPULARITY)]
        wild = longshots[PAYOUT_CLASS].isin([OBI, BIG])
        lines = self._summary(longshots, wild)
        for title, columns in LIFT_COLUMNS.items():
            lines += [f"## 切り口: {title}", ""]
            lines += [part for column in columns for part in self._section(longshots, wild, column)]
        return lines

    def _summary(self, longshots: pd.DataFrame, wild: pd.Series) -> list[str]:
        table = longshots.groupby(PAYOUT_CLASS)[IN_TOP3].agg(人気薄の頭数="size", 三着以内="sum")
        table["3着以内率"] = (table["三着以内"] / table["人気薄の頭数"]).round(4)
        races = longshots[wild].groupby(PAYOUT_CLASS)["レースID"].nunique().rename("レース")
        return ["## 払戻の段ごとの人気薄の3着以内", "", table.join(races).to_markdown(), ""]

    def _section(self, longshots: pd.DataFrame, wild: pd.Series, column: str) -> list[str]:
        if column not in longshots.columns:
            return []
        # 分位の区切りは人気薄の全体で1回だけ決め、荒れたレースとそれ以外を同じ区切りで比べる
        labeled = longshots.assign(**{column: self._lift.labels(longshots[column])})
        in_wild = self._lift.table(labeled[wild], column)
        usual = self._lift.table(labeled[~wild], column)
        table = pd.DataFrame({
            WILD_COUNT: in_wild[COUNT], WILD_RATE: in_wild[RATE], WILD_LIFT: in_wild[LIFT],
            USUAL_RATE: usual[RATE], USUAL_LIFT: usual[LIFT],
        }).dropna(subset=[WILD_COUNT])
        table[GAP] = table[WILD_LIFT] - table[USUAL_LIFT]
        return [f"### {column}", "", table.round(4).to_markdown(), ""]
