# AI用ビュー作成計画

## 1. 目的

PM本体テーブルをAIへ直接公開せず、業務上の意味・数値定義・公開フィールドを固定した`v_ai_...`ビューだけをAI分析に使用する。

ビューはデータを複製しない。PM本体の最新データをリアルタイムで参照し、更新・削除の同期漏れを防ぐ。AIが参照するビューは、`pm_ai_reader`へ`SELECT`だけを付与する。

本計画は[AI分析基盤仕様書](AI分析基盤仕様書.md)および[AI運用規約・AI用DB辞書](AI運用規約・AI用DB辞書.md)に従う。

## 2. 現在のビュー

| ビュー | 用途 | 状態 |
|---|---|---|
| `v_ai_purchase_receipt` | 仕入の入荷実績を平坦な列構成で参照する | 作成済み |
| `v_ai_shipment` | 出荷実績と品番情報を結合して参照する | 作成済み |

既存ビューは、開発・本番ごとに定義者、実行可否、`pm_ai_reader`の権限を確認する。開発DBの`v_ai_purchase_receipt`で発生しているエラー1449は、追加ビュー作成前に修正する。

## 3. 作成対象と優先順位

### 優先0：マスタビュー（実績ビューより先に作成する）

実績ビューは品番ID・工程IDなどのコードだけを持ち、名称や属性はマスタビューで引く。そのため、マスタビューを実績ビューより先に作成する（BOSS指示）。

| 候補 | 元テーブル | 状態 |
|---|---|---|
| 品番 | `m_product` | 未着手（BOSSが作成対象と順序を指定） |
| 工程 | `m_process` | 同上 |
| ライン | `m_line` | 同上 |
| 仕入先 | `m_supplier` | 同上 |
| 得意先 | `m_customer` | 同上 |
| 稼働カレンダ | `m_calendar_day` | 同上 |
| BOM（親品番のヘッダ） | `m_bom` | 同上（BOSS指示 2026-10-10） |
| BOM明細（子品番・員数） | `m_bom_item` | 同上 |
| ルーティング（ヘッダ） | `m_routing` | 同上（BOSS指示 2026-10-10） |
| ルーティング工程 | `m_routing_step` | 同上 |
| ルーティング工程の材料 | `m_routing_step_material` | 同上（BOSS指示 2026-10-10。作成する） |

BOM・ルーティングは、ヘッダと明細が別テーブルのため、1テーブル1ビューの原則に従い、別々のビューにする。ヘッダと明細の結合は、AIがビュー同士で行う（結合キーは各ビューの説明に書く）。

ユーザー関連（BOSS指示 2026-10-10。作成する）

| 候補 | 元テーブル | 状態 |
|---|---|---|
| ユーザー | `auth_user`（Django標準） | 未着手 |
| ユーザープロフィール（部署・役職） | `accounts_userprofile` | 未着手 |
| 部署 | `accounts_department` | 未着手 |

目的（BOSS指示 2026-10-10）：作業者別の実績、部署別の集計。

ユーザーは、パスワード（ハッシュ）・メールアドレス・個人名などを持つ。公開する列は、全フィールドの一覧からBOSSが決める。パスワード・認証情報・連絡先は、公開案から外す。個人名を公開する場合は、外部AIへ送る前に一時IDへ置換する（残業の個人別ビューと同じ扱い）。

マスタビューができた後、`SCREEN_SQL_TABLES`が許可している元テーブル（`m_supplier`・`m_product`・`m_line`・`m_calendar_day`）をビューへ置き換える。置き換えは既存動作の変更になるため、実施前にBOSSへ報告し、承認を得る。

### 優先1：正規実績・確定実績

| 候補ビュー | 対象 | 作成方針 |
|---|---|---|
| `v_ai_process_production_actual` | `t_process_realtime_record`の工程生産実績 | `record_type='PRODUCTION'`だけを対象にし、仕入実績を含めない |
| `v_ai_laser_production_actual` | レーザー実績 | レーザー画面と同じく、終了済み構成部品明細だけを対象にする |
| `v_ai_brake_production_actual` | ブレーキ・スポット実績 | `END`・`PAUSE`の数量だけを生産数として扱う |
| `v_ai_scrap_confirmed` | 確定仕損 | `event_type='SCRAP'`かつ確定・一部使用可の正味数量だけを対象にする |
| `v_ai_interruption` | 中断・強制終了 | `PAUSE`・`TEMP_END`の件数と理由を対象にする |

生産実績は、工程実績・レーザー実績・ブレーキ実績を無条件に`UNION`または合計しない。質問・工程ごとに正規データソースを選び、同じ事実を二重計上しない。

### 優先2：残業

| 候補ビュー | 対象 | 作成方針 |
|---|---|---|
| `v_ai_overtime_summary` | 残業申請のグループ別・日別集計 | 時間外・休日出勤の承認対象状態だけを対象にし、個人名を含めない |
| `v_ai_overtime_personal` | 個人別残業集計 | `overtime.personal_summary`権限を持つ利用者に限定して使用する。外部AIへ送る場合は一時IDへ置換する |

残業は申請時間であり、打刻実績ではない。

なお、残業の個人別について、「個人の順位付け・評価・査定に使用しない」とした従来の規定は、BOSS指示により取り下げた（2026-10-10）。

### 優先3：マスタ・将来領域

品番・工程・ライン・仕入先・得意先・稼働カレンダ・BOM・ルーティングのマスタビューは、優先0で先に作成する。仕入計画、在庫、進度、受注全体、製造指示、BOM展開明細は、数値定義が確定するまで作成しない。

## 4. 各ビューの作成前確認

### 4.1 ビュー設計の原則（BOSS決定）

