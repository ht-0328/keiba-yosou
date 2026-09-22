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

## 並行で作業するとき（ブランチごとに作業フォルダを分ける）

利用者は、このリポジトリで複数の Claude のセッションを同時に動かすことがある。1つの作業フォルダは1つのブランチしか持てないので、ブランチごとに作業フォルダ（Git の worktree）を分ける。

- **`keiba-yosou/`（メインの作業フォルダ）で、`git checkout` や `git switch` でブランチを切り替えない。** ほかのセッションが同じフォルダで作業していると、その足元のファイルとコミット先が変わってしまう。
- 自分のブランチの作業は、keiba-yosou の隣に作業フォルダを作って、そこで行う。名前は `keiba-yosou-worktree-<ブランチの短い名前>`（例 `../keiba-yosou-worktree-form-aptitude-top3`）。隣に置くのは、元DB（`../jvdata-store`）を、道具が今までどおり見つけられるようにするためである。
- 分けた作業フォルダの `reports/` は、メインの `reports/` へのつなぎ（ジャンクション）にする。`reports/` は Git の対象外で、作業フォルダごとに別になってしまうため。つなぐと、どの作業フォルダから書いても出力が1か所に集まり、`reports/stats` での答え合わせも使える。
- コミットの前に `git branch --show-current` で、自分の作業のブランチかを確かめる。`git add` はファイルを名前で指定し、フォルダごと足さない（ほかのセッションが同じフォルダに書いていることがある）。
- 見つけた未コミットの変更は、ほかのセッションが作業中のものかもしれない。自分のものと決めつけてコミットしない。

作る（メインの作業フォルダで、PowerShell から。`<名前>` はブランチの短い名前、`<元>` は分かれる元のブランチ）:

```powershell
git worktree add ..\keiba-yosou-worktree-<名前> -b <ブランチ> <元>        # 新しいブランチの作業フォルダを作る（既にあるブランチなら -b <ブランチ> <元> の代わりに <ブランチ>）
cmd /c mklink /J ..\keiba-yosou-worktree-<名前>\reports "$PWD\reports"   # reports をメインへつなぐ
uv sync --directory ..\keiba-yosou-worktree-<名前>                       # その作業フォルダ用の .venv を作る
```

消す（先につなぎを外す。外すのはつなぎだけで、メインの `reports/` の中身は消えない）:

```powershell
cmd /c rmdir ..\keiba-yosou-worktree-<名前>\reports   # つなぎを外す
git worktree remove ..\keiba-yosou-worktree-<名前>    # 作業フォルダを消す（ブランチとコミットは残る）
git worktree list                                     # 今ある作業フォルダの一覧
```

つなぎを外さずに `git worktree remove` しても、Git はつなぎの先をたどらない（メインの `reports/` は消えない）。ただし、つなぎと空のフォルダが残る。
