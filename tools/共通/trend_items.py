"""傾向スコアの点数化項目の登録簿。一覧の説明は ``tools/傾向スコア/score-items.md``。

言葉:

- 要因（``Factor``）: 成績を分ける切り口（``perf.DIMENSIONS`` の名前。2つ以上なら掛け合わせ）と、当てはめる馬の範囲（対象）の組。
  要因1つから、プラス要素（``P09``）とマイナス要素（``M09``）の2つの項目ができる。番号は一覧の ID と同じ。
- 対象（``Target``）: 全馬・穴馬（6番人気以下）・人気馬（1〜3番人気）。基準値も対象の馬だけの率にする。
- 無条件の項目（``FixedItem``）: 過去の成績を見ずに、当てはまれば加点・減点する項目。同レースの実績だけ。

どの値が良い・悪いかはここに書かない。コースごとの過去の成績が決める（``trend.classify``）。
"""

from __future__ import annotations

from dataclasses import dataclass

from . import perf

#: 項目のグループ（一覧の節の番号と名前）。
GROUPS: dict[int, str] = {
    1: "枠・馬番", 2: "脚質・位置取り", 3: "同レース・同コースの実績", 4: "騎手・調教師", 5: "血統",
    6: "前走・ローテーション", 7: "馬の属性", 8: "穴馬が来る型", 9: "人気馬の型",
}
PLUS, MINUS = 1, -1
#: 穴馬・人気馬の境目（単勝人気）。
LONGSHOT_MIN_POPULARITY = 6
FAVORITE_MAX_POPULARITY = 3


@dataclass(frozen=True)
class Target:
    """項目を当てはめる馬の範囲。``where_sql`` は事実表の列を使った条件で、過去の集計にも当日の馬にも同じ式を当てる。"""

    key: str
    title: str
    where_sql: str
    needs: frozenset[str] = frozenset()


ALL = Target("all", "全馬", "TRUE")
LONGSHOT = Target("longshot", f"穴馬（{LONGSHOT_MIN_POPULARITY}番人気以下）", f"popularity >= {LONGSHOT_MIN_POPULARITY}",
                  frozenset({perf.NEED_POPULARITY}))
FAVORITE = Target("favorite", f"人気馬（1〜{FAVORITE_MAX_POPULARITY}番人気）", f"popularity BETWEEN 1 AND {FAVORITE_MAX_POPULARITY}",
                  frozenset({perf.NEED_POPULARITY}))
TARGETS: dict[str, Target] = {target.key: target for target in (ALL, LONGSHOT, FAVORITE)}


@dataclass(frozen=True)
class Factor:
    """要因。``dims`` は切り口の名前の並び（2つ以上なら掛け合わせ）。"""

    no: int
    group: int
    title: str
    dims: tuple[str, ...]
    target: Target = ALL
    plus: bool = True
    minus: bool = True

    @property
    def key(self) -> str:
        """同じ集計を使い回すための鍵（切り口の組 + 対象）。"""
        return "+".join(self.dims) + "@" + self.target.key

    def item_id(self, sign: int) -> str:
        return f"{'P' if sign == PLUS else 'M'}{self.no:02d}"

    def signs(self) -> tuple[int, ...]:
        return tuple(sign for sign, enabled in ((PLUS, self.plus), (MINUS, self.minus)) if enabled)

    def dimension(self) -> perf.Dimension:
        """切り口（掛け合わせ済み）。"""
        dimensions = [perf.dimension(name) for name in self.dims]
        return dimensions[0] if len(dimensions) == 1 else perf.cross(*dimensions)

    def needs(self) -> frozenset[str]:
        """当日の馬に当てはめるのに要る材料。"""
        return self.dimension().needs | self.target.needs


@dataclass(frozen=True)
class FixedItem:
    """無条件の項目。``applies_sql`` は当日の馬の行（``entry_facts``）に当てる条件。"""

    id: str
    sign: int
    group: int
    title: str
    applies_sql: str


def _all(no: int, group: int, title: str, *dims: str) -> Factor:
    return Factor(no, group, title, dims)


def _longshot(no: int, title: str, *dims: str) -> Factor:
    """穴馬が来る型。悪い側は項目にしない（穴馬はもともと来にくい）。"""
    return Factor(no, 8, f"穴馬×{title}", dims, target=LONGSHOT, minus=False)


