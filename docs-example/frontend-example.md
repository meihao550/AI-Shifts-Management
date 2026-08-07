# フロントエンド ソースコード解説（Vue.js 初心者向け）

このドキュメントは、`frontend/` ディレクトリのソースコードが「どのように動いているか」を、
**Vue.js や TypeScript を知らない人でも読めるように** 解説したものです。

対象読者:

- プログラミングの基礎（変数・関数）はなんとなく分かるが、Vue.js は初めての人
- 「このアプリの画面がどうやって表示され、どうやってサーバーとやり取りしているのか」を知りたい人

---

## 0. まず結論：このアプリは何をしているか

このフロントエンドは **「AIシフト管理」アプリの画面（見た目＋操作）** を担当しています。

- 従業員（アルバイト・社員）の一覧を管理する
- 「この日は休みたい／入りたい」という希望を登録する
- AI にシフト表を自動生成させる
- 人件費（給料の合計）を計算して表示する
- シフト表を PDF / Excel で印刷・ダウンロードする

画面（フロントエンド）は **計算やデータ保存を自分ではしません**。
実際のデータは別の「サーバー（バックエンド）」が持っていて、
フロントエンドは **サーバーに「ちょうだい」「保存して」とお願いする** だけです。

```
[ブラウザ(この画面)]  ←→  [バックエンドAPI]  ←→  [データベース]
   Vue.js で作成            計算・保存を担当        データの倉庫
```

---

## 1. そもそも Vue.js とは？（超入門）

### 1-1. Vue.js は「画面を組み立てる道具」

昔ながらのウェブサイトは、HTML（骨組み）・CSS（見た目）・JavaScript（動き）を
バラバラに書いていました。

Vue.js は、この 3 つを **1 つのファイル（`.vue` ファイ）にまとめて書ける** 道具です。
1 つの `.vue` ファイルは「部品（コンポーネント）」と呼ばれ、次の 3 ブロックでできています。

```vue
<script setup lang="ts">
  // ① ロジック：データや処理を書く場所（JavaScript / TypeScript）
</script>

<template>
  <!-- ② 見た目：画面に表示する HTML を書く場所 -->
</template>

<style scoped>
  /* ③ デザイン：色や大きさなどの CSS を書く場所 */
</style>
```

このプロジェクトの `.vue` ファイルは、ほぼすべてこの形をしています。

### 1-2. Vue.js の一番大事な特徴：「リアクティブ」

Vue.js の最大の便利ポイントは **「データが変わると、画面が自動で書き換わる」** ことです。

たとえば「ローディング中かどうか」を表す `loading` という箱（変数）があるとします。

- `loading` を `true` にする → 画面にクルクル回るアイコンが自動で出る
- `loading` を `false` にする → クルクルが自動で消える

**プログラマが「画面を書き換えろ」と命令しなくても、データを変えるだけで画面が追従する**。
これがリアクティブです。このコードのあちこちに出てくる `ref(...)` や `computed(...)` は、
この「データが変わったら画面も変わる箱」を作るための道具です。

| 書き方 | 意味 | たとえ |
|--------|------|--------|
| `ref(0)` | 中身を変えられる箱 | ホワイトボード（書き換え可能） |
| `computed(() => ...)` | 他の箱から自動計算される箱 | 「合計」欄（元の数字が変わると自動再計算） |

---

## 2. プロジェクト全体の地図

`frontend/src/` の中身と、それぞれの役割です。

```
frontend/
├── index.html            ← 一番最初に読み込まれる土台のHTML
└── src/
    ├── main.ts           ← アプリの起動スイッチ（一番最初に動く）
    ├── App.vue           ← すべての画面の一番外側の枠
    │
    ├── router/           ← 「どのURLでどの画面を出すか」の地図
    │   └── index.ts
    │
    ├── views/            ← 1画面まるごと＝ページ（URLごとに1つ）
    │   ├── LoginView.vue        ログイン画面
    │   ├── DashboardView.vue    ダッシュボード（トップ）
    │   ├── ShiftTableView.vue   シフト表画面
    │   ├── EmployeesView.vue    従業員管理画面
    │   ├── RulesView.vue        ルール設定画面
    │   ├── PayrollView.vue      人件費計算画面
    │   ├── PrintPreviewView.vue 印刷プレビュー画面
    │   └── AuthCallbackView.vue ログイン後の中継画面
    │
    ├── components/       ← 複数の画面で使い回す部品
    │   ├── HeaderBar.vue         画面上部のメニュー
    │   └── AvailabilityCalendar.vue  休日/希望日カレンダー
    │
    ├── stores/           ← データの保管庫（アプリ全体で共有する情報）
    │   ├── auth.ts        ログイン情報
    │   ├── employee.ts    従業員データ
    │   ├── rule.ts        シフトのルール
    │   └── shift.ts       シフト・人件費データ
    │
    ├── api/              ← サーバーと通信する係
    │   └── client.ts
    │
    └── types/            ← データの「形」の定義書
        └── index.ts
```

