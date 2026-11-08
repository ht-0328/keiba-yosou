"""コマンド（fit-payout・predict）を通しで動かすテスト（今のモデルの代わりを使う）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ..command import CommandLine, FitPayoutCommand, PredictCommand
from ..repository.payout_estimator_repository import FILE_NAME
from .fake_prediction import FakePrediction
from .win5_sample import FORECAST_DAY, Win5Sample


def _run(command_line: CommandLine, argv: list[str]) -> int:
    with pytest.raises(SystemExit) as stopped:
        command_line.run(argv)
    return int(stopped.value.code)


def _command_line(sample: Win5Sample) -> CommandLine:
    return CommandLine((FitPayoutCommand(), PredictCommand(lambda args: FakePrediction(sample.odds))))


def test_fit_payoutは式を保存して表を出し_predictは記録を書いて表を出す(win5_db: Path, win5_sample: Win5Sample, tmp_path: Path) -> None:
    root, fit_out, predict_out = tmp_path / "win5", tmp_path / "fit.md", tmp_path / "predict.md"
    command_line = _command_line(win5_sample)
    code = _run(command_line, ["fit-payout", "--before", FORECAST_DAY.isoformat(), "--db", str(win5_db), "--models", str(root),
                               "--out", str(fit_out)])
    assert code == 0
    assert "配当の見積もりの式" in fit_out.read_text(encoding="utf-8")
    saved = json.loads((root / FILE_NAME).read_text(encoding="utf-8"))
    assert saved["使った期間"]["この日より前"] == FORECAST_DAY.isoformat()
    code = _run(command_line, ["predict", "--date", FORECAST_DAY.isoformat(), "--budget", "20", "--ordering", "上乗せ",
                               "--db", str(win5_db), "--models", str(root), "--out", str(predict_out)])
    assert code == 0
    text = predict_out.read_text(encoding="utf-8")
    assert "日のまとめ" in text and "選んだ買い目" in text and "5レース目" in text and "予算の候補ごと" in text
    record = json.loads((root / "記録" / f"{FORECAST_DAY.isoformat()}.json").read_text(encoding="utf-8"))
    assert record["予算"] == 20 and record["点数"] <= 20


def test_式が無ければfit_payoutを案内して止まる(win5_db: Path, win5_sample: Win5Sample, tmp_path: Path, capsys) -> None:
    code = _run(_command_line(win5_sample), ["predict", "--date", FORECAST_DAY.isoformat(), "--db", str(win5_db),
                                             "--models", str(tmp_path / "empty")])
    assert code == 1
    assert "fit-payout" in capsys.readouterr().err


def test_今のモデルが無ければtrainを案内して止まる(win5_db: Path, win5_sample: Win5Sample, tmp_path: Path, capsys) -> None:
    root = tmp_path / "win5"
    command_line = CommandLine()
    assert _run(command_line, ["fit-payout", "--before", FORECAST_DAY.isoformat(), "--db", str(win5_db), "--models", str(root),
                               "--out", str(tmp_path / "fit.md")]) == 0
    code = _run(command_line, ["predict", "--date", FORECAST_DAY.isoformat(), "--db", str(win5_db), "--models", str(root),
                               "--form-models", str(tmp_path / "no-models")])
    assert code == 1
    assert "train" in capsys.readouterr().err
