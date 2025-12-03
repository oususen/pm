# 生産管理システム マスタテーブル定義（必須版）

本ドキュメントは、量産・日単位管理・工程統合モデルを前提として\
**最小限でシステムを成立させる必須マスタ** をまとめたものです。

------------------------------------------------------------------------

# 1. 製品マスタ `m_product`

製品（品番）の基本情報。

  カラム名                  型                   説明
  ------------------------- -------------------- ------------------------
  id                        BIGINT PK            内部ID
  product_code              VARCHAR(30) UNIQUE   品番
  product_name              VARCHAR(100)         品名
  区分：　集合　単品　材料　購入品
  親
  unit                      VARCHAR(10)          個、kg など
  daily_target_qty          INT                  標準日産数（量産用）（これを生産能力にして：秒/個）
  standard_lt_days          INT                  標準リードタイム（日）（これは完成品に対して）
  self_lt_days          INT                  標準リードタイム（日）（これは親に対して）
  is_final_product          TINYINT(1)           最終製品フラグ　
  is_active                 TINYINT(1)           有効/無効
  created_at / updated_at   DATETIME             監査用

------------------------------------------------------------------------

# 2. 得意先マスタ `m_customer`

受注先の基本情報。

  カラム名                  型                   説明
  ------------------------- -------------------- --------------
  id                        BIGINT PK            
  customer_code             VARCHAR(20) UNIQUE   得意先コード
  customer_name             VARCHAR(100)         名称
  short_name                VARCHAR(40)          略称
  default_lt_days           INT                  標準LT（日）これは要らないですね
  calendar_id               BIGINT FK            使用カレンダ
  transport_lead_days       INT                  運送日数　　とりあえず要らない
  is_active                 TINYINT(1)           
  created_at / updated_at   DATETIME             

------------------------------------------------------------------------

# 3. 工程マスタ `m_process`

工程（切断/曲げ/溶接等）の定義。

  カラム名                  型                   説明
  ------------------------- -------------------- -----------------------
  id                        BIGINT PK            
  process_code              VARCHAR(20) UNIQUE   工程コード
  process_name              VARCHAR(50)          工程名
  is_outsource              TINYINT(1)           外作工程か
  default_cycle_time_sec    INT                  1個あたり秒（将来用）　多数の加工物あるからこれは要らない
  default_setup_time_min    INT                  段取り時間　　　　　　同上　要らない
  ライン
  is_active                 TINYINT(1)           
  created_at / updated_at   DATETIME             

------------------------------------------------------------------------

# 4. ラインマスタ `m_line`

生産ライン（Aライン、Bライン等）。

  カラム名                    型                   説明
  --------------------------- -------------------- -----------------
  id                          BIGINT PK            
  line_code                   VARCHAR(20) UNIQUE   
  line_name                   VARCHAR(50)          
  standard_capacity_per_day   INT                  1日あたり処理数　いらない
  is_active                   TINYINT(1)           
  created_at / updated_at     DATETIME             

------------------------------------------------------------------------

# 5. ルーティング（工程順序）（これは構成部品表を作成用ですか）

製品に紐づく工程構成。

## 5.1 ルーティングヘッダ `m_routing`

  カラム名                  型            説明
  ------------------------- ------------- ------------
  id                        BIGINT PK     
  product_id                BIGINT FK     対象製品
  routing_code              VARCHAR(30)   識別コード
  description               TEXT          備考
  is_default                TINYINT(1)    標準ルート
  is_active                 TINYINT(1)    
  created_at / updated_at   DATETIME      

## 5.2 ルーティング工程明細 `m_routing_step`

工程順序と日単位LT。

  カラム名                  型             説明
  ------------------------- -------------- ----------------
  id                        BIGINT PK      
  routing_id                BIGINT FK      
  step_no                   INT            工程順序
  process_id                BIGINT FK      工程ID
  line_id                   BIGINT FK      標準ライン
  lead_time_days            INT            日単位の工程LT
  remark                    VARCHAR(200)   
  created_at / updated_at   DATETIME       

------------------------------------------------------------------------

# 6. BOM（構成）

製品の構成部品。

## 6.1 BOMヘッダ `m_bom`

  カラム名                  型            説明
  ------------------------- ------------- --------
  id                        BIGINT PK     
  parent_product_id         BIGINT FK     親品番
  version                   VARCHAR(20)   
  valid_from                DATE          
  valid_to                  DATE NULL     
  is_active                 TINYINT(1)    
  created_at / updated_at   DATETIME      

## 6.2 BOM明細 `m_bom_item`

  カラム名                  型              説明
  ------------------------- --------------- --------
  id                        BIGINT PK       
  bom_id                    BIGINT FK       
  child_product_id          BIGINT FK       子品番
  quantity                  DECIMAL(12,3)   使用量
  loss_rate                 DECIMAL(5,3)    歩留　いる？
  remark                    VARCHAR(200)    
  created_at / updated_at   DATETIME        

------------------------------------------------------------------------

# 7. カレンダ（工場カレンダのみでOK）

## 7.1 カレンダヘッダ `m_calendar`

  カラム名                  型            説明
  ------------------------- ------------- ------
  id                        BIGINT PK     
  calendar_code             VARCHAR(20)   
  calendar_name             VARCHAR(50)   
  description               TEXT          
  created_at / updated_at   DATETIME      

## 7.2 カレンダ日単位 `m_calendar_day`

  カラム名                  型             説明
  ------------------------- -------------- -------------
  id                        BIGINT PK      
  calendar_id               BIGINT FK      
  target_date               DATE           
  is_working_day            TINYINT(1)     稼働日/休日
  note                      VARCHAR(100)   
  created_at / updated_at   DATETIME       

------------------------------------------------------------------------

# 8. ユーザー（最初は Django 標準でOK）

### Django auth_user を利用

独自テーブルは不要（必要になれば m_user を後追加）

------------------------------------------------------------------------

# ✔ まとめ

今回の MD は「最小限のマスタ構成」に絞っているため\
すぐ ER 図 → Django モデルに落とし込めます。
一番ムズイのは構成部品ツリー
------------------------------------------------------------------------

必要であれば、次を続けて作ります：

-   **最小構成の ER 図（テキスト版 / 図版）**\
-   **Django models.py（実際に動くコード）**\
-   **テーブル作成用 SQL（CREATE TABLE）**\
-   **マスタ画面UI（Vue）**

指示ください！
