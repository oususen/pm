# AI運用規約・AI用DB辞書

## 1. 目的

社内AIは、PMに蓄積された生産管理データを根拠として、次の業務を支援する。

- 生産・品質・中断・残業・進度などの状況把握と傾向分析
- トラブル発生時の事実整理、原因候補の整理、過去事例の検索支援
- 管理者・幹部会向けの説明資料および報告書の下書き
- 利用者の質問に対する、根拠と対象期間を明示した回答

社内AIは判断を補助する機能であり、製造指示・発注・出荷・在庫調整・人事評価を自動決定または自動実行しない。

## 2. 規約を強制する場所

- 正式な規約本文: 本書
- 規約をコードで強制する入口: `pm_backend/apps/ai/services/chat_service.py`の`AIChatAPIView`（旧 `ProductionAIDemoView`という名称、および互換入口だった `production/views_ai_demo.py` と `production/services/ai_demo_service.py`、旧URL `/api/production-ai-demo/` は削除済み）
- 画面: `pm-ui/src/views/ai/AIChat.vue`（`/ai/chat`）
- 運用設定の管理画面: `pm-ui/src/views/settings/AISettings.vue`（`/settings/ai`、権限 `settings.ai`）

モデルの変更（DeepSeek、Qwenなど）は許可するが、本書のデータアクセス・外部送信・禁止操作の規約を迂回してはならない。2-1 の運用設定で有効化できる範囲も、本書が許可した範囲を超えてはならない。

### 2-2. 権限のサーバー側検証

このプロジェクトは基本的に「権限判定はフロントエンドで行い、バックエンドは`IsAuthenticated`（ログイン済みであること）だけを見る」という設計方針（`accounts/permissions.py`の`HasResourcePermissionOrReadOnly`）を取る。ただし社内AIチャットは、次の2点についてサーバー側でも権限を検証する。

- `ai.chat`: `POST/GET /api/ai/chat/`の入口で、`accounts`の実効権限（`_build_effective_permissions`と同じ判定）に`ai.chat`の閲覧権限がなければ403を返す。
- `overtime.personal_summary`: フロントエンドが送る`allow_personal_overtime`は、サーバー側でも同じ実効権限を確認し、権限がなければ強制的に無効化する。フロントの申告だけを信用しない。

これは、個人別残業（誰がいつどれだけ残業したか）が社内でも特に慎重に扱うべきデータであり、`allow_personal_overtime`のようなクライアント申告のブール値だけを信用すると、ログイン済みの任意の利用者が直接APIを叩いて個人別残業を閲覧できてしまうために例外的に追加した。他のリソースへは展開しない。

## 2-1. 運用設定管理（画面: `/settings/ai`）

社内AIの一部の挙動は、コード変更なしに管理画面から調整できる。ただし調整できる範囲は本書が許可した範囲内に限り、画面(`ai/context/screen_context.py`)が許可していないツールを有効化しても使われない。

| 設定モデル（テーブル） | 内容 | 備考 |
|---|---|---|
| `AIProviderConfig`（`ai_provider_config`） | DeepSeek／Qwenの有効化・既定モデル | APIキー自体は含まない（4.3参照） |
| `AIToolPolicy`（`ai_tool_policy`） | 画面領域(`screen_id`)ごとに、ツール(`tool_code`)を有効化するか、外部AI（DeepSeek）への結果送信を許可するか(`allow_external_transfer`) | 無効化した組み合わせはDeepSeek・Qwenどちらからも呼べない |
| `AIDataPolicy`（`ai_data_policy`） | 集計結果の外部送信可否(`allow_aggregated_external_transfer`)、権限者への個人別集計許可(`allow_authorized_personal_data`)、外部送信する最大集計行数(`max_external_result_rows`) | 常に1行だけ保持する全体方針 |
| `AIAnalysisExecutionPolicy`（`ai_analysis_execution_policy`） | 分析案キャッシュ有効期限(`plan_cache_ttl_minutes`)、Python最大実行時間(`max_execution_seconds`)、最大メモリ(`max_memory_mb`)、CPU上限(`max_cpu_cores`)、取得行数の上限(`max_fetch_rows`) | 常に1行だけ保持する分析実行設定。初期値は60分・300秒・2048MB・1コア・100,000行。保存可能範囲は5〜480分・30〜600秒・512〜4096MB（128MB単位）・0.5〜2コア（0.5コア単位）・1,000〜100,000行（1,000行単位）で、API側で検証する |
| `AIKnowledgeSource`（`ai_knowledge_source`） | AIに参照させるリポジトリ内ドキュメントの登録（PMアプリ構造／マニュアル／手順書／安全・運用規約） | 参照させるファイルは登録済みのものに限る |

画面領域(`screen_id`)は `ai_home`（本社横断）、`orders`、`production`、`quality`、`overtime`、`purchase`、`shipping`、`inventory`、`masters` を持つ。`masters` では品番・BOM・工程・ライン・仕入先の読み取り照会だけを許可し、登録・更新・削除は許可しない。`inventory` は現時点でどのツールも割り当てていない（9章の区分Cに対応）。

## 3. 絶対禁止事項

### 3.1 DB操作

社内AIは、DBに対して次を実行してはならない。

- INSERT、UPDATE、DELETE、UPSERT
- DDL（CREATE、ALTER、DROP、TRUNCATE）
- 更新系SQL、ストアドプロシージャ、管理コマンドの実行
- 生産計画、在庫、受注、発注、出荷、承認、権限の変更

