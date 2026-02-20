<template>
  <div class="page">
    <h2 class="page-title">設変タイル</h2>

    <div class="card form-card">
      <h3>設変対象 登録</h3>
      <div class="grid top-grid">
        <div class="final-product-field">
          <div class="field-label">親製品 <span class="required">*</span></div>
          <input
            v-model="form.finalProductFilter"
            type="text"
            placeholder="品番/品名で絞り込み"
          />
          <select v-model="form.finalProductCode" @change="onFinalProductChange">
            <option value="">選択してください</option>
            <option
              v-for="product in filteredFinalProducts"
              :key="product.id"
              :value="product.product_code"
            >
              {{ product.product_code }} - {{ product.product_name }}
            </option>
          </select>
        </div>
        <label>
          切替予定日
          <input v-model="form.switchDate" type="date" />
        </label>
      </div>

      <div class="parts-header">
        <h4>構成部品（複数登録）</h4>
        <button class="btn-secondary" type="button" @click="addPartRow">部品行を追加</button>
      </div>

      <div class="parts-table-wrap">
        <table class="table parts-table">
          <thead>
            <tr>
              <th>旧部品コード</th>
              <th>旧部品名</th>
              <th>新部品コード</th>
              <th>打ち切り後必要量</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in partRows" :key="row.id">
              <td>
                <div class="cell-select">
                  <input v-model="row.oldPartFilter" type="text" placeholder="品番/品名で絞り込み" />
                  <select v-model="row.oldPartCode" @change="onOldPartChange(row)">
                    <option value="">選択してください</option>
                    <option
                      v-for="product in getFilteredProducts(row.oldPartFilter)"
                      :key="`old-${row.id}-${product.id}`"
                      :value="product.product_code"
                    >
                      {{ product.product_code }} - {{ product.product_name }}
                    </option>
                  </select>
                </div>
              </td>
              <td><input v-model="row.oldPartName" type="text" readonly /></td>
              <td>
                <div class="cell-select">
                  <input v-model="row.newPartFilter" type="text" placeholder="品番/品名で絞り込み" />
                  <select v-model="row.newPartCode">
                    <option value="">選択してください</option>
                    <option
                      v-for="product in getFilteredProducts(row.newPartFilter)"
                      :key="`new-${row.id}-${product.id}`"
                      :value="product.product_code"
                    >
                      {{ product.product_code }} - {{ product.product_name }}
                    </option>
                  </select>
                </div>
              </td>
              <td><input v-model.number="row.requiredQtyAfterEol" type="number" min="0" step="1" /></td>
              <td>
                <button class="btn-danger" type="button" @click="removePartRow(row.id)">削除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="actions">
        <button class="btn-primary" type="button" @click="addRecords">一括追加</button>
        <button class="btn-secondary" type="button" @click="resetForm">クリア</button>
        <button class="btn-secondary" type="button" @click="downloadCsv" :disabled="records.length === 0">CSV出力</button>
      </div>
    </div>

    <div class="card">
      <h3>設変過剰管理一覧</h3>
      <div class="summary">
        <span>件数: {{ records.length }}</span>
        <span>発注過剰合計: {{ totalExcessPurchaseQty }}</span>
        <span>生産過剰合計: {{ totalExcessProductionQty }}</span>
      </div>

      <table class="table" v-if="records.length">
        <thead>
          <tr>
            <th>最終品</th>
            <th>旧部品</th>
            <th>共用親製品</th>
            <th>新部品</th>
            <th>切替日</th>
            <th>切替日まで必要量</th>
            <th>切替日の生産計画在庫</th>
            <th>切替日の進度</th>
            <th>切替日の計進</th>
            <th>在庫</th>
            <th>進度</th>
            <th>発注過剰</th>
            <th>生産過剰</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in records" :key="item.id">
            <td v-if="editingId !== item.id">{{ item.final_product_code }} {{ item.final_product_name }}</td>
            <td v-else>
              <select v-model="editForm.final_product_code">
                <option
                  v-for="product in filteredFinalProducts"
                  :key="`edit-final-${item.id}-${product.id}`"
                  :value="product.product_code"
                >
                  {{ product.product_code }} - {{ product.product_name }}
                </option>
              </select>
            </td>
            <td v-if="editingId !== item.id">{{ item.old_part_code }} {{ item.old_part_name }}</td>
            <td v-else>
              <select v-model="editForm.old_part_code">
                <option
                  v-for="product in products"
                  :key="`edit-old-${item.id}-${product.id}`"
                  :value="product.product_code"
                >
                  {{ product.product_code }} - {{ product.product_name }}
                </option>
              </select>
            </td>
            <td>{{ item.parent_products_text || '-' }}</td>
            <td v-if="editingId !== item.id">{{ item.new_part_code || '-' }}</td>
            <td v-else>
              <select v-model="editForm.new_part_code">
                <option value="">選択なし</option>
                <option
                  v-for="product in products"
                  :key="`edit-new-${item.id}-${product.id}`"
                  :value="product.product_code"
                >
                  {{ product.product_code }} - {{ product.product_name }}
                </option>
              </select>
            </td>
            <td v-if="editingId !== item.id">{{ item.switch_date || '-' }}</td>
            <td v-else><input v-model="editForm.switch_date" type="date" /></td>
            <td>{{ item.required_until_switch_qty }}</td>
            <td>{{ item.switch_prod_planned_stock_qty }}</td>
            <td>{{ item.switch_prod_progress_qty }}</td>
            <td>{{ item.switch_prod_planned_progress_qty }}</td>
            <td>{{ item.stock_qty }}</td>
            <td>{{ item.progress_qty }}</td>
            <td :class="{ over: item.excess_purchase_qty > 0 }">{{ item.excess_purchase_qty }}</td>
            <td :class="{ over: item.excess_production_qty > 0 }">{{ item.excess_production_qty }}</td>
            <td v-if="editingId !== item.id">
              <button class="btn-secondary" type="button" @click="startEdit(item)">編集</button>
              <button class="btn-danger" type="button" @click="removeRecord(item.id)">削除</button>
            </td>
            <td v-else>
              <button class="btn-primary" type="button" @click="saveEdit(item.id)">保存</button>
              <button class="btn-secondary" type="button" @click="cancelEdit">取消</button>
              <button class="btn-danger" type="button" @click="removeRecord(item.id)">削除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else>データがありません。</p>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import api from "@/api/client";