**大まかな役割分担**を一言でいうと：

- **views** = ページ（見た目の主役）
- **components** = 使い回す部品
- **stores** = データの倉庫
- **api** = サーバーへの電話係
- **router** = URL と画面をつなぐ案内係
- **types** = データの設計図

---

## 3. アプリが起動するまでの流れ（順番に追う）

ユーザーがブラウザでアプリを開くと、次の順番でコードが動きます。

### ステップ①：`index.html`（土台）

```html
<div id="app"></div>
<script type="module" src="/src/main.ts"></script>
```

`<div id="app"></div>` という **空っぽの箱** が 1 つあるだけです。
Vue.js はこの空箱の中に、画面をまるごと作って差し込みます。
そして `main.ts` を呼び出します。

### ステップ②：`src/main.ts`（起動スイッチ）

```ts
const app = createApp(App)      // App.vue を土台にアプリを作る
app.use(createPinia())          // データ倉庫(Pinia)を使えるようにする
app.use(router)                 // URL振り分け(router)を使えるようにする
app.use(naive)                  // デザイン部品集(naive-ui)を使えるようにする
app.mount('#app')               // 上の空箱(#app)に画面を差し込む
```

ここで **アプリに 3 つの機能を追加** しています。

1. **Pinia**（ピニア）… データ倉庫。詳しくは第 6 章
2. **router**（ルーター）… URL ごとに画面を切り替える案内係。第 5 章
3. **naive-ui**（ナイーブ UI）… ボタン・表・カレンダーなど、
   **既製のきれいな部品セット**。`N` で始まる部品（`NButton` など）はすべてこれ。

最後の `app.mount('#app')` で、実際に画面が表示されます。

### ステップ③：`src/App.vue`（一番外側の枠）

すべての画面はこの `App.vue` の内側に表示されます。中身の要点：

```vue
<template>
  <n-config-provider :locale="jaJP">   <!-- 日本語設定 -->
    ...
      <HeaderBar v-if="showHeader" />   <!-- 上部メニュー（ログイン時だけ表示） -->
      <main>
        <router-view />                 <!-- ★ここに各ページが差し替わって出る★ -->
      </main>
    ...
  </n-config-provider>
</template>
```

一番大事なのは **`<router-view />`** です。
ここが「ページの表示場所」で、URL に応じて中身（ダッシュボード画面／シフト表画面…）が
入れ替わります。**枠（ヘッダー等）はそのままで、中身だけ差し替わる** のがポイントです。

また、起動直後に次の処理が動きます。

```ts
onMounted(async () => {
  await auth.restore()   // 「前回ログインしたままか？」をサーバーに確認
})
```

`onMounted` は **「この部品が画面に表示された瞬間に 1 回だけ実行する」** という予約です。
ここでログイン状態を復元しています。

---

## 4. `.vue` ファイルの読み方（テンプレートの記号）

`<template>` の中には、普通の HTML に加えて Vue.js 独自の記号が出てきます。
初めて見ると呪文に見えるので、代表的なものを表にします。

