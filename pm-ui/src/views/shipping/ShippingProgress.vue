<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">出荷進度照会</h2>
        <p class="subtitle">受注明細を基準に、日付別の内示・確定・実績・調整・進度を一覧化します。</p>
      </div>
      <div class="page-actions">
        <input
          type="text"
          v-model="lineFilter"
          placeholder="ラインコード/名称で絞り込み"
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
          <option :value="21">21日</option>
          <option :value="30">30日</option>
        </select>
        <button @click="load" :disabled="loading">更新</button>
      </div>
    </div>

    <div v-if="loading" class="loading">読込中...</div>
    <div v-else-if="error" class="no-data">エラー: {{ error }}</div>
    <div v-else>
      <div v-if="groups.length" class="group-list">
        <div v-for="g in groups" :key="g.key" class="group-card">
          <div class="info-block">
            <div class="info-row">
              <span class="info-label">品番</span>
              <span class="info-value">{{ g.product_code || "-" }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">品名</span>
              <span class="info-value">{{ g.product_name || "-" }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">ライン</span>
              <span class="info-value">{{ formatLine(g) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">工程</span>
              <span class="info-value">{{ formatProcess(g) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">合計内示</span>
              <span class="info-value">{{ fmtSummary(g.summary.forecast) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">合計確定</span>
              <span class="info-value">{{ fmtSummary(g.summary.firm) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">合計実績</span>
              <span class="info-value">{{ fmtSummary(g.summary.actual) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">合計調整</span>
              <span class="info-value" :class="{ negative: g.summary.adjust < 0 }">
                {{ fmtSummary(g.summary.adjust) }}
              </span>
            </div>
            <div class="info-row">
              <span class="info-label">進度</span>
              <span class="info-value">{{ g.summary.progressRate }}</span>
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
                    {{ row.key === "progress" ? getProgressRate(g, d) : fmt(getValue(g, d, row.key)) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <div v-else class="no-data">データがありません</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import api from "@/api/client";
import { addDays, formatISODate, parseISODate } from "@/utils/dateUtil";

const lineFilter = ref("");
const productFilter = ref("");
const startDate = ref(formatISODate(new Date()));
const horizon = ref(14);
const loading = ref(false);
const error = ref("");
const orderLines = ref([]);
const backlogs = ref([]);
let userSetStart = false;
const onStartChange = () => {
  userSetStart = true;
};

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
  { key: "actual", label: "実績" },
  { key: "adjust", label: "調整" },
  { key: "progress", label: "進度" },
];

const normalizeList = (payload) => {
  return Array.isArray(payload) ? payload : payload.results || [];
};

const applyOrderLines = (payload) => {
  const list = normalizeList(payload);
  orderLines.value = list;
  if (!userSetStart && orderLines.value.length) {
    const minDate = orderLines.value
      .map((d) => d.due_date)
      .sort()[0];
    if (minDate) {
      startDate.value = minDate;
    }
  }
};

const backlogKey = (productCode, date) => `${productCode || ""}__${date || ""}`;

const backlogMap = computed(() => {
  const map = new Map();
  for (const b of backlogs.value) {
    const key = backlogKey(b.product_code, b.plan_date);
    const current = map.get(key) || { actual: 0, adjust: 0 };
    current.actual += Number(b.actual_shipment_qty || 0);
    current.adjust += Number(b.adjust_qty || 0);
    map.set(key, current);
  }
  return map;
});

const groups = computed(() => {
  if (!orderLines.value.length) return [];
  const filtered = orderLines.value.filter((d) => {
    if (!d.due_date) return false;
    const within =
      d.due_date >= columns.value[0] &&
      d.due_date <= columns.value[columns.value.length - 1];
    const lineText = `${d.plant_code || ""}${d.ship_to_code || ""}`.toLowerCase();
    const prodText = `${d.product_code || ""}${d.product_name || ""}`.toLowerCase();
    const okLine =
      !lineFilter.value ||
      lineText.includes(lineFilter.value.trim().toLowerCase());
    const okProd =
      !productFilter.value ||
      prodText.includes(productFilter.value.trim().toLowerCase());
    return within && okLine && okProd;
  });

  const map = new Map();
  for (const d of filtered) {
    const key = `${d.product_code || ""}`;
    if (!map.has(key)) {
      map.set(key, {
        key,
        line_code: "",
        line_name: "",
        product_code: d.product_code,
        product_name: d.product_name,
        process_code: "",
        process_name: "",
        cells: {},
        totals: { forecast: 0, firm: 0, actual: 0, adjust: 0 },
        summary: { forecast: 0, firm: 0, actual: 0, adjust: 0, progressRate: "-" },
      });
    }
    const g = map.get(key);
    if (!g.cells[d.due_date]) {
      g.cells[d.due_date] = {
        forecast: 0,
        firm: 0,
        actual: 0,
        adjust: 0,
      };
    }
    const c = g.cells[d.due_date];
    const qty = Number(d.quantity || 0);
    if (d.order_type === "FORECAST") {
      c.forecast += qty;
    } else if (d.order_type === "FIRM") {
      c.firm += qty;
    } else {
      c.firm += qty;
    }
  }

  return Array.from(map.values()).map((g) => {
    g.totals = { forecast: 0, firm: 0, actual: 0, adjust: 0 };
    Object.entries(g.cells).forEach(([date, cell]) => {
      const backlog = backlogMap.value.get(backlogKey(g.product_code, date));
      cell.actual = backlog ? backlog.actual : 0;
      cell.adjust = backlog ? backlog.adjust : 0;
      g.totals.forecast += cell.forecast;
      g.totals.firm += cell.firm;
      g.totals.actual += cell.actual;
      g.totals.adjust += cell.adjust;
    });
    const denom = g.totals.firm > 0 ? g.totals.firm : g.totals.forecast;
    const rate = denom > 0 ? `${Math.round((g.totals.actual / denom) * 100)}%` : "-";
    g.summary = {
      forecast: g.totals.forecast,
      firm: g.totals.firm,
      actual: g.totals.actual,
      adjust: g.totals.adjust,
      progressRate: rate,
    };
    return g;
  });
});

const fmt = (n) => {
  if (n === null || n === undefined) return "";
  const num = Number(n);
  if (Number.isNaN(num)) return "";
  if (num === 0) return "";
  return num.toLocaleString();
};

const fmtSummary = (n) => {
  if (n === null || n === undefined) return "-";
  const num = Number(n);
  if (Number.isNaN(num)) return "-";
  return num.toLocaleString();
};

const getValue = (group, date, key) => {
  return group.cells?.[date]?.[key] ?? "";
};

const getProgressRate = (group, date) => {
  const firm = group.cells?.[date]?.firm ?? 0;
  const forecast = group.cells?.[date]?.forecast ?? 0;
  const actual = group.cells?.[date]?.actual ?? 0;
  const denom = firm > 0 ? firm : forecast;
  if (denom <= 0) return "-";
  return `${Math.round((actual / denom) * 100)}%`;
};

const getCellClass = (group, date, rowKey) => {
  if (rowKey === "progress") return "";
  const value = getValue(group, date, rowKey);
  if (value !== null && value !== undefined && Number(value) < 0) {
    return "negative";
  }
  return "";
};

const formatLine = (group) => {
  if (group.line_code && group.line_name) {
    return `${group.line_code} / ${group.line_name}`;
  }
  return group.line_code || group.line_name || "-";
};

const formatProcess = (group) => {
  if (group.process_code && group.process_name) {
    return `${group.process_code} / ${group.process_name}`;
  }
  return group.process_code || group.process_name || "-";
};

const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    const [orderLinesRes, backlogsRes] = await Promise.all([
      api.orders.listOrderLines({ page_size: 10000 }),
      api.lineBacklogs.getLineBacklogs(),
    ]);
    applyOrderLines(orderLinesRes.data || []);
    backlogs.value = normalizeList(backlogsRes.data || []);
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
  gap: 12px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
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

.group-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.group-card {
  display: grid;
  grid-template-columns: 260px 1fr;
  border: 1px solid #dce3ef;
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
.info-value.negative {
  color: #c00;
  font-weight: 700;
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
  background: #fee;
  color: #c00;
  font-weight: 700;
}
.no-data,
.loading {
  padding: 24px;
  text-align: center;
  color: #6b7280;
}
</style>
