"""攻略ポイントのページの組み立て（架空の出走の行から）。"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from 重賞攻略 import page  # noqa: E402


def _fictional_runners() -> pd.DataFrame:
    """架空の重賞「テスト記念」の3開催（8頭立て）。1番人気がいつも3着以内、逃げがいつも勝つ。"""
    rows = []
    rng = np.random.default_rng(7)
    for year, day in ((2024, "2024-06-02"), (2025, "2025-06-01"), (2026, "2026-06-07")):
        race_id = f"{year}060205010111"
        for number in range(1, 9):
            finish = number  # 馬番 = 人気 = 着順の単純な世界
            rows.append({
                "race_id": race_id, "race_date": pd.Timestamp(day), "year": year,
                "venue": "東京", "course": "芝・左", "distance_m": 2000, "condition": "良",
                "grade_code": "C", "field_size": 8, "frame_no": number, "horse_no": number,
                "horse_name": f"テストウマ{number}", "sex": "牡" if number % 2 else "牝",
                "age": 4 + number % 3, "affiliation": "栗東" if number <= 4 else "美浦",
                "popularity": number, "win_odds": number * 2.0, "finish": finish,
                "style": "逃げ" if number == 1 else ("先行" if number <= 3 else "差し"),
                "style_before": "逃げ" if number == 1 else "差し",
                "interval_days": 28 + int(rng.integers(0, 60)),
                "same_race_places_before": 1 if year > 2024 and number <= 3 else 0,
                "win_payout": 200 if finish == 1 else 0, "place_payout": 110 if finish <= 3 else 0,
                "stakes_no": "9001", "stakes_name": "テスト記念", "grade": "C",
                "prev_race_name": "前哨戦" if number <= 4 else None, "prev_class_name": "オープン",
                "distance_change": ("延長", "同じ", "短縮")[number % 3],
            })
    return pd.DataFrame(rows)


def _longer_wins_runners() -> pd.DataFrame:
    """架空の重賞の20開催（16頭立て）。距離延長の8頭がいつも短縮の8頭に先着する。どの人気も延長と短縮が半々になる。"""
    base = _fictional_runners().iloc[0]
    rows = []
    for edition in range(20):
        race_id = f"{2000 + edition}060205010111"
        longer = [number for number in range(1, 17) if number % 2 == edition % 2]
        shorter = [number for number in range(1, 17) if number not in longer]
        finishes = {number: place for place, number in enumerate(longer + shorter, start=1)}
        for number in range(1, 17):
            rows.append({**base.to_dict(), "race_id": race_id, "race_date": pd.Timestamp(f"{2000 + edition}-06-01"),
                         "year": 2000 + edition, "field_size": 16, "horse_no": number, "frame_no": (number + 1) // 2,
                         "popularity": number, "finish": finishes[number],
                         "distance_change": "延長" if number in longer else "短縮"})
    return pd.DataFrame(rows)


def test_build_page_renders_all_sections():
    runners = _fictional_runners()
    built = page.build_page(runners, runners, course_rates=None)
    for heading in ("# テスト記念", "## 攻略ポイント", "## 過去の開催", "## 人気の信頼度",
                    "## 脚質", "## 枠", "## ローテ", "## 距離の変更", "## 属性", "## リピーター", "## 荒れ度"):
        assert heading in built.markdown
    assert built.editions == 3
    assert built.file_name == "G3-テスト記念.md"


def test_page_flags_no_findings_for_a_tiny_sample():
    """3開催・24頭では、検定を満たすずれはまず出ない（自動要約は「見つからなかった」）。"""
    runners = _fictional_runners()
    built = page.build_page(runners, runners, course_rates=None)
    weak = [finding for finding in built.findings if finding.p_value >= page.SUMMARY_P]
    assert len(weak) == 0


def test_the_distance_section_says_longer_is_better_when_longer_horses_always_beat_shorter_ones():
    """同じ人気の中で延長の馬がいつも先着すれば、勝つ・穴馬の好走のどちらも「延長が有利（1%）」で、要約にも載る。"""
    runners = _longer_wins_runners()
    built = page.build_page(runners, runners, course_rates=None)
    assert built.distance_win == "延長が有利（1%）" and built.distance_longshot == "延長が有利（1%）"
    assert "| 勝つ（勝率） |" in built.markdown and "距離延長の穴馬（6番人気以下）" in built.markdown
    assert any(f.section == "距離" and f.text.startswith("勝つ（勝率）は延長が有利") for f in built.findings)
