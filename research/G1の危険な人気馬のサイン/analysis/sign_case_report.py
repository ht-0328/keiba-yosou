"""G1の人気馬で、サインごと・サインの数ごとの成績を数える表（事例の表）。"""

from __future__ import annotations

import pandas as pd

from 共通.render import Table

from .g1_favorites import LOST, G1Favorites
from .sign_columns import SIGN_COLUMNS, SIGN_COUNT

#: 前半・後半の境（後半は、モデルの比べのテスト期間と同じ 2020年から）。
_SECOND_HALF_FROM = 2020
#: サインの数の帯の上限（これ以上はまとめる）。
_COUNT_CAP = 3


class SignCaseReport:
    """G1の人気馬（``G1Favorites``）で、サインに当てはまる馬が、同じ人気の馬よりどれだけ負けたかを数える。

    「同じ人気から見た4着以下率」は、G1の人気馬全体での、人気（1〜5番人気）ごとの4着以下率を、その馬たちの人気の並びで平均したもの。
    サイン10 は2・3番人気だけに付くように、サインごとに人気の混ざり方が違うので、4着以下率そのものでなく、この差で比べる。
    回収率は、その馬の単勝・複勝を 100円ずつ買い続けたときのもの（消す側のサインなら、低いほどよい）。
    """

    def tables(self, signs: pd.DataFrame) -> list[Table]:
        rows = G1Favorites().select(signs)
        rows["expected"] = rows.groupby("popularity")[LOST].transform("mean")
        return [self._scope(rows), self._signs(rows), self._count(rows), self._first_favorite(rows)]

    def _scope(self, rows: pd.DataFrame) -> Table:
        record = {
            "期間": f"{rows['year'].min()}〜{rows['year'].max()}年", "レース数": rows["race_id"].nunique(), "人気馬の頭数": len(rows),
            "4着以下率": _rate(rows[LOST].mean()), "単勝回収率": _roi(rows["win_payout"]), "複勝回収率": _roi(rows["place_payout"]),
        }
        return Table.from_records([record], title="1. 対象（平地の G1 の人気馬。13頭以下は1〜3番人気、14頭以上は1〜5番人気）")

    def _signs(self, rows: pd.DataFrame) -> Table:
        later = rows["year"].ge(_SECOND_HALF_FROM)
        records = []
        for sign in SIGN_COLUMNS:
            hit = rows[sign].eq(1)
            records.append({
                "サイン": sign, **self._measures(rows[hit]),
                "当てはまらない馬の差": _points(rows.loc[~hit, LOST].mean() - rows.loc[~hit, "expected"].mean()),
                "差（2012〜2019年）": _gap(rows[hit & ~later]), "差（2020年〜）": _gap(rows[hit & later]),
            })
        return Table.from_records(records, title="2. サインごとの成績（サインに当てはまる人気馬）",
                                  note="差 = 4着以下率 − 同じ人気から見た4着以下率（ポイント）。プラスほど、同じ人気の馬より負けた。")

    def _count(self, rows: pd.DataFrame) -> Table:
        band = rows[SIGN_COUNT].clip(upper=_COUNT_CAP)
        records = [{"サインの数": f"{count}" + ("以上" if count == _COUNT_CAP else ""), **self._measures(rows[band.eq(count)]),
                    "差（2012〜2019年）": _gap(rows[band.eq(count) & rows["year"].lt(_SECOND_HALF_FROM)]),
                    "差（2020年〜）": _gap(rows[band.eq(count) & rows["year"].ge(_SECOND_HALF_FROM)])}
                   for count in range(_COUNT_CAP + 1)]
        return Table.from_records(records, title="3. サインの数ごとの成績")

    def _first_favorite(self, rows: pd.DataFrame) -> Table:
        first = rows[rows["popularity"].eq(1)]
        records = [{"サイン": sign, **self._measures(first[first[sign].eq(1)])} for sign in SIGN_COLUMNS]
        records.append({"サイン": "（1番人気の全体）", **self._measures(first)})
        return Table.from_records(records, title="4. 1番人気だけで見たサインごとの成績（消は1番人気を優先するため）")

    def _measures(self, part: pd.DataFrame) -> dict[str, object]:
        return {
            "頭数": len(part), "4着以下率": _rate(part[LOST].mean()), "同じ人気から見た4着以下率": _rate(part["expected"].mean()),
            "差": _gap(part), "単勝回収率": _roi(part["win_payout"]), "複勝回収率": _roi(part["place_payout"]),
        }


def _gap(part: pd.DataFrame) -> str:
    return _points(part[LOST].mean() - part["expected"].mean()) if len(part) else "-"


def _rate(value: float) -> str:
    return "-" if pd.isna(value) else f"{value:.1%}"


def _points(value: float) -> str:
    return "-" if pd.isna(value) else f"{value * 100:+.1f}"


def _roi(payout: pd.Series) -> str:
    return "-" if payout.empty else f"{payout.sum() / (100 * len(payout)):.0%}"
