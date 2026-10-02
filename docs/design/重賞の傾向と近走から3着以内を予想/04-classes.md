# 04 クラスとパッケージの設計

**この文書で決めること:** 手本の予想と同じ仕事をするクラスをどこに置くか。この予想だけに要るクラスは何か。共通の部品（`src/yosou/shared/`）に何を足すか。それらをどのフォルダ（パッケージ）・ファイルに置くか。コマンドの引数のうち、手本と違うものは何か。

**結論: データを読む・特徴量を作る・学習する・予測するのクラスは、ほかの予想と共通で、すでに `src/yosou/shared/` にある。この予想だけに作るのは、重賞の行を選ぶ `RunnerSelector`、まとまり K（重賞の傾向）を作る `StakesTendencyFeatures`、予測の流れを進める `PredictionWorkflow`、コマンド（`train`・`predict`・`evaluate`）である。`shared` には、傾向を読む `StakesTendencyRepository` を1つ足し、記録の入れ物 `EntryRecords` に `stakes_tendency` の表を足す（展開から着順を予想する予想の `race_history` と同じやり方）。学習の流れ（`TrainingWorkflow`）は共通のものをそのまま使う。**

- 1ファイル1クラス、1クラス1つの仕事、1 SQL につき1つのリポジトリ、という分け方の決まりは手本と同じで、[手本の 04 の「分け方の決まり」](../近走と適性から3着以内を予想/04-classes.md#分け方の決まり) を参照。
- 共通のクラスの一覧（どのクラスが何をするか）は [手本の 04 の「クラスの一覧」](../近走と適性から3着以内を予想/04-classes.md#クラスの一覧) を参照。この文書には、この予想だけのクラスと、`shared` に足す・変えるものを書く。
- 用語の意味（public メソッド・オーケストレーション・インターフェース・リポジトリ）は [手本の 02 の「機械学習の用語」](../近走と適性から3着以内を予想/02-glossary.md#機械学習の用語) を参照。
- クラスどうしが、どの順にどのメソッドを呼ぶかは [05-sequence.md](05-sequence.md) を参照。

## 1. 共通の部品と、この予想だけの部品の分け方

| まとまり | 共通にするか | この予想だけのもの |
|---|---|---|
| `repository/`（データの読み書き） | 共通。重賞の傾向を読む `StakesTendencyRepository` を足す（下の 2） | 無し |
| `dataset/`（学習データ・予測用データを作る） | 共通（`DatasetBuilder`・ローダー・`Top3TargetBuilder`・基準 `Top3Baseline`・`OddsResolver`・`OddsInput`・`TrainingPeriod`・`PeriodSplitter`） | 重賞の行を選ぶ `RunnerSelector` と、部品を渡して組み立てる `dataset_assembly.py` |
| `feature/`（特徴量を作る） | 共通（手本と同じまとまり A〜N の一覧と作るクラス、過去の記録から数える部品） | まとまり K を作る `StakesTendencyFeatures` と、この予想の特徴量の一覧 `ABILITY_CATALOG`（木曜・前日）・`RACE_DAY_CATALOG`（当日。295個） |
| `ml_model/`・`setting/`・`evaluation/`・`place_value/` | 共通 | 初期値の設定ファイルだけ（[14-hyperparameter-settings.md](14-hyperparameter-settings.md)） |
| `workflow/`（流れを進める） | 学習は共通の `TrainingWorkflow` | `PredictionWorkflow` と、予測を出す時点の並び `TIMINGS` |
| `command/` | 部品は共通（`CommonArguments`・`TrainingReportTables`・`PredictionTable`・`PlacePriceStep`） | コマンドの組み立てと、期間の既定（手本と違う。[08-training-data.md の 4](08-training-data.md#4-期間の指定)）、`evaluate` コマンド |

**共通のクラスが、予想ごとの違いを知らずに済むようにする。** そのために、`shared` のインターフェース（`Protocol`）を、この予想のクラスが守る（手本と同じ仕組み）。

| インターフェース（`shared` にある） | 決まり（public メソッド） | この予想で守るクラス |
|---|---|---|
| `SampleSelector` | `training_samples(出走の行, 学習データの始まり)`、`prediction_runners(出走の行, レースID)`、`keep_samples(特徴量の付いた行)` | `RunnerSelector`（この予想。重賞の行だけを選ぶ） |
| `TargetLabeler` | `build(サンプルの行)`、`label_name` | 共通の `Top3TargetBuilder` をそのまま使う |
| `FeatureGroup` | `build(記録)` | `StakesTendencyFeatures`（K。この予想で新しく作る唯一のまとまり）。J は共通の `MarketFeatures` をそのまま使う |
| `TargetBaseline` | `known_from`、`build(レースの全頭の行)` | 共通の `Top3Baseline` をそのまま使う（手本と同じ基準。前日・当日だけ） |
| `ProbabilityModel` | `fit`・`predict_proba`・`save`・`load` | 共通の `LightGbmModel`・`CatBoostModel` をそのまま使う |

| 決まり | 理由 |
|---|---|
| `shared` のクラスは、予想のパッケージを参照しない。予想のパッケージどうしも参照しない | 片方の予想の都合が、もう片方に入り込まない（手本と同じ決まり） |
| 傾向の数え上げの SQL は `tools/共通/stakes.py` のものを使い、同じ SQL を2か所に書かない | 分析ツール（`tools/重賞攻略/`）とモデルで数え方がずれない（[01-overview.md の「関連する道具」](01-overview.md#関連する道具分析ツール重賞攻略)）。事実表（`tools/共通/facts.py`）と同じやり方 |
| `EntryRecords` の `stakes_tendency` は、既定を空の表にし、ローダーがリポジトリを受け取ったときだけ埋める | 重賞の傾向を使わないほかの予想では、SQL が1本も増えない（`race_history` と同じやり方） |
| 「重賞か」の判断は `RunnerSelector` の1か所に置く | 学習と予測で対象がずれない。予測で重賞でないレースを渡されたら、ここで止まる（下の 4） |

## 2. `shared` に足す・変えるもの

どれも実装済みである（2026-09-29）。ほかの予想の動きは変えていない。

| 置き場所 | 追加・変更 | クラス | 内容 | 理由 |
|---|---|---|---|---|
| `shared/repository/` | 追加 | `StakesTendencyRepository` | `read(対象)`。`tools/共通/stakes.py` の SQL で、重賞の対応表の一時表（rid → 特別競走番号・グレード）を用意してから、対象のレースごとに1行の傾向を読む。列は、開催の同定（`race_id`・`stakes_no`・`grade`・`editions` = 過去の開催の数）、切り口ごとの過去の出走数 `*_n`・3着以内の数 `*_hits`（前・内枠は期待の数 `*_exp` も）、基準 `base_*`（前・内枠は超過複勝率 `base_front_excess`・`base_inner_excess`。[09-features.md の「縮めたずれの定義」](09-features.md#縮めたずれの定義)）。重賞でないレースの行は返らない | まとまり K の元。対応表は傾向の SQL の前提の一時表なので、事実表（`FactTableRepository.ensure()`）と同じ扱いで、このリポジトリが用意する |
| `shared/feature/` | 変更 | `EntryRecords` | 列 `stakes_tendency`（上のリポジトリの表。対象の重賞のレースごとに1行）を足す。既定は空の表 | K を、出走の行と `race_id` で突き合わせて作るため |
| `shared/dataset/` | 変更 | `EntryRecordsLoader`・`HistoryRecordsLoader`・`RaceRecordsLoader` | 作られるときに `StakesTendencyRepository` を受け取れるようにする。受け取らなければ呼ばず、`stakes_tendency` は空 | ほかの予想は SQL が増えない（`race_history` の `RaceEarlyRecordRepository` と同じやり方） |

## 3. パッケージ構成

予想方法のコードは `src/yosou/` の下に置く（keiba-yosou の決まり）。この予想のパッケージ名は、予想のやり方が分かる `stakes_tendency_top3`（stakes = 重賞・特別競走、tendency = 傾向、top3 = 3着以内）とする。

```text
src/yosou/stakes_tendency_top3/     重賞の傾向と近走から3着以内を予想する
├── __main__.py                     コマンドの入口（command/ を呼ぶだけ）
├── command/                        コマンド（train・predict・evaluate）の引数と、期間の既定
├── workflow/                       予測の流れ（ほかを順に呼ぶだけ）と、予測を出す時点
├── dataset/                        重賞の行の選び方と、DatasetBuilder の組み立て
├── feature/                        まとまり K（重賞の傾向）を作る。この予想の特徴量の一覧（ABILITY_CATALOG・RACE_DAY_CATALOG）
├── setting/                        ハイパーパラメータの初期値のファイル
└── tests/                          この予想の組み立てのテスト。合成DB だけを使う（keiba-yosou の決まり）
```

各フォルダには `__init__.py` を置き、その先頭に「クラス → 仕事」の表を書く。ファイルの名前は、クラスの名前を小文字と `_` にしたもの（`StakesTendencyFeatures` → `stakes_tendency_features.py`）。学習したモデルは、Git の対象外の `reports/重賞の傾向と近走から3着以内を予想/models/` の下に、時点ごと（`thursday`・`day_before`・`race_day`）に保存する。直下には、複勝の見込みの倍率のファイル `place_price.json` を置く（手本と同じ）。

| 決まり | 理由 |
|---|---|
| 参照の向きは一方向にする: `stakes_tendency_top3` → `shared`。`shared` から予想のパッケージを参照しない | 参照が循環すると、1つを直すと全部に響く |
| 予想のパッケージの中も一方向にする: `command` → `workflow` → `dataset` → `feature` | 手本と同じ決まり |
| 各フォルダの `__init__.py` で外に出すのは、ほかのフォルダから使うクラスだけにする | 外に見せるものが少ないほど、中を変えても外に響かない |
| この構成は、作りながら動かしてよい | 作る前に決めた構成は、少ない情報で決めたものだからである |

## 4. この予想だけのクラスの一覧

### dataset/ — 重賞の行を選ぶ

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `RunnerSelector` | 入れる行を選ぶ。平地・出走した馬（共通の `FlatRunnerFilter`）のうち、重賞（グレードコード A・B・C）の行だけを残す（[06-flowchart.md の図1](06-flowchart.md#図1-学習データに入れる行の選び方)）。予測では、渡されたレースが重賞でなければ `ValueError` を投げる（コマンドが「エラー:」の1行で見せる）。`keep_samples` はそのまま返す（重賞の全頭がサンプル） | `training_samples(出走の行, 学習データの始まり)`、`prediction_runners(出走の行, レースID)`、`keep_samples(特徴量の付いた行)` | 共通の `FlatRunnerFilter` |
| `dataset_assembly.py` の `ability_dataset_builder()`・`race_day_dataset_builder()` | この予想の部品（`RunnerSelector`、共通の `Top3TargetBuilder`、一覧、まとまりの並び（手本と同じ並びに `StakesTendencyFeatures`（K）を足したもの）、基準の作り方 `Top3Baseline`、傾向のリポジトリ `StakesTendencyRepository` と、手本と同じ M・L・N・O の元の記録を読む部品）を渡して、共通の `DatasetBuilder` を組み立てる関数。前者は木曜・前日（M・O・J・K）、後者は当日（A〜L・N・M・K） | `ability_dataset_builder(接続, スピード指数の置き場所)`・`race_day_dataset_builder(同じ)` | 上のクラスと共通の `DatasetBuilder` |
| `PoolFreeData`・`PoolAvailability` | 当日に券種のオッズが無いとき、N を外して N を使わないモデルに切り替える部品。手本（`form_aptitude_top3`）のものを借りる（`shared` と手本を別の作業が変えていたため。落ち着いたら `shared` に移す） | ― | ― |

### feature/ — まとまり K と特徴量の一覧

| 名前 | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `StakesTendencyFeatures`（`stakes_tendency_features.py`） | まとまり K（重賞の傾向）の 10個を作る。`EntryRecords` の `stakes_tendency` の表を、出走の行と `race_id` で突き合わせ、切り口ごとの「縮めたずれ」と、自分が当てはまるかを掛けた列を作る（作り方は [09-features.md の K](09-features.md#k-重賞の傾向10個)）。`FeatureGroup` を守る | `build(記録)` | ― |
| `ABILITY_CATALOG`・`RACE_DAY_CATALOG`（`feature_catalog.py`） | この予想の特徴量の一覧。手本と同じ材料に K を足したもの（木曜・前日は `ABILITY_FEATURES + HEAD_TO_HEAD_FEATURES + MARKET_FEATURES + K_FEATURES`、当日は手本の当日の 285個 + `K_FEATURES` の 295個。[09-features.md](09-features.md)）。K の一覧 `K_FEATURES`（10個。名前・まとまり・型・いつから分かるか）も、このファイルに置く | ―（値） | 共通の `FeatureCatalog` |

### workflow/ — 流れを進める

| 名前 | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `PredictionWorkflow` | 予測の流れを進める。予測に使うオッズを決め、予測用データを作り、その時点のモデル2つを読み込み、予測確率を平均し、前日・当日は複勝の期待値を足す。手本の `PredictionWorkflow` と同じ流れ（[05-sequence.md の図2](05-sequence.md#図2-予測)） | `run(レースID, 時点, 渡されたオッズ=省略可)` | 共通の `OddsResolver`・`DatasetBuilder`・`ModelRepository`・`EnsembleModel`・`PlaceValueColumns` |
| `prediction_timings.py` の `TIMINGS`・`ABILITY_TIMINGS`・`FORM_TIMINGS` | この予想が学習し、予測を出す時点（木曜・前日・当日）と、馬の力の材料のモデルで予測する時点（木曜・前日）・当日の材料のモデルで予測する時点（当日）。手本と同じ分け方 | ―（値） | ― |

`PredictionWorkflow` は、ほかのクラスを呼んで受け渡すだけで、計算・判断・SQL は書かない。当日に券種のオッズが無ければ、N を外して券種オッズなしのモデルに切り替える（手本と同じ）。**学習の流れ（`TrainingWorkflow`）は、共通のものをそのまま使う。** この予想は材料ごとに `TrainingWorkflow` を作り、時点の並びと、初期値の設定ファイルと、この予想の期間の既定を渡す。モデルは 3つの時点と券種オッズなしの当日 × 2つで、8個になる。

### command/ — コマンド

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `CommandLine` | 入口。引数を読み、サブコマンドを実行し、結果の表を出す | `run(引数)` |
| `TrainCommand` | `train`: 学習する。期間の引数から `TrainingPeriod` を作る（**既定がこの予想専用。** [08-training-data.md の 4](08-training-data.md#4-期間の指定)）。学習のあとに、共通の `PlacePriceStep` で複勝の見込みの倍率を保存する（手本と同じ） | `add_parser(subparsers)`、`run(引数)` |
| `PredictCommand` | `predict`: 1つの重賞を予測する。引数は手本と同じ（`--odds` など）。重賞でないレースは `RunnerSelector` が止める | `add_parser(subparsers)`、`run(引数)` |
| `EvaluateCommand` | `evaluate`: 保存したモデルで、学習に使っていない期間（検証・テスト）の重賞を予測し、複勝を期待値で買ったときの回収率（共通の `ValueBands` の帯別）と、本命（確率1位）と1番人気の比べ方を表にする（[16-evaluation.md の 4](16-evaluation.md#4-evaluate-コマンド学習に使っていない期間での確かめ)） | `add_parser(subparsers)`、`run(引数)` |
| `period_defaults.py` の期間の既定 | この予想の期間の既定（[08-training-data.md の 4](08-training-data.md#4-期間の指定) の表の値）。`TrainCommand` と `EvaluateCommand` が使う | ―（値） |

## 5. コマンドの引数

コマンドは `uv run python -m yosou.stakes_tendency_top3 <train か predict か evaluate> …` で動かす。**引数の多くは手本と同じである。** 共通の引数（`--models`・`--db`・`--format`・`--out`）、`train` の `--config` と期間の4つ、`predict` の `rid`・`--date`・`--venue`・`--race`・`--timing`・`--odds`、引数の決まり（省略形を受け付けない、誤りは「エラー:」の1行で止まる、元DB は読む段だけ開く）は、[手本の 04 の「コマンドの引数」](../近走と適性から3着以内を予想/04-classes.md#コマンドの引数) を参照。下の表は、この予想で違うところだけである。

| コマンド | 引数・出力 | この予想では |
|---|---|---|
| 共通 | `--models` の既定 | `reports/重賞の傾向と近走から3着以内を予想/models` |
| `train`・`predict`・`evaluate` | `--figure-cache` | スピード指数をとっておく場所（手本と同じ引数。既定は `reports/能力指数/cache`） |
| `train` | 期間の引数の既定 | この予想専用の既定（[08-training-data.md の 4](08-training-data.md#4-期間の指定) の表）。引数で変えられるのは手本と同じ |
| `train` | 出す表 | 手本と同じ5つ（学習データの期間・検証データでの当たり具合・人気の基準との比べ方・保存したモデル・複勝の見込みの倍率） |
| `predict` | `rid` | 重賞のレースだけ。重賞でないレースを渡すと「エラー: このレースは重賞（G1・G2・G3）ではない」の1行で止まる |
| `predict` | 出す表 | 手本と同じ（確率の高い順。前日・当日は複勝の期待値の列付き） |
| `evaluate` | 引数 | `train` と同じ期間の4つと、共通の引数。学習のときと同じ区切りを渡すと、学習に使っていない検証・テストの期間で測る |
| `evaluate` | 出す表 | 期間（検証・テスト）× 時点ごとに、本命と1番人気の比べ方の表と、期待値の帯ごとの表（前日・当日だけ）。表の中身は [16-evaluation.md の 4](16-evaluation.md#4-evaluate-コマンド学習に使っていない期間での確かめ) |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-29 |
| 更新 | 2026-09-29: `shared` への追加とこの予想のパッケージが実装されたのに合わせ、状態と `StakesTendencyRepository` の列（`*_exp`・`base_*_excess`）を直した。2026-10-02: 手本の新しい材料で作り直したので、組み立ての関数・一覧・時点の分け方・券種オッズなしの部品を直した |