def _favorite(no: int, title: str, *dims: str) -> Factor:
    """人気馬の型。良い側 = 信頼できる人気馬、悪い側 = 危険な人気馬。"""
    return Factor(no, 9, f"人気馬×{title}", dims, target=FAVORITE)


#: 要因の目録。番号は ``score-items.md`` の ID（P01 / M01 …）と同じ。
FACTORS: tuple[Factor, ...] = (
    # 1. 枠・馬番
    _all(1, 1, "枠番", "frame"),
    _all(2, 1, "枠帯", "frame-band"),
    _all(3, 1, "馬番", "number"),
    _all(4, 1, "馬番の偶数・奇数", "number-parity"),
    _all(5, 1, "最内・大外", "gate-edge"),
    _all(6, 1, "頭数帯×枠帯", "field-size", "frame-band"),
    # 2. 脚質・位置取り
    _all(7, 2, "推定脚質", "style-before"),
    _all(8, 2, "前後", "style-side"),
    _all(9, 2, "枠帯×前後", "frame-band", "style-side"),
    _all(10, 2, "枠帯×推定脚質", "frame-band", "style-before"),
    _all(11, 2, "逃げ候補の数×推定脚質", "lead-candidates", "style-before"),
    _all(12, 2, "頭数帯×前後", "field-size", "style-side"),
    _all(13, 2, "前走の4角位置", "prev-corner4"),
    _all(14, 2, "前走の脚質", "prev-style"),
    _all(15, 2, "逃げ経験", "lead-exp"),
    _all(16, 2, "前走の上がり順位", "prev-last3f-rank"),
    _all(17, 2, "前後×前走の上がり順位", "style-side", "prev-last3f-rank"),
    _all(18, 2, "距離の変更×前後", "distance-change", "style-side"),
    # 3. 同レース・同コースの実績（19・20 は無条件の項目）
    _all(21, 3, "同コースの勝利経験", "course-win"),
    _all(22, 3, "同コースの実績", "course-place"),
    _all(23, 3, "同コースの出走回数", "course-runs"),
    _all(24, 3, "同じ競馬場の勝利経験", "venue-win"),
    _all(25, 3, "同じ距離の勝利経験", "dist-win"),
    _all(26, 3, "同じ馬場状態の3着内経験", "cond-place"),
    _all(27, 3, "持ち時計の順位（同コース・同馬場）", "best-time-rank"),
    _all(28, 3, "持ち時計の順位（同距離・同馬場）", "best-time-dist-rank"),
    _all(29, 3, "キャリア", "runs-before"),
    _all(30, 3, "通算勝利数", "wins-before"),
    # 4. 騎手・調教師
    _all(31, 4, "騎手", "jockey"),
    _all(32, 4, "調教師", "trainer"),
    _all(33, 4, "騎手×調教師", "jockey", "trainer"),
    _all(34, 4, "乗り替わり", "jockey-change"),
    _all(35, 4, "騎手×前後", "jockey", "style-side"),
    _all(36, 4, "騎手×枠帯", "jockey", "frame-band"),
    _all(37, 4, "所属", "affiliation"),
    _all(38, 4, "減量騎手", "apprentice"),
    # 5. 血統
    _all(39, 5, "父", "sire"),
    _all(40, 5, "母父", "damsire"),
    _all(41, 5, "父の父", "grandsire"),
    _all(42, 5, "父×前後", "sire", "style-side"),
    # 6. 前走・ローテーション
    _all(43, 6, "間隔", "interval"),
    _all(44, 6, "前走の着順", "prev-finish"),
    _all(45, 6, "前走の着差", "prev-margin"),
    _all(46, 6, "前走の人気", "prev-popularity"),
    _all(47, 6, "前走の人気×前走の着順", "prev-popularity", "prev-finish"),
    _all(48, 6, "距離の変更", "distance-change"),
    _all(49, 6, "芝ダ替わり", "surface-change"),
    _all(50, 6, "クラスの変更", "class-change"),
    _all(51, 6, "前走と同じ競馬場か", "venue-change"),
    _all(52, 6, "前走の競馬場", "prev-venue"),
    _all(53, 6, "前走の距離", "prev-distance"),
    _all(54, 6, "前走の頭数", "prev-field"),
    _all(55, 6, "前走の上がり3Fタイム", "prev-last3f"),
    _all(56, 6, "クラスの変更×前走の着順", "class-change", "prev-finish"),
    _all(57, 6, "間隔×前走の着順", "interval", "prev-finish"),
    # 7. 馬の属性
    _all(58, 7, "性別", "sex"),
    _all(59, 7, "馬齢", "age"),
    _all(60, 7, "斤量", "carried"),
    _all(61, 7, "ブリンカー", "blinker"),
    _all(62, 7, "馬体重", "body-weight"),
    _all(63, 7, "馬体重の増減", "weight-change"),
    # 8. 穴馬が来る型
    _longshot(70, "枠帯", "frame-band"),
    _longshot(71, "前後", "style-side"),
    _longshot(72, "枠帯×前後", "frame-band", "style-side"),
    _longshot(73, "前走の着順", "prev-finish"),
    _longshot(74, "前走の着差", "prev-margin"),
    _longshot(75, "同コースの実績", "course-place"),
    _longshot(76, "距離の変更", "distance-change"),
    _longshot(77, "騎手", "jockey"),
    _longshot(78, "間隔", "interval"),
    _longshot(79, "クラスの変更", "class-change"),
    _longshot(80, "持ち時計の順位", "best-time-dist-rank"),
    _longshot(81, "前走の人気", "prev-popularity"),
    _longshot(82, "父", "sire"),
    # 9. 人気馬の型（良い側 = 信頼できる人気馬、悪い側 = 危険な人気馬）
    _favorite(83, "枠帯", "frame-band"),
    _favorite(84, "前後", "style-side"),
    _favorite(85, "枠帯×前後", "frame-band", "style-side"),
    _favorite(86, "同コースの勝利経験", "course-win"),
    _favorite(87, "前走の着順", "prev-finish"),
    _favorite(88, "間隔", "interval"),
    _favorite(89, "乗り替わり", "jockey-change"),
    _favorite(90, "クラスの変更", "class-change"),
    _favorite(91, "距離の変更", "distance-change"),
    _favorite(92, "持ち時計の順位", "best-time-dist-rank"),
    _favorite(93, "前走の人気", "prev-popularity"),
    _favorite(94, "キャリア", "runs-before"),
    _favorite(95, "馬体重の増減", "weight-change"),
)

