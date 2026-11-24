"""高配当の買い目の成績の入口（``stats.py``）を、予想のパッケージの実物（``PredictionStore``・``HighPayoutRule``・既定の帯）で通しで動かすテスト。

予測と馬ごとの表は架空の値を tmp に書く。予想のパッケージを読み込めない間は飛ばす。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from yosou.shared.betting import TicketType

from 高配当の買い目.folders import STATS_FILE


def _prediction(race: str, day: str, ticket: str, combo: str, odds: float, payout: int, probability: float) -> dict:
    return {"race_id": race, "race_date": pd.Timestamp(day), "ticket_type": ticket, "combo": combo, "odds": odds, "payout": payout,
            "hit": int(payout > 0), "probability": probability, "probability_lightgbm": probability, "probability_catboost": probability,
            "market_probability": 1 / odds}


def test_実物の予測の置き場と買い目の決まりで_5つの表を出して成績のファイルに書く(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    try:
        from yosou.high_payout_combos import PredictionStore

        from 高配当の買い目 import stats
    except ImportError:
        pytest.skip("予想のパッケージ（yosou.high_payout_combos）がまだ読み込めない")
    store = PredictionStore(tmp_path / "predictions")
    # ワイドの帯は 10倍以上・300倍未満。期待値 1.05 以上は 0102（12倍 × 0.10）と 0304（20倍 × 0.06）。0103 は 9倍で線より安く、
    # 0105 は 300倍で上限以上、0306 は期待値 0.9
    store.save(TicketType.WIDE, 2022, pd.DataFrame([
        _prediction("A1", "2022-12-03", "ワイド", "0102", 12.0, 1200, 0.10), _prediction("A1", "2022-12-03", "ワイド", "0103", 9.0, 0, 0.50),
        _prediction("A1", "2022-12-03", "ワイド", "0105", 300.0, 0, 0.01)]))
    store.save(TicketType.WIDE, 2023, pd.DataFrame([
        _prediction("B1", "2023-01-07", "ワイド", "0304", 20.0, 0, 0.06), _prediction("B1", "2023-01-07", "ワイド", "0306", 30.0, 0, 0.03)]))
    horses = tmp_path / "horses"
    horses.mkdir()
    pd.DataFrame({"race_id": ["A1", "A2", "B1", "B2", "Z9"], "horse_no": 1,
                  "race_date": pd.to_datetime(["2022-12-03", "2022-12-03", "2023-01-07", "2023-01-07", "2019-01-05"])}).to_parquet(horses / "全部.parquet")
    out_dir = tmp_path / "out"
    args = stats.build_parser().parse_args(["--ticket", "ワイド", "--predictions", str(tmp_path / "predictions"), "--horses", str(horses),
                                            "--out-dir", str(out_dir)])
    stats.main(args)
    text = (out_dir / STATS_FILE).read_text(encoding="utf-8")
    assert capsys.readouterr().out == text
    for title in ("### 1. 券種ごとの成績", "### 2. 年ごとの回収率", "### 3. 期間ごとの成績", "### 4. 運用の目安", "### 5. 線の感度"):
        assert title in text
    # 全レースは、馬ごとの表のうち予測のある年（2022・2023年）の 4レース。買ったのは 2レース・2点で、払戻 1,200円 ÷ 投資 200円
    assert "| ワイド | 2 | 50.0% | 1.0 | 2 | 1 | 50.0% | 12.0 | 600.0% |" in text
    assert "全レース 4・開催日 2" in text and "ワイド 10倍以上 300倍未満" in text and "期待値（予想の確率 × 確定オッズ）が 1.05 以上" in text
    assert "| ワイド | 1200.0%（1） | 0.0%（0） |" in text
    # 馬連は予測が無いので、券種を絞らなければ止まる。高配当の買い目に無い券種は誤り
    with pytest.raises(ValueError, match="高配当の買い目に無い券種"):
        stats.main(stats.build_parser().parse_args(["--ticket", "単勝", "--predictions", str(tmp_path / "predictions")]))


def test_上限の点数の既定は今週の予想と同じで_0を渡すと上限なし(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    try:
        from yosou.high_payout_combos import PredictionStore

        from 高配当の買い目 import stats
    except ImportError:
        pytest.skip("予想のパッケージ（yosou.high_payout_combos）がまだ読み込めない")
    from 今週の予想.ticket_rules import HIGH_PAYOUT_LABELS, HIGH_PAYOUT_MAX_POINTS

    # 1レースに、期待値 1.05 以上のワイドが 2点（確率 0.10 の 0102 が当たり、0.06 の 0304 が外れ）
    PredictionStore(tmp_path / "predictions").save(TicketType.WIDE, 2023, pd.DataFrame([
        _prediction("B1", "2023-01-07", "ワイド", "0102", 12.0, 1200, 0.10), _prediction("B1", "2023-01-07", "ワイド", "0304", 20.0, 0, 0.06)]))
    horses = tmp_path / "horses"
    horses.mkdir()
    pd.DataFrame({"race_id": ["B1"], "horse_no": 1, "race_date": pd.to_datetime(["2023-01-07"])}).to_parquet(horses / "全部.parquet")
    common = ["--ticket", "ワイド", "--predictions", str(tmp_path / "predictions"), "--horses", str(horses), "--out-dir", str(tmp_path / "out")]
    parser = stats.build_parser()
    assert parser.parse_args(common).max_points == HIGH_PAYOUT_MAX_POINTS
    assert stats._ticket_types(None) == tuple(HIGH_PAYOUT_LABELS)   # 券種を絞らなければ、今週の予想が出していない券種も数える
    stats.main(parser.parse_args([*common, "--max-points", "1"]))
    capped = capsys.readouterr().out
    assert "確率の高い順に 1点まで" in capped and "| ワイド | 1 | 100.0% | 1.0 | 1 | 1 | 100.0% | 12.0 | 1200.0% |" in capped
    stats.main(parser.parse_args([*common, "--max-points", "0"]))
    open_ended = capsys.readouterr().out
    assert "上限の点数なし" in open_ended and "| ワイド | 1 | 100.0% | 2.0 | 2 | 1 | 100.0% | 12.0 | 600.0% |" in open_ended
