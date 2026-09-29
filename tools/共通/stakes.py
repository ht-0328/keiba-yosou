"""重賞（G1・G2・G3）のレースの同定と、レースごとの傾向の数え上げ。

重賞は毎年ほぼ同じ条件で行われるので、「そのレースならでは」の傾向（1番人気がどれだけ信頼できるか、
前に行く馬・内枠がどれだけ有利か、など）を過去の開催から数えられる。ここには、その土台を置く。

- **レースの同定は 特別競走番号で行う。** 競走名は年によって変わる（冠スポンサーの変更など）が、
  特別競走番号は変わらない（2011年以降の中央の重賞で、名前が別の番号に移った例は無いことを確かめた）。
- **傾向は「そのレースより前の開催」だけから数える**（リークなし）。同じ数え方を、分析のページ
  （``tools/重賞攻略/``）と予想モデルの特徴量（``yosou.shared.repository.StakesTendencyRepository``）の
  両方が使い、二重に定義しない。
- 傾向の「ずれ」は基準と比べて初めて意味を持つ。人気・ローテ・所属のずれは**同じグレードの重賞**を、
  脚質・枠のずれは**同じ競馬場・コース・距離の全クラスのレース**を基準にする。基準も「その日より前」だけから数える。

    from 共通 import db, facts, stakes
    con = db.connect(db.resolve_db())
    facts.ensure_facts(con)
    stakes.ensure_stakes_map(con)
    rows = con.execute(stakes.tendency_sql(facts.FACTS_TABLE)).df()
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


def _edition_agg_sql() -> str:
    """重賞の過去の開催（確定成績）ごとの数え上げ。1行 = 1開催。

    列は 開催の同定（race_id・stakes_no・grade・race_date）と、切り口ごとの 出走数 ``*_n``・3着以内の数 ``*_hits``。
    """
    return f"""
    SELECT f.race_id, m.stakes_no, m.grade, f.race_date,
           count(*) FILTER (f.popularity = 1) AS fav1_n,
           count(*) FILTER (f.popularity = 1 AND f.finish <= 3) AS fav1_hits,
           count(*) FILTER (f.popularity <= 3) AS fav123_n,
           count(*) FILTER (f.popularity <= 3 AND f.finish <= 3) AS fav123_hits,
           count(*) FILTER (f.style IN {keys.sql_list(FRONT_STYLES)}) AS front_n,
           count(*) FILTER (f.style IN {keys.sql_list(FRONT_STYLES)} AND f.finish <= 3) AS front_hits,
           coalesce(sum(3.0 / f.field_size) FILTER (f.style IN {keys.sql_list(FRONT_STYLES)}), 0) AS front_exp,
           count(*) FILTER (f.frame_no <= {INNER_FRAME_NO}) AS inner_n,
           count(*) FILTER (f.frame_no <= {INNER_FRAME_NO} AND f.finish <= 3) AS inner_hits,
           coalesce(sum(3.0 / f.field_size) FILTER (f.frame_no <= {INNER_FRAME_NO}), 0) AS inner_exp,
           count(*) FILTER (f.interval_days >= {REST_INTERVAL_DAYS}) AS rest_n,
           count(*) FILTER (f.interval_days >= {REST_INTERVAL_DAYS} AND f.finish <= 3) AS rest_hits,
           count(*) FILTER (f.affiliation = '栗東') AS west_n,
           count(*) FILTER (f.affiliation = '栗東' AND f.finish <= 3) AS west_hits,
           count(*) FILTER (f.same_race_places_before >= 1) AS repeat_n,
           count(*) FILTER (f.same_race_places_before >= 1 AND f.finish <= 3) AS repeat_hits
    FROM {facts.FACTS_TABLE} f
    JOIN {keys.q(STAKES_MAP_TABLE)} m USING (race_id)
    WHERE f.ran
    GROUP BY 1, 2, 3, 4
    """


def _course_agg_sql() -> str:
    """競馬場・コース・距離ごと、開催日ごとの数え上げ（平地の全クラス）。脚質・枠の基準に使う。"""
    return f"""
    SELECT venue, course, distance_m, race_date,
           count(*) FILTER (style IN {keys.sql_list(FRONT_STYLES)}) AS front_n,
           count(*) FILTER (style IN {keys.sql_list(FRONT_STYLES)} AND finish <= 3) AS front_hits,
           coalesce(sum(3.0 / field_size) FILTER (style IN {keys.sql_list(FRONT_STYLES)}), 0) AS front_exp,
           count(*) FILTER (frame_no <= {INNER_FRAME_NO}) AS inner_n,
           count(*) FILTER (frame_no <= {INNER_FRAME_NO} AND finish <= 3) AS inner_hits,
           coalesce(sum(3.0 / field_size) FILTER (frame_no <= {INNER_FRAME_NO}), 0) AS inner_exp
    FROM {facts.FACTS_TABLE}
    WHERE ran AND surface <> '障害'
    GROUP BY 1, 2, 3, 4
    """


def tendency_sql(target: str) -> str:
    """対象のレースごとに、それより前の開催から数えた傾向を付ける SQL。

    ``target`` は SQL の FROM に置ける関係（表の名前か、かっこで包んだ SELECT）。
    レース単位の列 ``race_id``・``race_date``・``venue``・``course``・``distance_m`` を持てばよい
    （事実表も、確定前のレースの ``entry_facts`` も渡せる）。重賞でないレースの行は返さない。

    返す列は、開催の同定（``race_id``・``stakes_no``・``grade``・``editions`` = 過去の開催の数）、
    切り口ごとの過去の 出走数 ``*_n``・3着以内の数 ``*_hits``、基準 ``base_*``
    （人気・休み明け・関西馬・好走経験は同じグレードの重賞の3着以内率、前・内枠は同じ競馬場・コース・距離の
    全クラスの**超過複勝率**（3着以内率 − 3÷頭数。頭数の違いをならすため）。前・内枠は自分の側にも
    期待の数 ``front_exp``・``inner_exp``（3÷頭数の合計）が付く。どの基準も、そのレースの開催日より前だけから数える）。
    """
    return f"""
    WITH target_race AS (
        SELECT DISTINCT t.race_id, t.race_date, t.venue, t.course, t.distance_m,
               m.stakes_no, m.grade
        FROM {target} t
        JOIN {keys.q(STAKES_MAP_TABLE)} m USING (race_id)
    ), edition AS (
        {_edition_agg_sql()}
    ), course_day AS (
        {_course_agg_sql()}
    ), past AS (
        -- 同じ重賞の、そのレースより前の開催の数え上げ
        SELECT t.race_id, count(e.race_id) AS editions,
               coalesce(sum(e.fav1_n), 0) AS fav1_n, coalesce(sum(e.fav1_hits), 0) AS fav1_hits,
               coalesce(sum(e.fav123_n), 0) AS fav123_n, coalesce(sum(e.fav123_hits), 0) AS fav123_hits,
               coalesce(sum(e.front_n), 0) AS front_n, coalesce(sum(e.front_hits), 0) AS front_hits,
               coalesce(sum(e.front_exp), 0) AS front_exp,
               coalesce(sum(e.inner_n), 0) AS inner_n, coalesce(sum(e.inner_hits), 0) AS inner_hits,
               coalesce(sum(e.inner_exp), 0) AS inner_exp,
               coalesce(sum(e.rest_n), 0) AS rest_n, coalesce(sum(e.rest_hits), 0) AS rest_hits,
               coalesce(sum(e.west_n), 0) AS west_n, coalesce(sum(e.west_hits), 0) AS west_hits,
               coalesce(sum(e.repeat_n), 0) AS repeat_n, coalesce(sum(e.repeat_hits), 0) AS repeat_hits
        FROM target_race t
        LEFT JOIN edition e ON e.stakes_no = t.stakes_no AND e.race_date < t.race_date
        GROUP BY 1
    ), grade_base AS (
        -- 同じグレードの重賞全体の基準（そのレースより前）
        SELECT t.race_id,
               sum(e.fav1_hits) / nullif(sum(e.fav1_n), 0) AS base_fav1,
               sum(e.fav123_hits) / nullif(sum(e.fav123_n), 0) AS base_fav123,
               sum(e.rest_hits) / nullif(sum(e.rest_n), 0) AS base_rest,
               sum(e.west_hits) / nullif(sum(e.west_n), 0) AS base_west,
               sum(e.repeat_hits) / nullif(sum(e.repeat_n), 0) AS base_repeat
        FROM target_race t
        LEFT JOIN edition e ON e.grade = t.grade AND e.race_date < t.race_date
        GROUP BY 1
    ), course_base AS (
        -- 同じ競馬場・コース・距離の全クラスの基準（そのレースより前）。
        -- 複勝率（3着内率）は頭数が少ないほど高く出るので、頭数から見た期待複勝率（3÷頭数）を引いた
        -- 「超過複勝率」で持つ（重賞はフルゲートが多く、そのまま比べると不利に見えるため）。
        SELECT t.race_id,
               (sum(c.front_hits) - sum(c.front_exp)) / nullif(sum(c.front_n), 0) AS base_front_excess,
               (sum(c.inner_hits) - sum(c.inner_exp)) / nullif(sum(c.inner_n), 0) AS base_inner_excess
        FROM target_race t
        LEFT JOIN course_day c ON c.venue = t.venue AND c.course = t.course
                              AND c.distance_m = t.distance_m AND c.race_date < t.race_date
        GROUP BY 1
    )
    SELECT t.race_id, t.stakes_no, t.grade, p.editions,
           p.fav1_n, p.fav1_hits, p.fav123_n, p.fav123_hits,
           p.front_n, p.front_hits, p.front_exp, p.inner_n, p.inner_hits, p.inner_exp,
           p.rest_n, p.rest_hits, p.west_n, p.west_hits, p.repeat_n, p.repeat_hits,
           g.base_fav1, g.base_fav123, g.base_rest, g.base_west, g.base_repeat,
           c.base_front_excess, c.base_inner_excess
    FROM target_race t
    JOIN past p USING (race_id)
    JOIN grade_base g USING (race_id)
    JOIN course_base c USING (race_id)
    """
