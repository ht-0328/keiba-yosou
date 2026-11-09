"""超荒れの展開と適性から大穴を当てる: 消（危険な人気馬）の決め方を探す（docs/04 の 5 の続き）。

    uv run python research/超荒れの展開と適性から大穴を当てる/danger_search.py --timing 当日 --db <元DB の写し>
    uv run python research/超荒れの展開と適性から大穴を当てる/danger_search.py --timing 当日 --check reports/…/印の成績/今の消/買い目/<名前>.csv   # 印の成績と同じ数になるか

今の消（予想「人気馬が4着以下になるかを予想」。区切りごとに検証期間で線を決め直す）を基準に、今のモデル（近走と適性から3着以内を予想）の
「1 − 3着以内の確率」で消を決めたとき（区切りごとの線と、人気帯ごとの固定の線）の全券種の印の成績を、道具「印の成績」と同じ部品で数える。
固定の線は、探索の期間（2019〜2024年）の「消を使う買い方」と「全部の合計」の的中率と回収率が今の消をどれだけ上回るか（差の最小）だけで、
人気帯ごとに1つずつ動かして選ぶ（``LineSearch``）。今の消にも同じ選び直しをして並べる。確認の期間（2025年から）は選んだあとに1回だけ見る。
結果は ``reports/超荒れの展開と適性から大穴を当てる/消の決め方の探索-<時点>.md``（表）と ``…-<時点>.csv``（全部の評価の成績）、
選んだ消の表 ``…/predictions/danger-flags-<消の元>-<時点>.pkl``（道具「印の成績」の ``--danger-flags`` に渡せる形）。
元DB を 20分ほど読む（印の成績を1回動かすのと同じくらい）。そのあと線を1つ動かすごとに 1〜3分。
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_RESEARCH = Path(__file__).resolve().parents[1]
_REPO_ROOT = _RESEARCH.parent
sys.path[:0] = [str(_RESEARCH), str(_REPO_ROOT / "tools"), str(_REPO_ROOT / "src")]

from 共通 import db  # noqa: E402

from yosou.shared.feature import PredictionTiming  # noqa: E402

from 印の成績.favorite_danger_judge import FavoriteDangerJudge  # noqa: E402
from 印の成績.fixed_line_danger_judge import FixedLineDangerJudge  # noqa: E402

from 超荒れの展開と適性から大穴を当てる.analysis.danger_search.combo_candidates import ComboCandidates  # noqa: E402
from 超荒れの展開と適性から大穴を当てる.analysis.danger_search.danger_evaluator import DangerEvaluator, Evaluation  # noqa: E402
from 超荒れの展開と適性から大穴を当てる.analysis.danger_search.danger_sources import CURRENT, MODEL, SOURCES, DangerSources  # noqa: E402
from 超荒れの展開と適性から大穴を当てる.analysis.danger_search.line_search import BANDS, LineSearch  # noqa: E402
from 超荒れの展開と適性から大穴を当てる.analysis.danger_search.odds_cache import OddsCache  # noqa: E402
from 超荒れの展開と適性から大穴を当てる.analysis.danger_search.payout_table import PayoutTable  # noqa: E402
from 超荒れの展開と適性から大穴を当てる.analysis.danger_search.race_variant_cache import RaceVariantCache  # noqa: E402
from 超荒れの展開と適性から大穴を当てる.analysis.danger_search.search_inputs import DEFAULT_MODELS, SearchInputs  # noqa: E402
from 超荒れの展開と適性から大穴を当てる.analysis.danger_search.search_report import SearchReport  # noqa: E402
from 超荒れの展開と適性から大穴を当てる.analysis.danger_search.ticket_metrics import GROUPS, TicketMetrics  # noqa: E402

DEFAULT_ROOT = _REPO_ROOT / "reports" / "超荒れの展開と適性から大穴を当てる"
_TIMINGS = {"当日": PredictionTiming.RACE_DAY, "前日": PredictionTiming.DAY_BEFORE}
#: 道具「印の成績」の買い目の csv の列 → この研究の買い目の列（``--check`` 用）。
_CSV_RENAMES = {"レースID": "race_id", "開催日": "race_date", "買い方": "rule", "券種": "ticket_type", "単位": "stake_units", "払戻（100円あたり）": "payout"}


def main() -> None:
    args = _parser().parse_args()
    timing = _TIMINGS[args.timing]
    started = time.monotonic()
    sources = DangerSources(timing, args.root)
    inputs = SearchInputs(timing, args.models)
    with db.open_db(args.db, default=db.JRA) as con:
        _log("入力を読みます", started)
        inputs.load(con, sources.race_ids())
        payouts = PayoutTable(con, inputs.days, inputs.race_ids)
        odds = OddsCache(con)
        cache = RaceVariantCache(inputs, payouts, odds, args.workers)
        combos = ComboCandidates(con, inputs, args.models)
        _log("組の期待値の候補を作ります", started)
        combos.build()
        evaluator = DangerEvaluator(inputs, cache, combos, payouts, odds)
        predictions = {source: sources.load(source) for source in SOURCES}
        _log("基準（今の消・区切りごとの線）を数えます", started)
        baseline_dangers, baseline_lines = FavoriteDangerJudge().judge(predictions[CURRENT], inputs.places)
        baseline = evaluator.evaluate(baseline_dangers)
        if args.check is not None:
            _check(baseline, args.check)
            cache.close()
            return
        named = {f"{CURRENT}（区切りごとの線）": baseline}
        _log("今のモデルの消（区切りごとの線）を数えます", started)
        model_dangers, model_lines = FavoriteDangerJudge().judge(predictions[MODEL], inputs.places)
        named[f"{MODEL}（区切りごとの線）"] = evaluator.evaluate(model_dangers)
        searches, chosen = {}, {}
        for source, fold_lines in ((MODEL, model_lines), (CURRENT, baseline_lines)):
            _log(f"{source} の固定の線を探します", started)
            search = LineSearch(lambda lines, source=source: evaluator.evaluate(_fixed(lines, predictions[source], inputs.places)),
                                baseline, passes=args.passes)
            best = search.run(_median_lines(fold_lines))
            searches[source], chosen[source] = search, best
            named[f"{source}（固定の線 {best.label()}）"] = best.evaluation
            flags = _fixed(best.lines, predictions[source], inputs.places)
            flags.to_pickle(args.root / "predictions" / f"danger-flags-{source}-{timing.value}.pkl")
        cache.close()
    report = SearchReport(timing, named, searches, chosen)
    print(f"書きました: {report.write(args.root / f'消の決め方の探索-{timing.value}.md')}", flush=True)
    print(f"書きました: {report.evaluations_csv(args.root / f'消の決め方の探索-{timing.value}.csv')}", flush=True)
    _log("終わりました", started)


def _fixed(lines: dict[str, float | None], predictions: pd.DataFrame, places: pd.DataFrame) -> pd.DataFrame:
    """固定の線で判定した消の表（線の無い人気帯は消にしない）。"""
    dangers, _ = FixedLineDangerJudge({band: line for band, line in lines.items() if line is not None}).judge(predictions, places)
    return dangers


def _median_lines(fold_lines: dict[str, dict[str, float]]) -> dict[str, float | None]:
    """区切りごとの線の中央値（探索の出発点）。線の無い区切りは数えない。どの区切りにも無ければ None。"""
    result: dict[str, float | None] = {}
    for band in BANDS:
        values = [bands.get(band) for bands in fold_lines.values()]
        values = [value for value in values if value is not None and not np.isnan(value)]
        result[band] = float(np.median(values)) if values else None
    return result


def _check(baseline: Evaluation, csv: Path) -> None:
    """基準の成績が、道具「印の成績」が書いた買い目の csv と同じ数になるかを並べる。"""
    table = pd.read_csv(csv, dtype={"レースID": str, "組番": str}, encoding="utf-8-sig")
    table = table[table["外した理由"].isna()].rename(columns=_CSV_RENAMES)
    expected = TicketMetrics().of(table)
    merged = baseline.metrics.merge(expected, on=["group", "span"], suffixes=("", "_印の成績"))
    merged = merged[merged["group"].isin(GROUPS)]
    pd.set_option("display.width", 250)
    columns = ["group", "span", "races", "races_印の成績", "hits", "hits_印の成績", "paid", "paid_印の成績", "stake", "stake_印の成績"]
    print(merged[columns].to_string(index=False))
    same = (np.isclose(merged["paid"], merged["paid_印の成績"]) & np.isclose(merged["stake"], merged["stake_印の成績"])
            & (merged["hits"] == merged["hits_印の成績"]) & (merged["races"] == merged["races_印の成績"])).all()
    print("同じ" if same else "違う", flush=True)


def _log(message: str, started: float) -> None:
    print(f"[{time.monotonic() - started:6.0f}秒] {message}", file=sys.stderr, flush=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--timing", default="当日", choices=tuple(_TIMINGS), help="時点（既定: 当日）")
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（写しを渡せば、ほかの道具と同時に動かせる）")
    parser.add_argument("--models", type=Path, default=DEFAULT_MODELS, help="複勝の見込みの倍率と組の確率の重みの置き場所")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="出力の置き場所")
    parser.add_argument("--passes", type=int, default=2, help="線を動かす回数の上限（既定: 2）")
    parser.add_argument("--workers", type=int, default=None, help="印付けと買い目を分けて行うプロセスの数（既定: CPU の数 − 2）")
    parser.add_argument("--check", type=Path, default=None, help="道具「印の成績」の買い目の csv。基準の成績が同じ数になるかだけを確かめて終わる")
    return parser


if __name__ == "__main__":
    main()