| 記号 | 名前 | 意味 | 例 |
|------|------|------|-----|
| `{{ 変数 }}` | 補間 | 変数の中身を文字として表示 | `{{ emp.name }}` → 従業員の名前 |
| `v-if="条件"` | 条件表示 | 条件が正のときだけ表示 | `v-if="shift"` シフトがある時だけ表示 |
| `v-else` | 反対 | `v-if` が偽のとき表示 | — |
| `v-for="x in list"` | 繰り返し | リストの数だけ繰り返し表示 | `v-for="emp in employees"` 従業員の数だけ行を作る |
| `:属性="変数"` | バインド | HTML属性に変数を渡す | `:src="user.picture_url"` 画像URLを渡す |
| `@click="関数"` | イベント | クリック時に関数を実行 | `@click="save"` 押したら保存 |
| `v-model="変数"` | 双方向 | 入力欄と変数を連動させる | 下で詳しく説明 |

### とくに重要：`v-model`（双方向バインディング）

```vue
<NInput v-model:value="devEmail" />
```

これは **「入力欄」と「変数 `devEmail`」を紐づける** 書き方です。

- ユーザーが入力欄に文字を打つ → `devEmail` の中身が自動で変わる
- コードで `devEmail` を変える → 入力欄の表示も自動で変わる

**「入力欄の値を取り出す／セットする」処理を自分で書かなくていい**、とても便利な仕組みです。
フォーム（従業員登録など）でよく使われています。

### `v-for` の実例（シフト表）

`ShiftTableView.vue` の表は、`v-for` の二重ループでできています。

```vue
<tr v-for="emp in employeeStore.employees" :key="emp.id">   <!-- 従業員ごとに「行」 -->
  <td>{{ emp.name }}</td>
  <td v-for="d in days" :key="d.getTime()">                 <!-- 日付ごとに「列」 -->
    {{ assignmentsFor(emp.id, d).label }}                   <!-- その人・その日の担当 -->
  </td>
</tr>
```

「従業員 25 人 × その月の日数」の表を、たった数行のループで組み立てています。
手で `<td>` を並べる必要はありません。データが増えれば行・列も自動で増えます。

> `:key="..."` は Vue.js が「どれがどれか」を見分けるための目印です。
> `v-for` を使うときは付ける決まりになっています（中身は気にしなくてOK）。

---

## 5. 画面の切り替え：ルーター（`router/index.ts`）

「どの URL のとき、どの画面（View）を表示するか」を決めているのがルーターです。

```ts
const routes = [
  { path: '/login',     component: () => import('@/views/LoginView.vue') },
  { path: '/dashboard', component: () => import('@/views/DashboardView.vue') },
  { path: '/shift',     component: () => import('@/views/ShiftTableView.vue') },
  { path: '/employees', component: () => import('@/views/EmployeesView.vue'),
    meta: { adminOnly: true } },   // ← 管理者しか入れない印
  ...
]
```

`path`（URL）と `component`（表示する画面）の対応表です。
たとえば `http://～/shift` を開くと `ShiftTableView.vue` が `<router-view />` の場所に出ます。

### 通せんぼ機能（ナビゲーションガード）

ルーターには **「画面を表示する前のチェック係」** があります。

```ts
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  // ① 前回ログイン状態をまだ確認してなければ確認する
  if (!auth.hydrated) { await auth.restore() }

  // ② ログインが必要な画面なのに未ログインなら → ログイン画面へ追い返す
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // ③ 管理者専用の画面に一般社員が来たら → ダッシュボードへ戻す
  if (to.meta.adminOnly && auth.user?.role !== 'admin') {
    return { name: 'dashboard' }
  }
})
```

`beforeEach` は **「どの画面に移動するときも、表示前に必ず通る関所」** です。
ここで「ログインしてる？」「管理者権限ある？」を確認し、
ダメなら別の画面へ **強制的に送り返します**。
これで、URL を直接打ち込んでも権限のない画面には入れません。

---

## 6. データの倉庫：ストア（Pinia）

### 6-1. なぜ倉庫が必要か

複数の画面が **同じデータ** を使いたいことがあります。
たとえば「ログインしているユーザーの名前」は、ヘッダーにもダッシュボードにも出ます。

そのたびにサーバーへ聞きに行くのは無駄なので、
**アプリ全体で共有する 1 個の倉庫（ストア）** に置いておきます。
これを実現するのが **Pinia（ピニア）** です。

このプロジェクトには 4 つの倉庫があります。

| ストア | 保管しているもの |
|--------|------------------|
| `auth.ts` | ログイン中のユーザー情報 |
| `employee.ts` | 従業員の一覧 |
| `rule.ts` | シフトパターン・必要人員のルール |
| `shift.ts` | シフト表・人件費のデータ |