AIが利用するDBアクセスは、規約に登録したDjango ORMの読み取り専用集計関数、または「AI用DB辞書の読み取り専用SQL」に限る。SQLは`pm_ai_reader`接続で実行し、`SELECT`一文・辞書登録済みテーブルと列・最大行数の範囲だけを許可する。モデル名やテーブル名を質問文に含めても、辞書外の列・テーブル、複数文、コメント、ワイルドカード取得は実行してはならない。

### 3.2 業務判断

- 懲戒判断をしない。（「個人の評価、順位付け、査定をしない」とした従来の規定は、BOSS指示により取り下げた。2026-10-10）
- 品質判定、出荷可否、発注承認などの最終判断をしない。
- 根拠データが不足する場合、推測で数値や原因を断定しない。

## 4. DeepSeekなど外部APIの利用規約

### 4.1 送信の原則

外部APIへは、回答生成に必要な最小限の情報だけを送信する。送信するデータは、規約に登録された取得関数の出力に限定する。

| データ種別 | 外部送信 | 条件 |
|---|---|---|
| 質問文・直近会話 | 条件付き許可 | 識別子を伏字化して送る |
| 分析画面の分析目的・期間 | 条件付き許可 | AI設定の外部送信の全体許可がオンの場合だけ。人名は**社員コード**、社名は顧客コード・仕入先コードへ置換して送り（4.1-3）、メールアドレスを除去する。利用者が送信前の目的文を確認してから送る。コード不明・同名による曖昧さ・取得失敗時は送信を止める。DBの明細行・件数は送らない |
| 集計済み生産実績 | 許可 | 品番・工程・期間・数量など分析に必要な最小項目 |
| 集計済み仕損・中断 | 許可 | 理由・工程・期間・数量または件数 |
| グループ単位の残業集計 | 許可 | 氏名を含めない |
| 個人別・明細別データ | 条件付き許可 | 個人別残業集計は画面の `overtime.personal_summary` 閲覧権限がある場合だけ、識別子を一時IDへ置換して送信する。氏名指定の個人別集計（`search_employee`で候補確認後に`get_individual_overtime`）としきい値超過者集計（`get_personal_overtime_threshold`）の両方が対象 |
| 本人の残業集計 | 許可 | 利用者本人の分だけを集計する（対象ユーザーはサーバーがログイン者に固定。氏名は結果に含めず、時間・件数だけを送信）。DeepSeek/OpenRouterは `get_my_overtime` を使い、ローカルQwenはサーバー側の固定集計を使う。`overtime.personal_summary` は不要で、`ai.chat` の権限があれば使える。他人の分は調べられない |
| 連絡先、認証情報、署名、添付ファイル | 禁止 | 伏字化しても送信しない |
| 未集計の全件エクスポート | 禁止 | 件数に関係なく送信しない |

### 4.1-2 分析画面における外部送信

分析画面では、AIがSQL・Pythonを作成するために、AI用ビューの定義、公開フィールド、分析目的、集計結果だけを外部AIへ自動送信できる。取得した明細行、会話履歴、チャット画面の集計結果は自動送信しない。

分析用の明細は、Djangoが`pm_ai_reader`で承認済みビューから取得し、一時DuckDBへ渡す。生成Pythonは一時DuckDBのスナップショットだけを扱い、MySQLの接続情報を持たない。

明細行の外部送信が分析上必要な場合は、次のすべてを満たす場合だけ許可する。

1. 利用者が今回の分析で送信することを明示承認する。
2. 氏名・ログインID・得意先名・仕入先名などを4.2の一時IDへ置換する。
3. 連絡先、認証情報、添付、未承認の自由記述を含めない。
4. 送信対象・目的・伏字化方法を分析画面へ表示する。

### 4.1-3 分析案の作成で外部AIへ送る識別子（社員コードを含む）

分析画面で分析案を外部AI（DeepSeek・OpenRouter）に作成させるとき、分析目的に含まれる登録済みの名称は、検索AIの一時IDではなく、次の登録コードへ置換して送る。2026-10-03にBOSSが、社員コードを外部AIへ送ることを明記するよう指示した。

| 目的文に含まれる名称 | 外部へ送る値 | 扱い |
|---|---|---|
| 利用者・作業者の氏名、ログインID | 社員コード（`profile.employee_code`） | PM内の名簿と照合すれば個人に結び付く識別子であり、個人情報に準じて扱う。氏名・ログインIDそのものは送らない |
| 得意先名・略称 | 得意先コード | 6.5-3のとおり、得意先コードは個人情報ではない |
| 仕入先名 | 仕入先コード | AI分析基盤仕様書2.2のとおり、名称ではなくコードを使う |

社員コードの外部送信は、次のすべてを満たす場合だけ許可する。

1. AI設定の外部送信の全体許可（`allow_aggregated_external_transfer`）がオンである。
2. 利用者が、置換後の目的文を送信前に画面で確認し、送信することに同意している。確認は、目的・期間・AI・モデルが変わると失効し、サーバーも署名で照合する。
3. 目的文の名称に対応するコードが未登録、または同名で複数のコードがある場合は、外部へ送らず止める。コードを推測・補完しない。
4. 送るのは、置換後の目的文、期間、公開ビューの説明だけである。DBの明細行・件数、氏名、連絡先は送らない。ログインIDは、送ってよい（BOSS指示 2026-10-10。従来は送らない扱いだった）。
5. 外部AIの回答中のコードは、名前へ自動で復元しない。送信した目的文は分析案に記録する。

