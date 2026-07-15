<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">出荷進度照会 <DataSourceDialog title="出荷進度照会" :sources="dsSources" /></h2>
        <p class="subtitle">受注明細を基準に、日付別の内示・確定・実績・調整・進度を一覧化します。</p>
      </div>
      <div class="page-actions">
        <input
          type="text"
          v-model="productFilter"
          placeholder="品番/品名で絞り込み"
        />
        <input
          type="text"
          v-model="customerFilter"
          placeholder="得意先で絞り込み"
        />
        <input
          type="text"
          v-model="shipToFilter"
          placeholder="納入先で絞り込み"
        />
        <button type="button" @click="toggleShipToMode">
          納入先: {{ splitByShipTo ? "分行" : "集約" }}
        </button>
        <input type="date" v-model="startDate" />
        <select v-model.number="horizon">
          <option :value="30">30日</option>
          <option :value="60">60日</option>
          <option :value="90">90日</option>
        </select>
        <select v-model="selectedFavoriteId" @change="applyFavorite">
          <option value="">お気に入り選択</option>
          <option v-for="fav in favorites" :key="fav.id" :value="String(fav.id)">
            {{ fav.name }}
          </option>
        </select>
        <input
          type="text"
          v-model.trim="favoriteName"
          placeholder="お気に入り名"
          style="min-width: 140px;"
        />
        <button type="button" class="favorite-star-btn" title="お気に入り登録" @click="saveFavorite" :disabled="loading">★</button>
        <button @click="load" :disabled="loading">更新</button>
        <button @click="recalculate" :disabled="loading || recalculating" class="recalc-btn">{{ recalculating ? '再計算中...' : '進度再計算' }}</button>
      </div>
    </div>

    <div class="page-body">
      <div class="list-area">
        <div v-if="loading" class="loading">読込中...</div>
        <div v-else-if="error" class="no-data">エラー: {{ error }}</div>
        <div v-else-if="!searched"></div>
        <div v-else>
          <div v-if="progressWarning" class="progress-warning">{{ progressWarning }}</div>
          <div v-if="groups.length" class="group-list">
            <div v-for="g in pagedGroups" :key="g.key" class="group-card">
              <div class="info-block">
                <div class="info-row product-code-row">
                  <span class="info-label">品番</span>
                  <span class="info-value">{{ g.product_code || "-" }}</span>
                  <button type="button" class="routing-expand-btn" @click="openOrderExpansionPage(g)">routing展開</button>
                </div>
                <div class="info-row">
                  <span class="info-label">品名</span>
                  <span class="info-value">{{ g.product_name || "-" }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">得意先</span>
                  <span class="info-value">{{ formatCustomer(g) }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">納入先</span>
                  <span class="info-value">{{ g.ship_to_display || "-" }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">合計内示</span>
                  <span class="info-value">{{ g.summary.forecast }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">合計確定</span>
                  <span class="info-value">{{ g.summary.firm }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">合計実績</span>
                  <span class="info-value">{{ g.summary.actual }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">合計調整</span>
                  <span class="info-value" :class="{ negative: g.summary.adjust < 0 }">
                    {{ g.summary.adjust }}
                  </span>
                </div>
                <div class="info-row">
                  <span class="info-label">進度</span>
                  <span class="info-value">{{ g.summary.progressRate }}</span>
                </div>
              </div>

              <div class="matrix-block">
                <table class="matrix-table" :style="{ minWidth: matrixMinWidth + 'px' }">
                  <thead>
                    <tr>
                      <th class="label-col">項目</th>
                      <th
                        v-for="d in columns"
                        :key="d"
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
                      <td
                        v-for="d in columns"
                        :key="`forecast-${d}`"
                        class="cell"
                        :class="{ holiday: isHoliday(d) }"
                      >
                        {{ formatValue(getValue(g, d, "forecast")) }}
                      </td>
                    </tr>
                    <tr>
                      <th class="label-col">確定</th>
                      <td
                        v-for="d in columns"
                        :key="`firm-${d}`"
                        class="cell"
                        :class="{ holiday: isHoliday(d) }"
                      >
                        {{ formatValue(getValue(g, d, "firm")) }}
                      </td>
                    </tr>
                    <tr>
                      <th class="label-col">実績</th>
                      <td
                        v-for="d in columns"
                        :key="`actual-${d}`"
                        class="cell"
                        :class="{ holiday: isHoliday(d) }"
                      >
                        {{ formatValue(getValue(g, d, "actual")) }}
                      </td>
                    </tr>
                    <tr>
                      <th class="label-col">調整</th>
                      <td
                        v-for="d in columns"
                        :key="`adjust-${d}`"
                        class="cell"
                        :class="{ negative: getValue(g, d, 'adjust') < 0, holiday: isHoliday(d) }"
                      >
                        {{ formatValue(getValue(g, d, "adjust")) }}
                      </td>
                    </tr>
                    <tr>
                      <th class="label-col">進度</th>
                      <td
                        v-for="d in columns"
                        :key="`progress-${d}`"
                        class="cell"
                        :class="{ holiday: isHoliday(d) }"
                      >
                        {{ getProgressRate(g, d) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <div v-else class="no-data">データがありません</div>
          <div v-if="groups.length" class="pagination-area">
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
              <label class="page-size">
                表示件数
                <select v-model.number="pageSize" class="page-size-select">
                  <option :value="10">10</option>
                  <option :value="20">20</option>
                  <option :value="50">50</option>
                  <option :value="100">100</option>
                </select>
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import api from "@/api/client";
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'
import {
  compareBySpecialOrderThenProductCode,
  resolveSpecialDisplayOrder,
} from "@/utils/groupSort";
import { addDays, formatISODate, parseISODate } from "@/utils/dateUtil";

const dsSources = [
  { op: '読み取り', table: 't_shipping_progress', desc: '出荷進度（再計算済み）' },
  { op: '読み取り', table: 'order / order_line', desc: '受注データ' },
  { op: '読み取り', table: 't_shipment_actual', desc: '出荷実績' },
  { op: '読み取り', table: 't_ship_to_lead_time', desc: '納入先リードタイム' },
  { op: '読み取り', table: 'm_product', desc: '製品マスタ' },
]

const productFilter = ref("");
const customerFilter = ref("");
const shipToFilter = ref("");
const defaultStart = new Date();
defaultStart.setDate(defaultStart.getDate() - 1);
const startDate = ref(formatISODate(defaultStart));
const horizon = ref(30);
const loading = ref(false);
const error = ref("");
const searched = ref(false);
const orderLines = ref([]);
const shipmentActuals = ref([]);
const shipToLeadTimeMap = ref(new Map());
const savedProgressMap = ref(new Map());
const progressWarning = ref("");
const holidays = ref(new Set());
const daisoCalendarId = ref(null);
const currentPage = ref(1);
const pageSize = ref(20);
const recalculating = ref(false);
const splitByShipTo = ref(true);
const router = useRouter();
const routingExpandStates = ref({});
const productCacheByCode = new Map();
const favorites = ref([]);
const selectedFavoriteId = ref("");
const favoriteName = ref("");

const normalizeList = (payload) => {
  return Array.isArray(payload) ? payload : payload?.results || [];
};

const normalizeQty = (value) => {
  const num = Number(value || 0);
  return Number.isFinite(num) ? num : 0;
};

const addQtyToMap = (target, date, qty) => {
  if (!date) return;
  const current = normalizeQty(target[date]);
  target[date] = current + normalizeQty(qty);
};

const toIsoDate = (value) => {
  if (!value) return "";
  if (typeof value === "string") return value.slice(0, 10);
  const d = value instanceof Date ? value : new Date(value);
  return Number.isNaN(d.getTime()) ? "" : formatISODate(d);
};

const shiftBusinessDays = (dateStr, days) => {
  const base = parseISODate(dateStr);
  if (!base || Number.isNaN(base.getTime())) return dateStr;
  if (!Number.isFinite(days) || days === 0) return formatISODate(base);
  const step = days > 0 ? 1 : -1;
  let remain = Math.abs(days);
  let cur = new Date(base);
  while (remain > 0) {
    cur = addDays(cur, step);
    const iso = formatISODate(cur);
    if (!isHoliday(iso)) remain -= 1;
  }
  return formatISODate(cur);
};

const getRoutingExpandStateByKey = (groupKey) => {
  if (!routingExpandStates.value[groupKey]) {
    routingExpandStates.value[groupKey] = {
      open: false,
      loading: false,
      loaded: false,
      error: "",
      nodes: [],
    };
  }
  return routingExpandStates.value[groupKey];
};

const getRoutingExpandState = (group) => getRoutingExpandStateByKey(group.key);
const isRoutingExpandLoading = (group) => getRoutingExpandState(group).loading;
const isRoutingExpanded = (group) => getRoutingExpandState(group).open;

const getRoutingExpandButtonLabel = (group) => {
  const state = getRoutingExpandState(group);
  if (state.loading) return "展開中...";
  return state.open ? "routing閉じる" : "routing展開";
};

const ORDER_LINES_PAGE_SIZE = 20000;

const fetchAllOpenOrderLines = async () => {
  const rows = [];
  let page = 1;
  const filterParams = {};
  if (productFilter.value) filterParams.product_code = productFilter.value;
  if (customerFilter.value) filterParams.customer_code = customerFilter.value;
  if (shipToFilter.value) filterParams.ship_to_code = shipToFilter.value;

  while (true) {
    const res = await api.orders.listOrderLines({
      page_size: ORDER_LINES_PAGE_SIZE,
      page,
      ...filterParams,
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

function formatDateHeader(dateStr) {
  const d = parseISODate(dateStr);
  if (!d || Number.isNaN(d.getTime())) return dateStr;
  const m = d.getMonth() + 1;
  const day = d.getDate();
  return `${m}/${day}`;
}

function isWeekend(dateStr) {
  const d = parseISODate(dateStr);
  if (!d || Number.isNaN(d.getTime())) return false;
  const day = d.getDay();
  return day === 0 || day === 6;
}

const columns = computed(() => {
  const start = parseISODate(startDate.value);
  if (!start || Number.isNaN(start.getTime())) return [];
  const cols = [];
  for (let i = 0; i < horizon.value; i++) {
    cols.push(formatISODate(addDays(start, i)));
  }
  return cols;
});

const matrixMinWidth = computed(() => 80 + columns.value.length * 60);

const endDate = computed(() => {
  if (!columns.value.length) return startDate.value;
  return columns.value[columns.value.length - 1];
});

const isHoliday = (dateStr) => holidays.value.has(dateStr) || isWeekend(dateStr);

const buildGroupKey = (productCode, customerCode, shipToCode) => {
  if (splitByShipTo.value) {
    return `${productCode}__${customerCode}__${shipToCode}`;
  }
  return `${productCode}__${customerCode}`;
};

const buildWeekendFallback = () => {
  return new Set(columns.value.filter((d) => isWeekend(d)));
};

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
      if (day.is_working_day === false) {
        holidaySet.add(dateStr);
      }
    }

    if (!holidaySet.size) {
      holidays.value = fallback;
      return;
    }
    holidays.value = new Set([...fallback, ...holidaySet]);
  } catch (e) {
    console.error("休日判定の取得に失敗:", e);
    holidays.value = fallback;
  }
};

const groups = computed(() => {
  if (!orderLines.value.length) {
    console.log("[ShippingProgress] 受注明細データなし");
    return [];
  }

  console.log("[ShippingProgress] グループ化開始");
  console.log("[ShippingProgress] 期間範囲:", columns.value[0], "～", columns.value[columns.value.length - 1]);

  // 確定優先: 同一品番・得意先・納入先・納期でFIRMがある内示を除外
  const firmSourceKeys = new Set();
  for (const order of orderLines.value) {
    const ot = String(order.effective_order_type || order.order_type || "").toUpperCase();
    if (ot === 'FIRM' && order.due_date && order.product_code) {
      const sk = `${order.product_code}__${order.customer_code || ''}__${(order.ship_to_code || '').trim()}__${order.due_date.slice(0, 10)}`;
      firmSourceKeys.add(sk);
    }
  }

  // 製品コード別にグループ化
  const map = new Map();
  let processedCount = 0;
  let skippedCount = 0;

  for (const order of orderLines.value) {
    if (!order.due_date || !order.product_code) {
      skippedCount++;
      continue;
    }

    // due_dateはAPIから文字列で返されるので、new Date()を通さない
    let dueDate = order.due_date ? order.due_date.slice(0, 10) : "";
    const ltKey = `${order.customer_code || ""}__${(order.ship_to_code || "").trim()}`;
    const addDaysVal = shipToLeadTimeMap.value.get(ltKey);
    if (addDaysVal > 0) {
      dueDate = shiftBusinessDays(dueDate, -addDaysVal);
    }
    const productCode = order.product_code;
    const customerCode = order.customer_code || "";
    const customerName = order.customer_name || "";
    const shipToCode = (order.ship_to_code || "").trim();

    // 製品フィルタ
    if (productFilter.value) {
      const filter = productFilter.value.toLowerCase();
      const text = `${order.product_code || ""}${order.product_name || ""}`.toLowerCase();
      if (!text.includes(filter)) {
        skippedCount++;
        continue;
      }
    }

    if (customerFilter.value) {
      const filter = customerFilter.value.toLowerCase();
      // コードは末尾一致（"1"→000001, "196"→000196）、名称は部分一致
      const codeMatch = customerCode.toLowerCase().endsWith(filter);
      const nameMatch = customerName.toLowerCase().includes(filter);
      if (!codeMatch && !nameMatch) {
        skippedCount++;
        continue;
      }
    }

    if (shipToFilter.value) {
      const filter = shipToFilter.value.toLowerCase();
      if (!shipToCode.toLowerCase().includes(filter)) {
        skippedCount++;
        continue;
      }
    }

    processedCount++;

    // グループ作成
    const groupKey = buildGroupKey(productCode, customerCode, shipToCode);
    const specialDisplayOrder = resolveSpecialDisplayOrder(order);
    if (!map.has(groupKey)) {
      map.set(groupKey, {
        key: groupKey,
        product_id: order.product || order.product_id || null,
        product_code: order.product_code,
        product_name: order.product_name,
        customer_code: customerCode,
        customer_name: customerName,
        ship_to_code: splitByShipTo.value ? shipToCode : "",
        ship_to_codes: new Set(),
        ship_to_display: "-",
        special_display_order: specialDisplayOrder,
        cells: {},
        summary: { forecast: 0, firm: 0, actual: 0, adjust: 0, progressRate: "-" },
      });
    }

    const group = map.get(groupKey);
    group.ship_to_codes.add(shipToCode);
    if (specialDisplayOrder !== null) {
      const currentOrder = resolveSpecialDisplayOrder(group);
      if (currentOrder === null || specialDisplayOrder < currentOrder) {
        group.special_display_order = specialDisplayOrder;
      }
    }

    // セル初期化
    if (!group.cells[dueDate]) {
      group.cells[dueDate] = {
        forecast: 0,
        firm: 0,
        actual: 0,
        adjust: 0,
      };
    }

    const cell = group.cells[dueDate];
    const qty = Number(order.quantity || 0);

    // 受注タイプ別に集計（確定優先: 同一source_keyのFIRMがあれば内示スキップ）
    const orderType = String(order.effective_order_type || order.order_type || "").toUpperCase();
    if (orderType === "FORECAST") {
      const sk = `${order.product_code}__${customerCode}__${shipToCode}__${order.due_date.slice(0, 10)}`;
      if (!firmSourceKeys.has(sk)) {
        cell.forecast += qty;
      }
    } else {
      cell.firm += qty;
    }
  }

  // shipmentActualsから実績を集計
  const actualMap = new Map();
  for (const actual of shipmentActuals.value) {
    if (!actual.shipment_date || !actual.product_code) continue;
    const aDate = actual.shipment_date ? actual.shipment_date.slice(0, 10) : "";
    const aProduct = actual.product_code;
    const aCustomer = actual.customer_code || "";
    const aShipTo = (actual.ship_to_code || "").trim();
    const aKey = buildGroupKey(aProduct, aCustomer, aShipTo);
    const perDate = actualMap.get(aKey) || new Map();
    const current = perDate.get(aDate) || 0;
    perDate.set(aDate, current + Number(actual.quantity || 0));
    actualMap.set(aKey, perDate);
  }

  for (const [key, group] of map.entries()) {
    const perDate = actualMap.get(key);
    if (!perDate) continue;
    for (const [date, qty] of perDate.entries()) {
      if (!group.cells[date]) {
        group.cells[date] = { forecast: 0, firm: 0, actual: 0, adjust: 0 };
      }
      group.cells[date].actual += qty;
    }
  }

  console.log("[ShippingProgress] 処理件数:", processedCount, "スキップ:", skippedCount);
  console.log("[ShippingProgress] グループ数:", map.size);

  // サマリー計算（表示期間内の日付のみ集計）
  const displayedDateSet = new Set(columns.value);

  const result = Array.from(map.values()).map((g) => {
    let totalForecast = 0;
    let totalFirm = 0;
    let totalActual = 0;
    let totalAdjust = 0;

    // 各日付のデータに実績・調整を追加
    for (const [date, cell] of Object.entries(g.cells)) {
      if (!displayedDateSet.has(date)) continue;
      totalForecast += cell.forecast;
      totalFirm += cell.firm;
      totalActual += cell.actual;
      totalAdjust += cell.adjust;
    }

    // サマリーの累積進度: 最終日の進度をgetProgressRateから取得
    const lastDate = columns.value[columns.value.length - 1];
    const lastProgressStr = lastDate ? getProgressRate(g, lastDate) : "0";

    g.summary = {
      forecast: totalForecast,
      firm: totalFirm,
      actual: totalActual,
      adjust: totalAdjust,
      progressRate: lastProgressStr,
    };
    const shipToList = Array.from(g.ship_to_codes || new Set()).filter((v) => v);
    if (splitByShipTo.value) {
      g.ship_to_display = g.ship_to_code || "-";
    } else if (shipToList.length <= 1) {
      g.ship_to_display = shipToList[0] || "-";
    } else {
      g.ship_to_display = "混在";
    }

    return g;
  }).filter((g) => {
    // 表示期間内にデータがないグループは非表示
    const s = g.summary;
    return s.forecast !== 0 || s.firm !== 0 || s.actual !== 0 || s.adjust !== 0;
  });

  result.sort((a, b) =>
    compareBySpecialOrderThenProductCode(a, b, {
      codeGetter: (item) => item.product_code || "",
    })
  );

  console.log("[ShippingProgress] 返却グループ数:", result.length);

  return result;
});

const totalPages = computed(() => {
  if (groups.value.length === 0) return 1;
  return Math.ceil(groups.value.length / pageSize.value);
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
  const total = groups.value.length;
  if (total === 0) return "0件";
  const start = (currentPage.value - 1) * pageSize.value + 1;
  const end = Math.min(currentPage.value * pageSize.value, total);
  return `${total}件中 ${start}-${end}件`;
});

const pagedGroups = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return groups.value.slice(start, start + pageSize.value);
});

const getValue = (group, date, key) => {
  return group.cells?.[date]?.[key] ?? 0;
};

const formatValue = (val) => {
  if (val === 0) return "";
  return val.toLocaleString();
};

const formatCustomer = (group) => {
  if (group.customer_name) {
    return `${group.customer_code || ""} ${group.customer_name}`.trim();
  }
  return group.customer_code || "-";
};

const toggleShipToMode = () => {
  splitByShipTo.value = !splitByShipTo.value;
  currentPage.value = 1;
};

const getProgressRate = (group, date) => {
  const savedKey = `${group.product_code}__${group.customer_code || ''}__${splitByShipTo.value ? (group.ship_to_code || '') : ''}__${date}`;
  const savedVal = savedProgressMap.value.get(savedKey);
  if (savedVal !== undefined) {
    return savedVal.toLocaleString();
  }
  return "-";
};

const openOrderExpansionPage = (group) => {
  const resolved = router.resolve({
    name: "ShippingOrderExpansion",
    query: {
      product_code: group.product_code || "",
      customer_code: group.customer_code || "",
      ship_to_code: group.ship_to_code || "",
      start_date: startDate.value || "",
      horizon: String(horizon.value || 30),
    },
  });
  window.open(resolved.href, "_blank", "noopener");
};

const getProductByCode = async (productCode) => {
  const code = String(productCode || "").trim();
  if (!code) return null;
  if (productCacheByCode.has(code)) return productCacheByCode.get(code);
  const res = await api.products.getProductsByCodesIn([code]);
  const rows = normalizeList(res.data || []);
  const found = rows.find((row) => String(row.product_code || "").trim() === code) || rows[0] || null;
  productCacheByCode.set(code, found);
  return found;
};

const getBOMChildrenByProductId = async (productId) => {
  const bomRes = await api.boms.getBOMs({ parent_product: productId, page_size: 200 });
  const allBoms = normalizeList(bomRes.data || []);
  if (!allBoms.length) return [];

  const parseTs = (row) => {
    const raw = row?.valid_from_datetime || row?.valid_from || row?.created_at || "";
    const ts = Date.parse(raw);
    return Number.isFinite(ts) ? ts : 0;
  };
  const activeBoms = allBoms.filter((b) => b.is_active);
  const candidates = activeBoms.length ? activeBoms : allBoms;
  const targetBom = [...candidates].sort((a, b) => parseTs(b) - parseTs(a))[0];
  if (!targetBom?.id) return [];

  const merged = new Map();
  const itemsRes = await api.bomItems.getBOMItems({ bom: targetBom.id, page_size: 2000 });
  const items = normalizeList(itemsRes.data || []);
  for (const item of items) {
    const childId = Number(item.child_product || 0);
    if (!childId) continue;
    const key = String(childId);
    const current = merged.get(key) || {
      child_product: childId,
      child_product_code: item.child_product_code || "",
      child_product_name: item.child_product_name || "",
      quantity: 0,
    };
    current.quantity += normalizeQty(item.quantity || 0);
    merged.set(key, current);
  }
  return Array.from(merged.values()).filter((row) => normalizeQty(row.quantity) > 0);
};

const getRoutingMaterialChildrenByProductId = async (productId) => {
  const routingsRes = await api.routings.getRoutings({ product: productId, page_size: 200 });
  const routings = normalizeList(routingsRes.data || []);
  if (!routings.length) return [];

  const merged = new Map();
  for (const routing of routings) {
    const materialsRes = await api.routings.getRoutingStepMaterials({ routing: routing.id, page_size: 5000 });
    const materials = normalizeList(materialsRes.data || []);
    for (const material of materials) {
      const childId = Number(material.component || 0);
      if (!childId) continue;
      const key = String(childId);
      const current = merged.get(key) || {
        child_product: childId,
        child_product_code: material.component_code || "",
        child_product_name: material.component_name || "",
        quantity: 0,
      };
      current.quantity += normalizeQty(material.quantity || 0);
      merged.set(key, current);
    }
  }
  return Array.from(merged.values()).filter((row) => normalizeQty(row.quantity) > 0);
};

const getChildrenByProductId = async (productId) => {
  const bomChildren = await getBOMChildrenByProductId(productId);
  if (bomChildren.length > 0) return bomChildren;
  return getRoutingMaterialChildrenByProductId(productId);
};

const buildRoutingTree = async (rootProductId) => {
  const nodesByProduct = new Map();
  const edgesByParent = new Map();
  const visited = new Set();

  const walk = async (productId) => {
    if (!productId || visited.has(productId)) return;
    visited.add(productId);
    const items = await getChildrenByProductId(productId);
    const children = [];
    for (const item of items) {
      const childId = Number(item.child_product || 0);
      if (!childId) continue;
      children.push({ childId, quantity: normalizeQty(item.quantity || 1) });
      if (!nodesByProduct.has(childId)) {
        nodesByProduct.set(childId, {
          product_id: childId,
          product_code: item.child_product_code || "",
          product_name: item.child_product_name || "",
        });
      }
      await walk(childId);
    }
    edgesByParent.set(productId, children);
  };

  await walk(rootProductId);
  return { nodesByProduct, edgesByParent };
};

const fetchBacklogsByProducts = async (productIds) => {
  if (!productIds.length) return [];
  const start = shiftBusinessDays(columns.value[0], -365);
  const end = columns.value[columns.value.length - 1];
  const res = await api.lineBacklogs.getLineBacklogs({
    product__in: productIds.join(","),
    plan_date__gte: start,
    plan_date__lte: end,
    include_order_split: true,
    page_size: 50000,
  });
  return normalizeList(res.data || []);
};

const buildBacklogMaps = (rows) => {
  const daily = new Map();
  const ltByProduct = new Map();
  for (const row of rows) {
    const pid = Number(row.product || 0);
    const date = toIsoDate(row.plan_date);
    if (!pid || !date) continue;
    if (!daily.has(pid)) daily.set(pid, {});
    const target = daily.get(pid);
    if (!target[date]) target[date] = { planned_progress: 0, progress: 0 };
    target[date].planned_progress += normalizeQty(row.planned_progress_qty);
    target[date].progress += normalizeQty(row.progress_qty);

    if (!ltByProduct.has(pid)) {
      const selfLt = row.self_lt_days !== null && row.self_lt_days !== undefined ? Number(row.self_lt_days) : null;
      const totalLt = row.total_lt_days !== null && row.total_lt_days !== undefined ? Number(row.total_lt_days) : null;
      ltByProduct.set(pid, {
        self_lt_days: Number.isFinite(selfLt) ? selfLt : null,
        total_lt_days: Number.isFinite(totalLt) ? totalLt : null,
      });
    }
  }
  return { daily, ltByProduct };
};

const buildRootRequiredMap = (group) => {
  const required = {};
  for (const date of columns.value) {
    const firm = normalizeQty(getValue(group, date, "firm"));
    const forecast = normalizeQty(getValue(group, date, "forecast"));
    const demand = firm > 0 ? firm : forecast;
    if (demand > 0) addQtyToMap(required, date, demand);
  }
  return required;
};

const buildExpandedNodes = (group, tree, backlogMaps, rootProductId) => {
  const { edgesByParent, nodesByProduct } = tree;
  const { daily, ltByProduct } = backlogMaps;
  const result = [];
  const seenPath = new Set();

  const walk = (parentProductId, parentRequired, level) => {
    const edges = edgesByParent.get(parentProductId) || [];
    for (const edge of edges) {
      const childId = edge.childId;
      const pathKey = `${parentProductId}->${childId}`;
      if (seenPath.has(pathKey)) continue;
      seenPath.add(pathKey);

      const childMeta = nodesByProduct.get(childId) || {};
      const ltMeta = ltByProduct.get(childId) || {};
      const ltDays = Number.isFinite(ltMeta.self_lt_days) ? ltMeta.self_lt_days : (Number.isFinite(ltMeta.total_lt_days) ? ltMeta.total_lt_days : 0);
      const childRequired = {};
      Object.entries(parentRequired).forEach(([parentDate, parentQty]) => {
        const shifted = shiftBusinessDays(parentDate, -Math.max(0, Number(ltDays || 0)));
        addQtyToMap(childRequired, shifted, normalizeQty(parentQty) * normalizeQty(edge.quantity || 1));
      });

      const perDay = daily.get(childId) || {};
      const plannedProgress = {};
      const progress = {};
      for (const date of columns.value) {
        plannedProgress[date] = normalizeQty(perDay?.[date]?.planned_progress);
        progress[date] = normalizeQty(perDay?.[date]?.progress);
      }

      result.push({
        key: `${group.key}-${childId}-${level}`,
        product_id: childId,
        product_code: childMeta.product_code || String(childId),
        product_name: childMeta.product_name || "",
        level,
        lt_days: ltDays,
        required: childRequired,
        planned_progress: plannedProgress,
        progress,
      });

      walk(childId, childRequired, level + 1);
    }
  };

  walk(rootProductId, buildRootRequiredMap(group), 1);
  return result;
};

const toggleRoutingExpand = async (group) => {
  const state = getRoutingExpandState(group);
  state.open = !state.open;
  if (!state.open || state.loaded || state.loading) return;
  state.loading = true;
  state.error = "";
  try {
    let rootProductId = Number(group.product_id || 0);
    if (!rootProductId) {
      const product = await getProductByCode(group.product_code);
      rootProductId = Number(product?.id || 0);
    }
    if (!rootProductId) {
      throw new Error("品番マスタに対象製品が見つかりません。");
    }

    const tree = await buildRoutingTree(rootProductId);
    const expandedProductIds = Array.from(tree.nodesByProduct.keys());
    const backlogRows = await fetchBacklogsByProducts(expandedProductIds);
    const backlogMaps = buildBacklogMaps(backlogRows);
    state.nodes = buildExpandedNodes(group, tree, backlogMaps, rootProductId);
    state.loaded = true;
  } catch (e) {
    console.error("routing展開の取得に失敗:", e);
    state.error = e?.message || "展開の取得に失敗しました。";
    state.nodes = [];
  } finally {
    state.loading = false;
  }
};

const load = async () => {
  loading.value = true;
  error.value = "";
  progressWarning.value = "";
  searched.value = true;
  routingExpandStates.value = {};
  try {
    // 納入地別出荷加算日数を取得
    try {
      const ltRes = await api.shipToLeadTimes.getAll({ is_active: true })
      const ltRows = normalizeList(ltRes.data || [])
      const m = new Map()
      for (const row of ltRows) {
        m.set(`${row.customer_code || ""}__${(row.ship_to_code || "").trim()}`, row.additional_days || 0)
      }
      shipToLeadTimeMap.value = m
    } catch (e) {
      console.error("出荷加算日数取得エラー:", e)
    }

    await loadHolidayColumns();
    orderLines.value = await fetchAllOpenOrderLines();
    const shipmentActualsRes = await api.shipmentActuals.getShipmentActuals({
      shipment_date__gte: startDate.value,
      shipment_date__lte: endDate.value,
      product_code: productFilter.value,
      customer_code: customerFilter.value,
      ship_to_code: shipToFilter.value,
      page_size: 10000,
    });
    shipmentActuals.value = normalizeList(shipmentActualsRes.data || []);

    // 保存済み進度を取得
    try {
      const progressRes = await api.shippingProgress.get({
        start_date: startDate.value,
        end_date: endDate.value,
        product_code: productFilter.value,
        customer_code: customerFilter.value,
        ship_to_code: shipToFilter.value,
      });
      const progressRows = (progressRes.data?.results) || [];
      const pMap = new Map();
      for (const row of progressRows) {
        const key = `${row.product_code}__${row.customer_code || ''}__${(row.ship_to_code || '').trim()}__${row.plan_date}`;
        pMap.set(key, row.progress_qty);
      }
      savedProgressMap.value = pMap;
      if (!pMap.size) {
        progressWarning.value = "進度データが未再計算です。『進度再計算』を実行してください。";
      }
    } catch (e) {
      console.error("保存済み進度の取得に失敗:", e);
      savedProgressMap.value = new Map();
      progressWarning.value = "進度データの取得に失敗しました。『進度再計算』後に再読込してください。";
    }

    console.log("[ShippingProgress] データロード完了");
    console.log("[ShippingProgress] 受注明細件数:", orderLines.value.length);
    console.log("[ShippingProgress] 出荷実績件数:", shipmentActuals.value.length);
    console.log("[ShippingProgress] 受注明細サンプル:", orderLines.value.slice(0, 3));
    console.log("[ShippingProgress] 開始日:", startDate.value);
    console.log("[ShippingProgress] 期間:", horizon.value);
    console.log("[ShippingProgress] カラム:", columns.value.slice(0, 5));
  } catch (e) {
    console.error("データ読み込みエラー:", e);
    error.value = e?.message || "読み込みに失敗しました";
  } finally {
    loading.value = false;
  }
};

const recalculate = async () => {
  recalculating.value = true;
  try {
    await api.shippingProgress.recalculate({
      start_date: startDate.value,
      end_date: endDate.value,
    });
    await load();
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '再計算に失敗しました';
    window.alert(`進度再計算エラー: ${msg}`);
  } finally {
    recalculating.value = false;
  }
};

const FAVORITE_SCREEN_KEY = "shipping.progress";

const toFavoritePayload = () => ({
  productFilter: productFilter.value || "",
  customerFilter: customerFilter.value || "",
  shipToFilter: shipToFilter.value || "",
  splitByShipTo: Boolean(splitByShipTo.value),
  horizon: Number(horizon.value || 30),
});

const applyFavoritePayload = (payload) => {
  productFilter.value = String(payload?.productFilter || "");
  customerFilter.value = String(payload?.customerFilter || "");
  shipToFilter.value = String(payload?.shipToFilter || "");
  splitByShipTo.value = Boolean(payload?.splitByShipTo ?? true);
  const nextHorizon = Number(payload?.horizon || 30);
  horizon.value = [30, 60, 90].includes(nextHorizon) ? nextHorizon : 30;
};

const loadFavorites = async () => {
  try {
    const res = await api.accounts.getFavorites({ screen_key: FAVORITE_SCREEN_KEY, page_size: 200 });
    favorites.value = Array.isArray(res.data) ? res.data : res.data?.results || [];
  } catch (e) {
    console.error("お気に入り取得失敗:", e);
  }
};

const applyFavorite = () => {
  const id = Number(selectedFavoriteId.value || 0);
  if (!id) return;
  const target = favorites.value.find((item) => Number(item.id) === id);
  if (!target) return;
  favoriteName.value = target.name || "";
  applyFavoritePayload(target.payload || {});
};

const saveFavorite = async () => {
  const name = String(favoriteName.value || "").trim();
  if (!name) {
    window.alert("お気に入り名を入力してください。");
    return;
  }
  const payload = {
    screen_key: FAVORITE_SCREEN_KEY,
    name,
    payload: toFavoritePayload(),
  };

  try {
    const id = Number(selectedFavoriteId.value || 0);
    if (id) {
      await api.accounts.updateFavorite(id, payload);
    } else {
      await api.accounts.createFavorite(payload);
    }
    await loadFavorites();
    const found = favorites.value.find((item) => item.name === name);
    selectedFavoriteId.value = found ? String(found.id) : "";
    window.alert("お気に入りを保存しました。");
  } catch (e) {
    const detail = e?.response?.data?.detail || e?.message || "保存に失敗しました。";
    window.alert(`お気に入り保存エラー: ${detail}`);
  }
};

const changePage = (page) => {
  const target = Math.min(Math.max(page, 1), totalPages.value);
  if (target === currentPage.value) return;
  currentPage.value = target;
};

watch([productFilter, customerFilter, shipToFilter, startDate, horizon], () => {
  currentPage.value = 1;
  holidays.value = buildWeekendFallback();
});

watch(pageSize, () => {
  currentPage.value = 1;
});

watch(groups, () => {
  if (currentPage.value > totalPages.value) {
    currentPage.value = totalPages.value;
  }
});

loadFavorites();

</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  height: 100%;
  min-height: 0;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}
.page-title {
  margin: 0 0 4px 0;
  font-size: 20px;
  font-weight: 700;
}
.subtitle {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}
.page-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.page-actions input,
.page-actions select,
.page-actions button {
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 13px;
}
.page-actions button {
  background: #3b82f6;
  color: white;
  cursor: pointer;
  font-weight: 500;
}
.page-actions button:hover:not(:disabled) {
  background: #2563eb;
}
.page-actions button:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}
.recalc-btn {
  background: #f59e0b !important;
  border-color: #d97706 !important;
  color: #fff !important;
  font-weight: 600;
}
.recalc-btn:hover:not(:disabled) {
  background: #d97706 !important;
}
.favorite-star-btn {
  background: #facc15 !important;
  border-color: #eab308 !important;
  color: #78350f !important;
  font-weight: 700;
  min-width: 34px;
}
.favorite-star-btn:hover:not(:disabled) {
  background: #eab308 !important;
}

.page-body {
  flex: 1;
  min-height: 0;
  display: flex;
}

.list-area {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.pagination-area {
  position: sticky;
  left: 0;
  margin-top: 12px;
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
  border: 1px solid #d1d5db;
  background-color: #fff;
  color: #374151;
  border-radius: 4px;
  cursor: pointer;
}

.pagination-btn.is-active {
  background-color: #1f2937;
  border-color: #1f2937;
  color: #fff;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-info {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  font-size: 12px;
  color: #6b7280;
}

.page-size {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.page-size-select {
  padding: 2px 6px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 12px;
}

.group-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.progress-warning {
  margin-bottom: 12px;
  padding: 10px 12px;
  border: 1px solid #f59e0b;
  border-radius: 8px;
  background: #fffbeb;
  color: #92400e;
  font-size: 13px;
  font-weight: 600;
}
.group-card {
  display: grid;
  grid-template-columns: 240px 1fr;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}
.info-block {
  position: sticky;
  left: 0;
  z-index: 3;
  padding: 12px;
  border-right: 1px solid #e5e7eb;
  background: #f9fafb;
  border-radius: 8px 0 0 8px;
}
.info-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid #e5e7eb;
  font-size: 13px;
}
.info-row:last-child {
  border-bottom: none;
}
.product-code-row {
  justify-content: flex-start;
  gap: 8px;
}
.routing-expand-btn {
  margin-left: auto;
  padding: 2px 8px;
  border: 1px solid #2563eb;
  border-radius: 4px;
  background: #3b82f6;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.routing-expand-btn:hover {
  background: #2563eb;
}
.routing-expand-btn:disabled {
  background: #9ca3af;
  border-color: #9ca3af;
  cursor: not-allowed;
}
.routing-expand-area {
  border-top: 1px solid #e5e7eb;
  background: #f8fafc;
  padding: 10px;
}
.routing-expand-error,
.routing-expand-empty {
  font-size: 12px;
  color: #475569;
  padding: 6px 4px;
}
.routing-node-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.routing-node-card {
  border: 1px solid #dbe4f0;
  border-radius: 6px;
  background: #fff;
  overflow: hidden;
}
.routing-node-header {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 6px 8px;
  border-bottom: 1px solid #e5e7eb;
  font-size: 12px;
  background: #f1f5f9;
}
.routing-node-level {
  font-weight: 700;
  color: #334155;
}
.routing-node-code {
  font-weight: 700;
  color: #0f172a;
}
.routing-node-name {
  color: #334155;
}
.routing-node-lt {
  margin-left: auto;
  color: #475569;
}
.routing-node-table {
  min-width: 900px;
}
.info-label {
  font-weight: 600;
  color: #374151;
}
.info-value {
  color: #111827;
  font-weight: 500;
}
.info-value.negative {
  color: #dc2626;
  font-weight: 700;
}
.matrix-block {
  overflow: visible;
}
.matrix-table {
  border-collapse: collapse;
  width: 100%;
}
.matrix-table th,
.matrix-table td {
  border: 1px solid #e5e7eb;
  padding: 6px 8px;
  text-align: right;
  font-size: 12px;
}
.matrix-table thead th {
  position: sticky;
  top: 0;
  background: #f3f4f6;
  font-weight: 600;
  z-index: 1;
  text-align: center;
}
.matrix-table thead th.holiday {
  background: #ffe5ef;
  color: #b03060;
}
.label-col {
  position: sticky;
  left: 240px;
  background: #f9fafb;
  z-index: 2;
  text-align: left !important;
  font-weight: 600;
  min-width: 80px;
}
.day-col {
  min-width: 60px;
}
.cell {
  background: #fff;
}
.cell.holiday:not(.negative) {
  background: #fff0f6;
}
.cell.negative {
  background: #fee;
  color: #dc2626;
  font-weight: 700;
}
.no-data,
.loading {
  padding: 40px;
  text-align: center;
  color: #6b7280;
  font-size: 14px;
}
</style>
