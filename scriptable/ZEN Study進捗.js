// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: deep-green; icon-glyph: graduation-cap;

// ZEN Study のレポート進捗をウィジェットに表示する。読み取り専用（GET のみ）で、
// ログイン Cookie は Scriptable のキーチェーンにだけ保存する。

const API = "https://api.nnn.ed.nico/v2/dashboard/report_progresses";
const WEB_ORIGIN = "https://www.nnn.ed.nico";
const KEYCHAIN_KEY = "zenstudy.cookie";
const CACHE_FILE = "zenstudy-progress-cache.json";
const REFRESH_MINUTES = 30;

const ACCENT = new Color("#30d6b2");
const WARN = new Color("#ff9f0a");
const ALERT = new Color("#ff453a");
const DONE = new Color("#8e8e93");
const TRACK = new Color("#8e8e93", 0.28);
const BG = Color.dynamic(new Color("#ffffff"), new Color("#1c1c1e"));
const TEXT = Color.dynamic(new Color("#1c1c1e"), new Color("#f2f2f7"));
const SUB = Color.dynamic(new Color("#6e6e73"), new Color("#98989d"));

class AuthError extends Error {}

// MARK: - 通信

function storedCookie() {
  return Keychain.contains(KEYCHAIN_KEY) ? Keychain.get(KEYCHAIN_KEY) : "";
}

function withTimeout(promise, seconds) {
  return Promise.race([promise, new Promise((_, reject) =>
    Timer.schedule(seconds * 1000, false, () => reject(new Error("時間切れです"))))]);
}

async function getJSON(path, cookie) {
  if (!cookie) throw new AuthError("ログインが必要です");
  const req = new Request(API + path);
  req.headers = { Cookie: cookie, Accept: "application/json" };
  req.timeoutInterval = 20;
  const body = await req.loadString();
  const status = req.response ? req.response.statusCode : 0;
  if (status === 401 || status === 403) throw new AuthError("ログインが切れています");
  if (status < 200 || status >= 300) throw new Error(`サーバーエラー (${status})`);
  return JSON.parse(body);
}

// MARK: - 集計

const deadlineOf = m => new Date(m.earliest_report_deadline || m.deadline || 0);
const testsDone = m => (m.passed_assessment_test_count || 0) >= (m.total_assessment_test || 0);
const isDone = m => m.passed_chapter_count >= m.total_chapter_count && testsDone(m);

function pickMonth(summaries, now) {
  const sorted = [...summaries].sort((a, b) => a.year - b.year || a.month - b.month);
  const open = m => deadlineOf(m) >= now;
  return sorted.find(m => open(m) && !isDone(m)) || sorted.find(open) || sorted[sorted.length - 1];
}

function summarize(overview, detail, now) {
  const summaries = overview.monthly_summaries || [];
  if (!summaries.length) throw new Error("レポートがありません");
  const current = pickMonth(summaries, now);
  const sorted = [...summaries].sort((a, b) => a.year - b.year || a.month - b.month);
  const next = sorted[sorted.indexOf(current) + 1] || null;
  const passedTestIDs = new Set((detail?.passed_assessment_tests || []).map(t => t.assessment_test_id));
  const groups = detail?.deadline_groups || [];
  const remaining = groups.flatMap(g => g.chapters || [])
    .filter(c => !c.exempted && c.passed_count < c.total_count)
    .map(c => ({ subject: c.subject_category_title || c.course_title, title: c.chapter_title,
                 passed: c.passed_count, total: c.total_count }))
    .sort((a, b) => (a.total - a.passed) - (b.total - b.passed));
  const tests = groups.flatMap(g => g.assessment_tests || [])
    .filter(t => !t.exempted && !passedTestIDs.has(t.assessment_test_id))
    .map(t => ({ subject: t.subject_category_title || t.course_title, title: t.title,
                 answered: t.total_answered_question || 0, total: t.total_question || 0 }));
  const month = m => m && ({
    year: m.year, month: m.month, deadline: deadlineOf(m).toISOString(),
    chaptersPassed: m.passed_chapter_count, chaptersTotal: m.total_chapter_count,
    testsPassed: m.passed_assessment_test_count || 0, testsTotal: m.total_assessment_test || 0,
  });
  return {
    fetchedAt: now.toISOString(),
    current: { ...month(current),
               materialsPassed: detail?.passed_material_count ?? null,
               materialsTotal: detail?.total_material_count ?? null },
    next: month(next),
    remaining, tests,
    overdue: sorted.filter(m => deadlineOf(m) < now && !isDone(m)).length,
    year: { passed: summaries.reduce((s, m) => s + m.passed_chapter_count, 0),
            total: summaries.reduce((s, m) => s + m.total_chapter_count, 0) },
  };
}