1. **基本は1テーブル1ビュー。** 1つのビューは1つの元テーブルから、必要な列だけを取得する。1つの元テーブルに複数のビューを作ってよい（例：記録タイプ別）。1ビューでは都合が悪い場合は、作成前に理由をBOSSへ報告する。
2. **ビューの中で結合してよいのは、マスタの属性を付けるときだけ。** 例：品番IDだけの実績に、品番コード・品名を付ける。
   - 結合先はマスタとし、結合キーはマスタの主キーにする。
   - `LEFT JOIN`を使い、実績の行数を増減させない。作成時に、元テーブルとビューの件数が一致することをDBで確認する。
   - 公開してよい列だけを結合する。個人名・連絡先を持つ列は結合しない。
   - 結合は「してよい」であり、必須ではない。§8.3（2026-10-08）のとおり、AIにビュー同士を結合させる方式も併用できる。どちらにするかは、ビューごとにBOSSが決める。
3. **実績同士を結合するビューは作らない。** 実績を比べる分析（入荷と出荷など）は、結合せず、同じ列に揃えて`UNION ALL`し、種類ごとに`SUM(CASE WHEN)`で並べる。結合すると目的ごとにビューが増えるため。
4. **対象行の絞り込み（`WHERE`）は、1つの元テーブルの中でなら付けてよい。** 例：`record_type='PRODUCTION'`。仕入実績の混入を、ビューの側で防ぐ。
5. **元テーブルの全フィールドを一覧にし、公開するかどうかはBOSSが決める。** 一覧には、列名・型・業務上の意味・公開案を載せる。ビューに含める列は、BOSSが公開と決めた列だけとする。非公開の列は、ビューに含めない。
6. **マスタビューを先に作る。** 実績ビューは、その後に作る。
7. **列の説明（AI用DB辞書・`ANALYSIS_VIEWS`の説明）は、各仕様書で意味を確認してから書く（BOSS指示 2026-10-10）。** 列名や項目名からの推測で書かない。仕様書に定義がない列は「意味は未確認」と書く。確認した出典（仕様書名・行）は、確認明細または各ビューの節に残す。

8. **ビューのマイグレーションは、標準SQLだけで書く（BOSS承認 2026-10-10）。** 将来、MySQLからPostgreSQLへ変更し、AI検索もDBへ直接アクセスしない予定のため。バッククォート・`DEFINER`・`SQL SECURITY`・DBの修飾など、MySQL固有の記法はマイグレーションに入れない。定義者と権限は、DBごとに書き方が違うため、マイグレーションに含めず、別の手順SQL（開発・本番とも、実行はBOSS）にする。
9. **ビューの定義者は、必ず専用ユーザー `pm_ai_view_owner` にする（BOSS指示 2026-10-10）。** `root` など、マイグレーションを実行したDBユーザーを定義者のまま残さない。
   - マイグレーション（`migrate`）でビューを作ると、定義者は実行したDBユーザー（`root` 等）になる。そのため、`migrate` の**直後に**、次の2つを行う。
     1. `pm_ai_view_owner` に、そのビューが読む元テーブルの**公開列だけ**の `SELECT` を、列単位で付与する（`GRANT SELECT (列, …) ON 元テーブル TO pm_ai_view_owner@localhost`）。
     2. `CREATE OR REPLACE DEFINER = pm_ai_view_owner@localhost SQL SECURITY DEFINER VIEW …` で、ビューを作り直し、定義者を付け替える。
   - ビューを新規に作る・変更するたびに、同じ手順を行う。手順SQLは、ビューごとに、各ビューの節（例 §9.3）へ書く。
   - 確認：`information_schema.VIEWS` の `DEFINER` が `pm_ai_view_owner@localhost` であること、`pm_ai_reader` の接続でビューが読めること、非公開列が読めないこと。
   - 理由：公開列だけに権限を絞る設計を効かせるため。定義者が存在しないとエラー1449でビューが読めなくなるため、`root` のように環境で変わるユーザーを使わない。
   - 実施状況：`v_ai_product` は開発DBで実施済み（2026-10-10。定義者 `pm_ai_view_owner@localhost`、公開32列の列権限、`pm_ai_reader` の接続で件数2,850・有効2,808、`image_url` は読めないことを確認）。本番は未実施（BOSSが実行）。
   - PostgreSQLへ移行した後は、定義者の考え方を「所有者を専用ロールにする」に読み替える（§9.3参照）。

### 4.1-1 仕様書で確認できた品番の列の意味（2026-10-10 調査）

| 列 | 仕様書にある意味 | 出典 |
|---|---|---|
| `order_lot_min`・`order_lot_multiple` | 発注量＝不足数を発注倍数の倍数に切り上げ、最小発注数未満なら最小発注数にする。`order_qty = ceil(不足数 / 倍数) × 倍数`、`order_qty = max(order_qty, 最小発注数)` | 自動発注提案仕様書.md:211-212 |
| `transfer_destination` | 移動先。値の表示順は 社内塗装・CWL・興和・直納・社内ライン・その他/未設定 | 自動納入リスト送信仕様書.md:87,91 |
| `category` | 値は ASSEMBLY・SINGLE・MATERIAL・PURCHASED・OUTSOURCED・UNKNOWN の6種。各値の意味の定義は見つからない（受注展開時の既定は PURCHASED＝購入品） | ER_diagram_v3.md:34、受注管理仕様書.md:777 |
| `is_virtual_set` | 仮想セット品番＝連産品。子実績を展開する | 仕入実績record_type分離仕様書.md:37 |
| `is_final_product`・`is_line_final_product` | 受注展開では最終品かどうかでリードタイムの扱いを分ける。ライン最終品は、前工程需要で後ラインの親が無い日の代替に使う。定義の文章は見つからない | 受注展開仕様書.md:418、前工程需要計算仕様書.md:93-101 |
| `management_unit`（品番） | 品番の管理区分としての定義は見つからない（工程の管理単位は DAY=日単位管理・MINUTE=分単位管理） | モデル定義のみ |
| `stock_location`・`identification_code`・`processing_area`・`size_*`・`specific_gravity` | 定義の文章は見つからない | — |

