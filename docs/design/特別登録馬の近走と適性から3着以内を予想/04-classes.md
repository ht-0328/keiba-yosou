# 04 クラスとパッケージの設計

**この文書で決めること:** データを読む・特徴量を作る・学習する・予測するを、どのクラスにやらせるか。中央の予想の部品のうち、何をそのまま使い、何をこの予想のために足すか。クラスをどのフォルダ（パッケージ）・ファイルに置くか。コマンドが、どんな引数を受け取り、何を出すか。

**結論: 学習の流れは共通の `TrainingWorkflow`、予測の流れは共通の `PredictionWorkflow`、7つの区切りでの確かめは、この予想の `WindowedBacktestWorkflow` が共通の `TrainingWorkflow`・`BacktestWorkflow` を区切りごとに呼んで進める。** 中央の予想の部品（馬の力の材料 M・対戦レーティング O・能力スコア T を作る部品、`DatasetBuilder`、モデル、評価）はそのまま使う。この予想のために足すのは、特別登録から「登録馬の行」を作る部品と、材料を「登録日相当」で切る決まりと、特別競走の印（Y）と、登録馬の確かめである。足すものは、この予想のパッケージ `src/yosou/special_registration_top3/` と、事実表の部品 `tools/共通/registration.py` に置き、共通の部品には「値を渡せる形」で小さく手を入れる。

