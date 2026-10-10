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
| ラインの所属グループ（ライン×グループの対応） | `accounts_unit_line_mapping` | 同上（BOSS指示 2026-10-10。ライン編集画面の「所属グループ」。`m_line`には列がないため、別のビューにする。全フィールドの一覧を作成し、BOSSが公開列を決める） |

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
   - 手順は、`python manage.py setup_ai_views --apply`（管理者で実行）で行える。手順SQL（§9.3・§14.1・§16.1・§19.1）は、コマンドが実行するSQLの記録として残す（§20）。
   - 実施状況：`v_ai_product` は開発DBで実施済み（2026-10-10。定義者 `pm_ai_view_owner@localhost`、公開32列の列権限（その後、2026-10-10 BOSS判断で30列へ修正。0037・§9.3参照）、`pm_ai_reader` の接続で件数2,850・有効2,808、`image_url` は読めないことを確認）。本番は未実施（BOSSが実行）。
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

## 8. 仕入先マスタのビュー `v_ai_supplier` の作成前確認（案。2026-10-08。**§17に置き換える**。以下は別セッションの古い草案で、設計原則§4.1と食い違う点がある）

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
| 公開フィールド（30列。2026-10-10 BOSS判断で`created_at`・`updated_at`を非公開に修正） | `id`、`product_code`、`product_name`、`category`、`unit`、`unit_price`、`standard_lt_days`、`stock_location`、`processing_area`、`line_id`、`process_id`、`next_process_id`、`management_unit`、`is_final_product`、`is_line_final_product`、`is_virtual_set`、`order_lot_min`、`order_lot_multiple`、`is_special_management_material`、`specific_gravity`、`size_length`、`size_width`、`size_thickness`、`transfer_destination`、`model_name`、`identification_code`、`product_group_id`、`used_container_id`、`capacity`、`is_active` |
| 非公開フィールド | `image_url`、`product_name_halfwidth`、`is_phantom`、`self_lt_days`、`created_at`、`updated_at`（BOSS判断。`created_at`・`updated_at`は2026-10-10に追加。BOSSが判断画面で非公開にしていたが、32列で実装・コミットしていたため、0037で修正） |
| 個人情報 | なし（個人名・連絡先・認証情報の列を含まない）。社内AIの列名検査（`SENSITIVE_IDENTIFIER`）に当たる列名もない |
| 検証方法 | ①ビューの行数＝`m_product`の行数（2,850）②`product_code`の一意性③`is_active`の件数（有効2,808・無効42）④`pm_ai_reader`でビューが読め、`m_product`の直接参照が拒否される⑤非公開の6列がビューにない |

### 9.1 未確認・注意
- `unit_price`は2,386行がNULL（単価の入っている品番は464行）。`line_id`は1,833行、`process_id`は2,003行がNULL。AIの説明文に「空の品番がある」と書く。
- `category`は6種（ASSEMBLY 1,015、OUTSOURCED 697、SINGLE 587、PURCHASED 284、UNKNOWN 198、MATERIAL 53）とNULL 16行。各値の業務上の意味は未確認。
- `management_unit`（品番の管理区分）はDAY 787・MINUTE 7・空2,056。工程の管理単位（DAY=日単位管理、MINUTE=分単位管理）と同じ意味かは未確認。
- `unit_price`は金額情報。BOSS判断で公開としたため、公開する。

### 9.2 あわせて変更するもの（案）
1. マイグレーション：`CREATE OR REPLACE VIEW v_ai_product AS SELECT <32列> FROM m_product`（0034。のち0037で30列へ修正）。ロールバックは`DROP VIEW IF EXISTS v_ai_product`。
2. ビューの定義者`pm_ai_view_owner`の権限：`m_product`の列単位の`SELECT`を、32列へ広げる（のち30列へ修正。§9.3）（現在は`id`・`product_code`・`product_name`の3列だけ。既存の`v_ai_shipment`が使用中）。本番では、権限付与のSQLをBOSSが実行する。
3. `pm_ai_reader`へ`v_ai_product`の`SELECT`だけを付与する。
4. AI用DB辞書（`sql_queries.py`）・`ANALYSIS_VIEWS`の説明・`ANALYSIS_COLUMN_TYPES`（開発DBの`SHOW COLUMNS`に合わせる）・`SCREEN_SQL_TABLES`・仕様書・運用規約を更新する。
5. 既存の`v_ai_shipment`（`m_product`を結合している）は、今回は変更しない。

### 9.3 実装の進捗（2026-10-10。generator。検証はevaluator待ち）

**実装済み（コード・文書）**
- `pm_backend/apps/ai/migrations/0034_ai_product_view.py` 新規。`CREATE OR REPLACE VIEW v_ai_product`（32列・別名なし・WHEREなし・結合なし）、ロールバックは`DROP VIEW IF EXISTS v_ai_product`。依存は`ai 0033`と`masters 0085`。`makemigrations --dry-run`は「No changes detected」。
- `sql_queries.py`：`BASE_SQL_SCHEMA`に`v_ai_product`（当初32列。2026-10-10に30列へ修正）、`TABLE_NOTES`に説明を追加（`ai_home`は`BASE_SQL_SCHEMA`の全キーを引くため自動で対象に入る）。
- `AI運用規約・AI用DB辞書.md`に§6.5-4を追加。

**実施していないこと（BOSS実行）**
- 実装時点（2026-10-10）は、`migrate`・ビュー作成・権限付与（GRANT）が未実行だった。**その後、開発DBで実施済み**（BOSS指示。`migrate ai 0034`でビュー作成、列権限の付与、定義者を`pm_ai_view_owner@localhost`へ付け替え。§4.1の9番・§12参照）。本番は未実施。
- 開発で確認済み（読み取りのみ）：マイグレーションのSELECT文は`m_product`に対して実行でき、2,850行・32列を返す。
- **2026-10-10 修正（BOSS承認）**：BOSSが判断画面で`created_at`・`updated_at`を非公開にしていたため、公開列を32列から30列に修正する。`0034_ai_product_view.py`は開発DBに適用済みのため書き換えず（32列の歴史的なSQLのまま）、新規マイグレーション`0037_ai_product_view_remove_dates.py`（`CREATE OR REPLACE VIEW v_ai_product AS SELECT <30列> FROM m_product`。ロールバックは0034の32列の定義へ戻す。依存は`ai 0036`・`masters 0085`で0034と同じ）で30列にする。実データ（開発DB、`pm_ai_reader`接続の読み取りのみ）：`m_product`から30列を読み、全2,850行×30列が`ANALYSIS_COLUMN_TYPES`の型で`_cell`を通る（エラー0）。**開発DBは、0037の`migrate`と手順SQLの実行（2026-10-10、BOSS承認のうえ、私が実行）で、30列に直した**（確認：30列で`created_at`・`updated_at`を含まない、`pm_ai_reader`で件数2,850・有効2,808、定義者`pm_ai_view_owner@localhost`、`pm_ai_view_owner`の`m_product`列権限は30列、`v_ai_shipment`は542件で影響なし）。本番は未反映。

**権限の付与方式の調査結果**：既存ビューの権限はマイグレーションに含まれず、手動SQL（`output/prod_view_definer_setup.sql`、開発は手動作成）で付与されている。そのため今回も手動SQLとする。
- 注意：マイグレーションで作ったビューの定義者は、マイグレーションを実行したDBユーザー（`root`等）になる。`v_ai_shipment`は別途`DEFINER = pm_ai_view_owner`で作り直した経緯がある。`v_ai_product`も、ビュー作成後に下の手順2で定義者を付け替える必要がある。

