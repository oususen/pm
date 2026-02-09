<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">進度のみ</h2>
        <p class="subtitle">内示・確定と工程の計画/実績から、計画進度と進度だけを確認します。</p>
      </div>
      <div class="page-actions">
        <input
          type="text"
          v-model="lineFilter"
          placeholder="ラインコード/名称で絞り込み"
          @keyup.enter="handleEnter"
          @dblclick="openCodeLookup"
        />
        <input
          type="text"
          v-model="processFilter"
          placeholder="工程コード/名称で絞り込み"
          @keyup.enter="handleEnter"
          @dblclick="openCodeLookup"
        />
        <input
          type="text"
          v-model="productFilter"
          placeholder="品番/品名で絞り込み"
          @keyup.enter="handleEnter"
        />
        <input
          type="date"
          v-model="startDate"
          @change="onStartChange"
          @keyup.enter="handleEnter"
        />
        <select v-model.number="horizon" @keyup.enter="handleEnter">
          <option :value="30">30日</option>
          <option :value="60">60日</option>
          <option :value="90">90日</option>
          <option :value="120">120日</option>
        </select>
        <button @click="load" :disabled="loading">更新</button>
        <button @click="recalculate" :disabled="loading || recalculating || !hasFilter">再計算</button>
      </div>
    </div>

    <div v-if="loading" class="status">読込中...</div>
    <div v-else-if="recalculating" class="status">再計算中...</div>
    <div v-else-if="error" class="status error">エラー: {{ error }}</div>
    <div v-else-if="!hasFilter" class="status">ライン、工程、または品番を入力してください</div>
    <div v-else>
      <div v-if="groups.length" class="group-list">
        <div v-for="g in groups" :key="g.key" class="group-card">
          <div class="info-block">
            <div class="info-row">
              <span class="info-label">ライン</span>
              <span class="info-value">{{ formatLine(g) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">工程</span>
              <span class="info-value">{{ g.process_code || "-" }} / {{ g.process_name || "-" }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">品番</span>
              <span class="info-value">{{ g.product_code || "-" }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">品名</span>
              <span class="info-value">{{ g.product_name || "-" }}</span>
            </div>
          </div>

          <div class="matrix-block">
            <table class="matrix-table">
              <thead>
                <tr>
                  <th class="label-col">項目</th>
                  <th v-for="d in columns" :key="d" class="day-col">{{ d }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in rowDefs" :key="row.key">
                  <th class="label-col">{{ row.label }}</th>
                  <td
                    v-for="d in columns"
                    :key="`${row.key}-${d}`"
                    class="cell"
                    :class="getCellClass(g, d, row.key)"
                  >
                    {{ fmt(getValue(g, d, row.key), row.showZero) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <div v-else class="status">データがありません</div>
    </div>

    <!-- ライン/工程コード確認モーダル（F4で開く） -->
    <div v-if="showCodeLookup" class="code-modal-overlay" @click.self="closeCodeLookup">
      <div class="code-modal">
        <div class="code-modal-header">
          <h3>ライン・工程コード一覧</h3>
          <button class="close-btn" type="button" @click="closeCodeLookup">×</button>
        </div>
        <div class="code-modal-body">
          <input
            type="text"
            v-model="codeSearch"
            placeholder="コード/名称で絞り込み"
            class="code-search"
          />
          <div class="code-columns">
            <div class="code-column">
              <div class="column-title">ライン</div>
              <div class="code-list">
                <button
                  v-for="line in filteredLines"
                  :key="line.id"
                  type="button"
                  class="code-item"
                  @click="applyLine(line)"
                >
                  <strong>{{ line.line_code || '-' }}</strong>
                  <span>{{ line.line_name || '名称未設定' }}</span>
                </button>
              </div>
            </div>
            <div class="code-column">
              <div class="column-title">工程</div>
              <div class="code-list">
                <button
                  v-for="p in filteredProcesses"
                  :key="p.id"
                  type="button"
                  class="code-item"
                  @click="applyProcess(p)"
                >
                  <strong>{{ p.process_code || '-' }}</strong>
                  <span>{{ p.process_name || '名称未設定' }}</span>
                </button>
              </div>
            </div>
          </div>
          <p class="code-hint">行をクリックするとフィルタ欄にセットします。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from "vue";
import api from "@/api/client";
import { addDays, formatISODate, parseISODate } from "@/utils/dateUtil";

const lineFilter = ref("");
const processFilter = ref("");
const productFilter = ref("");
const defaultStart = new Date();
defaultStart.setDate(1);
const startDate = ref(formatISODate(defaultStart));
const horizon = ref(30);
const loading = ref(false);
const recalculating = ref(false);
const error = ref("");
const backlogs = ref([]);
const lineDemands = ref([]);
let userSetStart = false;
const onStartChange = () => {
  userSetStart = true;
};

// フィルタ入力でEnter押下時に更新を実行
const handleEnter = () => {
  if (loading.value) return;
  load();
};

const hasFilter = computed(() =>
  Boolean(lineFilter.value || processFilter.value || productFilter.value)
);

const columns = computed(() => {
  const start = parseISODate(startDate.value);
  const cols = [];
  for (let i = 0; i < horizon.value; i++) {
    cols.push(formatISODate(addDays(start, i)));
  }
  return cols;
});

const rowDefs = [
  { key: "forecast", label: "内示" },
  { key: "firm", label: "確定" },
  { key: "plan", label: "計画" },
  { key: "actual", label: "実績" },
  { key: "adjust", label: "調整" },
  { key: "plannedProgress", label: "計進", showZero: true },
  { key: "progress", label: "進度", showZero: true },
];

const getBacklogParams = () => {
  const start = columns.value[0];
  const end = columns.value[columns.value.length - 1];
  return {
    plan_date__gte: start,
    plan_date__lte: end,
    include_order_split: true,
  };
};

const applyBacklogs = (payload) => {
  const list = Array.isArray(payload) ? payload : payload.results || [];
  backlogs.value = list;
  if (!userSetStart && !startDate.value && backlogs.value.length) {
    const minDate = backlogs.value.map((d) => d.plan_date).sort()[0];
    if (minDate) {
      startDate.value = minDate;
    }
  }
};

const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    const [backlogRes, demandRes] = await Promise.all([
      api.lineBacklogs.getLineBacklogs(getBacklogParams()),
      api.lineDemands.list({
        plan_date__gte: columns.value[0],
        plan_date__lte: columns.value[columns.value.length - 1],
        page_size: 5000,
      }),
    ]);
    applyBacklogs(backlogRes.data || []);
    const demandPayload = demandRes?.data || [];
    lineDemands.value = Array.isArray(demandPayload) ? demandPayload : demandPayload.results || [];
  } catch (e) {
    error.value = e?.message || "読み込みに失敗しました";
  } finally {
    loading.value = false;
  }
};

const getDisplayedLineIds = () => {
  const ids = new Set();
  groups.value.forEach((g) => {
    if (g.line_id) ids.add(g.line_id);
  });
  return Array.from(ids);
};

const recalculate = async () => {
  const lineIds = getDisplayedLineIds();
  if (!lineIds.length) {
    alert("再計算対象のラインがありません。先にデータを取得してください。");
    return;
  }
  recalculating.value = true;
  error.value = "";
  try {
    const start = columns.value[0];
    const end = columns.value[columns.value.length - 1];
    await Promise.all(
      lineIds.map((lineId) =>
        api.lineBacklogs
          .recalculateInventory({
            line_id: lineId,
            start_date: start,
            end_date: end,
            include_progress: true,
          })
          .catch((e) => console.error("再計算に失敗:", e))
      )
    );
    await load();
  } catch (e) {
    console.error(e);
    error.value = e?.message || "再計算に失敗しました";
  } finally {
    recalculating.value = false;
  }
};

// ライン・工程コード参照 (F4で開く)
const showCodeLookup = ref(false);
const lineList = ref([]);
const processList = ref([]);
const codeSearch = ref("");
const lookupLoading = ref(false);

const fetchCodeLookupData = async () => {
  if (lineList.value.length && processList.value.length) return;
  lookupLoading.value = true;
  try {
    const [lineRes, processRes] = await Promise.all([
      api.lines.getLines(),
      api.processes.getProcesses({ is_active: true }),
    ]);
    lineList.value = lineRes.data?.results || lineRes.data || [];
    processList.value = processRes.data?.results || processRes.data || [];
  } catch (e) {
    console.error("コード一覧の取得に失敗:", e);
    alert("ライン・工程コードの取得に失敗しました。");
  } finally {
    lookupLoading.value = false;
  }
};

const filteredLines = computed(() => {
  const kw = codeSearch.value.trim().toLowerCase();
  if (!kw) return lineList.value;
  return lineList.value.filter((l) =>
    `${l.line_code || ""}${l.line_name || ""}`.toLowerCase().includes(kw)
  );
});

const filteredProcesses = computed(() => {
  const kw = codeSearch.value.trim().toLowerCase();
  if (!kw) return processList.value;
  return processList.value.filter((p) =>
    `${p.process_code || ""}${p.process_name || ""}`.toLowerCase().includes(kw)
  );
});

const openCodeLookup = async () => {
  if (showCodeLookup.value) return;
  await fetchCodeLookupData();
  showCodeLookup.value = true;
};

const closeCodeLookup = () => {
  showCodeLookup.value = false;
  codeSearch.value = "";
};

const applyLine = (line) => {
  lineFilter.value = line.line_code || "";
  closeCodeLookup();
};

const applyProcess = (process) => {
  processFilter.value = process.process_code || "";
  closeCodeLookup();
};

// 修飾キーなしのF4でコード一覧を開く
const handleKeyDown = (e) => {
  if (e.key === "F4" && !e.altKey && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
    e.preventDefault();
    openCodeLookup();
  }
};

onMounted(() => {
  window.addEventListener("keydown", handleKeyDown);
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", handleKeyDown);
});

const createEmptyCell = () => ({
  forecast: 0,
  firm: 0,
  plan: 0,
  actual: 0,
  adjust: 0,
  progress: 0,
  plannedProgress: 0,
});

const groups = computed(() => {
  if (!backlogs.value.length) return [];
  const start = columns.value[0];
  const end = columns.value[columns.value.length - 1];
  const lineKeyword = lineFilter.value.trim().toLowerCase();
  const processKeyword = processFilter.value.trim().toLowerCase();
  const productKeyword = productFilter.value.trim().toLowerCase();

  const filtered = backlogs.value.filter((d) => {
    const within = d.plan_date >= start && d.plan_date <= end;
    const lineText = `${d.line_code || ""}${d.line_name || ""}`.toLowerCase();
    const processText = `${d.process_code || ""}${d.process_name || ""}`.toLowerCase();
    const prodText = `${d.product_code || ""}${d.product_name || ""}`.toLowerCase();
    const okLine = !lineKeyword || lineText.includes(lineKeyword);
    const okProcess = !processKeyword || processText.includes(processKeyword);
    const okProd = !productKeyword || prodText.includes(productKeyword);
    return within && okLine && okProcess && okProd;
  });

  // 顧客の内示/確定 (LineDemand) を日付・ライン・工程・品番でマップ化
  const filteredDemands = lineDemands.value.filter((d) => {
    const within = d.plan_date >= start && d.plan_date <= end;
    const lineText = `${d.line_code || ""}${d.line_name || ""}${d.line || ""}`.toLowerCase();
    const processText = `${d.process_code || ""}${d.process_name || ""}`.toLowerCase();
    const prodText = `${d.product_code || ""}${d.product_name || ""}`.toLowerCase();
    const okLine = !lineKeyword || lineText.includes(lineKeyword);
    const okProcess = !processKeyword || processText.includes(processKeyword);
    const okProd = !productKeyword || prodText.includes(productKeyword);
    return within && okLine && okProcess && okProd;
  });

  const demandMap = new Map();
  filteredDemands.forEach((d) => {
    const keyWithProcess = `${d.line || ""}__${d.process || ""}__${d.product || ""}__${d.plan_date}`;
    const keyNoProcess = `${d.line || ""}____${d.product || ""}__${d.plan_date}`;
    const forecast = Number(d.forecast_qty || 0);
    const firm = Number(d.firm_qty || 0);
    for (const k of [keyWithProcess, keyNoProcess]) {
      const existing = demandMap.get(k);
      if (existing) {
        existing.forecast += forecast;
        existing.firm += firm;
      } else {
        demandMap.set(k, { forecast, firm });
      }
    }
  });

  const pickDemand = (lineId, processId, productId, date) => {
    const k1 = `${lineId || ""}__${processId || ""}__${productId || ""}__${date}`;
    const k2 = `${lineId || ""}____${productId || ""}__${date}`;
    return demandMap.get(k1) || demandMap.get(k2) || null;
  };

  const map = new Map();
  for (const d of filtered) {
    const key = `${d.line || d.line_name || ""}__${d.process_code || d.process || ""}__${d.product_code || ""}`;
    if (!map.has(key)) {
      map.set(key, {
        key,
        line_id: d.line,
        line_code: d.line_code,
        line_name: d.line_name,
        process_id: d.process,
        process_code: d.process_code || d.process || "",
        process_name: d.process_name || "",
        product_id: d.product,
        product_code: d.product_code,
        product_name: d.product_name,
        cells: {},
      });
    }
    const g = map.get(key);
    if (!g.cells[d.plan_date]) {
      g.cells[d.plan_date] = createEmptyCell();
    }
    const cell = g.cells[d.plan_date];

    // 顧客の内示/確定はLineDemandから取得
    const demandVal = pickDemand(d.line, d.process, d.product, d.plan_date);
    if (demandVal) {
      cell.forecast = demandVal.forecast;
      cell.firm = demandVal.firm;
    }

    cell.plan += Number(d.plan_qty || 0);
    cell.actual += Number(d.actual_qty || 0);
    cell.adjust += Number(d.adjust_qty || 0);
    cell.progress += Number(d.progress_qty || 0);
    cell.plannedProgress += Number(d.planned_progress_qty || 0);
  }

  return Array.from(map.values());
});

const formatLine = (group) => {
  const code = group.line_code || "";
  const name = group.line_name || "";
  if (code && name) return `${code} ${name}`;
  return code || name || "-";
};

const fmt = (n, showZero = false) => {
  if (n === null || n === undefined) return "";
  const num = Number(n);
  if (Number.isNaN(num)) return "";
  if (num === 0 && !showZero) return "";
  return num.toLocaleString();
};

const getValue = (group, date, key) => {
  return group.cells?.[date]?.[key] ?? "";
};

const getCellClass = (group, date, rowKey) => {
  const val = Number(getValue(group, date, rowKey) || 0);
  if (rowKey === "adjust" && val < 0) return "negative";
  if ((rowKey === "progress" || rowKey === "plannedProgress") && val < 0) return "negative-strong";
  return "";
};
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  align-items: flex-start;
}
.page-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.page-actions input,
.page-actions select {
  padding: 6px 8px;
}
.subtitle {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.status {
  padding: 18px;
  text-align: center;
  color: #475569;
}
.status.error {
  color: #b91c1c;
}

.group-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.group-card {
  display: grid;
  grid-template-columns: 260px 1fr;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
}
.info-block {
  padding: 10px;
  border-right: 1px solid #e5e7eb;
  background: #f8fafc;
}
.info-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 4px;
  border-bottom: 1px solid #e5e7eb;
  font-size: 13px;
}
.info-label {
  font-weight: 700;
  color: #374151;
}
.info-value {
  color: #111827;
  margin-left: 8px;
}
.matrix-block {
  overflow: auto;
}
.matrix-table {
  border-collapse: collapse;
  min-width: 960px;
  width: 100%;
}
.matrix-table th,
.matrix-table td {
  border: 1px solid #e5e7eb;
  padding: 6px 8px;
  text-align: right;
  min-width: 80px;
}
.matrix-table thead th {
  position: sticky;
  top: 0;
  background: #f4f6fb;
  z-index: 1;
  text-align: center;
}
.label-col {
  position: sticky;
  left: 0;
  background: #f9fafb;
  z-index: 2;
  text-align: left;
  min-width: 100px;
}
.cell {
  background: #fff;
}
.cell.negative {
  background: #fff2f2;
  color: #c53030;
  font-weight: 700;
}
.cell.negative-strong {
  background: #ffe4e6;
  color: #b91c1c;
  font-weight: 700;
}

.code-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000;
}
.code-modal {
  background: #fff;
  border-radius: 10px;
  width: min(900px, 92vw);
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
  overflow: hidden;
}
.code-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #2f9e63; /* 薄い緑系 */
  color: #fff;
}
.close-btn {
  background: transparent;
  border: none;
  color: #fff;
  font-size: 18px;
  cursor: pointer;
}
.code-modal-body {
  padding: 12px 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.code-search {
  padding: 8px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
}
.code-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.code-column {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.column-title {
  background: #f3f4f6;
  padding: 8px 10px;
  font-weight: 700;
  border-bottom: 1px solid #e5e7eb;
}
.code-list {
  max-height: 300px;
  overflow: auto;
  display: flex;
  flex-direction: column;
}
.code-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: none;
  border-bottom: 1px solid #f1f5f9;
  background: #fff;
  cursor: pointer;
  text-align: left;
}
.code-item:hover {
  background: #e6f7ec; /* 薄い緑系のハイライト */
}
.code-item strong {
  min-width: 80px;
}
.code-hint {
  margin: 0;
  color: #6b7280;
  font-size: 12px;
}

@media (max-width: 720px) {
  .code-columns {
    grid-template-columns: 1fr;
  }
}
</style>
