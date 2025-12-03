# Django + Vue 生産システム設計まとめ

## 1. 全体イメージ（アーキテクチャ）

**バックエンド（Django / Django REST Framework）**
- データ定義・業務ロジック
- REST API 提供
- 生産計画計算・在庫計算・リードタイム計算

**フロントエンド（Vue）**
- 生産計画入力・一覧
- 各工程の進捗画面（ライン別）
- 在庫一覧・外作注文管理・運送計画画面

**DB（ｍｙSQL等）**
- 顧客・製品・工程・ライン  顧客というより取引先：区分は得意先、社内加工、購入先、運送
- 　　　　製品区分：集合　材料　単品　購入品
- 
- 受注／生産計画／実績  受注は一つのテーブル？得意先によってorderフォーマットが違うし　内示と確定がある
- 在庫（計画・実績）  
- サプライヤー・外作注文  
- 運送計画（客先／サプライヤー向け）

---

## 2. 工程系列・ライン構造

製品の工程系列：

```
レーザー切断 → ブレーキ曲げ → プロジェクション溶接 → スポット溶接 → MIG溶接（複数工程）
→ 検査 → 気密検査 → 艤装 → 出荷
```

- 同じ工程名でもライン違いが存在
- 製品ごとに Routing（工程ルート）を持つ

---

## 3. 必要機能

### ● 生産計画
- 受注情報（納期・数量）から工程計画を自動生成
- リードタイムに基づき工程開始／終了日を算出

### ● 運送計画（客先向け）
- 出荷工程の完了予定日 → 配送便へ自動割当

### ● 在庫管理
- 計画在庫：生産計画とリードタイムから計算  
- 実績在庫：入出庫実績から集計

### ● 進度管理
- 計画 vs 実績  
- 遅れ日数・遅れ工程を可視化

### ● 外作注文書作成
- 外作工程に対して PO（PurchaseOrder）を発行

### ● 運送計画（サプライヤー向け）
- 外作工程の持ち込み／引取りスケジュール管理

---

## 4. Django モデル設計（抜粋）これからコードは書かないで

### ● マスタ
```python
class Customer(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)

class Supplier(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
```

### ● 製品・工程・ライン
```python
class Product(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=200)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)

class Process(models.Model):
    name = models.CharField(max_length=50)

class Line(models.Model):
    name = models.CharField(max_length=50)
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
```

### ● Routing（工程ルート）
```python
class Routing(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE)

class RoutingStep(models.Model):
    routing = models.ForeignKey(Routing, on_delete=models.CASCADE, related_name="steps")
    order = models.PositiveIntegerField()
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    line = models.ForeignKey(Line, on_delete=models.CASCADE, null=True, blank=True)
    lead_time_days = models.DecimalField(max_digits=5, decimal_places=2)
    is_outsourced = models.BooleanField(default=False)
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.SET_NULL)
```

---

## 5. 生産計画・実績

```python
class SalesOrder(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    order_no = models.CharField(max_length=30)
    order_qty = models.IntegerField()
    due_date = models.DateField()
```

```python
class ProductionPlan(models.Model):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE)
    planned_qty = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
```

```python
class ProcessPlan(models.Model):
    production_plan = models.ForeignKey(ProductionPlan, on_delete=models.CASCADE)
    routing_step = models.ForeignKey(RoutingStep, on_delete=models.CASCADE)
    planned_start = models.DateField()
    planned_end = models.DateField()
    planned_qty = models.IntegerField()
```

---

## 6. 在庫管理モデル

```python
class Inventory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    location = models.CharField(max_length=50)
    qty = models.IntegerField()
```

```python
class StockTransaction(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    date = models.DateTimeField()
    qty = models.IntegerField()  # +入庫, -出庫
    reason = models.CharField(max_length=100)
```

---

## 7. 外作・運送計画

### ● 外作注文書
```python
class PurchaseOrder(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    order_no = models.CharField(max_length=30)
    issue_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=20, default="open")
```

### ● 運送計画
```python
class TransportPlan(models.Model):
    direction = models.CharField(max_length=20)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.CASCADE)
    plan_date = models.DateField()
    vehicle = models.CharField(max_length=50, null=True, blank=True)
    remark = models.TextField(blank=True)
```

---

## 8. Vue 側画面構成

### ● メイン機能
- 生産計画作成
- 工程ガントチャート表示
- 進度管理ダッシュボード
- 在庫一覧・推移グラフ
- 外作注文管理
- 運送計画管理（客先／サプライヤー）

※ ガントチャートは Chart.js / ECharts で実装可能

---

## 9. 開発ステップ（推奨）

1. マスタ構築（顧客・製品・工程・ライン・Routing）
2. 受注 → 生産計画（工程計画自動生成）
3. 工程ガントチャート・進度画面
4. 在庫計画（計算ロジック）
5. 外作管理・運送管理を追加

---