**実行手順SQL（開発・本番とも。実行はBOSS。本番は事前にバックアップ）**
```sql
-- 1. 定義者の権限を広げる（実行はrootなど管理者で）。2026-10-10 修正：30列（作成日・更新日は含めない）
GRANT SELECT (`id`, `product_code`, `product_name`, `category`, `unit`, `unit_price`, `standard_lt_days`,
  `stock_location`, `processing_area`, `line_id`, `process_id`, `next_process_id`, `management_unit`,
  `is_final_product`, `is_line_final_product`, `is_virtual_set`, `order_lot_min`, `order_lot_multiple`,
  `is_special_management_material`, `specific_gravity`, `size_length`, `size_width`, `size_thickness`,
  `transfer_destination`, `model_name`, `identification_code`, `product_group_id`, `used_container_id`,
  `capacity`, `is_active`)
  ON `pm_db`.`m_product` TO 'pm_ai_view_owner'@'localhost';
-- 2. マイグレーション適用後（開発: python manage.py migrate / 本番: docker exec ... migrate）、定義者を付け替える
-- （DBの選択に依存しないよう、ビューと元テーブルは pm_db で修飾する）
CREATE OR REPLACE DEFINER = `pm_ai_view_owner`@`localhost` SQL SECURITY DEFINER VIEW `pm_db`.`v_ai_product` AS
  SELECT id, product_code, product_name, category, unit, unit_price, standard_lt_days, stock_location,
  processing_area, line_id, process_id, next_process_id, management_unit, is_final_product,
  is_line_final_product, is_virtual_set, order_lot_min, order_lot_multiple, is_special_management_material,
  specific_gravity, size_length, size_width, size_thickness, transfer_destination, model_name,
  identification_code, product_group_id, used_container_id, capacity, is_active
  FROM `pm_db`.`m_product`;
-- 2-2. 【開発DBは32列で作成済みのため追加。2026-10-10】0037のmigrateと上の2の後に、定義者の作成日・更新日の列権限を取り消す
--      （順序注意：ビューが30列になる前に取り消すと、32列のビューが読めなくなる。本番は初回から30列のため、1のGRANTに2列を含めなければ本手順は不要）
--      v_ai_shipment は m_product の id・product_code・product_name だけを使うため、この取り消しの影響を受けない
REVOKE SELECT (`created_at`, `updated_at`) ON `pm_db`.`m_product` FROM 'pm_ai_view_owner'@'localhost';
-- 3. 読み取りユーザーへビューのSELECTのみ付与
--    開発DBの pm_ai_reader は localhost と 10.0.1.36 の2ホストあり、どちらも pm_db 全体への SELECT を持つため、開発では本手順は実質不要
--    （開発では「元テーブルの直接参照が拒否される」確認も成立しない）。本番は SHOW GRANTS FOR で、ホストと権限を確認してから付与する
GRANT SELECT ON `pm_db`.`v_ai_product` TO 'pm_ai_reader'@'<本番のpm_ai_readerのホスト部。SHOW GRANTS FOR で確認>';
-- 4. 確認
SHOW CREATE VIEW `pm_db`.`v_ai_product`;  SHOW GRANTS FOR 'pm_ai_view_owner'@'localhost';
SELECT COUNT(*), SUM(is_active) FROM `pm_db`.`v_ai_product`;  -- 期待値: 2850, 2808
```

**PostgreSQL移行を考慮した構成（BOSS指示 2026-10-10。将来 MySQL→PostgreSQL へ変更し、AI検索もDBへ直接アクセスしない予定）**
- マイグレーション `0034`（32列。のち `0037` で30列に修正）の `CREATE OR REPLACE VIEW v_ai_product AS SELECT <列> FROM m_product` と `DROP VIEW IF EXISTS v_ai_product` は、バッククォート・`DEFINER`・`SQL SECURITY`・DBの修飾を使わない標準SQLで、MySQLでもPostgreSQLでもそのまま通る書き方にした。**PostgreSQLでの実行は未確認**（開発環境にPostgreSQLがない）。
- 定義者・権限は、DBごとに書き方が違うため、マイグレーションに含めず、別の手順SQLにしている。上の手順SQLはMySQL用。PostgreSQLへ移行するときは、次のように書き直す（未実行・未検証。移行時に確認する）。
  - 定義者：PostgreSQLの標準では、ビューの所有者の権限で元テーブルを読む（`security_invoker`を付けない場合）。所有者は専用ロール（例 `pm_ai_view_owner`）にする。`DEFINER`句はない。
  - 列単位の権限：`GRANT SELECT (列, …) ON m_product TO pm_ai_view_owner;`（PostgreSQLも列単位に対応）。
  - 読み取り：`GRANT SELECT ON v_ai_product TO pm_ai_reader;`。元テーブルへの権限は付けない。
  - 確認：`\d+ v_ai_product`、`\dp v_ai_product`、`SELECT count(*), sum(is_active::int) FROM v_ai_product;`。
- PostgreSQLでは、MySQLの`tinyint(1)`が`boolean`になる。`ANALYSIS_COLUMN_TYPES`の型の対応（真偽→BIGINT の0/1）は、移行時に見直す。

**未実装（要確認・BOSS判断待ち）**（2026-10-10 更新: サイクルA・B・Cで解消。§12参照）
- `ANALYSIS_VIEWS`／`ANALYSIS_COLUMN_TYPES`：**サイクルCで登録済み**（`date_field=None`＝全行取得、32列の型は開発DBの`SHOW COLUMNS`に合わせた。2026-10-10に32列から30列へ修正。サイクルA=列型の拡張、サイクルB=date_fieldの任意化）。evaluator未検証。
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
- `analysis_execution_service.py`：`ANALYSIS_COLUMN_TYPES`に`v_ai_product`の32列を追加（2026-10-10に30列へ修正）（開発DBの`SHOW COLUMNS`を再取得して照合し、承認済みの対応と食い違いなし）。取得行数上限超過のメッセージを「条件を絞ってください(日付のあるビューは期間も絞れます)」へ（上限値は変更なし）。
- `analysis_planning_service.py`／`analysis_consult_service.py`：AIへ渡す定義を`ai_view_definition`経由に変更。分析案の指示の3か所と承認画面の「条件」（`_conditions_text`。日付ありだけなら従来と同じ文）を日付なしビューに対応（変更前後の全文は`AI分析基盤仕様書.md` §4.7-8に記載）。上限超過の承認時メッセージも同じ趣旨に変更。
- `analysis_codegen_service.py`：日付なしビューを含むときだけ、指示の末尾に`DATELESS_VIEW_RULE`を加える（日付ありだけの指示は1文字も変えない）。`analysis_guard_runtime.py`（WRAPPER_VERSION）は変更なし。
- `AIAnalysis.vue`：件数確認後、`period_applied=false`のビューの行に「期間: 適用しない（全行）」を表示。上限超過のメッセージを「条件（日付のあるビューは期間も）を絞って」へ。
- 変更していない：`SCREEN_SQL_TABLES`、`TERM_COLUMNS`、既存2ビューの`ANALYSIS_VIEWS`・`ANALYSIS_COLUMN_TYPES`。
- 試験：新規`ai.test_analysis_product_view`（11件）。`ai.test_analysis_column_guide`の1件（`process_id`を説明に書かない検査）は、出荷・入荷の説明に限定し、品番マスタは「空の品番がある」と書く承認内容に合わせて更新した。

**検証結果**（開発。読み取りのみ・テスト用DBなし）
- 個別実行：`ai.test_analysis_product_view` 11件OK、`ai.test_analysis_dateless_view` 10件OK、`ai.test_analysis_execution` 41件OK（skipped=2は実launcher用）、`ai.test_analysis_planning` 16件OK、`ai.test_analysis_column_guide` 20件OK、`ai.test_analysis_codegen` 74件OK（skipped=2）、`ai.test_analysis_jobs` 25件OK、`ai.test_analysis_multi_period` 20件OK、`ai.test_analysis_period_warning` 16件OK、`ai.test_analysis_worker_version` 12件OK。フロント`pm-ui/scripts/test-analysis-*.mjs` 7本OK（codegen 67・consult 23・error-banner 6・execution 35・external-confirmation 4・status-monitor 13・templates 53、fail 0）。
- 開発DBの実データ（`pm_ai_reader`接続）：`count_target_rows`相当2,850（`period_applied=false`）、`_count`2,850、`_pages`の全ページ合計2,850（5,000行・1,000行の両方）。全2,850行×32列（2026-10-10に30列へ修正。`created_at`は非公開）で`_cell`が`unsupported_value`を出さない（エラー0件）。NULLは保たれる（`unit_price`2,386・`specific_gravity`1,709・`line_id`1,833・`process_id`2,003・`created_at`0）。`unit_price`=Decimal('42.00')→'42.00'、`specific_gravity`=Decimal('7.8500')→'7.8500'、`created_at`→'2025-12-05 04:16:35.000000'。

**未完了**
- evaluatorによる検証：未実施。実機（AIを使う）の再試験：**未実施**。DuckDBコンテナ内での取り込み確認（A6）：未実施。テスト用DBを要する`ai.test_analysis_*`（consult等）：未実行。
- 画面の「期間: 適用しない（全行）」は件数確認（preview）の後にだけ出る（分析案の段階では`period_applied`が無いため）。承認画面上部の「条件」の文は、分析案作成時から日付なしを反映する。