### 6-2. ストアの中身（`auth.ts` を例に）

```ts
export const useAuthStore = defineStore('auth', {
  state: () => ({ user: null, hydrated: false }),   // ① データ本体
  getters: {                                        // ② データから計算する項目
    isAuthenticated: (s) => !!s.user,               //   ユーザーがいれば「ログイン中」
    isAdmin: (s) => s.user?.role === 'admin',       //   役割がadminなら「管理者」
  },
  actions: {                                        // ③ データを操作する処理
    async restore() { ... },     // 保存済みトークンでログイン状態を復元
    async devLogin(email, name) { ... },  // 開発用ログイン
    logout() { ... },            // ログアウト
  },
})
```

ストアは 3 つの部屋でできています。

- **state**（ステート）= データそのもの（ユーザー情報など）
- **getters**（ゲッター）= データから **自動計算** される値（「ログイン中か？」など）
- **actions**（アクション）= データを **書き換える処理**（ログイン／ログアウトなど）

画面側は `const auth = useAuthStore()` と書くだけでこの倉庫を使え、
`auth.user`（データ）や `auth.logout()`（処理）を呼べます。
**どの画面から使っても中身は同じ 1 個の倉庫** を共有します。

### 6-3. トークンとは？（ログインの仕組み）

ログインすると、サーバーから **トークン** という「合言葉の文字列」がもらえます。
これをブラウザに保存（`localStorage`）しておき、
以降サーバーに何かお願いするたびに **「私はこのトークンの持ち主です」** と提示します。
（実際の提示は次章の `api/client.ts` が自動でやってくれます。）

```ts
setToken(token) { localStorage.setItem('token', token) }  // 合言葉を保存
logout()        { localStorage.removeItem('token'); this.user = null }  // 忘れる＝ログアウト
```

---

## 7. サーバーとの通信：`api/client.ts`

フロントエンドは自分でデータを作らず、サーバーの API にお願いします。
その **電話係** が `api/client.ts` です。ここでは `axios`（アクシオス）という
通信ライブラリを使っています。

```ts
export const api = axios.create({
  baseURL: `${baseURL}/api`,   // 通信先の共通アドレス
  timeout: 30000,              // 30秒返事がなければ諦める
})
```

この `api` を通してサーバーとやり取りします。よく出てくる 4 種類：

| 書き方 | 意味 | 例え |
|--------|------|------|
| `api.get(...)` | データを **もらう** | 「従業員一覧ちょうだい」 |
| `api.post(...)` | データを **新規登録** | 「新しい従業員を追加して」 |
| `api.patch(...)` / `api.put(...)` | データを **更新** | 「この従業員を書き換えて」 |
| `api.delete(...)` | データを **削除** | 「この従業員を消して」 |

### 便利な自動処理：インターセプター

`client.ts` には「通信の前後に自動で挟まる処理」が 2 つあります。

**① 送信前：合言葉（トークン）を自動で付ける**

