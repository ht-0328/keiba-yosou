# 05 学習と予測のやりとり（シーケンス図）

**この文書で示すこと:** 学習と予測のとき、利用者・元DB と、[04-classes.md](04-classes.md) のクラスが、どの順に、どのメソッドを呼ぶか。

**結論: 流れは「学習」と「予測と買い目」の2つに分かれる。** 学習は `train` で、手本の `TrainCommand` が学習データを作り、`WildRaceRows` が荒れたレースの行だけを残してから、手本と同じ形で学んで保存する。予測と買い目は道具「帯狙い」の `ObiDayRun` が進め、レースごとに点数（荒れ具合の予想の確率と、今の予想の結果と3連単のオッズから出す予想が見た確率の平均）を出して線以上のレースを全部選び、選んだレースを `RaceForecaster` で荒れる前提の予想をして、買い方で1万円の買い目を組む。

図の読み方（凡例）は [手本の 05 の「図の読み方」](../近走と適性から3着以内を予想/05-sequence.md) を参照。用語の意味は [02-glossary.md](02-glossary.md) を参照。

## 図1. 学習

```mermaid
sequenceDiagram
    actor 利用者
    participant CL as CommandLine
    participant TC as TrainCommand（手本）
    participant WR as WildRaceRows
    participant RP as RacePayoutRepository
    participant TW as TrainingWorkflow（共通）
    participant DB as 元DB
    participant F as models/

    利用者->>CL: train
    CL->>TC: run(args)
    TC->>DB: 手本の学習データを作る（当日・木曜と前日）
    DB-->>TC: 学習データ
    TC->>WR: keep(con, 学習データ)
    WR->>RP: read(最初の開催日)
    RP->>DB: SQL（レースごとの払戻）
    DB-->>RP: 払戻
    RP-->>WR: レースごとの3連単の払戻
    WR-->>TC: 荒れたレースの行だけの学習データ
    loop 時点ごと（3着以内と1着。当日は券種オッズなしも）
        TC->>TW: train(学習データ, 設定)
        TW->>F: LightGBM と CatBoost を保存
    end
    TC-->>利用者: 検証データでの当たり具合の表
```

説明。学習データを作る段（元DB を開いている間）に、`WildRaceRows` が払戻を読んで行を絞る。そのあとは手本の学習とまったく同じで、置き場所だけが `reports/荒れる前提で着順を予想/models/` になる。

## 図2. 予測と買い目

```mermaid
sequenceDiagram
    actor 利用者
    participant OBI as obi.py
    participant RUN as ObiDayRun
    participant PK as ObiDayPicker
    participant TCH as TimingChooser
    participant UP as PredictionWorkflow（荒れ具合の予想）
    participant RF as RaceForecaster（今週の予想）
    participant FS as ForecastStore（今週の予想）
    participant SC as 点数（BigPayoutChance・RaceSelectionScore）
    participant FH as ForecastHorses
    participant AO as AnnouncedComboOdds
    participant PL as 買い方（一律・甲・乙・丙）
    participant DB as 元DB
    participant S as reports/帯狙い/

    利用者->>OBI: obi.py（--date）
    OBI->>RUN: run(con, 開催日)
    RUN->>DB: その日のレースの一覧
    RUN->>PK: rank(con, レースの一覧)
    loop レースごと
        PK->>TCH: choose(con, レース)
        TCH-->>PK: 時点
        PK->>UP: run(レース, 時点, 3連単)
        UP->>DB: オッズと予測用データ
        UP-->>PK: 3連単の荒れ具合の4つの確率（大荒れ＋超荒れ）
        PK->>FS: load(レース)（今週の予想が保存した結果）
        alt 同じ時点の結果があるとき
            FS-->>PK: 今の予想の結果
        else 無いとき
            PK->>RF: forecast(con, レース, 時点)（今の予想のモデル）
            RF-->>PK: 今の予想の結果
        end
        PK->>AO: read(レース, 3連単)
        AO-->>PK: 組 → オッズ
        PK->>SC: BigPayoutChance.of(今の予想の RaceHorses, オッズ) → RaceSelectionScore.of(大荒れ＋超荒れ, 予想が見た確率)
        SC-->>PK: 点数
    end
    PK-->>RUN: 点数の高い順（線以上を全部選ぶ。今の予想の結果も添える）
    loop 選んだレースごと
        RUN->>RF: forecast(con, レース, 時点)（この予想のモデル）
        RF->>DB: 予測用データ（手本と同じ）
        RF-->>RUN: 荒れる前提の3着以内と1着の確率・印
        RUN->>FH: of(荒れる前提の結果, 今の予想の結果)
        FH-->>RUN: RaceHorses
        RUN->>AO: read(レース, 3連単)
        AO->>DB: 締め切り前（なければ確定）の組ごとのオッズ
        AO-->>RUN: 組 → オッズ
        opt オッズがあるとき
            RUN->>PL: tickets(RaceHorses, オッズ)
            PL-->>RUN: 組と掛け金
        end
    end
    RUN-->>OBI: 1日の結果
    OBI->>S: <開催日>.json に保存
    OBI-->>利用者: 荒れそうなレースの上位・選んだレースごとの出走馬と買い目の表
```

説明。`RaceForecaster` には、この予想のモデルの置き場所を渡す。そのため、予測用データの作り方・材料の足し方・印の付け方・危険な人気馬の判定は、今週の予想とまったく同じで、確率だけが荒れる前提のモデルのものになる。その日の全レースを今の予想でも予想する（保存した同じ時点の結果があれば読む）のは、点数（予想が見た 1,000倍以上になる確率）と、一律の買い方の2着・3着の重みに使うためである（[15-decisions.md の 6・8](15-decisions.md#6-組の確率の2着3着の重み)）。今の予想は1レース数十秒かかるので、先に今週の予想を動かしておくと速い。組ごとのオッズが無いとき（当日の速報の前）は、買い目を組まず、当日にもう一度動かすことを結果に書く。

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-10-12 |