**反映状況**：開発DBのビュー`v_ai_product`は作成済み（定義者`pm_ai_view_owner`）。コードは未コミット。本番未反映（ビュー作成・権限付与・migrate・push・ビルドなし）。

## 13. 工程マスタのビュー `v_ai_process` の作成前確認（2026-10-10。BOSS承認済み。公開9列。実装は§14）

公開する列は、[AIマスタビュー確認明細](AIマスタビュー確認明細.md) §2 のBOSS判断のとおり。§4.1 の設計原則（1テーブル1ビュー・標準SQL・定義者は `pm_ai_view_owner`・列の説明は仕様書で確認）に従う。

| 確認項目 | 内容 |
|---|---|
| 業務目的 | AIが、工程をコード・名前・ライン・管理単位・稼働率・設備台数で、分析・説明できるようにする。実績ビュー（工程実績・仕損・中断など）の工程IDから、工程の名前や属性を引く |
| 元テーブル | `m_process` の1つだけ。結合なし（行数46） |
| 対象行 | 全行（絞り込みなし）。有効45・無効1。無効の工程は`is_active`で、AIが絞る |
| 数値定義 | なし（マスタ）。件数は行数。`process_code`は46行で重複なし・空なし。**`process_name`は46行中45種類で、同じ名前の工程がある**（「レーザ1」が`0801`と`801`の2つ。`801`は削除予定でBOSS確認済み。時期は未定。AIの説明文には、工程の特定にはコードを使う、とだけ書き、重複の注意は書かない） |
| 公開フィールド（9列） | `id`、`process_code`、`process_name`、`line_id`、`management_unit`、`operating_rate`、`equipment_count`、`two_person_only`、`is_active` |
| 非公開フィールド | `is_outsource`（BOSS判断 2026-10-10。ほとんどが0のため公開しない）、`created_at`、`updated_at`（BOSS判断が未決定のため、非公開として扱う） |
| 個人情報 | なし（個人名・連絡先・認証情報の列を含まない）。列名は、社内AIの列名検査（`SENSITIVE_IDENTIFIER`）に当たらない（実装時に再確認） |
| 検証方法 | ①ビューの行数＝`m_process`の行数（46）②`process_code`の一意性③`is_active`の件数（有効45・無効1）④`pm_ai_reader`でビューが読め、非公開の3列が読めない⑤定義者が`pm_ai_view_owner@localhost`⑥全行×9列が列型の検査（`_cell`）を通る |

### 13.1 列型の対応（`m_process`のSHOW COLUMNSからの導出。ビュー作成後に再確認する）

| 列 | MySQL型 | `ANALYSIS_COLUMN_TYPES` |
|---|---|---|
| `id`、`line_id` | bigint | `BIGINT` |
| `process_code`、`process_name`、`management_unit` | varchar | `VARCHAR` |
| `two_person_only`、`is_active` | tinyint(1) | `BIGINT`（0/1） |
| `equipment_count` | int unsigned | `BIGINT` |
| `operating_rate` | decimal(5,2) | `DECIMAL(18,2)` |

### 13.2 列の意味（仕様書で確認できた範囲。推測は書かない）

| 列 | 仕様書にある意味 | 出典 |
|---|---|---|
| `process_code` | `G`と`PURCHASE`は、実際の工程ではなく、BOM・ルーティングを作るときに、外作（`G`）・購買（`PURCHASE`）を示すための工程（BOSS指示 2026-10-10）。仕様書にも、`G`は外作工程、`PURCHASE`は購入品の工程とある | BOSS指示、仕入れ検収仕様書.md:168、在庫計算仕様書.md:708 |
| `is_outsource`（非公開） | 真なら外作工程として扱う（`process_code='G'`と同じ扱い）。ほとんどが0で、BOSS判断により公開しない | 仕入れ検収仕様書.md:168、購買需要計算仕様書.md:119 |
| `management_unit` | `DAY`=日単位管理（マクロ計画）、`MINUTE`=分単位管理（ミクロ実行）。DBは`MINUTE`が44工程、`DAY`が2工程（うち1つは購買） | モデル定義（`models.py`の選択肢） |
| `equipment_count` | 設備台数。工程負荷は「工程負荷時間÷設備台数」で按分する | 生産計画仕様書.md:739 |
| `line_id` | 工程の所属ライン（工程から見て親にあたるライン）。`m_line.id`と結べる | BOSS指示 2026-10-10 |
| `operating_rate`、`two_person_only` | 項目名のみ（稼働率(%)、2人1設備専用）。業務上の定義の文章は見つからない | 確認明細 §2 |

### 13.3 あわせて変更するもの（案）
1. マイグレーション `0035`：`CREATE OR REPLACE VIEW v_ai_process AS SELECT <9列> FROM m_process`（標準SQLのみ）。ロールバックは`DROP VIEW IF EXISTS v_ai_process`。
2. `migrate`の直後に、`pm_ai_view_owner`へ`m_process`の9列の列単位`SELECT`を付与し（現在、`m_process`への列権限はない）、定義者を`pm_ai_view_owner@localhost`へ付け替える（§4.1の9番。開発DBはBOSSの指示で私が実行、本番は手順SQLをBOSSが実行）。
3. `ANALYSIS_VIEWS`（`date_field=None`・`quantity_field=None`、説明は13.2の範囲）、`ANALYSIS_COLUMN_TYPES`（13.1。ビュー作成後に`SHOW COLUMNS`と照合）、`BASE_SQL_SCHEMA`・`TABLE_NOTES`、仕様書（基盤仕様書・規約辞書・本計画書）を更新する。
4. `SCREEN_SQL_TABLES`と`TERM_COLUMNS`は変更しない。

### 13.4 BOSSに決めてほしいこと
- **既存の`m_process`（元テーブル）の許可との関係**：現在、生産・品質・購買・マスタ画面のチャットSQLは、元テーブル`m_process`を直接参照できる（`sql_queries.py`の`BASE_SQL_SCHEMA`と`SCREEN_SQL_TABLES`）。ビューができた後、元テーブルの許可をビューへ置き換えるかは、既存の動作の変更になる。今回は置き換えず、ビューの追加だけにする案でよいか（置き換えは、全マスタビューが揃ってから、別に判断する）。
- 公開列の9列でよいか（BOSS判断の転記。`is_outsource`は、BOSS指示で非公開に変更）。

## 14. v_ai_process 実装（2026-10-10。BOSS承認済み: §13の公開9列、元テーブルの許可は置き換えずビューの追加のみ。実装済み・evaluator未検証）

**実装内容**
- `pm_backend/apps/ai/migrations/0035_ai_process_view.py` 新規。`CREATE OR REPLACE VIEW v_ai_process`（9列・別名なし・WHEREなし・結合なし・標準SQLのみ）、ロールバックは`DROP VIEW IF EXISTS v_ai_process`。依存は`ai 0034`と`masters 0084`（`two_person_only`の追加。他の8列はそれ以前）。`makemigrations --dry-run`は「No changes detected」。
- `sql_queries.py`：`BASE_SQL_SCHEMA`に`v_ai_process`（9列）、`TABLE_NOTES`に説明を追加（`ai_home`は自動で対象）。既存の`m_process`エントリと`SCREEN_SQL_TABLES`は変更していない。
- `analysis_data_service.py`：`ANALYSIS_VIEWS`に`v_ai_process`（label=工程マスタ、`date_field=None`、`quantity_field=None`、説明は§13.2の範囲のみ）。
- `analysis_execution_service.py`：`ANALYSIS_COLUMN_TYPES`に9列（§13.1）。
- 仕様書：`AI分析基盤仕様書.md`（公開ビュー一覧・型の対応）、`AI運用規約・AI用DB辞書.md`（§6.5-5を追加。既存の「品番・顧客コード・納入先コードの表記」は§6.5-6へ番号を繰り下げ）。

**検証結果**（開発。読み取りのみ・テスト用DBなし）
- 新規`ai.test_analysis_process_view` 9件を含め、`ai.test_analysis_process_view`・`product_view`・`dateless_view`・`execution`・`planning`・`column_guide`・`codegen`・`jobs`・`multi_period`・`period_warning`・`worker_version`の1コマンド実行で254件OK（再検証の時点では、別セッションが追加した試験を含めて265件OK。skipped=4は既存の実launcher用等）。フロント`pm-ui/scripts/test-analysis-*.mjs` 7本OK（codegen 68・consult 23・error-banner 6・execution 35・external-confirmation 4・status-monitor 13・templates 53、fail 0）。
- 開発DBの実データ（`pm_ai_reader`接続、`SELECT <9列> FROM m_process`）：46行・有効45・`process_code`の重複なし。全46行×9列が`_cell`を通る（エラー0件）。`m_process`のSHOW COLUMNS（bigint・varchar・tinyint(1)・int unsigned・decimal(5,2)）は§13.1の対応と一致。