```ts
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`  // 自動で添付
  return config
})
```

毎回の通信に、保存しておいたトークンを **自動で貼り付けて** くれます。
おかげで各画面はトークンのことを気にせず「ちょうだい」と書くだけで済みます。

**② 受信後：ログイン切れを自動で処理**

```ts
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {   // 401 = 「あなた誰？」認証エラー
      localStorage.removeItem('token')    // 古い合言葉を捨てて
      window.location.href = '/login'     // ログイン画面へ飛ばす
    }
    return Promise.reject(err)
  },
)
```

サーバーが「401（認証切れ）」を返したら、**自動でログイン画面に戻します**。

---

## 8. データの設計図：`types/index.ts`

このプロジェクトは **TypeScript** で書かれています。
TypeScript は JavaScript に **「データの形（型）を書ける」** 機能を足したものです。

```ts
export interface Employee {
  id: number            // 数値
  name: string          // 文字
  email: string | null  // 文字 または 空(null)
  hourly_wage: number   // 時給（数値）
  active: boolean       // 在籍中か（true/false）
  ...
}
```

これは「従業員データはこういう形です」という **設計図** です。
設計図があると、たとえば `employee.hourly_wage` を文字として扱おうとしたり、
存在しない項目 `employee.salary` を書いたりした瞬間に、
**プログラムを動かす前にエラーで教えてくれます**。
バグを早い段階で防げるのが型の利点です。

`ShiftStatus = 'draft' | 'published' | 'finalized'` のように
**「取りうる値はこの 3 つだけ」** と決めることもできます
（ドラフト／公開中／確定済み）。

---

## 9. 実際の画面を 1 枚ずつ解説

ここまでの部品（router / store / api / types）が、実際の画面でどう組み合わさるかを見ます。

### 9-1. ログイン画面（`LoginView.vue`）

- **Google でログイン** ボタン → `window.location.href` でサーバーの
  Google 認証ページへ移動する（`loginWithGoogle`）
- **開発用ログイン** → 入力した Email/名前で `auth.devLogin()` を呼び、
  成功したらダッシュボードへ移動（`router.replace('/dashboard')`）
- **サンプルデータ投入 / リセット** → 開発用に、
  テスト用の従業員 25 名などをサーバーに作らせるボタン

```ts
async function loginDev() {
  try {
    await auth.devLogin(devEmail.value, devName.value)  // ① ストアのログイン処理を呼ぶ
    router.replace('/dashboard')                        // ② 成功→ダッシュボードへ
  } catch (e) {
    message.error(`ログインに失敗しました: ...`)         // ③ 失敗→エラー通知を出す
  }
}
```

> `try { ... } catch (e) { ... }` は **「失敗するかもしれない処理」の書き方** です。
> `try` の中で失敗したら `catch` に飛び、エラーメッセージを表示します。
> 通信は失敗する可能性があるので、ほぼ毎回この形で囲みます。

### 9-2. ログイン後の中継（`AuthCallbackView.vue`）

Google ログイン後、サーバーは URL の後ろにトークンを付けて
この画面（`/auth/callback?token=...`）に戻してきます。この画面は：

```ts
onMounted(async () => {
  const token = route.query.token   // URLからトークンを取り出す
  if (token) {
    auth.setToken(token)            // 保存して
    await auth.restore()            // ユーザー情報を取得して
    router.replace('/dashboard')    // ダッシュボードへ
  } else {
    router.replace('/login')        // トークンが無ければログインへ戻す
  }
})
```

**画面を表示した瞬間に処理して、すぐ別画面へ移動する** だけの「中継地点」です。
ユーザーには一瞬「ログイン処理中…」と見えます。

### 9-3. ダッシュボード（`DashboardView.vue`）

トップ画面。今月の人件費・自分の勤務時間・シフトの状態を **カード** で並べます。

```ts
onMounted(async () => {
  loading.value = true                     // クルクル開始
  try {
    await shiftStore.fetch(year, month)    // 今月のシフトを取得
    if (shiftStore.shift) {
      await shiftStore.fetchPayroll(year, month)  // あれば人件費も取得
    }
  } finally {
    loading.value = false                  // 必ずクルクル停止
  }
})
```

`computed` を使って、倉庫のデータから表示用の値を自動計算しています。

```ts
const monthlyCost = computed(() => payroll.value?.monthly_total ?? 0)
```

「人件費データがあればその月間合計、なければ 0」という意味です
（`?? 0` は「左が空なら 0 を使う」の記号）。
**元のデータ（`payroll`）が更新されれば、この `monthlyCost` も画面も自動で変わります。**

### 9-4. シフト表（`ShiftTableView.vue`）— このアプリの主役

最も複雑な画面。やっていることは大きく 4 つ。

**(1) 起動時に必要データを一気に取得**

```ts
onMounted(async () => {
  await Promise.all([                    // 3つを同時にお願いして待つ
    employeeStore.fetchAll(),            // 従業員一覧
    ruleStore.fetchPatterns(),           // シフトパターン
    shiftStore.fetch(year.value, month.value),  // 今月のシフト
  ])
})
```

> `Promise.all([...])` は **「複数の通信を同時に走らせて、全部終わるまで待つ」** 書き方。
> 1 個ずつ順番に待つより速く済みます。

**(2) 表を組み立てる**（第 4 章の `v-for` 二重ループ）
従業員 × 日付のマス目に、その人がその日担当するシフト（朝／夜／深夜）を表示します。

**(3) AI にシフトを生成させる**

```ts
async function generate() {
  const res = await shiftStore.generate({
    year: year.value, month: month.value,
    natural_language_note: naturalNote.value,  // 「8/15は田中さん休み」等の自由文
    use_llm: useLLM.value,
  })
  if (res.warnings.length) message.warning(...)   // 警告があれば表示
  else message.success(`シフトを生成しました ...`) // 成功メッセージ
}
```

ユーザーが自然文で事情を書いて「生成」を押すと、サーバー側の AI／最適化エンジンが
シフト表を自動で作り、その結果を倉庫に保存 → 画面の表が自動更新されます。

**(4) メインシフト以外の割当を赤く強調**

```ts
const mainMismatch = !!mainType && matches.some((a) => a.shift_type !== mainType)
```

「その人の本来の担当（朝など）と違うシフトに入っている」マスを検出して、
CSS クラス `cell-main-mismatch` を付けて **赤く** 目立たせます
（`:class="{ 'cell-main-mismatch': ... }"` = 条件が正のときだけそのクラスを付ける書き方）。

### 9-5. 従業員管理（`EmployeesView.vue`）

従業員の一覧表示・追加・編集・削除（いわゆる CRUD）を行う画面です。

- 一覧は naive-ui の **`NDataTable`**（高機能な表部品）で表示
- 表の列の定義（`columns`）に「操作」列を作り、
  各行に「編集」「削除」ボタンを **`h(...)` 関数** で埋め込んでいます

```ts
async function save() {
  if (form.value.id) {
    await store.update(form.value.id, form.value)  // idがある＝既存 → 更新
  } else {
    await store.create(form.value)                 // idが無い＝新規 → 追加
  }
}
```

`form.value.id` があるかどうかで「更新」か「新規登録」かを自動で切り替えています。
1 つのフォームを追加・編集の両方で使い回す、よくあるテクニックです。

> `h(...)` は「テンプレートを使わず JavaScript で HTML 部品を作る」書き方です。
> 表のセルの中にボタンを動的に入れたいときなど、限られた場面で使われます。
> 普段のページは `<template>` で書くので、これは応用と考えてOKです。

### 9-6. ルール設定（`RulesView.vue`）

管理者が「シフトのパターン（朝 9:00-17:00 など）」と
「必要人員（平日の朝は 2 人、など）」を設定する画面です。

必要人員の初期値は `defaultStaffing()` で用意され、
編集した内容を `saveStaffing()` でサーバーに保存します。

### 9-7. 人件費計算（`PayrollView.vue`）

対象月を選んで「計算」を押すと、サーバーが計算した人件費レポートを取得して
**従業員別** と **日別** の 2 つの表で表示します。
計算はすべてサーバー側で、この画面は **結果を表に並べるだけ** です。

### 9-8. 印刷プレビュー（`PrintPreviewView.vue`）

シフト表を PDF / Excel でダウンロードする画面です。

```ts
async function download(kind) {
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
  const blob = await res.blob()              // ファイルの中身(バイナリ)を受け取る
  const a = document.createElement('a')      // 見えないリンクを作り
  a.href = URL.createObjectURL(blob)
  a.download = `shift-${shiftId}.pdf`        // ダウンロード名を指定して
  a.click()                                  // クリックを自動実行＝保存ダイアログ
}
```

「見えないダウンロードリンクを裏で作ってクリックさせる」という、
ファイルダウンロードの定番テクニックです。

---

## 10. 共通部品（components）

### 10-1. ヘッダー（`HeaderBar.vue`）

全画面の上部に出るメニューバー。ログイン中のみ表示されます（第 3 章参照）。

```ts
const nav = computed(() => {
  const items = [
    { label: 'ダッシュボード', to: '/dashboard' },
    { label: 'シフト表', to: '/shift' },
    { label: '人件費', to: '/payroll' },
  ]
  if (auth.isAdmin) {                          // 管理者のときだけ
    items.push({ label: '従業員管理', to: '/employees' })
    items.push({ label: 'ルール設定', to: '/rules' })
  }
  return items
})
```

**ログイン中のユーザーが管理者かどうかで、表示するメニューを変えています。**
一般社員には「従業員管理」「ルール設定」のメニューが出ません。
（第 5 章の通せんぼ機能と合わせて、二重に権限を守っています。）

### 10-2. 休日/希望日カレンダー（`AvailabilityCalendar.vue`）

「この従業員はこの日休み／この日入りたい」を **カレンダー上でクリックして登録** する部品。
シフト表画面の中に埋め込まれて使われます（部品の再利用）。

- `props`（プロップス）で親から「年・月」を受け取る
  → `const props = defineProps<{ year: number; month: number }>()`
- 月の日数分のマスを計算で作り、日付をクリックすると
  「休日として登録／希望日として登録」のポップアップが出る
- 登録・削除するたびにサーバー（`employeeStore`）へ反映

> **props（プロップス）** = 親部品から子部品へ渡す「設定値」のこと。
> この部品は自分では年月を決めず、親（シフト表画面）から
> 「2026 年 8 月を表示して」と指示を受けて動きます。
> 同じ部品を別の月で何度でも使い回せます。

---

## 11. まとめ：1 つの操作を最初から最後まで追う

最後に、**「シフト表画面を開いてAIでシフトを生成する」** という操作が、
これまで説明した部品をどう通っていくかを一気に追ってみましょう。

```
① ユーザーがメニューの「シフト表」をクリック
      │