### 4.2 作成前確認の項目

各ビューは、次の項目を文書化し、BOSSの承認後に作成する。

| 確認項目 | 内容 |
|---|---|
| 業務目的 | AIが何を分析・説明するためのビューか |
| 元テーブル | 参照するテーブルと結合条件 |
| 対象行 | ステータス、レコード種別、期間などの抽出条件 |
| 数値定義 | 数量・件数・時間の正式な算出方法 |
| 公開フィールド | AIへ見せる列と列の業務上の意味 |
| 非公開フィールド | 連絡先、認証情報、未承認の自由記述などの除外対象 |
| 個人情報 | 利用権限、一時ID化、外部AI送信可否 |
| 検証方法 | 既存画面・DB実データとの件数、数量、期間の照合方法 |

得意先・仕入先は名称ではなくコードを原則とする。例として、クボタは`000196`、ホウダテクニカルは`000180`である。

## 5. 実装手順

### 5.1 定義作成

1. 対象モデルと既存画面の集計ロジックを確認する。
2. 元テーブル、結合条件、対象行、数値定義、フィールド一覧を作成する。
3. 代表的な実データで、既存画面と件数・数量・対象期間を照合する。
4. BOSSがビュー定義とAI公開範囲を承認する。

### 5.2 マイグレーション

1. `pm_backend/apps/ai/migrations/`へ新規マイグレーションを作成する。
2. `CREATE OR REPLACE VIEW v_ai_... AS ...`でビューを定義する。
3. ビューの定義者には、開発・本番に常に存在する専用サービスユーザーを使用する。`root`を定義者に使用しない。
4. ロールバック用に`DROP VIEW IF EXISTS v_ai_...`または直前のビュー定義を用意する。
5. 開発DBへ適用し、`SELECT`実行と既存画面との照合を行う。

### 5.3 AI公開設定

1. `pm_ai_reader`へ、対象`v_ai_...`ビューの`SELECT`だけを付与する。
2. 元テーブルへの`SELECT`、更新、削除、DDL、ストアドプロシージャ実行権限を持たないことを確認する。
3. `pm_backend/apps/ai/services/sql_queries.py`のAI用DB辞書へ、ビュー名、公開フィールド、業務上の意味を追加する。
4. `SCREEN_SQL_TABLES`へ、画面起点ごとに許可するビューだけを追加する。
5. [AI運用規約・AI用DB辞書](AI運用規約・AI用DB辞書.md)と[AIチャット仕様書](AIチャット仕様書.md)を更新する。

### 5.4 本番反映

1. 本番DBに、ビュー定義者ユーザーと`pm_ai_reader`の権限が存在することを確認する。
2. マイグレーションを適用する。
3. `SHOW CREATE VIEW`と`SHOW GRANTS`で、ビュー定義と権限を確認する。
4. `pm_ai_reader`でビューが読め、元テーブルへの直接参照が拒否されることを確認する。
5. PM画面の既存業務処理が影響を受けないことを確認する。

## 6. 検証項目

- 既存画面とビューの件数・数量・対象期間が一致する。
- 仕入実績が生産実績へ混入しない。
- 複数実績ソースを合計して二重計上しない。
- `pm_ai_reader`はビューだけを`SELECT`できる。
- ビューからの`INSERT`、`UPDATE`、`DELETE`はできない。
- 定義者が存在せずエラー1449になる状態がない。
- 個人情報・連絡先・認証情報・未承認の自由記述が公開フィールドに含まれない。
- 外部AIへ送る値は、運用規約に定めた一時ID化・送信方針に従う。

## 7. 完成条件

- 優先1の各ビューについて、業務定義・公開フィールド・検証結果が承認済みである。
- 追加ビューはAI用DB辞書・画面別許可リスト・運用規約へ反映済みである。
- 開発・本番で、AI用ビューの実行可否と`pm_ai_reader`の権限を確認済みである。
- AI分析画面は、承認済みの`v_ai_...`ビューだけを使用できる。

## 8. 仕入先マスタのビュー `v_ai_supplier` の作成前確認（案。2026-10-08。BOSSの承認待ち）

実機の安定性の評価（試験T8「9月の入荷を仕入先ごとに集計して」）で、結果の表が「仕入先ID」（`supplier_id`＝`m_supplier.id`。データベースの内部の番号）だけになった。現場が分かるのは、仕入先名か、せめて仕入先コード。入荷実績ビューには、仕入先の列が`supplier_id`しかなく、仕入先マスタのビューも、まだない。§3 優先3「マスタ・将来領域」の、仕入先を、分析画面で必要になったため、追加する。

| 確認項目 | 内容 |
|---|---|
| 業務目的 | AIが、仕入先をコード・名前で、分析・説明できるようにする（仕入先ごとの入荷の集計の、表示に、内部のIDを出さない）。仕入先の一覧・種類別の件数にも使う |
| 元テーブル | `m_supplier`（29行。`supplier_code`は一意・空なし。入荷に出る仕入先6社は、すべて、マスタにある＝孤立なし） |
| 対象行 | 全行（絞り込みなし）。ビューは、データを複製しない |
| 数値定義 | なし（マスタ。件数は、行数） |
| 公開フィールド | `id`（仕入先の内部ID。他のビューとの結合用）、`supplier_code`（仕入先コード）、`supplier_name`（仕入先名）、`supplier_type`（`purchase`=購入先・`outsource`=外作先・`both`=両方） |
| 非公開フィールド | `order_email`（発注先メール）、`contact_person`（担当者名）、`phone_number`（電話番号）、`calendar_id`（カレンダーのID。分析に不要） |
| 個人情報 | 仕入先名は会社名で、連絡先（メール・担当者・電話）は、含めない。結果の画面には出るが、**AIへは、列名と型だけを送り、値は送らない**。外部AIへ送る目的文の、名称→コード置換は、従来どおり |
| 検証方法 | `m_supplier`の行数（29）と、ビューの行数が一致。コードの一意性。入荷実績ビューの仕入先別の集計（9月: 仕入先16=20,259・仕入先8=11,270）を、コード・名前つきで、照合。`pm_ai_reader`でビューが読め、元テーブルの直接参照は、ビューだけに絞った権限では、拒否される |