**未完了**
- 実装時点は、開発DBにビュー`v_ai_process`が未作成だった。**その後、開発DBで実施済み**（BOSS承認 2026-10-10）：`migrate ai 0035`でビュー作成、`pm_ai_view_owner`へ`m_process`の9列の列権限を付与、定義者を`pm_ai_view_owner@localhost`へ付け替え（§4.1の9番）。確認結果：`SHOW COLUMNS FROM v_ai_process`は9列で、型は`ANALYSIS_COLUMN_TYPES`の対応（bigint・varchar・decimal(5,2)・int unsigned・tinyint(1)）と一致。`pm_ai_reader`の接続で、件数46・有効45・`process_code`の種類46。`is_outsource`・`created_at`・`updated_at`は読めない（列がない）。4つの`v_ai_`ビューの定義者は、すべて`pm_ai_view_owner@localhost`。
- evaluatorによる検証：未実施。実機（AIを使う）の再試験：未実施。テスト用DBを要する`ai.test_analysis_*`：未実行。

**反映状況**：開発DBにビュー作成済み・定義者付け替え済み（2026-10-10）。コミット・本番未反映。本番は、`migrate 0035`のあとに、権限付与と定義者の付け替えをBOSSが実行する（§4.1の9番）。

### 14.1 本番・開発の手順SQL（v_ai_process。実行はBOSS。本番は事前にバックアップ。Codexレビュー指摘への対応。2026-10-10）
```sql
-- 1. 定義者の権限を9列へ広げる（rootなど管理者で）
GRANT SELECT (`id`, `process_code`, `process_name`, `line_id`, `management_unit`, `operating_rate`,
  `equipment_count`, `two_person_only`, `is_active`)
  ON `pm_db`.`m_process` TO 'pm_ai_view_owner'@'localhost';
-- 2. マイグレーション適用後（開発: python manage.py migrate / 本番: docker exec ... migrate）、定義者を付け替える
CREATE OR REPLACE DEFINER = `pm_ai_view_owner`@`localhost` SQL SECURITY DEFINER VIEW `pm_db`.`v_ai_process` AS
  SELECT `id`, `process_code`, `process_name`, `line_id`, `management_unit`, `operating_rate`,
  `equipment_count`, `two_person_only`, `is_active`
  FROM `pm_db`.`m_process`;
-- 3. 読み取りユーザーへビューのSELECTのみ付与（開発のpm_ai_readerはDB全体のSELECTを持つため、実質不要。本番はSHOW GRANTSで確認してから）
GRANT SELECT ON `pm_db`.`v_ai_process` TO 'pm_ai_reader'@'<本番のpm_ai_readerのホスト部。SHOW GRANTS FOR で確認>';
-- 4. 確認
SELECT TABLE_NAME, DEFINER, SECURITY_TYPE FROM information_schema.VIEWS WHERE TABLE_SCHEMA = 'pm_db' AND TABLE_NAME = 'v_ai_process';
SELECT COUNT(*), SUM(is_active), COUNT(DISTINCT process_code) FROM `pm_db`.`v_ai_process`;  -- 開発の期待値: 46, 45, 46
SHOW GRANTS FOR 'pm_ai_view_owner'@'localhost';
```

## 15. ラインマスタのビュー `v_ai_line` の作成前確認（2026-10-10。BOSS承認済み。公開6列。実装は§16）

公開する列は、[AIマスタビュー確認明細](AIマスタビュー確認明細.md) §3 のBOSS判断のとおり。§4.1 の設計原則（1テーブル1ビュー・標準SQL・定義者は `pm_ai_view_owner`・列の説明は仕様書で確認）に従う。

| 確認項目 | 内容 |
|---|---|
| 業務目的 | AIが、ラインをコード・名前・種別・カレンダで、分析・説明できるようにする。実績・計画・工程・BOMなどのビューのライン（`line_id`）から、ラインの名前や種別を引く |
| 元テーブル | `m_line` の1つだけ。結合なし（行数57） |
| 対象行 | 全行（絞り込みなし）。有効56・無効1。購買ライン（`PURCHASE`）を含む。無効のラインは`is_active`で、AIが絞る |
| 数値定義 | なし（マスタ）。件数は行数。`line_code`は57行で重複なし・空なし。`line_name`も57行で重複なし |
| 公開フィールド（6列） | `id`、`line_code`、`line_name`、`calendar_id`、`line_type`、`is_active` |
| 非公開フィールド | `lead_time_days`（BOSS判断 2026-10-10。現在は使っていないため）、`use_direct_process`（同。現在は実質使っていないため）、`created_at`、`updated_at`（BOSS判断が未決定のため、非公開として扱う） |
| 個人情報 | なし。ただし、購買ラインの`line_name`は**仕入先の会社名**（例: エトー株式会社）で、`line_code`は仕入先コード。AIは、仕入先名を、コードの置き換えなしで読める（仕入先名は会社名で個人情報ではない。外部AIへ送る目的文の置換は従来どおり） |
| 検証方法 | ①ビューの行数＝`m_line`の行数（57）②`line_code`の一意性③`is_active`の件数（有効56・無効1）④`pm_ai_reader`でビューが読め、非公開の4列が読めない⑤定義者が`pm_ai_view_owner@localhost`⑥全行×6列が列型の検査（`_cell`）を通る |

### 15.1 実データ（開発DB）
- ライン種別（`line_type`）：`PROD`（社内ライン）26（有効26）、`PURCHASE`（購買ライン）29（有効29）、`OUTSOURCE`（外作）1（有効0）、`OTHER`1（有効1）。
- `calendar_id`が空のラインが38。`lead_time_days`は空なし（0〜2）。`use_direct_process`が真のラインは1（板金スポットライン）。
- `line_code`は、先頭がゼロのものが27（購買ラインの仕入先コード。例 `000044`）、英字で始まるものが30。**文字列のまま扱う。**

### 15.2 列型の対応（`m_line`のSHOW COLUMNSからの導出。ビュー作成後に再確認する）
| 列 | MySQL型 | `ANALYSIS_COLUMN_TYPES` |
|---|---|---|
| `id`、`calendar_id` | bigint | `BIGINT` |
| `line_code`、`line_name`、`line_type` | varchar | `VARCHAR` |
| `is_active` | tinyint(1) | `BIGINT`（0/1） |

### 15.3 列の意味（仕様書で確認できた範囲。推測は書かない）
| 列 | 仕様書にある意味 | 出典 |
|---|---|---|
| `line_type` | 値は `PROD`・`PURCHASE`・`OUTSOURCE`・`OTHER`。意味は、§15.5のBOSSの説明のとおり（`PROD`は社内ライン、`PURCHASE`は外作先・購入先の購買ライン、`OUTSOURCE`は外作ライン（使っていない・削除予定）、`OTHER`はクボタ納期調整） | BOSS説明、ER_diagram_v3.md:23、単独計画仕様書.md:24、仕入れ検収仕様書.md:76、仕入れ先カレンダ仕様書.md:18 |
| `line_code` | 購買ラインでは仕入先コード | 仕入れ先カレンダ仕様書.md:18、仕入れ検収仕様書.md:76 |
| `calendar_id` | ラインの勤務カレンダ（購買ラインでは、仕入先のカレンダの割当先）。`m_calendar_day`の`calendar_id`と結べる | モデルの項目名、仕入れ先カレンダ仕様書.md:28 |
| `is_active` | 有効（1）／無効（0）。**ER図は「購買ラインは意図的に0」と書くが、開発DBでは購買ライン29がすべて1。仕様書と実データが食い違う（下記）** | ER_diagram_v3.md:9-11、DB実データ |
| `lead_time_days`、`use_direct_process`（非公開） | 項目名のみ（リードタイム(日)、工程直接展開）。BOSS判断で非公開にした。意味と使われ方は§15.5 | 確認明細 §3 |

### 15.4 BOSSに決めてほしいこと
- ~~公開列の8列でよいか~~ → **決定済み（2026-10-10）**：6列（`lead_time_days`・`use_direct_process`は、BOSS判断で非公開）。
- ~~`is_active`の説明~~ → **決定済み（承認）**：ER図は購買ラインを「意図的に`is_active=0`」とするが、開発DBでは購買ライン29がすべて有効（1）。AIの説明文には、「`is_active`は有効(1)・無効(0)」とだけ書き、購買ラインの扱いは書かない案でよいか。
- ~~元テーブル`m_line`の許可~~ → **決定済み（承認）**：置き換えず、ビューの追加だけにする（工程のときと同じ）。
- ~~`lead_time_days`・`use_direct_process`の意味~~ → **決定済み**：BOSSの説明とコード調査を§15.5に記録。2列とも非公開。

