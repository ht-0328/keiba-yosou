# 04 クラスとパッケージの設計

**この文書で決めること:** 手本の予想と同じ仕事をするクラスをどこに置くか。この予想だけに要るクラスは何か。共通の部品（`src/yosou/shared/`）に何を足すか。それらをどのフォルダ（パッケージ）・ファイルに置くか。コマンドの引数のうち、手本と違うものは何か。

**結論: 学習の流れは共通の `TrainingWorkflow`、予測の流れは共通の `PredictionWorkflow` が進める（手本と同じ）。予測の流れを時点に合わせて組み立てるのは、この予想の `GradedRacePrediction` である。この予想だけに作るのは、行の重みを決める `GradedRaceWeighter`、予測を重賞だけに絞る `GradedRunnerSelector`、まとまり W を作る `GradedRaceFeatures`（と部品 `GradeLadder`・`SameStakesHistory`）、特徴量の一覧、`DatasetBuilder` の組み立ての関数、重みの設定を読む `GradedWeightSettings`、コマンドである。`shared` には、行の重みを受け渡す仕組み（`SampleWeighter` と `TrainingData` の重み）、重みを渡す学習（`LightGbmModel`・`CatBoostModel`）、重賞での実績を読む `GradedCareerRepository` を足し、引退した予想のまとまり K の部品を `shared` に移す。**