### 8.1 あわせて変更するもの（案）
1. **`v_ai_purchase_receipt`に、`supplier_code`・`supplier_name`を追加**（`m_supplier`と`supplier_id`で、左結合。仕入先がない行も、残す。入荷の行は、増えない）。AIが、ビューどうしを結合しなくても、仕入先のコード・名前を使える（小さいモデルでも、取り違えにくい）。
2. **AIへの指示・対応表**: 「仕入先・外作先」→`supplier_code`・`supplier_name`。仕入先ごとの集計は、コードと名前を出し、**内部のID（`*_id`）は、結果に出さない**（品番の「品番→製品名→数量」と同じ考え方）。
3. **ビューの定義者`pm_ai_view_owner`の権限**: `m_supplier`の`id`・`supplier_code`・`supplier_name`・`supplier_type`の列単位の`SELECT`を追加（連絡先の列は、付けない）。
4. **AI用DB辞書**（`sql_queries.py`の`BASE_SQL_SCHEMA`・`TABLE_NOTES`）・列の型・`ANALYSIS_VIEWS`の説明・`SCREEN_SQL_TABLES`（仕入画面の許可ビューへ`v_ai_supplier`）・仕様書・運用規約を更新。
5. 手順は、§5のとおり: マイグレーションで`CREATE OR REPLACE VIEW`（定義者は`pm_ai_view_owner@localhost`。rootを使わない）→開発で適用・照合→本番は、SQLを用意して、BOSSが実行（権限の付与・ビューの作成。本番の変更は、承認と、バックアップが必要）。

### 8.2 BOSSに決めてほしいこと
- 公開する列の範囲（上の4列でよいか。**仕入先名を、公開するか**。§4 の原則は「名称ではなくコード」だが、現場が分かるのは名前のため、コードと名前の両方を、おすすめする）。
- 入荷実績ビューへ、`supplier_code`・`supplier_name`を足すか。
- 得意先・品番・ライン・工程など、他にも、内部のIDだけの列があるか（現状の入荷実績ビューの`line_id`・`process_id`は、ラインと工程のIDで、コード・名前の列が、ない）。

### 8.3 設計メモ（BOSS指示 2026-10-08。「ビュー作成は大きなプロジェクトのため、別に検討する」。コードの変更なし）

**決定したこと**
- `v_ai_supplier`の公開列は、`id`・`supplier_code`・`supplier_name`・`calendar_id`・`supplier_type`。非公開は、`order_email`・`contact_person`・`phone_number`。ビューの定義者`pm_ai_view_owner`の権限も、同じ5列の`SELECT`。
- **`v_ai_purchase_receipt`には、仕入先の列を足さない**。都度、列を足すのは避け、**AIに、2つのビューを結合させる**（入荷の`supplier_id`＝仕入先の`id`）。
- 結合が、小さいモデルで、安定して成功するかは、**試験で、成功率を見て決める**（T8と同じ目的で、数回）。成功率が低ければ、よく使う組み合わせだけ、結合済みの列を足す（併用）。

**AIへの指示の案**
1. 結果には、内部のID（`*_id`）を出さない。仕入先ごとの集計は、コードと名前を出す（品番→製品名と、同じ考え方）。
2. 出したい列が、内部のIDしかないときは、**他のビューに、コード・名前の列がないか、確認する**。
3. 手順を考える前に、**ビューの構造・説明・ビューどうしの関係（結合のキー）を、最初に確認する**。作業の順序は、「①列の意味を読む→②目的の言葉を列に結び付ける→③**ビューどうしの関係を確認する**→④手順を作る」。ビューの説明文に、関係（例: 入荷の`supplier_id`＝仕入先の`id`）を、書く。
4. 分析に必要なビューは、**データ範囲に、すべて入れる**（マスタのビューを選び忘れると、コード生成が、「列がない」と止まる。T2の「納入場名」と同じ型の失敗）。

**機械の安全網の案**
- 結果に出す列が、`supplier_id`などの内部IDだけで、対応するマスタのビューが、データ範囲にないときは、承認の前に、警告を出す（列の言葉の食い違いの警告と、同じ仕組み）。

**留意**
- 仕入先マスタにない仕入先IDの入荷は、今のデータでは0件（入荷の6社は、すべて、マスタにある）。結合の種類（内部結合・左結合）は、重要度が低い。将来、マスタにない行ができても、黙って消えるだけなので、結果の件数を、確認できるとよい。

**別に検討する課題（大きい変更）**
- **日付列のないビュー（マスタ）を扱う**（取り下げの決定: BOSS 2026-10-10。「全ビューに日付列を必須とする」規定を取り下げ、`date_field=None`で全行取得する方式に変更。実装は§11サイクルB）: 従来の仕組みは、すべてのビューが日付列を持つ前提だった（分析案の検証・件数の確認・データの取り出し〔`analysis_data_service`・`analysis_execution_service`〕）。マスタは、期間で絞らず、全行を取得する。
- ビューの作成（マイグレーション）・権限・辞書・画面別の許可リスト・指示・試験・仕様書・運用規約・本番のSQL。

