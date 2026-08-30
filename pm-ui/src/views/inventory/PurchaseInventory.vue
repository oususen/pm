<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">仕入れ在庫 / 残量一覧 <DataSourceDialog title="" :sources="dsSources" /></h2>
        <p class="subtitle">購入品を対象に、日付別の数量を右に並べて表示します。</p>
      </div>
      <div class="page-actions">
        <select v-model.number="selectedSupplier" @change="onSupplierChange">
          <option value="">-- 仕入先を選択 --</option>
          <option v-for="s in suppliers" :key="s.id" :value="s.id">
            {{ s.supplier_code }} - {{ s.supplier_name }}
          </option>
        </select>
        <input
          type="text"
          v-model="productFilter"
          placeholder="品番/品名で絞り込み"
        />
        <input type="date" v-model="startDate" @change="onStartChange" />
        <select v-model.number="horizon">
          <option :value="30">30日</option>
          <option :value="60">60日</option>
          <option :value="90">90日</option>
          <option :value="120">120日</option>
        </select>
        <button @click="load" :disabled="loading || !selectedSupplier">更新</button>
        <button
          @click="recalculateInventory"
          :disabled="loading || recalculating || !purchaseLineId"
        >
          在庫再計算
        </button>
        <button
          @click="recalculateVisibleProducts"
          :disabled="loading || recalculating || !purchaseLineId || !groups.length"
        >
          表示品番だけ再計算
        </button>
        <button
          @click="exportToExcel"
          :disabled="!groups.length"
        >
          Excel出力
        </button>
        <button
          @click="openDeepRecalcDialog"
          :disabled="loading || recalculating || !purchaseLineId || !groups.length"
          class="btn-deep-recalc"
        >
          過去から再計算
        </button>
      </div>
    </div>

    <!-- 過去から再計算 確認ダイアログ -->
    <div v-if="showDeepRecalcDialog" class="deep-recalc-overlay" @click.self="showDeepRecalcDialog = false">
      <div class="deep-recalc-modal">
        <div class="deep-recalc-header">
          <h3>過去から在庫・進度を再計算</h3>
          <button class="close-btn" type="button" @click="showDeepRecalcDialog = false">×</button>
        </div>
        <div class="deep-recalc-body">
          <p>
            表示開始日（<strong>{{ startDate }}</strong>）を起点に、在庫・進度を過去から巻き直します。
          </p>
          <ul>
            <li>計算範囲: {{ startDate }} 〜 {{ columns[columns.length - 1] }}</li>
            <li>在庫・進度を再計算した後、計画在庫・計画進度も自動的に更新されます。</li>
            <li>データ量によっては完了まで時間がかかる場合があります。</li>
          </ul>
          <p class="deep-recalc-danger">※ 過去の日の実績を入力した後にのみ実行してください。<br>表示開始日を実績入力日の一番古い日にしてください。<br>むやみに実行すると在庫・進度データが不整合になる恐れがあります。</p>
          <div class="deep-recalc-actions">
            <button type="button" @click="showDeepRecalcDialog = false">キャンセル</button>
            <button type="button" class="btn-confirm-deep" @click="confirmDeepRecalc">実行</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading">読込中...</div>
    <div v-else-if="error" class="no-data">エラー: {{ error }}</div>
    <div v-else-if="!selectedSupplier" class="no-data">
      仕入先を選択してください
    </div>
    <div v-else>
      <div v-if="groups.length" class="group-scroll" ref="groupScrollRef" @scroll="onMainScroll">
        <div class="group-list">
          <div v-for="g in groups" :key="g.key" class="group-card">
            <div class="info-block">
              <div class="info-row">
                <span class="info-label">品番</span>
                <span class="info-value">{{ g.product_code || '-' }}</span>
                <button @click="openWhereUsed(g)" class="expand-btn where-used-btn">
                  ▶ 逆展開
                </button>
              </div>
              <div class="info-row">
                <span class="info-label">品名</span>
                <span class="info-value">{{ g.product_name || '-' }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">仕入先</span>
                <span class="info-value">{{ g.line_name || '-' }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">仕入先コード</span>
                <span class="info-value">{{ g.line_code || '-' }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">翌月</span>
                <span class="info-value"></span>
              </div>
              <div class="info-row">
                <span class="info-label">翌々月</span>
                <span class="info-value"></span>
              </div>
              <div class="info-row lt-row">
                <span class="lt-item"><span class="info-label">自LT</span> {{ g.self_lt_days ?? "-" }}</span>
                <span class="lt-item"><span class="info-label">出荷LT</span> {{ g.total_lt_days ?? "-" }}</span>
              </div>
            </div>

            <div class="matrix-block">
              <table class="matrix-table">
                <thead>
                  <tr>
                    <th class="label-col">項目</th>
                    <th v-for="d in columns"
                      :key="d"
                      class="day-col"
                      :class="{ holiday: isHoliday(d) }"
                    >{{ formatDayHeader(d) }}</th>
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
                      {{ fmt(getValue(g, d, row.key)) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div v-if="g.showChildren" class="children-list">
              <div v-if="g.children.length === 0" class="no-children">BOM子製品がありません</div>
              <div v-for="(child, idx) in g.children" :key="idx" class="child-card">
                <div class="child-info">
                  <div class="child-row">
                    <span class="child-label">品番</span>
                    <span class="child-value">{{ child.product_code }}</span>
                  </div>
                  <div class="child-row">
                    <span class="child-label">品名</span>
                    <span class="child-value">{{ child.product_name }}</span>
                  </div>
                  <div class="child-row">
                    <span class="child-label">工程</span>
                    <span class="child-value">{{ child.process_code }}</span>
                  </div>
                  <div class="child-row">
                    <span class="child-label">BOM数量</span>
                    <span class="child-value">{{ child.bom_quantity }}</span>
                  </div>
                </div>
                <div class="child-matrix">
                  <table class="matrix-table">
                    <thead>
                      <tr>
                        <th class="label-col">項目</th>
                        <th v-for="d in columns"
                          :key="d"
                          class="day-col"
                          :class="{ holiday: isHoliday(d) }"
                        >{{ formatDayHeader(d) }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="row in rowDefs" :key="row.key">
                        <th class="label-col">{{ row.label }}</th>
                        <td
                          v-for="d in columns"
                          :key="`${row.key}-${d}`"
                          class="cell"
                          :class="getCellClass(child, d, row.key)"
                        >
                          {{ fmt(getValue(child, d, row.key)) }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="no-data">データがありません</div>
    </div>
    <div
      v-if="groups.length"
      class="floating-x-scroll"
      ref="floatingScrollRef"
      @scroll="onFloatingScroll"
    >
      <div class="floating-x-scroll-inner" :style="{ width: `${floatingInnerWidth}px` }"></div>
    </div>

    <div v-if="loading || recalculating" class="processing-overlay">
      <div class="processing-box">
        <p class="processing-title">データ更新中</p>
        <p class="processing-sub">少々お待ちください</p>
      </div>
    </div>

  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, onUpdated, nextTick, ref } from "vue";
import api from "@/api/client";
import { authState } from "@/auth";
import { addDays, formatISODate, parseISODate } from "@/utils/dateUtil";
import DataSourceDialog from '@/components/DataSourceDialog.vue'
import {
  compareBySpecialOrderThenProductCode,
  resolveSpecialDisplayOrder,
} from "@/utils/groupSort";

const dsSources = [
  { section: '在庫・進度データ' },
  { op: '需要/実績 読み書き', table: 'line_backlog', desc: '需要(seq=0)・計画実績(seq>0)・調整数・仕損' },
  { op: '在庫再計算 書き込み', table: 'line_backlog', desc: '在庫・計画在庫・進度の再計算結果' },
  { section: 'マスタ' },
  { op: '仕入先 読み取り', table: 'm_supplier', desc: '仕入先マスタ' },
  { op: '製品 読み取り', table: 'm_product', desc: '製品マスタ（購入品フィルタ）' },
  { op: 'BOM 読み取り', table: 'm_bom / m_bom_item', desc: '部品表（逆展開・子製品表示）' },
  { op: 'ルーティング 読み取り', table: 'm_routing_step', desc: 'ルーティング工程（仕入先→製品特定）' },
  { op: 'ライン 読み取り', table: 'm_line', desc: 'ラインマスタ（仕入先ライン解決）' },
  { op: 'カレンダー 読み取り', table: 'm_calendar / m_calendar_day', desc: '営業日カレンダー（休日表示）' },
]
const selectedSupplier = ref("");
const productFilter = ref("");
const defaultStart = new Date();
defaultStart.setDate(1);
const startDate = ref(formatISODate(defaultStart));
const horizon = ref(30);
const loading = ref(false);
const error = ref("");
const recalculating = ref(false);
const demands = ref([]);
const suppliers = ref([]);
const holidays = ref(new Set());
const products = ref([]);
const purchaseLineId = ref("");
const adjustInputs = ref({});
const adjustSaving = ref({});
const groupScrollRef = ref(null);
const floatingScrollRef = ref(null);
const floatingInnerWidth = ref(0);
let syncingScroll = false;
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

const formatDayHeader = (dateStr) => {
  if (!dateStr) return "";
  const d = parseISODate(dateStr);
  if (!d || Number.isNaN(d.getTime())) return dateStr;
  const m = d.getMonth() + 1;
  const day = d.getDate();
  return `${m}/${day}`;
};

const isWeekend = (dateStr) => {
  const d = parseISODate(dateStr);
  if (!d || Number.isNaN(d.getTime())) return false;
  const day = d.getDay();
  return day === 0 || day === 6;
};

const isHoliday = (dateStr) => holidays.value.has(dateStr) || isWeekend(dateStr);

const buildWeekendFallback = () => {
  return new Set(columns.value.filter((d) => isWeekend(d)));
};

const normalizeList = (payload) => {
  return Array.isArray(payload) ? payload : payload?.results || [];
};

const loadHolidayColumns = async () => {
  const fallback = buildWeekendFallback();
  try {
    // この画面は特定カレンダーに依存しないため、'daiso'をフォールバックとして使用
    const res = await api.calendars.getCalendars({ search: "daiso", page_size: 1 });
    const rows = normalizeList(res.data || []);
    const daisoCalendar = rows.find((row) => String(row.calendar_code || "").toLowerCase() === "daiso");
    if (!daisoCalendar?.id) {
      holidays.value = fallback;
      return;
    }
    const daysRes = await api.calendars.getCalendarDays(daisoCalendar.id, { page_size: 5000 });
    const dayRows = normalizeList(daysRes.data || []);
    const displayedDateSet = new Set(columns.value);
    const holidaySet = new Set(
      dayRows
        .filter(day => !day.is_working_day && displayedDateSet.has(day.target_date))
        .map(day => day.target_date)
    );
    holidays.value = holidaySet.size > 0 ? new Set([...fallback, ...holidaySet]) : fallback;
  } catch (e) {
    console.error("休日判定の取得に失敗:", e);
    holidays.value = fallback;
  }
};

const rowDefs = [
  { key: "forecast", label: "計需" },
  { key: "firm", label: "実需" },
  { key: "plan", label: "計画" },
  { key: "actual", label: "実績" },
  { key: "adjust", label: "調整" },
  { key: "scrap", label: "仕損" },
  { key: "stock", label: "在庫" },
  { key: "planned_stock", label: "計画在庫" },
  { key: "progress", label: "進度" },
];

const applyDemands = (payload) => {
  const list = Array.isArray(payload) ? payload : payload.results || [];
  demands.value = list;
  if (!userSetStart && !startDate.value && demands.value.length) {
    const minDate = demands.value.map((d) => d.plan_date).sort()[0];
    if (minDate) {
      startDate.value = minDate;
    }
  }
};

const groups = computed(() => {
  if (!demands.value.length) return [];
  const filtered = demands.value.filter((d) => {
    const within =
      d.plan_date >= columns.value[0] &&
      d.plan_date <= columns.value[columns.value.length - 1];
    const prodText = `${d.product_code || ""}${d.product_name || ""}`.toLowerCase();
    const okProd =
      !productFilter.value ||
      prodText.includes(productFilter.value.trim().toLowerCase());
    return within && okProd;
  });

  const buildGroupKey = (row) => {
    return `${row.line || row.line_name || ""}__${row.product_code || ""}`;
  };

  const chooseRepresentativeProcess = (group, row) => {
    const nextId = row.process ?? null;
    const nextCode = row.process_code || row.process || "";
    const nextName = row.process_name || "";
    if (!group.process_id && !group.process_code) {
      group.process_id = nextId;
      group.process_code = nextCode;
      group.process_name = nextName;
      return;
    }
    if (String(group.process_code || "").toUpperCase() === "PURCHASE") {
      return;
    }
    if (String(nextCode || "").toUpperCase() === "PURCHASE") {
      group.process_id = nextId;
      group.process_code = nextCode;
      group.process_name = nextName;
    }
  };

  const map = new Map();
  for (const d of filtered) {
    const key = buildGroupKey(d);
    const specialDisplayOrder = resolveSpecialDisplayOrder(d);
    if (!map.has(key)) {
        map.set(key, {
          key,
          line_code: d.line_code,
          line_name: d.line_name,
          product_code: d.product_code,
          product_name: d.product_name,
          product_id: d.product,
          line_id: d.line,
          process_id: d.process,
          process_code: d.process_code || d.process || "",
          process_name: d.process_name || "",
          is_virtual_set: Boolean(d.is_virtual_set),
          special_display_order: specialDisplayOrder,
          total_lt_days: null,
          self_lt_days: null,
          cells: {},
          children: [],
          showChildren: false,
          isChild: false,
        });
      }
      const g = map.get(key);
      chooseRepresentativeProcess(g, d);
      if (specialDisplayOrder !== null) {
        const currentOrder = resolveSpecialDisplayOrder(g);
        if (currentOrder === null || specialDisplayOrder < currentOrder) {
          g.special_display_order = specialDisplayOrder;
        }
      }
      if (g.total_lt_days === null && d.total_lt_days !== null && d.total_lt_days !== undefined) {
        g.total_lt_days = Number(d.total_lt_days);
      }
      if (g.self_lt_days === null && d.self_lt_days !== null && d.self_lt_days !== undefined) {
        g.self_lt_days = Number(d.self_lt_days);
      }
      if (d.is_virtual_set) g.is_virtual_set = true;
    if (!g.cells[d.plan_date]) {
      g.cells[d.plan_date] = {
        forecast: 0,
        firm: 0,
        plan: 0,
        actual: 0,
        adjust: 0,
        scrap: 0,
        stock: 0,
        planned_stock: 0,
        progress: 0,
      };
    }
    const c = g.cells[d.plan_date];
    const seqVal = Number.isFinite(Number(d.sequence_no)) ? Number(d.sequence_no) : 0;
    const orderQty = Number(d.order_qty || 0);
    const demandQty = Number(d.demand_qty_plan || 0);
    const planQty = Number(d.plan_qty || 0);
    const isDemandRow = (orderQty > 0 || demandQty > 0) && planQty === 0;
    const hasFirmSplit = d.firm_order_qty !== null && d.firm_order_qty !== undefined;
    if (isDemandRow) {
      const hasForecastSplit = d.forecast_order_qty !== null && d.forecast_order_qty !== undefined;
      const forecastVal = Number((hasForecastSplit ? d.forecast_order_qty : d.order_qty) || 0);
      if (c.demand_seq === undefined || seqVal < c.demand_seq) {
        c.demand_seq = seqVal;
        c.forecast = forecastVal;
      } else if (seqVal === c.demand_seq) {
        c.forecast = Math.max(c.forecast, forecastVal);
      }
    }
    const firmVal = Number((hasFirmSplit ? d.firm_order_qty : d.actual_shipment_qty) || 0);
    const shouldApplyFirm = (isDemandRow && hasFirmSplit) || !hasFirmSplit;
    if (shouldApplyFirm) {
      if (c.firm_seq === undefined || seqVal < c.firm_seq) {
        c.firm_seq = seqVal;
        c.firm = firmVal;
      } else if (seqVal === c.firm_seq) {
        c.firm = Math.max(c.firm, firmVal);
      }
    }
    c.plan += Number(d.plan_qty || 0);
    c.actual += Number(d.actual_qty || 0);
    c.adjust += Number(d.adjust_qty || 0);
    c.scrap += Number(d.scrap_qty || 0);
    c.stock += Number(d.stock_qty || 0);
    c.planned_stock += Number(d.planned_stock_qty || 0);
    // 進度はバックエンドで計算された値を使用
    c.progress += Number(d.progress_qty || 0);
  }

  // 進度が日付抜けで途切れないよう、日付順に直近値をキャリーする
  const carryForwardProgress = (group) => {
    let last = null;
    columns.value.forEach((date) => {
      const cell = group.cells[date];
      const val = cell ? cell.progress : undefined;
      if (val !== null && val !== undefined) {
        last = val;
      } else if (last !== null && last !== undefined) {
        if (!group.cells[date]) group.cells[date] = {};
        group.cells[date].progress = last;
      }
    });
    if (group.children && group.children.length) {
      group.children.forEach(carryForwardProgress);
    }
  };

  const result = Array.from(map.values());
  result.forEach(carryForwardProgress);
  result.sort((a, b) => {
    const aVirtual = Boolean(a?.is_virtual_set);
    const bVirtual = Boolean(b?.is_virtual_set);
    if (aVirtual !== bVirtual) return aVirtual ? 1 : -1;
    return compareBySpecialOrderThenProductCode(a, b, {
      codeGetter: (item) => item.product_code || "",
    });
  });
  return result;
});

const fmt = (n) => {
  if (n === null || n === undefined) return "";
  const num = Number(n);
  if (Number.isNaN(num)) return "";
  if (num === 0) return "";
  return num.toLocaleString();
};

const getValue = (group, date, key) => {
  return group.cells?.[date]?.[key] ?? "";
};

const getCellClass = (group, date, rowKey) => {
  const classes = [];
  if (isHoliday(date)) classes.push("holiday");
  if (rowKey === "stock" || rowKey === "planned_stock" || rowKey === "progress") {
    const value = getValue(group, date, rowKey);
    if (value !== null && value !== undefined && Number(value) < 0) {
      classes.push("negative");
    }
  }
  return classes.join(" ");
};

const adjustKey = (group, date) => `${group.key}__${date}`;

const getAdjustInputValue = (group, date) => {
  const key = adjustKey(group, date);
  if (Object.prototype.hasOwnProperty.call(adjustInputs.value, key)) {
    return adjustInputs.value[key];
  }
  const current = getValue(group, date, "adjust");
  if (current === null || current === undefined) return "";
  const num = Number(current);
  if (Number.isNaN(num) || num === 0) return "";
  return String(num);
};

const onAdjustInput = (group, date, event) => {
  adjustInputs.value[adjustKey(group, date)] = event.target.value;
};

const onAdjustEnter = (event) => {
  event.target.blur();
};

const isAdjustSaving = (group, date) => {
  return Boolean(adjustSaving.value[adjustKey(group, date)]);
};

const updateAdjustDemand = (group, date, adjustQty) => {
  let idx = demands.value.findIndex(
    (d) =>
      d.line === group.line_id &&
      d.process === group.process_id &&
      d.product === group.product_id &&
      d.plan_date === date
  );
  if (idx < 0) {
    idx = demands.value.findIndex(
      (d) =>
        d.line === group.line_id &&
        d.product === group.product_id &&
        d.plan_date === date
    );
  }
  if (idx >= 0) {
    demands.value[idx].adjust_qty = adjustQty;
    return;
  }
  demands.value.push({
    line: group.line_id,
    line_code: group.line_code,
    line_name: group.line_name,
    process: group.process_id,
    process_code: group.process_code,
    process_name: group.process_name,
    product: group.product_id,
    product_code: group.product_code,
    product_name: group.product_name,
    plan_date: date,
    order_qty: 0,
    actual_qty: 0,
    plan_qty: 0,
    adjust_qty: adjustQty,
    scrap_qty: 0,
    stock_qty: 0,
    planned_stock_qty: 0,
    progress_qty: 0,
  });
};

const saveAdjust = async (group, date) => {
  if (group.isChild) return;
  if (!group.line_id || !group.process_id || !group.product_id) {
    alert("調整の保存に必要な情報が不足しています。");
    return;
  }
  const key = adjustKey(group, date);
  if (adjustSaving.value[key]) return;
  const raw = adjustInputs.value[key];
  let adjustQty = 0;
  if (raw !== "" && raw !== null && raw !== undefined) {
    const parsed = Number(raw);
    if (Number.isNaN(parsed) || !Number.isFinite(parsed)) {
      alert("調整数は数値で入力してください。");
      return;
    }
    if (!Number.isInteger(parsed)) {
      alert("調整数は整数で入力してください。");
      return;
    }
    adjustQty = parsed;
  }
  const current = Number(getValue(group, date, "adjust") || 0);
  if (adjustQty === current) {
    delete adjustInputs.value[key];
    return;
  }

  adjustSaving.value[key] = true;
  try {
    await api.lineBacklogs.save({
      line_id: group.line_id,
      items: [
        {
          product_id: group.product_id,
          process_id: group.process_id,
          plan_date: date,
          adjust_qty: adjustQty,
        },
      ],
    });
    updateAdjustDemand(group, date, adjustQty);
    const start = columns.value[0];
    const end = columns.value[columns.value.length - 1];
    await api.lineBacklogs.recalculateInventory({
      line_id: group.line_id,
      start_date: start,
      end_date: end,
    });
    await reloadDemands();
    delete adjustInputs.value[key];
  } catch (e) {
    console.error("調整の保存に失敗:", e);
    alert("調整の保存に失敗しました。");
  } finally {
    delete adjustSaving.value[key];
  }
};

const loadBOMChildren = async (group) => {
  if (!group.product_id) return;

  try {
    const bomRes = await api.boms.getBOMs({ parent_product: group.product_id });
    const boms = bomRes.data || [];

    if (!boms.length) {
      group.children = [];
      return;
    }

    const activeBoms = boms.filter((b) => b.is_active);
    if (!activeBoms.length) {
      group.children = [];
      return;
    }

    const bom = activeBoms[0];
    const itemsRes = await api.bomItems.getBOMItems({ bom: bom.id });
    const items = itemsRes.data || [];

    const children = [];
    for (const item of items) {
      const childDemands = demands.value.filter(
        (d) =>
          d.product === item.child_product &&
          d.plan_date >= columns.value[0] &&
          d.plan_date <= columns.value[columns.value.length - 1]
      );

      if (childDemands.length > 0) {
        const childCells = {};
        for (const d of childDemands) {
          if (!childCells[d.plan_date]) {
            childCells[d.plan_date] = {
              forecast: 0,
              firm: 0,
              plan: 0,
              actual: 0,
              adjust: 0,
              scrap: 0,
              stock: 0,
              planned_stock: 0,
              progress: 0,
            };
          }
          const c = childCells[d.plan_date];
          const seqVal = Number.isFinite(Number(d.sequence_no)) ? Number(d.sequence_no) : 0;
          const orderQty = Number(d.order_qty || 0);
          const demandQty = Number(d.demand_qty_plan || 0);
          const planQty = Number(d.plan_qty || 0);
          const isDemandRow = (orderQty > 0 || demandQty > 0) && planQty === 0;
          const hasFirmSplit = d.firm_order_qty !== null && d.firm_order_qty !== undefined;
          if (isDemandRow) {
            const hasForecastSplit = d.forecast_order_qty !== null && d.forecast_order_qty !== undefined;
            const forecastVal = Number((hasForecastSplit ? d.forecast_order_qty : d.order_qty) || 0);
            if (c.demand_seq === undefined || seqVal < c.demand_seq) {
              c.demand_seq = seqVal;
              c.forecast = forecastVal;
            } else if (seqVal === c.demand_seq) {
              c.forecast = Math.max(c.forecast, forecastVal);
            }
          }
          const firmVal = Number((hasFirmSplit ? d.firm_order_qty : d.actual_shipment_qty) || 0);
          const shouldApplyFirm = (isDemandRow && hasFirmSplit) || !hasFirmSplit;
          if (shouldApplyFirm) {
            if (c.firm_seq === undefined || seqVal < c.firm_seq) {
              c.firm_seq = seqVal;
              c.firm = firmVal;
            } else if (seqVal === c.firm_seq) {
              c.firm = Math.max(c.firm, firmVal);
            }
          }
          c.plan += Number(d.plan_qty || 0);
          c.actual += Number(d.actual_qty || 0);
          c.adjust += Number(d.adjust_qty || 0);
          c.scrap += Number(d.scrap_qty || 0);
          c.stock += Number(d.stock_qty || 0);
          c.planned_stock += Number(d.planned_stock_qty || 0);
          // 進度はバックエンドで計算された値を使用
          c.progress += Number(d.progress_qty || 0);
        }

        const childDemand = childDemands[0];
        children.push({
          product_code: childDemand.product_code,
          product_name: childDemand.product_name,
          product_id: childDemand.product,
          process_code: childDemand.process_code,
          process_name: childDemand.process_name,
          process_id: childDemand.process,
          line_code: childDemand.line_code,
          line_name: childDemand.line_name,
          line_id: childDemand.line,
          bom_quantity: item.quantity,
          cells: childCells,
          isChild: true,
        });
      }
    }

    group.children = children;
  } catch (e) {
    console.error("BOM子製品の読み込みに失敗:", e);
    group.children = [];
  }
};

const toggleChildren = async (group) => {
  group.showChildren = !group.showChildren;
  if (group.showChildren && group.children.length === 0) {
    await loadBOMChildren(group);
  }
};

const openWhereUsed = (group) => {
  if (!group.product_id) return
  const url = `/masters/where-used?productId=${group.product_id}`
  window.open(url, '_blank')
};

const reloadDemands = async () => {
  if (!purchaseLineId.value) return;
  const res = await api.lineBacklogs.getLineBacklogs(getBacklogParams());
  const payload = res.data || [];
  applyDemands(payload);
};

const getBacklogParams = () => {
  const start = columns.value[0];
  const end = columns.value[columns.value.length - 1];
  const productIds = products.value.map((p) => p.id);
  return {
    line: purchaseLineId.value,
    product__in: productIds.join(","),
    plan_date__gte: start,
    plan_date__lte: end,
    include_order_split: true,
  };
};

const getDisplayedProductTargets = () => {
  const productIds = new Set();
  const productCodes = new Set();
  groups.value.forEach((group) => {
    if (!group.product_id) return;
    productIds.add(group.product_id);
    if (group.product_code) {
      productCodes.add(group.product_code);
    }
  });
  return {
    product_ids: Array.from(productIds).sort((a, b) => a - b),
    product_codes: Array.from(productCodes).sort(),
  };
};

const buildVisibleProductConfirmMessage = (target) => {
  const preview = target.product_codes.slice(0, 10).join(", ");
  const suffix = target.product_codes.length > 10 ? ` ほか${target.product_codes.length - 10}件` : "";
  return `表示中の${target.product_codes.length}件を再計算しますか？\n${preview}${suffix}`;
};

const fetchSuppliers = async () => {
  const res = await api.suppliers.getSuppliers();
  suppliers.value = res.data.results || res.data || [];
};

const fetchProducts = async (supplierId = null) => {
  try {
    let targetProductIds = new Set();
    if (supplierId) {
      // ルーティング基準（互換）:
      // 1) 外作先一致
      // 2) 仕入先コードと一致するライン上の工程
      const supplier = suppliers.value.find((s) => Number(s.id) === Number(supplierId));
      const [stepsBySupplierRes, linesRes] = await Promise.all([
        api.routings.getRoutingSteps({ supplier: supplierId, page_size: 5000 }),
        api.lines.getLines({ page_size: 500 }),
      ]);
      const stepsBySupplier = stepsBySupplierRes.data.results || stepsBySupplierRes.data || [];
      const allLines = linesRes.data.results || linesRes.data || [];
      const purchaseLine = supplier?.supplier_code
        ? allLines.find((l) => String(l.line_code || "").trim() === String(supplier.supplier_code || "").trim())
        : null;
      let stepsByLine = [];
      if (purchaseLine?.id) {
        const stepsByLineRes = await api.routings.getRoutingSteps({ line: purchaseLine.id, page_size: 5000 });
        stepsByLine = stepsByLineRes.data.results || stepsByLineRes.data || [];
      }
      const mergedSteps = [...stepsBySupplier, ...stepsByLine];
      targetProductIds = new Set(
        mergedSteps
          .map((s) => Number(s.output_product))
          .filter((id) => Number.isFinite(id) && id > 0)
      );
    } else {
      const params = { sourcing_type: "BUY" };
      const bomItemsRes = await api.bomItems.getBOMItems(params);
      const bomItems = bomItemsRes.data.results || bomItemsRes.data || [];
      targetProductIds = new Set(bomItems.map((item) => item.child_product));
    }

    const allProducts = await api.products.getAllProducts();
    const filtered =
      supplierId && targetProductIds.size
        ? allProducts.filter((p) => !p.is_phantom && targetProductIds.has(p.id))
        : allProducts.filter((p) => !p.is_phantom);

    products.value = filtered.sort((a, b) =>
      (a.product_code || "").localeCompare(b.product_code || "")
    );
  } catch (e) {
    console.error("購入品の取得エラー", e);
    products.value = [];
  }
};

const refreshPurchaseDemand = async () => {
  if (!selectedSupplier.value) return false;
  const start = columns.value[0];
  const end = columns.value[columns.value.length - 1];
  const pickupRes = await api.lineBacklogs.pickupPurchase({
    supplier_id: selectedSupplier.value,
    start_date: start,
    end_date: end,
  });
  purchaseLineId.value = pickupRes?.data?.line_id || "";
  return Boolean(purchaseLineId.value);
};

const refreshScrapQty = async () => {
  if (!purchaseLineId.value) return false;
  const start = columns.value[0];
  const end = columns.value[columns.value.length - 1];
  try {
    await api.lineBacklogs.recalculateScrap({
      line_id: purchaseLineId.value,
      start_date: start,
      end_date: end,
    });
    return true;
  } catch (e) {
    console.error("仕損再計算に失敗:", e);
    return false;
  }
};

const onSupplierChange = () => {
  demands.value = [];
  purchaseLineId.value = "";
};

const load = async () => {
  if (!selectedSupplier.value) return;
  loading.value = true;
  error.value = "";
  try {
    await fetchProducts(selectedSupplier.value);
    const productIds = products.value.map((p) => p.id);
    if (!productIds.length) {
      demands.value = [];
      return;
    }
    const refreshed = await refreshPurchaseDemand();
    if (!refreshed) {
      throw new Error("仕入れラインの解決に失敗しました");
    }
    await refreshScrapQty();
    const res = await api.lineBacklogs.getLineBacklogs(getBacklogParams());
    const payload = res.data || [];
    applyDemands(payload);
    await loadHolidayColumns();
  } catch (e) {
    error.value = e?.message || "読み込みに失敗しました";
  } finally {
    loading.value = false;
  }
};

const recalculateInventory = async () => {
  if (!purchaseLineId.value) return;
  if (!confirm("在庫と計画在庫を再計算しますか？")) {
    return;
  }
  recalculating.value = true;
  error.value = "";
  try {
    const start = columns.value[0];
    const end = columns.value[columns.value.length - 1];
    await api.lineBacklogs.recalculateInventory({
      line_id: purchaseLineId.value,
      start_date: start,
      end_date: end,
    });
    await reloadDemands();
    await loadHolidayColumns();
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || "在庫再計算に失敗しました";
    alert("エラー: " + error.value);
  } finally {
    recalculating.value = false;
  }
};

const recalculateVisibleProducts = async () => {
  if (!purchaseLineId.value || !selectedSupplier.value) return;
  const target = getDisplayedProductTargets();
  if (!target.product_ids.length) {
    alert("再計算対象の品番がありません。");
    return;
  }
  if (!confirm(buildVisibleProductConfirmMessage(target))) {
    return;
  }

  recalculating.value = true;
  error.value = "";
  try {
    const start = columns.value[0];
    const end = columns.value[columns.value.length - 1];

    await api.lineBacklogs.pickupPurchaseForProducts({
      supplier_id: selectedSupplier.value,
      start_date: start,
      end_date: end,
      product_ids: target.product_ids,
    });
    await api.lineBacklogs.recalculateScrapForProducts({
      line_id: purchaseLineId.value,
      start_date: start,
      end_date: end,
      product_ids: target.product_ids,
    });
    await api.lineBacklogs.recalculateInventoryForProducts({
      line_id: purchaseLineId.value,
      start_date: start,
      end_date: end,
      product_ids: target.product_ids,
    });
    await reloadDemands();
    await loadHolidayColumns();
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || "表示品番の再計算に失敗しました";
    alert("エラー: " + error.value);
  } finally {
    recalculating.value = false;
  }
};

const showDeepRecalcDialog = ref(false);

const openDeepRecalcDialog = () => {
  showDeepRecalcDialog.value = true;
};

const confirmDeepRecalc = async () => {
  showDeepRecalcDialog.value = false;
  recalculating.value = true;
  error.value = "";
  try {
    const start = startDate.value;
    const end = columns.value[columns.value.length - 1];
    await api.lineBacklogs.recalculateInventoryDeep({
      line_id: purchaseLineId.value,
      start_date: start,
      end_date: end,
    });
    await reloadDemands();
    await loadHolidayColumns();
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || "過去から再計算に失敗しました";
    alert("エラー: " + error.value);
  } finally {
    recalculating.value = false;
  }
};

const escapeCsv = (val) => {
  if (val === null || val === undefined) return '';
  const str = String(val);
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return '"' + str.replace(/"/g, '""') + '"';
  }
  return str;
};

const formatDateSlash = (dateStr) => {
  if (!dateStr) return dateStr;
  const d = parseISODate(dateStr);
  if (!d || Number.isNaN(d.getTime())) return dateStr;
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`;
};

const exportToExcel = () => {
  if (!groups.value.length) {
    alert('出力対象のデータがありません。');
    return;
  }
  const supplierObj = suppliers.value.find((s) => s.id === selectedSupplier.value);
  const supplierLabel = supplierObj
    ? `${supplierObj.supplier_code} - ${supplierObj.supplier_name}`
    : String(selectedSupplier.value || '');
  const start = columns.value[0] || '';
  const end = columns.value[columns.value.length - 1] || '';

  const bom = '\ufeff';
  const lines = [];
  lines.push([escapeCsv('仕入先'), escapeCsv(supplierLabel)].join(','));
  lines.push([escapeCsv('期間'), escapeCsv(`${start} ～ ${end}`)].join(','));
  lines.push('');

  // ヘッダー行（日付をYYYY/M/D形式に）
  const headerRow = ['品番', '品名', '出荷LT', '自LT', '項目', ...columns.value.map(formatDateSlash)];
  lines.push(headerRow.map(escapeCsv).join(','));

  // データ行（品番・品名は各品番の最初の行のみ出力）
  for (const g of groups.value) {
    const ltDays = g.total_lt_days !== null && g.total_lt_days !== undefined ? g.total_lt_days : '';
    const selfLt = g.self_lt_days !== null && g.self_lt_days !== undefined ? g.self_lt_days : '';
    rowDefs.forEach((row, idx) => {
      const isFirst = idx === 0;
      const cells = [
        isFirst ? (g.product_code || '') : '',
        isFirst ? (g.product_name || '') : '',
        ltDays,
        selfLt,
        row.label,
        ...columns.value.map((d) => {
          const val = getValue(g, d, row.key);
          if (val === null || val === undefined || val === '') return '';
          const num = Number(val);
          return Number.isNaN(num) ? '' : num;
        }),
      ];
      lines.push(cells.map(escapeCsv).join(','));
    });
  }

  const csvContent = bom + lines.join('\r\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  const supplierCode = supplierObj?.supplier_code || '';
  link.href = url;
  link.download = `仕入れ在庫_${supplierCode}_${start}_${end}.csv`;
  link.click();
  URL.revokeObjectURL(url);
};

const updateFloatingScroll = () => {
  const main = groupScrollRef.value;
  const floating = floatingScrollRef.value;
  if (!main || !floating) return;
  floatingInnerWidth.value = Math.max(main.scrollWidth, main.clientWidth);
  floating.scrollLeft = main.scrollLeft;
};

const onMainScroll = () => {
  const main = groupScrollRef.value;
  const floating = floatingScrollRef.value;
  if (!main || !floating || syncingScroll) return;
  syncingScroll = true;
  floating.scrollLeft = main.scrollLeft;
  syncingScroll = false;
};

const onFloatingScroll = () => {
  const main = groupScrollRef.value;
  const floating = floatingScrollRef.value;
  if (!main || !floating || syncingScroll) return;
  syncingScroll = true;
  main.scrollLeft = floating.scrollLeft;
  syncingScroll = false;
};

const onWindowResize = () => {
  updateFloatingScroll();
};

onMounted(async () => {
  window.addEventListener("resize", onWindowResize);
  await fetchSuppliers();
  nextTick(updateFloatingScroll);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", onWindowResize);
});

onUpdated(() => {
  nextTick(updateFloatingScroll);
});
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
  position: sticky;
  top: 0;
  z-index: 50;
  background: #f5f5e6;
  padding: 6px 0;
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
.group-scroll {
  overflow-x: auto;
  scrollbar-width: none;
}
.group-scroll::-webkit-scrollbar {
  display: none;
}
.floating-x-scroll {
  position: sticky;
  bottom: 0;
  z-index: 30;
  overflow-x: auto;
  overflow-y: hidden;
  border: 1px solid #d1d5db;
  background: #f8fafc;
  height: 16px;
}
.floating-x-scroll-inner {
  height: 1px;
}
.group-card {
  display: grid;
  grid-template-columns: 260px 1fr;
  border: 1px solid #dce3ef;
  border-radius: 10px;
  overflow: visible;
  background: #fff;
  width: max-content;
  min-width: 100%;
}
.info-block {
  position: sticky;
  left: 0;
  z-index: 4;
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
.lt-row {
  display: flex;
  gap: 12px;
}
.lt-item {
  font-size: 12px;
  color: #374151;
}
.matrix-block {
  --fixed-left: 260px;
  overflow: visible;
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
.matrix-table thead th.holiday {
  background: #ffe5ef;
  color: #b03060;
}
.label-col {
  position: sticky;
  left: var(--fixed-left, 0px);
  background: #f9fafb;
  z-index: 2;
  text-align: left;
  min-width: 100px;
}
.cell {
  &.negative {
    background: #fee;
    color: #c00;
    font-weight: bold;
  }
  background: #fff;
}
.cell.holiday:not(.negative) {
  background: #fff0f6;
}
.cell-input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  padding: 4px 6px;
  text-align: right;
  font-size: 12px;
  background: #fff;
}
.cell-input:disabled {
  background: #f3f4f6;
  color: #9ca3af;
}
.no-data,
.loading {
  padding: 24px;
  text-align: center;
  color: #6b7280;
}
.expand-btn {
  margin-left: 8px;
  padding: 4px 8px;
  font-size: 12px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.expand-btn:hover {
  background: #2563eb;
}
.where-used-btn {
  background: #17a2b8;
}
.where-used-btn:hover {
  background: #138496;
}
.children-list {
  padding: 12px;
  background: #f1f5f9;
  border-top: 2px solid #cbd5e1;
}
.no-children {
  padding: 12px;
  text-align: center;
  color: #64748b;
  font-size: 13px;
}
.child-card {
  display: grid;
  grid-template-columns: 200px 1fr;
  margin-bottom: 12px;
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  overflow: hidden;
}
.child-card:last-child {
  margin-bottom: 0;
}
.child-info {
  position: sticky;
  left: 0;
  z-index: 4;
  padding: 8px;
  background: #fefce8;
  border-right: 1px solid #e5e7eb;
}
.child-row {
  display: flex;
  justify-content: space-between;
  padding: 4px;
  font-size: 12px;
  border-bottom: 1px solid #fde68a;
}
.child-row:last-child {
  border-bottom: none;
}
.child-label {
  font-weight: 600;
  color: #92400e;
}
.child-value {
  color: #451a03;
}
.child-matrix {
  --fixed-left: 200px;
  overflow: visible;
}
.processing-overlay {
  position: fixed;
  inset: 0;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  pointer-events: all;
}
.processing-box {
  background: #1f2a44;
  color: #fff;
  padding: 18px 28px;
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
  text-align: center;
  min-width: 240px;
}
.processing-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.05em;
}
.processing-sub {
  margin: 6px 0 0;
  font-size: 13px;
  opacity: 0.9;
}

/* 過去から再計算 ボタン */
.btn-deep-recalc {
  background: #7c3aed;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 13px;
  &:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
  &:not(:disabled):hover {
    background: #6d28d9;
  }
}

/* 過去から再計算 ダイアログ */
.deep-recalc-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000;
}
.deep-recalc-modal {
  background: #fff;
  border-radius: 10px;
  width: min(520px, 92vw);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
  overflow: hidden;
}
.deep-recalc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #7c3aed;
  color: #fff;
  h3 { margin: 0; font-size: 15px; }
}
.close-btn {
  background: transparent;
  border: none;
  color: #fff;
  font-size: 18px;
  cursor: pointer;
}
.deep-recalc-body {
  padding: 16px;
  font-size: 14px;
  line-height: 1.7;
  p { margin: 0 0 8px; }
  ul {
    margin: 0 0 10px;
    padding-left: 20px;
    li { margin-bottom: 4px; }
  }
}
.deep-recalc-danger {
  color: #dc2626;
  font-size: 13px;
  font-weight: 700;
}
.deep-recalc-warn {
  color: #b45309;
  font-size: 12px;
}
.deep-recalc-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
  button {
    padding: 7px 18px;
    border-radius: 6px;
    border: 1px solid #cbd5e1;
    cursor: pointer;
    font-size: 13px;
  }
}
.btn-confirm-deep {
  background: #7c3aed;
  color: #fff;
  border-color: #7c3aed !important;
  &:hover { background: #6d28d9; }
}
</style>