async function fetchProgress(now, cookie = storedCookie()) {
  const overview = await getJSON("", cookie);
  const current = pickMonth(overview.monthly_summaries || [], now);
  let detail = null;
  if (current) {
    const service = encodeURIComponent(overview.service || "basic");
    try { detail = await getJSON(`/monthly/${current.year}/${current.month}?service=${service}`, cookie); }
    catch (error) { if (error instanceof AuthError) throw error; }
  }
  return summarize(overview, detail, now);
}

// MARK: - キャッシュ（直近の成功結果）

// アプリとウィジェットの両方から確実に読めるよう iCloud に置く（進捗だけで秘密情報は含まない）。
function cacheStore() {
  try { return FileManager.iCloud(); } catch { return FileManager.local(); }
}
function cachePath(fm) {
  return fm.joinPath(fm.documentsDirectory(), CACHE_FILE);
}
async function readCache() {
  for (const fm of [cacheStore(), FileManager.local()]) {
    try {
      const path = cachePath(fm);
      if (!fm.fileExists(path)) continue;
      if (fm.isFileStoredIniCloud && fm.isFileStoredIniCloud(path) && !fm.isFileDownloaded(path)) await fm.downloadFileFromiCloud(path);
      return JSON.parse(fm.readString(path));
    } catch {}
  }
  return null;
}
function writeCache(data) {
  try { const fm = cacheStore(); fm.writeString(cachePath(fm), JSON.stringify(data)); } catch {}
}

// MARK: - 表示用の文字列

const ratio = (a, b) => (b > 0 ? Math.min(1, a / b) : 1);