### 15.5 列の意味の追記（BOSS説明・コード調査。2026-10-10）
| 列 | 意味 | 出典 |
|---|---|---|
| `line_type` | **BOSSの説明（2026-10-10）**：`PROD`=社内ライン（社内だけに絞るときに使う）。`PURCHASE`=仕入先の購買ライン（外作先・購入先のライン。社内ライン以外のライン。コード=仕入先コード、名前=仕入先の会社名）。`OUTSOURCE`=外作ライン（ID14 `GAISAKU`。**現在は使っていない。削除予定**）。`OTHER`=クボタ納期調整（ID103 `KBT_DUE_ADJ`。意味の文章は未確認）。コードの調査：`OUTSOURCE`は、購買ラインの品を外作ライン・外作工程へ切り替える／戻す管理コマンドがあり、受注展開・バックログ・生産実績の整合チェックで`PROD`と並んで対象 | BOSS説明、`convert_purchase_to_gaisaku.py`・`revert_gaisaku_line_to_supplier.py`、生産実績整合チェック仕様書.md:18 |
| `lead_time_days` | リードタイム(日)。**最初は使ったが、後では使わなくなった（BOSS）**。主なリードタイムはルーティング工程側。コードには、工程側が空のときの代替などの参照が残る（`lead_time_utils.py`、`bom_service.py:87-92`、`inventory_calculator.py:404`）。値は、0日が50ライン、1日が6、2日が1 | BOSS説明、コード調査 |
| `use_direct_process` | 自動計画の展開で、ルーティングを使わず、指定の工程に直接書き込む（スポット系ライン向け）。BOMの員数の掛け算も行わない。真なのは、ID10「板金スポットライン」の1つだけ。**BOSSは、板金スポットラインのExcel導入（計画入力画面のスポット→Excel→forup取込）に使う、と推測。コード調査では、Excel取込の処理に、このフラグの参照は見つからなかった（参照は、自動計画の生成コマンドだけ）** | モデルの説明文、`generate_production_plan.py:435`、`auto_plan_expansion.py:28` |

**BOSS判断（2026-10-10。判断画面で変更）**：`lead_time_days`（現在使っていない）と`use_direct_process`（自動計画の展開用。板金スポットラインの自動計画は無効で、実質使っていない）は、**非公開**にした。公開は6列。`use_direct_process`の使用箇所は、リポジトリ全体の検索で、自動計画の生成コマンド（`generate_production_plan.py:435`）の1か所だけ。板金スポットラインの自動計画の設定（ID10）は無効で、最後の実行は2026-03-01。

### 15.6 BOSS指摘への調査結果（2026-10-10。ライン編集画面）
- **`line_type='PURCHASE'`**：仕入先の購買ライン。外作先と購入先を絞るときに使う（BOSS）。開発DBでは、購買ライン29の`line_code`が、すべて仕入先コードと一致し、仕入先29（`purchase`＝購入先17、`outsource`＝外作先9、`both`＝両方3）と同数。
- **所属グループ**：`m_line`に列はない。別テーブル `accounts_unit_line_mapping`（`unit_id`＝グループ、`line_id`、`sort_order`、`is_default`、作成・更新日時）に持つ。グループは`accounts_department`の`level='unit'`の行（フロア・タンク・第一工場・第二工場・板金・調達・出荷の6つ）。28行、21ライン。**36ラインは、グループ未割当**。割当があるのは、すべて`PROD`のライン。→ 1テーブル1ビューの原則に従い、**別のビュー（案：`v_ai_unit_line`）にする**。
- **このラインを使用する工程**：画面は、ルーティングではなく**工程マスタの`line_id`**から集計している（`LineMaster.vue:210`）。`v_ai_process`の`line_id`で、AIも同じ関係を引ける。工程を持つラインは27。ルーティング工程が使うラインは53（別のビュー）。

## 16. v_ai_line 実装（2026-10-10。BOSS承認済み: §15の公開6列、元テーブルの許可は置き換えずビューの追加のみ。実装済み・evaluator未検証）

**実装内容**
- `pm_backend/apps/ai/migrations/0036_ai_line_view.py` 新規。`CREATE OR REPLACE VIEW v_ai_line`（6列・別名なし・WHEREなし・結合なし・標準SQLのみ）、ロールバックは`DROP VIEW IF EXISTS v_ai_line`。依存は`ai 0035`と`masters 0023`（`line_type`の追加。`calendar_id`は0015、他の4列は0001）。`makemigrations --dry-run`は「No changes detected」。
- `sql_queries.py`：`BASE_SQL_SCHEMA`に`v_ai_line`（6列）、`TABLE_NOTES`に説明を追加（`ai_home`などは自動で対象）。既存の`m_line`エントリと`SCREEN_SQL_TABLES`は変更していない。
- `analysis_data_service.py`：`ANALYSIS_VIEWS`に`v_ai_line`（label=ラインマスタ、`date_field=None`、`quantity_field=None`、説明は§15.3・§15.5の範囲のみ。`lead_time_days`・`use_direct_process`・`created_at`・`updated_at`と、購買ラインの`is_active`の扱いは書かない）。
- `analysis_execution_service.py`：`ANALYSIS_COLUMN_TYPES`に6列（§15.2）。
- 試験：`apps/ai/test_analysis_line_view.py` 新規。既存の`test_analysis_column_guide.py`の1検査を更新（下記）。
- 仕様書：`AI分析基盤仕様書.md`（公開ビュー一覧・型の対応）、`AI運用規約・AI用DB辞書.md`（§6.5-6を追加。既存の「品番・顧客コード・納入先コードの表記」は§6.5-7へ繰り下げ。他の文書・コードに§6.5-6への参照はなかった）。

**既存試験の更新（承認範囲の反映。検査は弱めていない）**
- `test_analysis_column_guide.py` の `test_no_real_data_note_and_no_unconfirmed_meaning`：全ビューの説明に「クボタ」が入らないことの検査が、`line_type`の値の名称「OTHER=クボタ納期調整」（BOSS承認）で失敗したため、この語句だけを除いた文字列で「クボタ」の不在を検査するように変更。これ以外の「クボタ」は従来どおり不可。

**検証結果**（開発。読み取りのみ・テスト用DBなし）
- 新規`ai.test_analysis_line_view` 9件を含め、`ai.test_analysis_line_view`・`process_view`・`product_view`・`dateless_view`・`execution`・`planning`・`column_guide`・`codegen`・`jobs`・`multi_period`・`period_warning`・`worker_version`の1コマンド実行で263件OK（skipped=4）。フロント`pm-ui/scripts/test-analysis-*.mjs` 7本OK（codegen 68・consult 23・error-banner 6・execution 35・external-confirmation 4・status-monitor 13・templates 53、fail 0）。
- 開発DBの実データ（`AI_DB_ALIAS`接続、`SELECT <6列> FROM m_line`）：57行・有効56・`line_code`の重複なし・`calendar_id`が空38。全57行×6列が`_cell`を通る（エラー0件）。`m_line`のSHOW COLUMNS（bigint・varchar(20/50/20)・tinyint(1)）は§15.2の対応と一致。

**未完了**
- 実装時点は、開発DBにビュー`v_ai_line`が未作成だった。**その後、開発DBで実施済み**（BOSS承認 2026-10-10）：`migrate ai 0036`でビュー作成、`pm_ai_view_owner`へ`m_line`の6列の列権限を付与、定義者を`pm_ai_view_owner@localhost`へ付け替え（§4.1の9番）。確認結果：`SHOW COLUMNS FROM v_ai_line`は6列で、型は`ANALYSIS_COLUMN_TYPES`の対応（bigint・varchar・tinyint(1)）と一致。`pm_ai_reader`の接続で、件数57・有効56・`line_code`の種類57。`lead_time_days`・`use_direct_process`・`created_at`・`updated_at`は読めない（列がない）。全57行×6列が列型の検査を通る（エラー0）。5つの`v_ai_`ビューの定義者は、すべて`pm_ai_view_owner@localhost`。
- evaluatorによる検証：未実施。実機（AIを使う）の再試験：未実施。テスト用DBを要する`ai.test_analysis_*`：未実行。

