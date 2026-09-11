# ui技

## 目的
画面の行数を減らし、ラベルと入力欄を1行で見せる。

## 適用方針
- 「ラベル上・入力下」の縦並びは使わない。
- `label` の中に「ラベル文字」と「入力要素」を置き、横並びにする。
- フィルタ行も入力行（例: 新規作成フォーム）と同じ並べ方に統一する。

## 推奨HTML（Vue）
```vue
<div class="prepare-form filter-form">
  <label>
    <span class="field-label">ライン</span>
    <select v-model="selectedLine"></select>
  </label>
  <label>
    <span class="field-label">製品</span>
    <select v-model="selectedProduct"></select>
  </label>
  <label>
    <span class="field-label">ステータス</span>
    <select v-model="batchStatusFilter"></select>
  </label>
</div>
```

## 推奨CSS
```css
.prepare-form {
  display: flex;
  flex-wrap: wrap;
  align-items: end;
  gap: 8px;
}

.prepare-form label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  width: auto;
  flex: 0 0 auto;
}

.field-label {
  white-space: nowrap;
  min-width: 56px;
}

.prepare-form select,
.prepare-form input {
  padding: 5px 7px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
}
```

## 実装ルール
- フィルタ欄は専用の崩れやすいレイアウトを避け、`prepare-form` を再利用する。
- 幅を固定しすぎない（`width: auto` + `flex: 0 0 auto` を基本）。
- 画面幅が狭い場合は `flex-wrap: wrap` で折り返し、重なりを防ぐ。
- ラベル幅は `field-label` の `min-width` で揃える。
- 必須マーク `*` は必ずラベルと同一行に置く（別行に落とさない）。
  - 推奨: `<span class="field-inline-label">項目名 <span class="required-mark">*</span></span>`
  - 禁止: `*` を独立した行・独立した要素として配置すること。

## NG例
- `label` を縦積みにする（`flex-direction: column`）。
- フィルタだけ別実装で右寄せ・縦積みになる指定を入れる。
- `nowrap` と固定幅を多用して重なりを発生させる。

## 参照
- 対象実装: `pm-ui/src/views/quality/IntegratedChecksheetOperation.vue`