function timeLeft(iso, now) {
  const ms = new Date(iso) - now;
  if (ms < 0) return "期限切れ";
  const day = d => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const days = Math.round((day(new Date(iso)) - day(now)) / 86400000);
  if (days <= 0) return `今日まで（あと${Math.max(1, Math.floor(ms / 3600000))}時間）`;
  return `あと${days}日`;
}
function shortDate(iso) {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}
function clockTime(iso) {
  const d = new Date(iso);
  return `${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}
function progressColor(data, now) {
  const c = data.current;
  if (c.chaptersPassed >= c.chaptersTotal && c.testsPassed >= c.testsTotal) return DONE;
  const ms = new Date(c.deadline) - now;
  if (ms < 0) return ALERT;
  return ms < 3 * 86400000 ? WARN : ACCENT;
}
function materialsText(c) {
  if (c.materialsTotal == null) return null;
  return `教材 ${Math.round(ratio(c.materialsPassed, c.materialsTotal) * 100)}%`;
}

// MARK: - 描画部品

function barImage(width, height, value, color) {
  const ctx = new DrawContext();
  ctx.size = new Size(width, height);
  ctx.opaque = false;
  ctx.respectScreenScale = true;
  const track = new Path();
  track.addRoundedRect(new Rect(0, 0, width, height), height / 2, height / 2);
  ctx.addPath(track);
  ctx.setFillColor(TRACK);
  ctx.fillPath();
  if (value > 0) {
    const fill = new Path();
    const w = Math.max(height, width * value);
    fill.addRoundedRect(new Rect(0, 0, w, height), height / 2, height / 2);
    ctx.addPath(fill);
    ctx.setFillColor(color);
    ctx.fillPath();
  }
  return ctx.getImage();
}

function ringImage(size, value, color) {
  const ctx = new DrawContext();
  ctx.size = new Size(size, size);
  ctx.opaque = false;
  ctx.respectScreenScale = true;
  const line = size * 0.11;
  const r = (size - line) / 2;
  const arc = (from, to) => {
    const points = [];
    const steps = Math.max(2, Math.ceil(80 * (to - from)));
    for (let i = 0; i <= steps; i++) {
      const a = -Math.PI / 2 + 2 * Math.PI * (from + (to - from) * i / steps);
      points.push(new Point(size / 2 + r * Math.cos(a), size / 2 + r * Math.sin(a)));
    }
    const path = new Path();
    path.addLines(points);
    return path;
  };
  ctx.setLineWidth(line);
  ctx.addPath(arc(0, 1));
  ctx.setStrokeColor(TRACK);
  ctx.strokePath();
  if (value > 0) {
    ctx.addPath(arc(0, value));
    ctx.setStrokeColor(color);
    ctx.strokePath();
  }
  return ctx.getImage();
}

function text(stack, value, font, color = TEXT, lines = 1) {
  const t = stack.addText(value);
  t.font = font;
  t.textColor = color;
  t.lineLimit = lines;
  t.minimumScaleFactor = 0.7;
  return t;
}

function row(stack, spacing = 4) {
  const r = stack.addStack();
  r.layoutHorizontally();
  r.centerAlignContent();
  r.spacing = spacing;
  return r;
}

function footer(stack, data, note) {
  const r = row(stack);
  if (note) text(r, note, Font.mediumSystemFont(10), WARN);
  r.addSpacer();
  text(r, `${clockTime(data.fetchedAt)} 更新`, Font.systemFont(10), SUB);
}

// MARK: - ウィジェット

function headline(stack, data, now, big) {
  const c = data.current;
  const color = progressColor(data, now);
  const top = row(stack);
  text(top, `${c.month}月レポート`, Font.semiboldSystemFont(big ? 15 : 13));
  top.addSpacer();
  text(top, timeLeft(c.deadline, now), Font.mediumSystemFont(11), color === ACCENT ? SUB : color);
  stack.addSpacer(4);
  const count = row(stack, 3);
  count.bottomAlignContent();
  text(count, `${c.chaptersPassed}`, Font.boldRoundedSystemFont(big ? 34 : 30));
  text(count, `/ ${c.chaptersTotal}`, Font.mediumRoundedSystemFont(15), SUB);
  if (c.testsTotal > 0) {
    count.addSpacer(6);
    text(count, `テスト ${c.testsPassed}/${c.testsTotal}`, Font.mediumSystemFont(11), SUB);
  }
  return color;
}

// 年間（6月〜12月分の合計）の進み。月のゲージと同じ幅・太さで真下に揃え、色だけ控えめにする。
function yearGauge(stack, data, width, height, big) {
  const r = row(stack, 6);
  r.size = new Size(width, 0);
  text(r, "年間", Font.semiboldSystemFont(big ? 12 : 11), SUB);
  r.addSpacer();
  text(r, `${data.year.passed}/${data.year.total}`, Font.regularMonospacedSystemFont(big ? 11 : 10), SUB);
  stack.addSpacer(3);
  stack.addImage(barImage(width, height, ratio(data.year.passed, data.year.total), SUB)).imageSize = new Size(width, height);
}

function buildSmall(w, data, now, note) {
  const c = data.current;
  const color = headline(w, data, now, false);
  w.addSpacer(6);
  w.addImage(barImage(130, 6, ratio(c.chaptersPassed, c.chaptersTotal), color)).imageSize = new Size(130, 6);
  w.addSpacer(6);
  text(w, [`期限 ${shortDate(c.deadline)}`, materialsText(c)].filter(Boolean).join(" · "), Font.systemFont(11), SUB);
  w.addSpacer(5);
  yearGauge(w, data, 130, 6, false);
  w.addSpacer();
  footer(w, data, note);
}

function remainingList(stack, data, limit) {
  const items = data.remaining.slice(0, limit);
  for (const item of items) {
    const r = row(stack, 6);
    text(r, item.subject, Font.mediumSystemFont(12));
    r.addSpacer();
    text(r, `${item.passed}/${item.total}`, Font.regularMonospacedSystemFont(11), SUB);
  }
  const more = data.remaining.length - items.length;
  const extra = [more > 0 ? `ほか${more}件` : null, data.tests.length ? `テスト${data.tests.length}件` : null].filter(Boolean);
  if (extra.length) text(stack, extra.join(" · "), Font.systemFont(11), SUB);
  if (!data.remaining.length && !data.tests.length) text(stack, "今月分は完了しています", Font.mediumSystemFont(12), SUB);
}

function buildMedium(w, data, now, note) {
  const c = data.current;
  const body = w.addStack();
  body.layoutHorizontally();
  body.spacing = 14;
  const left = body.addStack();
  left.layoutVertically();
  left.size = new Size(140, 0);
  const color = headline(left, data, now, false);
  left.addSpacer(6);
  left.addImage(barImage(140, 6, ratio(c.chaptersPassed, c.chaptersTotal), color)).imageSize = new Size(140, 6);
  left.addSpacer(6);
  text(left, [`期限 ${shortDate(c.deadline)}`, materialsText(c)].filter(Boolean).join(" · "), Font.systemFont(11), SUB);
  left.addSpacer(6);
  yearGauge(left, data, 140, 6, false);
  const right = body.addStack();
  right.layoutVertically();
  right.spacing = 3;
  text(right, "残り", Font.semiboldSystemFont(11), SUB);
  remainingList(right, data, 4);
  w.addSpacer();
  footer(w, data, note);
}

function buildLarge(w, data, now, note) {
  const c = data.current;
  const color = headline(w, data, now, true);
  w.addSpacer(8);
  w.addImage(barImage(300, 8, ratio(c.chaptersPassed, c.chaptersTotal), color)).imageSize = new Size(300, 8);
  w.addSpacer(6);
  text(w, [`期限 ${shortDate(c.deadline)}`, materialsText(c)].filter(Boolean).join(" · "), Font.systemFont(12), SUB);
  w.addSpacer(8);
  yearGauge(w, data, 300, 8, true);
  w.addSpacer(10);
  text(w, "残りの教科", Font.semiboldSystemFont(12), SUB);
  w.addSpacer(4);
  // 年間ゲージの分を空けるため、教科とテストは合わせて5行まで。
  const testRows = Math.min(data.tests.length, 2);
  const shown = 5 - testRows;
  for (const item of data.remaining.slice(0, shown)) {
    const r = row(w, 8);
    const label = r.addStack();
    label.layoutVertically();
    text(label, item.subject, Font.mediumSystemFont(13));
    text(label, item.title, Font.systemFont(10), SUB);
    r.addSpacer();
    r.addImage(barImage(56, 4, ratio(item.passed, item.total), ACCENT)).imageSize = new Size(56, 4);
    text(r, `${item.passed}/${item.total}`, Font.regularMonospacedSystemFont(11), SUB);
    w.addSpacer(3);
  }
  for (const t of data.tests.slice(0, testRows)) {
    const r = row(w, 6);
    text(r, `${t.subject} テスト`, Font.mediumSystemFont(13));
    r.addSpacer();
    text(r, `${t.answered}/${t.total}問`, Font.regularMonospacedSystemFont(11), SUB);
  }
  const hidden = [data.remaining.length > shown ? `ほか${data.remaining.length - shown}件` : null,
                  data.tests.length > testRows ? `テストほか${data.tests.length - testRows}件` : null].filter(Boolean);
  if (hidden.length) text(w, hidden.join(" · "), Font.systemFont(11), SUB);
  if (!data.remaining.length && !data.tests.length) text(w, "今月分は完了しています", Font.mediumSystemFont(13), SUB);
  w.addSpacer();
  const lines = [];
  if (data.next) lines.push(`次は${data.next.month}月 ${data.next.chaptersPassed}/${data.next.chaptersTotal}`);
  if (data.overdue) lines.push(`未完了の過去月 ${data.overdue}`);
  if (lines.length) text(w, lines.join(" · "), Font.systemFont(11), data.overdue ? ALERT : SUB);
  w.addSpacer(4);
  footer(w, data, note);
}

function buildAccessory(w, family, data, now, note) {
  const c = data.current;
  const value = ratio(c.chaptersPassed, c.chaptersTotal);
  if (family === "accessoryInline") {
    text(w, `${c.month}月 ${c.chaptersPassed}/${c.chaptersTotal} · ${timeLeft(c.deadline, now)}`, Font.systemFont(12));
  } else if (family === "accessoryCircular") {
    const stack = w.addStack();
    stack.size = new Size(58, 58);
    stack.backgroundImage = ringImage(58, value, Color.white());
    stack.layoutVertically();
    stack.centerAlignContent();
    const top = row(stack);
    top.addSpacer();
    text(top, `${c.chaptersPassed}/${c.chaptersTotal}`, Font.boldRoundedSystemFont(13), Color.white());
    top.addSpacer();
  } else {
    text(w, `${c.month}月レポート ${c.chaptersPassed}/${c.chaptersTotal}`, Font.semiboldSystemFont(13), Color.white());
    w.addSpacer(3);
    w.addImage(barImage(150, 5, value, Color.white())).imageSize = new Size(150, 5);
    w.addSpacer(3);
    text(w, note || [timeLeft(c.deadline, now), materialsText(c)].filter(Boolean).join(" · "), Font.systemFont(11), Color.white());
  }
}

function buildMessage(w, title, detail) {
  text(w, "ZEN Study", Font.semiboldSystemFont(13), SUB);
  w.addSpacer(6);
  text(w, title, Font.semiboldSystemFont(14), TEXT, 2);
  w.addSpacer(4);
  text(w, detail, Font.systemFont(11), SUB, 3);
}

async function buildWidget(family) {
  const now = new Date();
  const w = new ListWidget();
  // A web URL here gets handed to the ZEN Study app by iOS, so tapping stays inside Scriptable.
  w.url = `scriptable:///run/${encodeURIComponent(Script.name())}?action=preview`;
  w.refreshAfterDate = new Date(now.getTime() + REFRESH_MINUTES * 60000);
  const accessory = family && family.startsWith("accessory");
  if (!accessory) {
    w.backgroundColor = BG;
    w.setPadding(14, 16, 12, 16);
  }
  let data = null;
  let note = null;
  try {
    data = await fetchProgress(now);
    writeCache(data);
  } catch (error) {
    data = await readCache();
    const auth = error instanceof AuthError;
    const hadLogin = !!storedCookie();
    // ログインの問題ならタップでそのままログイン画面を開く。
    if (auth) w.url = `scriptable:///run/${encodeURIComponent(Script.name())}?action=login`;
    note = auth ? (hadLogin ? "ログインが切れています" : "ログインが必要です") : "更新できませんでした";
    if (!data) {
      if (accessory) text(w, auth ? `ZEN Study ${hadLogin ? "ログイン切れ" : "要ログイン"}` : "ZEN Study 取得失敗", Font.systemFont(12));
      else if (auth) buildMessage(w, hadLogin ? "ログインが切れています" : "ログインが必要です", "タップしてログインしてください。");
      else buildMessage(w, note, String(error.message || error));
      return w;
    }
  }
  if (accessory) buildAccessory(w, family, data, now, note);
  else if (family === "small") buildSmall(w, data, now, note);
  else if (family === "large") buildLarge(w, data, now, note);
  else buildMedium(w, data, now, note);
  return w;
}

