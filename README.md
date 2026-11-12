# zengauge

ZEN Study（N高・S高などの学習サイト）のレポート進捗を、iPhone のホーム画面・ロック画面に
ウィジェットで表示する。[Scriptable](https://scriptable.app/) のスクリプト 1 本で動き、PC は要らない。

PC（Mac / Windows）から進捗を取得して iCloud Drive 経由で渡す Python 版も同梱している。

> 非公式のツールです。ZEN Study / N Lobby とは関係ありません。自分のアカウントでのみ使ってください。
> 使っている API は公開されていないもので、予告なく変わることがあります。

## 表示する内容

| | 小 | 中 | 大 |
|---|---|---|---|
| 今月のレポート（済み / 全体、締め切りまでの日数） | ○ | ○ | ○ |
| 月間ゲージ・年間ゲージ（同じ幅で上下に並べる） | ○ | ○ | ○ |
| 教材の進み（%） | ○ | ○ | ○ |
| 残りの教科 | – | 4件 | 5行（テスト含む） |
| 来月分・締めを過ぎた未完了の月 | – | – | ○ |
| 更新時刻 | ○ | ○ | ○ |

ロック画面（インライン・円形・長方形）にも対応している。
締め切りが 3 日以内になるとゲージが橙、過ぎると赤になる。

## iPhone だけで使う

1. App Store から Scriptable を入れる。
2. [`scriptable/ZEN Study進捗.js`](scriptable/ZEN%20Study進捗.js) の中身を Scriptable の新規スクリプトに貼り付け、
   名前を「ZEN Study進捗」にする（iCloud Drive の `Scriptable` フォルダに置いてもよい）。
3. スクリプトを実行して「スマホでログイン」を選ぶ。N Lobby のログイン画面が出るのでログインする。
4. ホーム画面に Scriptable のウィジェットを置き、スクリプトに「ZEN Study進捗」を選ぶ。

ウィジェットは 30 分ごとに自分で更新する。ログインが切れると「ログインが切れています」と出て、
タップするとログイン画面が開く。

### ログインの仕組み

ZEN Study のログインは `www.nnn.ed.nico/auth/n_lobby` → N Lobby → `/auth/n_lobby/callback` の順に進む。
最初と最後を Scriptable の `Request` が行い、内蔵ブラウザには N Lobby の画面だけを出す
（callback への移動は `WebView.shouldAllowRequest` で止めて、Scriptable 側で開き直す）。
こうするとブラウザの中に閉じ込められる HttpOnly のセッション Cookie を受け取れるので、
Scriptable のキーチェーンに保存してウィジェットが自分で取得できる。

- パスワードはスクリプトを通らず、保存もしない。
- 保存するのはセッション Cookie だけで、Scriptable のキーチェーンに入る。
- 読み取り専用。ZEN Study 側に書き込む API は使わない。

## PC から渡す（任意）

PC（Mac / Windows）が 30 分ごとに進捗を取得し、iCloud Drive の Scriptable フォルダに書き出す。
ウィジェットは PC の書き出しが 75 分以内ならそれを表示する。スマホでのログインがうまくいかないときに使う。

**ターミナルは使わない。** ダブルクリックだけで準備できる。

1. このページの緑の「Code」→「Download ZIP」でダウンロードし、ZIP を開く（できたフォルダは好きな場所に置いてよい）。
2. フォルダの中の **Mac は `setup-mac.command`、Windows は `setup-windows.bat`** をダブルクリックする。
3. 黒い画面が開いて準備が進む。途中でブラウザが開くので、ZEN Study にログインする。
4. 「完了しました」と出たら終わり。画面は閉じてよい。

ログインが切れたときも、同じファイルをもう一度ダブルクリックすればよい。
自動更新をやめるときは `stop-mac.command` / `stop-windows.bat` をダブルクリックする。

### 初めて開くときの注意

ネットから落としたファイルなので、最初の 1 回だけ確認が出る。

- **Mac**: 「開けません」「Apple は検証できませんでした」と出たら「完了」を押し、
  「システム設定」→「プライバシーとセキュリティ」を開いて、下の方の「このまま開く」を押す。
- **Windows**: 「Windows によって PC が保護されました」と出たら「詳細情報」→「実行」を押す。

### 必要なもの

- Python 3.9 以上。Mac は標準のもので動く（入っていなければ、入れるよう案内する画面が出る）。
  Windows は [python.org](https://www.python.org/downloads/) から入れ、最初の画面で「Add python.exe to PATH」にチェックを入れる。
- Windows では「iCloud for Windows」で iCloud Drive を有効にしておく。
- ログイン用のブラウザ（Chromium）は、最初のログインのときに自動で入る。

### ターミナルで使う場合

ダウンロードしたフォルダの中で実行する。

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

以下、Mac は `.venv/bin/python zengauge.py`、Windows は `.venv\Scripts\python zengauge.py` を `zg` と書く。

| コマンド | 内容 |
|---|---|
| `zg login` | Chromium が開くので ZEN Study にログインする。確認できたら閉じて保存し、1 回書き出す |
| `zg sync` | 進捗を取得して書き出す |
| `zg schedule` | 30 分ごとの自動更新を登録する（Mac は launchd、Windows はタスクスケジューラ）。`--off` で解除 |
| `zg status` | ログインの有効・無効、書き出し先、最後の書き出し、自動更新の有無 |
| `zg import <file>` | 既存のログイン情報を取り込む（Playwright の storageState.json か `name=value; ...` 形式の Cookie ファイル） |
| `zg setup --scriptable-dir <dir>` | Scriptable の iCloud フォルダを指定する |

ログイン情報は Mac なら `~/Library/Application Support/zengauge/`、
Windows なら `%APPDATA%\zengauge\` に保存し、リポジトリや iCloud には置かない。
iCloud に書き出すのは進捗の数字だけ。

既知の問題: macOS では、launchd から動く Python が iCloud フォルダ内の古い書き出しファイルを
消せないことがある（`com.apple.macl` による保護）。その場合ファイルが溜まるが、ウィジェットは一番新しいものを読む。

## テスト

```bash
python3 -m unittest discover -s tests
```

テストは架空のデータだけを使う。Node があれば、Python の集計とウィジェットの JavaScript の集計が
一致することも確かめる。