## 9. 品番マスタのビュー `v_ai_product` の作成前確認（案。2026-10-10。BOSSの承認待ち）

マスタビューの最初の1つ。公開する列は、[AIマスタビュー確認明細](AIマスタビュー確認明細.md)のBOSS判断のとおり。

| 確認項目 | 内容 |
|---|---|
| 業務目的 | AIが、品番をコード・名前・分類・寸法・発注条件で、分析・説明できるようにする。実績ビューの品番ID・品番コードから、品名や分類を引く |
| 元テーブル | `m_product` の1つだけ。結合なし（行数2,850） |
| 対象行 | 全行（絞り込みなし）。有効2,808・無効42。無効品番は`is_active`で、AIが絞る |
| 数値定義 | なし（マスタ）。件数は行数。`product_code`は2,850行で重複なし・空なし |
| 公開フィールド（32列） | `id`、`product_code`、`product_name`、`category`、`unit`、`unit_price`、`standard_lt_days`、`stock_location`、`processing_area`、`line_id`、`process_id`、`next_process_id`、`management_unit`、`is_final_product`、`is_line_final_product`、`is_virtual_set`、`order_lot_min`、`order_lot_multiple`、`is_special_management_material`、`specific_gravity`、`size_length`、`size_width`、`size_thickness`、`transfer_destination`、`model_name`、`identification_code`、`product_group_id`、`used_container_id`、`capacity`、`is_active`、`created_at`、`updated_at` |
| 非公開フィールド | `image_url`、`product_name_halfwidth`、`is_phantom`、`self_lt_days`（BOSS判断） |
| 個人情報 | なし（個人名・連絡先・認証情報の列を含まない）。社内AIの列名検査（`SENSITIVE_IDENTIFIER`）に当たる列名もない |
| 検証方法 | ①ビューの行数＝`m_product`の行数（2,850）②`product_code`の一意性③`is_active`の件数（有効2,808・無効42）④`pm_ai_reader`でビューが読め、`m_product`の直接参照が拒否される⑤非公開の4列がビューにない |

### 9.1 未確認・注意
- `unit_price`は2,386行がNULL（単価の入っている品番は464行）。`line_id`は1,833行、`process_id`は2,003行がNULL。AIの説明文に「空の品番がある」と書く。
- `category`は6種（ASSEMBLY 1,015、OUTSOURCED 697、SINGLE 587、PURCHASED 284、UNKNOWN 198、MATERIAL 53）とNULL 16行。各値の業務上の意味は未確認。
- `management_unit`（品番の管理区分）はDAY 787・MINUTE 7・空2,056。工程の管理単位（DAY=日単位管理、MINUTE=分単位管理）と同じ意味かは未確認。
- `unit_price`は金額情報。BOSS判断で公開としたため、公開する。

### 9.2 あわせて変更するもの（案）
1. マイグレーション：`CREATE OR REPLACE VIEW v_ai_product AS SELECT <32列> FROM m_product`。ロールバックは`DROP VIEW IF EXISTS v_ai_product`。
2. ビューの定義者`pm_ai_view_owner`の権限：`m_product`の列単位の`SELECT`を、32列へ広げる（現在は`id`・`product_code`・`product_name`の3列だけ。既存の`v_ai_shipment`が使用中）。本番では、権限付与のSQLをBOSSが実行する。
3. `pm_ai_reader`へ`v_ai_product`の`SELECT`だけを付与する。
4. AI用DB辞書（`sql_queries.py`）・`ANALYSIS_VIEWS`の説明・`ANALYSIS_COLUMN_TYPES`（開発DBの`SHOW COLUMNS`に合わせる）・`SCREEN_SQL_TABLES`・仕様書・運用規約を更新する。
5. 既存の`v_ai_shipment`（`m_product`を結合している）は、今回は変更しない。

### 9.3 実装の進捗（2026-10-10。generator。検証はevaluator待ち）

**実装済み（コード・文書）**
- `pm_backend/apps/ai/migrations/0034_ai_product_view.py` 新規。`CREATE OR REPLACE VIEW v_ai_product`（32列・別名なし・WHEREなし・結合なし）、ロールバックは`DROP VIEW IF EXISTS v_ai_product`。依存は`ai 0033`と`masters 0085`。`makemigrations --dry-run`は「No changes detected」。
- `sql_queries.py`：`BASE_SQL_SCHEMA`に`v_ai_product`（32列）、`TABLE_NOTES`に説明を追加（`ai_home`は`BASE_SQL_SCHEMA`の全キーを引くため自動で対象に入る）。
- `AI運用規約・AI用DB辞書.md`に§6.5-4を追加。

**実施していないこと（BOSS実行）**
- 実装時点（2026-10-10）は、`migrate`・ビュー作成・権限付与（GRANT）が未実行だった。**その後、開発DBで実施済み**（BOSS指示。`migrate ai 0034`でビュー作成、列権限の付与、定義者を`pm_ai_view_owner@localhost`へ付け替え。§4.1の9番・§12参照）。本番は未実施。
- 開発で確認済み（読み取りのみ）：マイグレーションのSELECT文は`m_product`に対して実行でき、2,850行・32列を返す。

**権限の付与方式の調査結果**：既存ビューの権限はマイグレーションに含まれず、手動SQL（`output/prod_view_definer_setup.sql`、開発は手動作成）で付与されている。そのため今回も手動SQLとする。
- 注意：マイグレーションで作ったビューの定義者は、マイグレーションを実行したDBユーザー（`root`等）になる。`v_ai_shipment`は別途`DEFINER = pm_ai_view_owner`で作り直した経緯がある。`v_ai_product`も、ビュー作成後に下の手順2で定義者を付け替える必要がある。

