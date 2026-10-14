"""重賞（G1・G2・G3）のレースの同定と、「その重賞の過去の開催の出走馬」の読み出し。

重賞は毎年ほぼ同じ条件で行われるので、「そのレースならでは」の傾向（このレースでは、どの前走から来た馬・どの枠・
どの人気の馬が走るか、など）を過去の開催から数えられる。ここには、その土台を置く。

- **レースの同定は 特別競走番号で行う。** 競走名は年によって変わる（冠スポンサーの変更など）が、
  特別競走番号は変わらない（2011年以降の中央の重賞で、名前が別の番号に移った例は無いことを確かめた）。
- **過去の開催は「そのレースより前の開催」だけ**（リークなし）。対象のレースごとに、同じ特別競走番号で開催日が前の
  開催の出走馬を並べる（``edition_runners_sql``）。予想モデルの特徴量（``yosou.shared.repository.StakesTendencyRepository``）は
  これを読み、「自分と同じ条件（前走のレース・枠・人気など）だった馬の成績」を数える。重賞全体やコースの基準とは比べない。
- 分析のページ（``tools/重賞攻略/``）は同じ対応表（``stakes_map``）で重賞を見分ける。

    from 共通 import db, facts, stakes
    con = db.connect(db.resolve_db())
    facts.ensure_facts(con)
    stakes.ensure_stakes_map(con)
    rows = con.execute(stakes.edition_runners_sql(facts.FACTS_TABLE)).df()
"""

from __future__ import annotations

import duckdb

from . import facts, keys

#: 重賞のレースの対応表（rid → 特別競走番号・グレード・競走名）の一時表の名前。
STAKES_MAP_TABLE = "stakes_map"
#: グレードコード → 呼び名。障害の重賞（F・G・H = J・G1〜J・G3）は含めない（予想の対象は平地だけ）。
GRADE_NAMES: dict[str, str] = {"A": "G1", "B": "G2", "C": "G3"}
#: そのレースの行として使わないデータ区分（削除・レース中止）。
_DEAD_STAGES: tuple[str, ...] = ("0", "9")
#: 「休み明け」とみなす前走からの日数（中9週以上）。
REST_INTERVAL_DAYS = 63
#: 「前に行った馬」とみなす脚質判定。最初のコーナーの順位ではなく脚質判定を使うのは、
#: コーナーを5回以上通るコース（中山2500mなど）では最初のコーナーの順位が取れないのと、
#: 脚質判定のほうがレースごとの傾向の持続性が強かったため（前後半の相関 0.49 対 0.37）。
FRONT_STYLES: tuple[str, ...] = ("逃げ", "先行")
#: 「内枠」とみなす枠番。
INNER_FRAME_NO = 3
#: 前走のレースの鍵（``prev_key``）のうち、中央の確定成績に前走が無い馬（初出走・地方・海外帰り）の値。
NO_PREV_KEY = "前走なし"
#: 前走が重賞のときの鍵の頭。競走名でなく特別競走番号で見分ける（名前は年によって変わる）。
_STAKES_KEY_PREFIX = "重賞 "


def stakes_map_sql() -> str:
    """重賞のレースごとに1行（race_id・特別競走番号・グレード・競走名）を返す SQL。

    確定前の行（出走馬名表・出馬表）も入れる。これから走る重賞の予測に、そのレースの
    特別競走番号が要るため。同じレースに複数の行があれば最新の1行。中央だけ。
    """
    rid = keys.rid_expr()
    grades = keys.sql_list(GRADE_NAMES)
    return f"""
    SELECT {rid} AS race_id, "特別競走番号" AS stakes_no,
           trim("グレードコード") AS grade, trim("競走名本題") AS stakes_name,
           {keys.race_date_expr()} AS race_date
    FROM ra
    WHERE trim("グレードコード") IN {grades} AND "データ区分" NOT IN {keys.sql_list(_DEAD_STAGES)}
      AND {keys.jra_only()}
    {keys.latest_qualify(keys.RACE_KEY)}
    """


def ensure_stakes_map(con: duckdb.DuckDBPyConnection, name: str = STAKES_MAP_TABLE) -> str:
    """重賞のレースの対応表（一時表）が無ければ作る。表の名前を返す。"""
    exists = con.execute(
        "SELECT count(*) FROM duckdb_tables() WHERE table_name = ? AND temporary", [name],
    ).fetchone()[0]
    if not exists:
        con.execute(f"CREATE TEMP TABLE {keys.q(name)} AS {stakes_map_sql()}")
    return name


#: 過去の開催の出走馬の行が持つ、馬の条件と結果の列（名前, 型）。対象の行（``is_target``）ではどれも NULL。
RUNNER_COLUMNS: tuple[tuple[str, str], ...] = (
    ("finish", "INTEGER"), ("popularity", "INTEGER"), ("win_odds", "DOUBLE"), ("frame_no", "INTEGER"),
    ("style", "VARCHAR"), ("interval_days", "INTEGER"), ("affiliation", "VARCHAR"), ("same_race_places_before", "INTEGER"),
    ("age", "INTEGER"), ("sex", "VARCHAR"), ("prev_finish", "INTEGER"), ("prev_popularity", "INTEGER"),
    ("win_payout", "DOUBLE"), ("place_payout", "DOUBLE"),
)


