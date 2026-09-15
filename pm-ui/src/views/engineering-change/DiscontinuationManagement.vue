<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">打ち切り管理</h2>
      <button class="btn-primary" type="button" @click="toggleCreateForm" :disabled="!canEdit">
        {{ showCreateForm ? "新規作成を閉じる" : "新規作成" }}
      </button>
    </div>
    <p v-if="!canView" class="helper warning">この画面を閲覧する権限がありません。</p>
    <p v-else-if="!canEdit" class="helper warning">閲覧のみ可能です（編集権限がありません）。</p>

    <!-- 新規作成フォーム -->
    <div class="card form-card" v-if="showCreateForm && canEdit">
      <h3>打ち切り案件 登録</h3>
      <div class="grid top-grid">
        <label>
          案件名
          <input v-model="form.title" type="text" placeholder="例: 7ton系SH 量産終息" />
        </label>
        <label>
          終了時期
          <input v-model="form.endDate" type="date" />
        </label>
        <label>
          備考
          <input v-model="form.note" type="text" placeholder="備考" />
        </label>
      </div>

      <div class="parts-header">
        <h4>完成品（複数登録）</h4>
        <button class="btn-secondary" type="button" @click="addProductRow">完成品行を追加</button>
      </div>

      <div class="parts-table-wrap">
        <table class="table parts-table">
          <thead>
            <tr>
              <th>完成品コード</th>
              <th>完成品名</th>
              <th>打ち切り時期</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in productRows" :key="row.id">
              <td>
                <div class="cell-select">
                  <input v-model="row.filter" type="text" placeholder="品番/品名で絞り込み" />
                  <select v-model="row.productCode" @change="onProductChange(row)">
                    <option value="">選択してください</option>
                    <option
                      v-for="p in getFilteredProducts(row.filter)"
                      :key="`prod-${row.id}-${p.id}`"
                      :value="p.product_code"
                    >
                      {{ p.product_code }} - {{ p.product_name }}
                    </option>
                  </select>
                </div>
              </td>
              <td><input v-model="row.productName" type="text" readonly /></td>
              <td><input v-model="row.endDate" type="date" /></td>
              <td>
                <button class="btn-danger" type="button" @click="removeProductRow(row.id)">削除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="form-actions">
        <button class="btn-primary" type="button" @click="submitCreate" :disabled="submitting">
          {{ submitting ? "登録中..." : "登録" }}
        </button>
      </div>
    </div>

    <!-- 一覧 -->
    <div v-if="canView" class="list-section">
      <p v-if="loading" class="helper">読み込み中...</p>
      <p v-else-if="cases.length === 0" class="helper">打ち切り案件はまだ登録されていません。</p>

      <div v-for="c in cases" :key="c.id" class="card case-card">
        <div class="case-header">
          <div class="case-title">
            <span class="case-code">{{ c.case_code }}</span>
            <span class="case-name">{{ c.title }}</span>
            <span v-if="c.end_date" class="case-end-date">終了: {{ c.end_date }}</span>
          </div>
          <div class="case-actions">
            <button v-if="canEdit" class="btn-secondary btn-sm" @click="startAddProduct(c)">完成品追加</button>
            <button v-if="canEdit" class="btn-danger btn-sm" @click="deleteCase(c)">案件削除</button>
          </div>
        </div>
        <div v-if="c.note" class="case-note">備考: {{ c.note }}</div>

        <!-- 完成品ごとの展開 -->
        <div v-for="dp in c.products" :key="dp.id" class="product-block">
          <div class="product-header">
            <span class="product-code">{{ dp.product_code }}</span>
            <span class="product-name">{{ dp.product_name }}</span>
            <span class="product-end-date">
              打ち切り:
              <input
                v-if="canEdit"
                type="date"
                :value="dp.end_date"
                class="inline-date"
                @change="updateProductEndDate(dp, $event)"
              />
              <span v-else>{{ dp.end_date || '未設定' }}</span>
            </span>
            <button
              v-if="canEdit"
              class="btn-secondary btn-sm"
              @click="recalculateProduct(dp)"
              :disabled="dp._recalculating"
            >
              {{ dp._recalculating ? '計算中...' : '再計算' }}
            </button>
            <button v-if="canEdit" class="btn-danger btn-sm" @click="deleteProduct(dp, c)">削除</button>
          </div>

          <!-- 構成品一覧 -->
          <table v-if="dp.parts.length > 0" class="table parts-list-table">
            <thead>
              <tr>
                <th>構成品コード</th>
                <th>構成品名</th>
                <th>調達</th>
                <th>調達先</th>
                <th>打切日(LT加味)</th>
                <th class="num">現在庫</th>
                <th class="num">現在進度</th>
                <th class="num">現在計進</th>
                <th class="num">計画在庫(打切日)</th>
                <th class="num">進度(打切日)</th>
                <th class="num">計進(打切日)</th>
                <th>計庫判定</th>
                <th>計進判定</th>
                <th>共用先</th>
                <th v-if="canEdit"></th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="part in dp.parts"
                :key="part.id"
                :class="{
                  'excess-row': part.judgment_stock === 'excess' || part.judgment_progress === 'excess',
                  'shared-check-row': !( part.judgment_stock === 'excess' || part.judgment_progress === 'excess') && (part.judgment_stock === 'shared_check' || part.judgment_progress === 'shared_check'),
                }"
              >
                <td>{{ part.part_code }}</td>
                <td>{{ part.part_name }}</td>
                <td>{{ part.sourcing_label || '-' }}</td>
                <td>{{ part.supplier_name || '-' }}</td>
                <td class="date-cell">{{ part.part_end_date || '-' }}</td>
                <td class="num">{{ part.stock_qty ?? '-' }}</td>
                <td class="num" :class="{ 'val-positive': part.progress_qty > 0, 'val-negative': part.progress_qty < 0 }">
                  {{ part.progress_qty ?? '-' }}
                </td>
                <td class="num" :class="{ 'val-positive': part.planned_progress_qty > 0, 'val-negative': part.planned_progress_qty < 0 }">
                  {{ part.planned_progress_qty ?? '-' }}
                </td>
                <td class="num" :class="{ 'val-positive': part.planned_stock_at_end > 0 }">
                  {{ part.planned_stock_at_end ?? '-' }}
                </td>
                <td class="num" :class="{ 'val-positive': part.progress_at_end > 0, 'val-negative': part.progress_at_end < 0 }">
                  {{ part.progress_at_end ?? '-' }}
                </td>
                <td class="num" :class="{ 'val-positive': part.planned_progress_at_end > 0, 'val-negative': part.planned_progress_at_end < 0 }">
                  {{ part.planned_progress_at_end ?? '-' }}
                </td>
                <td>
                  <span v-if="part.judgment_stock === 'excess'" class="badge-excess">過剰</span>
                  <span v-else-if="part.judgment_stock === 'shared_check'" class="badge-shared-check">要確認</span>
                  <span v-else class="badge-ok">-</span>
                </td>
                <td>
                  <span v-if="part.judgment_progress === 'excess'" class="badge-excess">過剰</span>
                  <span v-else-if="part.judgment_progress === 'shared_check'" class="badge-shared-check">要確認</span>
                  <span v-else class="badge-ok">-</span>
                </td>
                <td>
                  <span v-if="part.shared_parents.length === 0" class="no-share">-</span>
                  <span v-else class="shared-badge">
                    <span v-for="(sp, i) in part.shared_parents" :key="sp.product_id">
                      {{ sp.product_code }}{{ i < part.shared_parents.length - 1 ? ', ' : '' }}
                    </span>
                  </span>
                </td>
                <td v-if="canEdit">
                  <button class="btn-danger btn-xs" @click="deletePart(part, dp)">削除</button>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-else class="helper">構成品なし（BOMが未登録の可能性があります）</p>
        </div>
      </div>
    </div>

    <!-- 完成品追加ダイアログ -->
    <div v-if="addProductDialog.show" class="modal-overlay" @click.self="addProductDialog.show = false">
      <div class="modal-card">
        <h3>完成品追加 ({{ addProductDialog.caseName }})</h3>
        <div class="cell-select">
          <input v-model="addProductDialog.filter" type="text" placeholder="品番/品名で絞り込み" />
          <select v-model="addProductDialog.productCode" @change="onAddProductChange">
            <option value="">選択してください</option>
            <option
              v-for="p in getFilteredProducts(addProductDialog.filter)"
              :key="`add-${p.id}`"
              :value="p.product_code"
            >
              {{ p.product_code }} - {{ p.product_name }}
            </option>
          </select>
        </div>
        <label>
          打ち切り時期
          <input v-model="addProductDialog.endDate" type="date" />
        </label>
        <div class="form-actions">
          <button class="btn-primary" @click="submitAddProduct" :disabled="!addProductDialog.productCode">追加</button>
          <button class="btn-secondary" @click="addProductDialog.show = false">キャンセル</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { authState } from "@/auth";