**反映状況**：開発DBにビュー作成済み・定義者付け替え済み（2026-10-10）。本番未反映。本番は、`migrate 0036`のあとに、権限付与と定義者の付け替えをBOSSが実行する（§4.1の9番）。

### 16.1 本番・開発の手順SQL（v_ai_line。実行はBOSS。本番は事前にバックアップ。Codexレビュー指摘への対応。2026-10-10）
```sql
-- 1. 定義者の権限を6列へ広げる（rootなど管理者で）
GRANT SELECT (`id`, `line_code`, `line_name`, `calendar_id`, `line_type`, `is_active`)
  ON `pm_db`.`m_line` TO 'pm_ai_view_owner'@'localhost';
-- 2. マイグレーション適用後、定義者を付け替える
CREATE OR REPLACE DEFINER = `pm_ai_view_owner`@`localhost` SQL SECURITY DEFINER VIEW `pm_db`.`v_ai_line` AS
  SELECT `id`, `line_code`, `line_name`, `calendar_id`, `line_type`, `is_active`
  FROM `pm_db`.`m_line`;
-- 3. 読み取りユーザーへビューのSELECTのみ付与（開発のpm_ai_readerはDB全体のSELECTを持つため、実質不要。本番はSHOW GRANTSで確認してから）
GRANT SELECT ON `pm_db`.`v_ai_line` TO 'pm_ai_reader'@'<本番のpm_ai_readerのホスト部。SHOW GRANTS FOR で確認>';
-- 4. 確認
SELECT TABLE_NAME, DEFINER, SECURITY_TYPE FROM information_schema.VIEWS WHERE TABLE_SCHEMA = 'pm_db' AND TABLE_NAME = 'v_ai_line';
SELECT COUNT(*), SUM(is_active), COUNT(DISTINCT line_code) FROM `pm_db`.`v_ai_line`;  -- 開発の期待値: 57, 56, 57
SHOW GRANTS FOR 'pm_ai_view_owner'@'localhost';
```

## 17. 仕入先マスタのビュー `v_ai_supplier` の作成前確認（2026-10-10。BOSS承認済み。実装は§19。§8を置き換える）

公開する列は、[AIマスタビュー確認明細](AIマスタビュー確認明細.md) §4 のBOSS判断のとおり。§4.1 の設計原則（1テーブル1ビュー・標準SQL・定義者は `pm_ai_view_owner`・列の説明は仕様書で確認）に従う。§8（2026-10-08）の草案は、「入荷ビューに仕入先の列を足さず、AIにビュー同士を結合させる」という方針で書かれており、今回の原則（結合は、マスタの属性を付けるときだけ可。実績同士は不可）と矛盾しない範囲で引き継ぐ。

| 確認項目 | 内容 |
|---|---|
| 業務目的 | AIが、仕入先をコード・名前・区分・カレンダで、分析・説明できるようにする。入荷実績ビュー（`v_ai_purchase_receipt`）の`supplier_id`から、仕入先のコード・名前を引く（仕入先ごとの入荷の集計の表示に、内部のIDを出さない） |
| 元テーブル | `m_supplier` の1つだけ。結合なし（行数29） |
| 対象行 | 全行（絞り込みなし）。`is_active`の列はない |
| 数値定義 | なし（マスタ）。件数は行数。`supplier_code`は29行で重複なし。`supplier_name`も29種類 |
| 公開フィールド（5列） | `id`、`supplier_code`、`supplier_name`、`supplier_type`、`calendar_id` |
| 非公開フィールド | `contact_person`（担当者名）、`phone_number`（電話番号）、`order_email`（送信メールアドレス）。個人名・連絡先のため |
| 個人情報 | 仕入先名は会社名（個人名ではない）。個人名・電話・メールの3列は、ビューに含めない。外部AIへ送る目的文の、名称→コード置換は、従来どおり（運用規約 §4.1-3） |
| 検証方法 | ①ビューの行数＝`m_supplier`の行数（29）②`supplier_code`の一意性③区分の件数（購入17・外作9・両方3）④`pm_ai_reader`でビューが読め、非公開の3列が読めない⑤定義者が`pm_ai_view_owner@localhost`⑥全行×5列が列型の検査（`_cell`）を通る⑦入荷実績ビューの仕入先別の集計（9月: 仕入先16=20,259・仕入先8=11,270。§8の記録）を、コード・名前つきで照合 |

### 17.1 実データ（開発DB）
- 29行。区分は、購入（`purchase`）17、外作（`outsource`）9、両方（`both`）3。
- `calendar_id`が空の仕入先が28（仕入先専用カレンダがあるのは1つ）。
- `supplier_code`は、先頭がゼロのものが27、英字で始まるものが2（例 `G00001`）。最大6桁。**文字列のまま扱う。**
- 購買ライン（`line_type='PURCHASE'`）29の`line_code`が、すべて仕入先コードと一致する（ラインビュー §15.6）。

### 17.2 列型の対応（`m_supplier`のSHOW COLUMNSからの導出。ビュー作成後に再確認する）
| 列 | MySQL型 | `ANALYSIS_COLUMN_TYPES` |
|---|---|---|
| `id`、`calendar_id` | bigint | `BIGINT` |
| `supplier_code`、`supplier_name`、`supplier_type` | varchar | `VARCHAR` |

### 17.3 列の意味（仕様書で確認できた範囲。推測は書かない）
| 列 | 意味 | 出典 |
|---|---|---|
| `supplier_type` | 値は `purchase`=購入、`outsource`=外作、`both`=両方。購入先・外作先を分けるときに使う（購買ラインの種別と同じ、BOSS説明） | モデルの選択肢（`models.py`）、BOSS説明（ライン§15.5） |
| `supplier_code` | 仕入先コード。購買ラインの`line_code`と同じ。先頭ゼロを含む文字列 | 仕入れ先カレンダ仕様書.md:18、仕入れ検収仕様書.md:76 |
| `supplier_name` | 仕入先名（会社名） | 項目名 |
| `calendar_id` | 仕入先専用カレンダー（稼働カレンダの`calendar_id`と結べる。空の仕入先が多い） | モデルの項目名、自動発注提案仕様書.md:39、AIマスタビュー確認明細.md（BOSS判断） |

### 17.4 あわせて変更するもの（実施内容は§19）
1. マイグレーション `0038`：`CREATE OR REPLACE VIEW v_ai_supplier AS SELECT <5列> FROM m_supplier`（標準SQLのみ）。ロールバックは`DROP VIEW IF EXISTS v_ai_supplier`。
2. `migrate`の直後に、`pm_ai_view_owner`へ`m_supplier`の5列の列単位`SELECT`を付与し（現在、`m_supplier`への列権限はない）、定義者を`pm_ai_view_owner@localhost`へ付け替える（§4.1の9番）。
3. `ANALYSIS_VIEWS`・`ANALYSIS_COLUMN_TYPES`・`BASE_SQL_SCHEMA`・`TABLE_NOTES`・仕様書を更新する。`v_ai_purchase_receipt`の列は変えない（既存ビューの定義を変えると、保存済みテンプレートが再利用できなくなる）。
4. `SCREEN_SQL_TABLES`・`TERM_COLUMNS`・AIへの指示文は変更しない。元テーブル`m_supplier`の許可（購買画面）は、置き換えず、ビューの追加だけにする。

### 17.5 BOSSに決めてほしいこと
- ~~公開列の5列でよいか~~ → **決定済み（承認 2026-10-10）**：5列（BOSS判断の転記どおり）。
- ~~元テーブル`m_supplier`の許可~~ → **決定済み（承認）**：置き換えず、ビューの追加だけにする。
- ~~§8の古い草案を、この§17に置き換えてよいか~~ → **決定済み（承認）**：§17に置き換える。

