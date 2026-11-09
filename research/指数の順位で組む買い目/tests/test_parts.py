"""研究「指数の順位で組む買い目」の部品のテスト。値は架空（元DB は使わない）。"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from 指数の順位で組む買い目.analysis.repo_paths import RepoPaths  # noqa: E402

RepoPaths().add_to_sys_path()

from yosou.shared.betting import TicketType  # noqa: E402

from 指数の順位で組む買い目.analysis.baseline_summary import BaselineSummary  # noqa: E402
from 指数の順位で組む買い目.analysis.formation import BOX, Formation  # noqa: E402
from 指数の順位で組む買い目.analysis.formation_catalog import FormationCatalog  # noqa: E402
from 指数の順位で組む買い目.analysis.member_races import MemberRaces  # noqa: E402
from 指数の順位で組む買い目.analysis.payout_floor import PayoutFloor  # noqa: E402
from 指数の順位で組む買い目.analysis.period import CONFIRM, EXPLORE, WHOLE  # noqa: E402
from 指数の順位で組む買い目.analysis.period_table import PeriodTable  # noqa: E402
from 指数の順位で組む買い目.analysis.rank_span import RankSpan  # noqa: E402
from 指数の順位で組む買い目.analysis.rank_table import FIELD, RANK_TOP3, RANK_WIN, RankTable  # noqa: E402
from 指数の順位で組む買い目.analysis.row_spec import RowSpec  # noqa: E402
from 指数の順位で組む買い目.analysis.summary_table import SummaryTable  # noqa: E402
from 指数の順位で組む買い目.analysis.ticket_builder import COMBO, TicketBuilder  # noqa: E402
from 指数の順位で組む買い目.analysis.ticket_settlement import TicketSettlement  # noqa: E402
from 指数の順位で組む買い目.analysis.yearly_table import YearlyTable  # noqa: E402

BY_LABEL = FormationCatalog.by_label()


def _ranked() -> pd.DataFrame:
    """1レース 10頭。順位 r の馬番は 11 − r（1位 = 馬番 10 … 10位 = 馬番 1）。"""
    ranks = np.arange(1, 11)
    return pd.DataFrame({
        "race_id": "R1", "race_date": pd.Timestamp("2025-03-01"), "horse_no": 11 - ranks, RANK_TOP3: ranks, RANK_WIN: ranks, FIELD: 10,
        "finish": ranks, "popularity": ranks,
    })


@pytest.mark.parametrize("label, field, points", [
    ("単勝 1位", 18, 1), ("馬単 1位→2〜8位", 18, 7), ("馬単 2位→1位・3位", 18, 2),
    ("3連単 1位→2〜8位→2〜8位の残り", 18, 42), ("3連単 1位→2・3位→9位以下", 18, 20), ("3連単 1位→9位以下→2・3位", 18, 20),
    ("3連単 2位→1位→3〜8位", 18, 6), ("3連単 2位→3位→1位・4〜8位", 18, 6), ("3連単 3位→1・2位→1・2位の残り・4〜8位", 18, 12),
    ("3連単 4位→1位→2・3・5・6位", 18, 4), ("3連単 5位→1位→2〜4位・6位", 18, 4),
    ("ワイド 1位−2〜5位", 18, 4), ("馬連 1位−2〜8位", 18, 7), ("馬連 2位−3位", 18, 1),
    ("3連複 1位−2〜4位−3〜8位の残り", 18, 15), ("3連複 1位−2・3位−9位以下", 18, 20), ("3連複 1位−5〜7位−6〜8位の残り", 18, 6), ("3連複 2位−3位−4〜8位", 18, 5),
    ("上位5頭BOX 馬連", 18, 10), ("上位5頭BOX 馬単", 18, 20), ("上位5頭BOX 3連複", 18, 10), ("上位5頭BOX 3連単", 18, 60),
    # 頭数が足りないとき: 9位以下が無ければ 0点、2〜8位が 2〜6位になれば点数が減る
    ("3連単 1位→2・3位→9位以下", 8, 0), ("3連複 1位−2・3位−9位以下", 9, 2), ("馬単 1位→2〜8位", 6, 5), ("3連単 1位→2〜8位→2〜8位の残り", 6, 20),
    ("上位5頭BOX 3連単", 4, 24), ("3連単 5位→1位→2〜4位・6位", 5, 3),
])
def test_形ごとの点数はサイトの表のとおりで_頭数が足りない順位の組は作らない(label: str, field: int, points: int) -> None:
    assert len(BY_LABEL[label].rank_combos(field)) == points


def test_順番を問わない券種は同じ馬の組を1つにまとめ_順番を問う券種は分ける() -> None:
    trio = Formation("t", TicketType.TRIO, ((RankSpan(1, 1),), (RankSpan(2, 3),), (RankSpan(2, 3),)), ())
    assert trio.rank_combos(10) == [(1, 2, 3)]
    trifecta = Formation("t", TicketType.TRIFECTA, ((RankSpan(1, 1),), (RankSpan(2, 3),), (RankSpan(2, 3),)), ())
    assert trifecta.rank_combos(10) == [(1, 2, 3), (1, 3, 2)]


def test_列の数が券種の馬の数と合わなければ誤り() -> None:
    with pytest.raises(ValueError):
        Formation("t", TicketType.QUINELLA, ((RankSpan(1, 1),),), ())


def test_集計金額は固定の額か点数との掛け算() -> None:
    assert PayoutFloor(yen=5000).of(7) == 5000 and PayoutFloor(per_point=500).of(7) == 3500
    assert PayoutFloor(per_point=500).label == "点数×500円以上" and PayoutFloor(yen=10_000).label == "10,000円以上"
    with pytest.raises(ValueError):
        PayoutFloor()


def test_一覧には6券種と上位5頭BOXがあり_合計の行は券種ごととBOXと全部() -> None:
    assert [ticket.label for ticket in FormationCatalog.tickets()] == ["単勝", "馬単", "3連単", "ワイド", "馬連", "3連複"]
    assert all(formation.group == BOX for formation in FormationCatalog.boxes()) and len(FormationCatalog.boxes()) == 4
    labels = [spec.label for spec in FormationCatalog.row_specs()]
    assert "馬単 の形の合計" in labels and "3連単 の形の合計" in labels and "単勝 の形の合計" not in labels
    assert labels[-3:] == ["上位5頭BOX の合計", "全部の合計（BOX を除く）", "全部の合計（BOX を含む）"]


def test_順位は走った馬の中で確率の高い順_同じ確率は馬番の小さい順_取消は入らない() -> None:
    top3 = pd.DataFrame({"race_id": "R", "race_date": pd.Timestamp("2025-01-05"), "horse_id": ["a", "b", "c", "d"],
                         "horse_no": [1, 2, 3, 4], "probability": [0.3, 0.5, 0.5, 0.9]})
    win = pd.DataFrame({"race_id": "R", "horse_id": ["a", "b", "c", "d"], "probability": [0.4, 0.1, 0.2, np.nan]})
    results = pd.DataFrame({"race_id": "R", "horse_id": ["a", "b", "c"], "horse_no": [1, 2, 3], "finish": [1, 2, 3], "popularity": [3, 1, 2]})
    ranked = RankTable().build(top3, win, results)
    by_no = ranked.set_index("horse_no")
    assert list(by_no.index) == [2, 3, 1]                    # 3着以内の順（d は取消で入らない）
    assert by_no.loc[[1, 2, 3], RANK_TOP3].tolist() == [3, 1, 2]
    assert by_no.loc[[1, 2, 3], RANK_WIN].tolist() == [1, 3, 2]
    assert (ranked[FIELD] == 3).all()


def test_買い目は順位を馬番に写し_順番を問わない券種は馬番を昇順に並べる() -> None:
    ranked = _ranked()
    exacta = TicketBuilder().build(ranked, RANK_TOP3, BY_LABEL["馬単 2位→1位・3位"])
    assert sorted(exacta[COMBO].tolist()) == [908, 910]        # 2位 = 馬番 9 → 1位 10・3位 8
    quinella = TicketBuilder().build(ranked, RANK_TOP3, BY_LABEL["馬連 2位−3位"])
    assert quinella[COMBO].tolist() == [809]                    # 昇順（08-09）
    trio = TicketBuilder().build(ranked, RANK_TOP3, BY_LABEL["3連複 1位−2・3位−9位以下"])
    assert sorted(trio[COMBO].tolist()) == [10810, 10910, 20810, 20910]  # 1位 10・2位 9/3位 8・9位 2/10位 1 を馬番の昇順に
    win = TicketBuilder().build(ranked, RANK_TOP3, BY_LABEL["単勝 1位"])
    assert win[COMBO].tolist() == [10]


def test_買い目は頭数ごとにまとめて作り_レースをまたいでも同じ組になる() -> None:
    first = _ranked()
    second = _ranked().assign(race_id="R2", horse_no=lambda t: 12 - t[RANK_TOP3])   # 1位 = 馬番 11
    small = _ranked().head(6).assign(race_id="R3", **{FIELD: 6})                       # 6頭（9位以下は無い）
    ranked = pd.concat([first, second, small], ignore_index=True)
    tickets = TicketBuilder().build(ranked, RANK_TOP3, BY_LABEL["馬単 1位→2〜8位"])
    assert tickets.groupby("race_id").size().to_dict() == {"R1": 7, "R2": 7, "R3": 5}
    assert sorted(tickets[tickets["race_id"] == "R2"][COMBO].tolist()) == [1104, 1105, 1106, 1107, 1108, 1109, 1110]
    none = TicketBuilder().build(small, RANK_TOP3, BY_LABEL["3連単 1位→2・3位→9位以下"])
    assert none.empty


def test_精算は組の数で払戻を当て_レースごとに点数と払戻と的中にまとめる() -> None:
    tickets = pd.DataFrame({"race_id": ["A", "A", "A", "B", "B"], COMBO: [102, 103, 104, 102, 103]})
    payouts = pd.DataFrame({"race_id": ["A", "C"], COMBO: [103, 102], "payout": [1250.0, 300.0]})
    settled = TicketSettlement().settle(tickets, payouts).set_index("race_id")
    assert settled.loc["A", "points"] == 3 and settled.loc["A", "payout"] == 1250.0 and bool(settled.loc["A", "hit"])
    assert settled.loc["B", "points"] == 2 and settled.loc["B", "payout"] == 0.0 and not bool(settled.loc["B", "hit"])
    assert TicketSettlement().settle(tickets.iloc[0:0], payouts).empty


def _settled() -> pd.DataFrame:
    """2つの形 × 3レース（2024年 2レース・2025年 1レース）。"""
    return pd.DataFrame({
        "timing": "当日", "ranking": "3着以内の確率の順", "group": "形",
        "formation": ["単勝 1位"] * 3 + ["馬単 1位→2〜8位"] * 3, "ticket": ["単勝"] * 3 + ["馬単"] * 3,
        "race_id": ["A", "B", "C"] * 2,
        "race_date": [pd.Timestamp("2024-01-06"), pd.Timestamp("2024-01-07"), pd.Timestamp("2025-01-05")] * 2,
        "points": [1, 1, 1, 7, 7, 7], "payout": [250.0, 0.0, 0.0, 0.0, 0.0, 4200.0],
    }).assign(hit=lambda t: t["payout"] > 0)


def test_合計の行はレースごとに点数と払戻を足し_どれかが当たれば的中() -> None:
    spec = RowSpec("合計", "2券種", ("単勝 1位", "馬単 1位→2〜8位"))
    merged = MemberRaces().of(_settled(), spec).set_index("race_id")
    assert merged.loc["A", "points"] == 8 and merged.loc["A", "payout"] == 250.0 and bool(merged.loc["A", "hit"])
    assert merged.loc["B", "points"] == 8 and not bool(merged.loc["B", "hit"])
    assert merged.loc["C", "payout"] == 4200.0


def test_期間の表は探索と確認に分け_実額なしの表には投資と払戻の列が無い() -> None:
    specs = [RowSpec("単勝 1位", "単勝", ("単勝 1位",), (PayoutFloor(yen=500),)),
             RowSpec("馬単 1位→2〜8位", "馬単", ("馬単 1位→2〜8位",), (PayoutFloor(per_point=500), PayoutFloor(yen=5000)))]
    table = PeriodTable(specs, [EXPLORE, CONFIRM, WHOLE], with_yen=True).table(_settled(), "t")
    rows = {(row[0], row[2]): row for row in table.rows}
    win_explore = rows[("単勝 1位", EXPLORE.label)]
    assert win_explore[3] == "2" and win_explore[4] == "2" and win_explore[7] == "200円" and win_explore[8] == "250円" and win_explore[9] == "125.0%"
    assert win_explore[11] == "1" and win_explore[12] == "50.0%"
    assert win_explore[13] == "0.0%（500円以上）"                       # 250円の的中は集計金額に届かない
    exacta_confirm = rows[("馬単 1位→2〜8位", CONFIRM.label)]
    assert exacta_confirm[4] == "7" and exacta_confirm[9] == "600.0%" and exacta_confirm[13] == "100.0%（点数×500円以上） ／ 0.0%（5,000円以上）"
    assert rows[("単勝 1位", CONFIRM.label)][12] == "0.0%"
    docs = PeriodTable(specs, [WHOLE], with_yen=False).table(_settled(), "t")
    assert "投資" not in docs.columns and "払戻" not in docs.columns and len(docs.rows[0]) == len(docs.columns)
    # 残る「円」は 1レースの金額（点数 × 100円）と集計金額の線だけで、払戻の実額は無い
    assert all("円" not in cell for row in docs.rows for cell in row[3:6] + row[7:-1])


def test_要約の表は探索と確認の回収率と的中率を1行に並べ_実額を出さない() -> None:
    specs = [RowSpec("単勝 1位", "単勝", ("単勝 1位",), (PayoutFloor(yen=500),)), RowSpec("無い形", "馬連", ("無い形",))]
    table = SummaryTable(specs, [EXPLORE, CONFIRM]).table(_settled(), "t")
    assert table.columns[4:8] == [f"{EXPLORE.label} 回収率", f"{EXPLORE.label} 的中率", f"{CONFIRM.label} 回収率", f"{CONFIRM.label} 的中率"]
    assert table.rows == [["単勝 1位", "単勝", "1.0", "100円", "125.0%", "50.0%", "0.0%", "0.0%", "0.0%（500円以上）"]]   # 無い形の行は出ない


def test_年ごとの表は回収率と的中率を年の列に並べる() -> None:
    specs = [RowSpec("単勝 1位", "単勝", ("単勝 1位",))]
    recovery, hits = YearlyTable(specs).tables(_settled(), "t")
    assert recovery.columns == ["形", "券種", "2024", "2025"]
    assert recovery.rows[0] == ["単勝 1位", "単勝", "125.0%", "0.0%"]
    assert hits.rows[0] == ["単勝 1位", "単勝", "50.0%", "0.0%"]


def test_比べる相手は印の成績の買い目のCSVから外した理由の無い買い目をレースごとにまとめる(tmp_path: Path) -> None:
    csv = tmp_path / "買い目.csv"
    pd.DataFrame({
        "レースID": ["A", "A", "A", "B", "B"], "開催日": ["2025-01-05"] * 3 + ["2025-01-06"] * 2, "区切り": "2025年前半", "期待度": "高",
        "買い方": ["単勝", "馬連", "馬連", "単勝", "3連複（◎軸）"], "券種": ["単勝", "馬連", "馬連", "単勝", "3連複"],
        "組番": ["01", "0102", "0103", "02", "010203"], "単位": 1.0, "期待値": np.nan, "組の確率": np.nan, "確定オッズ": 3.0,
        "払戻（100円あたり）": [300.0, 0.0, 800.0, 0.0, 5000.0], "外した理由": [None, None, "トリガミ", None, None],
    }).to_csv(csv, index=False, encoding="utf-8-sig")
    table = BaselineSummary().summarize(csv, chunk_rows=2).set_index(["formation", "race_id"])
    assert table.loc[("単勝", "A"), "payout"] == 300.0 and bool(table.loc[("単勝", "A"), "hit"])
    assert table.loc[("馬連", "A"), "points"] == 1 and table.loc[("馬連", "A"), "payout"] == 0.0     # トリガミの1点は数えない
    assert ("3連複（◎軸）", "B") not in table.index                                                   # 比べる相手の買い方ではない
    assert table.loc[("単勝", "B"), "ticket"] == "単勝" and table.loc[("単勝", "A"), "race_date"] == pd.Timestamp("2025-01-05")