- 1ファイル1クラス、1クラス1つの仕事、1 SQL につき1つのリポジトリ、Workflow は受け渡すだけ、という分け方の決まりは手本と同じで、[手本の 04 の「分け方の決まり」](../近走と適性から3着以内を予想/04-classes.md#分け方の決まり) を参照。
- 共通のクラスの一覧（どのクラスが何をするか）は [手本の 04 の「クラスの一覧」](../近走と適性から3着以内を予想/04-classes.md#クラスの一覧) を参照。この文書には、この予想だけのクラスと、`shared` に足す・変えるものを書く。
- 用語の意味（public メソッド・オーケストレーション・インターフェース・リポジトリ）は [手本の 02 の「機械学習の用語」](../近走と適性から3着以内を予想/02-glossary.md#機械学習の用語) を参照。
- クラスどうしが、どの順にどのメソッドを呼ぶかは [05-sequence.md](05-sequence.md) を参照。

## 1. 共通の部品と、この予想だけの部品の分け方

| まとまり | 共通にするか | この予想だけのもの |
|---|---|---|
| `repository/`（データの読み書き） | 共通。重賞での実績を読む `GradedCareerRepository` を足す（下の 2）。その重賞の傾向は、引退した予想の `StakesTendencyRepository`（共通にある）をそのまま使う | 無し |
| `dataset/`（学習データ・予測用データを作る） | 共通（`DatasetBuilder`・ローダー・`RunnerSelector`・`Top3TargetBuilder`・`Top3Baseline`・`WinBaseline`・`WinTargetData`・`OddsResolver`・`TrainingPeriod`・`PeriodSplitter`・`PoolFreeData`・`FinishPowerFreeData`・`PaceAttachment`）。行の重みの決まり `SampleWeighter` を足す | 重みを決める `GradedRaceWeighter`、予測を重賞に絞る `GradedRunnerSelector`、組み立ての関数 `graded_race_assembly.py` |
| `feature/`（特徴量を作る） | 共通（手本のまとまり A〜X の一覧と作るクラス）。まとまり K の部品を、引退した予想のパッケージから `shared/feature/stakes_tendency/` に移す | まとまり W を作る `GradedRaceFeatures`（部品 `GradeLadder`・`SameStakesHistory`）と、この予想の特徴量の一覧 |
| `ml_model/` | 共通。`LightGbmModel`・`CatBoostModel` が、学習データの重みを `fit` に渡すようにする（下の 2） | 無し |
| `setting/`・`evaluation/`・`place_value/`・`win_value/` | 共通 | 初期値の設定ファイル（重みの表を足したもの）と、重みの設定を読む `GradedWeightSettings`（[14-hyperparameter-settings.md](14-hyperparameter-settings.md)） |
| `workflow/`（流れを進める） | 学習は共通の `TrainingWorkflow`、予測は共通の `PredictionWorkflow` | 予測の流れを時点に合わせて組み立てる `GradedRacePrediction` と、時点の並び |
| `command/` | 部品は共通（`CommonArguments`・`TrainingReportTables`・`PredictionTable`・`PlacePriceStep`・`FigureCacheArgument`・`DevelopmentRootArgument`）。学習データの期間の引数は手本の `TrainPeriodArguments` と同じ形 | コマンドの組み立てと、重賞の行だけの当たり具合の表 `GradedValidationTables` |

**共通のクラスが、予想ごとの違いを知らずに済むようにする。** そのために、`shared` のインターフェース（`Protocol`）を、この予想のクラスが守る（手本と同じ仕組み）。

| インターフェース（`shared` にある） | 決まり（public メソッド） | この予想で守るクラス |
|---|---|---|
| `SampleSelector` | `training_samples(出走の行, 学習データの始まり)`、`prediction_runners(出走の行, レースID)`、`keep_samples(特徴量の付いた行)` | `GradedRunnerSelector`（学習は共通の `RunnerSelector` と同じく平地の全頭、予測は重賞だけ） |
| `SampleWeighter`（**足す**） | `weights(サンプルの行)` | `GradedRaceWeighter`（重賞の行は設定の重み、ほかは 1） |
| `TargetLabeler` | `build(サンプルの行)`、`label_name` | 共通の `Top3TargetBuilder` をそのまま使う |
| `FeatureGroup` | `build(記録)` | `GradedRaceFeatures`（W）。K は共通に移す `StakesTendencyFeatures` をそのまま使う |
| `TargetBaseline` | `known_from`、`build(レースの全頭の行)` | 共通の `Top3Baseline`・`WinBaseline` をそのまま使う |
| `ProbabilityModel` | `fit`・`predict_proba`・`save`・`load` | 共通の `LightGbmModel`・`CatBoostModel`（重みを受け取れるようにしたもの） |

| 決まり | 理由 |
|---|---|
| `shared` のクラスは、予想のパッケージを参照しない。予想のパッケージどうしも参照しない（例外は手本と同じ: 材料の部品 `yosou.form_aptitude_materials` と、学習のときの展開の予想 `yosou.race_development` の `PaceForecastHistory`） | 片方の予想の都合が、もう片方に入り込まない（手本と同じ決まり） |
| まとまり K の部品は、引退した予想のパッケージから `shared` に移し、引退した予想もそこから使う | この予想が引退した予想のパッケージを参照すると、上の決まりに反する。写すと2か所で食い違う |
| 重賞かどうかの判断（グレードコード A・B・C）は、`GradeLadder` の1か所に書き、重み・予測の絞り込み・W のどれもそれを使う | 学習の重み・予測の対象・特徴量の「重賞か」がずれない |
| 行の重みは目的変数とは別の列として持ち、特徴量にしない | 重みは「どの行の誤差を重く見るか」で、馬の材料ではない。予測のときには要らない |
| `TrainingData` の重みは既定を「無し」にし、`SampleWeighter` を渡された `DatasetBuilder` だけが付ける | 重みを使わないほかの予想は、今と同じ学習のまま（`fit` に重みが渡らない） |
| 重賞の行だけの当たり具合は、この予想のコマンドの表（`GradedValidationTables`）が出し、共通の `ModelEvaluator` は変えない | 共通の評価は全行で測る作りのままにし、「重賞の行だけ」はこの予想の事情として閉じる |

## 2. `shared` に足す・変えるもの

どれも、これから作る。ほかの予想の動きは変えない（重みを渡さなければ今と同じ）。

| 置き場所 | 追加・変更 | クラス | 内容 | 理由 |
|---|---|---|---|---|
| `shared/dataset/` | 追加 | `SampleWeighter` | 行の重みの決まり（インターフェース）。`weights(サンプルの行)` が、行ごとの重み（1 以上の数）を返す | 予想ごとの重みの付け方を、`DatasetBuilder` が知らずに済む |
| `shared/dataset/` | 変更 | `DatasetBuilder`・`TrainingData`・`SplitData`・`PeriodSplitter` | `DatasetBuilder` が作られるときに `SampleWeighter` を受け取れるようにし、受け取ったら `TrainingData.weight`（行ごとの重み）を付ける。`PeriodSplitter` は重みも同じ行で分ける。既定は重み無し | 学習データと検証データの両方に、同じ決まりで重みを付ける |
| `shared/dataset/` | 変更 | `WinTargetData`・`PoolFreeData`・`FinishPowerFreeData`・`PaceAttachment` | 持ち替え・列の付け外しのとき、重みをそのまま持ち越す | 1着のモデル・券種オッズなしのモデル・木曜のモデルも、同じ重みで学ぶ |
| `shared/ml_model/` | 変更 | `LightGbmModel`・`CatBoostModel` | `fit(学習データ, 検証データ)` で、学習データに重みがあれば、学習と検証の両方に渡す（LightGBM は `sample_weight`・`eval_sample_weight`、CatBoost は `Pool` の `weight`。[03-library-basics.md](03-library-basics.md#行に重みを付けて学ぶ)）。予測は変えない | 早期終了も、重賞の行を重く見た検証データの当たり具合で決める |
| `shared/repository/` | 追加 | `GradedCareerRepository` | `read(対象)`。1本の SQL で、対象の出走ごとに、その馬の開催日より前の中央の出走から、重賞の出走数・3着以内の数・勝利数、G1 の3着以内の数、今回の格以上のレースでの3着以内の数、直近の重賞の着順、前走のグレードコードとクラス名を数える（事実表の列から。1行 = 対象の出走） | まとまり W の実績の元（[09-features.md の W](09-features.md#w-重賞の格と実績14個)） |
| `shared/feature/` | 変更 | `EntryRecords` | 列 `graded_career`（上のリポジトリの表）を足す。既定は空の表 | 重賞の実績を、出走の行と突き合わせて W を作るため |
| `shared/dataset/` | 変更 | `EntryRecordsLoader`・`HistoryRecordsLoader`・`RaceRecordsLoader` | `GradedCareerRepository` を受け取れるようにし、受け取らなければ呼ばない（`graded_career` は空） | ほかの予想は SQL が増えない（`StakesTendencyRepository` と同じやり方） |
| `shared/feature/stakes_tendency/` | 移す | `StakesTendencyFeatures`・`ConditionBands`・`EditionStats`・`CUTS`・`TendencyCut`・`STATS`・`K_FEATURES` | 引退した予想のパッケージ（`src/yosou/stakes_tendency_top3/feature/`）から中身を変えずに移す。作り方は [引退した予想の 04 の 4](../重賞の傾向と近走から3着以内を予想/04-classes.md#4-この予想だけのクラスの一覧) と [09 の K](../重賞の傾向と近走から3着以内を予想/09-features.md#k-重賞の傾向51個) のまま | 2つの予想から使うため |

## 3. パッケージ構成

予想方法のコードは `src/yosou/` の下に置く（keiba-yosou の決まり）。この予想のパッケージ名は、予想のやり方が分かる `graded_race_top3_win`（graded race = 重賞、top3 = 3着以内、win = 1着）とする（名前は [15-decisions.md の 5](15-decisions.md#5-パッケージ名) で決める）。

```text
src/yosou/graded_race_top3_win/     重賞に特化して3着以内と1着を予想する
├── __main__.py                     コマンドの入口（command/ を呼ぶだけ）
├── command/                        コマンド（train・predict）の引数と、重賞の行だけの当たり具合の表
├── workflow/                       予測の流れの組み立て（GradedRacePrediction）と、予測を出す時点
├── dataset/                        行の重み・予測する行の選び方と、DatasetBuilder の組み立て
├── feature/                        まとまり W（重賞の格と実績）を作る。この予想の特徴量の一覧
├── setting/                        ハイパーパラメータと重みの初期値のファイル、重みの設定を読む部品
└── tests/                          この予想の組み立てのテスト。合成DB だけを使う（keiba-yosou の決まり）
```

各フォルダには `__init__.py` を置き、その先頭に「クラス → 仕事」の表を書く。ファイルの名前は、クラスの名前を小文字と `_` にしたもの（`GradedRaceWeighter` → `graded_race_weighter.py`）。

学習したモデルは、Git の対象外の `reports/重賞に特化して3着以内と1着を予想/models/` に、手本と同じ形で保存する。3着以内のモデルは `models/<時点>/`、1着のモデルは `models/1着/<時点>/`、当日の券種オッズなしは `models/券種オッズなし/race_day/`・`models/券種オッズなし/1着/race_day/`。直下には、複勝の見込みの倍率のファイル `place_price.json` を置く（手本と同じ）。

| 決まり | 理由 |
|---|---|
| 参照の向きは一方向にする: `graded_race_top3_win` → `form_aptitude_materials` → `shared` | 参照が循環すると、1つを直すと全部に響く（手本と同じ） |
| 予想のパッケージの中も一方向にする: `command` → `workflow` → `dataset` → `feature`、`command`・`dataset` → `setting` | 同上 |
| 各フォルダの `__init__.py` で外に出すのは、ほかのフォルダから使うクラスだけにする | 外に見せるものが少ないほど、中を変えても外に響かない |
| この構成は、作りながら動かしてよい | 作る前に決めた構成は、少ない情報で決めたものだからである |

## 4. この予想だけのクラスの一覧

### dataset/ — 行の重みと、予測する行の選び方

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `GradedRaceWeighter` | 学習データの行ごとの重みを決める。重賞の行は設定の重み（初期値 5）、ほかは 1（[06-flowchart.md の図1](06-flowchart.md#図1-学習データの行の重みの決め方)）。`SampleWeighter` を守る | `weights(サンプルの行)` | `GradeLadder` |
| `GradedRunnerSelector` | 入れる行を選ぶ。学習は共通の `RunnerSelector` と同じ（平地・出走した馬の全頭）。予測は、渡されたレースが平地の重賞でなければ `ValueError` を投げる（[06-flowchart.md の図2](06-flowchart.md#図2-予測する馬の行の選び方)。コマンドが「エラー:」の1行で見せる）。`SampleSelector` を守る | `training_samples(出走の行, 学習データの始まり)`、`prediction_runners(出走の行, レースID)`、`keep_samples(特徴量の付いた行)` | 共通の `RunnerSelector`、`GradeLadder` |
| `graded_race_assembly.py` の `ability_dataset_builder()`・`race_day_dataset_builder()` | 手本の組み立て（`shared/dataset/form_aptitude_assembly.py` の同じ名前の関数）と同じ部品に、この予想の部品（`GradedRunnerSelector`、`GradedRaceWeighter`、まとまりの並びに W の `GradedRaceFeatures` と K の `StakesTendencyFeatures` を足したもの、一覧、`StakesTendencyRepository` と `GradedCareerRepository`）を渡して、共通の `DatasetBuilder` を組み立てる関数。前者は木曜・前日（M・O・J に W・K）、後者は当日（A〜L・N・M・Q に W・K） | `ability_dataset_builder(接続, 重みの設定, スピード指数の置き場所)`・`race_day_dataset_builder(同じ)` | 上のクラスと共通の `DatasetBuilder` |

### feature/ — まとまり W と特徴量の一覧

| 名前 | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `GradedRaceFeatures`（`graded_race_features.py`） | まとまり W（重賞の格と実績）の 14個を作る。出走の行（グレードコード・クラス名・重量種別・斤量）と、`EntryRecords` の `graded_career`（重賞での実績）と `stakes_tendency`（同じ重賞の過去の開催の出走馬）から作る（[09-features.md の W](09-features.md#w-重賞の格と実績14個)）。`FeatureGroup` を守る | `build(記録)` | `GradeLadder`・`SameStakesHistory` |
| `GradeLadder`（`grade_ladder.py`） | グレードコードと競走条件から、格の名前（G1・G2・G3・L・OP・条件）と格の段を決める。重賞かどうかもここで答える（[06-flowchart.md の図3](06-flowchart.md#図3-格の名前の決め方)） | `name_of(グレードコード, クラス名)`、`step_of(格の名前)`、`is_graded(グレードコード)` | ― |
| `SameStakesHistory`（`same_stakes_history.py`） | `stakes_tendency` の表（対象のレース × 過去の開催の1頭）から、対象の馬自身の行を引き、同じ重賞の出走数・3着以内の数・直前の開催の着順を出す。重賞でないレースの行は欠損値 | `of(過去の開催の出走馬, 出走の行)` | ― |
| `W_FEATURES`・`ABILITY_CATALOG`・`RACE_DAY_CATALOG`・`RACE_DAY_WIN_CATALOG`（`feature_catalog.py`） | この予想の特徴量の一覧。手本の一覧（`shared/feature/form_aptitude_catalog.py`）に、W の一覧 `W_FEATURES`（14個。名前・まとまり・型・いつから分かるか）と K の一覧 `K_FEATURES`（51個）を足したもの（[07-prediction-timing.md](07-prediction-timing.md#時点ごとに使う特徴量)） | ―（値） | 共通の `FeatureCatalog` |

### workflow/ — 予測の流れの組み立て

| 名前 | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `GradedRacePrediction` | この予想の予測の流れを、時点に合わせて組み立てて1つの重賞を予測する。時点で `DatasetBuilder`（木曜・前日は `ability_dataset_builder`、当日は `race_day_dataset_builder`）・材料を足す関数（P・S・T のうち手本と同じもの）・モデルの置き場所（3着以内・1着・券種オッズなし）を選んで、共通の `PredictionWorkflow` を作る。手本の `FormAptitudePrediction` と同じ形で、組み立てる部品だけが違う | `run(接続, レースID, 時点, 渡されたオッズ=省略可)`、`explain(…)`、`workflow(接続, 時点)` | 共通の `PredictionWorkflow`、`yosou.form_aptitude_materials` の `MaterialAttachers` |
| `prediction_timings.py` の `TIMINGS`・`ABILITY_TIMINGS`・`FORM_TIMINGS` | 予測を出す時点（木曜・前日・当日）と、馬の力の材料で予測する時点（木曜・前日）、今の材料で予測する時点（当日）。手本と同じ分け方 | ―（値） | ― |

`PredictionWorkflow` は、ほかのクラスを呼んで受け渡すだけで、計算・判断・SQL は書かない（手本と同じ）。**印（◎○▲△☆注、消）・期待度・印からの買い目は、この予想のクラスでは付けない。** この予想は、3着以内と1着の確率と、複勝・単勝の期待値までを出す。印と期待度は、買い方の設計書の決まり（[07 の 5](../買うレースと買い目を決める/07-expected-value.md#5-印の付け方)・[03 の 5](../買うレースと買い目を決める/03-race-screening.md#5-レースごとの目安期待度)）を道具（今週の予想・印の成績）がこの予想の確率に当てて付ける（手本と同じ分け方。道具の直しは [05-sequence.md の「これから作るところ」](05-sequence.md#これから作るところ)）。

### setting/ — 初期値と重みの設定

| 名前 | 仕事 | 主な public メソッド |
|---|---|---|
| `default_settings.toml` | ハイパーパラメータの初期値（手本と同じ値）と、重賞の行の重みの初期値（`[sample_weight]` の `graded_race = 5.0`）（[14-hyperparameter-settings.md](14-hyperparameter-settings.md)） | ―（ファイル） |
| `GradedWeightSettings` | 設定ファイルの `[sample_weight]` の表を読む。共通の `SettingsFile`・`SettingsNameCheck`・`SettingsOverlay` で、初期値に利用者の設定を重ねる。重みが 1 未満ならエラー | `load(設定ファイルのパス, 初期値のファイル)`、`graded_race` |

### command/ — コマンド

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `CommandLine` | 入口。引数を読み、サブコマンドを実行し、結果の表を出す | `run(引数)` |
| `TrainCommand` | `train`: 学習する。手本の `TrainCommand` と同じ流れ（今の材料と馬の力の材料の2つの学習データで、3着以内と1着のモデルを学ぶ）。違うのは、`GradedWeightSettings` で重みを読んで組み立ての関数に渡すことと、学習のあとに重賞の行だけの当たり具合の表を足すこと | `run(引数)` |
| `PredictCommand` | `predict`: 1つの重賞を予測する。引数は手本と同じ（`--odds` など）。重賞でないレースは `GradedRunnerSelector` が止める | `run(引数)` |
| `GradedValidationTables` | 検証データのうち重賞の行だけで、時点ごと・目的変数ごとに、共通の `MetricCalculator` で指標（ログ損失・AUC・Brier・確率1位の馬の3着以内率と回収率・1番人気の同じ値）を出し、表にする | `tables(学習の結果)` |
| `TrainPeriodArguments` | 学習データの期間の引数。手本の `TrainPeriodArguments` と同じ引数・同じ既定（[08-training-data.md の 5](08-training-data.md#5-期間の指定)）。手本のパッケージを参照しないため、引数の定義は `shared/command/` に移して両方から使う | `add_to(parser)`・`form_period_of(引数)`・`ability_period_of(引数)` |

## 5. コマンドの引数

コマンドは `uv run python -m yosou.graded_race_top3_win <train か predict> …` で動かす。**引数は手本と同じである。** 共通の引数（`--models`・`--db`・`--format`・`--out`・`--figure-cache`・`--development-root`）、`train` の `--config` と期間の5つ、`predict` の `rid`・`--date`・`--venue`・`--race`・`--timing`・`--odds`、引数の決まり（省略形を受け付けない、誤りは「エラー:」の1行で止まる、元DB は読む段だけ開く）は、[手本の 04 の「コマンドの引数」](../近走と適性から3着以内を予想/04-classes.md#コマンドの引数) を参照。下の表は、この予想で違うところだけである。

| コマンド | 引数・出力 | この予想では |
|---|---|---|
| 共通 | `--models` の既定 | `reports/重賞に特化して3着以内と1着を予想/models` |
| `train` | `--config` | 手本の項目に加えて、重賞の行の重み（`[sample_weight]` の `graded_race`）も書ける（[14-hyperparameter-settings.md](14-hyperparameter-settings.md)） |
| `train` | 出す表 | 手本と同じ表に、「検証データのうち重賞の行だけの当たり具合」（時点ごと・目的変数ごと。LightGBM・CatBoost・平均の3行）を足す。使った重みも「学習データの期間」の表に出す |
| `predict` | `rid` | 平地の重賞のレースだけ。重賞でないレースを渡すと「エラー: このレースは平地の重賞（G1・G2・G3）ではない」の1行で止まる |
| `predict` | 出す表 | 手本と同じ（確率の高い順。前日・当日は複勝と単勝の期待値の列付き） |

```powershell
uv run python -m yosou.graded_race_top3_win train
uv run python -m yosou.graded_race_top3_win predict 2026111506050811 --timing 当日
```

（1行目は、既定の期間と重みで、3つの時点の3着以内と1着のモデルを学習するコマンド。2行目は、1つの重賞の出走馬について、3着以内に入る確率と1着になる確率を出すコマンド。レースID は架空の例）

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-11-14 |