### 17.6 仕入先とラインの関係（BOSS指摘への調査。2026-10-10。開発DB・読み取りのみ）
- **仕入先と購買ラインは、1対1。つなぐ列は、ラインの`line_code`と仕入先の`supplier_code`（文字列の一致）。** 外部キー（ID）では結ばれていない。購買ライン（`line_type='PURCHASE'`）29と、仕入先29が、すべて、コードで一致する（仕入れ先カレンダ仕様書.md:18、仕入れ検収仕様書.md:76）。
- **LineBacklog（`line_backlog`）**：`line_id`は`m_line`のID。仕入先の列はない。購買ラインの行は148,445行（28ライン）で、すべて、`line_code`が仕入先コードと一致する。社内ライン（`PROD`）は350,870行（25ライン）。→ 仕入先を知るには、`line_id`→ラインの`line_code`→仕入先の`supplier_code`。
- **工程実績（`t_process_realtime_record`）**：`line_id`の**列はない**。仕入実績（`record_type='PURCHASE'`）は、`event_data`（JSON）の中に`line_id`と`supplier_id`を持つ。2,872行すべてが`supplier_id`を持ち、2,831行が`line_id`を持つ。この2,831行は、`line_id`が購買ラインで、そのラインの`line_code`が、`supplier_id`の仕入先コードと一致する（2,831行すべて）。`line_id`を持たない41行は、工程コードが`PURCHASE`（購入）の行。工程コードが`G`（外作）の行は、2,831行。→ 入荷実績ビュー（`v_ai_purchase_receipt`）は、`supplier_id`と`line_id`の両方を、列として持つ。
- **工程マスタの`line_id`**：`G`・`PURCHASE`の工程は、ラインを持たない（`m_process.line_id`は空）。仕入先の区別は、工程ではなく、ラインで行う（仕入実績record_type分離仕様書.md:25）。
- **ルーティング工程**：ラインの種別は、社内4,707、購買2,970、外作1。`supplier_id`を持つのは534行。
- **AIへの説明**：`v_ai_line`と`v_ai_supplier`の説明に、「購買ラインの`line_code`＝仕入先の`supplier_code`（同じ文字列で結べる。先頭ゼロを含む）」を書く。

## 18. 日付なしビューの指示文の見直し（2026-10-10。BOSS承認済み。Codex第2回レビュー指摘1への対応。実装済み・evaluator未検証）

**背景**：日付なしビュー（`v_ai_product`・`v_ai_process`・`v_ai_line`）に対し、AIが`created_at BETWEEN {{period_from}} AND {{period_to}}`のような日付の絞り込みを付けても、生成物の検査では拒否できない。BOSS判断：日付なしビューの日付の列で絞る分析は正しい分析であり、検査は追加しない。代わりに指示文を、日付の列で絞る分析を禁止しない形に直し、「必ず`parameters_unused`で拒否される」という説明を訂正する。

**実装内容**
- `pm_backend/apps/ai/services/analysis_codegen_service.py`：`DATELESS_VIEW_RULE`のみ書き換え（`SYSTEM_PROMPT`本体は変更なし。日付ありだけのsystemは変更前と同一）。
  - 変更前：「日付の列を持たない承認ビュー(datasetsのdescriptionに「期間では絞らず全行が対象」とあるビュー)は、期間で絞らず全行を使う(そのビューに期間の条件や日付の条件を付けない)。期間の変数 period_from・period_to は、日付のあるビューの条件にだけ使う。」
  - 変更後：「日付の列を持たない承認ビュー(datasetsのdescriptionに「期間では絞らず全行が対象」とあるビュー)は、システムの期間では絞られず、全行が取り込まれる。分析の中で、目的に応じて、そのビューの日付の列(descriptionに列があるもの)で絞るのは構わない。システムの期間の変数 period_from・period_to は、日付のあるビューの期間条件に使う。目的が日付での絞り込みを求めていない場合は、日付の条件を付けない。」
- 検査（`validate_generated`・`_apply_parameters`）、`analysis_guard_runtime.py`、既存ビューの登録は変更なし。上限値・フォールバックの新設なし。
- 仕様書：`AI分析基盤仕様書.md`（§4.7-8の指示文の記録、日付なしビューの日付の列での絞り込みを追記）、`Codexレビュー依頼_AI用ビュー.md`（指摘1の対応欄と確認項目7を更新）。

**検証結果**（DBを作らない試験のみ）：`ai.test_analysis_*`の12モジュールを1コマンドで263件OK（skipped=4。その後、品番の30列化と別セッションの追加を含めて265件OK）。`pm-ui/scripts/test-analysis-*.mjs` 7本 fail 0。既存の試験の更新は不要（`test_analysis_product_view.py`は定数参照で比較しており、日付あり単独のsystemがSYSTEM_PROMPTと一致する検査もそのまま合格）。

**未完了**：evaluatorによる検証、実機のAI再試験（日付なしビューの日付の列で絞る目的・絞らない目的の両方）。

**反映状況**：コード変更のみ。コミット・本番未反映。

## 19. v_ai_supplier 実装（2026-10-10。BOSS承認済み: §17の公開5列、元テーブルの許可は置き換えずビューの追加のみ。実装済み・evaluator未検証）

**実装内容**
- `pm_backend/apps/ai/migrations/0038_ai_supplier_view.py` 新規。`CREATE OR REPLACE VIEW v_ai_supplier`（5列・別名なし・WHEREなし・結合なし・標準SQLのみ）、ロールバックは`DROP VIEW IF EXISTS v_ai_supplier`。依存は`ai 0037`と`masters 0059`（`supplier_type`の追加。`calendar_id`は0032、他の3列は0001）。`makemigrations --dry-run`は「No changes detected」。
- `sql_queries.py`：`BASE_SQL_SCHEMA`に`v_ai_supplier`（5列）、`TABLE_NOTES`に説明を追加。既存の`m_supplier`エントリと`SCREEN_SQL_TABLES`は変更していない。
- `analysis_data_service.py`：`ANALYSIS_VIEWS`に`v_ai_supplier`（label=仕入先マスタ、`date_field=None`、`quantity_field=None`、説明は§17.3の範囲のみ。`contact_person`・`phone_number`・`order_email`は書かない）。
- `analysis_execution_service.py`：`ANALYSIS_COLUMN_TYPES`に5列（§17.2）。
- 試験：`apps/ai/test_analysis_supplier_view.py` 新規（10件）。既存の試験の更新は不要（既存ビューの出力は変わらず、既存の固定ハッシュはすべて同じ値のまま合格）。
- 仕様書：`AI分析基盤仕様書.md`（公開ビュー一覧・型の対応）、`AI運用規約・AI用DB辞書.md`（§6.5-7を追加。既存の「品番・顧客コード・納入先コードの表記」は§6.5-8へ繰り下げ。他の文書・コードに§6.5-7・§6.5-8への参照はなかった）。
- 既存ビュー5つ（出荷・入荷・品番・工程・ライン）の定義（説明・列）のJSONのSHA-256（新規試験の固定値）：`aaed5cd71d844171d20fc26e92ab5a257bec3b4929b7c54e88781206a4abe454`。v_ai_supplier の追加前後で同一（追加は、既存エントリを変えない追記のみ）。既存4ビューの値は`12dd1770…`、既存3ビューの値は`4d111066…`で、既存の試験の固定値と一致した。

**検証結果**（開発。読み取りのみ・テスト用DBなし）
- 新規`ai.test_analysis_supplier_view` 10件を含め、`ai.test_analysis_supplier_view`・`line_view`・`process_view`・`product_view`・`dateless_view`・`execution`・`planning`・`column_guide`・`codegen`・`jobs`・`multi_period`・`period_warning`・`worker_version`の1コマンド実行で275件OK（skipped=4）。フロント`pm-ui/scripts/test-analysis-*.mjs` 7本OK（codegen 68・consult 23・error-banner 6・execution 35・external-confirmation 4・status-monitor 13・templates 53、fail 0）。
- 開発DBの実データ（`AI_DB_ALIAS`接続、`SELECT <5列> FROM m_supplier`）：29行・`supplier_code`の重複なし（29種類）・区分は購入17・外作9・両方3・`calendar_id`が空28。全29行×5列が`_cell`を通る（エラー0件）。`m_supplier`のSHOW COLUMNS（bigint・varchar(20/100/20)・bigint）は§17.2の対応と一致。入荷実績ビューの`supplier_id`は2,872行すべて値があり、`m_supplier.id`に存在しない行は0件。

**未完了**
- 実装時点は、開発DBにビュー`v_ai_supplier`が未作成だった。**その後、開発DBで実施済み**（BOSS承認 2026-10-10）：`migrate ai 0038`（21:06に適用済み。実行者は記録上不明）、`setup_ai_views --apply`（定義者を`pm_ai_view_owner@localhost`へ付け替え、`m_supplier`の5列の列権限を付与。コマンドの最初の実機実行）。確認結果：`SHOW COLUMNS FROM v_ai_supplier`は5列で、型は`ANALYSIS_COLUMN_TYPES`の対応（bigint・varchar）と一致。`pm_ai_reader`の接続で、29件・コード29種類・区分は購入17・外作9・両方3。`contact_person`・`phone_number`・`order_email`は読めない（列がない）。全29行×5列が列型の検査を通る（エラー0）。入荷ビューの仕入先IDで、仕入先ビューにない行は0件。購買ライン29が、仕入先コードですべて結合できる。6つの`v_ai_`ビューの定義者は、すべて`pm_ai_view_owner@localhost`。`setup_ai_views --check`は要対応0件。
- evaluatorによる検証：未実施。実機（AIを使う）の再試験：未実施。テスト用DBを要する`ai.test_analysis_*`：未実行。