**実行手順SQL（開発・本番とも。実行はBOSS。本番は事前にバックアップ）**
```sql
-- 1. 定義者の権限を32列へ広げる（実行はrootなど管理者で）
GRANT SELECT (`id`, `product_code`, `product_name`, `category`, `unit`, `unit_price`, `standard_lt_days`,
  `stock_location`, `processing_area`, `line_id`, `process_id`, `next_process_id`, `management_unit`,
  `is_final_product`, `is_line_final_product`, `is_virtual_set`, `order_lot_min`, `order_lot_multiple`,
  `is_special_management_material`, `specific_gravity`, `size_length`, `size_width`, `size_thickness`,
  `transfer_destination`, `model_name`, `identification_code`, `product_group_id`, `used_container_id`,
  `capacity`, `is_active`, `created_at`, `updated_at`)
  ON `pm_db`.`m_product` TO 'pm_ai_view_owner'@'localhost';
-- 2. マイグレーション適用後（開発: python manage.py migrate / 本番: docker exec ... migrate）、定義者を付け替える
-- （DBの選択に依存しないよう、ビューと元テーブルは pm_db で修飾する）
CREATE OR REPLACE DEFINER = `pm_ai_view_owner`@`localhost` SQL SECURITY DEFINER VIEW `pm_db`.`v_ai_product` AS
  SELECT id, product_code, product_name, category, unit, unit_price, standard_lt_days, stock_location,
  processing_area, line_id, process_id, next_process_id, management_unit, is_final_product,
  is_line_final_product, is_virtual_set, order_lot_min, order_lot_multiple, is_special_management_material,
  specific_gravity, size_length, size_width, size_thickness, transfer_destination, model_name,
  identification_code, product_group_id, used_container_id, capacity, is_active, created_at, updated_at
  FROM `pm_db`.`m_product`;
-- 3. 読み取りユーザーへビューのSELECTのみ付与
--    開発DBの pm_ai_reader は localhost と 10.0.1.36 の2ホストあり、どちらも pm_db 全体への SELECT を持つため、開発では本手順は実質不要
--    （開発では「元テーブルの直接参照が拒否される」確認も成立しない）。本番は SHOW GRANTS FOR で、ホストと権限を確認してから付与する
GRANT SELECT ON `pm_db`.`v_ai_product` TO 'pm_ai_reader'@'<本番のpm_ai_readerのホスト部。SHOW GRANTS FOR で確認>';
-- 4. 確認
SHOW CREATE VIEW `pm_db`.`v_ai_product`;  SHOW GRANTS FOR 'pm_ai_view_owner'@'localhost';
SELECT COUNT(*), SUM(is_active) FROM `pm_db`.`v_ai_product`;  -- 期待値: 2850, 2808
```

**PostgreSQL移行を考慮した構成（BOSS指示 2026-10-10。将来 MySQL→PostgreSQL へ変更し、AI検索もDBへ直接アクセスしない予定）**
- マイグレーション `0034` の `CREATE OR REPLACE VIEW v_ai_product AS SELECT <32列> FROM m_product` と `DROP VIEW IF EXISTS v_ai_product` は、バッククォート・`DEFINER`・`SQL SECURITY`・DBの修飾を使わない標準SQLで、MySQLでもPostgreSQLでもそのまま通る書き方にした。**PostgreSQLでの実行は未確認**（開発環境にPostgreSQLがない）。
- 定義者・権限は、DBごとに書き方が違うため、マイグレーションに含めず、別の手順SQLにしている。上の手順SQLはMySQL用。PostgreSQLへ移行するときは、次のように書き直す（未実行・未検証。移行時に確認する）。
  - 定義者：PostgreSQLの標準では、ビューの所有者の権限で元テーブルを読む（`security_invoker`を付けない場合）。所有者は専用ロール（例 `pm_ai_view_owner`）にする。`DEFINER`句はない。
  - 列単位の権限：`GRANT SELECT (列, …) ON m_product TO pm_ai_view_owner;`（PostgreSQLも列単位に対応）。
  - 読み取り：`GRANT SELECT ON v_ai_product TO pm_ai_reader;`。元テーブルへの権限は付けない。
  - 確認：`\d+ v_ai_product`、`\dp v_ai_product`、`SELECT count(*), sum(is_active::int) FROM v_ai_product;`。
- PostgreSQLでは、MySQLの`tinyint(1)`が`boolean`になる。`ANALYSIS_COLUMN_TYPES`の型の対応（真偽→BIGINT の0/1）は、移行時に見直す。

**未実装（要確認・BOSS判断待ち）**（2026-10-10 更新: サイクルA・B・Cで解消。§12参照）
- `ANALYSIS_VIEWS`／`ANALYSIS_COLUMN_TYPES`：**サイクルCで登録済み**（`date_field=None`＝全行取得、32列の型は開発DBの`SHOW COLUMNS`に合わせた。サイクルA=列型の拡張、サイクルB=date_fieldの任意化）。evaluator未検証。
- `SCREEN_SQL_TABLES`：計画書に許可する画面の指定がないため追加していない（`ai_home`は自動で対象）。マスタ画面（`masters`）・生産・出荷等への許可はBOSS判断（**今も未実装**）。`TERM_COLUMNS`も未変更。
- 列型：開発DBでビュー作成後に`SHOW COLUMNS FROM v_ai_product`を取得し、サイクルCで`ANALYSIS_COLUMN_TYPES`へ反映した（§12）。

## 10. サイクルA: 列型の拡張（2026-10-10。BOSS承認済みの範囲。実装済み・evaluator未検証）

