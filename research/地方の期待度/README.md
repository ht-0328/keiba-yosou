# 地方の期待度

**何をする研究か。** 地方の発走前の通知に添える「期待度」（レースに添える1つだけの目安。S・A・B・C）を、何から点数にし、どこで線を引くかを、
地方の未見の予測で決める。最初は ◎ の確率と単勝の期待値から作り（docs/01）、そのあと、そのレースの推奨買目の見込みから作るように変えた（docs/02）。

**なぜ始めたか。** 利用者から「地方競馬の予想で自信度を出してほしい」「中央は配当率と的中率を分けているが、地方はいったん1つの指標で、期待度の高いものにしてほしい」
「あくまで期待度を出すだけで、買い目は変えない」と言われた（2026-11-10）。続けて「期待度は、そもそも推奨買目の期待度にしたほうがいいのでは」と言われた（2026-11-16）。

結論は [docs/02-推奨買目の見込みで付ける期待度.md](docs/02-推奨買目の見込みで付ける期待度.md)（今の期待度）と [docs/01-点数と線の決め方.md](docs/01-点数と線の決め方.md)（◎ の点数。道具「印の成績」の表13 の地方の分け方）。本番の決まりは設計書「買うレースと買い目を決める」の [11](../../docs/design/買うレースと買い目を決める/11-local-expectation.md)。
数値（地方競馬DATA 由来の成績・回収率）は Git 対象外の `reports/地方の期待度/` に出し、この README と docs には書かない。

## この文書で使う言葉の意味

| 言葉 | 意味 | この研究では（架空の例） |
|---|---|---|
| ◎ | 通知と同じ決め方で付けた本命。単勝 30倍以下の馬の中で単勝の期待値（1着になる確率 × 単勝オッズ）が1位（`MarkRule`） | 1着の確率 0.28・単勝 4.0倍 の馬 |
| 点数 | ◎ の確率と期待値から作る1つの数。候補の式ごとに違う | 1着の確率 ＋ 3 ×（期待値 − 1）= 0.28 + 3 × 0.12 = 0.64 |
| 等級 | 点数を S・A・B・C にしたもの。線は下の値を含む（`GradeLines`） | 0.64 → S |
| 線を決める年・確かめる年 | 線は 2024年の点数の分位（上から 20%・30%・30%・20%）で決め、2025・2026年で等級の順に成績が上がるかを見る | |
| 順に上がった | C → B → A → S の順に、率（勝率・複勝率・単勝回収率・複勝回収率）が真に上がったこと | |

## フォルダの中身

| 場所 | 何があるか |
|---|---|
| `expectation.py` | 入口。◎ の行を読み（無ければ作り）、点数の候補ごとに年 × 等級の ◎ の単勝・複勝の成績と推奨買目の成績、まとめの表を Markdown に書く |
| `analysis/top_picks.py` | 地方の予想モデルの backtest の未見の予測（`predictions-2024検証`）に、印の成績と同じ決め方で印を付け、◎ の行（確率・期待値・結果・払戻・頭数）だけを残して pickle にとっておく（`TopPicks`） |
| `analysis/score_candidate.py` | 点数の候補の式（`CANDIDATES`。結果を見る前に決めた一覧） |
| `analysis/grade_lines.py` | 線の決め方（分位・0.01 刻み）と、点数を等級にする（`GradeLines`） |
| `analysis/grade_year_table.py` | 年 × 等級の ◎ の成績の表と、順に上がった年の数え上げ（`GradeYearTable`） |
| `analysis/recommended_tickets.py` | 研究「地方の万馬券」段5 の買い目（1行 = 1点）をレースにまとめ、等級ごとの推奨買目の回収率と的中レース率（`RecommendedTickets`） |
| `analysis/expectation_study.py` | 流れ（`ExpectationStudy`） |
| `grade.py` | 入口。過去のレースの推奨買目を本番と同じ決まりで作り直し（`--build`）、推奨買目の見込みの帯・等級ごとの成績を年ごとに書く（docs/02） |
| `analysis/recommended_bets_builder.py` | 過去のレースの推奨買目を本番と同じ決まり・同じ組の確率で作り直す（`RecommendedBetsBuilder`。入れ替え・前の年・本番の係数の3通り） |
| `analysis/bulk_plan_chooser.py` | 本番の買い方（`RECOMMENDED_PLANS`）を、頭数・形・荒れ具合・点数の上限をレースごとに引いてまとめて当てはめる（`BulkPlanChooser`） |
| `analysis/race_scores.py` | 推奨買目を1レースにまとめ、点数・投資・払戻・見込みの回収率・期待の儲けを出す（`RaceScores`） |
| `analysis/grade_study.py` | 見込みの帯と等級ごとの成績、◎ の点数・本番の線との比べ、等級の順に上がったかの表（`GradeStudy`） |
| `docs/` | 01 点数と線の決め方（◎ の点数）、02 推奨買目の見込みで付ける期待度（今の期待度） |
| `tests/` | 架空の値で部品を確かめるテスト（実DB は要らない） |
| `reports/地方の期待度/`（Git 対象外） | `期待度の候補-当日.md`・`期待度の候補-前日.md`・`cache/◎-<予測>-<時点>.pkl`・`推奨買目[-前の年・-本番].pkl`・`レース[-前の年・-本番].pkl`・`推奨買目の見込みの期待度[-前の年・-本番].md` |

## 動かし方

リポジトリ直下（`keiba-yosou/`）から実行する。元DB は nvdata-store の `nvdata.duckdb`（読むだけ）。◎ の行を作るときは地方の全成績の事実表を作るので十数分かかる。

```bash
uv run python research/地方の期待度/expectation.py                 # 当日の時点（◎ の行が無ければ元DB から作る）
uv run python research/地方の期待度/expectation.py --timing 前日     # 前日の時点
uv run python research/地方の期待度/expectation.py --rebuild        # ◎ の行を作り直す（予測を作り直したとき）
uv run python research/地方の期待度/grade.py --build              # 推奨買目を作り直して、見込みの期待度の表を書く（元DB を読む。20〜30分。--db で写しを渡せる）
uv run python research/地方の期待度/grade.py --build --protocol 前の年   # 前の年だけで当てはめた組の確率で（2025・2026年）
uv run python research/地方の期待度/grade.py --build --protocol 本番 --test-from 2026-01-01   # 本番の予想モデルの予測と本番の係数で（2026年）
uv run python research/地方の期待度/grade.py                      # 作り直した推奨買目から表だけ書き直す（数十秒。◎ の点数との比べに expectation.py の ◎ の行を使う）
uv run python -m pytest -q research/地方の期待度                    # テスト
```
