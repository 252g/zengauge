# zengauge

**ZEN Study のレポート進捗を、iPhone のホーム画面でひと目で。**

ZEN Study（N高・S高などで使われている学習サイト）の「今月のレポートがあと何本残っているか」を、
iPhone のウィジェットに表示します。無料アプリ [Scriptable](https://scriptable.app/) で動き、PC は要りません。

```
┌──────────────────────────┐
│ 11月レポート      あと4日 │
│ 7 / 10      テスト 0/3   │
│ ━━━━━━━━━━━━━━──────     │  ← 今月
│ 期限 11/15 · 教材 94%    │
│ 年間              53/64  │
│ ━━━━━━━━━━━━━━━━━━──     │  ← 年間
│                 18:30 更新│
└──────────────────────────┘
```

> [!NOTE]
> 非公式のツールです。ZEN Study・N Lobby の運営元とは関係ありません。
> 自分のアカウントでのみ使ってください。ZEN Study 側の仕様が変わると動かなくなることがあります。

## できること

- 今月のレポートの進み（済み / 全体）と、締め切りまでの日数
- 今月と年間の進みをゲージで表示（締め切り 3 日前から橙、過ぎると赤）
- 残っている教科と、それぞれの進み（中・大サイズ）
- 定期テストの進み、来月分、締めを過ぎて終わっていない月（大サイズ）
- ロック画面のウィジェットにも対応
- 30 分ごとに自動で更新

## はじめかた（iPhone だけ・5 分ほど）

### 1. Scriptable を入れる

App Store で「[Scriptable](https://apps.apple.com/app/scriptable/id1405459188)」を入れます（無料）。

### 2. スクリプトを入れる

1. iPhone でこのページの [`scriptable/ZEN Study進捗.js`](scriptable/ZEN%20Study進捗.js) を開き、右上の「Raw」を押します。
2. 表示された文字を全部選んでコピーします。
3. Scriptable を開き、右上の「＋」を押して、コピーした文字を貼り付けます。
4. 上の名前の部分を押して「**ZEN Study進捗**」に変え、「Done」を押します。

### 3. ログインする

1. Scriptable の一覧で「ZEN Study進捗」を押して実行し、「**スマホでログイン**」を選びます。
2. N Lobby のログイン画面が出るので、いつもどおりログインします。
3. 「ログインできました」と出たら、左上のボタンで閉じます。

### 4. ウィジェットを置く

1. ホーム画面の何もないところを長押しし、左上の「編集」→「ウィジェットを追加」を押します。
2. 「Scriptable」を選び、好きな大きさのウィジェットを追加します。
3. 追加したウィジェットを長押しして「ウィジェットを編集」を押し、**Script** で「ZEN Study進捗」を選びます。

これで完成です。

## よくある質問

**パスワードは大丈夫？**
パスワードは N Lobby の画面に直接入れるだけで、スクリプトは読みませんし、保存もしません。
保存するのはログイン状態を表す情報（Cookie）だけで、iPhone の中（Scriptable のキーチェーン）にしまわれます。
ZEN Study 以外のサーバーには何も送りません。

**ZEN Study に何か書き込まれたりしない？**
しません。進捗を読むだけです。

**「ログインが切れています」と出た**
しばらくするとログインの有効期限が切れます。ウィジェットを押すとログイン画面が開くので、もう一度ログインしてください。
それまでは、最後に取れた数字がそのまま表示されます。

**締め切りの日付が違う気がする**
ZEN Study に登録されている、その月で一番早いレポートの締め切りを表示しています。

**ウィジェットがすぐに変わらない**
iPhone がウィジェットを更新するタイミングは iOS が決めるので、30 分より遅れることがあります。
すぐ見たいときはウィジェットを押すと、最新の状態を大きく表示します。

**やめたいとき**
Scriptable でスクリプトを実行し「ログイン情報を削除」を選んでから、スクリプトとウィジェットを消してください。

## PC でログインして QR コードで送る

スマホでのログインがうまくいかないときは、PC（Mac / Windows）でログインして、
QR コードで iPhone に送ることもできます。送ったあとはウィジェットが自分で更新するので、PC は要りません。

1. このページ上の緑の「Code」→「Download ZIP」でダウンロードし、ZIP を開きます。
2. フォルダの中の **Mac は `setup-mac.command`、Windows は `setup-windows.bat`** をダブルクリックします。
3. 途中でブラウザが開くので、ZEN Study にログインします。
4. QR コードが表示されたら、iPhone のカメラで読み取り、「Scriptable で開く」→「保存する」を押します。

- 先に iPhone の Scriptable に「ZEN Study進捗」を入れておいてください（[はじめかた](#2-スクリプトを入れる)の 2 まで）。
- ログインが切れたら、同じファイルをもう一度ダブルクリックして、新しい QR コードを読み取ります。
- QR コードにはログイン情報が入っています。人に見せたり、撮影して送ったりしないでください。
- 初めて開くときは、ネットから落としたファイルなので確認が出ます。
  Mac は「システム設定」→「プライバシーとセキュリティ」の「このまま開く」、
  Windows は「詳細情報」→「実行」で開けます。
- Windows では [Python](https://www.python.org/downloads/)（最初の画面で「Add python.exe to PATH」にチェック）が必要です。
  Mac は最初から入っているもので動きます。

## 開発者向け

<details>
<summary>ログインの仕組み</summary>

ZEN Study のログインは `www.nnn.ed.nico/auth/n_lobby` → N Lobby → `/auth/n_lobby/callback` の順に進みます。
最初と最後を Scriptable の `Request` が行い、内蔵ブラウザには N Lobby の画面だけを出します
（callback への移動は `WebView.shouldAllowRequest` で止めて、Scriptable 側で開き直します）。
こうすると、ブラウザの中に閉じ込められる HttpOnly のセッション Cookie を受け取れるので、
キーチェーンに保存してウィジェットが自分で取得できます。

進捗は `https://api.nnn.ed.nico/v2/dashboard/report_progresses`（と月別の詳細）を GET で読んでいます。
</details>

<details>
<summary>PC 版をコマンドで使う</summary>

ダウンロードしたフォルダの中で実行します。Python 3.9 以上。

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python zengauge.py login
```

| コマンド | 内容 |
|---|---|
| `login` | Chromium でログインして保存し、iPhone に送る QR コードを表示する（Chromium は初回に自動で入る） |
| `qr` | 保存したログインの QR コードをもう一度表示する |
| `status` | ログインの状態（有効期限の目安）と今月の進捗を表示する |
| `import <file>` | 既存のログイン情報を取り込む（Playwright の storageState.json か `name=value; ...` 形式） |

QR コードの中身は `scriptable:///run/ZEN%20Study進捗?action=import&cookie=…` というリンクです。
ログイン情報は Mac なら `~/Library/Application Support/zengauge/`、Windows なら `%APPDATA%\zengauge\` に保存します。
</details>

<details>
<summary>テスト</summary>

```bash
python3 -m unittest discover -s tests
```

架空のデータだけを使います。Node があれば、Python の集計とウィジェットの JavaScript の集計が一致することも確かめます。
</details>