登録されていない人名・社名や、自由記述の機密は置換されないため、画面で利用者へ注意を表示する。ローカルQwenは社外へ送信しないため、この確認と置換の対象外である。


### 4.1-4 SQL・Pythonの生成で外部AIへ送る内容

分析画面で、承認済みの分析案から、外部AI（DeepSeek・OpenRouter）にSQL・Pythonを作成させるとき（AI分析基盤仕様書4.8）も、4.1-3の規則（全体許可・コード置換・未登録や同名で止める・応答のコードを復元しない）を適用する。追加の条件は次のとおり。

1. 置換は、目的文だけでなく、AIが作った手順・出力案を含む、送る自由記述のすべてに適用する。**題名（タイトル）は、コード生成のAIへ送らない**（2026-10-07。AI分析基盤仕様書4.8・5.3-10）。
2. 送るのは、置換後の分析案、承認ビューの名前・列名・型・説明、期間、実行環境の制約だけである。**実データ・明細行・idの値・承認件数・利用者名・実行履歴は送らない**。DuckDBのエラー文も送らない。
3. 利用者は、実際に送る文面の全体を、送信前に画面で確認する。確認は、利用者・分析案・版・AI・モデル・何回目の生成か・送信内容のいずれかが変わると失効し、サーバーも署名で照合する。再生成のたびに確認を取り直す。
4. 送信の直前に、AIの利用可否（管理設定・外部送信の全体許可・APIキー）を再確認し、許可が取り消されていれば送らない。

### 4.1-5 テンプレートを参考にした生成で外部AIへ送る内容（2026-10-09）

分析画面で、保存済みテンプレートを参考にして、外部AI（DeepSeek・OpenRouter）に分析案・SQL・Pythonを作成させるとき（AI分析基盤仕様書5.3-11）も、4.1-3・4.1-4の規則（全体許可・置換・送信前の全文確認・未登録名称で停止）に従う。加えて、次を守る。

1. 送るのは、利用者が選んだ**1つのテンプレート**の、名称・目的・手順・出力案・条件・データ範囲（ビュー・列）・期間と、コード生成のときは、変数の形のSQL・Python・変数の定義（既定値を含む）である。**テンプレートのコード本文が、外部送信の対象になる**（初めて）。却下理由・確認者・通知の記録は、送らない。
2. 変数の既定値に、品番・顧客コード・納入先コードの実値が入るため、これらの識別子が外部へ送られる。6.5-3のとおり、得意先コードは個人情報ではない。社員コードに相当する値が、テンプレートの文・コードに入っている場合も、4.1-3の規則（置換後を、送信前に確認）に従う。
3. 登録名称は、コードへ置換する。置換できない名称（未登録・同名）がある場合、または、変数名・手順名が登録名称と衝突して、置換でコードと変数の定義が食い違う場合は、外部へ送らず止める。**コードを推測・補完しない**。
4. 置換は、登録名称とメールアドレスだけである。**数字の羅列（電話番号の形など）は、置換されない**。テンプレートに個人情報が含まれていないか、利用者が、送信前の全文確認で確認する。
5. 参考にできるのは、利用者が全文を見られるテンプレートだけ（承認済みは分析権限のある全員、管理者承認待ちは作成者と管理者）。管理者承認前のテンプレートを参考にしたことは、画面に明記する。
6. 外部AIの回答（参考から作った分析案・コード）は、承認を引き継がない。手順・データ範囲・コード・試行・コード承認を、新しい分析として、毎回取り直す。元のテンプレートは、変更しない。
7. ローカルQwenでは、参考を使えない（文脈長の制約）。外部AIが使えない場合に、参考なしで続ける、別のAIへ切り替える、ことはしない。

### 4.2 伏字化と復元

分析タブの目的文は、2026-10-03にBOSSが承認した実コード方式を使う。ユーザー名・氏名は社員コード（`accounts_userprofile.employee_code`）、顧客名・略称は顧客コード（`m_customer.customer_code`）、仕入先名は仕入先コード（`m_supplier.supplier_code`）へ置換する。先頭ゼロを保持し、無効化済みも含める。登録実績の作業者名に対応するユーザーコードがない場合も送信を止める。コードは応答時に名前へ自動復元しない。対応表はリクエスト内だけに保持する。未登録の名称や機密は自由文から確実に検出できないため、置換後の目的文を画面へ提示して利用者確認を必須とする。入力や対応コードが変わった場合は確認を取り直す。コードは完全な匿名化ではない。

以下の一時ID方式は検索タブ・ドロワーの既存方式であり、今回は変更しない。将来の分析明細送信も未実装である。

個人名、ログインID、得意先名、仕入先名など、分析上必要な識別子は以下の方式で扱う。

1. サーバー内で一時ID（例: `作業者A`、`得意先X`、`仕入先A`）に置換する。
2. 対応表はリクエスト処理中のメモリだけに保持し、外部APIへ送信しない。
3. API応答に一時IDが含まれる場合だけ、画面へ返す直前に元の表示名へ復元する。
4. メールアドレス、住所、署名画像、認証情報は復元対象にせず、外部APIへ送信しない。電話番号は、連絡先の列（`phone_number` 等）を個人情報列として制御するが、文字列としての置換は行わない（品番・得意先コードなどの数字の並びを電話番号と誤判定して値が失われたため、2026-10-01に置換を廃止）。

