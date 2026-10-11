"""トラックバイアス: 当日の先に終わったレースで「市場の見立てより来た馬が内か外か・前か後ろか」を数え、出走馬ごとにバイアス向き・バイアス逆を判定する。

    uv run python tools/トラックバイアス/track_bias.py --date 2026-10-11 --venue 東京 --race 11            # 1レース
    uv run python tools/トラックバイアス/track_bias.py 2026101105050411                                    # rid で
    uv run python tools/トラックバイアス/track_bias.py --date 2026-10-11 --all                             # その日の全レース
    uv run python tools/トラックバイアス/track_bias.py --date 2026-10-11 --venue 東京 --race 11 --timing 前日   # 時点を指定する
    uv run python tools/トラックバイアス/track_bias.py --date 2026-10-11 --all --rebuild                   # 傾きの表を作り直してから

同じ馬場（競馬場 × 芝ダ × 内外回り）の、その日の先に終わったレース（前の日のレースは 0.5 本）ごとの「内の傾き」「前の傾き」
（残差 = 3着以内 − 市場から見た3着以内率 を、馬番の位置・4コーナーの位置に回帰した傾き）を平均し、過去の傾き
（同じ馬場 × 開催の何日目 × 馬場状態の平均。k = 4 本ぶんの重み）と混ぜて「使う傾き」にする。各馬の補正 B は
使う内の傾き × 内らしさ + 使う前の傾き × 予想の前らしさ（予想「展開から着順を予想」の④ 4コーナーの位置）で、3着以内の確率のポイント。
線（±0.02）でバイアス向き・バイアス逆を判定する（設計書「買うレースと買い目を決める」06 の 1）。
時点（前日・当日）は DB の情報から自動で選ぶ（今週の予想と同じ決め方。木曜は馬番が無いので前日として数える）。
レースごとの傾きと過去の傾きの表は 2011年からの全出走から作り、``reports/トラックバイアス/cache/`` にとっておく（元DB が更新されたら作り直す。1分ほど）。
先に ``uv run python -m yosou.race_development train`` で展開のモデルを作っておく。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import card, cli, db, race  # noqa: E402
from 共通.render import Table  # noqa: E402

from 今週の予想.timing_chooser import TimingChooser  # noqa: E402

from yosou.development_score.entry_name_repository import HORSE_NAME, HORSE_NO, EntryNameRepository  # noqa: E402
from yosou.form_aptitude_top3.command.development_root_argument import DEFAULT_DEVELOPMENT_ROOT  # noqa: E402
from yosou.shared.feature import PredictionTiming  # noqa: E402
from yosou.track_bias import (  # noqa: E402
    DEFAULT_CACHE_FOLDER,
    DEFAULT_LINE,
    BiasJudge,
    MemoizedPaceForecast,
    PriorSlopeTableStore,
    RaceBiasSource,
    names,
)

#: 1頭ごとの表の列。
HORSE_COLUMNS: list[str] = ["馬番", "馬名", "内の分", "前の分", "バイアス補正", "判定"]


def main(args) -> None:
    judge = BiasJudge(args.line)
    with db.open_db(args.db) as con:
        if args.rebuild:
            print("レースごとの傾きと過去の傾きの表を 2011年からの全出走から作り直しています …", file=sys.stderr, flush=True)
        slopes, table = PriorSlopeTableStore(args.cache).load(con, db.resolve_db(args.db), rebuild=args.rebuild)
        source = RaceBiasSource(MemoizedPaceForecast(args.development_root / "models").run, slopes, table)
        results = _race_views(con, source, judge, args)
    cli.emit(results, args)


def _race_views(con, source: RaceBiasSource, judge: BiasJudge, args) -> list[Table]:
    chooser = TimingChooser()
    results = []
    for rid in _rids(con, args):
        header = card.race_header(con, rid)
        if header["コース"].startswith("障害"):
            print(f"飛ばします（障害）: {card.header_title(header)}", file=sys.stderr, flush=True)
            continue
        if args.timing:
            timing, reason = PredictionTiming.parse(args.timing), "指定"
        else:
            choice = chooser.choose(con, rid)
            timing, reason = choice.timing, choice.reason
        if timing is PredictionTiming.THURSDAY:
            timing, reason = PredictionTiming.DAY_BEFORE, f"{reason}。木曜は馬番が無いので前日として数える"
        corrected = source.of(con, rid, timing)
        used = source.used_slopes(con, rid, timing).iloc[0]
        results.append(_race_table(corrected, used, EntryNameRepository(con).read(rid), card.header_title(header), timing, reason, judge))
    return results


def _race_table(corrected, used, entries, title: str, timing: PredictionTiming, reason: str, judge: BiasJudge) -> Table:
    horses = corrected.merge(entries, on="horse_id", how="left")
    horses[names.VERDICT] = judge.of(horses[names.CORRECTION])
    horses = horses.sort_values(names.CORRECTION, ascending=False, na_position="last", kind="stable")
    rows = []
    for _, horse in horses.iterrows():
        row: dict[str, Any] = {"馬番": _plain(horse[HORSE_NO]), "馬名": horse[HORSE_NAME], "内の分": _points(horse[names.INNER_PART]),
                               "前の分": _points(horse[names.FRONT_PART]), "バイアス補正": _points(horse[names.CORRECTION]), "判定": horse[names.VERDICT]}
        rows.append([row[column] for column in HORSE_COLUMNS])
    note = (f"時点: {timing.label}（{reason}）。当日の傾き: 内 {_points(used[names.INNER_SLOPE])}・前 {_points(used[names.FRONT_SLOPE])}"
            f"（数えたレース {used[names.RACES]:g} 本）。過去の傾き: 内 {_points(used[names.PRIOR_INNER])}・前 {_points(used[names.PRIOR_FRONT])}。"
            f"使う傾き: 内 {_points(used[names.USED_INNER])}・前 {_points(used[names.USED_FRONT])}"
            f"（いつもの傾き: 内 {_points(used[names.COURSE_INNER])}・前 {_points(used[names.COURSE_FRONT])}）。"
            f"内の分 = （使う内の傾き − いつもの内の傾き）× 内らしさ（最内 +0.5〜大外 −0.5）、前の分 = （使う前の傾き − いつもの前の傾き）× 予想の前らしさ（展開の予想④）。"
            f"バイアス補正は3着以内の確率のポイント。線 ±{judge._line:g} でバイアス向き・バイアス逆")
    return Table(HORSE_COLUMNS, rows, title=f"トラックバイアス: {title}", note=note)


def _rids(con, args) -> list[str]:
    if args.all:
        if not args.date or args.rid or args.race:
            raise ValueError("--all は --date（と --venue）と合わせて使います")
        cards = card.list_cards(con, date_from=args.date, date_to=args.date, venue=args.venue)
        if not cards.rows:
            raise LookupError(f"{args.date} のレースが DB にありません")
        rid_at = cards.columns.index("rid")
        return [row[rid_at] for row in cards.rows]
    if args.rid:
        return [args.rid]
    if args.date and args.venue and args.race:
        return [race.resolve_rid(con, args.date, args.venue, args.race)]
    raise ValueError("レースを指定します: rid か --date --venue --race、またはその日の全レースなら --date --all")


def _points(value) -> str:
    return "" if value is None or value != value else f"{value:+.3f}"


def _plain(value):
    return None if value is None or value != value else int(value)


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("rid", nargs="?", help="レースの rid（16桁）")
    parser.add_argument("--date", help="開催日（YYYY-MM-DD）")
    parser.add_argument("--venue", help="競馬場（東京・中山 … かコード）")
    parser.add_argument("--race", type=int, help="レース番号")
    parser.add_argument("--all", action="store_true", help="--date の日の全レース（--venue で絞れる）")
    parser.add_argument("--timing", choices=[timing.label for timing in PredictionTiming], default=None,
                        help="時点を指定する（省略すると DB の情報から自動で選ぶ）")
    parser.add_argument("--line", type=float, default=DEFAULT_LINE, help=f"バイアス向き・バイアス逆の線（既定: {DEFAULT_LINE:g}）")
    parser.add_argument("--rebuild", action="store_true", help="傾きの表を作り直す（元DB が更新されたときは自動で作り直す）")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE_FOLDER, help="傾きの表をとっておく場所（既定: reports/トラックバイアス/cache）")
    parser.add_argument("--development-root", type=Path, default=DEFAULT_DEVELOPMENT_ROOT,
                        help="予想「展開から着順を予想」の置き場所（既定: reports/展開から着順を予想。その models/ を読む）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
