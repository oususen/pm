<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">進捗管理 <DataSourceDialog title="進捗管理" :sources="dsSources" /></h2>
      <div class="page-actions">
        <input
          type="text"
          v-model="lineFilter"
          placeholder="ラインコード/名称で絞り込み"
        />
        <input
          type="text"
          v-model="processFilter"
          placeholder="工程コード/名称で絞り込み"
        />
        <input
          type="text"
          v-model="productFilter"
          placeholder="品番/品名で絞り込み"
        />
        <input type="date" v-model="startDate" @change="onStartChange" />
        <select v-model.number="horizon">
          <option :value="7">7日</option>
          <option :value="14">14日</option>
          <option :value="30">30日</option>
          <option :value="60">60日</option>
          <option :value="90">90日</option>
        </select>
        <button @click="load" :disabled="loading">更新</button>
      </div>
    </div>

    <div class="page-content">
      <div v-if="loading">読込中...</div>
      <div v-else-if="error" class="no-data">エラー: {{ error }}</div>
      <div v-else>
        <div v-if="rows.length" class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th class="sticky-col" style="min-width: 220px;">ライン / 工程 / 品目</th>
                <th v-for="d in columns" :key="d.date" class="date-head">
                  <div>{{ d.label }}</div>
                  <div class="weekday">{{ d.weekday }}</div>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in pagedRows" :key="r.key">
                <td class="sticky-col">{{ r.label }}</td>
                <td v-for="d in columns" :key="d.date" :class="['num', getCellClass(r, d.date)]">
                  <template v-if="r.cells[d.date]">
                    <div v-if="showPlan(r.cells[d.date])">P: {{ fmt(r.cells[d.date].plan) }}</div>
                    <div v-if="showActual(r.cells[d.date])">A: {{ fmt(r.cells[d.date].actual) }}</div>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="rows.length" class="pagination-area">
          <div class="pagination" v-if="totalPages > 1">
            <button class="pagination-btn" :disabled="currentPage === 1" @click="changePage(1)">
              最初
            </button>
            <button class="pagination-btn" :disabled="currentPage === 1" @click="changePage(currentPage - 1)">
              前へ
            </button>
            <button
              v-for="page in visiblePages"
              :key="page"
              class="pagination-btn"
              :class="{ 'is-active': page === currentPage }"
              @click="changePage(page)"
            >
              {{ page }}
            </button>
            <button class="pagination-btn" :disabled="currentPage >= totalPages" @click="changePage(currentPage + 1)">
              次へ
            </button>
            <button class="pagination-btn" :disabled="currentPage >= totalPages" @click="changePage(totalPages)">
              最後
            </button>
          </div>
          <div class="pagination-info">
            <span>{{ pageRangeLabel }}</span>
          </div>
        </div>
        <div v-else class="no-data">データがありません</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import api from "@/api/client";
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'
import { addDays, formatISODate, parseISODate } from "@/utils/dateUtil";
import {
  compareBySpecialOrderThenProductCode,
  resolveSpecialDisplayOrder,
} from "@/utils/groupSort";

const dsSources = [
  { op: '読み取り', table: 'line_backlog', desc: '生産計画・実績データ' },
  { op: '読み取り', table: 'm_line', desc: 'ライン一覧' },
]

const lineFilter = ref("");
const processFilter = ref("");
const productFilter = ref("");
const startDate = ref(formatISODate(new Date()));
const horizon = ref(7);
const loading = ref(false);
const error = ref("");
const backlogs = ref([]);
const productionLines = ref([]);
const currentPage = ref(1);
const pageSize = 20;
let userSetStart = false;
const onStartChange = () => {
  userSetStart = true;
};

const productionLineIds = computed(() => new Set(
  productionLines.value.map((line) => String(line.id))
));

