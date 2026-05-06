<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">受注展開</h2>
        <p class="subtitle">完成品と構成部品の内示・確定・計進・進度を表示します。</p>
      </div>
      <button type="button" @click="goBack">戻る</button>
    </div>

    <div v-if="loading" class="status">読込中...</div>
    <div v-else-if="error" class="status error">{{ error }}</div>
    <div v-else-if="!blocks.length" class="status">データがありません</div>
    <div v-else class="block-list-wrap">
      <div ref="mainScrollRef" class="block-list" @scroll="syncFromMain">
        <div v-for="b in pagedBlocks" :key="b.key" class="block-card">
          <div class="block-body">
            <div class="meta-panel">
              <template v-if="b.is_shipping_summary">
                <div class="meta-row"><span class="meta-label">完成品</span><span class="meta-value">{{ b.product_code }}</span></div>
                <div class="meta-row"><span class="meta-label">品名</span><span class="meta-value">{{ b.product_name || "-" }}</span></div>
                <div class="meta-row"><span class="meta-label">納入場</span><span class="meta-value">{{ b.ship_to_display || "-" }}</span></div>
                <div class="meta-row"><span class="meta-label">顧客</span><span class="meta-value">{{ b.customer_display || "-" }}</span></div>
              </template>
              <template v-else>
                <div class="meta-row"><span class="meta-label">品番</span><span class="meta-value">{{ b.product_code }}</span></div>
                <div class="meta-row"><span class="meta-label">品名</span><span class="meta-value">{{ b.product_name || "-" }}</span></div>
                <div class="meta-row"><span class="meta-label">ライン</span><span class="meta-value">{{ b.line_display || "-" }}</span></div>
                <div class="meta-row"><span class="meta-label">工程</span><span class="meta-value">{{ b.process_display || "-" }}</span></div>
              </template>
            </div>
            <table class="matrix-table">
              <thead>
                <tr>
                  <th class="label-col">項目</th>
                  <th
                    v-for="d in columns"
                    :key="`${b.key}-${d}`"
                    class="day-col"
                    :class="{ holiday: isHoliday(d) }"
                  >
                    {{ formatDateHeader(d) }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th class="label-col">内示</th>
                  <td v-for="d in columns" :key="`${b.key}-f-${d}`" class="day-col" :class="{ holiday: isHoliday(d) }">{{ fmt(b.forecast?.[d] || 0) }}</td>
                </tr>
                <tr>
                  <th class="label-col">確定</th>
                  <td v-for="d in columns" :key="`${b.key}-fi-${d}`" class="day-col" :class="{ holiday: isHoliday(d) }">{{ fmt(b.firm?.[d] || 0) }}</td>
                </tr>
                <tr>
                  <th class="label-col">実績</th>
                  <td v-for="d in columns" :key="`${b.key}-pp-${d}`" class="day-col" :class="{ holiday: isHoliday(d) }">{{ fmt(b.planned_progress?.[d] || 0) }}</td>
                </tr>
                <tr>
                  <th class="label-col">調整</th>
                  <td v-for="d in columns" :key="`${b.key}-ad-${d}`" class="day-col" :class="{ holiday: isHoliday(d) }">{{ fmt(b.adjust?.[d] || 0) }}</td>
                </tr>
                <tr>
                  <th class="label-col">進度</th>
                  <td v-for="d in columns" :key="`${b.key}-p-${d}`" class="day-col" :class="{ holiday: isHoliday(d) }">{{ fmt(b.progress?.[d] || 0) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <div class="pager" v-if="totalPages > 1">
        <button type="button" @click="changePage(currentPage - 1)" :disabled="currentPage === 1">前へ</button>
        <span>{{ currentPage }} / {{ totalPages }}</span>
        <button type="button" @click="changePage(currentPage + 1)" :disabled="currentPage >= totalPages">次へ</button>
      </div>
      <div class="pager-info">{{ pageStart }}-{{ pageEnd }} / {{ blocks.length }}件</div>
    </div>
    <div
      v-if="blocks.length"
      ref="topScrollRef"
      class="floating-x-scroll"
      @scroll="syncFromTop"
    >
      <div class="floating-x-scroll-inner" :style="{ width: `${scrollContentWidth}px` }"></div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onBeforeUnmount, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import api from "@/api/client";
import { addDays, formatISODate, parseISODate } from "@/utils/dateUtil";

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const error = ref("");
const blocks = ref([]);
const currentPage = ref(1);
const pageSize = 5;
const holidays = ref(new Set());
const daisoCalendarId = ref(null);
const topScrollRef = ref(null);
const mainScrollRef = ref(null);
const scrollContentWidth = ref(0);
let syncingScroll = false;

const productCode = computed(() => String(route.query.product_code || "").trim());
const customerCode = computed(() => String(route.query.customer_code || "").trim());
const shipToCode = computed(() => String(route.query.ship_to_code || "").trim());
const startDate = computed(() => String(route.query.start_date || formatISODate(new Date())));
const horizon = computed(() => {
  const n = Number(route.query.horizon || 30);
  return Number.isFinite(n) && n > 0 ? n : 30;
});

const columns = computed(() => {
  const start = parseISODate(startDate.value);
  if (!start || Number.isNaN(start.getTime())) return [];
  const arr = [];
  for (let i = 0; i < horizon.value; i += 1) arr.push(formatISODate(addDays(start, i)));
  return arr;
});

const isWeekend = (dateStr) => {
  const d = parseISODate(dateStr);
  if (!d || Number.isNaN(d.getTime())) return false;
  const day = d.getDay();
  return day === 0 || day === 6;
};

const isHoliday = (dateStr) => holidays.value.has(dateStr) || isWeekend(dateStr);

const buildWeekendFallback = () => new Set(columns.value.filter((d) => isWeekend(d)));

const resolveDaisoCalendarId = async () => {
  if (daisoCalendarId.value) return daisoCalendarId.value;
  const res = await api.calendars.getCalendars({ search: "daiso", page_size: 200 });
  const rows = normalizeList(res.data || []);
  const found = rows.find((row) => String(row.calendar_code || "").toLowerCase() === "daiso");
  if (found?.id) {
    daisoCalendarId.value = found.id;
    return found.id;
  }
  return null;
};

const loadHolidayColumns = async () => {
  const fallback = buildWeekendFallback();
  try {
    const calendarId = await resolveDaisoCalendarId();
    if (!calendarId) {
      holidays.value = fallback;
      return;
    }
    const res = await api.calendars.getCalendarDays(calendarId, { page_size: 5000 });
    const rows = normalizeList(res.data || []);
    const displayedDateSet = new Set(columns.value);
    const holidaySet = new Set();
    for (const day of rows) {
      const dateStr = day.target_date ? day.target_date.slice(0, 10) : "";
      if (!displayedDateSet.has(dateStr)) continue;
      if (day.is_working_day === false) holidaySet.add(dateStr);
    }
    holidays.value = new Set([...fallback, ...holidaySet]);
  } catch (e) {
    console.error("休日判定の取得に失敗:", e);
    holidays.value = fallback;
  }
};

const formatDateHeader = (dateStr) => {
  const d = parseISODate(dateStr);
  if (!d || Number.isNaN(d.getTime())) return dateStr;
  return `${d.getMonth() + 1}/${d.getDate()}`;
};

const fmt = (n) => {
  const num = Number(n || 0);
  if (!Number.isFinite(num) || num === 0) return "";
  return num.toLocaleString();
};

const totalPages = computed(() => Math.max(1, Math.ceil(blocks.value.length / pageSize)));
const pagedBlocks = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  return blocks.value.slice(start, start + pageSize);
});
const pageStart = computed(() => (blocks.value.length ? (currentPage.value - 1) * pageSize + 1 : 0));
const pageEnd = computed(() => Math.min(currentPage.value * pageSize, blocks.value.length));
const changePage = (p) => {
  if (p < 1 || p > totalPages.value) return;
  currentPage.value = p;
  nextTick(updateScrollWidth);
};

const updateScrollWidth = () => {
  const el = mainScrollRef.value;
  scrollContentWidth.value = el ? el.scrollWidth : 0;
};

const syncFromTop = () => {
  if (syncingScroll) return;
  const top = topScrollRef.value;
  const main = mainScrollRef.value;
  if (!top || !main) return;
  syncingScroll = true;
  main.scrollLeft = top.scrollLeft;
  syncingScroll = false;
};

const syncFromMain = () => {
  if (syncingScroll) return;
  const top = topScrollRef.value;
  const main = mainScrollRef.value;
  if (!top || !main) return;
  syncingScroll = true;
  top.scrollLeft = main.scrollLeft;
  syncingScroll = false;
};

const normalizeList = (payload) => (Array.isArray(payload) ? payload : payload?.results || []);
const toDate = (value) => String(value || "").slice(0, 10);
const ORDER_LINES_PAGE_SIZE = 20000;

const flattenTree = (node, level = 0, acc = []) => {
  if (!node || !node.product_id) return acc;
  acc.push({
    key: `${node.product_id}-${level}-${acc.length}`,
    level,
    product_id: Number(node.product_id),
    product_code: node.product_code || String(node.product_id),
    product_name: node.product_name || "",
  });
  const children = Array.isArray(node.children) ? node.children : [];
  children.forEach((child) => flattenTree(child, level + 1, acc));
  return acc;
};

const dedupeNodesByProduct = (nodes) => {
  const byProduct = new Map();
  nodes.forEach((node) => {
    const pid = Number(node.product_id || 0);
    if (!pid) return;
    const existing = byProduct.get(pid);
    if (!existing || node.level < existing.level) {
      byProduct.set(pid, { ...node, key: `p-${pid}` });
    }
  });
  return Array.from(byProduct.values()).sort((a, b) => {
    if (a.level !== b.level) return a.level - b.level;
    return String(a.product_code || "").localeCompare(String(b.product_code || ""));
  });
};

const buildByProductDateMap = (rows, mapper) => {
  const map = new Map();
  rows.forEach((row) => {
    const pid = Number(row.product || 0);
    const date = toDate(row.plan_date);
    if (!pid || !date) return;
    if (!map.has(pid)) map.set(pid, {});
    const cell = map.get(pid);
    if (!cell[date]) cell[date] = mapper.init();
    mapper.add(cell[date], row);
  });
  return map;
};

const buildProcessByProductMap = (rows) => {
  const map = new Map();
  rows.forEach((row) => {
    const pid = Number(row.product || 0);
    if (!pid) return;
    if (!map.has(pid)) map.set(pid, new Set());
    const code = String(row.process_code || "").trim();
    const name = String(row.process_name || "").trim();
    const label = [code, name].filter(Boolean).join(" ");
    if (label) map.get(pid).add(label);
  });
  return map;
};

const buildLineByProductMap = (rows) => {
  const map = new Map();
  rows.forEach((row) => {
    const pid = Number(row.product || 0);
    if (!pid) return;
    if (!map.has(pid)) map.set(pid, new Set());
    const lineName = String(row.line_name || "").trim();
    if (lineName) map.get(pid).add(lineName);
  });
  return map;
};

const buildSeriesByDate = (perBacklog, perDemand, cols) => {
  const forecast = {};
  const firm = {};
  const planned = {};
  const progress = {};
  cols.forEach((d) => {
    forecast[d] = Number(perDemand[d]?.forecast || 0);
    firm[d] = Number(perDemand[d]?.firm || 0);
    planned[d] = Number(perBacklog[d]?.pp || 0);
    progress[d] = Number(perBacklog[d]?.p || 0);
  });
  return { forecast, firm, planned_progress: planned, progress };
};

const buildShippingSummarySeriesByOrderLines = (rows, cols) => {
  const byDate = new Map();
  rows.forEach((row) => {
    const d = toDate(row.due_date);
    if (!d) return;
    if (!byDate.has(d)) byDate.set(d, { forecast: 0, firm: 0 });
    const cell = byDate.get(d);
    const qty = Number(row.quantity || 0);
    const orderType = String(row.effective_order_type || row.order_type || "").toUpperCase();
    if (orderType === "FORECAST") {
      cell.forecast += qty;
    } else {
      cell.firm += qty;
    }
  });

  const forecast = {};
  const firm = {};
  const planned = {};
  const progress = {};
  cols.forEach((d) => {
    const cell = byDate.get(d) || {};
    forecast[d] = Number(cell.forecast || 0);
    firm[d] = Number(cell.firm || 0);
    planned[d] = 0;
    progress[d] = 0;
  });
  return { forecast, firm, planned_progress: planned, progress };
};

const buildDisplayText = (rows, key, nameKey = "") => {
  const values = Array.from(new Set(rows.map((row) => String(row?.[key] || "").trim()).filter(Boolean)));
  if (!values.length) return "-";
  if (values.length === 1 && nameKey) {
    const name = String(rows.find((row) => String(row?.[key] || "").trim() === values[0])?.[nameKey] || "").trim();
    return name ? `${values[0]} ${name}`.trim() : values[0];
  }
  return values.length === 1 ? values[0] : "混在";
};

const fetchRootOrderLines = async () => {
  const rows = [];
  let page = 1;
  const endDate = columns.value[columns.value.length - 1];
  while (true) {
    const res = await api.orders.listOrderLines({
      page_size: ORDER_LINES_PAGE_SIZE,
      page,
      product_code: productCode.value,
      customer_code: customerCode.value || undefined,
      ship_to_code: shipToCode.value || undefined,
      due_date__gte: columns.value[0],
      due_date__lte: endDate,
    });
    const payload = res.data || {};
    const pageRows = normalizeList(payload);
    if (!pageRows.length) break;
    rows.push(...pageRows);
    if (!payload.next) break;
    page += 1;
  }
  return rows;
};

const buildShipmentActualByDate = (rows, cols) => {
  const byDate = new Map();
  rows.forEach((row) => {
    const d = toDate(row.shipment_date);
    if (!d) return;
    byDate.set(d, Number(byDate.get(d) || 0) + Number(row.quantity || 0));
  });
  return Object.fromEntries(cols.map((d) => [d, Number(byDate.get(d) || 0)]));
};

const load = async () => {
  if (!productCode.value) {
    error.value = "完成品が指定されていません。";
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    if (!columns.value.length) {
      blocks.value = [];
      return;
    }
    await loadHolidayColumns();
    const productRes = await api.products.getProductsByCodesIn([productCode.value]);
    const products = normalizeList(productRes.data || []);
    const root = products.find((p) => String(p.product_code || "").trim() === productCode.value) || products[0];
    if (!root?.id) throw new Error("完成品が見つかりません。");

    const bomTreeRes = await api.bomService.getBomTree(root.id);
    const tree = bomTreeRes.data || {};
    const rawNodes = flattenTree(tree, 0, []);
    const nodes = dedupeNodesByProduct(rawNodes);
    const productIds = Array.from(new Set(nodes.map((n) => n.product_id)));

    const [backlogsRes, demandsRes, rootOrderLines, shipmentActualsRes] = await Promise.all([
      api.lineBacklogs.getLineBacklogs({
        product__in: productIds.join(","),
        plan_date__gte: columns.value[0],
        plan_date__lte: columns.value[columns.value.length - 1],
        include_order_split: true,
        page_size: 50000,
      }),
      api.lineDemands.list({
        product__in: productIds.join(","),
        plan_date__gte: columns.value[0],
        plan_date__lte: columns.value[columns.value.length - 1],
      }),
      fetchRootOrderLines(),
      api.shipmentActuals.getShipmentActuals({
        shipment_date__gte: columns.value[0],
        shipment_date__lte: columns.value[columns.value.length - 1],
        product_code: productCode.value,
        customer_code: customerCode.value || undefined,
        ship_to_code: shipToCode.value || undefined,
        page_size: 10000,
      }),
    ]);

    const backlogs = normalizeList(backlogsRes.data || []);
    const demands = normalizeList(demandsRes.data || []);
    const shipmentActuals = normalizeList(shipmentActualsRes.data || []);

    const backlogMap = buildByProductDateMap(backlogs, {
      init: () => ({ pp: 0, p: 0 }),
      add: (cell, row) => {
        cell.pp += Number(row.planned_progress_qty || 0);
        cell.p += Number(row.progress_qty || 0);
      },
    });
    const demandMap = buildByProductDateMap(demands, {
      init: () => ({ forecast: 0, firm: 0 }),
      add: (cell, row) => {
        cell.forecast += Number(row.forecast_qty || 0);
        cell.firm += Number(row.firm_qty || 0);
      },
    });
    const processMap = buildProcessByProductMap(backlogs);
    const lineMap = buildLineByProductMap(backlogs);

    const mappedBlocks = nodes.map((n) => {
      const perBacklog = backlogMap.get(n.product_id) || {};
      const perDemand = demandMap.get(n.product_id) || {};
      const processSet = processMap.get(n.product_id) || new Set();
      const lineSet = lineMap.get(n.product_id) || new Set();
      return {
        ...n,
        ...buildSeriesByDate(perBacklog, perDemand, columns.value),
        process_display: Array.from(processSet).join(", "),
        line_display: Array.from(lineSet).join(", "),
      };
    });

    // 先頭(Lv0)に「出荷進度照会」ブロックを挿入
    const rootNode = nodes.find((n) => n.level === 0);
    if (rootNode) {
      const rootBacklog = backlogMap.get(rootNode.product_id) || {};
      const shippingSummaryBlock = {
        ...rootNode,
        key: `shipping-summary-${rootNode.product_id}`,
        ...buildShippingSummarySeriesByOrderLines(rootOrderLines, columns.value),
        planned_progress: buildShipmentActualByDate(shipmentActuals, columns.value),
        progress: Object.fromEntries(columns.value.map((d) => [d, Number(rootBacklog[d]?.p || 0)])),
        is_shipping_summary: true,
        customer_display: buildDisplayText(rootOrderLines, "customer_code", "customer_name"),
        ship_to_display: buildDisplayText(rootOrderLines, "ship_to_code"),
        line_display: "-",
        process_display: "出荷進度照会",
      };
      blocks.value = [shippingSummaryBlock, ...mappedBlocks];
    } else {
      blocks.value = mappedBlocks;
    }
    currentPage.value = 1;
    await nextTick();
    updateScrollWidth();
  } catch (e) {
    console.error("受注展開読込エラー:", e);
    error.value = e?.message || "読込に失敗しました。";
    blocks.value = [];
  } finally {
    loading.value = false;
  }
};

const goBack = () => router.back();

onMounted(() => {
  window.addEventListener("resize", updateScrollWidth);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", updateScrollWidth);
});

load();
</script>

<style scoped>
.page-container { padding: 16px; padding-bottom: 36px; display: flex; flex-direction: column; gap: 12px; }
.page-header { display: flex; justify-content: space-between; gap: 8px; align-items: flex-start; }
.page-title { margin: 0; font-size: 20px; }
.subtitle { margin: 0; color: #64748b; font-size: 13px; }
.status { padding: 20px; text-align: center; color: #475569; }
.status.error { color: #b91c1c; }
.block-list-wrap { display: flex; flex-direction: column; gap: 8px; }
.block-list { display: flex; flex-direction: column; gap: 12px; overflow-x: auto; }
.block-card { border: 1px solid #dbe4f0; border-radius: 8px; overflow: hidden; background: #fff; min-width: max-content; }
.block-body { display: flex; align-items: stretch; }
.meta-panel { width: 260px; min-width: 260px; border-right: 1px solid #e5e7eb; background: #f8fafc; }
.meta-row { display: flex; gap: 8px; padding: 8px 10px; border-bottom: 1px solid #e5e7eb; font-size: 12px; }
.meta-label { width: 40px; color: #475569; font-weight: 700; }
.meta-value { flex: 1; color: #0f172a; font-weight: 600; }
.matrix-table { border-collapse: collapse; width: auto; table-layout: fixed; }
.matrix-table th, .matrix-table td { border: 1px solid #e5e7eb; padding: 4px 2px; text-align: right; font-size: 11px; }
.matrix-table thead th { background: #f8fafc; text-align: center; }
.matrix-table .holiday { background: #f7e8ee; }
.label-col {
  text-align: left !important;
  width: 45px;
  min-width: 45px;
  max-width: 45px;
  white-space: nowrap;
  background: #f8fafc;
}
.day-col { width: 40px; min-width: 40px; max-width: 40px; }
.pager { display: flex; gap: 12px; align-items: center; justify-content: center; }
.pager-info { text-align: center; color: #475569; font-size: 12px; }
.floating-x-scroll {
  position: fixed;
  left: 16px;
  right: 16px;
  bottom: 0;
  z-index: 999;
  overflow-x: auto;
  overflow-y: hidden;
  border: 1px solid #d1d5db;
  background: #f8fafc;
  height: 16px;
}
.floating-x-scroll-inner { height: 1px; }
</style>

