"""傾向スコア: 当日のレースと条件が同じ過去レースから傾向を出し、出走馬を項目ごとに +1 / −1 で採点する。

言葉（項目の一覧は ``tools/傾向スコア/score-items.md``、登録簿は ``trend_items``）:

- 母集団: 傾向を出すために集める過去の出走。**当日のレースの開催日より前**で、芝ダが当日と同じものだけ。
- 段（``Level``）: 母集団の広さ。狭い順に 同レース → 4つ一致 → 3つ以上一致 → 2つ以上一致。
  「一致」は 競馬場・コース・距離・馬場状態 のうち当日と同じものの数。当日の馬場状態が分からなければ 4つ一致 は空になる。
- 基準値: 段ごとの、対象の馬（全馬 / 穴馬 / 人気馬）全体の成績。
- 判定（``classify``）: 値ごとの成績を基準値と比べて「頭向き」「相手向き」「悪い」に分ける。
  出走数が ``min_runs`` 以上ある、いちばん狭い段で判定する。どの段でも足りなければ判定しない（0 点）。
  倍率（``good``・``bad``）に加えて、差が偶然では起きにくいこと（``min_z``）も求める。
- 材料（``RaceMaterial``）: DB から読んだもの全部。``collect`` が作り、``score`` は DB を使わずに採点する。
  同じレースを線引きだけ変えて採点し直すとき、DB の読み直しを省ける。
- 推定脚質: 当日の脚質はレース前に分からないので、事実表の ``style_before``（直近3走の中央）を過去にも当日にも使う。

当日の馬の値は ``facts.build_entry_facts`` が事実表と同じ SQL で作るので、過去の集計と同じ式（``perf.Dimension``）を
そのまま当てられる。発走前の DB に無い人気・馬場状態・馬体重は ``ManualInputs`` で手で与える。

    from 共通 import trend
    report = trend.score_race(con, rid, trend.ManualInputs.parse(condition="良", popularity="3:1,7:2"))
    report.tables()    # Markdown / CSV 用の表
    report.to_dict()   # 画面（グラフ）用
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import duckdb

from . import card, codes, perf
from .facts import ENTRY_TABLE, FACTS_TABLE, EntryScope, build_entry_facts, ensure_facts
from .render import Table
from .trend_items import FACTORS, FIXED_ITEMS, GROUPS, MINUS, PLUS, Factor, FixedItem, Target, item_count

#: 判定に要る出走数の下限（最初の値）。少ないと偶然で「良い」「悪い」が付く。
MIN_RUNS = 20
#: 基準値の何倍以上で「良い」、何倍以下で「悪い」とするか（最初の値）。
GOOD_RATIO = 1.3
BAD_RATIO = 0.7
#: 差が偶然では起きにくいことを求める強さ（基準値からの隔たりを、出走数に見合うばらつきで割った値の下限）。
#: 0 なら求めない。1.64 は「偶然なら20回に1回しか起きない隔たり」。出走数が少ない値に「良い」「悪い」が付きすぎるのを抑える。
MIN_Z = 1.64
#: 母集団の一時表の名前。``LABELED_TABLE`` は、母集団の各行に切り口の値と段ごとの数を先に付けた細い表（要因ごとの集計を速くする）。
POPULATION_TABLE = "trend_population"
LABELED_TABLE = "trend_labeled"
#: 傾向の表に出す値の数の上限。これを超える切り口（騎手・父など）は、当日の馬が当たる値だけを出す。
MAX_TREND_LABELS = 16
#: 判定の名前。
HEAD, PARTNER, BAD, NEUTRAL = "頭向き", "相手向き", "悪い", ""
GOOD_VERDICTS: tuple[str, ...] = (HEAD, PARTNER)
_LABEL_JOINER = " × "
_POPULARITY_SEPARATOR, _PAIR_SEPARATOR = ":", ","


@dataclass(frozen=True)
class Level:
    """母集団の段。``where_sql`` は母集団の一時表の行を選ぶ条件。"""

    key: str
    title: str
    where_sql: str


#: 段の目録（狭い順）。
LEVELS: tuple[Level, ...] = (
    Level("same", "同レース", "is_same_race"),
    Level("match4", "4つ一致（競馬場・コース・距離・馬場状態）", "match_count = 4"),
    Level("match3", "3つ以上一致", "match_count >= 3"),
    Level("match2", "2つ以上一致", "match_count >= 2"),
)
LEVEL_BY_KEY: dict[str, Level] = {level.key: level for level in LEVELS}
#: いちばん広い段に入る条件。
_MIN_MATCH = 2

#: 要る材料が当日の馬にあるかを見る条件（``entry_facts`` の行に当てる）。
_NEED_SQL: dict[str, str] = {
    perf.NEED_GATE: "horse_no IS NOT NULL", perf.NEED_POPULARITY: "popularity IS NOT NULL",
    perf.NEED_GOING: "condition_code IS NOT NULL", perf.NEED_WEIGHT: "body_weight IS NOT NULL",
    perf.NEED_MINING: "dm_rank IS NOT NULL", perf.NEED_RESULT: "FALSE",
}
#: 当日の馬の表に出す列（事実表の列名）。
_ENTRY_COLUMNS: tuple[str, ...] = (
    "horse_id", "horse_no", "frame_no", "horse_name", "sex", "age", "jockey", "trainer", "carried", "popularity", "win_odds",
    "body_weight", "weight_change", "style_before", "ran", "abnormal_name", "finish", "interval_days", "prev_finish",
    "win_payout", "place_payout",
)


# ------------------------------------------------------------------ 入力

@dataclass(frozen=True)
class ManualInputs:
    """発走前の DB に無い材料。``condition_code`` は馬場状態コード、``popularity`` は 馬番 → 人気、``weights`` は 馬番 → （馬体重, 増減）。"""

    condition_code: str | None = None
    popularity: Mapping[int, int] = field(default_factory=dict)
    weights: Mapping[int, tuple[int, int | None]] = field(default_factory=dict)

    @classmethod
    def parse(cls, condition: str | None = None, popularity: str | None = None, weights: str | None = None) -> "ManualInputs":
        """文字の引数から作る。``condition`` は 良 / 稍重 / 重 / 不良、``popularity`` は ``3:1,7:2``（馬番:人気）、
        ``weights`` は ``3:480:+2,5:502:-4``（馬番:馬体重:増減。増減は省ける）。"""
        return cls(
            condition_code=codes.condition_code(condition) if condition and condition.strip() else None,
            popularity=_parse_popularity(popularity or ""), weights=_parse_weights(weights or ""),
        )

    def condition_name(self) -> str:
        return codes.TRACK_CONDITION.get(self.condition_code or "", "")

    def popularity_text(self) -> str:
        return _PAIR_SEPARATOR.join(f"{no}{_POPULARITY_SEPARATOR}{rank}" for no, rank in sorted(self.popularity.items()))

    def weights_text(self) -> str:
        parts = []
        for no, (weight, change) in sorted(self.weights.items()):
            parts.append(f"{no}{_POPULARITY_SEPARATOR}{weight}" + (f"{_POPULARITY_SEPARATOR}{change:+d}" if change is not None else ""))
        return _PAIR_SEPARATOR.join(parts)


def _pairs(text: str, what: str) -> list[list[str]]:
    """``3:1,7:2`` を ``[["3", "1"], ["7", "2"]]`` にする。"""
    out = []
    for part in text.replace(" ", "").split(_PAIR_SEPARATOR):
        if not part:
            continue
        values = part.split(_POPULARITY_SEPARATOR)
        if len(values) < 2 or not all(values[:2]):
            raise ValueError(f"{what} は 馬番:値 をカンマで並べてください（例 3:1,7:2）: {part}")
        out.append(values)
    return out


def _parse_popularity(text: str) -> dict[int, int]:
    try:
        return {int(no): int(rank) for no, rank, *_ in _pairs(text, "人気")}
    except ValueError as error:
        raise ValueError(f"人気は 馬番:人気 の整数で書いてください（例 3:1,7:2）: {error}") from None


def _parse_weights(text: str) -> dict[int, tuple[int, int | None]]:
    try:
        return {int(no): (int(weight), int(rest[0]) if rest and rest[0] else None) for no, weight, *rest in _pairs(text, "馬体重")}
    except ValueError as error:
        raise ValueError(f"馬体重は 馬番:馬体重:増減 の整数で書いてください（例 3:480:+2）: {error}") from None


@dataclass(frozen=True)
class Options:
    """採点の設定。``scope`` を与えると、その段だけで判定する（はしごを使わない）。"""

    scope: str | None = None
    min_runs: int = MIN_RUNS
    good: float = GOOD_RATIO
    bad: float = BAD_RATIO
    min_z: float = MIN_Z

    def __post_init__(self) -> None:
        if self.scope is not None and self.scope not in LEVEL_BY_KEY:
            raise ValueError(f"段は {', '.join(LEVEL_BY_KEY)} のどれかです: {self.scope}")
        if self.min_runs < 1:
            raise ValueError(f"出走数の下限は 1 以上です: {self.min_runs}")

    def levels(self) -> tuple[Level, ...]:
        """判定に使う段（狭い順）。"""
        return (LEVEL_BY_KEY[self.scope],) if self.scope else LEVELS


# ------------------------------------------------------------------ 判定

def z_score(rate: float, base_rate: float, runs: int) -> float:
    """率が基準値からどれだけ離れているかを、出走数に見合うばらつき（二項分布の標準偏差）で割った値。"""
    spread = math.sqrt(base_rate * (1 - base_rate) / runs) if runs and 0 < base_rate < 1 else 0.0
    return (rate - base_rate) / spread if spread else 0.0


def classify(row: perf.PerfRow, base: perf.PerfRow, options: Options = Options()) -> str:
    """値の成績を基準値と比べる。頭向き = 勝率が良い、相手向き = 勝率は届かないが連対率か複勝率が良い、悪い = 複勝率が悪い。

    「良い」は基準値の ``good`` 倍以上、「悪い」は ``bad`` 倍以下で、どちらも隔たりが ``min_z`` 以上（偶然では起きにくい）のとき。
    良いと悪いの両方に当たる（出走数が少ないときにまれに起きる）なら、判定しない。
    """
    if not row.runs or not base.runs:
        return NEUTRAL
    rates, base_rates = row.rates(), base.rates()

    def is_good(name: str) -> bool:
        return (base_rates[name] > 0 and rates[name] >= base_rates[name] * options.good
                and z_score(rates[name], base_rates[name], row.runs) >= options.min_z)

    is_bad = (base_rates["複勝率"] > 0 and rates["複勝率"] <= base_rates["複勝率"] * options.bad
              and z_score(rates["複勝率"], base_rates["複勝率"], row.runs) <= -options.min_z)
    good = HEAD if is_good("勝率") else PARTNER if (is_good("連対率") or is_good("複勝率")) else NEUTRAL
    if is_bad:
        return NEUTRAL if good else BAD
    return good


def _total(rows: Sequence[perf.PerfRow]) -> perf.PerfRow:
    """成績の行を足し合わせる（基準値を作る）。"""
    sums = [sum(getattr(row, name) for row in rows) for name in ("runs", "first", "second", "third", "win_return", "place_return")]
    return perf.PerfRow(("全体",), *sums)


def perf_dict(row: perf.PerfRow | None) -> dict[str, Any] | None:
    """成績を画面用の辞書にする（率は 0〜1）。"""
    if row is None or not row.runs:
        return None
    rates = row.rates()
    return {
        "runs": row.runs, "first": row.first, "second": row.second, "third": row.third, "out": row.out, "counts": row.counts(),
        "win": rates["勝率"], "quinella": rates["連対率"], "place": rates["複勝率"],
        "win_return": rates["単勝回収率"], "place_return": rates["複勝回収率"],
    }


# ------------------------------------------------------------------ 結果の形

@dataclass
class LabelTrend:
    """切り口の値1つの傾向。``rows`` は 段 → 成績、``level`` は判定に使った段（判定できなければ None）。"""

    labels: tuple[Any, ...]
    rows: dict[str, perf.PerfRow]
    level: str | None = None
    verdict: str = NEUTRAL
    horses: list[str] = field(default_factory=list)

    def text(self) -> str:
        return _LABEL_JOINER.join(str(label) for label in self.labels)


@dataclass
class FactorTrend:
    """要因1つの傾向。``skipped`` は当日の馬に当てはめられない理由（未入力の材料）。"""

    factor: Factor
    columns: tuple[str, ...]
    baselines: dict[str, perf.PerfRow]
    labels: list[LabelTrend]
    skipped: str = ""


@dataclass(frozen=True)
class Hit:
    """1頭が1項目に当たった記録。"""

    item_id: str
    sign: int
    group: int
    title: str
    label: str
    verdict: str
    level: str | None
    row: perf.PerfRow | None
    baseline: perf.PerfRow | None


@dataclass
class HorseScore:
    """1頭の採点。``entry`` は当日の馬の行（``_ENTRY_COLUMNS`` の値）。"""

    entry: dict[str, Any]
    hits: list[Hit] = field(default_factory=list)

    def count(self, sign: int) -> int:
        return sum(1 for hit in self.hits if hit.sign == sign)

    @property
    def score(self) -> int:
        return sum(hit.sign for hit in self.hits)

    def verdict_count(self, verdict: str) -> int:
        return sum(1 for hit in self.hits if hit.verdict == verdict)

    def group_scores(self) -> dict[int, int]:
        return {group: sum(hit.sign for hit in self.hits if hit.group == group) for group in GROUPS}

    def display_no(self) -> str:
        return str(self.entry["horse_no"]) if self.entry["horse_no"] is not None else "未定"


@dataclass
class TrendReport:
    """1レースの採点の結果。"""

    rid: str
    header: dict[str, Any]
    inputs: ManualInputs
    options: Options
    missing: list[str]
    levels: list[dict[str, Any]]
    horses: list[HorseScore]
    scratched: list[dict[str, Any]]
    trends: list[FactorTrend]
    same_race: Table

    def title(self) -> str:
        return card.header_title(self.header)

    def result_known(self) -> bool:
        return any(horse.entry["finish"] is not None for horse in self.horses)

    # --- 表（Markdown / CSV）
    def tables(self) -> list[Table]:
        return [self.summary_table(), self.ranking_table(), self.highlight_table(), self.breakdown_table(), self.same_race]

    def summary_table(self) -> Table:
        counts = item_count()
        rows: list[list[Any]] = [["レース", self.title()], ["rid", self.rid],
                                 ["馬場状態", self.header["馬場"] if not self.inputs.condition_name() else f"{self.inputs.condition_name()}（手入力）"]]
        rows += [[f"母集団: {level['title']}", f"{level['races']:,} レース・{level['runs']:,} 頭" + (f"（{level['perf']['counts']}・複勝率 {perf.percent(level['perf']['place'])}）" if level["perf"] else "")]
                 for level in self.levels]
        rows.append(["項目の数", f"プラス {counts[PLUS]}・マイナス {counts[MINUS]}"])
        rows.append(["判定の線引き", f"出走数 {self.options.min_runs} 以上、基準値の {self.options.good} 倍以上で良い、{self.options.bad} 倍以下で悪い"
                     + (f"、偶然では起きにくい差だけ（強さ {self.options.min_z}）" if self.options.min_z > 0 else "")
                     + (f"、段は {LEVEL_BY_KEY[self.options.scope].title} だけ" if self.options.scope else "")])
        rows.append(["未入力の材料", "、".join(self.missing) if self.missing else "なし"])
        note = "未入力の材料を使う項目は 0 点。馬場状態が無ければ、馬場状態を問わない段（3つ以上一致から）で採点する。" if self.missing else ""
        return Table(["項目", "値"], rows, title=f"傾向スコア: {self.title()}", note=note)

    def ranking_table(self) -> Table:
        columns = ["順位", "枠", "馬番", "馬名", "人気", "推定脚質", "合計", "プラス", "マイナス", "頭向き", "相手向き", "当たった項目"]
        if self.result_known():
            columns.insert(5, "着順")
        rows = []
        for rank, horse in enumerate(self.horses, start=1):
            e = horse.entry
            row = [rank, e["frame_no"], e["horse_no"], e["horse_name"], e["popularity"], e["style_before"] or "不明",
                   f"{horse.score:+d}", horse.count(PLUS), horse.count(MINUS), horse.verdict_count(HEAD), horse.verdict_count(PARTNER),
                   " ".join(hit.item_id for hit in horse.hits)]
            if self.result_known():
                row.insert(5, e["finish"])
            rows.append(row)
        note = "合計 = プラスの数 − マイナスの数。頭向き = 勝率が良い傾向、相手向き = 勝率は並だが連対率か複勝率が良い傾向。"
        if self.scratched:
            note += " 出走しない馬: " + "、".join(f"{s['horse_name']}（{s['abnormal_name']}）" for s in self.scratched) + "。"
        return Table(columns, rows, title="ランキング（点数の高い順）", note=note)

    def breakdown_table(self) -> Table:
        columns = ["馬番", "馬名", "項目", "点", "要因", "値", "判定", "母集団", *perf.PERF_COLUMNS, "基準の勝率", "基準の複勝率"]
        rows = []
        for horse in self.horses:
            for hit in horse.hits:
                cells = hit.row.cells() if hit.row else [""] * len(perf.PERF_COLUMNS)
                base = hit.baseline.rates() if hit.baseline else None
                rows.append([horse.entry["horse_no"], horse.entry["horse_name"], hit.item_id, f"{hit.sign:+d}", hit.title, hit.label,
                             hit.verdict or "無条件", LEVEL_BY_KEY[hit.level].title if hit.level else "", *cells,
                             perf.percent(base["勝率"]) if base else "", perf.percent(base["複勝率"]) if base else ""])
        return Table(columns, rows, title="馬ごとの内訳（当たった項目と、その根拠の成績）")

    def highlight_table(self) -> Table:
        columns = ["グループ", "要因", "対象", "値", "判定", "母集団", *perf.PERF_COLUMNS, "基準の複勝率", "当てはまる馬"]
        names = {horse.entry["horse_id"]: f"{horse.display_no()} {horse.entry['horse_name']}" for horse in self.horses}
        rows = []
        for trend in self.trends:
            for label in trend.labels:
                if not label.verdict or label.level is None:
                    continue
                base = trend.baselines[label.level].rates()
                rows.append([GROUPS[trend.factor.group], trend.factor.title, trend.factor.target.title, label.text(), label.verdict,
                             LEVEL_BY_KEY[label.level].title, *label.rows[label.level].cells(), perf.percent(base["複勝率"]),
                             "、".join(names[hid] for hid in label.horses)])
        return Table(columns, rows, title="このレースの条件の傾向（良い・悪いと判定された値）",
                     note="騎手・父のように値の多い切り口は、当日の馬が当たる値だけを出す。")

    # --- 画面用
    def to_dict(self) -> dict[str, Any]:
        counts = item_count()
        return {
            "rid": self.rid, "title": self.title(), "header": self.header, "result_known": self.result_known(),
            "inputs": {"condition": self.inputs.condition_name(), "popularity": self.inputs.popularity_text(), "weights": self.inputs.weights_text()},
            "options": {"scope": self.options.scope, "min_runs": self.options.min_runs, "good": self.options.good, "bad": self.options.bad,
                        "min_z": self.options.min_z},
            "missing": self.missing, "levels": self.levels, "groups": {str(no): name for no, name in GROUPS.items()},
            "counts": {"plus": counts[PLUS], "minus": counts[MINUS]},
            "horses": [_horse_dict(rank, horse) for rank, horse in enumerate(self.horses, start=1)],
            "scratched": self.scratched,
            "trends": [_trend_dict(trend) for trend in self.trends],
            "same_race": {"title": self.same_race.title, "columns": self.same_race.columns, "rows": self.same_race.rows, "note": self.same_race.note},
        }


def _horse_dict(rank: int, horse: HorseScore) -> dict[str, Any]:
    e = horse.entry
    return {
        "rank": rank, "hid": e["horse_id"], "no": e["horse_no"], "frame": e["frame_no"], "name": e["horse_name"],
        "sex_age": f"{e['sex']}{e['age'] or ''}", "jockey": e["jockey"], "carried": e["carried"], "popularity": e["popularity"],
        "style_before": e["style_before"] or "不明", "finish": e["finish"], "body_weight": e["body_weight"], "weight_change": e["weight_change"],
        "score": horse.score, "plus": horse.count(PLUS), "minus": horse.count(MINUS),
        "head": horse.verdict_count(HEAD), "partner": horse.verdict_count(PARTNER),
        "groups": {str(group): value for group, value in horse.group_scores().items()},
        "hits": [{"id": hit.item_id, "sign": hit.sign, "group": hit.group, "title": hit.title, "label": hit.label,
                  "verdict": hit.verdict or "無条件", "level": hit.level, "perf": perf_dict(hit.row), "base": perf_dict(hit.baseline)}
                 for hit in horse.hits],
    }


def _trend_dict(trend: FactorTrend) -> dict[str, Any]:
    factor = trend.factor
    return {
        "key": factor.key, "no": factor.no, "group": factor.group, "title": factor.title, "target": factor.target.key,
        "target_title": factor.target.title, "skipped": trend.skipped, "columns": list(trend.columns),
        "ids": {str(sign): factor.item_id(sign) for sign in factor.signs()},
        "baselines": {key: perf_dict(row) for key, row in trend.baselines.items()},
        "labels": [{"label": label.text(), "verdict": label.verdict, "level": label.level, "horses": label.horses,
                    "rows": {key: perf_dict(row) for key, row in label.rows.items()}} for label in trend.labels],
    }


# ------------------------------------------------------------------ 採点

@dataclass
class RaceMaterial:
    """1レースの採点の材料。DB から読んだもの全部で、ここから先（``score``）は DB を使わない。

    ``population`` は 要因の鍵 → （切り口の値, 段 → 成績）の並び。線引きを変えて採点し直すとき（検証）に使い回せる。
    """

    rid: str
    header: dict[str, Any]
    entries: list[dict[str, Any]]
    population: dict[str, list[tuple[tuple[Any, ...], dict[str, perf.PerfRow]]]]
    levels: list[dict[str, Any]]
    same_race: Table


def collect(con: duckdb.DuckDBPyConnection, rid: str, inputs: ManualInputs = ManualInputs(),
            factors: Sequence[Factor] = FACTORS, fixed_items: Sequence[FixedItem] = FIXED_ITEMS) -> RaceMaterial:
    """採点の材料を DB から読む。レースが無ければ ``LookupError``。一時表は使い終わったら消す。"""
    ensure_facts(con)
    header = card.race_header(con, rid)
    build_entry_facts(con, EntryScope(rid, inputs.condition_code), popularity=inputs.popularity, weights=inputs.weights)
    try:
        race = _race_attributes(con)
        _build_population(con, race)
        singles = _single_dimensions(factors)
        _build_labeled(con, singles)
        return RaceMaterial(
            rid=rid, header=header, entries=_entries(con, factors, fixed_items, singles),
            population=_population(con, factors, singles),
            levels=_level_summaries(con), same_race=_same_race_table(con, race),
        )
    finally:
        for table in (LABELED_TABLE, POPULATION_TABLE, ENTRY_TABLE):
            _fetch(con, f"DROP TABLE IF EXISTS {table}")


def score(material: RaceMaterial, inputs: ManualInputs = ManualInputs(), options: Options = Options(),
          factors: Sequence[Factor] = FACTORS, fixed_items: Sequence[FixedItem] = FIXED_ITEMS) -> TrendReport:
    """材料から採点する。``factors``・``fixed_items`` は ``collect`` に渡したものと同じにする。"""
    runners = [entry for entry in material.entries if entry["ran"]]
    horses = {entry["horse_id"]: HorseScore(entry) for entry in runners}
    trends = [_factor_trend(factor, material.population[factor.key], runners, horses, options) for factor in factors]
    _apply_fixed_items(fixed_items, runners, horses)
    ranked = sorted(horses.values(), key=lambda h: (-h.score, -h.count(PLUS), h.entry["horse_no"] or 0, h.entry["horse_name"]))
    return TrendReport(
        rid=material.rid, header=material.header, inputs=inputs, options=options, missing=_missing_inputs(runners, factors),
        levels=material.levels, horses=ranked,
        scratched=[{"horse_name": e["horse_name"], "abnormal_name": e["abnormal_name"]} for e in material.entries if not e["ran"]],
        trends=trends, same_race=material.same_race,
    )


def score_race(con: duckdb.DuckDBPyConnection, rid: str, inputs: ManualInputs = ManualInputs(), options: Options = Options()) -> TrendReport:
    """1レースを採点する（材料を読んで、採点する）。"""
    return score(collect(con, rid, inputs), inputs, options)


def _fetch(con: duckdb.DuckDBPyConnection, sql: str, params: Any = None) -> list[tuple]:
    """実行して全部読む。結果を読み切ってから次の SQL を打つ（同じ接続で結果が上書きされないように）。"""
    cursor = con.execute(sql, params) if params is not None else con.execute(sql)
    return cursor.fetchall() if cursor.description else []


def _race_attributes(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    names = ("race_date", "venue_code", "track_code", "distance_m", "condition_code", "surface", "race_name")
    row = _fetch(con, f"SELECT {', '.join(names)} FROM {ENTRY_TABLE} LIMIT 1")[0]
    return dict(zip(names, row))


def _build_population(con: duckdb.DuckDBPyConnection, race: Mapping[str, Any]) -> None:
    """母集団の一時表。開催日より前・同じ芝ダで、2つ以上一致するか同レースの出走。"""
    _fetch(con, f"""
        CREATE OR REPLACE TEMP TABLE {POPULATION_TABLE} AS
        SELECT * FROM (
            SELECT *,
                   (venue_code = $venue)::INTEGER + (track_code = $track)::INTEGER + (distance_m = $distance)::INTEGER
                       + coalesce((condition_code = CAST($condition AS VARCHAR))::INTEGER, 0) AS match_count,
                   coalesce(race_name <> '' AND race_name = $name, FALSE) AS is_same_race
            FROM {FACTS_TABLE}
            WHERE ran AND race_date < $day AND surface = $surface
        ) WHERE match_count >= {_MIN_MATCH} OR is_same_race
    """, {"venue": race["venue_code"], "track": race["track_code"], "distance": race["distance_m"], "condition": race["condition_code"],
          "name": race["race_name"] or "", "day": race["race_date"], "surface": race["surface"]})


#: 段ごとに数える6つ（出走・1着・2着・3着・単勝払戻・複勝払戻）。``perf.perf_row_from`` の引数の順。
_COUNTED: tuple[tuple[str, str], ...] = (
    ("runs", "1"), ("first", "coalesce(finish = 1, FALSE)::INTEGER"), ("second", "coalesce(finish = 2, FALSE)::INTEGER"),
    ("third", "coalesce(finish = 3, FALSE)::INTEGER"), ("win", "win_payout"), ("place", "place_payout"),
)
#: 対象（``Target.where_sql``）が使える列。細い表に残す。
_TARGET_COLUMNS: tuple[str, ...] = ("popularity",)


def _counted_columns() -> str:
    """母集団の1行が、段ごとに何として数えられるかの列（``runs_same`` など）。段に入らない行は 0。"""
    return ", ".join(f"CASE WHEN {level.where_sql} THEN {value} ELSE 0 END AS {name}_{level.key}"
                     for level in LEVELS for name, value in _COUNTED)


def _level_sums() -> str:
    """``_counted_columns`` の列の和（段の順 × 数える6つの順）。"""
    return ", ".join(f"sum({name}_{level.key})" for level in LEVELS for name, _ in _COUNTED)


def _rows_by_level(labels: tuple[Any, ...], values: Sequence[Any]) -> dict[str, perf.PerfRow]:
    """``_level_sums`` の結果を 段 → 成績 にする。出走の無い段は入れない。"""
    out = {}
    for index, level in enumerate(LEVELS):
        chunk = values[index * len(_COUNTED):(index + 1) * len(_COUNTED)]
        if chunk[0]:
            out[level.key] = perf.perf_row_from(labels, chunk)
    return out


def _single_dimensions(factors: Sequence[Factor]) -> dict[str, perf.Dimension]:
    """要因が使う切り口（掛け合わせる前の1つずつ）。名前 → 切り口。"""
    return {name: perf.dimension(name) for factor in factors for name in factor.dims}


def _label_sql(dimension: perf.Dimension) -> str:
    """切り口の値を文字にした式。数えない行（``where_sql`` に合わない行）は NULL。過去の集計にも当日の馬にも同じ式を当てる。"""
    return f"CASE WHEN ({dimension.where_sql}) THEN CAST({dimension.columns[0].sql} AS VARCHAR) END"


def _build_labeled(con: duckdb.DuckDBPyConnection, singles: Mapping[str, perf.Dimension]) -> None:
    """母集団の各行に、切り口の値・並び順・段ごとの数を付けた細い表を作る。"""
    labels = ", ".join(f"{_label_sql(dimension)} AS label_{index}, {dimension.order_sql[0]} AS order_{index}"
                       for index, dimension in enumerate(singles.values()))
    _fetch(con, f"CREATE OR REPLACE TEMP TABLE {LABELED_TABLE} AS "
                f"SELECT {labels}, {_counted_columns()}, race_id, {', '.join(_TARGET_COLUMNS)} FROM {POPULATION_TABLE}")


def _level_summaries(con: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """段ごとのレース数・出走数・全馬の基準値（画面の見出し用）。"""
    races = ", ".join(f"count(DISTINCT CASE WHEN runs_{level.key} = 1 THEN race_id END)" for level in LEVELS)
    row = _fetch(con, f"SELECT {races}, {_level_sums()} FROM {LABELED_TABLE}")[0]
    rows = _rows_by_level(("全体",), row[len(LEVELS):]) if row[len(LEVELS)] is not None else {}
    return [{"key": level.key, "title": level.title, "races": row[index] or 0, "runs": rows[level.key].runs if level.key in rows else 0,
             "perf": perf_dict(rows.get(level.key))} for index, level in enumerate(LEVELS)]


def _entries(con: duckdb.DuckDBPyConnection, factors: Sequence[Factor], fixed_items: Sequence[FixedItem],
             singles: Mapping[str, perf.Dimension]) -> list[dict[str, Any]]:
    """当日の馬の行に、切り口の値・対象かどうか・要る材料があるか・無条件の項目に当たるかを付けて読む。"""
    selects = list(_ENTRY_COLUMNS)
    selects += [f"({sql}) AS need_{index}" for index, sql in enumerate(_NEED_SQL.values())]
    targets = {factor.target.key: factor.target for factor in factors}
    selects += [f"coalesce(({target.where_sql}), FALSE) AS target_{key}" for key, target in targets.items()]
    selects += [f"{_label_sql(dimension)} AS label_{index}" for index, dimension in enumerate(singles.values())]
    selects += [f"coalesce(({item.applies_sql}), FALSE) AS fixed_{index}" for index, item in enumerate(fixed_items)]
    cursor = con.execute(f"SELECT {', '.join(selects)} FROM {ENTRY_TABLE} ORDER BY horse_no, horse_name")
    names = [description[0] for description in cursor.description]
    records = [dict(zip(names, row)) for row in cursor.fetchall()]
    position = {name: index for index, name in enumerate(singles)}
    for record in records:
        record["needs"] = {need: record[f"need_{index}"] for index, need in enumerate(_NEED_SQL)}
        record["labels"] = {}
        for factor in factors:
            labels = tuple(record[f"label_{position[name]}"] for name in factor.dims)
            record["labels"][factor.dims] = None if None in labels else labels
    return records


def _missing_inputs(runners: Sequence[Mapping[str, Any]], factors: Sequence[Factor]) -> list[str]:
    """項目が要る材料のうち、当日のどの馬にも無いもの。"""
    wanted = sorted({need for factor in factors for need in factor.needs()})
    return [need for need in wanted if not any(runner["needs"][need] for runner in runners)]


def _population(con: duckdb.DuckDBPyConnection, factors: Sequence[Factor],
                singles: Mapping[str, perf.Dimension]) -> dict[str, list[tuple[tuple[Any, ...], dict[str, perf.PerfRow]]]]:
    """要因ごとの母集団の成績（要因の鍵 → 値ごとの 段 → 成績）。切り口の組が同じ要因は、対象が違っても1回の集計で済ませる。"""
    by_dims: dict[tuple[str, ...], list[Factor]] = {}
    for factor in factors:
        by_dims.setdefault(factor.dims, []).append(factor)
    out = {}
    for dims, group in by_dims.items():
        targets = list({factor.target.key: factor.target for factor in group}.values())
        rows = _population_rows(con, dims, targets, singles)
        for factor in group:
            out[factor.key] = rows[factor.target.key]
    return out


def _population_rows(con: duckdb.DuckDBPyConnection, dims: tuple[str, ...], targets: Sequence[Target],
                     singles: Mapping[str, perf.Dimension]) -> dict[str, list[tuple[tuple[Any, ...], dict[str, perf.PerfRow]]]]:
    """母集団を切り口の値ごとに集計する。対象（全馬・穴馬・人気馬）に入るかどうかでも分けて数え、対象ごとに足し直す。

    返すのは 対象の鍵 → （値, 段 → 成績）の並び。値は切り口の並び順。
    """
    position = {name: index for index, name in enumerate(singles)}
    labels = [f"label_{position[name]}" for name in dims]
    flags = [f"coalesce(({target.where_sql}), FALSE)" for target in targets]
    orders = ", ".join(f"min(order_{position[name]})" for name in dims)
    known = " AND ".join(f"{label} IS NOT NULL" for label in labels)
    rows = _fetch(con, f"""
        SELECT {', '.join(labels)}, {', '.join(flags)}, {_level_sums()}
        FROM {LABELED_TABLE}
        WHERE {known}
        GROUP BY {', '.join([*labels, *flags])} ORDER BY {orders}
    """)
    width, flag_end = len(labels), len(labels) + len(flags)
    out: dict[str, list[tuple[tuple[Any, ...], dict[str, perf.PerfRow]]]] = {}
    for index, target in enumerate(targets):
        sums: dict[tuple[Any, ...], list[int]] = {}
        for row in rows:
            if row[width + index]:
                total = sums.setdefault(tuple(row[:width]), [0] * (len(LEVELS) * len(_COUNTED)))
                for column, value in enumerate(row[flag_end:]):
                    total[column] += value or 0
        out[target.key] = [(value, _rows_by_level(value, total)) for value, total in sums.items()]
    return out


def _judge(label: LabelTrend, baselines: Mapping[str, perf.PerfRow], options: Options) -> None:
    """出走数が足りる、いちばん狭い段で判定する。"""
    for level in options.levels():
        row = label.rows.get(level.key)
        if row is not None and row.runs >= options.min_runs:
            label.level, label.verdict = level.key, classify(row, baselines[level.key], options)
            return


def _factor_trend(factor: Factor, population: Sequence[tuple[tuple[Any, ...], dict[str, perf.PerfRow]]],
                  runners: Sequence[Mapping[str, Any]], horses: Mapping[str, HorseScore], options: Options) -> FactorTrend:
    """要因1つの傾向を判定し、当日の馬に当てはめて点を付ける。"""
    dimension = factor.dimension()
    baselines = {level.key: _total([rows[level.key] for _, rows in population if level.key in rows]) for level in LEVELS}
    trends = {labels: LabelTrend(labels, rows) for labels, rows in population}
    for label in trends.values():
        _judge(label, baselines, options)
    needs = sorted(factor.needs())
    for runner in runners:
        labels = runner["labels"][factor.dims]
        if labels is None or not runner[f"target_{factor.target.key}"] or not all(runner["needs"][need] for need in needs):
            continue
        label = trends.setdefault(labels, LabelTrend(labels, {}))
        label.horses.append(runner["horse_id"])
        sign = PLUS if label.verdict in GOOD_VERDICTS else MINUS if label.verdict == BAD else 0
        if sign and sign in factor.signs():
            horses[runner["horse_id"]].hits.append(Hit(
                factor.item_id(sign), sign, factor.group, factor.title, label.text(), label.verdict, label.level,
                label.rows.get(label.level or ""), baselines.get(label.level or ""),
            ))
    shown = list(trends.values())
    if len(shown) > MAX_TREND_LABELS:
        shown = [label for label in shown if label.horses]
    lacking = [need for need in needs if not any(runner["needs"][need] for runner in runners)]
    return FactorTrend(factor, dimension.column_names, baselines, shown, skipped="未入力: " + "・".join(lacking) if lacking else "")


def _apply_fixed_items(fixed_items: Sequence[FixedItem], runners: Sequence[Mapping[str, Any]], horses: Mapping[str, HorseScore]) -> None:
    for index, item in enumerate(fixed_items):
        for runner in runners:
            if runner[f"fixed_{index}"]:
                horses[runner["horse_id"]].hits.append(Hit(item.id, item.sign, item.group, item.title, "", NEUTRAL, None, None, None))
    for horse in horses.values():
        horse.hits.sort(key=lambda hit: (-hit.sign, hit.item_id))


#: 同レースの過去の表に出す列（事実表の列名, 見出し）。
_SAME_RACE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("race_date", "日付"), ("venue", "場"), ("course", "コース"), ("distance_m", "距離"), ("condition", "馬場"), ("field_size", "頭数"),
    ("finish", "着順"), ("frame_no", "枠"), ("horse_no", "馬番"), ("horse_name", "馬名"), ("popularity", "人気"), ("win_odds", "単勝"),
    ("style_before", "推定脚質"), ("style", "脚質"), ("corner4", "4角"), ("jockey", "騎手"), ("race_id", "rid"),
)
_PLACED = 3


def _same_race_table(con: duckdb.DuckDBPyConnection, race: Mapping[str, Any]) -> Table:
    """同レースの過去の開催の、3着までの馬。"""
    select = ", ".join(column for column, _ in _SAME_RACE_COLUMNS)
    rows = _fetch(con, f"SELECT {select} FROM {POPULATION_TABLE} WHERE is_same_race AND finish <= {_PLACED} ORDER BY race_date DESC, finish, horse_no")
    name = race["race_name"] or ""
    note = ("競走名と芝ダが同じ過去のレース。年によって競馬場や距離が違うことがあるので、場・コース・距離の列で確かめる。"
            if name else "平場（競走名なし）のレースには、同レースの過去はありません。")
    return Table([title for _, title in _SAME_RACE_COLUMNS], [list(row) for row in rows],
                 title=f"同レースの過去（3着まで）: {name}" if name else "同レースの過去", note=note)


def catalog_table() -> Table:
    """項目の一覧（ID・符号・グループ・要因・対象・切り口・要る材料）。"""
    rows = []
    for factor in FACTORS:
        for sign in factor.signs():
            rows.append([factor.item_id(sign), f"{sign:+d}", GROUPS[factor.group], factor.title, factor.target.title,
                         " × ".join(factor.dims), "・".join(sorted(factor.needs()))])
    rows += [[item.id, f"{item.sign:+d}", GROUPS[item.group], item.title, "全馬", "（無条件）", ""] for item in FIXED_ITEMS]
    rows.sort(key=lambda row: (row[0][0] != "P", row[0]))
    return Table(["項目", "点", "グループ", "要因", "対象", "切り口", "要る材料"], rows, title="傾向スコアの項目の一覧",
                 note="どの値が良い・悪いかは、コースごとの過去の成績が決める。説明は tools/傾向スコア/score-items.md。")
