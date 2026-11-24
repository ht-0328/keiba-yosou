# 04 クラスとパッケージの設計

**この文書で決めること:** 「1行 = 1つの組」「券種ごとのモデル」「当日だけの予測」を、ほかの予想と共有の部品（`src/yosou/shared/`）の上にどう載せるか。この予想だけに要るクラスは何か。どのクラスが流れを進めるか。それらをどのフォルダ（パッケージ）・ファイルに置くか。コマンドの引数と、この予想を使う道具に見せる入口は何か。

**結論: 市場の確率を作る・モデルを学習して保存する・設定を読む・元DB を読む、のクラスは共有のものをそのまま使い、共有の部品は変えない。この予想だけに作るのは、組の表を作るクラス（`dataset/`・`feature/`）、ファイルを読み書きするクラス（`repository/`）、買い目の決まり（`betting/`）、当たり具合を測るクラス（`evaluation/`）、流れを進めるクラス（`workflow/`）、コマンド（`command/`）である。流れを進めるのは、組の表づくりの `TableWorkflow`、年ごとの学習と予測の `WalkForwardWorkflow`、本番のモデルの学習の `ProductionTraining`、1レースの予測の `HighPayoutPredictor` の4つで、どれもほかのクラスを順に呼んで受け渡すだけである。組の表を作る入口 `ComboTableBuilder` は、学習用の表づくりと本番の予測の両方が使う。**