- 用語の意味は [02-glossary.md](02-glossary.md) を参照。
- クラスどうしが、どの順にどのメソッドを呼ぶかは [05-sequence.md](05-sequence.md) を参照。
- 分け方の決まり（1ファイル1クラス・1クラス1つの仕事・1 SQL 1 リポジトリ・Workflow は受け渡すだけ・`Manager` を付けない など）は、中央の予想の [04 の「分け方の決まり」](../近走と適性から3着以内を予想/04-classes.md#分け方の決まり) と同じである。

## 1. 共通の部品と、この予想だけの部品の分け方

| 区分 | 何か | 置き場所 |
|---|---|---|
| そのまま使う共通の部品 | `DatasetBuilder`・`HistoryRecordsLoader`・`EntryRecordsLoader`・`AbilitySourcesLoader`・`FeatureBuilder`・`HorseAbilityFeatures`（M）・`HeadToHeadRatingFeatures`（O）・`RunnerSelector`・`Top3TargetBuilder`・`WinTargetData`・`PeriodSplitter`・`TrainingPeriod`・`LightGbmModel`・`CatBoostModel`・`EnsembleModel`・`TrainingWorkflow`・`PredictionWorkflow`・`BacktestWorkflow`・`SegmentedPrediction`・`ModelRepository`・`HyperparameterSettings`・評価のクラス | `src/yosou/shared/` |
| そのまま使う、ほかの予想の部品 | `AbilityScoreAttachment`（T を足す）・`ABILITY_SCORE_FEATURES` | `src/yosou/ability_score/`（設計書「買うレースと買い目を決める」の[モジュール2](../買うレースと買い目を決める/04-ability-aptitude.md)） |
| 値を渡せる形に直す共通の部品 | 事実表の SQL（`facts.py`。`ra`・`se` の代わりに読む関係）、`TargetScope`（材料の締めの日の列）、`WorkoutSummaryRepository`・`AbilityRunRepository`・`HeadToHeadRunRepository`（締めの日の列を読む）、`CumulativeRecordRates`・`RecentRecordRates`・`RatingHistoryBuilder`（締めの日で切る）、`PredictionTiming.parse`（「特別登録」の書き方）、`TrainingRows`（区切りの終わりで切る `RowsUntil`） | `tools/共通/`・`src/yosou/shared/` |
| この予想だけの部品 | 登録馬の行の SQL、登録馬の行の一時表、登録のあるレースを引く、登録馬の記録を集める、登録日相当、特別競走の印（Y）、特徴量の一覧、相手と比べる材料を外す、時点の表示名、7つの区切りでの確かめ、登録馬の確かめ、コマンド、初期値の設定ファイル | `tools/共通/registration.py`・`src/yosou/special_registration_top3/` |

**共通の部品に if 文を足さず、値を渡せる形にするのは、中央の予想の動きを変えずにこの予想を足すためである。** 事実表の SQL は、渡さなければ今までどおり `ra`・`se` を読む。材料の締めの日は、列が無ければ今までどおり開催日の前日になる。中央の予想・道具・テストはそのまま通る。

## 2. パッケージ構成

```text
tools/共通/
├── facts.py                    事実表の SQL。ra・se の代わりに読む関係（EntryRows）を受け取れるようにする。既定は今のまま
└── registration.py             特別登録（tk・tk__登録馬毎情報・um）から、ra・se と同じ列の「登録馬の行」を作る SQL（registration_rows_sql(接続, rid)。表が無い DB では空の関係）

src/yosou/shared/               両方の予想から使う部品（中央の予想の 04 の構成と同じ）
├── repository/                 TargetScope に材料の締めの日の列（as_of_date）が増える。調教のまとめ・馬の力の出走・対戦の出走の3つのリポジトリが、その列を読む
├── feature/ability/            MaterialCutoff が行ごとの締めの日を答え、CumulativeRecordRates・RecentPeopleRates が、その日で切る
├── feature/head_to_head/       RatingHistoryBuilder が、締めの日の時点のレーティングを付ける
├── feature/prediction_timing.py  「特別登録」も thursday の枠として受ける（REGISTRATION_TIMING_LABEL）
└── dataset/                    TrainingRows に、区切りの終わりで行を切る RowsUntil が増える

tools/全頭評価/                 登録馬の全頭評価（この予想の確率と寄与・事実表・重賞の傾向から、1レース1枚の Markdown を書く道具）
├── review.py                   入口（レースを選び、評価を書く）
├── field_review.py             1レースの評価を組み立てる
├── horse_points.py             1頭の強み・弱みの文
├── stakes_tendency_points.py   重賞の過去の開催からの傾向の文
├── horse_facts_repository.py・previous_run_repository.py・stakes_edition_repository.py・registration_stakes_map.py  読む部品（1 SQL 1 クラス）
├── review_labels.py            特徴量の分類と名前（今週の予想の FeatureLabels を再利用）
├── review_document.py・review_writer.py  文書の中身と Markdown
└── tests/                      合成DB の特別登録で、評価が1枚書けることのテスト

src/yosou/special_registration_top3/   特別登録馬の近走と適性から3着以内を予想する
├── __main__.py                 コマンドの入口（command/ を呼ぶだけ）
├── command/                    コマンド（train・predict・backtest・registrations）の引数。入口
├── workflow/                   予測を出す時点と表示名（特別登録）、1着のモデルの置き場所、7つの区切りでの確かめ、登録馬の確かめ
├── dataset/                    DatasetBuilder の組み立て（1つ）、登録馬の記録を集める、登録日相当、相手と比べる材料を外す
├── repository/                 登録馬の行の一時表、登録のあるレースを引く（2つの SQL。1 SQL 1 リポジトリ）
├── feature/                    この予想の特徴量の一覧（M 168個・O・T・Y の 180個）と、特別競走の印（Y）を作るクラス
├── setting/                    ハイパーパラメータの初期値のファイル
└── tests/                      この予想の組み立てのテスト。合成DB（tools/合成DB/synth.py に tk を足す）だけを使う
```

各フォルダには `__init__.py` を置き、その先頭に「クラス → 仕事」の表を書く。ファイルの名前は、クラスの名前を小文字と `_` にしたもの。学習したモデルは、Git の対象外の `reports/特別登録馬の近走と適性から3着以内を予想/models/` に保存する。3着以内のモデルは `models/thursday/`、1着のモデルは `models/1着/thursday/`。時点のフォルダ名は共通の値（`thursday`）のままにする（[07-prediction-timing.md の「時点の表し方」](07-prediction-timing.md#時点の表し方)）。7つの区切りのモデルは `models-区切り/<区切り>/`、予測の表は `predictions/` に書く。

| 決まり | 理由 |
|---|---|
| 参照の向きは一方向にする: `special_registration_top3` → `shared`・`ability_score`。`shared` から予想のパッケージを参照しない。中央の予想のパッケージ（`form_aptitude_top3`）も参照しない | 片方の予想の都合が、もう片方に入り込まない |
| 中央と同じ部品は `shared` に1つだけ置き、このパッケージに写さない | 片方だけ直すと食い違う |
| この予想だけの決めごとは、`shared`・`tools/共通` の中に if 文で書かず、値（`EntryRows`・`as_of_date` の列・`RowsUntil`）として外から渡す。渡さなければ今までの動き | 共通のクラスの中に「どの予想か」の if 文が増えない。中央の動きが変わらない |
| 登録馬の行の SQL は `tools/共通/registration.py` に置く | 事実表の SQL と同じ列を作るので、事実表の SQL の隣に置く（`src/yosou/` の下に事実表の列の定義を写さない） |
| この構成は、作りながら動かしてよい | 作る前に決めた構成は、少ない情報で決めたものだからである |

## 3. 共通の部品に足すこと

| 部品 | 足すこと | 中央（既定） | この予想 |
|---|---|---|---|
| `facts.facts_sql()`・`build_entry_facts()` | `ra`・`se` の代わりに読む関係（`EntryRows`: レースの行の関係と、出走の行の関係）を受け取る。省略すると `ra`・`se` | `ra`・`se` | `registration.registration_rows_sql(接続, rid)` が作る「登録馬の行」（`ra`・`se` と同じ列。下の表）を足した関係 |
| `TargetScope` | 関係に「材料の締めの日」の列 `as_of_date` があれば、それを締めの日にする（`as_of_column`・`as_of_expr()`）。無ければ開催日の前日 | 列が無い（前日まで） | 学習では事実表に `RegistrationCutoff` の SQL の式で列を足した関係（`HistoryRecordsLoader(as_of_sql=…)` が `TargetScope.since(first_day, as_of_sql)` に渡す）、予測では登録馬の行の一時表の列（`TargetScope.of_table(表, as_of_column)`） |
| `WorkoutSummaryRepository` | 14日・30日の調教を `as_of_date` までで数える | 前日まで | 登録日相当まで（最終追い切りは入らない） |
| `AbilityRunRepository`・`HeadToHeadRunRepository` | 対象の行の `as_of_date` を読んで返す（SQL は変えず、列を足すだけ） | 列は欠損値 | 登録日相当 |
| `CumulativeRecordRates`・`RecentRecordRates` | 対象の行に `as_of_date` があれば、その日までの記録で数える（無ければ前日まで） | 前日まで | 登録日相当まで |
| `RatingHistoryBuilder` | 対象の行に、`as_of_date` までのレースの結果で更新したレーティングを付ける（レーティングを書く日を締めの日の翌日にし、更新は開催日のまま行う） | 開催日の前日の時点 | 登録日相当の時点 |
| `MaterialCutoff`（`shared/feature/ability/`） | 行ごとの材料の締めの日を答える（`as_of_date` があればその日、無ければ開催日の前日）。`CumulativeRecordRates`・`RecentPeopleRates` が使う | 開催日の前日 | 登録日相当 |
| `PredictionTiming.parse()` | 「特別登録」も `thursday` として受ける（`REGISTRATION_TIMING_LABEL`。地方の「出馬表」と同じ形） | 木曜・前日・当日 | 「特別登録」。表示名はこの予想の `TIMING_LABELS` で、`TrainingReportTables`・`PredictionTable`・`BacktestReportTables` に渡す |
| `TrainingRows` | 区切りの終わり（テスト期間の終わり）より後の行を落とす `RowsUntil(日)` を足す | `AllRows` | `WindowedBacktestWorkflow` が区切りごとに渡す |
| `tools/合成DB/synth.py` | 合成DB に `tk`・`tk__登録馬毎情報` を足す（確定前のレースに登録馬の行。値は架空） | ― | この予想のテストが使う |

**登録馬の行（`registration.registration_rows_sql(接続, rid)`）の作り方。** `tk` の月曜の版（データ区分 2。無ければ日曜の版 1。削除 0 は読まない）から、レースの行（`ra` と同じ列）と、登録馬ごとの出走の行（`se` と同じ列）を作る。馬番・枠番は NULL、出走したか（`ran`）は真（出走するとみなす）、異常区分は無し。

| `ra`・`se` の列 | 登録馬の行での元 |
|---|---|
| 開催年・開催月日・競馬場コード・開催回・開催日目・レース番号（rid） | `tk` のキー |
| 競走名・特別競走番号・グレードコード・競走種別・競走記号・重量種別・競走条件コード（2歳〜5歳以上・最若年）・距離・トラックコード・コース区分 | `tk` の同じ名前の列 |
| 馬場状態（芝・ダート）・天候・出走頭数 | NULL（未発表）。出走頭数は使わない特徴量なので欠損のまま |
| 血統登録番号・馬名・性別コード・調教師コード・調教師東西所属コード・負担重量 | `tk__登録馬毎情報` の同じ名前の列（負担重量は、ハンデ戦の日曜の版では 0 → NULL） |
| 馬齢 | 開催年 − 血統登録番号の先頭 4 桁（生年）。`se` の馬齢に当たる |
| 馬主コード・生産者コード・3代血統（父・父の父・母父） | 競走馬マスタ（`um`・`um__3代血統情報`）と産駒マスタ（`sk`）から、血統登録番号で引く。無い馬（初招待の外国馬など）は NULL |
| 馬番・枠番・騎手コード・騎手の減量・ブリンカー使用区分・馬体重・増減・単勝オッズ・単勝人気・着順 | NULL（この時点には無い。木曜以降に DB に `se` があっても読まない。[11-leak-prevention.md の 7](11-leak-prevention.md#決まり)） |
| 異常区分 | 無し（出走するとみなす）。出走取消は木曜以降の話なので反映しない |

事実表と同じ SQL（`facts_sql`）が、この行に前走・累積・同じ競走名での成績・クラスの並び順を付ける。クラスは競走条件コードとグレードコードから、中央と同じ `class_name_sql` で読む。材料の締めの日（`as_of_date`）は `RegistrationCutoff` の SQL の式で付ける。

## 4. クラスの一覧

中央の予想と共通のクラス（`DatasetBuilder`・`FeatureBuilder`・M と O のクラス・`LightGbmModel`・`CatBoostModel`・`EnsembleModel`・`TrainingWorkflow`・`PredictionWorkflow`・`ModelRepository`・評価・設定）の仕事と public メソッドは、中央の予想の [04 の「クラスの一覧」](../近走と適性から3着以内を予想/04-classes.md#クラスの一覧) を、`BacktestWorkflow` は地方の予想の [04 の「workflow/」](../地方競馬の近走と適性から3着以内を予想/04-classes.md#workflow--流れを進めるshared) を参照。ここには、この予想のために足すクラスと、直す共通のクラスを書く。

### workflow/ — 流れを進める（この予想。学習・予測・テスト期間の確かめは `shared`）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `TrainingWorkflow`（`shared`。そのまま） | 学習の流れ。時点は `TIMINGS`（特別登録の1つ）。学習データを作る → 時期で分ける → LightGBM と CatBoost を学習する → 保存する → 検証データで当たり具合を確かめる | `run(設定ファイルのパス)`、`read_training_data()`、`train(学習データ, 設定ファイルのパス)` |
| `PredictionWorkflow`（`shared`。そのまま） | 予測の流れ。予測用データを作り、3着以内のモデルと1着のモデルで2つの予測確率を平均する。オッズを決める段・券種オッズなしへの切り替え・期待値は、この予想では使わない（渡さない） | `run(レースID, 時点)` |
| `WindowedBacktestWorkflow`（この予想） | 7つの区切りでの確かめの流れ（[16-evaluation.md の 4.](16-evaluation.md#4-7つの区切りでの確かめ)）。学習データを1回作り、区切りごとに、区切りの終わりで行を切り（`RowsUntil`）、その区切りの `TrainingPeriod` で共通の `TrainingWorkflow.train()` を呼んで `models-区切り/<区切り>/` に保存し、共通の `BacktestWorkflow.run()` でテスト期間を予測して、区切りの名前を付けた予測の表を1つにまとめる。`--variant 相手と比べない` のときは `FieldComparisonFreeData` で列を外してから同じ手順を通す。`--compare` で木曜のモデルの予測の表が渡されれば、`PredictionComparison` で同じレース・同じ馬を突き合わせる | `run(学習データ, 区切りの一覧, 設定ファイルのパス)` |
| `PredictionComparison`（この予想） | 2つの予測の表（この予想と木曜のモデル）を、レースID と馬ID で突き合わせ、特別競走の行だけで、区切りごとにログ損失・AUC を並べる | `compare(この予想の予測, 木曜の予測)` |
| `RegistrationCheckWorkflow`（この予想） | 登録馬の確かめの流れ（[16-evaluation.md の 7.](16-evaluation.md#7-登録馬全員に出した予想の確かめ)）。期間の特別登録のレースを `RegistrationListRepository` で引き、1レースずつ `PredictionWorkflow.run()` で登録馬の全員に予測を出し、事実表の確定成績と突き合わせて、出走したか・着順・確定人気を付けた表を書く | `run(期間)` |
| `registration_prediction_workflow()`（この予想） | 共通の `PredictionWorkflow` を、この予想の決めごと（登録馬の行の `registration_dataset_builder`・オッズを決めない `NoOddsResolver`・複勝の期待値なし・3着以内と1着の両方に T を足す関数）で組み立てる関数（`prediction_assembly.py`） | `registration_prediction_workflow(接続, モデルの置き場所, スピード指数の置き場所=省略可)` |
| `SpecialRaceEvaluation`・`SpecialRaceRows`（この予想） | テスト期間の行のうち特別競走の行（Y = 1）と、予測の表の確率（レースID・馬ID で突き合わせる）を集め、モデルごと・平均と「頭数から見た割合」の当たり具合を測る。区切りをまたいでつなげて全期間の値も出す | `rows_of(テスト期間の行, 予測の表, 区切りの名前)`、`evaluate(時点, 行)` |
| `BacktestWindow`・`WINDOWS`・`windows_named()`（この予想） | 7つの区切りの表（名前・検証とテストの始まり・テスト期間の終わり）と、名前で選ぶこと（`backtest_windows.py`） | `period(ウォームアップの始まり, 学習の始まり)` |
| `TIMINGS`・`TIMING_LABELS`・`WIN_FOLDER`（この予想） | 予測を出す時点（`thursday` の1つ）、時点の表示名（特別登録）、1着のモデルの置き場所、モデルと予測の表の既定の置き場所（`prediction_timings.py`） | ― |

### command/ — コマンド（入口はこの予想、部品は `shared`）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `CommandLine` | 入口。引数を読み、サブコマンド（train・predict・backtest・registrations）を実行し、結果の表を出す | `run(引数)` |
| `TrainCommand` | `train`: 学習する。1つの学習データ（`registration_dataset_builder`）に T を足し（`AbilityScoreAttachment`）、3着以内のモデルと、目的変数を「1着」に持ち替えた1着のモデル（`WinTargetData`。基準は無し）を学ぶ。元DB は学習データを読む段だけ開く | `run(引数)` |
| `PredictCommand` | `predict`: 1レースの登録馬の全員を予測する。rid か `--date --venue --race` で指定し、`--all` でその日の登録のある全レース。登録が無ければ、取り込み方（jvdata-store の `fetch --dataspec TOKU`）を案内して止まる | `run(引数)` |
| `BacktestCommand` | `backtest`: 7つの区切りでの確かめ。`WindowedBacktestWorkflow` を呼び、区切りごとの当たり具合の表を出し、予測の表を `reports/特別登録馬の近走と適性から3着以内を予想/predictions/` に書く | `run(引数)` |
| `RegistrationsCommand` | `registrations`: 登録馬の確かめ。`RegistrationCheckWorkflow` を呼び、出走した登録馬だけでの当たり具合（登録馬の中で比べた材料のずれ）を出す。出走するかどうかは当てないので、出走しなかった馬の割合は出さない | `run(引数)` |
| `CommonArguments`（`shared`） | 共通の引数（`--models` `--db` `--format` `--out`）。予想の名前を受け取る | `add_to(parser)` |
| `PeriodArguments`（この予想） | `train` と `backtest` に共通の、学習データの期間の引数（`--warmup-from` `--train-from` `--valid-from` `--test-from`）と、引数から `TrainingPeriod` を作ること | `add_to(parser)`、`period_of(args)` |
| `FigureCacheArgument`（`shared` に移す） | スピード指数の置き場所の引数（`--figure-cache`）。中央の予想のパッケージにあるものを、両方から使えるように `shared/command/` に移す | `add_to(parser)` |
| `RegistrationPredictionTable` | 登録馬の予測の結果を、3着以内の確率の高い順の表にする（順位・馬名・調教師・負担重量・交流区分・3着以内と1着の確率・LightGBM と CatBoost の確率。馬番・オッズ・期待値の列は無い） | `table()` |
| `WindowedBacktestTables` | 7つの区切りでの確かめの結果を、目的変数ごとの「特別競走の行の当たり具合」「全レースの行の当たり具合（参考）」「木曜のモデルとの比べ」と書いた予測の表 の表にする | `tables()` |
| `RegistrationCheckTables` | 登録馬の確かめの結果を、「登録と出走」「出走した登録馬だけでの当たり具合」「予測できなかったレース」「書いた表」の表にする | `tables()` |

### dataset/ — 学習データ・予測用データを作る（組み立てはこの予想、ほかは `shared`）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `registration_dataset_builder()`（この予想） | 共通の `DatasetBuilder` を、この予想の決めごとで組み立てる関数（`dataset_assembly.py`）。学習用のローダーは共通の `HistoryRecordsLoader`（`AbilitySourcesLoader` と `HeadToHeadRunRepository` を渡し、対象は `RegistrationCutoff` の締めの日の列を足した `TargetScope`）、予測用のローダーは `RegistrationRecordsLoader`。行の選び方は `RunnerSelector`、目的変数は `Top3TargetBuilder`、特徴量は `FeatureBuilder(CATALOG, (HorseAbilityFeatures(168列), HeadToHeadRatingFeatures(), SpecialRaceFeatures()))`、基準は無し。学習データの始まりは `TRAIN_FIRST_DAY`（2012年1月1日） | `registration_dataset_builder(接続, スピード指数の置き場所=省略可)` |
| `RegistrationRecordsLoader`（この予想） | 予測用に、1レースの登録馬の記録を集める。事実表を用意し（`FactTableRepository.ensure()`）、登録馬の行の一時表を作り（`RegistrationEntryTableRepository.build()`）、共通の `EntryRecordsLoader.load()` で記録を集める。速報（馬場状態・馬体重・取消）とオッズは読まない（この時点には無く、あっても使わない）。`RaceRecordsLoader` と同じ `load(レースID, 単勝人気=省略可, 単勝オッズ=省略可)` の形を守り、人気とオッズは受け取っても使わない | `load(レースID)` |
| `RegistrationCutoff`（この予想） | 登録日相当（材料の締めの日）の決め方: 開催日より前の直近の月曜日（[06-flowchart.md の図3](06-flowchart.md#図3-登録日相当の決め方)）。SQL の式（事実表・登録馬の行に列を足す）と、Python の関数（テストと表示）の両方を持つ | `sql(開催日の式)`、`of(開催日)` |
| `FieldComparisonFreeData`（この予想） | 学習データ・予測用データから相手と比べる材料の 70列（`FIELD_COMPARISON_NAMES`）を外し、一覧からも除く（`backtest --variant 相手と比べない`） | `training(学習データ)`、`prediction(予測用データ)` |
| `RunnerSelector`・`Top3TargetBuilder`・`WinTargetData`・`PeriodSplitter`・`TrainingPeriod`（`shared`。そのまま） | 入れる行の選び方（[06-flowchart.md の図1](06-flowchart.md#図1-学習データに入れる行の選び方)）、目的変数（3着以内と1着）、1着のモデル用の持ち替え（基準の無い学習データでは目的変数の列だけを持ち替える）、時期で分ける、期間の4つの日 | ― |
| `RowsUntil`（`shared` に足す） | 学習データから、ある日（その日を含まない）より後の行を落とす（`TrainingRows` の決まりを守る）。区切りごとの学習に使う。元DB は使わない | `keep(接続=None, 学習データ)` |
| `NoOddsResolver`（この予想） | 予測に使うオッズを決めない（いつも None）。共通の `PredictionWorkflow` の「オッズを決める」段に渡す | `resolve(レースID, 渡されたオッズ)` |

### repository/ — データの読み書き（1 SQL につき 1 リポジトリ。この予想）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `RegistrationEntryTableRepository` | 1レースの登録馬に、事実表と同じ列を付けた一時表を作る。`registration.registration_rows_sql(接続, rid)` の登録馬の行を `EntryRows` として `facts.build_entry_facts()` に渡し、作られるときに受け取った締めの日の SQL の式（`RegistrationCutoff.sql`）で材料の締めの日の列を足す。登録が無ければ、取り込み方（`jvstore fetch --dataspec TOKU`）を添えて `LookupError`。月曜の版が無ければ日曜の版を使う（[06-flowchart.md の図2](06-flowchart.md#図2-登録馬の行の作り方)） | `build(レースID)` |
| `RegistrationEntryInfoRepository` | 1レースの登録馬の、表に出す情報（調教師の略称・負担重量・交流区分）を特別登録から読む（1 SQL）。事実表の列には調教師の名前と交流区分が無いので、`predict` と `registrations` が予測のあとに馬ID で突き合わせる | `read(レースID)` |
| `RegistrationRaceRepository` | 開催日・競馬場・レース番号から、`tk` にある登録の rid を引く（1 SQL）。`ra` にまだ無いレースのため、`race.resolve_rid()` の代わりに使う | `resolve(開催日, 競馬場, レース番号)` |
| `RegistrationListRepository` | 期間の、特別登録のある平地のレースの一覧（rid・開催日・競走名の有無・登録頭数）を読む（1 SQL）。`predict --all` と `registrations` が使う | `read(期間)` |
| 共通のリポジトリ（`EntryRepository`・`PastRunRepository`・`AbilityRunRepository`・`SpeedFigureRepository`・`WorkoutSummaryRepository`・`SalePriceRepository`・`HeadToHeadRunRepository`・`CareerCountRepository`・`ModelRepository` など） | 事実表か一時表を対象に読むので、そのまま使う。締めの日の列を読む3つは上の「3.」 | ― |

### feature/ — 特徴量（一覧とこの予想のまとまりはこの予想、作るクラスは `shared`）

| 名前 | 仕事 |
|---|---|
| `REGISTRATION_ABILITY_FEATURES` | M の 202個から、特別登録の時点に無いもの 34個（枠番・馬番・馬場状態・馬体重の 10個、騎手の 20個、出走頭数、ブリンカー、持ち時計の順位 2個）を除いた 168個（[09-features.md の M](09-features.md#m-馬の力の材料168個)）。名前は共通の `ABILITY_FEATURES` のまま |
| `BASE_CATALOG`・`CATALOG` | `BASE_CATALOG` は `FeatureBuilder` が記録から作る一覧（176個）: `REGISTRATION_ABILITY_FEATURES` + `HEAD_TO_HEAD_FEATURES`（O）+ `SPECIAL_RACE_FEATURES`（Y）。`CATALOG` はそれに `ABILITY_SCORE_FEATURES`（T。学習データ・予測用データに `AbilityScoreAttachment` で足す）を足した、この予想の特徴量の一覧（180個）。どれも数値で、`thursday` から分かる |
| `FIELD_COMPARISON_NAMES` | 相手と比べる材料の 70個の名前（[09-features.md](09-features.md#相手と比べる材料70個)）。`FieldComparisonFreeData` が外すのに使う |
| `SPECIAL_RACE_FEATURES`・`SpecialRaceFeatures` | Y. 特別競走の印（1個）。出走の行の `race_name` が空でなければ 1、空なら 0。`FeatureGroup` を守る |
| `TIMING_LABELS`（`workflow/`） | 時点の表示名。`thursday` → 特別登録 |

### setting/ — 設定ファイル（初期値のファイルはこの予想、読むクラスは `shared`）

`setting/default_settings.toml` に初期値を置く（[14-hyperparameter-settings.md](14-hyperparameter-settings.md)）。読むクラスは共通の `HyperparameterSettings`。

### tools/共通/registration.py — 登録馬の行の SQL

| 名前 | 仕事 |
|---|---|
| `registration_rows_sql(接続, rid)` | `tk`・`tk__登録馬毎情報` から `ra`・`se` と同じ列の登録馬の行を作り、そのレースの `ra`・`se` の行の代わりに足した関係（`EntryRows`）を返す（上の「3.」の表。馬主・生産者・血統は事実表の SQL が `um`・`sk` から引く）。月曜の版を選び、無ければ日曜の版（`chosen_registration_sql`）。特別登録の表が無い DB では空の関係にする（`table_relation`・`runner_table_relation`） |
| `EntryRows`（`facts.py`） | 事実表の SQL が `ra`・`se` の代わりに読む関係の組（レースの行・出走の行）。省略すると `ra`・`se` |

### tools/全頭評価 — 全頭評価の道具

登録の時点の出し方（[15-decisions.md の 13](15-decisions.md#13-印の付け方と出し方)）。予想のパッケージではなく道具なので `tools/` に置き、この予想の部品（`registration_prediction_workflow`・`RegistrationEntryInfoRepository`・`RegistrationListRepository`・`RegistrationRaceRepository`）と、共通の `PredictionWorkflow.explain`（特徴量の値と寄与）、今週の予想の `FeatureLabels`、重賞の傾向の `共通.stakes` を使う。参照は道具 → 予想・共通の一方向。

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `FieldReview` | 1レースの全頭評価を組み立てる。予測（確率と寄与）→ 登録馬の行から事実を読む → 前走を読む → 重賞なら過去の開催を読む → 馬ごとに強み・弱みを作る → 文書にする | `build(レースID)` |
| `HorsePoints` | 1頭の強み・弱みの文を定型で作る。事実（能力指数と対戦レーティングのメンバー内順位、前走の着順と人気と着差、同じコース・同じレースの成績、休み明け・距離とクラスの変更・芝ダ替わり、先行力、調教師と血統の率と全体の値との差、調教のタイムの順位、中央での出走の有無）と、モデルの寄与（分類ごとのロジットの上げ下げが 0.05 以上の分類を上下 2つまで、根拠の特徴量を添えて） | `of(事実, 特徴量, 寄与, 登録頭数, 前走)` |
| `StakesTendencyPoints` | 重賞の過去の開催の出走馬から、登録馬と同じ条件（前走のレース名・前走の人気・休み明け・関西馬・好走経験）の馬の着別度数と回収率の文を作り、3着以内率が全体より 5ポイント以上高ければ強み、低ければ弱みにする。出走数 8未満の条件は出さない | `lines_of(過去の出走馬, 登録馬の事実, 前走のレース名)` |
| `HorseFactsRepository` | 登録馬の行の一時表から、評価に使う事実（近走・適性・人・血統）を読む（1 SQL） | `read(対象)` |
| `PreviousRunRepository` | 登録馬の前走（レース名・クラス・競馬場・距離・着順・人気・着差）を事実表から読む（1 SQL） | `read(対象)` |
| `RegistrationStakesMap` | 重賞の対応表（`stakes_map`）を用意し、登録の時点のレース（`ra` にまだ無い）を特別登録から足す（1 SQL）。重賞でなければ None | `ensure(レースID)` |
| `StakesEditionRepository` | 同じ重賞の過去の開催の出走馬（前走のレース名と人気・休み明け・所属・好走経験・着順・払戻）を読む（1 SQL） | `read(特別競走番号, 開催日)` |
| `ReviewLabels` | 特徴量の分類と名前。今週の予想の `FeatureLabels` に、能力スコア（T）を「能力」にする決まりを足す | `category(名前)`・`display_name(名前)`・`display_value(名前, 値)` |
| `ReviewWriter` | 文書（`FieldReviewDocument`）を Markdown にする（レースの条件、有力馬の候補、評価順の表、馬ごとの基本情報・強み・弱み、注記） | `markdown(文書)` |
| `HorseReview`・`FieldReviewDocument` | 文書の中身（1頭の評価と、1レースの評価） | ― |

```powershell
uv run python tools/全頭評価/review.py --date 2026-10-18 --venue 京都 --race 11
uv run python tools/全頭評価/review.py --date 2026-10-18 --all
```

（1行目は、1レースの登録馬の全頭評価を `reports/全頭評価/<開催日>/<rid>.md` に書いて標準出力にも出すコマンド。2行目は、その日の特別登録のある平地の全レースを順に書くコマンド。`--models` は予想の学習済みモデルの置き場所（既定は `reports/特別登録馬の近走と適性から3着以内を予想/models`）。1レース 1〜4分）

## コマンドの引数

コマンドは `train`（学習）・`predict`（登録馬の予測）・`backtest`（7つの区切りでの確かめ）・`registrations`（登録馬の確かめ）の4つで、リポジトリ直下から `uv run python -m yosou.special_registration_top3 <コマンド> …` で動かす。引数の名前と意味は、中央の予想の [04 の「コマンドの引数」](../近走と適性から3着以内を予想/04-classes.md#コマンドの引数) と同じにする。違いは次のとおり。

| 引数 | この予想での既定・意味 |
|---|---|
| `--models` | `reports/特別登録馬の近走と適性から3着以内を予想/models` |
| `--db` | `../jvdata-store/jvdata.duckdb`（中央と同じ）。読むだけ |
| `--timing` | 無い（時点は特別登録の1つ。`predict` は常にこの時点で出す） |
| `--odds` | 無い（オッズを使わない） |
| `--warmup-from`・`--train-from`・`--valid-from`・`--test-from` | [08-training-data.md の「4. 期間の指定」](08-training-data.md#4-期間の指定)。既定は 2011-01-01・2012-01-01・2025-07-01・2026-01-01。学習データは1つなので `--ability-train-from` は無い |
| `--figure-cache` | スピード指数の置き場所（既定 `reports/能力指数/cache/`。中央と同じ） |
| `--development-root` | 無い（P を使わない） |
| `predict` の `rid` / `--date --venue --race` | 登録のあるレース。rid は `tk` から引く（`RegistrationRaceRepository`）。`--all` でその日の登録のある全レース |
| `backtest` の `--windows` | 回す区切り（例 `2025年後半`。省略すると7つ全部）。区切りの表は [16-evaluation.md の 4.](16-evaluation.md#4-7つの区切りでの確かめ) |
| `backtest` の `--variant` | `全部`（既定。180個）か `相手と比べない`（110個）。予測の表の名前に付く |
| `backtest` の `--compare` | 木曜のモデルの予測の表（研究「既存モデルの改善」の7つの区切りの木曜の予測の pkl）。渡すと同じレース・同じ馬で比べる |
| `backtest` の `--models-root`・`--predictions` | 区切りごとのモデルの置き場所（既定 `reports/特別登録馬の近走と適性から3着以内を予想/models-区切り`）と、予測の表を書く場所（既定 `…/predictions`。`thursday.pkl`・`thursday-1着.pkl`。変えた版は名前に `-相手と比べない` が付く） |
| `registrations` の `--from`・`--to` | 確かめる特別登録の期間（既定はテスト期間の始まり 2026-01-01 から DB にある最後の日）。モデルは `--models`（既定は 2026年の区切りのモデル `models-区切り/2026年`） |

`train` が出す表は、学習データの期間・検証データでの当たり具合・人気の基準との比べ方・保存したモデル（`TrainingReportTables`）を、3着以内のモデルと1着のモデル（題に「1着:」が付く）の両方で出す。`predict` が出す表は、確率の高い順に、順位・馬名・調教師・負担重量・交流区分・出走すれば3着以内に入る確率・出走すれば1着になる確率・LightGBM と CatBoost の確率。馬番・オッズ・期待値の列は出ない（この時点には無い）。`backtest` と `registrations` が出す表は [16-evaluation.md](16-evaluation.md) を参照。

引数の決まり（省略を受け付けない・誤りは1行で止まる・元DB は読む段だけ開く）も中央と同じである。

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-10-13 |