import { hasPermission } from "@/router";
import api from "@/api/client";

const cases = ref([]);
const loading = ref(false);
const submitting = ref(false);
const showCreateForm = ref(false);
const allProducts = ref([]);
const permissionReady = ref(false);

const canAccess = (level = "view") => {
  const user = authState.user;
  if (!user) return false;
  return hasPermission(user, "engineering_change", level);
};
const canView = computed(() => permissionReady.value && canAccess("view"));
const canEdit = computed(() => permissionReady.value && canAccess("edit"));

const form = ref({ title: "", endDate: "", note: "" });
const productRows = ref([]);
let rowIdCounter = 0;

const addProductDialog = ref({
  show: false,
  caseId: null,
  caseName: "",
  filter: "",
  productCode: "",
  productId: null,
  endDate: "",
});

function toggleCreateForm() {
  showCreateForm.value = !showCreateForm.value;
  if (showCreateForm.value && productRows.value.length === 0) {
    addProductRow();
  }
}

function addProductRow() {
  productRows.value.push({
    id: ++rowIdCounter,
    filter: "",
    productCode: "",
    productName: "",
    productId: null,
    endDate: form.value.endDate,
  });
}

function removeProductRow(id) {
  productRows.value = productRows.value.filter((r) => r.id !== id);
}

