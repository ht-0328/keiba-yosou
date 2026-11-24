"""コマンド（walk・train）と、券種を絞る引数のテスト。乱数で作った架空のシーズンだけを使う。"""

from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import pytest

from yosou.shared.betting import TicketType

from ..command import CommandLine
from ..command.ticket_argument import ticket_types_of
from ..repository import PredictionStore, TicketModelRepository
from .conftest import FAST_SETTINGS, FIRST_TEST_YEAR

WIDE, TRIO, TRIFECTA = TicketType.WIDE, TicketType.TRIO, TicketType.TRIFECTA


@pytest.fixture()
def config(tmp_path: Path) -> Path:
    """テストで速く学習が終わる設定のファイル。"""
    path = tmp_path / "fast.toml"
    path.write_text(FAST_SETTINGS, encoding="utf-8", newline="\n")
    return path


def _run(arguments: list[str]) -> int:
    """コマンドを流して、終わりの番号（成功なら 0）を返す。"""
    with pytest.raises(SystemExit) as exit_info:
        CommandLine().run(arguments)
    return exit_info.value.code


def _tables_folder(season: SimpleNamespace) -> str:
    return str(season.tables.path(WIDE, FIRST_TEST_YEAR).parent)


def test_walkコマンドは_年ごとの予測を保存して_学習と成績の表を出す(season: SimpleNamespace, config: Path, tmp_path: Path) -> None:
    out = tmp_path / "walk.md"
    arguments = ["walk", "--first-year", str(FIRST_TEST_YEAR), "--ticket", "ワイド", "--config", str(config),
                 "--tables", _tables_folder(season), "--predictions", str(tmp_path / "predictions"), "--out", str(out)]
    assert _run(arguments) == 0
    assert PredictionStore(tmp_path / "predictions").years(WIDE) == [2023, 2024]
    text = out.read_text(encoding="utf-8")
    assert "ワイド: 年ごとの学習" in text and "ワイド: 買い目の年ごとの成績" in text and "予測した" in text
    assert _run(arguments) == 0                                    # 2回目は、済んでいる年を飛ばす
    assert "済んでいるので飛ばした" in out.read_text(encoding="utf-8")


def test_trainコマンドは_本番のモデルを保存して_当たり具合の表を出す(season: SimpleNamespace, config: Path, tmp_path: Path) -> None:
    out = tmp_path / "train.md"
    arguments = ["train", "--ticket", "wide", "--config", str(config), "--tables", _tables_folder(season),
                 "--models", str(tmp_path / "models"), "--out", str(out)]
    assert _run(arguments) == 0
    models = TicketModelRepository(tmp_path / "models")
    assert models.has(WIDE) and not models.has(TRIFECTA)          # --ticket で絞った券種だけ
    text = out.read_text(encoding="utf-8")
    assert "学習した本番のモデル" in text and "検証の期間での当たり具合" in text and "ワイド" in text


def test_表の無いフォルダで学ぼうとすると_誤りを1行で見せて終わる(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    arguments = ["walk", "--ticket", "3連複", "--tables", str(tmp_path), "--predictions", str(tmp_path / "predictions")]
    assert _run(arguments) == 1
    assert "表が足りません" in capsys.readouterr().err


def test_券種の引数は_名前でも英名でも書け_省くと5つ全部() -> None:
    assert len(ticket_types_of(argparse.Namespace(ticket=None))) == 5
    assert ticket_types_of(argparse.Namespace(ticket=["3連単", "trio", " ワイド "])) == [TRIFECTA, TRIO, WIDE]


def test_扱わない券種の名前は誤り() -> None:
    with pytest.raises(ValueError, match="扱わない券種"):
        ticket_types_of(argparse.Namespace(ticket=["単勝"]))
