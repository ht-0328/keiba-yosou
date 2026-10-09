"""1つの重賞の「攻略ポイント」のページ（Markdown）を組み立てる。

ページの狙いは、**どのレースでも成り立つ一般論ではなく、そのレースならではのずれ**を出すこと。
1番人気や前に行く馬が走るのはどのレースでも同じなので、必ず基準（同じグレードの重賞全体、
同じコースの全クラス、またはそのレースの中のほかの馬）と比べ、ずれの大きさと検定の印を添える。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from 共通 import distance_change
from 共通.distance_change_verdict import SHOWN_CHANGES, DistanceChangeVerdict, Verdict
from 共通.render import Table, to_markdown

from . import stats
from .loading import NO_PREV, NO_PREV_NAME
from .stats import BAND_COLUMNS, BandResult

#: 自動要約に載せる線。検定の p 値と、最低の出走数。
SUMMARY_P = 0.10
SUMMARY_MIN_RUNS = 12
#: 回収率で自動要約に載せる線（過去に合わせすぎの注意付きで載せる）。
ROI_MIN_RUNS = 30
PLACE_ROI_LINE = 110.0
WIN_ROI_LINE = 150.0

#: 切り口ごとの持続性の注意（2011〜2018 と 2019〜2026 のずれの相関による。調査は reports/重賞攻略/ を参照）。
_PERSISTENT = "年をまたいで持続しやすい切り口"
_UNSTABLE = "年ごとの入れ替わりが大きい切り口（参考程度）"
PERSISTENCE: dict[str, str] = {
    "人気": _PERSISTENT, "脚質": _PERSISTENT, "枠": _PERSISTENT,
    "ローテ": _UNSTABLE, "属性": _UNSTABLE, "経験": _UNSTABLE, "荒れ度": _UNSTABLE,
    "距離": _UNSTABLE,
}
#: 距離の変更の帯（表の名前・事実表の値）。
_DISTANCE_BANDS: tuple[tuple[str, str], ...] = (
    ("距離短縮", distance_change.SHORTER), ("同じ距離", distance_change.SAME), ("距離延長", distance_change.LONGER),
)


@dataclass
class Finding:
    """自動要約の1項目。"""

    section: str
    text: str
    p_value: float

    def line(self) -> str:
        return f"- 【{self.section}】{self.text}"


@dataclass
class StakesPage:
    """1つの重賞のページ。``markdown`` が本文、``findings`` は一覧（索引ページにも使う）。"""

    stakes_no: str
    stakes_name: str
    grade: str
    venue: str
    course: str
    distance_m: int
    editions: int
    markdown: str = ""
    findings: list[Finding] = field(default_factory=list)
    #: 短縮と延長のどちらが有利か（勝つ・穴馬の好走）。索引に使う。
    distance_win: str = ""
    distance_longshot: str = ""

    @property
    def file_name(self) -> str:
        grade_name = {"A": "G1", "B": "G2", "C": "G3"}.get(self.grade, self.grade)
        safe = "".join(ch for ch in self.stakes_name if ch not in '\\/:*?"<>|').strip() or self.stakes_no
        return f"{grade_name}-{safe}.md"


def build_page(race_rows: pd.DataFrame, grade_rows: pd.DataFrame,
               course_rates: pd.Series | None) -> StakesPage:
    """1つの重賞のページを組み立てる。

    - ``race_rows``: その重賞の出走の行（全開催）。
    - ``grade_rows``: 同じグレードの重賞全体の出走の行（人気の基準に使う）。
    - ``course_rates``: そのレースのコースの全クラスの基準
      （``front_rate``・``inner_rate``。コースの行が無ければ None）。
    """
    last = race_rows.loc[race_rows["race_date"].idxmax()]
    page = StakesPage(
        stakes_no=str(last["stakes_no"]), stakes_name=str(last["stakes_name"]), grade=str(last["grade"]),
        venue=str(last["venue"]), course=str(last["course"]), distance_m=int(last["distance_m"]),
        editions=int(race_rows["race_id"].nunique()),
    )
    sections: list[str] = []
    sections.append(_editions_section(race_rows))
    sections.append(_popularity_section(page, race_rows, grade_rows))
    sections.append(_style_section(page, race_rows, course_rates))
    sections.append(_frame_section(page, race_rows, course_rates))
    sections.append(_rotation_section(page, race_rows))
    sections.append(_distance_section(page, race_rows, grade_rows))
    sections.append(_attribute_section(page, race_rows))
    sections.append(_repeat_section(page, race_rows))
    sections.append(_upset_section(page, race_rows, grade_rows))
    page.markdown = "\n\n".join([_header(page, race_rows), _summary_section(page), *sections]) + "\n"
    return page


def _header(page: StakesPage, race_rows: pd.DataFrame) -> str:
    grade_name = {"A": "G1", "B": "G2", "C": "G3"}.get(page.grade, page.grade)
    period = f"{int(race_rows['year'].min())}〜{int(race_rows['year'].max())}年"
    lines = [
        f"# {page.stakes_name}（{grade_name}）の攻略ポイント",
        "",
        f"- 条件: {page.venue} {page.course} {page.distance_m}m（いちばん新しい開催のもの）",
        f"- 対象: {period} の {page.editions} 開催、のべ {len(race_rows)} 頭",
        "- 「基準の複勝率」は、人気は同じグレードの重賞全体、脚質の前・枠の内はこのコースの全クラス、"
        "距離の変更は同じグレードの重賞の同じ距離の変更の馬、それ以外はこのレースのほかの出走馬。判定は ◎ = p<0.05、○ = p<0.10（そのずれが偶然出る確率）",
    ]
    names = race_rows.groupby("stakes_name")["year"].max().sort_values(ascending=False)
    if len(names) > 1:
        olds = "・".join(str(name) for name in names.index[1:])
        lines.append(f"- 名前の変わった同じレースを含む（旧: {olds}）")
    return "\n".join(lines)


def _summary_section(page: StakesPage) -> str:
    lines = ["## 攻略ポイント（自動の要約）", ""]
    if page.findings:
        page.findings.sort(key=lambda f: f.p_value)
        lines.extend(finding.line() for finding in page.findings)
    else:
        lines.append("- 基準からの有意なずれは見つからなかった（このレースは平均的な重賞として扱う）")
    lines += [
        "",
        f"> 持続性の注意: 人気・脚質・枠のずれは{_PERSISTENT.replace('切り口', '')}、"
        f"ローテ・属性・経験・荒れ度のずれは{_UNSTABLE.replace('切り口', '')}である"
        "（2011〜2018年と2019〜2026年で相関を検証。前後半の相関は 前 0.49・内枠 0.30・上位人気 0.27、"
        "荒れ度・二桁人気は 0.16 以下）。距離の変更（短縮と延長のどちらが有利か）も、2011〜2018年と2019〜2026年で"
        "重賞ごとの向きがそろわず、年をまたいで続いていなかった（参考程度）。全コースを合わせると、延長の穴馬は人気ほど走らない"
        "傾向がどの期間でも続いている（基礎統計の目次の「3. 延長と短縮のどちらが有利か」）。",
    ]
    return "\n".join(lines)


def _editions_section(race_rows: pd.DataFrame) -> str:
    rows = []
    for race_id, group in sorted(race_rows.groupby("race_id"), reverse=True):
        winner = group[group["finish"] == 1]
        favorite = group[group["popularity"] == 1]
        placed = group[group["finish"] <= 3].sort_values("finish")
        rows.append([
            str(group["race_date"].iloc[0])[:10], group["condition"].iloc[0], len(group),
            f"{winner['horse_name'].iloc[0]}（{int(winner['popularity'].iloc[0])}人気）" if len(winner) else "―",
            _favorite_finish(favorite),
            "-".join(str(int(p)) for p in placed["popularity"] if pd.notna(p)),
        ])
    table = Table(columns=["開催日", "馬場", "頭数", "勝ち馬", "1番人気の着順", "3着内の人気"], rows=rows)
    return "## 過去の開催\n\n" + to_markdown(table).rstrip()


def _favorite_finish(favorite: pd.DataFrame) -> str:
    if len(favorite) == 0:
        return "―"
    finish = favorite["finish"].iloc[0]
    return f"{int(finish)}着" if pd.notna(finish) else "中止・失格"


def _popularity_section(page: StakesPage, race_rows: pd.DataFrame, grade_rows: pd.DataFrame) -> str:
    bands = [("1番人気", 1, 1), ("2〜3番人気", 2, 3), ("4〜6番人気", 4, 6),
             ("7〜9番人気", 7, 9), ("10番人気以下", 10, 99)]
    results = []
    for label, low, high in bands:
        rows = race_rows[race_rows["popularity"].between(low, high)]
        base = grade_rows[grade_rows["popularity"].between(low, high)]
        base_rate = float((base["finish"] <= 3).mean()) if len(base) else None
        results.append(stats.against_base(label, rows, base_rate))
    _collect(page, "人気", results, texts={
        "1番人気": ("1番人気が基準より強い（実力どおり決まりやすい）", "1番人気が基準より弱い（疑う価値がある）"),
        "2〜3番人気": ("2〜3番人気が基準より強い", "2〜3番人気が基準より弱い"),
        "4〜6番人気": ("4〜6番人気が基準より走る", "4〜6番人気が基準より走らない"),
        "7〜9番人気": ("7〜9番人気が基準より走る", "7〜9番人気が基準より走らない"),
        "10番人気以下": ("10番人気以下が基準より走る", "10番人気以下が基準より走らない"),
    })
    return _band_table("## 人気の信頼度（基準: 同じグレードの重賞全体）", results)


def _style_section(page: StakesPage, race_rows: pd.DataFrame, course_rates: pd.Series | None) -> str:
    front_label = "前に行った馬（脚質判定が逃げ・先行）"
    front = race_rows[race_rows["style"].isin(["逃げ", "先行"])]
    front_base = _adjusted_base(course_rates, "front_excess", front)
    results = [stats.against_base(front_label, front, front_base)]
    for style in ("逃げ", "先行", "差し", "追込"):
        rows = race_rows[race_rows["style"] == style]
        if len(rows) == 0:
            continue
        rest = race_rows[race_rows["style"].notna() & (race_rows["style"] != style)]
        results.append(stats.against_rest(f"脚質判定が{style}", rows, rest))
    for style in ("逃げ", "先行", "差し", "追込"):
        rows = race_rows[race_rows["style_before"] == style]
        if len(rows) == 0:
            continue
        rest = race_rows[race_rows["style_before"].notna() & (race_rows["style_before"] != style)]
        results.append(stats.against_rest(f"推定脚質が{style}", rows, rest))
    _collect(page, "脚質", results[:1], texts={
        front_label: ("前に行く馬がこのコースの平均より走る（先行有利）",
                      "前に行く馬がこのコースの平均より走らない（先行不利）"),
    })
    _collect(page, "脚質", [r for r in results[1:] if r.label.startswith("推定脚質")])
    return _band_table("## 脚質（前の基準: このコースの全クラス。推定脚質はレース前に分かる側）", results)


def _frame_section(page: StakesPage, race_rows: pd.DataFrame, course_rates: pd.Series | None) -> str:
    inner = race_rows[race_rows["frame_no"] <= 3]
    inner_base = _adjusted_base(course_rates, "inner_excess", inner)
    results = [stats.against_base("内枠（1〜3枠）", inner, inner_base)]
    for label, low, high in [("中枠（4〜6枠）", 4, 6), ("外枠（7〜8枠）", 7, 8)]:
        rows = race_rows[race_rows["frame_no"].between(low, high)]
        rest = race_rows[~race_rows.index.isin(rows.index)]
        results.append(stats.against_rest(label, rows, rest))
    _collect(page, "枠", results[:1], texts={
        "内枠（1〜3枠）": ("内枠がこのコースの平均より有利", "内枠がこのコースの平均より不利"),
    })
    _collect(page, "枠", results[1:])
    return _band_table("## 枠（内枠の基準: このコースの全クラス）", results)


def _adjusted_base(course_rates: pd.Series | None, column: str, rows: pd.DataFrame) -> float | None:
    """コース基準の複勝率を、そのレースの頭数に合わせた値にする。

    コースの全クラスの基準は少頭数のレースを含み、複勝率（3着内率）は頭数が少ないほど高く出る。
    そこで基準は「超過複勝率」（3着内率 − 3÷頭数）で持ち、このレースの側の期待複勝率
    （3÷頭数の平均）を足し戻して比べる。
    """
    if course_rates is None or len(rows) == 0:
        return None
    expected = float((3.0 / rows["field_size"]).mean())
    return float(course_rates[column]) + expected


def _rotation_section(page: StakesPage, race_rows: pd.DataFrame) -> str:
    results = []
    for label, low, high in [("間隔が中2週以内", 0, 21), ("中3〜8週", 22, 62), ("休み明け（中9週以上）", 63, 9999)]:
        rows = race_rows[race_rows["interval_days"].between(low, high)]
        rest = race_rows[race_rows["interval_days"].notna() & ~race_rows.index.isin(rows.index)]
        results.append(stats.against_rest(label, rows, rest))
    prev = race_rows["prev_race_name"].map(_prev_label)
    counts = prev.value_counts()
    for name in counts.index:
        if counts[name] < 8:
            continue
        rows = race_rows[prev == name]
        rest = race_rows[prev != name]
        results.append(stats.against_rest(f"前走が{name}", rows, rest))
    _collect(page, "ローテ", results)
    return _band_table("## ローテ（基準: このレースのほかの出走馬）", results)


def _distance_section(page: StakesPage, race_rows: pd.DataFrame, grade_rows: pd.DataFrame) -> str:
    """距離短縮・同じ距離・距離延長の成績（基準: 同じグレードの重賞の、同じ距離の変更の馬）と、短縮と延長のどちらが有利か。"""
    longshot_line = distance_change.LONGSHOT_MIN_POPULARITY
    results = []
    for longshot in (False, True):
        for label, change in _DISTANCE_BANDS:
            rows, base = (frame[frame["distance_change"] == change] for frame in (race_rows, grade_rows))
            if longshot:
                rows, base = (frame[frame["popularity"] >= longshot_line] for frame in (rows, base))
                label = f"{label}の穴馬（{longshot_line}番人気以下）"
            base_rate = float((base["finish"] <= 3).mean()) if len(base) else None
            results.append(stats.against_base(label, rows, base_rate))
    _collect(page, "距離", results)
    runs, base = _with_outcomes(race_rows), _with_outcomes(grade_rows)
    verdicts = (("勝つ（勝率）", DistanceChangeVerdict().win(runs, base)),
                ("穴馬の好走（複勝率）", DistanceChangeVerdict().longshot(runs, base)))
    page.distance_win, page.distance_longshot = (verdict.winner for _, verdict in verdicts)
    for name, verdict in verdicts:
        _collect_verdict(page, name, verdict)
    lines = [_band_table("## 距離の変更（基準: 同じグレードの重賞の、同じ距離の変更の馬）", results), "",
             "**短縮と延長のどちらが有利か。** 前走より距離が短い馬（短縮）と長い馬（延長）を、このレースの全開催で比べたもの。"
             "かっこの中は人気から見た差（同じグレードの重賞で同じ人気の馬がふつう出す率との差）。"
             "有利なほうは、短縮と延長の人気から見た差の違いが検定で 5%（1%）の線を超えたときだけ書く。", "",
             "| 見るもの | " + " | ".join(SHOWN_CHANGES) + " | 有利なほう |", "|" + " :--- |" * (len(SHOWN_CHANGES) + 2)]
    lines.extend(f"| {name} | " + " | ".join(verdict.results[change].text() for change in SHOWN_CHANGES)
                 + f" | {verdict.winner} |" for name, verdict in verdicts)
    return "\n".join(lines)


def _with_outcomes(rows: pd.DataFrame) -> pd.DataFrame:
    """判定（``DistanceChangeVerdict``）が読む列（距離の変更・1着・2着・3着）を付ける。"""
    finish = pd.to_numeric(rows["finish"], errors="coerce")
    return rows.assign(label_distance_change=rows["distance_change"], first=finish.eq(1), second=finish.eq(2), third=finish.eq(3))


def _collect_verdict(page: StakesPage, name: str, verdict: Verdict) -> None:
    """短縮か延長が有利と判定できたら、自動要約に載せる。"""
    side = verdict.favored
    if side is None or verdict.p_value is None:
        return
    other = distance_change.LONGER if side == distance_change.SHORTER else distance_change.SHORTER
    favored, rest = verdict.results[side], verdict.results[other]
    page.findings.append(Finding(
        section="距離", p_value=verdict.p_value,
        text=f"{name}は{verdict.winner} — {side} {favored.text()}、{other} {rest.text()}（かっこは人気から見た差）"))


def _prev_label(name: object) -> str:
    if pd.isna(name):
        return NO_PREV
    text = str(name).strip()
    return text if text else NO_PREV_NAME


def _attribute_section(page: StakesPage, race_rows: pd.DataFrame) -> str:
    results = []
    for label, low, high in [("3歳", 3, 3), ("4歳", 4, 4), ("5歳", 5, 5), ("6歳以上", 6, 99)]:
        rows = race_rows[race_rows["age"].between(low, high)]
        if len(rows) == 0:
            continue
        results.append(stats.against_rest(label, rows, race_rows[~race_rows.index.isin(rows.index)]))
    for sex in ("牡", "牝", "セン"):
        rows = race_rows[race_rows["sex"] == sex]
        if len(rows) == 0:
            continue
        results.append(stats.against_rest(sex, rows, race_rows[race_rows["sex"] != sex]))
    for area in ("美浦", "栗東"):
        rows = race_rows[race_rows["affiliation"] == area]
        if len(rows) == 0:
            continue
        results.append(stats.against_rest(area, rows, race_rows[race_rows["affiliation"] != area]))
    _collect(page, "属性", results)
    return _band_table("## 属性（基準: このレースのほかの出走馬）", results)


def _repeat_section(page: StakesPage, race_rows: pd.DataFrame) -> str:
    experienced = race_rows[race_rows["same_race_places_before"] >= 1]
    rest = race_rows[~race_rows.index.isin(experienced.index)]
    results = [stats.against_rest("このレースで3着以内の経験あり", experienced, rest),
               stats.against_rest("経験なし（初出走を含む）", rest, experienced)]
    _collect(page, "経験", results[:1], texts={
        "このレースで3着以内の経験あり": ("このレースの好走経験者が繰り返し走る（リピーターのレース）",
                                          "このレースの好走経験者は繰り返さない"),
    })
    return _band_table("## リピーター（基準: このレースのほかの出走馬）", results)


def _upset_section(page: StakesPage, race_rows: pd.DataFrame, grade_rows: pd.DataFrame) -> str:
    winners = race_rows[race_rows["finish"] == 1]
    base_winners = grade_rows[grade_rows["finish"] == 1]
    editions = race_rows["race_id"].nunique()
    big = race_rows[(race_rows["popularity"] >= 10) & (race_rows["finish"] <= 3)]
    lines = [
        "## 荒れ度",
        "",
        f"- 勝ち馬の平均人気: {winners['popularity'].mean():.1f}"
        f"（同じグレードの基準: {base_winners['popularity'].mean():.1f}）",
        f"- 二桁人気の3着内: {editions} 開催で {len(big)} 回",
        "",
        "> 荒れ度は年ごとの入れ替わりが大きく、持続性の検証でも相関が弱い。買い方の参考程度にとどめる。",
    ]
    return "\n".join(lines)


def _band_table(title: str, results: list[BandResult]) -> str:
    table = Table(columns=list(BAND_COLUMNS), rows=[result.row() for result in results])
    return f"{title}\n\n" + to_markdown(table).rstrip()


def _collect(page: StakesPage, section: str, results: list[BandResult],
             texts: dict[str, tuple[str, str]] | None = None) -> None:
    """帯の結果から、自動要約に載せるものを拾う。``texts`` は (プラスのとき, マイナスのとき) の言い回し。"""
    for result in results:
        finding = _finding_of(section, result, texts or {})
        if finding is not None:
            page.findings.append(finding)


def _finding_of(section: str, result: BandResult, texts: dict[str, tuple[str, str]]) -> Finding | None:
    if result.p_value is None or result.diff_pt is None or result.runs < SUMMARY_MIN_RUNS:
        return None
    significant = result.p_value < SUMMARY_P
    valuable = result.runs >= ROI_MIN_RUNS and (
        result.place_roi >= PLACE_ROI_LINE or result.win_roi >= WIN_ROI_LINE)
    if not significant and not valuable:
        return None
    if result.label in texts:
        base_text = texts[result.label][0 if result.diff_pt >= 0 else 1]
    else:
        direction = "走る" if result.diff_pt >= 0 else "走らない"
        base_text = f"「{result.label}」が基準より{direction}"
    detail = (f"複勝率のずれ {result.diff_pt:+.1f}pt（{result.runs}頭・{stats.mark(result.p_value) or '有意でない'}）、"
              f"単勝回収率 {result.win_roi:.0f}%・複勝回収率 {result.place_roi:.0f}%")
    note = "。回収率が線を超えるが、過去に合わせすぎの可能性に注意" if valuable and not significant else ""
    return Finding(section=section, text=f"{base_text} — {detail}{note}", p_value=result.p_value)
