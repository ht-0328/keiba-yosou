# 03 LightGBM と CatBoost（と pandas）の使い方

**この文書の目的:** 設計を読む前に、LightGBM と CatBoost（と、表を扱う pandas）で何ができるかを知っておく。

**この文書で示すこと: モデルの道具は手本の予想とまったく同じである。そのため、道具の説明は書かず、[手本の 03](../近走と適性から3着以内を予想/03-library-basics.md) を参照する。この予想で増える道具は、設定ファイルを読む PyYAML だけである。**

## 手本の 03 のどこに何が書いてあるか

| 知りたいこと | 手本の節 |
|---|---|
| 入れるパッケージ（`lightgbm`・`catboost`・`scikit-learn`・`pandas`） | [1. 準備](../近走と適性から3着以内を予想/03-library-basics.md#1-準備) |
| 表（`DataFrame`）の作り方、列の型、欠損値 | [2. pandas の使い方](../近走と適性から3着以内を予想/03-library-basics.md#2-pandas-の使い方) |
| 2つのモデルに共通の流れ（モデルを作る → `fit()` → `predict_proba()`） | [3. 2つに共通する使い方](../近走と適性から3着以内を予想/03-library-basics.md#3-2つに共通する使い方) |
| LightGBM のコード例と機能 | [4. LightGBM の使い方](../近走と適性から3着以内を予想/03-library-basics.md#4-lightgbm-の使い方) |
| CatBoost のコード例と機能 | [5. CatBoost の使い方](../近走と適性から3着以内を予想/03-library-basics.md#5-catboost-の使い方) |
| 2つの予測確率の平均のしかた | [6. 2つの予測確率を合わせる](../近走と適性から3着以内を予想/03-library-basics.md#6-2つの予測確率を合わせる) |

## この予想で違う点

### PyYAML（設定ファイルを読む）

設定ファイルを YAML で書くので、PyYAML（`pyyaml`）を足した（`pyproject.toml`）。使うのは、安全な読み込み（`yaml.SafeLoader`）だけである。安全な読み込みは、YAML の中に書かれた Python のオブジェクトを作らない。

```python
import yaml

text = "name: sample\ntarget: 馬券内\npopularity:\n  min: 6\n  max: 10\n"
values = yaml.load(text, Loader=yaml.SafeLoader)
print(values)  # {'name': 'sample', 'target': '馬券内', 'popularity': {'min': 6, 'max': 10}}
```

（YAML の文字列を、Python の辞書にするコード）

PyYAML の安全な読み込みは、同じキーが2回あっても黙って後ろの値を使う。書き間違いに気づけるよう、この予想では、同じキーをエラーにする読み込み（`UniqueKeyLoader`）を足した（[14-hyperparameter-settings.md](14-hyperparameter-settings.md#決まり)）。

### オッズを出発点にする渡し方

オッズの基準を使うときは、LightGBM の `init_score`、CatBoost の `baseline` に、基準のロジット（確率を log(p ÷ (1 − p)) にした値）を渡す。既存の予想モデル（`form_aptitude_top3` など）と同じ共通の部品を使う（[12-lightgbm.md](12-lightgbm.md#1-学習データの渡し方)・[13-catboost.md](13-catboost.md#1-学習データの渡し方)）。

## この予想で使う機能と、書いてある文書

| この予想でやること | 使う機能 | この予想での使い方 |
|---|---|---|
| 設定ファイルを読む | `yaml.load(…, Loader=SafeLoader)` | [14-hyperparameter-settings.md](14-hyperparameter-settings.md) |
| 選んだ特徴量で学習する | `fit()` | [05-sequence.md](05-sequence.md#図1-学習)、[12-lightgbm.md](12-lightgbm.md)・[13-catboost.md](13-catboost.md) |
| 学習しすぎを防ぐ | 検証データと早期終了 | [12-lightgbm.md](12-lightgbm.md#2-ハイパーパラメータの初期値)・[13-catboost.md](13-catboost.md#2-ハイパーパラメータの初期値) |
| オッズを出発点にする | `init_score`・`baseline` | [12-lightgbm.md](12-lightgbm.md#1-学習データの渡し方)・[13-catboost.md](13-catboost.md#1-学習データの渡し方) |
| 学習したモデルを取っておく | 保存と読み込み | [12-lightgbm.md](12-lightgbm.md#6-保存)・[13-catboost.md](13-catboost.md#6-保存) |
| 1レースの対象の馬の確率を出す | `predict_proba()` の2列目 | [05-sequence.md](05-sequence.md#図2-予測) |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-26 |
| 確かめた版 | LightGBM・CatBoost は手本と同じ。PyYAML の例は pyyaml 6 で動かして確かめた |