function onProductChange(row) {
  const found = allProducts.value.find((p) => p.product_code === row.productCode);
  if (found) {
    row.productName = found.product_name;
    row.productId = found.id;
  } else {
    row.productName = "";
    row.productId = null;
  }
}

function getFilteredProducts(filter) {
  if (!filter) return allProducts.value.slice(0, 100);
  const lc = filter.toLowerCase();
  return allProducts.value
    .filter((p) => p.product_code.toLowerCase().includes(lc) || p.product_name.toLowerCase().includes(lc))
    .slice(0, 100);
}

async function submitCreate() {
  if (!form.value.title.trim()) {
    alert("案件名は必須です");
    return;
  }
  const products = productRows.value
    .filter((r) => r.productId)
    .map((r) => ({
      product_id: r.productId,
      end_date: r.endDate || form.value.endDate || null,
    }));
  if (products.length === 0) {
    alert("完成品を1つ以上選択してください");
    return;
  }
  submitting.value = true;
  try {
    await api.discontinuations.create({
      title: form.value.title,
      end_date: form.value.endDate || null,
      note: form.value.note,
      products,
    });
    showCreateForm.value = false;
    form.value = { title: "", endDate: "", note: "" };
    productRows.value = [];
    await loadCases();
  } catch (e) {
    alert("登録に失敗しました: " + (e.response?.data?.detail || e.message));
  } finally {
    submitting.value = false;
  }
}

async function loadCases() {
  loading.value = true;
  try {
    const res = await api.discontinuations.list();
    cases.value = res.data;
  } catch (e) {
    console.error("打ち切り案件取得失敗", e);
  } finally {
    loading.value = false;
  }
}

async function deleteCase(c) {
  if (!confirm(`案件「${c.title}」を削除しますか？`)) return;
  try {
    await api.discontinuations.deleteCase(c.id);
    await loadCases();
  } catch (e) {
    alert("削除に失敗しました");
  }
}

async function updateProductEndDate(dp, event) {
  const newDate = event.target.value || null;
  try {
    await api.discontinuations.updateProduct(dp.id, { end_date: newDate });
    dp.end_date = newDate;
  } catch (e) {
    alert("更新に失敗しました");
  }
}

async function recalculateProduct(dp) {
  dp._recalculating = true;
  try {
    const res = await api.discontinuations.recalculateProduct(dp.id);
    alert(res.data.detail || '再計算完了');
    await loadCases();
  } catch (e) {
    alert("再計算に失敗しました: " + (e.response?.data?.detail || e.message));
  } finally {
    dp._recalculating = false;
  }
}

async function deleteProduct(dp, c) {
  if (!confirm(`完成品「${dp.product_code}」を削除しますか？`)) return;
  try {
    await api.discontinuations.deleteProduct(dp.id);
    await loadCases();
  } catch (e) {
    alert("削除に失敗しました");
  }
}

async function deletePart(part, dp) {
  if (!confirm(`構成品「${part.part_code}」を削除しますか？`)) return;
  try {
    await api.discontinuations.deletePart(part.id);
    await loadCases();
  } catch (e) {
    alert("削除に失敗しました");
  }
}

function startAddProduct(c) {
  addProductDialog.value = {
    show: true,
    caseId: c.id,
    caseName: c.title,
    filter: "",
    productCode: "",
    productId: null,
    endDate: c.end_date || "",
  };
}

function onAddProductChange() {
  const found = allProducts.value.find((p) => p.product_code === addProductDialog.value.productCode);
  addProductDialog.value.productId = found ? found.id : null;
}

