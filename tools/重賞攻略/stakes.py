"""重賞（G1・G2・G3）ごとの「攻略ポイント」を、過去の開催のずれから出す。

    uv run python tools/重賞攻略/stakes.py --list                    # 重賞の一覧（番号・名前・開催数）
    uv run python tools/重賞攻略/stakes.py --name 有馬               # 名前（部分一致）で1レースのページを出す
    uv run python tools/重賞攻略/stakes.py --no 0006                 # 特別競走番号で
    uv run python tools/重賞攻略/stakes.py --all                     # 全重賞のページと索引を reports/重賞攻略/ に書く
    uv run python tools/重賞攻略/stakes.py --name 有馬 --before 2025-12-01   # その日より前の開催だけで数える

どのレースでも成り立つ一般論（1番人気や前に行く馬が走る）ではなく、**そのレースならではのずれ**を出す。
人気の信頼度は同じグレードの重賞全体と、脚質の前・枠の内はそのコースの全クラスと、
年齢・ローテなどはそのレースのほかの出走馬と比べ、ずれの大きさ・検定の印・回収率を添える。
持続性の注意（人気・脚質・枠は年をまたいで持続しやすい、荒れ度などは入れ替わりやすい）もページに書く。

予想モデル「重賞の傾向と近走から3着以内を予想」の特徴量は、同じ数え上げ（tools/共通/stakes.py）を使う。
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from 共通 import cli, db, facts  # noqa: E402
from 共通.render import Table  # noqa: E402
from 重賞攻略 import loading, page  # noqa: E402

#: --all の既定の出力先（Git 対象外）。
DEFAULT_OUT_DIR = Path("reports/重賞攻略")


def main(args) -> None:
    with db.open_db(args.db) as con:
        runners = loading.load_runners(con)
        course_rates = _course_rates(con)
    if args.before:
        limit = date.fromisoformat(args.before).isoformat()
        runners = runners[runners["race_date"].astype(str).str[:10] < limit]
        if runners.empty:
            raise ValueError(f"{args.before} より前の重賞の開催がありません")
    if args.list:
        cli.emit(_list_table(runners), args)
        return
    if args.all:
        _write_all(runners, course_rates, args.out_dir)
        return
    stakes_no = _chosen_stakes_no(runners, args)
    built = _build_one(runners, course_rates, stakes_no)
    _write_page_text(built.markdown, args.out)


def _course_rates(con) -> pd.DataFrame:
    """競馬場・コース・距離ごとの、全クラスの「前」「内枠」の複勝率（脚質・枠の基準）。"""
    from 共通 import keys, stakes as stakes_sql
    front_styles = keys.sql_list(stakes_sql.FRONT_STYLES)
    inner = stakes_sql.INNER_FRAME_NO
    return con.execute(f"""
    SELECT venue, course, distance_m,
           count(*) FILTER (style IN {front_styles}) AS front_n,
           avg(((finish <= 3)::int) - 3.0 / field_size) FILTER (style IN {front_styles}) AS front_excess,
           avg(((finish <= 3)::int) - 3.0 / field_size) FILTER (frame_no <= {inner}) AS inner_excess
    FROM {facts.FACTS_TABLE} WHERE ran AND surface <> '障害'
    GROUP BY 1, 2, 3
    """).df().set_index(["venue", "course", "distance_m"])


def _chosen_stakes_no(runners: pd.DataFrame, args) -> str:
    """--no か --name から、対象の重賞を1つに決める。決まらなければ候補を見せて誤りにする。"""
    if args.no:
        if (runners["stakes_no"] == args.no).any():
            return args.no
        raise ValueError(f"特別競走番号 {args.no} の重賞が見つかりません（--list で一覧）")
    if not args.name:
        raise ValueError("--list・--all・--name・--no のどれかを指定してください")
    names = loading.latest_names(runners)
    hits = names[names["stakes_name"].str.contains(args.name, regex=False)]
    if len(hits) == 1:
        return str(hits["stakes_no"].iloc[0])
    if hits.empty:
        raise ValueError(f"名前に「{args.name}」を含む重賞が見つかりません（--list で一覧）")
    candidates = "・".join(hits["stakes_name"])
    raise ValueError(f"候補が複数あります: {candidates}（--no で番号を指定してください）")


def _build_one(runners: pd.DataFrame, course_rates: pd.DataFrame, stakes_no: str) -> page.StakesPage:
    race_rows = runners[runners["stakes_no"] == stakes_no]
    grade = race_rows.loc[race_rows["race_date"].idxmax(), "grade"]
    grade_rows = runners[runners["grade"] == grade]
    return page.build_page(race_rows, grade_rows, _rates_of(course_rates, race_rows))


def _rates_of(course_rates: pd.DataFrame, race_rows: pd.DataFrame) -> pd.Series | None:
    """そのレースのコース（いちばん多く使われた組み合わせ）の基準の率。無ければ None。"""
    key = (race_rows.groupby(["venue", "course", "distance_m"]).size().idxmax())
    if key not in course_rates.index:
        return None
    return course_rates.loc[key]


def _list_table(runners: pd.DataFrame) -> Table:
    names = loading.latest_names(runners)
    grade_names = {"A": "G1", "B": "G2", "C": "G3"}
    rows = [[row["stakes_no"], grade_names.get(row["grade"], row["grade"]), row["stakes_name"],
             row["venue"], row["course"], row["distance_m"], row["editions"],
             f"{row['first_year']}〜{row['last_year']}"] for _, row in names.iterrows()]
    return Table(columns=["特別競走番号", "グレード", "競走名", "競馬場", "コース", "距離", "開催数", "期間"],
                 rows=rows, note=f"重賞 {len(rows)} レース（いちばん新しい開催の条件で表示）")


def _write_all(runners: pd.DataFrame, course_rates: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    pages: list[page.StakesPage] = []
    for stakes_no in loading.latest_names(runners)["stakes_no"]:
        built = _build_one(runners, course_rates, str(stakes_no))
        (out_dir / built.file_name).write_text(built.markdown, encoding="utf-8")
        pages.append(built)
    (out_dir / "README.md").write_text(_index_markdown(pages), encoding="utf-8")
    print(f"{len(pages)} レースのページと索引を {out_dir} に書きました")


def _index_markdown(pages: list[page.StakesPage]) -> str:
    lines = [
        "# 重賞攻略の索引", "",
        "レースごとの攻略ポイント（過去の開催の、基準からのずれ）。作り直すときは "
        "`uv run python tools/重賞攻略/stakes.py --all`。", "",
        "| グレード | 競走名 | 条件 | 開催数 | 攻略ポイント | 主なポイント |",
        "|" + " :--- |" * 6,
    ]
    grade_names = {"A": "G1", "B": "G2", "C": "G3"}
    for built in pages:
        first = built.findings[0].text.split(" — ")[0] if built.findings else "（有意なずれなし）"
        condition = f"{built.venue} {built.course} {built.distance_m}m"
        lines.append(
            f"| {grade_names.get(built.grade, built.grade)} | [{built.stakes_name}]({built.file_name}) "
            f"| {condition} | {built.editions} | {len(built.findings)} | {first} |")
    lines.append("")
    return "\n".join(lines)


def _write_page_text(markdown: str, out: Path | None) -> None:
    if out is None:
        sys.stdout.write(markdown)
        sys.stdout.flush()
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(markdown, encoding="utf-8")


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--list", action="store_true", help="重賞の一覧を出して終わる")
    parser.add_argument("--all", action="store_true", help=f"全重賞のページと索引を --out-dir（既定 {DEFAULT_OUT_DIR}）に書く")
    parser.add_argument("--name", help="競走名（部分一致）で1レースを選ぶ")
    parser.add_argument("--no", help="特別競走番号で1レースを選ぶ")
    parser.add_argument("--before", help="この開催日より前の開催だけで数える（YYYY-MM-DD。モデルが見る値の確かめ用）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="--all の出力先")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
