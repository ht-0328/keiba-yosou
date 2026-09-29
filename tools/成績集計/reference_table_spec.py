"""基準のページの節（コース×馬場状態）に置く表の決まり。"""

from __future__ import annotations

from dataclasses import dataclass

#: 騎手・調教師を勝率で並べるときの件数と、要る出走数（少ないと率が極端になりやすい）。
RANKED_TOP, RANKED_MIN_RUNS = 10, 5


@dataclass(frozen=True)
class ReferenceTableSpec:
    """節の中の1つの表。``title`` は見出し、``label`` は先頭の列の名前、``column`` は ``ReferenceRuns`` の列。

    ``ranked`` なら、出走 ``RANKED_MIN_RUNS`` 以上の値のうち勝率の上位 ``RANKED_TOP`` 件だけ出す。
    """

    title: str
    label: str
    column: str
    ranked: bool = False


#: 各節に置く表。答え合わせ（``check.py``）は「単勝人気」の表の「1」の行を読む。
SECTION_TABLES: tuple[ReferenceTableSpec, ...] = (
    ReferenceTableSpec("単勝人気", "単勝人気", "popularity"),
    ReferenceTableSpec("単勝オッズ", "単勝オッズ", "odds_band"),
    ReferenceTableSpec("枠番", "枠番", "frame_no"),
    ReferenceTableSpec("馬番", "馬番", "horse_no"),
    ReferenceTableSpec("性別（牡牝が混ざったレースだけ）", "性別", "mixed_sex"),
    ReferenceTableSpec("馬齢（年齢が混ざったレースだけ）", "馬齢", "mixed_age"),
    ReferenceTableSpec(f"騎手（勝率の上位 {RANKED_TOP}・出走 {RANKED_MIN_RUNS} 以上）", "騎手", "jockey", ranked=True),
    ReferenceTableSpec(f"調教師（勝率の上位 {RANKED_TOP}・出走 {RANKED_MIN_RUNS} 以上）", "調教師", "trainer", ranked=True),
)