const defaultForm = () => ({
  finalProductFilter: "",
  finalProductCode: "",
  finalProductName: "",
  switchDate: "",
});

const createPartRow = () => ({
  id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  oldPartFilter: "",
  oldPartCode: "",
  oldPartName: "",
  newPartFilter: "",
  newPartCode: "",
  requiredQtyAfterEol: 0,
});

const form = reactive(defaultForm());
const partRows = ref([createPartRow()]);
const records = ref([]);
const finalProducts = ref([]);
const products = ref([]);
const processing = ref(false);
const editingId = ref(null);
const editForm = reactive({
  final_product_code: "",
  old_part_code: "",
  new_part_code: "",
  switch_date: "",
  required_qty_after_eol: 0,
});

const filteredFinalProducts = computed(() => {
  const keyword = form.finalProductFilter.trim().toLowerCase();
  if (!keyword) return finalProducts.value;
  return finalProducts.value.filter((product) => {
    const code = String(product.product_code || "").toLowerCase();
    const name = String(product.product_name || "").toLowerCase();
    return code.includes(keyword) || name.includes(keyword);
  });
});

const loadRecords = async () => {
  try {
    const res = await api.engineeringChanges.list();
    records.value = Array.isArray(res.data) ? res.data : [];
  } catch (error) {
    console.error("設変データ取得失敗:", error);
    records.value = [];
  }
};

const loadFinalProducts = async () => {
  try {
    const finalList = await api.products.getAllProducts({ is_final_product: true });
    finalProducts.value = Array.isArray(finalList) ? finalList : [];
  } catch (error) {
    console.error("最終品一覧の取得に失敗:", error);
    finalProducts.value = [];
  }
};

const loadProducts = async () => {
  try {
    const all = await api.products.getAllProducts();
    products.value = Array.isArray(all) ? all : [];
  } catch (error) {
    console.error("部品候補の取得に失敗:", error);
    products.value = [];
  }
};

const getFilteredProducts = (keyword) => {
  const normalized = String(keyword || "").trim().toLowerCase();
  if (!normalized) return products.value;
  return products.value.filter((product) => {
    const code = String(product.product_code || "").toLowerCase();
    const name = String(product.product_name || "").toLowerCase();
    return code.includes(normalized) || name.includes(normalized);
  });
};

const onFinalProductChange = () => {
  const selected = finalProducts.value.find((item) => item.product_code === form.finalProductCode);
  form.finalProductName = selected?.product_name || "";
};

const onOldPartChange = (row) => {
  const selected = products.value.find((item) => item.product_code === row.oldPartCode);
  row.oldPartName = selected?.product_name || "";
};

const addPartRow = () => {
  partRows.value.push(createPartRow());
};

const removePartRow = (id) => {
  if (partRows.value.length === 1) {
    partRows.value = [createPartRow()];
    return;
  }
  partRows.value = partRows.value.filter((row) => row.id !== id);
};

const resetForm = () => {
  Object.assign(form, defaultForm());
  partRows.value = [createPartRow()];
};

const addRecords = () => {
  if (processing.value) return;
  if (!form.finalProductCode.trim()) {
    alert("最終品コードは必須です。");
    return;
  }

  const targets = partRows.value.filter((row) => row.oldPartCode.trim());
  if (targets.length === 0) {
    alert("旧部品コードを1件以上入力してください。");
    return;
  }

  const parts = targets.map((row) => {
    return {
      old_part_code: row.oldPartCode.trim(),
      new_part_code: row.newPartCode.trim(),
      required_qty_after_eol: Number(row.requiredQtyAfterEol || 0),
    };
  });
  processing.value = true;
  api.engineeringChanges.create({
    final_product_code: form.finalProductCode.trim(),
    switch_date: form.switchDate || null,
    parts,
  }).then(async () => {
    resetForm();
    await loadRecords();
  }).catch((e) => {
    console.error("設変登録失敗", e);
    alert("登録に失敗しました。");
  }).finally(() => {
    processing.value = false;
  });
};

