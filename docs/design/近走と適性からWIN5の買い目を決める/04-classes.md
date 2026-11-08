# 04 クラスとパッケージの設計

**この文書で決めること:** 今のモデル（今毎週の予想に使っているモデル）の1着の確率を、この予想がどう受け取るか。この予想だけに要るクラス（WIN5 の日を読む・レースごとに使う確率を選ぶ・確率をそろえる・配当を見積もる・買い目を組む・過去の WIN5 で精算する）は何か。それらをどのフォルダ（パッケージ）・ファイルに置くか。コマンドの引数は何か。

**結論: 今のモデルの予測を作る部品（`DatasetBuilder`・`FeatureBuilder`・`PredictionWorkflow`・LightGBM と CatBoost のモデルなど）の多くは、すでに `src/yosou/shared/` にある。今のモデルのパッケージと道具「今週の予想」だけが持っていた「予測の流れの組み立て」と「時点の選び方」は `shared` に移した（材料を作る部品だけは `yosou.form_aptitude_materials`）。この予想はそれを呼んで、今のモデルの学習済みモデルで1着の確率を出す（[15-decisions.md の 9](15-decisions.md#9-今のモデルの1着の確率の受け取り方)）。この予想だけに作るのは、WIN5 の日の流れを進める `Win5PredictionWorkflow` と、対象レース（`leg/`）・配当（`payout/`）・買い目（`formation/`）・精算（`settlement/`）の部品、リポジトリ、コマンドである。モデルを学ぶクラスは作らない。**

- 1ファイル1クラス、1クラス1つの仕事、1 SQL につき1つのリポジトリ、入れ子は1段まで、という分け方の決まりは手本と同じで、[手本の 04 の「分け方の決まり」](../近走と適性から3着以内を予想/04-classes.md#分け方の決まり) を参照。
- 今のモデルのクラスの仕事は [手本の 04 の「クラスの一覧」](../近走と適性から3着以内を予想/04-classes.md#クラスの一覧) を参照。この文書には、移すものと、この予想だけのクラスを書く。
- 用語の意味（public メソッド・オーケストレーション・リポジトリ）は [手本の 02 の「機械学習の用語」](../近走と適性から3着以内を予想/02-glossary.md#機械学習の用語) を、「今のモデル」は [02-glossary.md](02-glossary.md#今のモデルの用語) を参照。
- クラスどうしが、どの順にどのメソッドを呼ぶかは [05-sequence.md](05-sequence.md) を参照。

## 1. 今のモデルの1着の確率の受け取り方

この予想は、道具「今週の予想」が出すのと同じ1着の確率を、WIN5 の1レース目の締め切り前に、対象レース5つについて出す必要がある。**予想のパッケージどうしで import はしない**（片方を直すともう片方が壊れる）ので、今のモデルのパッケージと道具にしか無かった次のものを `shared` に移し、今のモデル・道具「今週の予想」・この予想の3つから使う（[15-decisions.md の 9](15-decisions.md#9-今のモデルの1着の確率の受け取り方)）。移す作業は済んでいる。

| 移したもの | 前の置き場所 | 移した先 | この予想での使い方 |
|---|---|---|---|
| 特徴量の一覧（`ABILITY_CATALOG`・`RACE_DAY_CATALOG`・`RACE_DAY_WIN_CATALOG` など） | `form_aptitude_top3/feature/feature_catalog.py` | `shared/feature/form_aptitude_catalog.py` | 今のモデルの予測用データを作る |
| `DatasetBuilder` の組み立ての関数（`ability_dataset_builder()`・`race_day_dataset_builder()` など） | `form_aptitude_top3/dataset/dataset_assembly.py` | `shared/dataset/form_aptitude_assembly.py` | 同上 |
| 時点の並びとモデルの置き場所の名前（`ABILITY_TIMINGS`・`WIN_FOLDER`・`POOL_FREE_FOLDER` など） | `form_aptitude_top3/workflow/prediction_timings.py` | `shared/workflow/form_aptitude_timings.py` | 今のモデルの1着のモデルを、時点ごとのフォルダから読む |
| 予測の流れの組み立て（時点に合わせて `DatasetBuilder`・材料を足す関数・モデルを選んで `PredictionWorkflow` を作るところ） | `form_aptitude_top3/command/predict_command.py`、道具「今週の予想」の `RaceForecaster._workflow()` | `shared/workflow/form_aptitude_prediction.py` の `FormAptitudePrediction`（材料を作る部品の決まりは `shared/workflow/form_aptitude_materials.py` の `FormAptitudeMaterials`） | 対象レースの、今のモデルの1着の確率を出す（`run(接続, レースID, 時点)` が全頭の表を返す） |
| 材料（P・S・T・U・V）を作る部品 `MaterialAttachers` | `form_aptitude_top3/command/material_attachers.py` | `src/yosou/form_aptitude_materials/material_attachers.py`（`shared` ではない） | `FormAptitudePrediction` に、接続から作る関数として渡す。予想「展開から着順を予想」（`yosou.race_development`）の保存したモデルと材料のパッケージ（`development_score`・`track_bias` など）を使うので、`shared` に置くと `shared` が予想のパッケージを参照することになる。そこで `shared` には決まり（`FormAptitudeMaterials`）だけを置き、守るクラスを材料の部品のパッケージに置いた |
| レースごとの時点の選び方（オッズ・馬番・馬体重・馬場状態の有無から木曜・前日・当日を選ぶ） | 道具「今週の予想」の `TimingChooser`・`TimingChoice` | `shared/workflow/timing_chooser.py`・`timing_choice.py` | 対象レースで、今のモデルのどの時点を使うかを選ぶ |
| 引数 `--development-root`（`DevelopmentRootArgument`。前日のモデルが使う、予想「展開から着順を予想」の置き場所） | `form_aptitude_top3/command/development_root_argument.py` | `shared/command/development_root_argument.py` | `predict` の引数 |

今のモデルのパッケージと道具「今週の予想」も、移したあとの `shared` を使う形に直した（今のモデルのパッケージは `command/` と `setting/` だけになった）。こうすると、道具「今週の予想」・発走前の通知とこの予想は、同じ部品・同じ学習済みモデルで1着の確率を出すので、値が食い違わない。

| まとまり | 共通にするか | この予想だけのもの |
|---|---|---|
| `repository/`（データの読み書き） | 共通（出走・過去走・調教・速報・締め切り前のオッズ・券種オッズ・今のモデルのファイル） | WIN5 の日と過去の WIN5 を読む SQL、配当の見積もりの式のファイル |
| `dataset/`・`feature/`・`ml_model/`・`setting/` | 全部共通（移したものを含む）。材料を作る部品は `yosou.form_aptitude_materials` | 無し（この予想はモデルを学ばないので、ハイパーパラメータの設定ファイルも持たない。[14-hyperparameter-settings.md](14-hyperparameter-settings.md)） |
| `workflow/`（流れを進める） | 今のモデルの予測の流れ（移した `FormAptitudePrediction` と `PredictionWorkflow`）と時点の選び方 | WIN5 の日の予測の流れ `Win5PredictionWorkflow` |
| `leg/`・`payout/`・`formation/`・`settlement/` | 無し | 下の「3.」 |
| `command/` | 部品は共通、入口は予想ごと | コマンドの組み立てと引数 |

| 決まり | 理由 |
|---|---|
| `shared` のクラスは、予想のパッケージを参照しない | 片方の予想の都合が、もう片方に入り込まない |
| 予想のパッケージどうしも参照しない（`form_aptitude_win5_tickets` から `form_aptitude_top3` を import しない）。材料を作る部品 `yosou.form_aptitude_materials` は予想のパッケージではないので、`command/` から使ってよい | 両方で使う部品は `shared` に置く。予想を直したときに、ほかの予想が壊れない |
| この予想は、今のモデルの学習済みモデルを読むだけで、書かない | 今のモデルの学び直しは、今のモデルのコマンド（`python -m yosou.form_aptitude_top3 train`）が受け持つ |
| 1着の確率をレースの中でそろえるのは、今のモデルが2つのモデルの確率を平均したあとにする | 平均する前にそろえると、LightGBM と CatBoost のどちらかの確率の大きさの癖が、平均に残るため |
| 配当の見積もりと買い目の組み方は、確率の出どころを知らない | 今のモデルの確率でも、オッズから見た勝率でも、同じ部品で組の期待値を出せる。過去の WIN5 での確かめで、区切りごとの予測を渡すのにも使える（[16-evaluation.md の 1.](16-evaluation.md#1-期間の分け方)） |

## 2. パッケージ構成

予想方法のコードは `src/yosou/` の下に置く（keiba-yosou の決まり）。この予想のパッケージ名は、フォルダ名「近走と適性からWIN5の買い目を決める」（[15-decisions.md の 6](15-decisions.md#6-フォルダ名)）に合わせて `form_aptitude_win5_tickets`（form = 近走、aptitude = 適性、win5_tickets = WIN5 の買い目）とする。

```text
src/yosou/form_aptitude_win5_tickets/       近走と適性からWIN5の買い目を決める
├── __main__.py                     コマンドの入口（command/ を呼ぶだけ）
├── command/                        コマンド（fit-payout・predict）の引数と、配当の見積もりの式を作る段
├── workflow/                       WIN5 の日の予測の流れ（ほかを順に呼ぶだけ）
├── leg/                            対象レース1つ: 使う確率を選ぶ・今のモデルの1着の確率を出す・レースの中でそろえる
├── payout/                         配当の見積もり: 発売票数の見積もり・式の材料・式・上限と自分の1票
├── formation/                      買い目: 馬の並べ方・フォーメーション・日の期待値・組み方の探索・買う日の判断
├── settlement/                     過去の WIN5 での精算: 当たり・返還・払戻、比べる相手の買い目
├── repository/                     WIN5 の日・過去の WIN5 を読む SQL、配当の見積もりの式のファイル
└── tests/                          テスト。合成DB だけを使う（keiba-yosou の決まり）
```

各フォルダには `__init__.py` を置き、その先頭に「クラス → 仕事」の表を書く。ファイルの名前は、クラスの名前を小文字と `_` にしたもの（`FormationSearch` → `formation_search.py`）。この予想が作るものは、配当の見積もりの式のファイル `payout_estimator.json` と、実際に予想した結果の記録（`記録/<開催日>.json`）で、どちらも Git の対象外の `reports/近走と適性からWIN5の買い目を決める/` に置く。

| 決まり | 理由 |
|---|---|
| 参照の向きは一方向にする: `form_aptitude_win5_tickets` → `form_aptitude_materials`（`command/` だけ）→ `shared`。`shared` から予想のパッケージと `form_aptitude_materials` を参照しない | 参照が循環すると、1つを直すと全部に響く |
| 予想のパッケージの中も一方向にする: `command` → `workflow` → `leg`・`formation`、`formation` → `payout`。`settlement` は `formation` と `payout` を使う。`repository` は `workflow`・`command`・`leg`（障害の対象レースの出走馬を読む `LegRunnerRepository`）から使う。`payout`・`settlement` は、過去の WIN5 の表の列の名前（`repository/win5_columns.py`）だけを参照する | 手本と同じ決まり。`leg` と列の名前は、作りながら足した |
| 各フォルダの `__init__.py` で外に出すのは、ほかのフォルダから使うクラスだけにする | 外に見せるものが少ないほど、中を変えても外に響かない |
| この構成は、作りながら動かしてよい | 作る前に決めた構成は、少ない情報で決めたものだからである |

## 3. この予想だけのクラスの一覧

### workflow/ — 流れを進める

| 名前 | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `Win5PredictionWorkflow` | WIN5 の日の予測の流れを進める。その日の WIN5 を読み、対象レースごとに使う確率を選んで今のモデルの1着の確率を出してそろえ、発売票数を見積もり、買い目を組み（予算の候補ごとにも）、買うかどうかを決める。元DB への接続・`LegWinPredictor`・`FormationSearch` はコマンドが作って渡す | `run(開催日, 予算, 買う日の線)` | `Win5DayRepository`、`LegModelChooser`、`LegWinPredictor`、`RaceWinShare`、`Win5HistoryRepository`、`PoolSizeEstimate`、`FormationSearch`、`DayBuyJudge` |
| `Win5Forecast` | WIN5 の日の予測の結果を表す値（日・対象レースごとの予測・払戻に回るお金の見込み・並べ方・予算・線・選んだ買い目・予算の候補ごとの買い目・判断）。記録の形（辞書）にもする | `to_dict()` | ― |
| `LegForecast` | 対象レース1つの予測の結果を表す値（レースID・使った確率と理由・全頭の確率の表） | `to_dict(買い目の馬番)` | ― |

`Win5PredictionWorkflow` は、ほかのクラスを呼んで受け渡すだけで、計算・判断・SQL は書かない。

### leg/ — 対象レース1つの1着の確率

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `LegModel` | 対象レースで使う確率を表す値（列挙。今のモデルの当日・今のモデルの前日・オッズだけ） | ―（値） | ― |
| `LegModelChoice` | 選んだ確率（`LegModel`）と、選んだ理由の文と、使ったオッズの断面（締め切り前の単勝オッズの発表月日時分。記録に残す） | ―（値） | ― |
| `LegModelChooser` | 対象レースが障害なら「オッズだけ」。平地なら、`shared` に移した時点の選び方で今のモデルの時点を選び、木曜（オッズが無い）なら止める（[06-flowchart.md の図1](06-flowchart.md#図1-対象レースで使う確率の選び方)）。`LegModelChoice` を返す | `choose(接続, レースID)` | 移した `TimingChooser`（材料の有無は `共通.race_signals` の `RaceSignalReader` で1回だけ読む） |
| `LegWinPredictor` | 選んだ時点で、対象レースの全頭の今のモデルの1着の確率（2つのモデルの平均）を出す。当日に券種のオッズが無いときに券種オッズなしのモデルに切り替えるのは、今のモデルの流れの中で行われる。「オッズだけ」のときは、オッズから見た勝率をそのまま確率にする。`FormAptitudePrediction` は `command/` が作って渡す（材料を作る部品 `MaterialAttachers` を、接続から作る関数として渡す） | `predict(接続, レースID, LegModelChoice)` | 移した `FormAptitudePrediction`、共通の `MarketWinProbability`、`LegRunnerRepository`（オッズだけのとき） |
| `RaceWinShare` | 1レースの全頭の1着の確率を、合計が 1 になるようにそろえ、オッズから見た勝率と上乗せの列を足す | `of(1レースの予測の結果)` | 共通の `MarketWinProbability` |

### payout/ — 配当の見積もり

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `PoolSizeEstimate` | その日の発売票数を、それより前の WIN5 の発売票数から見積もる（[09-features.md の 2.](09-features.md#2-配当の見積もりに使う値)）。同じ曜日の種類の回が無ければ、曜日を問わず直近 10回 | `of(過去の WIN5, 開催日, 土曜か)` | ― |
| `PayoutPool` | その日の払戻に回るお金の見込みを表す値（発売票数の見積もりとキャリーオーバー。払戻に回るお金 = 発売票数の見積もり × 100円 × 払戻率 + キャリーオーバー） | ―（値） | ― |
| `ComboMarketProbability` | 過去の当たり組の5頭の確定単勝オッズと、各対象レースの全頭の単勝オッズの逆数の合計から、市場の組の確率を出す（`MarketWinProbability` と同じ決まり） | `of_winners(当たり組のオッズ, 逆数の合計)` | ― |
| `PayoutFeatures` | 組の材料（市場の組の確率の逆数の対数、キャリーオーバーの比の対数）を作る | `of(市場の組の確率, キャリーオーバー, 発売票数の見積もり)` | ― |
| `PayoutEstimator` | 配当の見積もりの式。過去の当たり組で傾きと切片と戻すときの補正を決め（`fit`。新しい式を返す）、組の材料から式の値を出す（`estimate`）（[10-target.md の 2.](10-target.md#2-配当の見積もりで当てるもの)） | `fit(材料, 払戻)`、`estimate(材料)`、`to_dict()`、`from_dict(値)` | scikit-learn の `LinearRegression` |
| `PayoutCeiling` | 式の値に、払戻の上限と自分の1票の分を当てて、見積もりの配当にする（[06-flowchart.md の図2](06-flowchart.md#図2-組1つの配当の見積もり)） | `apply(式の値, 払戻に回るお金)` | ― |
| `PayoutTrainingRows` | 過去の WIN5 の表から、式を作るのに使う当たり組の行（開催日・材料・払戻）を作る。的中無の回と、前の回が無く発売票数を見積もれない回は入れない。`fit-payout` と道具「印の成績」の `--win5`（区切りごと）が使う | `of(過去の WIN5)` | `PoolSizeEstimate`、`ComboMarketProbability`、`PayoutFeatures` |

### formation/ — 買い目

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `LegOrdering` | 対象レースの馬を、買い目に入れる順に並べる決まり（列挙。上乗せの順・1着の確率の順。[15-decisions.md の 5](15-decisions.md#5-買い目の組み方と予算の決め方)） | `order(1レースの確率の表)` | ― |
| `Formation` | フォーメーションを表す値。レースごとに選んだ馬番の並びと、点数（頭数のかけ算） | `points`、`combos()`、`contains(組)` | ― |
| `ComboGrid` | フォーメーションの全部の組の、当たる確率と見積もりの配当を表す値（各レースの馬の並びの位置の5次元の並び） | ―（値） | ― |
| `FormationChoice` | 組んだフォーメーションと、買い目のどれかが当たる確率・見積もりの払戻の合計・日の期待値を表す値 | `expected_value`、`to_dict()` | ― |
| `FormationValue` | フォーメーションの全部の組について、当たる確率と見積もりの配当を表の計算でまとめて出し（`grid`）、買い目のどれかが当たる確率と日の期待値を返す（`of`） | `grid(5レースの確率の表, PayoutPool)`、`of(Formation, 5レースの確率の表, PayoutPool)` | `PayoutFeatures`、`PayoutEstimator`、`PayoutCeiling` |
| `FormationSearch` | 予算に収まる頭数の並び（各レース何頭か）を全部試し、各レースは `LegOrdering` の順に上から選んで、見積もりの払戻の合計がいちばん大きいフォーメーションを選ぶ（[06-flowchart.md の図3](06-flowchart.md#図3-買い目の組み方と買う日の判断)） | `best(5レースの確率の表, 予算, PayoutPool)`、`best_by_budget(5レースの確率の表, 予算の候補, PayoutPool)` | `LegOrdering`、`Formation`、`FormationValue` |
| `DayDecision` | 買う か 見送り（列挙） | ―（値） | ― |
| `DayBuyJudge` | 日の期待値が買う日の線以上なら「買う」、未満なら「見送り」 | `judge(日の期待値, 線)` | ― |

`FormationSearch` は、予算の候補の上限まで各レースの上位の馬を並べた全部の組の値（`ComboGrid`）を1回だけ出し、5つの向きに累積の和をとって、どの頭数の並びの合計も引くだけで分かるようにする（[06-flowchart.md の図3](06-flowchart.md#図3-買い目の組み方と買う日の判断) の「計算を使い回す」）。試す予算・線・並べ方の候補と `predict` の既定は `formation/buying_defaults.py` に置く。既定は、道具「印の成績」の `--win5` で探索期間から選んだ1着の確率の順・240点・線 1.50 である（[16-evaluation.md の「確かめた結果」](16-evaluation.md#確かめた結果)）。

### settlement/ — 過去の WIN5 での精算（[16-evaluation.md](16-evaluation.md) の確かめに使う）

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `Win5Outcome` | 過去の WIN5 の1回の結果を表す値（当たり組と100円あたりの払戻・的中無の印・対象レースごとの取消と除外の馬番・発売票数・キャリーオーバー） | ―（値） | ― |
| `Win5Outcomes` | `Win5HistoryRepository` と `Win5ScratchRepository` の表から、開催日ごとの `Win5Outcome` を作る | `of(過去の WIN5, 取消と除外)` | ― |
| `Win5Settlement` | 過去の WIN5 の1回について、買い目が当たったか、返還があったかを元DB の当たり組と照らし、払戻（返還の代金を含む）を出す。取消・除外の馬を含む組は代金が戻る。的中無の回に当たり組を買っていたら、払戻に回るお金（その回の発売票数 × 100円 × 払戻率 + キャリーオーバー）を自分の1票で受け取る（上限で頭打ち）。組を1つずつ並べずに数える | `settle(Formation, Win5Outcome)` | `PayoutPool` |
| `Win5Settled` | 1回の精算の結果を表す値（点数・代金・払戻・当たり・返還の点数） | ―（値） | ― |
| `RuleFormations` | 比べる相手 (1)。ルール集の WIN5 のルール（1レースだけ穴馬3頭・残り上位人気2頭の 48点 × 5セット = 240点）の買い目を、オッズの順の人気から作る | `of(5レースの人気)` | `Formation` |
| `PopularityFormation` | 比べる相手 (2)。各レースの人気の上位から、予算に収まるいちばん大きいフォーメーション（各レースの頭数をなるべくそろえる）を作る | `of(5レースの人気, 予算)` | `Formation` |
| `Win5BacktestTables` | 買い方ごと・期間ごと（と年ごと）の、買った日数・投資・払戻・回収率・的中率・開催日を単位にした 90% の幅を表にする | `tables(精算の結果)` | 共通の `BootstrapInterval` |

### repository/ — この予想だけの読み書き

| クラス | 読む・書くもの | 主な public メソッド |
|---|---|---|
| `Win5Day` | WIN5 の日を表す値。開催日、対象レース5つのレースID（発売の順）、キャリーオーバー金額初期、土曜か日曜・祝日か（手本の `TargetScope` と同じく、リポジトリが返す値なので `repository/` に置く） | ―（値） |
| `Win5DayRepository` | 元DB の `wf` と子表 `wf__重勝式対象レース情報` から、1つの開催日の WIN5（対象レース5つ・キャリーオーバー金額初期）を読み、`Win5Day` にする（SQL 1本） | `read(開催日)` |
| `Win5HistoryRepository` | 元DB の `wf`・`wf__重勝式対象レース情報`・`wf__重勝式払戻情報` と `se` から、ある日より前の WIN5 の回ごとに、対象レース・当たり組・払戻・発売票数・キャリーオーバー・返還と的中無の印・当たり組の5頭の確定単勝オッズと、各対象レースの全頭の単勝オッズの逆数の合計を読む（SQL 1本。中止の回は読まない。事実表は作らないので速い） | `read(この日より前)` |
| `Win5ScratchRepository` | ある日より前の WIN5 の対象レースで、出走取消・発走除外・競走除外になった馬の馬番を読む（SQL 1本。精算の返還に使う） | `read(この日より前)` |
| `Win5LegRunnerHistoryRepository` | ある日より前の WIN5（成績の版）の対象レースの出走馬（取消・除外を除く）の馬番・確定単勝オッズと、レースの発走時刻・障害か（`ra`・`se` のいちばん新しい行。SQL 1本）。道具「印の成績」の `--win5` が、区切りごとの予測と合わせて対象レースの確率の表を作り、発走の間隔で馬体重が出ていたかをまねるのに使う | `read(この日より前)` |
| `LegRunnerRepository` | 1レースの出走馬（取消・除外を除く）の馬番・馬名と、出走の行の単勝オッズを読む（SQL 1本。障害の対象レースを「オッズだけ」で予想するのに使う） | `read(レースID)` |
| `Win5ForecastRecordRepository` | 実際に予想した結果（日のまとめ・買い目・対象レースごとの確率と、使ったオッズの断面）を `記録/<開催日>.json` に書く・読む（SQL は持たない）。確定オッズで確かめた成績と、実際に予想した成績を同じ表で比べるため（[15-decisions.md の 7](15-decisions.md#7-締め切り時点のオッズと確定オッズの差の扱い)）。同じ日に予想し直したら上書きする | `save(Win5Forecast.to_dict() の辞書, 開催日)`、`load(開催日)` |
| `PayoutEstimatorRepository` | 配当の見積もりの式（傾き・切片・戻すときの補正・使った期間）を `payout_estimator.json` に書く・読む（SQL は持たない） | `save(PayoutEstimator.to_dict() の辞書, 使った期間)`、`load()` |

### command/ — コマンド

| クラス | 置き場所 | 仕事 | 主な public メソッド |
|---|---|---|---|
| `CommandLine` | この予想 | 入口。引数を読み、サブコマンドを実行し、結果の表を出す | `run(引数)` |
| `FitPayoutCommand` | この予想 | `fit-payout`: 配当の見積もりの式を作る。`--before` の日より前の WIN5 の当たり組で `PayoutEstimator` を作り、`PayoutEstimatorRepository` で保存する。式の傾き・切片・外れの散らばり・使った回数の表を返す | `run(引数)` |
| `PredictCommand` | この予想 | `predict`: WIN5 の日を予測する。`--budget`・`--min-value`・`--ordering` を受け取り、保存した式を読んで `Win5PredictionWorkflow` に渡す。結果は `Win5ForecastRecordRepository` で自動で記録する | `run(引数)` |
| `FormModelsArgument` | この予想 | `predict` の引数 `--form-models`（今のモデルの学習済みモデルの置き場所） | `add_to(parser)` |
| `Win5ForecastTables` | この予想 | 予測の結果を、日のまとめ・選んだ買い目・対象レースごとの全頭の表・予算の候補ごとの表にする（下の「4.」） | `tables()` |
| `CommonArguments` | `shared` | 共通の引数（`--db` `--format` `--out`。`--models` はこの予想では式と記録の置き場所で、下のフォルダを持たない既定（`models_folder=""`）で使う） | `add_to(parser)` |
| `FigureCacheArgument` | `shared` | 今のモデルの予測に要る引数 `--figure-cache`（今のモデルのコマンドと同じ） | `add_to(parser)` |
| `DevelopmentRootArgument` | `shared` | 今のモデルの予測に要る引数 `--development-root`（前日のモデルが使う、予想「展開から着順を予想」の置き場所。今のモデルのコマンドと同じ） | `add_to(parser)` |

過去の WIN5 での確かめの入口は、この予想のコマンドではなく、道具「印の成績」に足す（`--win5`。[16-evaluation.md の 7.](16-evaluation.md#7-道具と全券種の回収率)）。道具は、この予想の `settlement/`・`formation/`・`payout/`・`repository/` の部品を呼ぶだけにする（同じ精算を2か所に書かない）。道具の側にあるのは、確かめの流れ（`win5_stats.py`）と、時点のまね方・区切りごとの予測の読み込み・買い方の選び方・採用の判定・表（`tools/印の成績/win5_*.py`）だけである。

## 4. コマンドの引数

コマンドは `uv run python -m yosou.form_aptitude_win5_tickets <fit-payout か predict> …` で動かす。共通の引数（`--db`・`--format`・`--out`）と引数の決まりは、[手本の 04 の「コマンドの引数」](../近走と適性から3着以内を予想/04-classes.md#コマンドの引数) と同じである。

| コマンド | 引数・出力 | この予想では |
|---|---|---|
| 共通 | `--models` の既定 | `reports/近走と適性からWIN5の買い目を決める`。配当の見積もりの式 `payout_estimator.json` を置く |
| 共通 | `--form-models` | 今のモデルの学習済みモデルの置き場所。既定は `reports/近走と適性から3着以内を予想/models`（今のモデルのコマンドの既定と同じ） |
| `fit-payout` | `--before 日` | この日より前の WIN5 で式を作る。既定は今日 |
| `fit-payout` | 出す表 | 配当の見積もりの式の表（傾き・切片・外れの散らばり・使った回数） |
| `predict` | `--date` | WIN5 の開催日（省略すると今日） |
| `predict` | `--budget 点数` | 1回の予算（点数）。省略すると、[16-evaluation.md の 4.](16-evaluation.md#4-買い目の組み方と買う日の線) で選んだ値 |
| `predict` | `--min-value 期待値` | 買う日の線。省略すると、[16-evaluation.md の 4.](16-evaluation.md#4-買い目の組み方と買う日の線) で選んだ値 |
| `predict` | `--ordering 並べ方` | 各レースの馬を選ぶ順（上乗せの順・1着の確率の順）。省略すると、[16-evaluation.md の 4.](16-evaluation.md#4-買い目の組み方と買う日の線) で選んだ値。既定（予算・線も）は `formation/buying_defaults.py` に置く |
| `predict` | `--figure-cache`・`--development-root` | 今のモデルの予測に要る置き場所。意味と既定は今のモデルのコマンドと同じ |
| `predict` | `--odds`・`--timing` | 受け取らない。対象レースが5つあり、オッズは元DB の締め切り前のオッズを、時点はレースごとに選ぶ（[07-prediction-timing.md](07-prediction-timing.md#対象レースごとの確率の選び方)） |
| `predict` | 出す表 | (1) 日のまとめ（キャリーオーバー・発売票数の見積もり・点数・金額・買い目のどれかが当たる確率・日の期待値・買う／見送り）、(2) 選んだ買い目（レースごとの馬番）、(3) 対象レースごとの全頭の表（馬番・馬名・使った時点・そろえた1着の確率・オッズから見た勝率・上乗せ・買い目に入れたか）、(4) 予算の候補ごとの、いちばん良い買い目の当たる確率と日の期待値 |
| `predict` | 止まるとき | その日の WIN5 が元DB に無い（jvdata-store で速報の WIN5 を取り込む案内を出す）、対象レースのどれかに締め切り前のオッズが無い（速報のオッズを取り込む案内を出す）、配当の見積もりの式が無い（`fit-payout` を案内する）、今のモデルの学習済みモデルが無い（今のモデルの `train` を案内する） |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-11-08 |
| 更新 | 2026-11-08: 15 の 3〜12 が決まり、パッケージ名をフォルダ名に合わせ、実際の予想の記録（15 の 7）を足した |
| 更新 | 2026-11-08: 15 の 1 が決まり、1着のモデルを学ぶクラスを外し、今のモデルの1着の確率を受け取る形にした |
| 更新 | 2026-11-08: パッケージを作り、作りながら足したクラス（値を表すクラス・`LegRunnerRepository`・`Win5ScratchRepository`・`PayoutTrainingRows`・`FormModelsArgument` など）と引数 `--ordering` を表に入れた。`Win5HistoryRepository` は事実表でなく `se` から読む形にした |
| 更新 | 2026-11-08: 「1.」の部品を移した。材料を作る部品 `MaterialAttachers` は、予想「展開から着順を予想」を使うので `shared` でなく `yosou.form_aptitude_materials` に置き、`shared` には決まり `FormAptitudeMaterials` を置いた。`--development-root` の引数を表に入れた |
| 更新 | 2026-11-08: 道具「印の成績」の `--win5` を作り、`Win5LegRunnerHistoryRepository` と道具の側の分担を書いた。`predict` の既定を、探索期間で選んだ買い方にした |