**実装内容**（既存ビュー`v_ai_shipment`・`v_ai_purchase_receipt`の動作は変えない。画面の動作も変わらない）
- `pm_backend/apps/ai/services/analysis_execution_service.py`：`_cell`のDECIMAL分岐を`DECIMAL(p,s)`の一般形へ（`parse_decimal_type`：p 1〜38・s 0〜p、`_decimal_cell`：丸めず、小数桁・整数部の桁の超過・NaN・無限大は`unsupported_value`）。BIGINTは`int`のみ（bool拒否）を維持。
- `analysis-sandbox/job/job_main.py`：`COLUMN_TYPES`の完全一致に加え、`is_allowed_column_type`（`fullmatch`の厳密な正規表現）でDECIMAL(p,s)を許可。`DECIMAL(18,3)`は固定の許可リストから正規表現側へ移したが、結果は従来どおり許可。
- 変更していない：`ANALYSIS_COLUMN_TYPES`、BASE_SQL_SCHEMAとの一致検査、`analysis_guard_runtime.py`（WRAPPER_VERSION不変）。
- 仕様書：`AI分析基盤仕様書.md`の列型（DECIMALの一般化）を追記。

**検証結果**
- `python manage.py test ai.test_analysis_execution`：40件、OK（skipped=2は実launcher用の既存skip）。追加3件（DECIMAL一般形・型名の厳密解釈・BIGINT）を含む。既存の拒否ケース（`test_unsupported_values_are_rejected`）も合格。
- `python -m unittest discover -s analysis-sandbox/tests -p "test_column_types.py"`：2件、OK（job_mainの`validate_header`と`is_allowed_column_type`。Docker・DuckDB不使用）。

**追加修正：DECIMAL(p,s)の先頭ゼロ拒否（2026-10-10。BOSS承認済み）**
- 変更：`analysis_execution_service.py`の`parse_decimal_type`と`job_main.py`の`is_allowed_column_type`の正規表現を、p・sとも「0単独、または先頭が1〜9の1〜2桁」に統一。許可例：DECIMAL(18,3)・(10,0)・(5,0)・(38,2)・(3,3)。拒否例：DECIMAL(18,03)・(01,00)・(018,03)・(00,0)・(5,00)。範囲検査（p 1〜38、s 0〜p）は従来どおり。理由：型名がそのままDuckDBの`CREATE TABLE`に入り、DuckDBが先頭ゼロを受け付けるか未確認のため、最初から通さない。通常の書き方の挙動は変わらない。
- 試験追加：`ai.test_analysis_execution`に1件、`analysis-sandbox/tests/test_column_types.py`に1件。実行結果：`python manage.py test ai.test_analysis_execution`＝41件OK（skipped=2は既存の実launcher用skip）、`test_column_types.py`＝3件OK。
- BOSS承認事項の記録：①`DECIMAL(18,3)`の既存動作の変更（小数4桁以上・整数部15桁超の値を`unsupported_value`で拒否）を承認。②先頭ゼロ拒否を承認。③DuckDBでの取り込み確認（A6）は、作業Cの実データ試験とまとめて行う（未実施）。
- 仕様書：`AI分析基盤仕様書.md`のDECIMAL記述に「先頭ゼロの数字は拒否」を追記。

**未完了**
- A6（DuckDBコンテナ内での`DECIMAL(p,s)`の取り込み確認）：ローカルに`duckdb`が無い（`import duckdb`が失敗）ため**未確認**。コンテナの再ビルド・起動もしていない。
- evaluatorによる検証：未実施。
- サイクルB・C：対象外（未着手）。

**反映状況**：開発・本番とも未反映（コードと試験のみ。コミット・migrate・push・ビルドなし）。

## 11. サイクルB: date_field の任意化（日付なしビューの全行取得。2026-10-10。BOSS承認済みの範囲。実装済み・evaluator未検証）

**実装内容**（既存ビュー`v_ai_shipment`・`v_ai_purchase_receipt`のSQL文字列・パラメータ・検査は変えない。このサイクルでは`v_ai_product`を`ANALYSIS_VIEWS`へ登録しない＝サイクルC）
- `pm_backend/apps/ai/services/analysis_data_service.py`：`build_where(view, date_from, date_to, last_id=None)`を新設（WHERE句と束縛パラメータを返す共通関数）。日付ありは従来と同じ`WHERE `f` >= %s AND `f` <= %s`（+`AND `id` > %s`）、`date_field=None`は期間条件を付けず、`last_id`があるときだけ`WHERE `id` > %s`。`count_target_rows`がこれを使う。`ANALYSIS_VIEWS[view]['date_field']`は`[]`で参照（キーなしはKeyError。`.get()`で補わない）。`validate_datasets`の「日付フィールドを取得列に含める」検査は`date_field`が`None`でないビューにだけ適用。
- `pm_backend/apps/ai/services/analysis_execution_service.py`：`_pages`・`_count`が`build_where`を使う（ページ件数5,000行は変更なし）。
- 変更していない：`analysis_guard_runtime.py`、`ANALYSIS_COLUMN_TYPES`、AIへの指示文、`AIAnalysis.vue`、`TERM_COLUMNS`、`quantity_field`。
- 仕様書：`AI分析基盤仕様書.md`（期間必須規定の取り下げ、日付なしビューの全行取得・COUNT・照合・上限の扱い）。

**検証結果**（偽のDB接続・模擬launcher・SimpleTestCaseのみ。開発DBへの書き込みなし）
- 追加：`pm_backend/apps/ai/test_analysis_dateless_view.py` 10件（B1〜B8。試験側で`ANALYSIS_VIEWS`・`ANALYSIS_COLUMN_TYPES`・`BASE_SQL_SCHEMA`を`patch.dict`し、`date_field=None`の試験用ビュー`v_ai_testmaster`を使用）。`python manage.py test ai.test_analysis_dateless_view`＝10件OK。
- 既存の回帰（個別実行）：`ai.test_analysis_execution` 41件OK（skipped=2は既存の実launcher用）、`ai.test_analysis_planning` 16件OK、`ai.test_analysis_column_guide` 20件OK、`ai.test_analysis_codegen` 74件OK（skipped=2）、`ai.test_analysis_jobs` 25件OK、ほか`ai.test_analysis_*`のSimpleTestCaseのみの各モジュールがOK。
- 未実行：テスト用DBを要する`ai.test_analysis_*`の各モジュール（consult・execution_flow・followup・permissions・reference_*・refinement・run・template_*）は、既存のテスト用DB`test_*`の削除確認で停止し実行できなかった（削除はしていない）。