def _prev_key_sql(prev: str, prev_map: str) -> str:
    """前走のレースの鍵。重賞なら特別競走番号、特別競走なら競走名、平場ならクラス名、前走が無ければ ``NO_PREV_KEY``。"""
    return f"""CASE WHEN {prev_map}.stakes_no IS NOT NULL THEN '{_STAKES_KEY_PREFIX}' || {prev_map}.stakes_no
                WHEN {prev}.prev_race_name IS NOT NULL AND {prev}.prev_race_name <> '' THEN {prev}.prev_race_name
                WHEN {prev}.prev_class_name IS NOT NULL THEN {prev}.prev_class_name
                ELSE '{NO_PREV_KEY}' END"""


def edition_runners_sql(target: str) -> str:
    """対象の重賞のレースごとに、それより前の開催の出走馬を並べる SQL（対象の馬の行も付ける）。

    ``target`` は SQL の FROM に置ける関係（表の名前か、かっこで包んだ SELECT）。レース単位の列 ``race_id``・``race_date`` と
    馬の列 ``horse_id`` を持てばよい（事実表も、確定前のレースの ``entry_facts`` も渡せる）。重賞でないレースの行は返さない。

    返す行は2種類で、``is_target`` で見分ける。

    - 偽: 過去の開催の出走馬。1行 = 対象のレース（``target_race_id``）× その重賞のそれより前の開催の1頭。
      列は 開催の同定（``race_id``・``stakes_no``・``race_date``・``horse_id``）、条件と結果（``RUNNER_COLUMNS``。
      ``style``・``popularity``・``win_odds`` はその開催の確定値、``win_payout``・``place_payout`` は 100円あたりの払戻で外れは 0）、
      前走のレースの鍵 ``prev_key``。
    - 真: 対象の馬そのもの。1行 = 対象のレースの1頭。``prev_key`` だけが意味を持つ（出走の行には前走のレース名が無いため）。
      条件と結果の列は NULL。

    どちらも、そのレースの開催日より前の確定成績だけから作る（リークなし）。
    """
    stakes_map = keys.q(STAKES_MAP_TABLE)
    facts_table = facts.FACTS_TABLE
    runner_columns = ", ".join(f"CAST(f.{name} AS {kind}) AS {name}" for name, kind in RUNNER_COLUMNS)
    empty_columns = ", ".join(f"NULL::{kind} AS {name}" for name, kind in RUNNER_COLUMNS)
    runner_names = ", ".join(name for name, _ in RUNNER_COLUMNS)
    latest = "p.race_date || p.race_id"
    return f"""
    WITH target_race AS (
        SELECT DISTINCT t.race_id, CAST(t.race_date AS DATE) AS race_date, m.stakes_no
        FROM {target} t
        JOIN {stakes_map} m USING (race_id)
    ), target_horse AS (
        SELECT t.race_id, CAST(t.horse_id AS VARCHAR) AS horse_id, r.race_date, r.stakes_no
        FROM {target} t
        JOIN target_race r USING (race_id)
    ), ran_row AS (
        SELECT race_id, race_date, horse_id, race_name, class_name
        FROM {facts_table}
        WHERE ran
    ), prev_of_runner AS (
        -- 馬ごとの1つ前の出走（出走した行だけ）
        SELECT race_id, horse_id,
               lag(race_id) OVER w AS prev_race_id, lag(race_name) OVER w AS prev_race_name,
               lag(class_name) OVER w AS prev_class_name
        FROM ran_row
        WINDOW w AS (PARTITION BY horse_id ORDER BY race_date, race_id)
    ), prev_of_target AS (
        -- 対象の馬の、そのレースより前の最後の出走（確定前の行は事実表に無いので、別に引く）
        SELECT h.race_id, h.horse_id,
               arg_max(p.race_id, {latest}) AS prev_race_id, arg_max(p.race_name, {latest}) AS prev_race_name,
               arg_max(p.class_name, {latest}) AS prev_class_name
        FROM target_horse h
        JOIN ran_row p ON p.horse_id = h.horse_id AND CAST(p.race_date AS DATE) < h.race_date
        GROUP BY 1, 2
    ), edition_runner AS (
        -- 重賞の確定成績の出走馬（過去の開催になりうる行）
        SELECT f.race_id, m.stakes_no, CAST(f.race_date AS DATE) AS race_date, f.horse_id,
               {runner_columns},
               {_prev_key_sql("p", "pm")} AS prev_key
        FROM {facts_table} f
        JOIN {stakes_map} m USING (race_id)
        LEFT JOIN prev_of_runner p ON p.race_id = f.race_id AND p.horse_id = f.horse_id
        LEFT JOIN {stakes_map} pm ON pm.race_id = p.prev_race_id
        WHERE f.ran
    )
    SELECT t.race_id AS target_race_id, FALSE AS is_target,
           e.race_id, e.stakes_no, e.race_date, e.horse_id, {runner_names}, e.prev_key
    FROM target_race t
    JOIN edition_runner e ON e.stakes_no = t.stakes_no AND e.race_date < t.race_date
    UNION ALL
    SELECT h.race_id AS target_race_id, TRUE AS is_target,
           h.race_id, h.stakes_no, h.race_date, h.horse_id, {empty_columns},
           {_prev_key_sql("p", "pm")} AS prev_key
    FROM target_horse h
    LEFT JOIN prev_of_target p ON p.race_id = h.race_id AND p.horse_id = h.horse_id
    LEFT JOIN {stakes_map} pm ON pm.race_id = p.prev_race_id
    """
