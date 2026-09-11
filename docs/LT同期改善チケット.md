# LT同期改善チケット（remark維持・FK優先化）

## 背景

- 現行のBOM↔Routing同期は `RoutingStep.remark`（親品番文字列）への依存が強く、表記ゆれ・手修正・空値で同期先を誤るリスクがある。
- `BOMItem` と `RoutingStep` の二重管理を継続する場合でも、同期解決は参照整合性を持つFKを優先すべき。

## 方針

- 一次情報は `BOMItem`。
- `RoutingStep` は生成物として、元BOM明細を指す `source_bom_item_id` を保持する。
- 同期・再生成の紐付けは `source_bom_item_id` を最優先とし、`remark` は維持する。

## 実装タスク

1. モデル変更
- `m_routing_step.source_bom_item_id`（nullable FK -> `m_bom_item.id`）を追加する。

2. 生成処理変更
- BOMからRouting自動生成時に、生成した各 `RoutingStep` へ `source_bom_item_id` を設定する。

3. 同期処理変更
- `BOMItemViewSet.perform_update` の同期先解決を FK優先へ変更する。
- `RoutingStepViewSet.perform_create/perform_update` のBOM側同期を FK優先へ変更する。

4. 既存データ移行
- 既存 `RoutingStep` に対して、`output_product_id + process_id + line_id + 親BOM` で候補を推定し `source_bom_item_id` を埋める。
- 推定不能レコードは未設定で残し、差分一覧を出力する。

5. 段階移行
- 互換期間中は `source_bom_item_id` 不在時のみ `remark` フォールバックを許容する。
- 移行完了後も `remark` は保持し、同期解決での優先順位を「FK優先・remark補助」とする。

## 受け入れ条件

- `remark` を変更しても同期先が変化しない（`source_bom_item_id` 設定済み行）。
- 同期対象解決に `source_bom_item_id` が使われる。
- 既存データ移行後、`source_bom_item_id` 未設定件数が可視化される。

## 作成日 2026-04-13