**未完了**
- evaluatorによる検証：未実施。上記のテスト用DBを要するモジュールの回帰：未確認。
- `v_ai_product`の`ANALYSIS_VIEWS`登録・指示文・画面・`TERM_COLUMNS`：サイクルC（未着手）。

**反映状況**：開発・本番とも未反映（コードと試験のみ。コミット・migrate・push・ビルドなし）。

## 12. サイクルC: v_ai_product の登録と文面（2026-10-10。BOSS承認済みの範囲。実装済み・evaluator未検証）

**実装内容**
- `analysis_data_service.py`：`ANALYSIS_VIEWS`に`v_ai_product`（label=品番マスタ、`date_field=None`、`quantity_field=None`、description）を追加。descriptionは§4.1-1で確認した意味だけを書き、定義のない列は「業務上の意味は未確認」と明記（`unit_price`・`line_id`・`process_id`の空、1行=1品番、`is_active`で絞る、実績ビューのproduct_idとidが結べることを含む）。新設`ai_view_definition(view)`は値が`None`のキーを出さない（日付ありの2ビューは従来と同じ内容）。`count_target_rows`の応答の各ビューに`period_applied`（日付ありtrue・日付なしfalse）を追加（応答の追加のみ）。
- `analysis_execution_service.py`：`ANALYSIS_COLUMN_TYPES`に`v_ai_product`の32列を追加（開発DBの`SHOW COLUMNS`を再取得して照合し、承認済みの対応と食い違いなし）。取得行数上限超過のメッセージを「条件を絞ってください(日付のあるビューは期間も絞れます)」へ（上限値は変更なし）。
- `analysis_planning_service.py`／`analysis_consult_service.py`：AIへ渡す定義を`ai_view_definition`経由に変更。分析案の指示の3か所と承認画面の「条件」（`_conditions_text`。日付ありだけなら従来と同じ文）を日付なしビューに対応（変更前後の全文は`AI分析基盤仕様書.md` §4.7-8に記載）。上限超過の承認時メッセージも同じ趣旨に変更。
- `analysis_codegen_service.py`：日付なしビューを含むときだけ、指示の末尾に`DATELESS_VIEW_RULE`を加える（日付ありだけの指示は1文字も変えない）。`analysis_guard_runtime.py`（WRAPPER_VERSION）は変更なし。
- `AIAnalysis.vue`：件数確認後、`period_applied=false`のビューの行に「期間: 適用しない（全行）」を表示。上限超過のメッセージを「条件（日付のあるビューは期間も）を絞って」へ。
- 変更していない：`SCREEN_SQL_TABLES`、`TERM_COLUMNS`、既存2ビューの`ANALYSIS_VIEWS`・`ANALYSIS_COLUMN_TYPES`。
- 試験：新規`ai.test_analysis_product_view`（11件）。`ai.test_analysis_column_guide`の1件（`process_id`を説明に書かない検査）は、出荷・入荷の説明に限定し、品番マスタは「空の品番がある」と書く承認内容に合わせて更新した。

**検証結果**（開発。読み取りのみ・テスト用DBなし）
- 個別実行：`ai.test_analysis_product_view` 11件OK、`ai.test_analysis_dateless_view` 10件OK、`ai.test_analysis_execution` 41件OK（skipped=2は実launcher用）、`ai.test_analysis_planning` 16件OK、`ai.test_analysis_column_guide` 20件OK、`ai.test_analysis_codegen` 74件OK（skipped=2）、`ai.test_analysis_jobs` 25件OK、`ai.test_analysis_multi_period` 20件OK、`ai.test_analysis_period_warning` 16件OK、`ai.test_analysis_worker_version` 12件OK。フロント`pm-ui/scripts/test-analysis-*.mjs` 7本OK（codegen 67・consult 23・error-banner 6・execution 35・external-confirmation 4・status-monitor 13・templates 53、fail 0）。
- 開発DBの実データ（`pm_ai_reader`接続）：`count_target_rows`相当2,850（`period_applied=false`）、`_count`2,850、`_pages`の全ページ合計2,850（5,000行・1,000行の両方）。全2,850行×32列で`_cell`が`unsupported_value`を出さない（エラー0件）。NULLは保たれる（`unit_price`2,386・`specific_gravity`1,709・`line_id`1,833・`process_id`2,003・`created_at`0）。`unit_price`=Decimal('42.00')→'42.00'、`specific_gravity`=Decimal('7.8500')→'7.8500'、`created_at`→'2025-12-05 04:16:35.000000'。

**未完了**
- evaluatorによる検証：未実施。実機（AIを使う）の再試験：**未実施**。DuckDBコンテナ内での取り込み確認（A6）：未実施。テスト用DBを要する`ai.test_analysis_*`（consult等）：未実行。
- 画面の「期間: 適用しない（全行）」は件数確認（preview）の後にだけ出る（分析案の段階では`period_applied`が無いため）。承認画面上部の「条件」の文は、分析案作成時から日付なしを反映する。

**反映状況**：開発DBのビュー`v_ai_product`は作成済み（定義者`pm_ai_view_owner`）。コードは未コミット。本番未反映（ビュー作成・権限付与・migrate・push・ビルドなし）。