const removeRecord = async (id) => {
  try {
    await api.engineeringChanges.deletePart(id);
    await loadRecords();
  } catch (e) {
    console.error("設変削除失敗", e);
    alert("削除に失敗しました。");
  }
};

const startEdit = (item) => {
  editingId.value = item.id;
  editForm.final_product_code = item.final_product_code || "";
  editForm.old_part_code = item.old_part_code || "";
  editForm.new_part_code = item.new_part_code || "";
  editForm.switch_date = item.switch_date || "";
  editForm.required_qty_after_eol = Number(item.required_qty_after_eol || 0);
};

const cancelEdit = () => {
  editingId.value = null;
};

const saveEdit = async (id) => {
  try {
    await api.engineeringChanges.updatePart(id, {
      final_product_code: editForm.final_product_code,
      old_part_code: editForm.old_part_code,
      new_part_code: editForm.new_part_code,
      switch_date: editForm.switch_date || null,
      required_qty_after_eol: Number(editForm.required_qty_after_eol || 0),
    });
    editingId.value = null;
    await loadRecords();
  } catch (e) {
    console.error("設変更新失敗", e);
    alert("更新に失敗しました。");
  }
};

const totalExcessPurchaseQty = computed(() => {
  return records.value.reduce((sum, item) => sum + Number(item.excess_purchase_qty || 0), 0);
});

const totalExcessProductionQty = computed(() => {
  return records.value.reduce((sum, item) => sum + Number(item.excess_production_qty || 0), 0);
});

const downloadCsv = () => {
  const header = [
    "最終品コード",
    "最終品名",
    "旧部品コード",
    "旧部品名",
    "共用親製品",
    "新部品コード",
    "切替予定日",
    "切替日まで必要量",
    "切替日の生産計画在庫",
    "切替日の進度",
    "切替日の計進",
    "在庫",
    "進度",
    "発注過剰",
    "生産過剰",
  ];

  const rows = records.value.map((item) => [
    item.final_product_code,
    item.final_product_name,
    item.old_part_code,
    item.old_part_name,
    item.parent_products_text,
    item.new_part_code,
    item.switch_date,
    item.required_until_switch_qty,
    item.switch_prod_planned_stock_qty,
    item.switch_prod_progress_qty,
    item.switch_prod_planned_progress_qty,
    item.stock_qty,
    item.progress_qty,
    item.excess_purchase_qty,
    item.excess_production_qty,
  ]);

  const esc = (v) => `"${String(v ?? "").replaceAll("\"", "\"\"")}"`;
  const content = [header, ...rows].map((line) => line.map(esc).join(",")).join("\n");
  const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `設変過剰管理_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

onMounted(async () => {
  await Promise.all([loadFinalProducts(), loadProducts(), loadRecords()]);
});
</script>

<style scoped>
.page {
  padding: 16px;
  display: grid;
  gap: 16px;
}
.card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}
.top-grid {
  grid-template-columns: minmax(320px, 1fr) 220px;
  align-items: end;
}
.final-product-field {
  display: grid;
  gap: 6px;
}
.field-label {
  font-size: 13px;
  color: #334155;
}
.required {
  color: #dc2626;
  font-weight: 700;
}
label {
  display: grid;
  gap: 4px;
  font-size: 13px;
  color: #334155;
}
input {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 7px 8px;
}
select {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 7px 8px;
  background: #fff;
}
@media (max-width: 780px) {
  .top-grid {
    grid-template-columns: 1fr;
  }
}
.parts-header {
  margin-top: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.parts-table-wrap {
  margin-top: 8px;
  overflow-x: auto;
}
.parts-table input {
  min-width: 110px;
}
.cell-select {
  display: grid;
  gap: 4px;
  min-width: 180px;
}
.cell-select input,
.cell-select select {
  min-width: 160px;
}
.parts-table td:nth-child(4) input {
  width: 55px;
  min-width: 55px;
}
.actions {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.btn-primary,
.btn-secondary,
.btn-danger {
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 7px 10px;
  cursor: pointer;
  white-space: nowrap;
}
.btn-primary {
  background: #2563eb;
  color: #fff;
}
.btn-secondary {
  background: #e2e8f0;
  color: #0f172a;
}
.btn-danger {
  background: #fee2e2;
  color: #991b1b;
}
.summary {
  display: flex;
  gap: 16px;
  margin-bottom: 10px;
  font-weight: 600;
}
.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.table th,
.table td {
  border: 1px solid #e2e8f0;
  padding: 6px;
  text-align: left;
}
.badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
}
.badge.over {
  background: #fee2e2;
  color: #991b1b;
}
.badge.ok {
  background: #dcfce7;
  color: #166534;
}
.over {
  color: #b91c1c;
  font-weight: 700;
}
</style>