// MARK: - アプリ内メニュー

async function showMessage(title, message) {
  const alert = new Alert();
  alert.title = title;
  alert.message = message;
  alert.addAction("OK");
  await alert.present();
}

// PC の zengauge がログイン後に表示する QR コードから開かれる（scriptable:///run/...?action=import&cookie=...）。
// 読み込んだログイン情報で実際に取得できたときだけ保存する。
async function importFromQR(value) {
  // Scriptable normally decodes query parameters already; decode again only if it did not.
  let cookie = String(value || "").trim();
  if (/%3D/i.test(cookie)) { try { cookie = decodeURIComponent(cookie); } catch {} }
  if (!/(^|;\s*)_zane_session=[^;]+/.test(cookie)) {
    await showMessage("読み込めませんでした", "QR コードの中身が ZEN Study のログイン情報ではありませんでした。");
    return;
  }
  const confirm = new Alert();
  confirm.title = "PC のログインを使いますか？";
  confirm.message = "QR コードから読み込んだ ZEN Study のログイン情報を、この iPhone に保存します。";
  confirm.addAction("保存する");
  confirm.addCancelAction("やめる");
  if (await confirm.present() < 0) return;
  try {
    const data = await fetchProgress(new Date(), cookie);
    Keychain.set(KEYCHAIN_KEY, cookie);
    writeCache(data);
    await showMessage("ログインできました", `${progressLine(data)}\n\nウィジェットは次の更新（30分以内）から反映されます。PC はもう閉じて大丈夫です。`);
  } catch (error) {
    await showMessage("ログインできませんでした", error instanceof AuthError
      ? "このログイン情報はもう使えません。PC でもう一度ログインして、新しい QR コードを読み取ってください。"
      : String(error.message || error));
  }
}

