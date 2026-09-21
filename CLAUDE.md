# keiba-yosou

- DB（`../jvdata-store/jvdata.duckdb`）のデータを扱う依頼では、SQL を組み立てる前に `tools/README.md` の早見表を見て、`tools/` のツールで済ませる。ツールに無い機能が要るときだけ `tools/共通/` に部品を足す。
- 元DB は読むだけ（`read_only=True`）。取得・取り込みは隣の jvdata-store の責務で、ここには持ち込まない。
- ツールは全部 `tools/` の下。ツール1つにつき日本語のフォルダ1つ（例 `tools/成績集計/perf.py`）。`src/yosou/` は予想方法を作るときのもので、ツールを置かない。
- 馬名・騎手名・オッズ・払戻など JV-Data 由来の実値を docs・README・コミット・PR・報告に書かない。出力は標準出力か `reports/`（Git 対象外）へ。
- 実行は `uv run python tools/<ツール>/<file>.py`。uv が PATH に無ければ `%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe` を使う。
- `*.bat` は UTF-8（BOM なし）・CRLF で保存し、コメントは日本語で書く。ただし日本語は、先頭の `goto :main` と `:main` の間のコメントの中にだけ書く（例 `tools/検索画面/run.bat`）。cmd.exe は bat をコンソールのコードページで読むので、実行される行に日本語があるとコメントの切れ端がコマンドとして実行される。Shift_JIS では保存しない（エディタや GitHub で文字化けする）。
- テストは `uv run python -m pytest -q`。合成 DB（`tools/合成DB/synth.py`）だけを使い、実DBに触るテストを書かない。
- 新しい集計を作ったら `uv run python tools/成績集計/perf.py --check` で `reports/stats` の値と一致することを確かめてから先へ進む。
- コミットは Conventional Commits（`feat:` `fix:` `docs:` `refactor:` `test:` `chore:`）。main に直接積まず、作業ブランチで。push と PR は頼まれたときだけ。
- コードの基準は `../software-engineering-guide/docs/01-good-code.md`（GC-01〜GC-17）。