#: 無条件の項目。同レースは過去の開催が少なく（2016年からでも最大 10回あまり）、成績で判定するには出走数が足りないため。
FIXED_ITEMS: tuple[FixedItem, ...] = (
    FixedItem("P19", PLUS, 3, "同レースで勝ったことがある", "same_race_wins_before >= 1"),
    FixedItem("P20", PLUS, 3, "同レースで3着内に来たことがある（勝ちは無い）", "same_race_wins_before = 0 AND same_race_places_before >= 1"),
    FixedItem("M19", MINUS, 3, "同レースに出て着外だけ", "same_race_runs_before >= 1 AND same_race_places_before = 0"),
)


def validate(factors: tuple[Factor, ...] = FACTORS, fixed: tuple[FixedItem, ...] = FIXED_ITEMS) -> None:
    """登録簿の誤りを見つける。番号の重複、知らない切り口、レース後にしか分からない切り口。"""
    ids = [factor.item_id(sign) for factor in factors for sign in factor.signs()] + [item.id for item in fixed]
    duplicated = sorted({item_id for item_id in ids if ids.count(item_id) > 1})
    if duplicated:
        raise ValueError(f"項目の ID が重なっています: {', '.join(duplicated)}")
    for factor in factors:
        if factor.group not in GROUPS:
            raise ValueError(f"知らないグループです: {factor.group}（{factor.title}）")
        if perf.NEED_RESULT in factor.needs():  # perf.dimension が知らない切り口を落とす
            raise ValueError(f"レースが終わってから分かる切り口は項目にできません: {factor.title}")
        for name in factor.dims:
            dimension = perf.dimension(name)
            if len(dimension.columns) != 1 or len(dimension.order_sql) != 1:  # 採点は「切り口1つ = 値1列」を前提に集計する
                raise ValueError(f"項目に使える切り口は1列のものだけです: {name}（{factor.title}）")


def item_count() -> dict[int, int]:
    """プラス要素とマイナス要素の数。"""
    signs = [sign for factor in FACTORS for sign in factor.signs()] + [item.sign for item in FIXED_ITEMS]
    return {PLUS: signs.count(PLUS), MINUS: signs.count(MINUS)}