// MARK: - スマホでログイン
// ZEN Study のログインは www.nnn.ed.nico/auth/n_lobby → N Lobby → /auth/n_lobby/callback の順に進む。
// 最初と最後は Scriptable 自身（Request）が行い、ブラウザには N Lobby のログイン画面だけを出す。
// こうするとブラウザ内に閉じ込められる HttpOnly のセッション Cookie を直接受け取れるので、
// キーチェーンに保存してウィジェットが自分で更新できる。パスワードはスクリプトを通らない。

const LOGIN_START = WEB_ORIGIN + "/auth/n_lobby";
const LOGIN_CALLBACK = WEB_ORIGIN + "/auth/n_lobby/callback";

function headerValue(headers, name) {
  const key = Object.keys(headers || {}).find(k => k.toLowerCase() === name);
  return key ? headers[key] : null;
}
function cookieJar(cookies, base = {}) {
  const jar = { ...base };
  for (const c of cookies || []) {
    if (c && c.name && (!c.domain || /nnn\.ed\.nico$/.test(c.domain))) jar[c.name] = c.value;
  }
  return jar;
}
const cookieHeader = jar => Object.entries(jar).map(([k, v]) => `${k}=${v}`).join("; ");

// 転送を追わずに 1 回だけ GET する（転送先と Set-Cookie を自分で受け取るため）。
async function getOnce(url, jar) {
  const req = new Request(url);
  req.onRedirect = () => null;
  req.timeoutInterval = 20;
  if (jar) req.headers = { Cookie: cookieHeader(jar) };
  await req.load();
  return req.response || {};
}