伏字化で必要な分析ができない場合は、対象項目、送信目的、保存有無を規約に追記し、承認後に範囲を拡張する。

会話履歴（`ai_conversation`）には、画面に表示した復元後の回答（権限者の場合は氏名・個人別残業時間を含む）を保存する。外部APIへは送らず、閲覧・削除は会話の作成者本人に限る。対応表（一時ID⇔実名）自体は保存しない。保存期間はAI設定の「会話履歴の保存期間」で管理し（0は無期限）、期限を過ぎた会話は自動削除する。

### 4.3 APIキー

- APIキーはバックエンドの `pm_backend/.env` の環境変数でのみ管理する。
- APIキーを画面、ログ、仕様書、Git、チャットに出力しない。
- DeepSeekのモデルは画面で選択できるが、バックエンドが許可したモデルIDだけを受け付ける。

### 4.4 AI分析の結果の記録（評価の蓄積）に関する規則（2026-10-09、BOSS承認。記録は、未実装。計画: AI分析_結果の記録実装計画.md）

AI分析の結果（成功・失敗・失敗の理由コード・採用）を記録し、お手本の優先、失敗の型の把握、モデル・指示文の比較に使う（目的: AIが、だんだん賢くなること）。記録と集計には、次の規則を守る。

1. **記録するもの**: 固定コードと数値だけ（段階・成否・失敗の理由コード・モデル名・指示文の版・試行回数・テンプレートの内部ID・版など）。許可リストで検査し、未知の文字列は、固定コード`unknown_reason`にする。
2. **記録しないもの**: 目的文・手順・出力案・条件・追加の指示、SQL・Pythonの本文と個別のコードを特定できるハッシュ、実行結果・明細・件数、期間・利用ビュー・列、テンプレートの名称、品番・顧客コード・登録名称などの値、AIの応答本文・`unsupported`の理由文・例外のメッセージ本文、変数名。
3. **個人を持たない**: 利用者の識別（user・氏名・ユーザー名）、分析案ID、ワーカーID、元のレコード（実行履歴など）のIDを、記録しない（識別子は、非公開の乱数、または、鍵付きのハッシュ）。**例外**: テンプレートの内部ID・版、参考にしたテンプレートの内部ID・版は、短期の詳細記録に限り保持してよい（BOSS承認 2026-10-10）。長期集計には保持しない。元テンプレート（作成者・承認者を持つ）との照合による再識別のリスクが残るため、テンプレート別・参考テンプレート別の集計は、少数を隠す。
4. **個人が推測されるリスクの対策**: 集計から個人が推測されるリスクを減らす対策（日単位の日時、集計の出口の固定、少数の非表示、細かい期間・多軸の組み合わせを出さない）を取る。これらの対策は、完全な匿名化を保証するものではない。
5. **集計の出口**: 管理者（設定「AI」の編集権限）向けの集計だけ。生の行を出さない。コマンド・SQL・出力ファイルにも、同じルールを適用し、閲覧者と持ち出しの範囲を決める。
6. **記録の確定点**: 処理が確定した後に記録する（実行は、ワーカーの最終確定の時点）。記録の失敗は、本来の処理（分析・実行）に影響させない。記録は、二重にしない。
7. **分母**: 「送信前に拒否された要求」と「実際にAIを呼んだ試行」を分ける。中止・期限切れ・状態不明は、成功率の分母から除き、除外件数を併記する。状態不明の観測は分母に含めない。後に最終確定した実行は、その最終結果に従って算入する（初回の観測と最終確定は別の事象で、各事象を重複して記録しない）。観測できた完了試行の率であり、全件ではない、と明記する。
8. **意味の区別**: 保存・管理者承認・実行の成功・利用者による結果の採用は、別の意味として記録する。
9. **保持**: 詳細な記録の保持と、粗くした長期の集計の保持を、分けて決める（日数は、BOSS承認）。
10. **学習データへの転用**: 記録・テンプレートの承認を、学習利用の承認とみなさない。学習への自動の転用を、禁止する。学習に使うときは、別の計画で、本文・コード・既定値の、機密・個人情報の確認と、学習利用の承認を、必須にする。
11. **外部送信しない**: 記録・集計を、外部AIへ送らない。
12. **モデルの比較**: 順位と断定しない。件数・除外件数・カテゴリ・参考の有無・改良の有無・試行回数を併記する。

## 5. AI用DB辞書の利用区分

| 区分 | 意味 | AIの扱い |
|---|---|---|
| A: 利用許可 | 定義・関連・集計方法を確認済み | 規約に登録した集計関数から参照可 |
| B: 伏字化利用 | 個票を分析する必要がある | 伏字化・最小化を実装後に限定参照可 |
| C: 定義確認待ち | 数量や業務上の意味が未確定 | AI分析・外部送信とも不可 |
| D: 機密/運用設定 | 認証、連絡先、権限、設定、添付など | AI参照・外部送信とも不可 |

## 6. 現在の利用許可データ（区分A）

### 6.1 基本マスタ

