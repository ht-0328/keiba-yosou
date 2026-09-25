# 14 ハイパーパラメータを外から指定する

**この文書で決めること:** 木の数などのハイパーパラメータと、この予想で利用者が選ぶもの（特徴量・目的・時点・人気範囲・条件・期間）を、プログラムを書き換えずに外から指定する方法。

**結論: 1つのモデルの作り方を、1つの設定ファイル（YAML）に書く。ハイパーパラメータの部分（`lightgbm`・`catboost`）は、手本の設定ファイル（TOML）と同じ項目・同じ決まりで、変えたいものだけを書く。書き間違い（知らないキー・同じキーの2回・型の誤り）は、学習を始める前にエラーにする。**

- 手本の設定ファイルの項目と決まりは [手本の 14 の「設定ファイルの形」](../近走と適性から3着以内を予想/14-hyperparameter-settings.md#設定ファイルの形) と [「決まり」](../近走と適性から3着以内を予想/14-hyperparameter-settings.md#決まり) を参照。
- 用語の意味は [02-glossary.md](02-glossary.md) を参照。

## 設定ファイルの形

```yaml
# 1つのモデルの作り方。name ごとに reports/custom_binary/<name>/ に保存する（上書きしない）。
name: top3_turf_short_pop6_10
features_file: features.txt   # 設定ファイルからの相対パス
target: 馬券内                # 馬券内 / 馬券外 / 勝利
timing: 当日                  # 木曜 / 前日 / 当日

popularity:                   # 省略すれば全人気
  min: 6
  max: 10

conditions:                   # 省略すれば絞らない
  芝ダ: 芝
  距離: {max: 1600}

odds_baseline: true           # 前日・当日だけ

training:                     # 省略すれば既定の期間
  train_from: 2021-08-01
  valid_from: 2025-07-01
  test_from: 2026-01-01

lightgbm:                     # 変えたいものだけ書く
  min_category_count: 500
  params:
    learning_rate: 0.03
catboost:
  params:
    depth: 8
```

（`train --config <このファイル>` で学習する設定ファイルの例。特徴量テキストには、[01-overview.md の「1頭の例」](01-overview.md#1頭の例) の 10個を書いた）

| キー | 意味 | 書いてある文書 |
|---|---|---|
| `name` | 保存先のフォルダ名。英数字・`_`・`-` だけ。Windows の予約名（`CON` など）は使えない | [12-lightgbm.md](12-lightgbm.md#6-保存) |
| `features_file` | 特徴量テキストのパス（設定ファイルからの相対パスか、絶対パス） | [09-features.md](09-features.md#特徴量の選び方) |
| `target` | 目的変数 | [10-target.md](10-target.md) |
| `timing` | 予測する時点 | [07-prediction-timing.md](07-prediction-timing.md) |
| `popularity` | 人気範囲（`min`・`max`。1以上の整数。片方だけでもよい） | [08-training-data.md](08-training-data.md#3-どのサンプルを入れるか) |
| `conditions` | 対象を絞る条件 | [08-training-data.md](08-training-data.md#3-どのサンプルを入れるか) |
| `odds_baseline` | オッズを出発点にするか（`true`・`false`。省略は `false`） | [12-lightgbm.md](12-lightgbm.md#1-学習データの渡し方) |
| `training` | 期間の区切り（`warmup_from`・`train_from`・`valid_from`・`test_from`） | [08-training-data.md](08-training-data.md#4-期間の指定) |
| `lightgbm`・`catboost` | ハイパーパラメータ。手本の設定ファイルと同じ項目 | [12-lightgbm.md](12-lightgbm.md#2-ハイパーパラメータの初期値)・[13-catboost.md](13-catboost.md#2-ハイパーパラメータの初期値) |

## 決まり

| 決まり | 理由 |
|---|---|
| YAML は安全な読み込み（`SafeLoader`）で読む | YAML の中に書かれた Python のオブジェクトを作らない |
| 知らないキー・同じキーの2回・文字列でないキーはエラーにする（行番号付き） | PyYAML は同じキーの2回を黙って後ろの値にするので、書き間違いに気づけない（[03-library-basics.md](03-library-basics.md#pyyaml設定ファイルを読む)） |
| 型が違う値（整数に文字列、数値に `true` など）と、範囲の外の値（負の学習率など）はエラーにする | 学習を何分も回したあとで失敗しないようにする |
| 目的関数（`objective`・`loss_function`）は変えられない | 二値分類に決まっているため（手本と同じ） |
| 使った設定は、モデルと一緒に `model.json` に保存する。予測は元の設定ファイルを読まない | 設定ファイルを書き換えても、学習したモデルの予測は変わらない（[12-lightgbm.md](12-lightgbm.md#6-保存)） |
| 同じ `name` の保存先があれば、学習を始める前に止める | 前のモデルを黙って上書きしない |

## この予想で違う点

| 項目 | 手本 | この予想 |
|---|---|---|
| 書式 | TOML | YAML。ハイパーパラメータ以外（特徴量・目的・条件など）も1つのファイルに書くため（[15-decisions.md](15-decisions.md#1-設定をyamlの1ファイルにまとめるか)） |
| 指定のしかた | `train --config <TOML>` を省略すれば初期値 | `train --config <YAML>` は必ず指定する。ハイパーパラメータを省略すれば初期値 |
| 初期値の置き場所 | `src/yosou/form_aptitude_top3/setting/default_settings.toml` | **手本の同じファイルを読んでいる。** 予想のパッケージどうしで import しない決まりと違うので、直すなら `custom_binary` に初期値のファイルを持つ（[04-classes.md](04-classes.md#4-手本の決まりと違うところ)） |
| 同じ設定で学習するモデルの数 | 3つの時点 | 設定の1つの時点だけ（[07-prediction-timing.md](07-prediction-timing.md#時点ごとにモデルを分ける理由)） |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-26 |
| 確かめたこと | 上の例のファイルを `ModelSettings.load()` で読み、LightGBM と CatBoost のモデルに渡せることを確かめた（2026-09-26） |
