# BOMとルーティング

## 概要
BOMからルーティングを自動生成する際のルールをまとめる。
対象はBOMツリー（BOM TREE）とルーティング工程（m_routing_step）。

## 用語
- BOM階層: BOMツリー上の深さ。ドット区切りの数で表現する。
- hierarchy_path: BOMツリーでの通しパス。例: `1.1.1.4`
- hierarchy_depth: 階層の深さ。例: `1.1.1.4` -> 4
- step_no: 工程順を表す番号。昇順で前工程 -> 後工程。
- parallel_group: 同一step_no内の順序グループ。

## BOM -> ルーティング自動生成
### 1) 階層パスの付け方
- BOMを深さ優先で辿り、兄弟の順序(idx)を積み上げて `hierarchy_path` を作る。
- 例: 1番目の子 -> `1`、その子の1番目の子 -> `1.1`、以後同様。
- `hierarchy_depth` はドット区切りの数。
  - `1.1.1.4` -> 4
  - `18.1` -> 2

### 2) 工程番号(step_no)と並列グループ(parallel_group)
受注展開(ORDERDEMAND)で工程順として使用できるよう、以下の採番ルールを適用する。

- **step_no**: 階層を反転して付与する。
  - `step_no = (max_depth - 階層数 + 1) * 1000`
  - 最終工程(階層1)が最大step_noになる。
- **parallel_group**: `hierarchy_path` の数字を連結して整数化。
  - `1.1.1.4` -> `1114`
  - `1.1.4.1` -> `1141`
  - `1.1.18.1` -> `11181`

### 3) 最終工程
- 最終工程(完成品)は `hierarchy_path = final`、`hierarchy_depth = 0`。
- `step_no` は自動生成工程の **最大step_no + 1** に設定する。
  - 最終工程が常に最後(最大)になることを保証する。

## ORDERDEMAND展開での利用
- 受注展開は `step_no` 昇順 -> `parallel_group` 昇順で処理される。
- 上記ルールにより、BOM階層の順序が工程順として利用可能になる。
- 注意: BOMの並び順が工程順と一致していることが前提。

## 注意事項
- step_noは `(routing_id, step_no, parallel_group)` で一意。
- `time_unit='DAY'` の場合は `lead_time_days > 0` を必須。
- リードタイムの遡りは稼働日(カレンダ)を考慮して算出する。