| モデル（テーブル） | フィールド名 | 関連 | AI利用目的 | 外部送信 |
|---|---|---|---|---|
| `masters.Product`（`m_product`） | `product_code`, `product_name`, `category`, `unit`, `line`, `process`, `is_active` | ライン、工程、BOM、実績、需要 | 品番・品名・工程の特定 | 品番・品名は必要時のみ。個人情報は含めない |
| `masters.BOM` / `BOMItem`（`m_bom` / `m_bom_item`） | `parent_product_id`, `version`, `valid_from`, `valid_to`, `is_active`, `child_product_id`, `quantity`, `sourcing_type`, `supplier_id`, `process_id`, `line_id`, `lead_time_days`, `remark` | 製品、工程、ライン、仕入先 | BOM構成・有効期間・調達条件・備考の読み取り照会 | 許可。備考は質問に必要な該当行だけを外部AIへ送信する |
| `masters.Line`（`m_line`） | `line_code`, `line_name`, `line_type`, `lead_time_days` | 工程、需要、進度、実績 | ライン別集計の軸 | 許可 |
| `masters.Process`（`m_process`） | `process_code`, `process_name`, `line`, `management_unit` | 製品、実績、仕損、中断 | 工程別分析の軸 | 許可 |
| `masters.CalendarDay`（`m_calendar_day`） | `target_date`, `is_working_day`, `work_minutes` | カレンダ、ライン、仕入先 | 稼働日・期間判定 | 許可 |

`masters.Customer` と `masters.Supplier` は名称・コード照会に限りサーバー内で参照する。外部APIへ名称を送る場合は、4.2の一時IDに置換する。`Supplier.contact_person`、`phone_number`、`order_email` は区分Dであり、参照・送信禁止とする。

### 6.2 生産実績

| モデル（テーブル） | フィールド名 | 関連 | 数値定義 | AI利用 |
|---|---|---|---|---|
| `production.ProcessRealtimeRecord` | `timestamp`, `record_type`, `qty`, `line`, `process`, `product`, `product_code`, `operator_name` | 製品、ライン、工程、仕損 | `record_type='PRODUCTION'` の `qty` 合計を生産実績とする。仕入の入荷実績は `record_type='PURCHASE'` で保存されるため含まれない（区別前の2026年9月は `PRODUCTION` の数量の46%が仕入分だった）。品番を質問で指定した場合は `product_code` の完全一致で絞り込む | 日別・工程別・品番別の生産数。作業者別は伏字化利用 |
| `production.LaserActual` / `LaserActualDetail`（`t_laser_actual` / `t_laser_actual_detail`） | `work_date`, `operator_action`, `detail_type`, `product_code`, `total_qty` | レーザー実績ヘッダ、品番別明細、製品、工程 | 生産実績照会のレーザータブと同じく、`operator_action='END'` かつ `detail_type='COMPONENT'` の `total_qty` を品番別生産数とする。START・PAUSE・未終了の明細は含めない | 品番指定時にレーザー実績があれば、`ProcessRealtimeRecord` と合算せずレーザー実績を正規根拠にする |
| `production.LineRealtimeRecord` | `line`, `product`, `product_code`, `product_name`, `timestamp`, `record_type`, `qty`, `equipment_state` | ライン、工程、製品 | ライン実績として登録された数量。ProcessRealtimeRecordとの二重集計を禁止 | 定義差分確認後に限定利用 |
| `production.ProductionOrder` / `ProcessActual` | `order_no`, `product`, `routing`, `line`, `order_qty`, `scheduled_start_date`, `scheduled_end_date`, `status`, `production_order`, `routing_step`, `process`, `completed_qty`, `actual_duration_min`, `completed_at` | 製品、工程、ルーティング | 指示・実績の意味を個別仕様で確認する | 区分C。将来の指示対実績分析候補 |

### 6.3 仕損・品質

| モデル（テーブル） | フィールド名 | 関連 | 数値定義 | AI利用 |
|---|---|---|---|---|
| `quality.ScrapRecord`（`t_scrap_record`） | `plan_date`, `event_type`, `disposition_status`, `qty`, `return_qty`, `reason`, `occurrence_process`, `product` | ライン、工程、製品、実績 | 確定仕損は `event_type='SCRAP'` かつ `disposition_status in ('REJECTED','PARTIAL')`。正味数量は `qty - return_qty` | 理由別・工程別・期間別の正味仕損数量 |
| `quality.ScrapRecordDetail`（`t_scrap_record_detail`） | `scrap_record`, `product`, `product_code`, `product_name`, `process_id`, `line_id`, `supplier_id`, `sourcing_type`, `deduct_qty`, `is_replenished`, `replenished_at`, `is_backlog_processed` | ScrapRecord、製品、BOM | BOM展開明細。親仕損との二重合計禁止 | 区分C。部品影響分析は定義確認後 |

### 6.4 中断・トラブル

| モデル（テーブル） | フィールド名 | 関連 | 数値定義 | AI利用 |
|---|---|---|---|---|
| `production.BrakeLineRecord`（`brake_line_record`） | `plan_date`, `process`, `product`, `product_code`, `operator_action`, `operator_action_reason`, `qty` | 工程、製品、ライン | 生産数は`operator_action in ('END','PAUSE')`の`qty`合計（作業区間ごとに終了・中断時点の加工数を登録するため重複しない。生産実績照会・`LineBacklog.actual_qty`と同じ定義）。中断・強制終了は`operator_action in ('PAUSE','TEMP_END')`のレコード件数 | 品番指定時のブレーキ生産数、理由別・工程別の中断件数 |

作業者ユーザーと作業者名は外部送信前に伏字化する。

### 6.5 残業