async function startLogin() {
  const res = await getOnce(LOGIN_START);
  const jar = cookieJar(res.cookies);
  let url = headerValue(res.headers, "location");
  if (url && url.startsWith("/")) url = WEB_ORIGIN + url;
  if (!url || !jar._zane_session) {
    const missing = [url ? null : "転送先なし", jar._zane_session ? null : "Cookieなし"].filter(Boolean).join("・");
    throw new Error(`ログインを始められませんでした（${res.statusCode || "応答なし"}・${missing}）`);
  }
  return { url, jar };
}

async function finishLogin(callbackURL, jar) {
  const res = await getOnce(callbackURL, jar);
  const cookie = cookieHeader(cookieJar(res.cookies, jar));
  let data;
  try { data = await fetchProgress(new Date(), cookie); }
  catch (error) {
    if (error instanceof AuthError) throw new Error(`ZEN Study がログインを受け付けませんでした（${res.statusCode || "応答なし"}）。もう一度試してください。`);
    throw error;
  }
  Keychain.set(KEYCHAIN_KEY, cookie);
  writeCache(data);
  return data;
}

const escapeHTML = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
function resultPage(title, message) {
  return `<meta name="viewport" content="width=device-width"><meta name="color-scheme" content="light dark">
<body style="font:17px -apple-system;padding:48px 24px;text-align:center">
<h2>${escapeHTML(title)}</h2><p>${escapeHTML(message).replace(/\n/g, "<br>")}</p>
<p style="color:gray">左上のボタンで閉じてください。</p></body>`;
}
const progressLine = data => `${data.current.month}月レポート ${data.current.chaptersPassed}/${data.current.chaptersTotal}`;

