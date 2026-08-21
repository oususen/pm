<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">在庫 / 残量一覧</h2>
        <p class="subtitle">製品情報を左に、日付別の数量を右に並べて表示します。</p>
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
        <button @click="recalculate" :disabled="loading || recalculating">表示ライン全品番再計算</button>
        <button
          @click="recalculateVisibleProducts"
          :disabled="loading || recalculating || !groups.length"
        >
          表示品番だけ再計算
        </button>
        <button @click="exportToExcel" :disabled="!groups.length">Excel出力</button>
        <button
          @click="openDeepRecalcDialog"
          :disabled="loading || recalculating || !groups.length || !canDeepRecalc"
          class="btn-deep-recalc"
        >
          過去から再計算
        </button>
      </div>
    </div>

    <!-- 過去から再計算 確認ダイアログ -->
    <div v-if="showDeepRecalcDialog" class="code-modal-overlay" @click.self="showDeepRecalcDialog = false">
      <div class="code-modal deep-recalc-modal">
        <div class="code-modal-header">
          <h3>過去から在庫・進度を再計算</h3>
          <button class="close-btn" type="button" @click="showDeepRecalcDialog = false">×</button>
        </div>
        <div class="code-modal-body deep-recalc-body">
          <p>
            表示開始日（<strong>{{ startDate }}</strong>）を起点に、在庫・進度を過去から巻き直します。
          </p>
          <ul>
            <li>対象: <strong>表示中の品番（{{ getDisplayedLineIds().length }}ライン）</strong></li>
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
    <div v-else-if="!lineFilter && !processFilter && !productFilter" class="no-data">
      ライン、工程、または品番を入力してください
    </div>
    <div v-else>
      <div v-if="groups.length" class="group-scroll" ref="groupScrollRef" @scroll="onMainScroll">
        <div class="group-list">
          <div v-for="g in groups" :key="g.key" class="group-card">
            <div class="info-block">
            <div class="info-row">
              <span class="info-label">品番</span>
              <span class="info-value">{{ g.product_code || '-' }}</span>
              <button @click="openWhereUsed(g)" class="expand-btn where-used-btn">▶ 逆展開</button>
            </div>
            <div class="info-row">
              <span class="info-label">品名</span>
              <span class="info-value">{{ g.product_name || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">工程名</span>
              <span class="info-value">{{ getDisplayProcessName(g) || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">工程コード</span>
              <span class="info-value">{{ getDisplayProcessCode(g) || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">予定</span>
              <span class="info-value">{{ fmt(getMonthTotal(g, 'forecast')) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">実需</span>
              <span class="info-value">{{ fmt(getMonthTotal(g, 'firm')) }}</span>
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
                    <th
                      v-for="d in columns"
                      :key="d"
                      class="day-col"
                      :class="{ holiday: isHoliday(d) && !isHolidayWork(d), 'holiday-work': isHolidayWork(d) }"
                    >
                      {{ formatDayHeader(d) }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in rowDefs" :key="row.key">
                    <th class="label-col">{{ row.label }}</th>
                    <td v-for="d in columns"
                      :key="`${row.key}-${d}`"
                      class="cell"
                      :class="[getCellClass(g, d, row.key), { holiday: isHoliday(d) && !isHolidayWork(d), 'holiday-work': isHolidayWork(d) }]"
                    >
                      {{ fmt(getValue(g, d, row.key)) }}
                    </td>
                  </tr>
                </tbody>
              </table>
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
import { computed, ref, onMounted, onBeforeUnmount, onUpdated, nextTick } from "vue";
import api from "@/api/client";
import { addDays, formatISODate, parseISODate } from "@/utils/dateUtil";
import {
  compareBySpecialOrderThenProductCode,
  resolveSpecialDisplayOrder,
} from "@/utils/groupSort";
import { authState } from "@/auth";
import { hasPermission } from "@/router";

const canDeepRecalc = computed(() => {
  const user = authState.user;
  if (!user) return false;
  return hasPermission(user, "production.progress", "edit");
});

const lineFilter = ref("");
const processFilter = ref("");
const productFilter = ref("");
const defaultStart = new Date();
defaultStart.setDate(1);
const startDate = ref(formatISODate(defaultStart));
const horizon = ref(30);
const loading = ref(false);
const error = ref("");
const demands = ref([]);
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

// フィルタ入力でEnter押下時に更新を走らせる
const handleEnter = () => {
  if (loading.value) return;
  load();
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

const getBacklogParams = () => {
  const start = columns.value[0];
  const end = columns.value[columns.value.length - 1];
  const params = {
    plan_date__gte: start,
    plan_date__lte: end,
    include_order_split: true,
  };
  if (lineFilter.value.trim()) params.line_search = lineFilter.value.trim();
  if (processFilter.value.trim()) params.process_search = processFilter.value.trim();
  if (productFilter.value.trim()) params.product_search = productFilter.value.trim();
  return params;
};

const rowDefs = [
  { key: "forecast", label: "計需" },
  { key: "firm", label: "実需" },
  { key: "plan", label: "計画" },
  { key: "actual", label: "実績" },
  { key: "adjust", label: "調整" },
  { key: "scrap", label: "仕損" },
  { key: "stock", label: "在庫" },
  { key: "planned_stock", label: "計庫" },
  { key: "progress", label: "進度" },
];

// 休日判定用のキャッシュ
const holidays = ref(new Set());
const holidayWorkDates = ref(new Set());
const lineCalendarMap = ref({});
const calendarDayCache = ref({});

const normalizeCalendarId = (calendarValue) => {
  if (calendarValue === null || calendarValue === undefined) return null;
  if (typeof calendarValue === "object") return calendarValue?.id ?? null;
  return calendarValue;
};

const isNonWorkingCalendarDay = (day) => {
  if (!day) return false;
  const isWorking = day.is_working_day;
  if (isWorking === false) return true;
  if (typeof isWorking === "string" && isWorking.toLowerCase() === "false") return true;
  return false;
};

const buildWeekendSet = () => {
  const set = new Set();
  columns.value.forEach((date) => {
    const d = parseISODate(date);
    if (!d || Number.isNaN(d.getTime())) return;
    const dow = d.getDay();
    if (dow === 0 || dow === 6) {
      set.add(formatISODate(d));
    }
  });
  return set;
};

const ensureLineList = async () => {
  if (lineList?.value?.length) return;
  try {
    const res = await api.lines.getLines({ page_size: 500 });
    lineList.value = res.data?.results || res.data || [];
  } catch (e) {
    console.error("ライン一覧の取得に失敗:", e);
  }
};

const ensureLineCalendars = async (lineIds) => {
  if (!Array.isArray(lineIds) || !lineIds.length) return lineCalendarMap.value;
  await ensureLineList();
  const map = { ...lineCalendarMap.value };
  (lineList.value || []).forEach((line) => {
    if (line?.id !== undefined && map[line.id] === undefined) {
      map[line.id] = normalizeCalendarId(line.calendar);
    }
  });
  const missing = lineIds.filter((id) => map[id] === undefined);
  if (missing.length) {
    await Promise.all(
      missing.map(async (id) => {
        try {
          const res = await api.lines.getLine(id);
          map[id] = normalizeCalendarId(res.data?.calendar);
        } catch (err) {
          console.error("ライン詳細の取得に失敗:", err);
          map[id] = null;
        }
      })
    );
  }
  lineCalendarMap.value = map;
  return map;
};

const loadCalendarDays = async (calendarId) => {
  if (!calendarId) return [];
  if (calendarDayCache.value[calendarId]) {
    return calendarDayCache.value[calendarId];
  }
  try {
    const res = await api.calendars.getCalendarDays(calendarId, { page_size: 5000 });
    const rows = res.data?.results || res.data || [];
    calendarDayCache.value[calendarId] = rows;
    return rows;
  } catch (e) {
    console.error("カレンダ日の取得に失敗:", e);
    return [];
  }
};

const resolveDaisoCalendarId = async () => {
  const pickDaiso = (rows) => {
    const list = rows || [];
    const exact = list.find((row) => String(row.calendar_code || "").trim().toLowerCase() === "daiso");
    if (exact) return exact;
    return list.find((row) => {
      const code = String(row.calendar_code || "").trim().toLowerCase();
      const name = String(row.calendar_name || "").trim().toLowerCase();
      return code.includes("daiso") || name.includes("daiso") || name.includes("ダイソウ");
    });
  };
  try {
    const res = await api.calendars.getCalendars({ search: 'daiso', page_size: 200 });
    const rows = res.data?.results || res.data || [];
    let daiso = pickDaiso(rows);
    if (!daiso) {
      const fallbackRes = await api.calendars.getCalendars({ page_size: 5000 });
      const fallbackRows = fallbackRes.data?.results || fallbackRes.data || [];
      daiso = pickDaiso(fallbackRows);
    }
    return daiso?.id || null;
  } catch (e) {
    console.error('DAISOカレンダ取得エラー', e);
    return null;
  }
};

const updateHolidays = async () => {
  if (!columns.value.length) {
    holidays.value = new Set();
    return;
  }
  const start = columns.value[0];
  const end = columns.value[columns.value.length - 1];
  const fallback = buildWeekendSet();

  try {
    const lineIds = getDisplayedLineIds();
    const calendarMap = await ensureLineCalendars(lineIds);
    const calendarIds = Array.from(
      new Set(
        lineIds
          .map((id) => normalizeCalendarId(calendarMap?.[id]))
          .filter((id) => id !== null && id !== undefined)
      )
    );
    // ライン専用カレンダが無い場合はDAISOカレンダをフォールバック
    if (!calendarIds.length) {
      const daisoId = await resolveDaisoCalendarId();
      if (daisoId) calendarIds.push(daisoId);
    }
    if (!calendarIds.length) {
      holidays.value = fallback;
      return;
    }

    const holidaySet = new Set();
    const hwDates = new Set();
    for (const calendarId of calendarIds) {
      const days = await loadCalendarDays(calendarId);
      days.forEach((day) => {
        const dateStr = day.target_date;
        if (!dateStr) return;
        if (dateStr < start || dateStr > end) return;
        if (day.is_holiday_work) {
          hwDates.add(dateStr);
        } else if (isNonWorkingCalendarDay(day)) {
          holidaySet.add(dateStr);
        }
      });
    }
    holidays.value = holidaySet.size ? holidaySet : fallback;
    holidayWorkDates.value = hwDates;
  } catch (e) {
    console.error("休日判定の更新に失敗:", e);
    holidays.value = fallback;
  }
};

const isHoliday = (dateStr) => holidays.value.has(dateStr);
const isHolidayWork = (dateStr) => holidayWorkDates.value.has(dateStr);

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

const isHiddenStCoproductParent = (row) => {
  const code = String(row?.product_code || "").trim().toUpperCase();
  return Boolean(row?.is_virtual_set) && code.startsWith("ST");
};

const reloadDemands = async () => {
  const res = await api.lineBacklogs.getLineBacklogs(getBacklogParams());
  const payload = res.data || [];
  applyDemands(payload);
  await updateHolidays();
};

const groups = computed(() => {
  if (!demands.value.length) return [];
  const filtered = demands.value.filter((d) => {
    if (isHiddenStCoproductParent(d)) return false;
    const within =
      d.plan_date >= columns.value[0] &&
      d.plan_date <= columns.value[columns.value.length - 1];
    const lineCode = (d.line_code || "").toLowerCase();
    const lineName = (d.line_name || "").toLowerCase();
    const processCodeRaw = d.process_code === "PURCHASE" ? (d.supplier_code || d.line_code || d.process_code || "") : (d.process_code || "");
    const processNameRaw = d.process_code === "PURCHASE" ? (d.supplier_name || d.line_name || d.process_name || "") : (d.process_name || "");
    const processCodeLower = processCodeRaw.toLowerCase();
    const processNameLower = processNameRaw.toLowerCase();
    const prodText = `${d.product_code || ""}${d.product_name || ""}`.toLowerCase();
    const filterLower = lineFilter.value ? lineFilter.value.trim().toLowerCase() : "";
    const okLine =
      !filterLower ||
      lineCode === filterLower ||
      lineName.includes(filterLower);
    const processFilterLower = processFilter.value ? processFilter.value.trim().toLowerCase() : "";
    const okProcess =
      !processFilterLower ||
      processCodeLower === processFilterLower ||
      processNameLower.includes(processFilterLower);
    const okProd =
      !productFilter.value ||
      prodText.includes(productFilter.value.trim().toLowerCase());
    return within && okLine && okProcess && okProd;
  });

  const map = new Map();
  for (const d of filtered) {
    const key = `${d.line || d.line_name || ""}__${d.process_code || d.process || ""}__${d.product_code || ""}`;
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
          supplier_code: d.supplier_code || (d.process_code === "PURCHASE" ? (d.line_code || "") : ""),
          supplier_name: d.supplier_name || (d.process_code === "PURCHASE" ? (d.line_name || "") : ""),
          special_display_order: specialDisplayOrder,
          total_lt_days: null,
          self_lt_days: null,
          cells: {},
        });
      }
      const g = map.get(key);
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
      if (!g.supplier_code && d.supplier_code) g.supplier_code = d.supplier_code;
      if (!g.supplier_name && d.supplier_name) g.supplier_name = d.supplier_name;
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
    // 計需は需要行のみ採用（計画行は除外）
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
    // 実需:
    // - 最終品: 需要行の firm_order_qty を優先
    // - 中間品: sequence_no 最小行の actual_shipment_qty（後工程実績）を採用
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
    // 計画は全seq合算
    c.plan += Number(d.plan_qty || 0);
    // 実績: このラインの生産実績
    c.actual += Number(d.actual_qty || 0);
    c.adjust += Number(d.adjust_qty || 0); // 調整数
    c.scrap += Number(d.scrap_qty || 0); // 仕損数
    // 在庫・計画在庫・進度は仕様どおり最小sequence_no行のみ採用
    if (c.inventory_seq === undefined || seqVal < c.inventory_seq) {
      c.inventory_seq = seqVal;
      c.stock = Number(d.stock_qty || 0);
      c.planned_stock = Number(d.planned_stock_qty || 0);
      c.progress = Number(d.progress_qty || 0);
    } else if (seqVal === c.inventory_seq) {
      c.stock = Math.max(c.stock, Number(d.stock_qty || 0));
      c.planned_stock = Math.max(c.planned_stock, Number(d.planned_stock_qty || 0));
      c.progress = Math.max(c.progress, Number(d.progress_qty || 0));
    }
  }
  const result = Array.from(map.values());
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

const openWhereUsed = (group) => {
  if (!group.product_id) return
  window.open(`/masters/where-used?productId=${group.product_id}`, '_blank')
};

const isPurchaseProcessGroup = (group) => String(group?.process_code || "").toUpperCase() === "PURCHASE";

const normalizePurchaseSupplierName = (name) => {
  const raw = String(name || "").trim();
  if (!raw) return "";
  return raw.startsWith("仕入:") ? raw.slice(3).trim() : raw;
};

const getDisplayProcessName = (group) => {
  if (isPurchaseProcessGroup(group)) {
    const name = group?.supplier_name || group?.line_name || "";
    return normalizePurchaseSupplierName(name);
  }
  return group?.process_name || "";
};

const getDisplayProcessCode = (group) => {
  if (isPurchaseProcessGroup(group)) {
    return group?.supplier_code || group?.line_code || "";
  }
  return group?.process_code || "";
};

const monthKey = (dateStr) => String(dateStr || "").slice(0, 7);
const startMonthKey = computed(() => monthKey(startDate.value));

const getMonthTotal = (group, key) => {
  const targetMonth = startMonthKey.value;
  if (!targetMonth || !group?.cells) return 0;
  let total = 0;
  Object.keys(group.cells).forEach((date) => {
    if (monthKey(date) !== targetMonth) return;
    total += Number(group.cells?.[date]?.[key] || 0);
  });
  return total;
};

const getValue = (group, date, key) => {
  return group.cells?.[date]?.[key] ?? "";
};

const getCellClass = (group, date, rowKey) => {
  // 在庫・計画在庫・進度がマイナスの場合は赤色表示
  if (rowKey === 'stock' || rowKey === 'planned_stock' || rowKey === 'progress') {
    const value = getValue(group, date, rowKey);
    if (value !== null && value !== undefined && Number(value) < 0) {
      return 'negative';
    }
  }
  return '';
};

const adjustKey = (group, date) => `${group.key}__${date}`;

const getAdjustInputValue = (group, date) => {
  const key = adjustKey(group, date);
  if (Object.prototype.hasOwnProperty.call(adjustInputs.value, key)) {
    return adjustInputs.value[key];
  }
  const current = getValue(group, date, 'adjust');
  if (current === null || current === undefined) return '';
  const num = Number(current);
  if (Number.isNaN(num) || num === 0) return '';
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
  const idx = demands.value.findIndex(
    (d) =>
      d.line === group.line_id &&
      d.process === group.process_id &&
      d.product === group.product_id &&
      d.plan_date === date
  );
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
    alert('調整の保存に必要な情報が不足しています。');
    return;
  }
  const key = adjustKey(group, date);
  if (adjustSaving.value[key]) return;
  const raw = adjustInputs.value[key];
  let adjustQty = 0;
  if (raw !== '' && raw !== null && raw !== undefined) {
    const parsed = Number(raw);
    if (Number.isNaN(parsed) || !Number.isFinite(parsed)) {
      alert('調整数は数値で入力してください。');
      return;
    }
    if (!Number.isInteger(parsed)) {
      alert('調整数は整数で入力してください。');
      return;
    }
    adjustQty = parsed;
  }
  const current = Number(getValue(group, date, 'adjust') || 0);
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
    console.error('調整の保存に失敗:', e);
    alert(e?.response?.data?.detail || '調整の保存に失敗しました。');
  } finally {
    delete adjustSaving.value[key];
  }
};

// 表示中のグループからラインIDを取得
const getDisplayedLineIds = () => {
  return [...new Set(groups.value.map((g) => g.line_id).filter(Boolean))];
};

const getDisplayedLineTargets = () => {
  const map = new Map();
  groups.value.forEach((group) => {
    if (!group.line_id || !group.product_id) return;
    if (!map.has(group.line_id)) {
      map.set(group.line_id, {
        line_id: group.line_id,
        line_code: group.line_code || "",
        product_ids: new Set(),
        product_codes: new Set(),
      });
    }
    const entry = map.get(group.line_id);
    entry.product_ids.add(group.product_id);
    if (group.product_code) {
      entry.product_codes.add(group.product_code);
    }
  });
  return Array.from(map.values()).map((entry) => ({
    line_id: entry.line_id,
    line_code: entry.line_code,
    product_ids: Array.from(entry.product_ids).sort((a, b) => a - b),
    product_codes: Array.from(entry.product_codes).sort(),
  }));
};

const buildVisibleProductConfirmMessage = (targets) => {
  const allCodes = targets.flatMap((target) => target.product_codes);
  const preview = allCodes.slice(0, 10).join(", ");
  const suffix = allCodes.length > 10 ? ` ほか${allCodes.length - 10}件` : "";
  return `表示中の${allCodes.length}件を再計算しますか？\n${preview}${suffix}`;
};

const refreshOrderQty = async (lineIds) => {
  if (!lineIds.length) return false;

  const start = columns.value[0];
  const end = columns.value[columns.value.length - 1];

  // 並列実行
  await Promise.all(
    lineIds.map((lineId) =>
      api.lineBacklogs.pickup({
        line_id: lineId,
        start_date: start,
        end_date: end,
      }).catch((e) => console.error('需要再計算に失敗:', e))
    )
  );
  return true;
};

const refreshScrapQty = async (lineIds) => {
  if (!lineIds.length) return false;

  const start = columns.value[0];
  const end = columns.value[columns.value.length - 1];

  // 並列実行
  await Promise.all(
    lineIds.map((lineId) =>
      api.lineBacklogs.recalculateScrap({
        line_id: lineId,
        start_date: start,
        end_date: end,
      }).catch((e) => console.error('仕損再計算に失敗:', e))
    )
  );
  return true;
};

const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    const res = await api.lineBacklogs.getLineBacklogs(getBacklogParams());
    const payload = res.data || [];
    applyDemands(payload);
    await updateHolidays();
  } catch (e) {
    error.value = e?.message || "読み込みに失敗しました";
  } finally {
    loading.value = false;
  }
};

const recalculating = ref(false);

const recalculate = async () => {
  const lineIds = getDisplayedLineIds();
  if (lineIds.length === 0) {
    alert("再計算対象のラインがありません。先にデータを取得してください。");
    return;
  }

  recalculating.value = true;
  error.value = "";
  try {
    const start = columns.value[0];
    const end = columns.value[columns.value.length - 1];

    // 1. 需要再計算（pickup）- 並列実行
    await refreshOrderQty(lineIds);

    // 2. 仕損再計算 - 並列実行
    await refreshScrapQty(lineIds);

    // 3. 在庫再計算 - 並列実行
    await Promise.all(
      lineIds.map((lineId) =>
        api.lineBacklogs.recalculateInventory({
          line_id: lineId,
          start_date: start,
          end_date: end,
        }).catch((e) => {
          if (e?.response?.data?.code === 'LINE_CALENDAR_MISSING') {
            alert(e.response.data.detail);
          }
          console.error('在庫再計算に失敗:', e);
        })
      )
    );

    // 4. 最新データを再取得
    const finalRes = await api.lineBacklogs.getLineBacklogs(getBacklogParams());
    applyDemands(finalRes.data || []);
    await updateHolidays();
  } catch (e) {
    error.value = e?.message || "再計算に失敗しました";
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
    const targets = getDisplayedLineTargets();
    if (targets.length === 0) {
      alert("ライン情報が見つかりません。先にデータを取得してください。");
      return;
    }
    await Promise.all(
      targets.map((target) =>
        api.lineBacklogs.recalculateInventoryDeep({
          line_id: target.line_id,
          start_date: start,
          end_date: end,
          product_ids: target.product_ids,
        })
      )
    );
    const finalRes = await api.lineBacklogs.getLineBacklogs(getBacklogParams());
    applyDemands(finalRes.data || []);
    await updateHolidays();
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || "過去から再計算に失敗しました";
  } finally {
    recalculating.value = false;
  }
};

const recalculateVisibleProducts = async () => {
  const targets = getDisplayedLineTargets();
  if (targets.length === 0) {
    alert("再計算対象の品番がありません。");
    return;
  }
  if (!confirm(buildVisibleProductConfirmMessage(targets))) {
    return;
  }

  recalculating.value = true;
  error.value = "";
  try {
    const start = columns.value[0];
    const end = columns.value[columns.value.length - 1];

    await Promise.all(
      targets.map((target) =>
        api.lineBacklogs.pickupForProducts({
          line_id: target.line_id,
          start_date: start,
          end_date: end,
          product_ids: target.product_ids,
        })
      )
    );

    await Promise.all(
      targets.map((target) =>
        api.lineBacklogs.recalculateScrapForProducts({
          line_id: target.line_id,
          start_date: start,
          end_date: end,
          product_ids: target.product_ids,
        })
      )
    );

    await Promise.all(
      targets.map((target) =>
        api.lineBacklogs.recalculateInventoryForProducts({
          line_id: target.line_id,
          start_date: start,
          end_date: end,
          product_ids: target.product_ids,
        })
      )
    );

    const finalRes = await api.lineBacklogs.getLineBacklogs(getBacklogParams());
    applyDemands(finalRes.data || []);
    await updateHolidays();
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || "表示品番の再計算に失敗しました";
  } finally {
    recalculating.value = false;
  }
};

// ライン・工程コード参照用
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
      api.lines.getLines({ page_size: 500 }),
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

const openCodeLookup = async () => {
  if (showCodeLookup.value) return;
  await fetchCodeLookupData();
  showCodeLookup.value = true;
};

const closeCodeLookup = () => {
  showCodeLookup.value = false;
  codeSearch.value = "";
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

const applyLine = (line) => {
  lineFilter.value = line.line_code || "";
  showCodeLookup.value = false;
};

const applyProcess = (process) => {
  processFilter.value = process.process_code || "";
  showCodeLookup.value = false;
};

// F4押下でコード一覧を表示（修飾キーなしのみ）
const handleKeyDown = (e) => {
  if (e.key === "F4" && !e.altKey && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
    e.preventDefault();
    openCodeLookup();
  }
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

onMounted(() => {
  window.addEventListener("keydown", handleKeyDown);
  window.addEventListener("resize", onWindowResize);
  nextTick(updateFloatingScroll);
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", handleKeyDown);
  window.removeEventListener("resize", onWindowResize);
});

onUpdated(() => {
  nextTick(updateFloatingScroll);
});

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
  const start = columns.value[0] || '';
  const end = columns.value[columns.value.length - 1] || '';

  const bom = '\ufeff';
  const lines = [];
  const filterLabel = [
    lineFilter.value ? `ライン:${lineFilter.value}` : '',
    processFilter.value ? `工程:${processFilter.value}` : '',
    productFilter.value ? `品番:${productFilter.value}` : '',
  ].filter(Boolean).join(' / ') || '（フィルタなし）';
  lines.push([escapeCsv('フィルタ'), escapeCsv(filterLabel)].join(','));
  lines.push([escapeCsv('期間'), escapeCsv(`${start} ～ ${end}`)].join(','));
  lines.push('');

  const headerRow = ['ライン', '工程コード', '工程名', '品番', '品名', '項目', ...columns.value.map(formatDateSlash)];
  lines.push(headerRow.map(escapeCsv).join(','));

  for (const g of groups.value) {
    rowDefs.forEach((row, idx) => {
      const isFirst = idx === 0;
      const lineLabel = isFirst ? (`${g.line_code || ''}${g.line_name ? ' ' + g.line_name : ''}`.trim()) : '';
      const cells = [
        lineLabel,
        isFirst ? getDisplayProcessCode(g) : '',
        isFirst ? getDisplayProcessName(g) : '',
        isFirst ? (g.product_code || '') : '',
        isFirst ? (g.product_name || '') : '',
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
  const filterSuffix = [lineFilter.value, processFilter.value, productFilter.value]
    .filter(Boolean).join('_') || 'all';
  link.href = url;
  link.download = `在庫残量一覧_${filterSuffix}_${start}_${end}.csv`;
  link.click();
  URL.revokeObjectURL(url);
};

// 画面を開いた時点ではデータを取得せず、フィルター入力後に更新ボタンで取得
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
.day-col {
  min-width: 54px !important;
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
.matrix-table thead th.holiday-work {
  background: #fde68a;
  color: #92400e;
}
.cell.holiday-work {
  background: #fef3c7;
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
.deep-recalc-modal {
  width: min(520px, 92vw);
}
.deep-recalc-body {
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
