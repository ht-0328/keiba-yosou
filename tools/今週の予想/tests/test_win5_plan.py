"""WIN5 の買う計画（Win5Record・Win5Planner・Win5BetRecorder・Win5Section と、まとめ・財布・表1とのつながり）のテスト。値は架空。"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from yosou.review import ReviewStore, names

from 今週の予想.bet_recorder import BetRecorder
from 今週の予想.day_summary import DaySummary
from 今週の予想.forecast_store import ForecastStore
from 今週の予想.plan_store import PlanStore
from 今週の予想.race_plan import RacePlan
from 今週の予想.tests.test_day_summary import WALLET
from 今週の予想.tests.test_forecast_store import sample_forecast
from 今週の予想.ticket_pick import TicketPick
from 今週の予想.wallet import POLICY_WALLET, Wallet
from 今週の予想.win5_bet_recorder import Win5BetRecorder
from 今週の予想.win5_combo import combo_legs, combo_text
from 今週の予想.win5_decision import Win5Decision
from 今週の予想.win5_plan import POLICY_NOTE
from 今週の予想.win5_planner import Win5Planner
from 今週の予想.win5_record import Win5Record
from 今週の予想.win5_record_store import WIN5_YOSOU_NAME, Win5RecordStore
from 今週の予想.win5_section import Win5Section

DAY = date(2025, 4, 20)
#: 対象レース5つ（東京 10R・京都 10R・福島 11R・東京 11R・京都 11R の架空の rid）。
LEGS = ("2025042005010210", "2025042008010210", "2025042003010211", "2025042005010211", "2025042008010211")
#: 多く買う日の買い目（3×2×2×1×4 = 48点）と、少なく買う日・見送りの参考の買い目（2×1×2×1×3 = 12点）。
PICKS = ((10, 5, 3), (6, 8), (2, 5), (4,), (11, 4, 10, 15))
SMALL_PICKS = ((10, 5), (6,), (2, 5), (4,), (11, 4, 10))
#: 判断の文字。
LARGE, SMALL, SKIP = "買う（多く）", "買う（少なく）", "見送り"
_TIERS = {LARGE: "多く", SMALL: "少なく", SKIP: "見送り"}


def _legs(picks_by_leg: tuple[tuple[int, ...], ...]) -> list[dict]:
    return [{"レースID": rid, "使った確率": "当日" if number < 4 else "前日", "理由": "架空", "オッズの断面": "04201400",
             "買い目": list(picks),
             "馬": [{"馬番": horse, "馬名": f"馬{horse}", "単勝オッズ": 5.0, "買い目に入れたか": horse in picks} for horse in range(1, 17)]}
            for number, (rid, picks) in enumerate(zip(LEGS, picks_by_leg, strict=True), start=1)]


def sample_win5_record(decision: str = LARGE, *, value: float = 1.83, favorite: float = 0.0031,
                       made_at: str = "2025-04-20T14:25:00") -> dict:
    """予想のパッケージの predict が書く記録（``Win5Forecast.to_dict()``）と同じ形の架空の辞書（段階の予算: 判断用 50点・線 1.25・
    少なく 30点・多く 100点・多く買う日の線 0.0025）。多く買う日は 48点（4,800円）、少なく買う日と見送りは 12点（1,200円）の買い目。
    ``value`` は判断用の買い目の日の期待値（買う買い目の日の期待値にも同じ値を入れる）、``favorite`` は本命の確率の積。"""
    large = decision == LARGE
    picks, points = (PICKS, 48) if large else (SMALL_PICKS, 12)
    return {"開催日": DAY.isoformat(), "予想した時刻": made_at, "キャリーオーバー": 0, "発売票数の見積もり": 7_000_000.0,
            "並べ方": "1着の確率の順", "判断用の予算": 50, "少なく買う日の予算": 30, "多く買う日の予算": 100, "多く買う日の線": 0.0025,
            "買う日の線": 1.25, "判断用の点数": 48, "判断用の当たる確率": 0.021, "判断用の期待値": value, "本命の確率の積": favorite,
            "判断": decision, "段階": _TIERS[decision], "予算": 100 if large else 30, "買い目": [list(each) for each in picks],
            "点数": points, "代金": points * 100, "当たる確率": 0.021 if large else 0.008, "見積もりの払戻の合計": points * 100 * value,
            "日の期待値": value, "配当の見積もりの式に使った当たり組の数": 100, "対象レース": _legs(picks), "予算の候補": []}


def old_win5_record(decision: str = "買う", *, value: float = 1.83) -> dict:
    """段階の予算より前の形の記録（予算が1つで、判断が「買う」か「見送り」）。点数は 48点。"""
    return {"開催日": DAY.isoformat(), "予想した時刻": "2025-04-20T14:25:00", "キャリーオーバー": 0, "発売票数の見積もり": 7_000_000.0,
            "並べ方": "1着の確率の順", "予算": 48, "買う日の線": 1.50, "判断": decision, "買い目": [list(picks) for picks in PICKS],
            "点数": 48, "代金": 4800, "当たる確率": 0.021, "見積もりの払戻の合計": 4800 * value, "日の期待値": value,
            "配当の見積もりの式に使った当たり組の数": 100, "対象レース": _legs(PICKS), "予算の候補": []}


def write_win5_record(root: Path, record: dict) -> Path:
    """予想の記録を ``<root>/記録/<開催日>.json`` に書く（predict の代わり）。"""
    path = root / "記録" / f"{record['開催日']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(record, ensure_ascii=False).encode("utf-8"))
    return path


def _wallet(tmp_path: Path, policy: int = 30_000) -> tuple[ReviewStore, Wallet]:
    store = ReviewStore(tmp_path / "review.duckdb")
    path = tmp_path / "財布.json"
    path.write_text(json.dumps({"勝負用": 100_000, "ポリシー用": policy, "単勝・馬単用": 100_000, "組の期待値用": 500_000,
                                "穴馬の複勝用": 100_000}), encoding="utf-8")
    return store, Wallet(store, path)


def test_フォーメーションの文字と馬番の並びを行き来する() -> None:
    text = combo_text(PICKS)
    assert text == "3,5,10/6,8/2,5/4/4,10,11,15"
    assert combo_legs(text) == ((3, 5, 10), (6, 8), (2, 5), (4,), (4, 10, 11, 15))


def test_記録から買い目と判断の文を読む() -> None:
    record = Win5Record.from_dict(sample_win5_record())
    assert record.buys and record.tiered and record.tier == "多く" and record.budget == 100 and record.points == 48 and record.stake == 4800
    assert record.formation == "3,5,10/6,8/2,5/4/4,10,11,15"
    assert record.value_text() == "判断用の買い目（50点）の期待値 1.83 ≥ 線 1.25"
    assert record.tier_text() == "本命の確率の積 0.31% ≥ 0.25% なので多く買う（予算 100点 10,000円）"
    assert record.reason_text() == "判断用の買い目（50点）の期待値 1.83 ≥ 線 1.25。本命の確率の積 0.31% ≥ 0.25% なので多く買う（予算 100点 10,000円）"
    assert record.tiers_text() == ("多く買う日 100点（10,000円）・少なく買う日 30点（3,000円）。本命の確率の積 0.25% 以上なら多く買う。"
                                   "買うかどうかは判断用の買い目（50点）の期待値が線 1.25 以上か")
    assert record.carry_text() == "なし"
    assert [leg.label for leg in record.legs] == ["東京10R", "京都10R", "福島11R", "東京11R", "京都11R"]
    assert record.legs[0].pick_text() == "10 馬10・5 馬5・3 馬3"
    small = Win5Record.from_dict(sample_win5_record(SMALL, value=1.40, favorite=0.0012))
    assert small.buys and small.tier == "少なく" and small.budget == 30 and small.points == 12 and small.stake == 1200
    assert small.reason_text() == "判断用の買い目（50点）の期待値 1.40 ≥ 線 1.25。本命の確率の積 0.12% < 0.25% なので少なく買う（予算 30点 3,000円）"
    skipped = Win5Record.from_dict(sample_win5_record(SKIP, value=1.2))
    assert not skipped.buys and skipped.budget == 30 and skipped.points == 12
    assert skipped.value_text() == "判断用の買い目（50点）の期待値 1.20 < 線 1.25" and skipped.tier_text() == ""
    assert skipped.reason_text() == skipped.value_text()


def test_段階の予算より前の形の記録も読める() -> None:
    record = Win5Record.from_dict(old_win5_record())
    assert record.buys and not record.tiered and record.tier == "" and record.budget == 48 and record.stake == 4800
    assert record.judge_budget == 48 and record.judge_value == 1.83 and record.favorite_product is None and record.favorite_line is None
    assert record.value_text() == "判断用の買い目（48点）の期待値 1.83 ≥ 線 1.50"
    assert record.tier_text() == "" and record.reason_text() == record.value_text() and record.tiers_text() == ""
    assert not Win5Record.from_dict(old_win5_record("見送り", value=1.2)).buys
    assert Win5Decision.of(record, None).label == "買う"


def test_線以上ならポリシー用の財布から買い_見送りの日は買わない(tmp_path: Path) -> None:
    _, wallet = _wallet(tmp_path)
    bought = Win5Planner(wallet).plan(Win5Record.from_dict(sample_win5_record()), DAY)
    assert (bought.buys, bought.stake_yen, bought.race_id, bought.decision) == (True, 4800, LEGS[0], LARGE)
    assert bought.reason == ("判断用の買い目（50点）の期待値 1.83 ≥ 線 1.25。本命の確率の積 0.31% ≥ 0.25% なので多く買う（予算 100点 10,000円）。"
                             "ポリシー用の財布から買う")
    small = Win5Planner(wallet).plan(Win5Record.from_dict(sample_win5_record(SMALL, value=1.40, favorite=0.0012)), DAY)
    assert (small.buys, small.stake_yen, small.decision) == (True, 1200, SMALL)
    assert "なので少なく買う（予算 30点 3,000円）。ポリシー用の財布から買う" in small.reason
    skipped = Win5Planner(wallet).plan(Win5Record.from_dict(sample_win5_record(SKIP, value=1.2)), DAY)
    assert (skipped.buys, skipped.stake_yen) == (False, 0)
    assert skipped.reason == "判断用の買い目（50点）の期待値 1.20 < 線 1.25 なので見送り"


def test_ポリシー用の財布の残高が代金に足りなければ買わない(tmp_path: Path) -> None:
    _, wallet = _wallet(tmp_path, policy=3_000)
    plan = Win5Planner(wallet).plan(Win5Record.from_dict(sample_win5_record()), DAY)
    assert not plan.buys
    assert plan.reason.endswith("なので多く買う（予算 100点 10,000円）が、ポリシー用の財布の残高 3,000円 が代金 4,800円 に足りないので買わない")
    assert Win5Decision.of(Win5Record.from_dict(sample_win5_record()), plan).label == "見送り"


def test_買う計画は表1に1日1行で書き_ポリシー用の財布から出る(tmp_path: Path) -> None:
    store, wallet = _wallet(tmp_path)
    plan = Win5Planner(wallet).plan(Win5Record.from_dict(sample_win5_record()), DAY)
    assert Win5BetRecorder(store).record(plan, "2025-04-20T14:25:00") == 1
    bets = store.read(names.BETS_TABLE)
    assert bets[[names.RACE_ID, names.TICKET_TYPE, names.COMBO, names.PARTICIPATION, names.STAKE_YEN]].values.tolist() == [
        [LEGS[0], names.WIN5_TICKET, "3,5,10/6,8/2,5/4/4,10,11,15", names.POLICY_WIN5, 4800]]
    assert wallet.balance(POLICY_WALLET) == 30_000 - 4800
    # 同じ日に予想し直して見送りになったら、前の行は消える
    skipped = Win5Planner(wallet).plan(Win5Record.from_dict(sample_win5_record(SKIP, value=1.2)), DAY)
    assert Win5BetRecorder(store).record(skipped, "2025-04-20T14:30:00") == 0
    assert store.read(names.BETS_TABLE).empty


def test_レースの買い目を書き直してもWIN5の行は消さない(tmp_path: Path) -> None:
    store, wallet = _wallet(tmp_path)
    Win5BetRecorder(store).record(Win5Planner(wallet).plan(Win5Record.from_dict(sample_win5_record()), DAY), "t")
    race = RacePlan(LEGS[0], "東京10R", "当日", "買わない", "", 0.0, 1.0, False,
                    tickets=(TicketPick("単勝", "03", "3", 1.1, 4.0, 300),))
    BetRecorder(store).record([race], "t")
    assert sorted(store.read(names.BETS_TABLE)[names.TICKET_TYPE]) == ["WIN5", "単勝"]


def test_まとめにWIN5の節を出す(tmp_path: Path) -> None:
    forecasts = ForecastStore(tmp_path / "今週の予想")
    forecasts.save(sample_forecast("2025042005010201"))
    summary = DaySummary(forecasts)
    assert "WIN5" not in summary.markdown(DAY)
    write_win5_record(tmp_path / WIN5_YOSOU_NAME, sample_win5_record())
    _, wallet = _wallet(tmp_path, policy=3_000)
    plan = Win5Planner(wallet).plan(Win5Record.from_dict(sample_win5_record()), DAY)
    PlanStore(forecasts).save(DAY, [], WALLET, plan)
    text = summary.markdown(DAY, brief=True)
    assert "- WIN5: 見送り・48点 4,800円（下の「WIN5」の節）" in text
    assert "## WIN5" in text and POLICY_NOTE in text
    assert "ポリシー用の財布の残高 3,000円 が代金 4,800円 に足りない" in text
    assert "- 段階の予算: 多く買う日 100点（10,000円）・少なく買う日 30点（3,000円）。本命の確率の積 0.25% 以上なら多く買う。" in text
    assert "| 1 | 東京10R | 当日 | 3 | 10 馬10・5 馬5・3 馬3 |" in text


def test_計画が無ければ予想の判断で節を書く(tmp_path: Path) -> None:
    lines = Win5Section().lines(Win5Record.from_dict(sample_win5_record()), None)
    assert lines[2] == ("- 判断: **買う（多く）**（判断用の買い目（50点）の期待値 1.83 ≥ 線 1.25。本命の確率の積 0.31% ≥ 0.25% なので多く買う"
                        "（予算 100点 10,000円））。予想した時刻 2025-04-20 14:25")
    assert lines[3] == "- 買い目: 48点 4,800円（ポリシー用の財布から）"
    assert lines[5].startswith("- 段階の予算: 多く買う日 100点（10,000円）・少なく買う日 30点（3,000円）")
    small = Win5Section().lines(Win5Record.from_dict(sample_win5_record(SMALL, value=1.40, favorite=0.0012)), None)
    assert small[2].startswith("- 判断: **買う（少なく）**（") and small[3] == "- 買い目: 12点 1,200円（ポリシー用の財布から）"
    assert Win5Section().head_line(Win5Record.from_dict(sample_win5_record()), None) == "- WIN5: 買う（多く）・48点 4,800円（下の「WIN5」の節）"
    old = Win5Section().lines(Win5Record.from_dict(old_win5_record()), None)
    assert old[2] == "- 判断: **買う**（判断用の買い目（48点）の期待値 1.83 ≥ 線 1.50）。予想した時刻 2025-04-20 14:25"
    assert not any(line.startswith("- 段階の予算") for line in old)


def test_記録が無い日は無いと返す(tmp_path: Path) -> None:
    records = Win5RecordStore(tmp_path)
    assert records.load(DAY) is None and records.made_at(DAY) is None
    write_win5_record(tmp_path, sample_win5_record())
    assert records.made_at(DAY) == "2025-04-20T14:25:00"


def test_表1の計画の行は精算の前の形(tmp_path: Path) -> None:
    store, wallet = _wallet(tmp_path)
    Win5BetRecorder(store).record(Win5Planner(wallet).plan(Win5Record.from_dict(sample_win5_record()), DAY), "t")
    row = store.read(names.BETS_TABLE).iloc[0]
    assert not row[names.SETTLED] and pd.isna(row[names.PAYOUT_YEN])
    assert row[names.BOUGHT_PROBABILITY] == 0.021 and row[names.BOUGHT_VALUE] == 1.83
