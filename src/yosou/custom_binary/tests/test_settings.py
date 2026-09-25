from pathlib import Path

import pytest

from ..feature.registrations import default_registry
from ..settings import ModelSettings, PopularityRange


BASE = "name: sample\nfeatures_file: features.txt\ntarget: 馬券内\ntiming: 当日\n"


def config(tmp_path: Path, text: str = BASE, features: str = "距離\n馬齢\n") -> Path:
    path = tmp_path / "model.yml"
    path.write_text(text, encoding="utf-8-sig")
    (tmp_path / "features.txt").write_text(features, encoding="utf-8-sig")
    return path


def test_relative_path_bom_comments_and_roundtrip(tmp_path, monkeypatch):
    path = config(tmp_path, features=" # 説明\n\n 距離 \n馬齢\n")
    monkeypatch.chdir(tmp_path.parent)
    registry = default_registry()
    settings = ModelSettings.load(path, registry)
    assert settings.selected == ("距離", "馬齢")
    assert ModelSettings.from_saved(settings.as_dict(), registry).as_dict() == settings.as_dict()


@pytest.mark.parametrize("extra,match", [
    ("typo: 1\n", "未知"), ("name: second\n", "重複"),
    ("popularity: {min: 3, min: 4}\n", "重複"),
    ("popularity: {min: true}\n", "整数"), ("popularity: {min: 0}\n", "整数"),
    ("popularity: {min: 2.5}\n", "整数"), ("popularity: {min: null}\n", "正の整数"),
    ("popularity: {min: 10, max: 6}\n", "minはmax以下"),
    ("training: {train_from: wrong}\n", "YYYY-MM-DD"),
    ("training: {train_from: 2026-01-01}\n", "前の日"),
    ("lightgbm: {params: {n_estimators: '20'}}\n", "型"),
    ("catboost: {params: {iterations: true}}\n", "型"),
    ("catboost: {params: {iterations: 0}}\n", "小さすぎ"),
    ("lightgbm: {params: {objective: regression}}\n", "目的関数"),
    ("lightgbm: {params: {learning_rate: .nan}}\n", "有限"),
    ("lightgbm: {params: {subsample: 2.0}}\n", "1以下"),
    ("catboost: []\n", "表"), ("training: null\n", "組"),
    ("1: value\n", "キーは文字列"),
])
def test_invalid_yaml(tmp_path, extra, match):
    with pytest.raises(ValueError, match=match):
        ModelSettings.load(config(tmp_path, BASE + extra), default_registry())


@pytest.mark.parametrize("key,value", [("name", "../escape"), ("name", "CON"), ("target", "複勝"), ("timing", "翌日")])
def test_invalid_identity(tmp_path, key, value):
    text = "\n".join(f"{key}: {value}" if line.startswith(f"{key}:") else line for line in BASE.splitlines())
    with pytest.raises(ValueError):
        ModelSettings.load(config(tmp_path, text), default_registry())


@pytest.mark.parametrize("features,match", [("距離\n距離\n", ":2:.*重複"), ("距離\nない項目\n", ":2:.*未登録"), ("# none\n", ":1:.*ありません")])
def test_feature_file_errors(tmp_path, features, match):
    with pytest.raises(ValueError, match=match):
        ModelSettings.load(config(tmp_path, features=features), default_registry())


def test_thursday_rejects_weight_instead_of_dropping_column(tmp_path):
    with pytest.raises(ValueError, match=":1:.*木曜には使えない"):
        ModelSettings.load(config(tmp_path, BASE.replace("当日", "木曜"), "馬体重\n"), default_registry())


def test_unsafe_yaml_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="YAML"):
        ModelSettings.load(config(tmp_path, "!!python/object/apply:os.system ['echo unsafe']"), default_registry())


def test_omitted_popularity_bounds():
    assert not PopularityRange().bounded
    assert PopularityRange(6).as_dict() == {"min": 6}
    assert PopularityRange(maximum=3).as_dict() == {"max": 3}