| モデル（テーブル） | フィールド名 | 関連 | 数値定義 | AI利用 |
|---|---|---|---|---|
| `overtime.OvertimeApplication`（`t_overtime_application`） | `work_date`, `application_type`, `hours`, `midnight_hours`, `team`, `status`, `applicant` | 組織、ユーザー、承認ログ | `application_type='overtime'` かつ提出済み以降の対象状態について、`hours + midnight_hours` を残業申請時間として合算 | グループ別・期間別集計。個人別は伏字化利用 |
| `overtime.OvertimeApprovalLog` | `application`, `approver`, `role`, `status`, `comment`, `acted_at` | 残業申請、ユーザー | 承認経過の履歴 | 区分B。コメント・氏名は伏字化必須 |

残業申請時間は打刻実績ではない。

### 6.5-2 仕入（入荷実績）

| ビュー | 列 | 有効条件 | AI利用 |
|---|---|---|---|
| `v_ai_purchase_receipt`（`ai/0012`で作成、`ai/0013`で抽出条件を変更） | `id`, `arrival_date`, `registered_at`, `supplier_id`, `line_id`, `product_id`, `product_code`, `product_name`, `qty`, `process_id`, `input_source` | `t_process_realtime_record` のうち `record_type='PURCHASE'` の行だけ。仕入れ実績照会画面と同じ定義 | 仕入画面・本社横断から読み取り専用SQLで、仕入先別・品番別・日別の入荷数を集計する |

- 入荷数量は `qty`、入荷日は `arrival_date`（`event_data.arrival_date`）。`arrival_date` は実際に入荷した日、`registered_at` はシステムへ登録した日時。検収（`PURCHASE_RECEIVING`・`PURCHASE_RECEIVING_MOBILE`）は入荷時にその場で登録するので両者は同じ日になるが、仕入れ実績入力（`PURCHASE_ACTUAL_INPUT`）は後から入力できるので異なることがある。入荷の日別・期間集計は必ず `arrival_date` を使う（2026-09-30時点では全2,531件が実績入力で、うち34件は入荷日と登録日が異なる）。
- `event_data` に入っているのは `source`・`line_id`・`supplier_id`・`arrival_date` だけで、個人情報は含まない。
- 仕入先名（`m_supplier.supplier_name`）は外部AIへ送る直前に一時ID（仕入先N）へ伏字化される。連絡先の列は従来どおり個人情報扱い。
- 仕入計画・入荷予定（`LineBacklog` の購買・外作ライン）と、在庫/残量・仕入れ進度（専用計算）はまだ対象外。

### 6.5-3 出荷（出荷実績）

| ビュー | 列 | 有効条件 | AI利用 |
|---|---|---|---|
| `v_ai_shipment`（`ai/0014`で作成） | `id`, `shipment_date`, `product_code`, `product_id`, `product_name`, `customer_code`, `ship_to_code`, `quantity`, `trip_allocation_id`, `remark_text` | `t_shipment_actual` 全行。製品は品番コードで `m_product` と結ぶ（`t_shipment_actual.product_id` は全行NULLのため） | 出荷画面・本社横断から読み取り専用SQLで、品番別・納入場別・日別の出荷数を集計する |

- 出荷数量は `quantity`、出荷日は `shipment_date`。日別・期間集計は `shipment_date` を使う。
- `customer_code`（得意先コード）・`ship_to_code`（納入場コード）はコードであり個人情報ではないため、全利用者に公開する。受注側（`m_customer.customer_code`・`t_order_line.ship_to_code`）も同じ扱いに変更した（得意先名・`customer_id` は従来どおり個人情報区分）。備考は列名 `remark` が個人情報の伏字化対象のため、ビューでは `remark_text` とする。
- `trip_allocation_id`（出荷便割付ID。なければNULL）と `remark_text`（システムが書く便の割付情報。例: `[TRIP_ACTUAL]54:576|PD=2026-07-22:42`）もAIへ渡す。`remark_text` は業務メモではない。
- 2026-10-01時点の開発DBでは488行すべてがクボタ（得意先コード000196）向け。本番の内容は未確認のため、TABLE_NOTES の「現在はクボタ向けのみ」は本番確認後に見直す。
- 出荷計画・便の進捗と、在庫・進度はまだ対象外。

### 6.5-4 品番マスタ（`v_ai_product`。2026-10-10 実装。開発DBへの適用・定義者の付け替えは実施済み。本番は未反映）

| ビュー | 列 | 有効条件 | AI利用 |
|---|---|---|---|
| `v_ai_product`（`ai/0034`で作成） | `id`, `product_code`, `product_name`, `category`, `unit`, `unit_price`, `standard_lt_days`, `stock_location`, `processing_area`, `line_id`, `process_id`, `next_process_id`, `management_unit`, `is_final_product`, `is_line_final_product`, `is_virtual_set`, `order_lot_min`, `order_lot_multiple`, `is_special_management_material`, `specific_gravity`, `size_length`, `size_width`, `size_thickness`, `transfer_destination`, `model_name`, `identification_code`, `product_group_id`, `used_container_id`, `capacity`, `is_active`, `created_at`, `updated_at`（32列） | `m_product` 全行（絞り込みなし・結合なし。2,850行のうち有効2,808・無効42）。非公開（ビューに含めない）: `image_url`, `product_name_halfwidth`, `is_phantom`, `self_lt_days` | 読み取り専用SQLで、品番の分類・寸法・発注条件の確認、実績ビューの `product_id` / `product_code` から品名・分類を引く |

