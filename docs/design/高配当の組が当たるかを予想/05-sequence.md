# 05 学習と予測のやりとり（シーケンス図）

**この文書で示すこと:** 組の表づくり・学習・年ごとの確かめ・1レースの予測のとき、利用者・元DB と、[04-classes.md](04-classes.md) のクラスが、どの順に、どのメソッドを呼ぶか。

**結論: 流れは4つに分かれる。** 組の表づくり（`tables`。図1）は `TableWorkflow` が進め、月ごとに元DB の確定オッズの板と払戻を読んで、組の表を年ごとのファイルに書く。本番のモデルの学習（`train`。図2）は `ProductionTraining` が、年ごとの学習と予測（`walk`。図3）は `WalkForwardWorkflow` が進め、どちらも保存した組の表だけから学ぶ（元DB を開かない）。1レースの予測と買い目（図4）は、今週の予想の当日の予想が `HighPayoutPredictor` と `HighPayoutRule` を呼んで行う。組の表を作る `ComboTableBuilder` は、図1 と図4 の両方に出てくる。

- public メソッドの中の判断（if 文による分かれ道）は [06-flowchart.md](06-flowchart.md) を参照。
- 図の読み方（凡例）は [手本の 05 の「図の読み方」](../近走と適性から3着以内を予想/05-sequence.md#図の読み方) を参照。
- 用語の意味は [02-glossary.md](02-glossary.md) を参照。

## 図に出てくるもの

| 名前 | 種類 | 呼ばれ方 |
|---|---|---|
| 利用者 | 人 | ― |
| 元DB | jvdata-store が作った DuckDB。この予想は読むだけ | 共有のリポジトリが SQL を1回流す |
| `TableWorkflow` など | この予想のクラス。一覧と仕事は [04-classes.md](04-classes.md#2-この予想だけのクラス) | public メソッドを1回呼ぶ |
| `LightGbmModel`・`CatBoostModel`・`EnsembleModel` | 共有のモデルのクラス | `fit()` か `predict_proba()` を1回呼ぶ（中のやりとりは [12-lightgbm.md](12-lightgbm.md)・[13-catboost.md](13-catboost.md)） |
| `horses/`・`tables/`・`predictions/`・`models/` | `reports/高配当の組が当たるかを予想/` の下のファイル | 1回書き込むか、1回読み込む |
| `RaceForecaster`・`ForecastTickets`・`HighPayoutPicker`・`RaceBoards` | 道具「今週の予想」のクラス（`tools/今週の予想/`） | public メソッドを1回呼ぶ |

## 図1. 組の表を作る

```mermaid
sequenceDiagram
    actor 利用者
    participant CL as CommandLine
    participant TC as TablesCommand
    participant HR as HorseTableRepository
    participant TW as TableWorkflow
    participant ML as FinalMarketLoader
    participant CB as ComboTableBuilder
    participant HL as HitLabeler
    participant CW as ComboTableWriter
    participant DB as 元DB
    participant F as tables/

    利用者->>CL: tables（--from・--to・--ticket）
    CL->>TC: run(args)
    TC->>HR: load()
    HR-->>TC: 馬ごとの表（horses/ の全部）
    TC->>TW: run(最初の開催日, 最後の開催日)
    loop 年ごと（済んでいる券種・年は飛ばす）
        loop 月ごと
            TW->>ML: load(その月の開催日, レースID, 券種)
            ML->>DB: 確定オッズの板（5券種）と払戻
            DB-->>ML: 板と払戻
            ML-->>TW: FinalMarket
            TW->>CB: build(その月の馬ごとの表, 板, 券種)
            CB->>CB: 市場の表 → 馬ごとの材料 → レースごとの表 → 券種ごとの組の表（06 の図1・図2）
            CB-->>TW: 券種ごとの組の表（特徴量と出発点）
            loop 券種ごと
                TW->>HL: label(券種, 組の表, 払戻, 開催日)
                HL-->>TW: 当たったか・払戻の付いた組の表
                TW->>CW: write(組の表)
                CW->>F: 券種と年ごとのファイルに足す
            end
        end
    end
    TW-->>TC: 券種ごと・年ごとの結果
    TC-->>利用者: 対象の組の数と当たった組の数の表
```

説明。元DB は、月ごとに板と払戻を読む間だけ開く。特徴量を作っている間は閉じているので、ほかの道具を待たせない。3連単は1年で数百万行になるので、月ごとに作って年のファイルに足し、1年ぶんをメモリに持たない。書いている途中のファイルは別の名前にしておき、書き終えてから名前を直す。途中で止まった年が、済んだ年に見えないようにするためである。`ComboTableBuilder.build()` の中で呼ぶクラス（`MarketTableBuilder`・`HorseMaterials`・`RaceMaterials`・`TicketTableAssembler` と `feature/` の各クラス）は [04-classes.md](04-classes.md#dataset--組の表を作る) を、表に入れる組の選び方は [06-flowchart.md の図1](06-flowchart.md#図1-表に入れる組の選び方) を参照。

## 図2. 学習

本番のモデルの学習（`train`）。

```mermaid
sequenceDiagram
    actor 利用者
    participant CL as CommandLine
    participant TC as TrainCommand
    participant HS as HyperparameterSettings
    participant PT as ProductionTraining
    participant YS as YearSamples
    participant MT as TicketModelTrainer
    participant M as LightGbmModel・CatBoostModel
    participant MR as TicketModelRepository
    participant MC as MarketComparison
    participant T as tables/
    participant F as models/

    利用者->>CL: train（--config・--ticket）
    CL->>TC: run(args)
    TC->>HS: load(設定ファイル, 初期値)
    HS-->>TC: 設定
    loop 券種ごと
        TC->>PT: run(券種)
        PT->>YS: by_year(券種)
        loop 表のある年ごと
            YS->>T: 組の表を読む
            YS->>YS: 当たりは全部、外れは間引いて重みを付ける（MissSampling）
        end
        YS-->>PT: 年ごとの学習の行
        PT->>PT: 最後の開催日の1年前までを学習、最後の1年を検証に分ける
        PT->>MT: fit(学習の行, 検証の行)
        MT->>M: fit(学習データ, 検証データ)（出発点と重みつき。2つのモデルで1回ずつ）
        M-->>MT: 学習済みのモデル
        MT-->>PT: LightGBM と CatBoost
        PT->>MR: save(券種, モデル, 設定)
        MR->>F: 券種ごとのフォルダに保存
        PT->>MC: losses(検証データ, モデル)
        MC-->>PT: 対数損失（モデルごと・平均・市場）
        PT-->>TC: 結果
    end
    TC-->>利用者: 学習と検証の期間・行数・木の数の表、検証の期間での当たり具合の表
```

説明。学習は、保存した組の表だけから行う（元DB を開かない）。1年ぶんの表を読んでは間引くので、メモリに残るのは間引いた行だけである。学習データへの詰め替え（特徴量・目的変数・出発点・行の重み）は `ModelDataFactory` が行い、`TicketModelTrainer` が呼ぶ。検証の期間での当たり具合は、木の数を決めるのに使った行で測るので目安である（[16-evaluation.md の 8](16-evaluation.md#8-本番のモデルの学習)）。

## 図3. 年ごとの学習と予測

確かめ用（`walk`）。テストの年ごとに学び直す。

```mermaid
sequenceDiagram
    actor 利用者
    participant CL as CommandLine
    participant WC as WalkCommand
    participant WF as WalkForwardWorkflow
    participant YS as YearSamples
    participant MT as TicketModelTrainer
    participant TP as TablePrediction
    participant PS as PredictionStore
    participant SM as YearlyPickSummary
    participant HR as HighPayoutRule
    participant T as tables/
    participant P as predictions/

    利用者->>CL: walk（--first-year・--ticket）
    CL->>WC: run(args)
    loop 券種ごと
        WC->>WF: run(券種, 始める年)
        WF->>YS: by_year(券種)
        YS-->>WF: 年ごとの学習の行（間引いて重みつき）
        loop テストの年ごと（予測の済んでいる年は飛ばす）
            WF->>MT: fit(2年前までの行, 1年前の行)
            MT-->>WF: 学習済みの LightGBM と CatBoost
            WF->>T: テストの年の組の表を読む（間引かない）
            WF->>TP: probabilities(テストの年の組の表)
            TP-->>WF: 行ごとの確率（2つの平均とモデルごと）
            WF->>PS: save(券種, 年, 予測)
            PS->>P: 券種と年ごとのファイルに保存
        end
        WF-->>WC: 年ごとの結果
        WC->>PS: load(券種)
        PS-->>WC: 年ごとの予測
        WC->>SM: summarize(この回に予測した年の予測)
        SM->>HR: pick(予測)
        HR-->>SM: 買う組
        SM-->>WC: 年ごとの点数・的中数・回収率
    end
    WC-->>利用者: 年ごとの学習の表、買い目の年ごとの成績の表
```

説明。どの年の予測も、その年より前のレースだけで学んだモデルが出す（[11-leak-prevention.md](11-leak-prevention.md#決まり) の 5）。テストの年の行は間引かずに全部を予測し、保存する。保存した予測は、道具「高配当の買い目」の `stats.py` が読んで、期間ごとの成績と 90% の幅、運用の目安を出す（[16-evaluation.md の 4](16-evaluation.md#4-年ごとの確かめ)）。`walk` が出す年ごとの成績は、その場で見るための簡単な表である。予測の済んでいる年は学び直さないので、途中で止まっても続きの年から再開できる（`--force` を付けると、済んでいる年も学び直す）。

## 図4. 1レースの予測と買い目

本番。今週の予想の当日の予想の中で行う。

```mermaid
sequenceDiagram
    actor 利用者
    participant RF as RaceForecaster（今週の予想）
    participant FT as ForecastTickets（今週の予想）
    participant RB as RaceBoards（今週の予想）
    participant HP as HighPayoutPicker（今週の予想）
    participant PR as HighPayoutPredictor
    participant CB as ComboTableBuilder
    participant TP as TablePrediction
    participant HR as HighPayoutRule
    participant DB as 元DB
    participant F as models/

    利用者->>RF: 当日の予想（1レース）
    RF->>RF: 全頭の予想を出し、印と危険な人気馬の判定を付ける（印を付けた1レースの表）
    RF->>FT: 買い目を組む
    FT->>RB: many(5券種)
    RB->>DB: 締め切り前のいちばん新しい板（券種ごとに1回）
    DB-->>RB: 板
    RB-->>FT: 券種 → 板
    FT->>HP: pick(印を付けた1レースの表, 板)
    HP->>PR: predict(馬ごとの表, 板)
    PR->>CB: build(馬ごとの表, 板, モデルのある券種)
    CB-->>PR: 作れた券種の組の表（06 の図2）
    loop 作れた券種ごと
        PR->>TP: probabilities(組の表)
        TP-->>PR: 行ごとの確率（2つの平均）
    end
    PR-->>HP: 組ごとの券種・組番・馬番・オッズ・確率・期待値
    HP->>HR: pick(組の表)
    HR-->>HP: 買う組（06 の図3）
    HP-->>FT: 高配当の買い目（「ワイド（高配当）」など。1点ずつ）
    FT-->>RF: ほかの買い目と合わせた買い目
    RF-->>利用者: 予想の結果（1レースの文・通知・その日の結果が読む）
```

説明。学習済みのモデルは、`HighPayoutPicker` を作るときに1回だけ読む（`HighPayoutPredictor.load()`。図では省いた）。モデルの置き場所が無ければ、高配当の買い目は作らない。馬ごとの表は、印を付けた1レースの表から、この予想に要る列だけを取り出したものである。板が足りない券種・モデルの無い券種は、組を返さないので 0点になる（誤りにしない）。本番で出す券種と上限の点数は、道具の側の定数（`tools/今週の予想/ticket_rules.py` の `HIGH_PAYOUT_TICKET_TYPES`・`HIGH_PAYOUT_MAX_POINTS`）で決める（[15-decisions.md の 15・16](15-decisions.md#15-本番で出す券種)）。評価できない馬（データの無い招待馬）を含む組は、道具の側で外す。買い目の見せ方と、財布に入れないことは [買うレースと買い目を決める の 08 の 2](../買うレースと買い目を決める/08-bankroll-and-review.md#高配当の買い目) を参照。

## 今は無く、これから作るところ

無い。締め切り前の5券種のオッズは、jvdata-store がすでに取っている（速報のオッズ）。

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-11-24 |