async function loginOnPhone() {
  let login;
  try { login = await startLogin(); }
  catch (error) { await showMessage("ログインできませんでした", String(error.message || error)); return; }
  const view = new WebView();
  let result = null;
  // N Lobby が ZEN Study へ戻そうとした瞬間に止め、その URL を Scriptable 側で開く。
  view.shouldAllowRequest = request => {
    const url = String(request.url || "");
    if (!url.startsWith(LOGIN_CALLBACK)) return true;
    if (!result) {
      result = finishLogin(url, login.jar);
      result.then(data => view.loadHTML(resultPage("ログインできました", progressLine(data))),
                  error => view.loadHTML(resultPage("ログインできませんでした", String(error.message || error))))
        .catch(() => {});
    }
    return false;
  };
  // N Lobby にログイン済みならここで戻ってくるので、画面を出さずに終わる。
  try { await withTimeout(view.loadURL(login.url), 30); } catch {}
  if (!result) await view.present(true);
  if (!result) {
    await showMessage("ログインが終わっていません", "N Lobby でログインする前に閉じられました。もう一度試してください。");
    return;
  }
  try {
    const data = await result;
    await showMessage("ログインできました", `${progressLine(data)}\n\nウィジェットは次の更新（30分以内）から反映されます。`);
  } catch (error) {
    await showMessage("ログインできませんでした", String(error.message || error));
  }
}

async function runInApp() {
  const menu = new Alert();
  menu.title = "ZEN Study 進捗";
  menu.message = storedCookie()
    ? "ログイン済みです。切れたら「スマホでログイン」か、PC の QR コードで入り直せます。"
    : "「スマホでログイン」を選ぶか、PC の zengauge が表示する QR コードを iPhone のカメラで読み取ってください。";
  const actions = [
    ["スマホでログイン", loginOnPhone],
    ["プレビュー（中）", async () => (await buildWidget("medium")).presentMedium()],
    ["プレビュー（大）", async () => (await buildWidget("large")).presentLarge()],
    ["プレビュー（小）", async () => (await buildWidget("small")).presentSmall()],
    ["ログイン情報を削除", async () => { if (Keychain.contains(KEYCHAIN_KEY)) Keychain.remove(KEYCHAIN_KEY); }],
  ];
  for (const [title] of actions) menu.addAction(title);
  menu.addCancelAction("閉じる");
  const choice = await menu.presentSheet();
  if (choice >= 0) await actions[choice][1]();
}

if (config.runsInWidget || config.runsInAccessoryWidget) {
  Script.setWidget(await buildWidget(config.widgetFamily));
} else if (args.queryParameters && args.queryParameters.action === "preview") {
  (await buildWidget("large")).presentLarge();
} else if (args.queryParameters && args.queryParameters.action === "login") {
  await loginOnPhone();
} else if (args.queryParameters && args.queryParameters.action === "import") {
  await importFromQR(args.queryParameters.cookie);
} else {
  await runInApp();
}
Script.complete();