const columns = computed(() => {
  const start = parseISODate(startDate.value);
  const cols = [];
  const weekdays = ["日", "月", "火", "水", "木", "金", "土"];
  for (let i = 0; i < horizon.value; i++) {
    const date = addDays(start, i);
    const dateStr = formatISODate(date);
    const dayLabel = weekdays[date.getDay()];
    cols.push({ date: dateStr, label: `${dateStr}`, weekday: dayLabel });
  }
  return cols;
});

const rows = computed(() => {
  if (!backlogs.value.length) return [];
  const start = columns.value[0]?.date;
  const end = columns.value[columns.value.length - 1]?.date;
  const lineKeyword = lineFilter.value.trim().toLowerCase();
  const processKeyword = processFilter.value.trim().toLowerCase();
  const productKeyword = productFilter.value.trim().toLowerCase();

  const isWithinRange = (d) => {
    if (!start || !end) return true;
    return d.plan_date >= start && d.plan_date <= end;
  };

  const matchesFilters = (d) => {
    const lineId = d.line ?? d.line_id;
    const isProductionLine =
      productionLineIds.value.size === 0 ||
      (lineId !== null && lineId !== undefined && productionLineIds.value.has(String(lineId)));
    const lineText = `${d.line_code || ""}${d.line_name || ""}${d.line || ""}`.toLowerCase();
    const processText = `${d.process_code || ""}${d.process_name || ""}${d.process || ""}`.toLowerCase();
    const productText = `${d.product_code || ""}${d.product_name || ""}`.toLowerCase();
    const okLine = !lineKeyword || lineText.includes(lineKeyword);
    const okProcess = !processKeyword || processText.includes(processKeyword);
    const okProduct = !productKeyword || productText.includes(productKeyword);
    return isWithinRange(d) && isProductionLine && okLine && okProcess && okProduct;
  };

  const map = new Map();
  const filteredBacklogs = backlogs.value.filter((d) => matchesFilters(d));
  for (const d of filteredBacklogs) {
    if (!d.plan_date) continue;
    const key = `${d.line_code || d.line_name || d.line || ""}__${d.process_code || d.process_name || d.process || ""}__${d.product_code}`;
    const specialDisplayOrder = resolveSpecialDisplayOrder(d);
    if (!map.has(key)) {
      const lineLabel = d.line_code || d.line_name || d.line || "-";
      const processLabel = d.process_code || d.process_name || d.process || "-";
      map.set(key, {
        key,
        label: `${lineLabel} / ${processLabel} / ${d.product_code}`,
        product_code: d.product_code || "",
        special_display_order: specialDisplayOrder,
        cells: {},
      });
    }
    const row = map.get(key);
    if (specialDisplayOrder !== null) {
      const currentOrder = resolveSpecialDisplayOrder(row);
      if (currentOrder === null || specialDisplayOrder < currentOrder) {
        row.special_display_order = specialDisplayOrder;
      }
    }
    if (!row.cells[d.plan_date]) {
      row.cells[d.plan_date] = { plan: 0, actual: 0 };
    }
    row.cells[d.plan_date].plan += Number(d.plan_qty || 0);
    row.cells[d.plan_date].actual += Number(d.actual_qty || 0);
  }
  const result = Array.from(map.values());
  result.sort((a, b) =>
    compareBySpecialOrderThenProductCode(a, b, {
      codeGetter: (item) => item.product_code || "",
    })
  );
  return result;
});

const totalPages = computed(() => {
  if (!rows.value.length) return 1;
  return Math.ceil(rows.value.length / pageSize);
});

const visiblePages = computed(() => {
  const total = totalPages.value;
  const current = currentPage.value;
  const windowSize = 2;
  const start = Math.max(1, current - windowSize);
  const end = Math.min(total, current + windowSize);
  const pages = [];
  for (let i = start; i <= end; i += 1) {
    pages.push(i);
  }
  return pages;
});

const pageRangeLabel = computed(() => {
  const total = rows.value.length;
  if (total === 0) return "0件";
  const start = (currentPage.value - 1) * pageSize + 1;
  const end = Math.min(currentPage.value * pageSize, total);
  return `${total}件中 ${start}-${end}件`;
});