**反映状況**：開発DBにビュー作成済み・定義者付け替え済み（2026-10-10）。本番未反映。本番は、`migrate 0038`のあとに、`setup_ai_views --apply`（管理者で実行）で、権限付与と定義者の付け替えをBOSSが実行する（§20）。

### 19.1 本番・開発の手順SQL（v_ai_supplier。実行はBOSS。本番は事前にバックアップ）
```sql
-- 1. 定義者の権限を5列へ広げる（rootなど管理者で。現在、m_supplierへの列権限はない。担当者名・電話番号・メールアドレスの列は付与しない）
GRANT SELECT (`id`, `supplier_code`, `supplier_name`, `supplier_type`, `calendar_id`)
  ON `pm_db`.`m_supplier` TO 'pm_ai_view_owner'@'localhost';
-- 2. マイグレーション適用後（migrate ai 0038）、定義者を付け替える
CREATE OR REPLACE DEFINER = `pm_ai_view_owner`@`localhost` SQL SECURITY DEFINER VIEW `pm_db`.`v_ai_supplier` AS
  SELECT `id`, `supplier_code`, `supplier_name`, `supplier_type`, `calendar_id`
  FROM `pm_db`.`m_supplier`;
-- 3. 読み取りユーザーへビューのSELECTのみ付与（開発のpm_ai_readerはDB全体のSELECTを持つため、実質不要。本番はSHOW GRANTSで確認してから）
GRANT SELECT ON `pm_db`.`v_ai_supplier` TO 'pm_ai_reader'@'<本番のpm_ai_readerのホスト部。SHOW GRANTS FOR で確認>';
-- 4. 確認
SELECT TABLE_NAME, DEFINER, SECURITY_TYPE FROM information_schema.VIEWS WHERE TABLE_SCHEMA = 'pm_db' AND TABLE_NAME = 'v_ai_supplier';
SELECT COUNT(*), COUNT(DISTINCT supplier_code), SUM(supplier_type='purchase'), SUM(supplier_type='outsource'), SUM(supplier_type='both') FROM `pm_db`.`v_ai_supplier`;  -- 開発の期待値: 29, 29, 17, 9, 3
SHOW COLUMNS FROM `pm_db`.`v_ai_supplier`;  -- 5列（bigint・varchar・varchar・varchar・bigint）
SHOW GRANTS FOR 'pm_ai_view_owner'@'localhost';
```

## 20. 管理コマンド setup_ai_views（2026-10-10。BOSS承認: 案B。実装済み・evaluator未検証）

**目的**：§4.1の9番の手順（列権限の付与・定義者の付け替え）を、管理者が `migrate` の後に1回実行する管理コマンドにまとめる。MySQL固有の処理はこのコマンドに閉じ込める（マイグレーションは標準SQLのまま）。

**実装内容**（`pm_backend/apps/ai/management/commands/setup_ai_views.py`）
- 対象：定数 `SIMPLE_MASTER_VIEWS`（`v_ai_product`→`m_product`、`v_ai_process`→`m_process`、`v_ai_line`→`m_line`、`v_ai_supplier`→`m_supplier`）。列は `BASE_SQL_SCHEMA[ビュー名]`（列の単一の情報源）。新しい単純なマスタビューは、この定数に1行足す。
- `v_ai_shipment`・`v_ai_purchase_receipt` は再作成しない（定義はマイグレーション0012〜0014）。`--check` で定義者を表示するだけ。
- 1ビューごとに ①`GRANT SELECT (列) ON 元テーブル TO owner`（足りない列だけ）②`CREATE OR REPLACE DEFINER = owner SQL SECURITY DEFINER VIEW`（定義者・SECURITY_TYPE・列が期待と違うときだけ）。全ビューの後に ③owner の元テーブル列権限のうち、同じ元テーブルを使う全ビューの公開列の和集合（`OTHER_VIEW_COLUMNS`：`m_product` の `id`・`product_code`・`product_name` ＝ v_ai_shipment 用、を含む）にない列を `REVOKE`。現在の権限は `information_schema.COLUMN_PRIVILEGES` から読み、差分だけを実行（冪等）。
- MySQL以外では「何もしない」と表示して終了（エラーにしない）。識別子はバッククォートで囲み、バッククォートを含む名前は拒否。ユーザー名・ホスト名は `re.fullmatch(r'[A-Za-z0-9_.%-]+')` で検査（末尾の改行も拒否）。
- 権限不足などで失敗したときは、失敗したSQLと実行済みのSQLを表示し、「管理者（rootなど）で実行する」ことを示して非0で終了。
- ビューの作り直し（CREATE）は、定義者・SECURITY_TYPE・列順のどれかが期待と違うときだけ実行する。**ビュー本体（WHERE・別名・列式・元テーブル）の違いは検出しない**（現在の4ビューは全行・結合なし・別名なしのため、実害は小さい。将来、本文の比較を足す余地がある）。
- `--check` は、owner が元テーブルに**表全体のSELECT**を持つ場合も「要対応」にする（承認内容になかった追加。表示だけで、自動では直さない。列権限がないので REVOKE も出ない）。DB全体（`SCHEMA_PRIVILEGES`）・グローバル（`USER_PRIVILEGES`）の権限は、検出しない設計。
- `--reader-host`：指定したときだけ、`pm_ai_reader` へ各ビューの `GRANT SELECT` を実行する。指定しなければ実行せず、表示だけ（開発のreaderはDB全体のSELECTを持ち、本番のホスト部は未確認のため）。
- ユーザー名・ホスト名は `re.fullmatch` で検査するため、末尾の改行も拒否する。
- 本節が参照する仕入先ビュー（`v_ai_supplier`・§19.1・マイグレーション0038）は、仕入先ビューのコミットと同時に反映する（先にコミットし、そのあとにこのコマンドをコミットする案B。BOSS承認 2026-10-10）。

**使い方**（`pm_backend` で、管理者のDB接続で実行）
```
python manage.py setup_ai_views                 # 既定: 実行予定のSQLを表示するだけ
python manage.py setup_ai_views --apply         # 実行（その後に自動で --check）
python manage.py setup_ai_views --check         # 読み取りのみの確認
```
オプション：`--owner`（既定 `pm_ai_view_owner`）、`--owner-host`（既定 `localhost`）、`--views`（対象を絞る）、`--reader-host`（指定したときだけ `pm_ai_reader` へビューのSELECTを付与。既定では実行しない。本番のホスト部は `SHOW GRANTS` で確認してから指定）。
`--check` は、定義者・SECURITY_TYPE・列（`information_schema.COLUMNS`の順序つき列名。BASE_SQL_SCHEMAと比較）・owner の列権限（公開列の和集合と一致）・`ai_reader` 接続での読み取り（`SELECT 1 FROM ビュー LIMIT 1`）を表示し、期待と違えば「要対応」と表示する。

**検証結果**
- 試験：`ai.test_setup_ai_views`（偽の接続・カーソル。DBを作らない）。生成SQLと BASE_SQL_SCHEMA・各マイグレーションの列の一致、dry-run、`--apply` の順序、不正名の拒否、MySQL以外、冪等、join系ビューの非再作成、実装を壊すと失敗すること（`OTHER_VIEW_COLUMNS` の保護・`fullmatch`・表全体のSELECTの検出・定義者／SECURITY_TYPEの比較。evaluatorが確認）、表全体のSELECTの `--check`、CREATE要否の個別条件、`--views` での絞り込み、GRANT・CREATE・REVOKE の失敗時の表示。
- 開発DB（読み取りのみ）：dry-run と `--check` を実行（2026-10-10）。`--apply` は未実行。`v_ai_supplier` の定義者が `root@localhost` で、`m_supplier` の列権限が未付与のため、dry-run は GRANT と CREATE の2文を表示した。他の3ビューは揃っている。

**未完了**：evaluatorによる検証。開発DBでの `--apply`（BOSS承認のもとで実行）。本番での実行。
**反映状況**：開発DBで、`--apply`を実機で実行済み（2026-10-10。仕入先ビューの定義者・権限を整えた。要対応0件。もう一度実行すると「実行するSQLはありません」で冪等）。本番未反映。