② router が URL /shift に対応する ShiftTableView.vue を <router-view> に表示
      │   （その前に beforeEach でログイン確認）
      │
③ ShiftTableView の onMounted が動き、api 経由でサーバーから
   従業員・パターン・今月シフトを取得 → stores（倉庫）に保存
      │
④ 倉庫のデータが変わったので、v-for の表が自動で描画される
      │
⑤ ユーザーが自由文を入力して「シフトを生成」ボタンをクリック(@click)
      │
⑥ generate() が shiftStore.generate() を呼ぶ
      │
⑦ api.post('/shifts/generate') でサーバーにお願い
   （トークンは client.ts が自動添付）
      │
⑧ サーバーが AI で作った結果を返す → 倉庫の shift データを更新
      │
⑨ 倉庫が変わったので、表が自動で新しいシフトに書き換わる（リアクティブ！）
      │
⑩ message.success(...) で「生成しました」と通知
```

この流れの中に、本ドキュメントで説明した要素がすべて登場します。

| 要素 | 役割 | 出てきた章 |
|------|------|-----------|
| router | URL → 画面の切り替え・権限チェック | 5 |
| view | ページの見た目と操作 | 9 |
| onMounted | 表示時の初期処理 | 3 |
| store（Pinia） | データの共有倉庫 | 6 |
| api（axios） | サーバー通信・トークン自動付与 | 7 |
| リアクティブ | データ変更→画面自動更新 | 1・9 |
| v-for / @click / v-model | テンプレートの記号 | 4 |

---

## 付録：用語ミニ辞典

| 用語 | かんたんな意味 |
|------|----------------|
| コンポーネント | 画面を作る「部品」。`.vue` ファイル 1 つ |
| リアクティブ | データを変えると画面が自動で変わる仕組み |
| `ref` / `computed` | リアクティブな箱 / 自動計算される箱 |
| テンプレート | `.vue` の `<template>`。見た目(HTML)を書く場所 |
| ディレクティブ | `v-if` `v-for` `v-model` など `v-` で始まる命令 |
| ルーター | URL と画面を結びつける案内係 |
| ビュー(View) | 1 ページ分の画面 |
| ストア(Pinia) | アプリ全体で共有するデータ倉庫 |
| ステート/ゲッター/アクション | 倉庫の「データ本体／自動計算値／操作」 |
| axios | サーバーと通信するライブラリ |
| API | サーバーが提供する「お願いの窓口」 |
| トークン | ログイン済みを証明する合言葉の文字列 |
| props | 親部品から子部品へ渡す設定値 |
| naive-ui | ボタンや表など既製の見た目部品セット（`N`で始まる） |
| TypeScript | データの「型（形）」を書ける JavaScript |
| `async` / `await` | 「時間のかかる処理を待つ」ための書き方 |
| `onMounted` | 部品が表示された瞬間に 1 回だけ動く処理 |

---

*このドキュメントは `frontend/src` 以下のソースコードをもとに作成した解説資料です。*