- 個人情報の列は含まない。`unit_price`（金額）はBOSS判断で公開。
- 空（NULL）がある列: `unit_price` 2,386行、`line_id` 1,833行、`process_id` 2,003行、`category` 16行。`category` の6種（ASSEMBLY・OUTSOURCED・SINGLE・PURCHASED・UNKNOWN・MATERIAL）と `management_unit`（DAY・MINUTE・空）の業務上の意味は未確認。
- `ANALYSIS_VIEWS`（AI分析画面。`date_field=None`＝期間で絞らず全行）・`ANALYSIS_COLUMN_TYPES`（32列）に登録済み（2026-10-10、サイクルC。計画書 §12 参照。`SCREEN_SQL_TABLES`・`TERM_COLUMNS` は未変更）。
- 権限の付与は手動SQL（計画書 §9.3）。

### 6.5-5 工程マスタ（`v_ai_process`。2026-10-10 実装。開発DBへの適用は未実施。本番も未反映）

| ビュー | 列 | 有効条件 | AI利用 |
|---|---|---|---|
| `v_ai_process`（`ai/0035`で作成） | `id`, `process_code`, `process_name`, `line_id`, `management_unit`, `operating_rate`, `equipment_count`, `two_person_only`, `is_active`（9列） | `m_process` 全行（絞り込みなし・結合なし。46行のうち有効45・無効1）。非公開（ビューに含めない）: `is_outsource`, `created_at`, `updated_at` | 読み取り専用SQLで、工程のコード・名前・所属ライン・管理単位・設備台数の確認、実績ビューの工程IDから工程を引く |

- 個人情報の列は含まない。`process_code` は先頭ゼロを含む文字列（例 `0801`）で、工程の特定に使う。
- 列の意味は仕様書で確認できた範囲だけ書く（計画書 §13.2）。`operating_rate`（稼働率(%)）・`two_person_only`（2人1設備専用）は項目名のみで、業務上の定義は未確認。
- `ANALYSIS_VIEWS`（`date_field=None`＝全行）・`ANALYSIS_COLUMN_TYPES`（9列）・`BASE_SQL_SCHEMA`・`TABLE_NOTES` に登録済み。元テーブル `m_process` の許可（`BASE_SQL_SCHEMA['m_process']`・`SCREEN_SQL_TABLES`）は置き換えず、ビューの追加のみ。`TERM_COLUMNS` は未変更。
- 権限の付与・定義者の付け替えは手動SQL（計画書 §9.3 に倣う。`pm_ai_view_owner` へ `m_process` の9列の列単位 `SELECT`）。開発DBでは未実施。

### 6.5-6 品番・顧客コード・納入先コードの表記（AI分析の変数。2026-10-10）

- DuckDB（分析の実行）は大文字小文字を区別するが、MySQL（`utf8mb4_unicode_ci`）は区別しない。そのため、AI分析の変数（品番・顧客コード・納入先コード）の値は、**マスタ・公開ビューに保存されている正規の表記**に直してからコードに入れる。`upper()` は使わない（マスタに小文字の品番 `giji` が実在する）。
- 確認元（公開ビューが正）: 品番=`v_ai_product`、納入先コード=`v_ai_shipment` の実際の値（ともに読み取り専用の分析用接続）、顧客コード=`m_customer`（顧客マスタのビューは未作成。作成後は公開ビューへ切り替える）。マスタ・ビューにない値、および大文字小文字だけが違う値が複数あって決められない納入先コードは、拒否する（代わりの値は使わない）。
- 先頭ゼロ・全角半角の違いは対象外。詳細は `AI分析基盤仕様書.md` 5.3-5c。

### 6.6 受注（ルーティング未設定の注文品）

| モデル（テーブル） | フィールド名 | 有効条件 | AI利用 |
|---|---|---|---|
| `orders.OrderLine`（`t_order_line`） | `product_code`, `quantity`, `due_date`, `order_type`, `product`, `order` | `order.status='OPEN'`、製品あり、有効な`Routing`なし、画面既定では納期が90日前以降 | 「ルーティング未設定の注文品」画面と同じく品番ごとに1件へ絞った件数・品番・納期を参照する |
| `masters.Routing` | `product`, `is_active` | 同一製品に`is_active=True`が1件でもあれば対象外 | 未設定判定だけに利用する |

受注明細の数量は、品番ごとに画面表示対象として選ばれた代表明細の数量であり、全受注明細の合計ではない。得意先名、受注番号、顧客発注番号、備考は外部APIへ送信しない。

## 7. 関連図（現在許可する範囲）

```text
Product ──< BOM ──< BOMItem >── Product（子品目）
   │                 │
   ├── ProcessRealtimeRecord ──> Process ──> Line
   ├── LaserActualDetail ──> LaserActual ──> レーザー設備
   ├── ScrapRecord ────────────> Process / Line
   └── BrakeLineRecord ────────> Process / Line

Department ──< OvertimeApplication >── User
```

分析では、同じ事実を複数の実績テーブルから合計しない。特に生産実績は、質問ごとに規約で指定した正規データソースだけを使う。

## 8. 数値・期間の共通定義

- 日付の業務境界は午前8時。8:00より前の入力は前業務日として扱う画面・処理があるため、各集計関数は既存業務ロジックに従う。
- 生産数、仕損数、在庫数、進度、需要数、計画数は同じ「数量」でも意味が異なる。回答では対象モデル・項目・期間を根拠として示す。
- 進度の需要データは `production.LineDemand` を正規データソースとする。`LineBacklog.order_qty` や `demand_qty_plan` を代替利用しない。
- `LineBacklog` の `sequence_no=0` は需要専用行、`sequence_no>0` は計画専用行である。両者を混在させた合計や実績解釈をしてはならない。
- 在庫・進度・計画在庫の計算は既存の専用計算ロジックに従う。AIが独自式で再計算してはならない。

