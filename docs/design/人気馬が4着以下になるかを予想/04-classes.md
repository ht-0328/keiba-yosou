# 04 クラスとパッケージの設計

**この文書で決めること:** 手本の予想とこの予想で、同じ仕事をするクラスをどこに置くか。この予想だけに要るクラスは何か。それらをどのフォルダ（パッケージ）・ファイルに置くか。

**結論: データを読む・特徴量を作る・学習する・予測するのクラスは、手本の予想と共通である。共通のクラスは `src/yosou/shared/` に移し、両方の予想から使う。この予想だけに作るのは、人気馬の行を選ぶ・目的変数を付ける・人気を決める・人気の特徴量を作る、の4つの仕事のクラスと、予測の流れを進める `PredictionWorkflow`、コマンドである。学習の流れ（`TrainingWorkflow`）は中身が同じなので、共通にする。**

- 1ファイル1クラス、1クラス1つの仕事、1 SQL につき1つのリポジトリ、という分け方の決まりは手本と同じで、[手本の 04 の「分け方の決まり」](../近走と適性から3着以内を予想/04-classes.md#分け方の決まり) を参照。
- 共通のクラスの一覧（どのクラスが何をするか）は [手本の 04 の「クラスの一覧」](../近走と適性から3着以内を予想/04-classes.md#クラスの一覧) を参照。この文書には、この予想だけのクラスを書く。
- 用語の意味（public メソッド・オーケストレーション・インターフェース・リポジトリ・エンコーダー）は [手本の 02 の「機械学習の用語」](../近走と適性から3着以内を予想/02-glossary.md#機械学習の用語) を参照。
- クラスどうしが、どの順にどのメソッドを呼ぶかは [05-sequence.md](05-sequence.md) を参照。

**2026-09-23 の追記。** 穴馬の予想（[穴馬の 04 の「1. 共通の部品と、この予想だけの部品の分け方」](../穴馬が3着以内に入るかを予想/04-classes.md#1-共通の部品とこの予想だけの部品の分け方)）を作るときに、この文書で「この予想だけのクラス」としていたもののうち、人気を決める部品（`PopularityApplier`・`PopularityInput`）、締め切り前のオッズ（`AnnouncedOddsRepository`）、まとまり J（`PopularityHistoryFeatures`・`PopularityRunSummary`・一覧 `POPULARITY_FEATURES`）を `src/yosou/shared/` に移し、2つの予想から使う形にした。多頭数の線引き（14頭）も共通の定数になった。`PopularityInput` は、木曜用に「馬名:人気」も受け取る。下の表の「dataset/」「feature/」「repository/」のうち、それらの行は今は共通のクラスである（仕事は変わらない）。

## 1. 共通の部品と、この予想だけの部品の分け方

手本の予想（`src/yosou/form_aptitude_top3/`）には、この予想でもそのまま要るクラスが多い。同じクラスを2つのパッケージに複製すると、片方だけ直したときに食い違う。そこで、**共通のクラスを `src/yosou/shared/` に移し、両方の予想から使う。** これが、この予想を作るときの最初の作業になる（[15-decisions.md](15-decisions.md#8-共通部分の置き方)）。

| まとまり | 共通にするか | 中身 |
|---|---|---|
| `repository/`（データの読み書き） | 共通 | 出走の行・出走別着度数・過去走・調教・速報・締め切り前のオッズを読むクラス。読む SQL は予想で変わらない |
| `dataset/`（学習データ・予測用データを作る） | 大半を共通 | `DatasetBuilder`・記録を集めるクラス・`TrainingPeriod`・`PeriodSplitter`・速報を反映するクラス |
| `feature/`（特徴量を作る） | 大半を共通 | `FeatureBuilder`・まとまり A〜I の9クラス・過去の記録から数える部品・`PredictionTiming` |
| `ml_model/`（機械学習のモデル） | 共通 | `LightGbmModel`・`CatBoostModel`・エンコーダー・`EnsembleModel` |
| `setting/`（設定ファイルを読む） | 共通 | 設定ファイルを読む5クラス。初期値のファイルだけは予想ごとに持つ（[14-hyperparameter-settings.md](14-hyperparameter-settings.md)） |
| `evaluation/`（当たり具合を測る） | 共通 | 評価指標を計算するクラス。指標そのものは次の設計書で決める |
| `workflow/`（流れを進める） | 学習は共通、予測は予想ごと | `TrainingWorkflow` は、学習する時点の並びとハイパーパラメータの初期値のファイルを受け取るだけなので共通。`PredictionWorkflow` は人気の扱いが違うので予想ごと |
| `command/` | 予想ごと | 使うクラスの組み立てと、時点の数と、コマンドの引数が違う |

**共通のクラスが、予想ごとの違いを知らずに済むようにする。** そのために、`shared` にはインターフェース（`Protocol`）を置き、予想ごとのクラスがそれを守る。

| インターフェース（`shared` に置く） | 決まり（public メソッド） | この予想で守るクラス |
|---|---|---|
| `SampleSelector` | `training_samples(出走の行, 学習データの始まり)`、`prediction_runners(出走の行, レースID)`、`keep_samples(特徴量の付いた行)` | `FavoriteSelector` |
| `TargetLabeler` | `build(サンプルの行)`、`label_name` | `OutOfTop3TargetBuilder` |
| `FeatureGroup` | `build(記録)` | `PopularityHistoryFeatures` |
| `ProbabilityModel` | `fit`・`predict_proba`・`save`・`load` | 共通の `LightGbmModel`・`CatBoostModel` をそのまま使う |

| 決まり | 理由 |
|---|---|
| `shared` のクラスは、予想のパッケージを参照しない | 片方の予想の都合が、もう片方に入り込まない |
| `DatasetBuilder` は、行を選ぶクラス（`SampleSelector`）と目的変数を付けるクラス（`TargetLabeler`）を、作られるときに受け取る | 予想ごとの違いが、渡すクラスの中に収まる。`DatasetBuilder` の中に「どの予想か」の if 文が増えない |
| `FeatureBuilder` は、まとまりのクラス（`FeatureGroup`）の一覧を受け取る | まとまり J を足すのは、一覧に `PopularityHistoryFeatures` を足すだけで済む |
| `keep_samples()` は、特徴量を作ったあとに呼ぶ | レース内順位は、レースの全出走馬から計算する。人気馬だけに絞るのは、そのあとになる（[08-training-data.md](08-training-data.md#3-どのサンプルを入れるか)） |
| 手本の予想も、移したあとの `shared` を使う形に直す | 同じ仕事のクラスが2つに増えると、直すときに片方を忘れる |

手本の `RunnerSelector` と `TargetBuilder` は、`form_aptitude_top3` に残す。この2つは「全頭を入れる」「3着以内なら 1」という、手本の予想の決めごとだからである。`RunnerSelector` には、そのまま返す `keep_samples()` を足して、`SampleSelector` の決まりを守らせる。

ただし、**「障害レースと、出走しなかった馬を除く」という判断は、両方の予想で同じである。** そこで、この判断だけを `shared/dataset/flat_runner_filter.py` の `FlatRunnerFilter` に出し、`RunnerSelector` と `FavoriteSelector` の両方から使う（同じ判定を2か所に書かない）。

## 2. パッケージ構成

予想方法のコードは `src/yosou/` の下に置く（keiba-yosou の決まり）。この予想のパッケージ名は、予想のやり方が分かる `favorites_out_of_top3`（favorites = 上位人気、out of top3 = 3着以内に入らない）とする。

```text
src/yosou/shared/                   両方の予想から使う部品
├── repository/                     データの読み書き。1 SQL につき 1 リポジトリ
├── dataset/                        学習データ・予測用データを作る
├── feature/                        特徴量を作る（まとまり A〜I と、過去の記録から数える部品）
├── ml_model/                       LightGBM・CatBoost・エンコーダー・2つの平均
├── setting/                        設定ファイルを読む
├── evaluation/                     当たり具合を測る
├── workflow/                       学習の流れ（TrainingWorkflow）
├── command/                        コマンドの部品のうち、予想に依らないもの（共通の引数・結果の表）
└── tests/                          共通の部品のテストと、テスト用の合成のシーズン

src/yosou/favorites_out_of_top3/    人気馬が4着以下になるかを予想する
├── __main__.py                     コマンドの入口（command/ を呼ぶだけ）
├── command/                        コマンド（train・predict）の引数
├── workflow/                       予測の流れ（ほかを順に呼ぶだけ）と、予測を出す時点
├── dataset/                        人気馬の行を選ぶ・目的変数を付ける（人気を決める部品は 2026-09-23 に shared へ）
├── feature/                        この予想の特徴量の一覧（まとまり J を作る部品は 2026-09-23 に shared へ）
├── setting/                        ハイパーパラメータの初期値のファイル
└── tests/                          テスト。合成DB だけを使う（keiba-yosou の決まり）
```

各フォルダには `__init__.py` を置き、その先頭に「クラス → 仕事」の表を書く。ファイルの名前は、クラスの名前を小文字と `_` にしたもの（`FavoriteSelector` → `favorite_selector.py`）。学習したモデルは、Git の対象外の `reports/favorites_out_of_top3/models/` に、時点ごとに保存する。

| 決まり | 理由 |
|---|---|
| 参照の向きは一方向にする: `favorites_out_of_top3` → `shared`。`shared` から予想のパッケージを参照しない | 参照が循環すると、1つを直すと全部に響く |
| 予想のパッケージの中も一方向にする: `command` → `workflow` → `dataset` → `feature`。`dataset` は `repository` を使う | 手本と同じ決まり |
| 各フォルダの `__init__.py` で外に出すのは、ほかのフォルダから使うクラスだけにする | 外に見せるものが少ないほど、中を変えても外に響かない |
| この構成は、作りながら動かしてよい | 作る前に決めた構成は、少ない情報で決めたものだからである |

## 3. この予想だけのクラスの一覧

### dataset/ — 行を選ぶ・目的変数を付ける・人気を決める

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `FavoriteRule` | 人気馬の決まりを表す値。頭数の線引き（14頭以上が多頭数）と、頭数ごとの人気の範囲を持つ | `popularity_range(出走頭数)`、`is_favorite(人気, 出走頭数)`、`are_favorites(人気の列, 出走頭数の列)` | ― |
| `FavoriteSelector` | 学習データ・予測用データに入れる行を選び、「人気馬か」の列を足す。特徴量を作ったあとに、人気馬の行だけを残す（[06-flowchart.md](06-flowchart.md#図1-学習データに入れる行の選び方)） | `training_samples(出走の行, 学習データの始まり)`、`prediction_runners(出走の行, レースID)`、`keep_samples(特徴量の付いた行)` | `FavoriteRule`、共通の `FlatRunnerFilter` |
| `OutOfTop3TargetBuilder` | 目的変数を付ける。4着以下なら 1、3着以内なら 0（[10-target.md](10-target.md#作り方)） | `build(サンプルの行)`、`label_name` | ― |
| `PopularityApplier` | 予測のときに使う「馬番 → 人気」を決める。利用者が渡した人気を使い、無ければ元DB の締め切り前のオッズから作る（[06-flowchart.md](06-flowchart.md#図2-予測用データに人気を当てる)） | `resolve(レースID, 渡された人気)` | `AnnouncedOddsRepository` |
| `PopularityInput` | 利用者が渡した「馬番 → 人気」を表す値。`--pops 3:1 7:2` や `--pops 3:1,7:2` のような引数から作る | `of(引数の文字列)`、`as_mapping()` | ― |

決めた「馬番 → 人気」は、`PredictionWorkflow` が共通の `DatasetBuilder.build_prediction_data()` に渡し、出走の行に当てるのは共通の `RaceEntryTableRepository` である。人気を当てる仕事を出走の行の作り手に任せるので、`FavoriteSelector` は人気を決める手順を知らずに済む（[05-sequence.md](05-sequence.md#図2-予測)）。

### feature/ — まとまり J と、特徴量の一覧

| 名前 | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `PopularityHistoryFeatures` | まとまり J の4個を作る（[09-features.md](09-features.md#j-人気と人気の履歴4個)）。`FeatureGroup` を守る | `build(記録)` | `PopularityRunSummary`、共通の `AsOfLookup` |
| `PopularityRunSummary` | 過去走を、馬ごとの「その走までの近5走の人気のまとめ」にする（`feature/history/`） | `build(過去走)` | ― |
| `feature_catalog.py` の `J_FEATURES`・`CATALOG` | まとまり J の4個の一覧と、A〜I（共通の `BASE_FEATURES`）に J を足した、この予想の特徴量の一覧 | ―（値） | 共通の `FeatureCatalog` |

`FeatureBuilder` には、この `CATALOG` と、共通の A〜F・H・I の8つに `PopularityHistoryFeatures` を足したまとまりの並びを渡す（`dataset/dataset_assembly.py`）。G（`FieldComparisonFeatures`）は `FeatureBuilder` が内部で持つ。

### repository/ — 締め切り前のオッズ（共通）

| クラス | 読むもの | 主な public メソッド |
|---|---|---|
| `AnnouncedOddsRepository`（共通） | 締め切り前の単勝オッズ（`o1` の確定前の断面のうち、いちばん新しいもの）。断面は jvdata-store の `jvstore realtime` で入る（[07-prediction-timing.md](07-prediction-timing.md#予測のときの人気の与え方)） | `read(レースID)` |

はじめはこの予想だけが読むものとして、この予想のパッケージに置いていた。2026-09-23 に手本の予想も単勝オッズを使うようになったので、`shared/repository/` に移した。元DB にオッズの表が無いときは、ほかのリポジトリと同じく、同じ列を持つ空の関係で代わりにして「行なし」を返す。

### workflow/ — 流れを進める

| 名前 | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `PredictionWorkflow` | 予測の流れを進める。人気を決め、予測用データを作り、その時点のモデルを読み込み、2つの予測確率を平均する。木曜を渡されたら `ValueError` | `run(レースID, 時点, 渡された人気)` | `PopularityApplier`、共通の `DatasetBuilder`・`ModelRepository`・`EnsembleModel` |
| `prediction_timings.py` の `TIMINGS` | この予想が学習し、予測を出す時点（前日・当日）の並び | ―（値） | ― |

`PredictionWorkflow` は、ほかのクラスを呼んで受け渡すだけで、計算・判断・SQL は書かない。

**学習の流れ（`TrainingWorkflow`）と、学習の結果の入れ物（`TrainingReport`）は、共通の `shared/` に置く。** 手本の予想とこの予想で、`TrainingWorkflow` の中身は同じで、違うのは「学習する時点の並び」と「ハイパーパラメータの初期値のファイル」だけだからである。この2つは、作られるときに受け取る（`TrainingWorkflow(組み立て, 期間, モデルの置き場所, 時点の並び, 初期値のファイル)`）。この予想は `TIMINGS`（前日・当日の2つ）を渡すので、モデルは合わせて4つになる。

### command/ — コマンド

| クラス | 置き場所 | 仕事 | 主な public メソッド |
|---|---|---|---|
| `CommandLine` | この予想 | 入口。引数を読み、サブコマンドを実行し、結果の表を出す | `run(引数)` |
| `TrainCommand` | この予想 | `train`: 学習する。期間の引数から `TrainingPeriod` を作る。元DB は学習データを読む段だけ開き、学習のあいだはロックを持たない | `add_parser(subparsers)`、`run(引数)` |
| `PredictCommand` | この予想 | `predict`: 1レースの人気馬を予測する。`--pops` で人気を受け取り、`PopularityInput` にする | `add_parser(subparsers)`、`run(引数)` |
| `CommonArguments` | `shared` | 2つのサブコマンドに共通の引数（`--models` `--db` `--format` `--out`） | `add_to(parser)` |
| `TrainingReportTables` | `shared` | 学習の結果を表にする | `tables()` |
| `PredictionTable` | `shared` | 予測の結果を、4着以下になる確率の高い順の表にする。`extra_columns` に「人気順位」を渡して、人気の列も出す | `table()` |

`--timing` は、時点の書き方を共通の `PredictionTiming.parse()` で読む。木曜を渡されたときに止めるのは `PredictionWorkflow` で、誤りは `共通.cli` が1行で見せる（同じ判断を2か所に書かない）。

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-22 |
