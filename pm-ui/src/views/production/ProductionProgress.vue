<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">進捗管理</h2>
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
                <th v-for="d in columns" :key="d">{{ d }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in rows" :key="r.key">
                <td class="sticky-col">{{ r.label }}</td>
                <td v-for="d in columns" :key="d" :class="['num', getCellClass(r, d)]">
                  <template v-if="r.cells[d]">
                    <div v-if="showPlan(r.cells[d])">P: {{ fmt(r.cells[d].plan) }}</div>
                    <div v-if="showActual(r.cells[d])">A: {{ fmt(r.cells[d].actual) }}</div>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="no-data">データがありません</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import api from "@/api/client";
import { addDays, formatISODate, parseISODate } from "@/utils/dateUtil";

const lineFilter = ref("");
const processFilter = ref("");
const productFilter = ref("");
const startDate = ref(formatISODate(new Date()));
const horizon = ref(7);
const loading = ref(false);
const error = ref("");
const backlogs = ref([]);
const productionLines = ref([]);
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
  for (let i = 0; i < horizon.value; i++) {
    cols.push(formatISODate(addDays(start, i)));
  }
  return cols;
});

const rows = computed(() => {
  if (!backlogs.value.length) return [];
  const start = columns.value[0];
  const end = columns.value[columns.value.length - 1];
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
    if (!map.has(key)) {
      const lineLabel = d.line_code || d.line_name || d.line || "-";
      const processLabel = d.process_code || d.process_name || d.process || "-";
      map.set(key, {
        key,
        label: `${lineLabel} / ${processLabel} / ${d.product_code}`,
        cells: {},
      });
    }
    const row = map.get(key);
    if (!row.cells[d.plan_date]) {
      row.cells[d.plan_date] = { plan: 0, actual: 0 };
    }
    row.cells[d.plan_date].plan += Number(d.plan_qty || 0);
    row.cells[d.plan_date].actual += Number(d.actual_qty || 0);
  }
  return Array.from(map.values());
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

const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    const start = columns.value[0];
    const end = columns.value[columns.value.length - 1];
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
  min-width: 120px;
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
  border: 1px solid #e5e7eb;
  padding: 6px 8px;
}

.data-table thead th {
  position: sticky;
  top: 0;
  background: #f3f4f6;
  z-index: 3;
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
  background: #fee2e2;
}

input,
select {
  padding: 4px 6px;
  font-size: 12px;
}
</style>