## 9. 利用保留または禁止のデータ領域

以下はモデルが存在しても、初版では区分CまたはDとする。

| 領域 | 区分 | 理由 |
|---|---|---|
| 受注・出荷・便計画 | C（一部A） | 受注は「ルーティング未設定の注文品」だけ区分A。その他は納期・数量・顧客との関係、正規の進捗定義を領域ごとに確認する必要がある |
| 購買・発注提案・仕入先納入 | C（一部A） | 入荷実績（`v_ai_purchase_receipt`）だけ区分A。仕入計画・入荷予定・発注提案・在庫/進度は定義確認後に追加する |
| 在庫・棚卸・引当・進度 | C | 数量の意味と再計算責務が複雑なため、専用仕様を確認後に追加する |
| 設備点検・品質チェックシート・画像・添付 | D | 添付、画像、作業記録の送信可否を別途決める必要がある |
| ユーザー、権限、承認、通知、通話、認証 | D | 個人情報・認証情報・通信内容を含むため |
| システム設定、APIキー、メール送信設定 | D | 運用・認証情報のため |

## 10. 新しいデータ領域を追加する手順

1. 対象モデル、項目、テーブル間の関連をモデル定義から記録する。
2. 既存仕様書と実データで、数量・状態・日付の業務上の意味を確認する。
3. AIが使う集計関数、入力条件、出力項目、二重計上防止条件を本書へ追記する。
4. 外部APIへ送る項目、伏字化対象、禁止項目を決定する。
5. `ai/services/chat_service.py`（または関連する`ai/services/*.py`）に読み取り専用の専用関数として実装する。API入口の `ai/views.py` には業務ロジックを置かない。
6. 代表データで根拠・数量・期間を検証してから画面へ公開する。

未確認のまま、モデル名だけを根拠にAIの参照範囲へ追加してはならない。

## 10-1. AI用DB辞書の読み取り専用SQL

DeepSeekは、専用集計ツールだけでは回答できない場合に限り、画面起点で許可された区分Aのテーブル・列を用いた`SELECT`文を作成し、`pm_ai_reader`で実行できる。

- 許可するのは`SELECT`一文のみ。複数文、コメント、ワイルドカード（`*`）は拒否する。
- `INSERT`、`UPDATE`、`DELETE`、`CREATE`、`ALTER`、`DROP`、`TRUNCATE`、`SET`、`SHOW`、`CALL`、ロック取得、ファイル出力は常に拒否する。
- 氏名、連絡先、受注番号、顧客発注番号、備考、ロット番号、作業者・申請者・承認者の列は、通常のSQL辞書から除外する。AI設定で個人別集計を許可し、画面の個人別残業集計権限を持つ利用者に限り、個人情報列として参照できる。DeepSeekへ送る値は一時IDまたは伏字に置き換え、回答時にだけ復元する。
- 行数はAI設定の「外部送信する最大集計行数」以下とし、`LIMIT`がない場合はサーバーが付与する。
- 画面別に許可したテーブルを超える参照は拒否する。購買・出荷・在庫は、定義確認が完了するまでSQL照会を公開しない。
- このツール自体の有効化・無効化と、外部AI（DeepSeek）への送信可否は、2-1 の `AIToolPolicy`（画面ごと）で管理する。無効化した画面・プロバイダの組み合わせでは呼び出せない。

## 11. 実装状況

| 規約 | 現状 | 次の対応 |
|---|---|---|
| 更新・削除・DDL・管理SQLの拒否 | 実装済み | `sql_queries.py`のFORBIDDEN_SQLで常に拒否。追加時はキーワードを本書とコードへ同時追記 |
| AI用DB辞書の読み取り専用SQL（10-1） | 実装済み | `execute_readonly_sql`を`pm_ai_reader`（SELECT権限のみ、接続元IP限定）経由で実行。画面別ホワイトリスト外・書込み系・ワイルドカードは拒否 |
| 運用設定管理画面（2-1） | 実装済み | `/settings/ai`（権限`settings.ai`）でプロバイダ・ツール有効化・データ送信方針・ナレッジ登録を管理 |
| `ai.chat`・個人別残業のサーバー側権限検証（2-2） | 実装済み | `AIChatAPIView`（旧`ProductionAIDemoView`）に`IsAuthenticated`を追加し、`ai.chat`と`overtime.personal_summary`は実効権限をサーバー側でも確認する。あわせて`accounts.models.UserPermission.RESOURCE_CHOICES`に不足していた`ai`/`ai.chat`/`settings.ai`/`overtime.personal_summary`を追加した（未登録だと実効権限に一切現れず、一般ユーザーが権限を持てなかったため） |
| DeepSeekモデル許可リスト | 実装済み | モデル追加時は本書とコードを同時更新 |
| 生産・仕損・中断・残業の集計 | 実装済み | DeepSeekが品番検索・読み取り専用集計ツールを選択し、数値根拠を回答に継続表示 |
| 個人名などの一時伏字化 | 実装済み | PMに登録されたユーザー・作業者名・得意先名・仕入先名を一時IDへ置換する。個人別残業は `overtime.personal_summary` を持つ画面でだけ応答時に復元する。連絡先は復元しない |
| 受注・在庫・購買・出荷の分析 | 受注のルーティング未設定品だけ実装済み | その他の領域は辞書・集計関数を確認後に追加 |
