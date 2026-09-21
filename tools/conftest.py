"""pytest の共通 fixture。実DB は使わず、合成DB（tools/合成DB/synth.py）を tmp_path に作る。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from 合成DB import synth  # noqa: E402


@pytest.fixture
def synth_db(tmp_path: Path) -> Path:
    """東京 芝1600 良 の4レースなどが入った合成DB のパス。"""
    return synth.sample_db(tmp_path / "synth.duckdb")


@pytest.fixture
def card_db(tmp_path: Path) -> Path:
    """``synth_db`` の確定成績に、確定前の2レース（2025-04-19 東京 1R 出走馬名表・2R 出馬表）を足した合成DB のパス。"""
    return synth.card_db(tmp_path / "card.duckdb")


@pytest.fixture
def one_race_db(tmp_path: Path) -> Path:
    """1レース（1番人気 4着・4番人気 1着・中止1頭・取消1頭）だけの合成DB のパス。"""
    return synth.build_db(tmp_path / "one.duckdb", synth.simple_race())


@pytest.fixture
def trend_db(tmp_path: Path) -> Path:
    """傾向がはっきり出る合成DB のパス。東京 芝1600 良 でいつも馬番4 が勝つ6レースと、確定前の2レース（2025-04-19 東京 1R・2R）。"""
    return synth.trend_db(tmp_path / "trend.duckdb")