- 1ファイル1クラス、1クラス1つの仕事、1 SQL につき1つのリポジトリ、という分け方の決まりは手本と同じで、[手本の 04 の「分け方の決まり」](../近走と適性から3着以内を予想/04-classes.md#分け方の決まり) を参照。
- 共有のクラスの一覧は [手本の 04 の「クラスの一覧」](../近走と適性から3着以内を予想/04-classes.md#クラスの一覧) を参照。この文書には、この予想での使い方と、この予想だけのクラスを書く。
- 用語の意味（public メソッド・オーケストレーション・リポジトリ）は [手本の 02 の「機械学習の用語」](../近走と適性から3着以内を予想/02-glossary.md#機械学習の用語) を、組・オッズの帯・市場の確率は [02-glossary.md](02-glossary.md) を参照。
- クラスどうしが、どの順にどのメソッドを呼ぶかは [05-sequence.md](05-sequence.md) を参照。

## 1. ほかの予想と共有の部品の使い方

| 使うもの | どこにあるか | この予想での使い方 |
|---|---|---|
| `HorseStrength`・`TrifectaSources`・`PoolFolding`・`ComboBlendFeatures` | `src/yosou/shared/combo_value/` | `MarketTableBuilder` が呼び、券種ごとの市場の表（市場の確率 q と、3連単から足し合わせた確率 t）を作る。組の期待値の買い目と同じ部品なので、市場の確率の定義が2か所に分かれない |
| `LightGbmModel`・`CatBoostModel`・`EnsembleModel`・`MEMBER_TYPES` | `src/yosou/shared/ml_model/` | `TicketModelTrainer` が学習に、`TablePrediction` が予測と平均に使う。出発点と行の重みを渡す仕組みは、共有のクラスにすでにある（[12-lightgbm.md](12-lightgbm.md#1-学習データの渡し方)・[13-catboost.md](13-catboost.md#1-学習データの渡し方)） |
| `TrainingData`・`PredictionData`・`BaselineLogit` | `src/yosou/shared/dataset/` | `ModelDataFactory` が、組の表をこの形に詰め替える（特徴量・目的変数・出発点・行の重み） |
| `FeatureCatalog`・`Feature` | `src/yosou/shared/feature/` | 券種ごとの特徴量の一覧（`CATALOGS`）の形 |
| `HyperparameterSettings` | `src/yosou/shared/setting/` | 設定ファイルを読む（[14-hyperparameter-settings.md](14-hyperparameter-settings.md)） |
| `ModelRepository` | `src/yosou/shared/repository/` | `TicketModelRepository` が、券種ごとのフォルダで使う（[12-lightgbm.md の 6](12-lightgbm.md#6-保存)） |
| `FinalOddsRepository`・`PayoutRepository`・`RaceDayRange` | `src/yosou/shared/repository/` | `FinalMarketLoader` が、月ごとの確定オッズの板と払戻を読む。この予想だけの SQL は無い |
| `AnnouncedTicketOddsRepository` | `src/yosou/shared/repository/` | 本番で、道具の側（今週の予想の `RaceBoards`）が締め切り前の板を読んで、この予想に渡す |
| `TicketType` | `src/yosou/shared/betting/` | 券種と、その英名・組の頭数・着順を区別するか |
| `CommonArguments` | `src/yosou/shared/command/` | コマンドに共通の引数（下の 4） |
| `PlaceMarketRate` | `src/yosou/longshots_in_top3/feature/` | 複勝オッズから見た3着以内率（`pm`）を出す |

**共有の部品に足したもの・変えたものは無い。**

## 2. この予想だけのクラス

### workflow/ — 流れを進める

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `TableWorkflow` | 過去のレースの組の表を、月ごとに作って、年ごと・券種ごとのファイルに書く。元DB は、月ごとに読む間だけ開く。結果は `TableYearResult` | `run(最初の開催日, 最後の開催日)` | `FinalMarketLoader`・`ComboTableBuilder`・`HitLabeler`・`ComboTableRepository` |
| `WalkForwardWorkflow` | テストの年ごとに、2年前までで学び、1年前で早期終了し、その年の対象の組を全部予測して保存する（確かめ用）。予測の済んでいる年は飛ばす。結果は `WalkYearResult` | `run(券種, 始める年)` | `YearSamples`・`TicketModelTrainer`・`TablePrediction`・`PredictionStore` |
| `ProductionTraining` | 本番のモデルを券種ごとに学習して保存し、検証の期間での当たり具合を返す。結果は `ProductionTrainingResult` | `run(券種)` | `YearSamples`・`TicketModelTrainer`・`TicketModelRepository`・`MarketComparison` |
| `HighPayoutPredictor` | 本番の予測の入口。1レースの馬ごとの表と5券種の板から、対象の組の当たる確率と期待値を出す | `load(モデルの置き場所)`・`predict(馬ごとの表, 板)` | `ComboTableBuilder`・`TablePrediction`・`TicketModelRepository` |
| `YearSamples` | 保存した組の表を年ごとに読み、学習の行（外れを間引いて重みつき）にする | `of(券種, 年)`・`by_year(券種)` | `ComboTableRepository`・`MissSampling` |
| `TicketModelTrainer` | 1つの券種の LightGBM と CatBoost を、学習の行と検証の行から学習する | `fit(学習の行, 検証の行)` | `ModelDataFactory`・共有の `LightGbmModel`・`CatBoostModel` |
| `TablePrediction` | 組の表の全部の行に、当たる確率（2つの平均と、モデルごと）を付ける。行が多いので区切って予測する | `probabilities(組の表)` | `ModelDataFactory`・共有の `EnsembleModel` |

### dataset/ — 組の表を作る

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `PayoutBand` | 1つの券種の帯（学ぶ下限・高配当の線・上限）。不変の値 | `is_learnable(オッズ)`・`is_high_payout(オッズ)` | ― |
| `ComboTableBuilder` | 入口。馬ごとの表と5券種の板から、券種ごとの組の表（ID・オッズ・出発点・特徴量）を作る。板の出どころは問わない。板が足りない券種は作らない | `build(馬ごとの表, 板, 券種)` | `MarketTableBuilder`・`HorseMaterials`・`TrifectaPoolWin`・`RaceMaterials`・`TicketTableAssembler` |
| `MarketTableBuilder` | 5券種の板から、券種ごとの市場の表（1行 = 1組。市場の確率 q・t）を作る | `build(馬ごとの表, 板)` | 共有の `combo_value` のクラス |
| `TrifectaPoolWin` | 3連単の板から見た、馬ごとの勝率を出す | `of(3連単の板)` | ― |
| `HorseMaterials` | 馬ごとの表から、馬ごとの材料（組の位置ごとに付ける 20個と、Harville の式に使う2個）を作る | `of(馬ごとの表, 3連単から見た勝率)` | `PlaceMarketRate` |
| `RaceMaterials` | 馬ごとの材料から、レースごとの表（頭数・1番人気の値など）を作る | `of(馬ごとの材料)` | ― |
| `ComboMemberLookup` | 組の各位置の馬の材料を、馬ごとの材料の表から引く | `slots(行, 頭数)`・`members(位置, 着順を区別するか)` | `ComboMembers` |
| `TicketTableAssembler` | 1つの券種の対象の行を選び、特徴量のまとまり（A〜F）を順に付け、出発点を付けて組の表にする | `table(帯)` | `feature/` の各クラス・`ComboMemberLookup` |
| `FinalMarketLoader` | 期間ぶんの確定オッズの板（5券種）と払戻を、共有のリポジトリで読む。結果は `FinalMarket` | `load(開催日の範囲, レースID, 払戻を読む券種)` | 共有の `FinalOddsRepository`・`PayoutRepository` |
| `HitLabeler` | 組の表に、開催日と、当たったか・払戻を付ける | `label(券種, 組の表, 払戻, 開催日)` | ― |
| `MissSampling` | 学習の行を選ぶ（当たりは全部、外れは間引いて重みを付ける） | `sample(券種, 組の表, 年)` | ― |
| `ModelDataFactory` | 組の表を、共有の `TrainingData`・`PredictionData` に詰め替える | `training(組の表)`・`prediction(組の表)` | ― |

5券種の既定の帯（`DEFAULT_BANDS`）と期待値の線の既定（`DEFAULT_VALUE_LINE`）は `default_bands.py`、外れの組を残す割合（`MISS_KEEP_RATES`）と乱数の種のもとは `miss_keep_rates.py`、列の名前と並びは `column_names.py`・`table_columns.py`（どれも定数か関数だけ）。

### feature/ — 特徴量を作る

特徴量のまとまりごとに1クラス。どのクラスも、行の並びを変えずに、特徴量の列だけを返す。特徴量の定義は [09-features.md](09-features.md) を参照。

| クラス | 仕事 |
|---|---|
| `OwnMarketFeatures` | A. その券種の市場（オッズ・市場の確率・3連単から足し合わせた確率・その差） |
| `CrossMarketFeatures` | B. ほかの券種の市場。要る板の一覧は `REQUIRED_MARKETS` |
| `HarvilleFeatures` | C. Harville の式で出した組の確率（予想の1着の確率からと、単勝の市場から） |
| `HarvilleProbability`・`WidePairProbability` | Harville の式そのもの（着順どおり・並びを問わない）と、ワイドの「2頭とも3着以内」の確率 |
| `PositionHorseFeatures` | D. 組の位置ごとの馬の材料 |
| `ComboSummaryFeatures` | E. 組のまとめ |
| `RaceFeatures`・`RegionFeatures` | F. レースの材料と、そのレースの学ぶ帯の大きさ |
| `ComboMembers` | 組の馬ごとの材料（行 × 組の位置 × 材料）と、特徴量にするときの馬の並び（順不同の券種は人気順） |

券種ごとの特徴量の一覧は `feature_catalog.py` の `CATALOGS`、馬ごとの材料の名前は `material_names.py`、穴馬の線（6番人気以下・差 0.05 以上）は `longshot_rule.py`。

### repository/ — ファイルの読み書き

この予想だけの SQL は無い。どれも、Git の対象外の `reports/高配当の組が当たるかを予想/` の下のファイルを読み書きする。

| クラス | 読む・書くもの |
|---|---|
| `HorseTableRepository` | 馬ごとの表（`horses/*.parquet`。読むだけ。同じ出走が2つのファイルにあれば誤りにする） |
| `ComboTableRepository`・`ComboTableWriter` | 券種ごと・年ごとの組の表（`tables/<券種の英名>_<年>.parquet`）。書き手は、月ごとの表を順に足して書く |
| `PredictionStore` | 年ごとの予測（`predictions/<券種の英名>_<年>.parquet`。`walk` の出力） |
| `TicketModelRepository` | 券種ごとの学習済みモデルと設定（`models/<券種の英名>/race_day/`） |

### betting/ — 買い目の決まり

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `HighPayoutRule` | 確率の付いた組の表から、買う組を選ぶ（オッズが高配当の線以上・上限未満で、期待値が線以上。上限の点数があれば、1レース・1券種につき確率の高い順）。金額は持たない | `pick(確率の付いた組の表)` |

判断の手順は [06-flowchart.md の図3](06-flowchart.md#図3-買い目の選び方) を参照。

### evaluation/ — 当たり具合を測る

| クラス・関数 | 仕事 |
|---|---|
| `MarketComparison` | 検証の行での対数損失を、モデルごと・2つの平均・市場の確率・当たりの数に合わせた市場の確率で出す（[16-evaluation.md の 3](16-evaluation.md#3-比べる基準)） |
| `YearlyPickSummary` | 年ごとの予測から、買い目の決まりで選んだ組を全部 100円ずつ買ったときの、年ごとの点数・的中数・買ったレースの数・回収率を数える |
| `weighted_log_loss()` | 行の重みを付けた対数損失（関数） |

### command/ と setting/

| 名前 | 仕事 |
|---|---|
| `CommandLine` | 入口。引数を読み、サブコマンドを実行し、結果の表を出す |
| `TablesCommand`・`WalkCommand`・`TrainCommand` | サブコマンド `tables`・`walk`・`train`（下の 4） |
| `yosou_name.py` の `YOSOU_NAME` | この予想の名前（出力の既定の置き場所 `reports/高配当の組が当たるかを予想/` に使う） |
| `setting/default_settings.toml` | ハイパーパラメータの初期値（[14-hyperparameter-settings.md](14-hyperparameter-settings.md)） |

## 3. パッケージ構成

```text
src/yosou/high_payout_combos/
├── __init__.py            # この予想の説明と、外に出すもの（下の 5）
├── __main__.py            # python -m yosou.high_payout_combos の入口
├── command/               # CommandLine・TablesCommand・WalkCommand・TrainCommand・yosou_name.py
├── workflow/              # TableWorkflow・WalkForwardWorkflow・ProductionTraining・HighPayoutPredictor ほか
├── betting/               # HighPayoutRule
├── evaluation/            # MarketComparison・YearlyPickSummary・log_loss.py
├── dataset/               # PayoutBand・ComboTableBuilder・MarketTableBuilder・MissSampling・ModelDataFactory ほか
├── feature/               # まとまりごとの特徴量のクラス・feature_catalog.py
├── repository/            # HorseTableRepository・ComboTableRepository・PredictionStore・TicketModelRepository
├── setting/               # default_settings.toml
└── tests/                 # 合成のデータだけのテスト
```

| 決まり | 理由 |
|---|---|
| 仕事の領域でフォルダを分ける。1ファイルに1クラス、1クラスに1つの仕事 | ほかの予想と同じ（[手本の 04 の「分け方の決まり」](../近走と適性から3着以内を予想/04-classes.md#分け方の決まり)） |
| 参照の向きは `command` → `workflow` → `evaluation` → `betting` → `dataset` → `feature` の一方向。`repository` はファイルの読み書きだけで、`command`・`workflow`・`dataset` から使う | 下のものが上のものを知らないようにし、部品を取り替えやすくする |
| 組の表を作る入口は `ComboTableBuilder` の1つにし、板と馬ごとの表を引数で受け取る | 学習（確定オッズの板）と本番（締め切り前の板）で、同じクラスが特徴量を作る（[11-leak-prevention.md](11-leak-prevention.md#決まり) の 4） |
| 帯・期待値の線・外れの組を残す割合は、定数のファイルの1か所に置く | 学習・確かめ・本番・道具が、同じ値を使う |
| 馬ごとの表を作る仕事は、このパッケージに置かない（道具「高配当の買い目」が作る） | 印付けは、今週の予想と道具「印の成績」の部品（`tools/` の下）を順に呼んで行うので、道具の側に置く。予想のパッケージは、できた表を読むだけにする |
| モデル・組の表・予測の置き場所は `reports/高配当の組が当たるかを予想/`（Git の対象外） | JV-Data から作ったものなので公開しない |

## 4. コマンドの引数

`uv run python -m yosou.high_payout_combos <サブコマンド>` で動かす。元DB を開くのは `tables` だけである（`walk` と `train` は、保存した組の表から学ぶ）。

| サブコマンド | 何をするか | 引数 |
|---|---|---|
| `tables` | 過去のレースの組の表を作る | `--from`（最初の開催日。既定 2015-01-01）・`--to`（最後の開催日。省略すると馬ごとの表の最後の開催日）・`--force`（済んだ券種・年も作り直す）・`--horses`・`--tables`（置き場所） |
| `walk` | 年ごとに学んで次の年を予測し、買い目の年ごとの成績を出す | `--first-year`（予測を始める年。既定 2020）・`--value-line`（成績を数えるときの期待値の線。既定 1.05。予測は変わらない）・`--force`（予測の済んだ年も学び直す。省略すると飛ばして、続きの年から再開する）・`--config`・`--tables`・`--predictions` |
| `train` | 本番のモデルを学習して保存し、検証の期間での当たり具合を出す | `--config`・`--tables` |

- 3つに共通: `--ticket`（対象の券種。名前か英名をいくつでも。省略すると5つ全部）と、共有の引数 `--models`・`--db`・`--format`・`--out`（[手本の 04 の「2つに共通の引数」](../近走と適性から3着以内を予想/04-classes.md#2つに共通の引数)）。
- `predict` は無い。1レースの予測は、道具の側が `HighPayoutPredictor` を呼んで行う（下の 5）。
- 途中経過は標準エラーに、結果の表は標準出力か `--out` に出す。

## 5. 道具との約束

この予想を使う道具（今週の予想・発走前の通知・その日の結果・道具「高配当の買い目」）は、`yosou.high_payout_combos` から次のものだけを使う。

| 名前 | 何か |
|---|---|
| `YOSOU_NAME` | この予想の名前 |
| `PayoutBand`・`DEFAULT_BANDS`・`DEFAULT_VALUE_LINE` | 帯と、5券種の既定の帯、期待値の線の既定（1.05） |
| `HighPayoutPredictor` | 1レースの予測の入口。`load(モデルの置き場所)` で作り、`predict(馬ごとの表, 板)` で、組ごとの券種・組番・馬番の並び・オッズ・確率・期待値を返す |
| `HighPayoutRule` | 買い目の決まり。`pick(組の表)` で買う組だけを返す |
| `PredictionStore` | 年ごとの予測（`walk` の出力）を読む。成績を数える道具が使う |

道具の側のクラスは次のとおり。本番の買い目の出し方は [買うレースと買い目を決める の 08 の 2](../買うレースと買い目を決める/08-bankroll-and-review.md#高配当の買い目) を参照。

| クラス・ファイル | 仕事 |
|---|---|
| `tools/今週の予想/high_payout_picker.py` の `HighPayoutPicker` | 印を付けた1レースの表と締め切り前の板から、高配当の買い目を作る（`HighPayoutPredictor` → `HighPayoutRule` の順に呼ぶ） |
| `tools/今週の予想/race_boards.py` の `RaceBoards` | 1レースの締め切り前の板を、券種ごとに1回だけ読む |
| `tools/今週の予想/high_payout_summary.py` の `HighPayoutSummary` | 高配当の買い目を券種ごとにまとめて文にする（1レースの文・発走前の通知・その日の結果が使う） |
| `tools/高配当の買い目/horses.py` | 馬ごとの表を作る（[08-training-data.md の 5](08-training-data.md#5-馬ごとの予想の出どころ)） |
| `tools/高配当の買い目/stats.py` | 年ごとの予測から、買い目の成績を数える（[16-evaluation.md の 4](16-evaluation.md#4-年ごとの確かめ)） |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-11-24 |