const pagedRows = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  return rows.value.slice(start, start + pageSize);
});

const fmt = (n) => (n === null || n === undefined ? "" : n.toLocaleString());

const showPlan = (cell) => {
  const plan = Number(cell?.plan ?? 0);
  if (!Number.isFinite(plan)) return false;
  return plan !== 0;
};

const showActual = (cell) => {
  const plan = Number(cell?.plan ?? 0);
  const actual = Number(cell?.actual ?? 0);
  if (!Number.isFinite(plan) || !Number.isFinite(actual)) return false;
  return !(plan === 0 && actual === 0);
};

const getCellClass = (row, date) => {
  const cell = row?.cells?.[date];
  if (!cell) return "";
  if (!showPlan(cell) && !showActual(cell)) return "";
  const plan = Number(cell.plan ?? 0);
  const actual = Number(cell.actual ?? 0);
  if (!Number.isFinite(plan) || !Number.isFinite(actual)) return "";
  if (actual > plan) return "cell-over";
  if (actual === plan) return "cell-equal";
  return "cell-under";
};

const changePage = (page) => {
  const target = Math.min(Math.max(page, 1), totalPages.value);
  if (target === currentPage.value) return;
  currentPage.value = target;
};

const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    const start = columns.value[0]?.date;
    const end = columns.value[columns.value.length - 1]?.date;
    const [backlogsRes, productionLinesRes] = await Promise.all([
      api.lineBacklogs.getLineBacklogs({
        plan_date__gte: start,
        plan_date__lte: end,
      }),
      api.lines.getProductionLines(),
    ]);
    const backlogPayload = backlogsRes?.data || [];
    backlogs.value = Array.isArray(backlogPayload)
      ? backlogPayload
      : backlogPayload.results || [];
    const linePayload = productionLinesRes?.data || [];
    productionLines.value = Array.isArray(linePayload)
      ? linePayload
      : linePayload.results || [];
  } catch (e) {
    error.value = e?.message || "読み込みに失敗しました";
  } finally {
    loading.value = false;
  }
};

onMounted(load);

watch([lineFilter, processFilter, productFilter, startDate, horizon], () => {
  currentPage.value = 1;
});

watch(rows, () => {
  if (currentPage.value > totalPages.value) {
    currentPage.value = totalPages.value;
  }
});
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.page-content {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.num {
  text-align: right;
  min-width: 80px;
}

.table-wrap {
  flex: 1;
  min-height: 0;
  overflow: auto;
  max-height: calc(100vh - 240px);
}

.data-table {
  border-collapse: collapse;
  width: max-content;
  min-width: 100%;
}

.data-table th,
.data-table td {
  border: 1px solid #94a3b8;
  padding: 6px 8px;
}

.data-table thead th {
  position: sticky;
  top: 0;
  background: #f3f4f6;
  z-index: 3;
}

.data-table thead th:not(.sticky-col) {
  min-width: 80px;
}

.date-head {
  text-align: center;
}

.weekday {
  font-size: 11px;
  color: #475569;
  margin-top: 2px;
}

.pagination-area {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pagination {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.pagination-btn {
  padding: 4px 10px;
  border: 1px solid #94a3b8;
  background-color: #fff;
  color: #334155;
  border-radius: 4px;
  cursor: pointer;
}

.pagination-btn.is-active {
  background-color: #334155;
  border-color: #334155;
  color: #fff;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-info {
  font-size: 12px;
  color: #64748b;
}

.sticky-col {
  position: sticky;
  left: 0;
  background: #fff;
  z-index: 2;
}

.data-table thead .sticky-col {
  background: #f3f4f6;
  z-index: 4;
}

.cell-over {
  background: #fef3c7;
}

.cell-equal {
  background: #dcfce7;
}

.cell-under {
  background: #fecaca;
}

input,
select {
  padding: 4px 6px;
  font-size: 12px;
}
</style>