async function submitAddProduct() {
  const d = addProductDialog.value;
  if (!d.productId) return;
  try {
    await api.discontinuations.addProduct(d.caseId, {
      product_id: d.productId,
      end_date: d.endDate || null,
    });
    d.show = false;
    await loadCases();
  } catch (e) {
    alert("追加に失敗しました");
  }
}

onMounted(async () => {
  try {
    const res = await api.auth.me();
    authState.user = res.data?.authenticated ? res.data?.user || null : null;
  } catch (_) {
    authState.user = null;
  }
  permissionReady.value = true;

  const products = await api.products.getAllProducts();
  allProducts.value = Array.isArray(products) ? products : products?.results || [];
  await loadCases();
});
</script>

<style scoped>
.page { padding: 16px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.page-title { margin: 0; font-size: 18px; }

.card { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 12px; }
.form-card h3 { margin: 0 0 10px; font-size: 15px; }
.form-card h4 { margin: 0; font-size: 14px; }

.grid { display: grid; gap: 8px; }
.top-grid { grid-template-columns: 1fr 200px 1fr; }
.top-grid label { display: flex; flex-direction: column; gap: 2px; font-size: 13px; font-weight: 600; }
.top-grid input { padding: 4px 6px; font-size: 13px; border: 1px solid #cbd5e1; border-radius: 4px; }

.parts-header { display: flex; justify-content: space-between; align-items: center; margin: 10px 0 6px; }
.parts-table-wrap { overflow-x: auto; }

.table { width: 100%; border-collapse: collapse; font-size: 13px; }
.table th, .table td { border: 1px solid #e2e8f0; padding: 4px 6px; text-align: left; }
.table th { background: #f8fafc; font-weight: 600; white-space: nowrap; }
.table td input, .table td select { width: 100%; padding: 2px 4px; font-size: 13px; border: 1px solid #cbd5e1; border-radius: 3px; box-sizing: border-box; }

.cell-select { display: flex; flex-direction: column; gap: 2px; }
.cell-select input, .cell-select select { width: 100%; font-size: 13px; }

.form-actions { margin-top: 10px; display: flex; gap: 8px; }

.btn-primary { background: #2563eb; color: #fff; border: none; padding: 6px 14px; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-primary:hover { background: #1d4ed8; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-danger { background: #ef4444; color: #fff; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-sm { padding: 3px 8px; font-size: 12px; }
.btn-xs { padding: 2px 6px; font-size: 11px; }

.helper { color: #64748b; font-size: 13px; }
.helper.warning { color: #dc2626; }

.list-section { margin-top: 8px; }

.case-card { margin-bottom: 14px; }
.case-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.case-title { display: flex; align-items: center; gap: 10px; font-size: 14px; }
.case-code { font-weight: 700; color: #2563eb; }
.case-name { font-weight: 600; }
.case-end-date { color: #dc2626; font-size: 13px; font-weight: 600; }
.case-actions { display: flex; gap: 6px; }
.case-note { font-size: 12px; color: #64748b; margin-bottom: 8px; }

.product-block { border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px; margin-bottom: 8px; background: #fafbfc; }
.product-header { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; font-size: 13px; flex-wrap: wrap; }
.product-code { font-weight: 700; }
.product-name { color: #334155; }
.product-end-date { color: #b45309; font-weight: 600; display: flex; align-items: center; gap: 4px; }
.inline-date { padding: 2px 4px; font-size: 12px; border: 1px solid #cbd5e1; border-radius: 3px; }

.parts-list-table { margin-top: 4px; }
.num { text-align: right; white-space: nowrap; }
.date-cell { white-space: nowrap; font-size: 12px; }
.val-positive { color: #dc2626; font-weight: 700; }
.val-negative { color: #2563eb; font-weight: 700; }

.excess-row { background: #fee2e2; }
.shared-check-row { background: #fef3c7; }

.badge-excess { background: #dc2626; color: #fff; padding: 1px 6px; border-radius: 3px; font-size: 11px; font-weight: 700; }
.badge-shared-check { background: #f59e0b; color: #fff; padding: 1px 6px; border-radius: 3px; font-size: 11px; font-weight: 700; }
.badge-ok { color: #94a3b8; }

.shared-badge { color: #b45309; font-weight: 600; font-size: 12px; }
.no-share { color: #94a3b8; }

.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-card { background: #fff; border-radius: 8px; padding: 20px; min-width: 400px; max-width: 500px; }
.modal-card h3 { margin: 0 0 12px; font-size: 15px; }
.modal-card label { display: flex; flex-direction: column; gap: 2px; font-size: 13px; font-weight: 600; margin-top: 8px; }
.modal-card input { padding: 4px 6px; font-size: 13px; border: 1px solid #cbd5e1; border-radius: 4px; }
</style>
