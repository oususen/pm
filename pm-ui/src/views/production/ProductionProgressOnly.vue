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
        <button
          @click="recalculateVisibleProducts"
          :disabled="loading || recalculating || !hasFilter || !groups.length"
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
          :disabled="loading || recalculating || !hasFilter || !groups.length"
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
          <h3>過去から進度を再計算</h3>
          <button class="close-btn" type="button" @click="showDeepRecalcDialog = false">×</button>
        </div>
        <div class="code-modal-body deep-recalc-body">
          <p>
            表示開始日（<strong>{{ startDate }}</strong>）を基準に、ルーティング/BOM由来LTで算出した開始日から進度を再計算します。
          </p>
          <ul>
            <li>対象ライン: <strong>{{ getDisplayedLineIds().join(', ') }}</strong></li>
            <li>計算範囲: {{ startDate }} 〜 {{ columns[columns.length - 1] }}</li>
            <li>在庫は再計算せず、進度のみ更新します。</li>
            <li>データ量によっては完了まで時間がかかる場合があります。</li>
          </ul>
          <p class="deep-recalc-danger">※ 過去の日の実績を入力した後にのみ実行してください。<br>表示開始日を実績入力日の一番古い日にしてください。<br>むやみに実行すると在庫・進度データが不整合になる恐れがあります。</p>
          <p class="deep-recalc-warn">※ 各品番のLT算出結果（calc_start_date）の最古日を開始日に採用します。</p>
          <div class="deep-recalc-actions">
            <button type="button" @click="showDeepRecalcDialog = false">キャンセル</button>
            <button type="button" class="btn-confirm-deep" @click="confirmDeepRecalc">実行</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="status">読込中...</div>
    <div v-else-if="recalculating" class="status">再計算中...</div>
    <div v-else-if="error" class="status error">エラー: {{ error }}</div>
    <div v-else-if="!hasFilter" class="status">ライン、工程、または品番を入力してください</div>
    <div v-else>
      <div v-if="groups.length" class="group-scroll" ref="groupScrollRef" @scroll="onMainScroll">
        <div class="group-list">
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
              <button @click="openWhereUsed(g)" class="expand-btn where-used-btn">▶ 逆展開</button>
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
                      class="cell" :class="getCellClass(g, d, row.key)"
                    >
                      {{ fmt(getValue(g, d, row.key), row.showZero) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="status">データがありません</div>
    </div>
    <div
      v-if="groups.length"
      class="floating-x-scroll"
      ref="floatingScrollRef"
      @scroll="onFloatingScroll"
    >
      <div class="floating-x-scroll-inner" :style="{ width: `${floatingInnerWidth}px` }"></div>
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

const props = defineProps({
  mode: {
    type: String,
    default: "production",
  },
});

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
const purchaseTargetProductIds = ref([]);
const holidays = ref(new Set());
const lineCalendarMap = ref({});
const calendarDayCache = ref({});
const groupScrollRef = ref(null);
const floatingScrollRef = ref(null);
const floatingInnerWidth = ref(0);
let syncingScroll = false;
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

const formatDayHeader = (dateStr) => {
  if (!dateStr) return "";
  const d = parseISODate(dateStr);
  if (!d || Number.isNaN(d.getTime())) return dateStr;
  const m = d.getMonth() + 1;
  const day = d.getDate();
  return `${m}/${day}`;
};

const rowDefs = [
  { key: "forecast", label: "内示" },
  { key: "firm", label: "確定" },
  { key: "plan", label: "計画" },
  { key: "actual", label: "実績" },
  { key: "adjust", label: "調整" },
  { key: "plannedProgress", label: "計進", showZero: true },
  { key: "progress", label: "進度", showZero: true },
];

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

const resolvePurchaseCompatibleProductIds = async () => {
  const keyword = String(lineFilter.value || "").trim();
  if (!keyword) return [];

  const [supplierRes, lineRes] = await Promise.all([
    api.suppliers.getSuppliers({ page_size: 5000 }),
    api.lines.getLines({ page_size: 5000 }),
  ]);
  const supplierRows = normalizeList(supplierRes.data || []);
  const lineRows = normalizeList(lineRes.data || []);

  const matchedSuppliers = supplierRows.filter((s) => {
    const code = String(s.supplier_code || "").toLowerCase();
    const name = String(s.supplier_name || "").toLowerCase();
    const kw = keyword.toLowerCase();
    return code.includes(kw) || name.includes(kw);
  });

  const matchedLineIds = new Set(
    lineRows
      .filter((l) => {
        const code = String(l.line_code || "").toLowerCase();
        const name = String(l.line_name || "").toLowerCase();
        const kw = keyword.toLowerCase();
        return code.includes(kw) || name.includes(kw);
      })
      .map((l) => l.id)
      .filter((id) => Number.isFinite(Number(id)))
  );

  matchedSuppliers.forEach((supplier) => {
    const line = lineRows.find(
      (l) => String(l.line_code || "").trim() === String(supplier.supplier_code || "").trim()
    );
    if (line?.id) matchedLineIds.add(line.id);
  });

  const requests = [];
  matchedSuppliers.forEach((supplier) => {
    requests.push(api.routings.getRoutingSteps({ supplier: supplier.id, page_size: 5000 }));
  });
  matchedLineIds.forEach((lineId) => {
    requests.push(api.routings.getRoutingSteps({ line: lineId, page_size: 5000 }));
  });

  if (!requests.length) return [];
  const responses = await Promise.all(requests);
  const ids = new Set();
  responses.forEach((res) => {
    const steps = normalizeList(res.data || []);
    steps.forEach((step) => {
      const outputProductId = Number(step.output_product);
      if (Number.isFinite(outputProductId) && outputProductId > 0) {
        ids.add(outputProductId);
      }
    });
  });
  return Array.from(ids).sort((a, b) => a - b);
};

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

const ensureLineList = async () => {
  if (lineList?.value?.length) return;
  try {
    const res = await api.lines.getLines();
    lineList.value = normalizeList(res.data || []);
  } catch (e) {
    console.error("ライン一覧の取得に失敗:", e);
  }
};

const resolveCalcStartDateForProducts = async (productIds, fallbackStartDate) => {
  if (!Array.isArray(productIds) || !productIds.length) return fallbackStartDate;
  try {
    const responses = await Promise.all(
      productIds.map((productId) => api.lineBacklogs.getCalcStartDate({ product_id: productId }))
    );
    const dates = responses
      .map((res) => res?.data?.calc_start_date)
      .filter((dateStr) => typeof dateStr === "string" && dateStr.length > 0);
    if (!dates.length) return fallbackStartDate;
    return dates.reduce((minDate, dateStr) => (dateStr < minDate ? dateStr : minDate), dates[0]);
  } catch (e) {
    console.error("calc_start_date取得に失敗:", e);
    return fallbackStartDate;
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
    const rows = normalizeList(res.data || []);
    calendarDayCache.value[calendarId] = rows;
    return rows;
  } catch (e) {
    console.error("カレンダ日の取得に失敗:", e);
    return [];
  }
};

const loadHolidayColumns = async () => {
  const fallback = buildWeekendFallback();
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
        if (daiso?.id) calendarIds.push(daiso.id);
      } catch (e) {
        console.error('DAISOカレンダ取得エラー', e);
      }
    }
    if (!calendarIds.length) {
      holidays.value = fallback;
      return;
    }

    const start = columns.value[0];
    const end = columns.value[columns.value.length - 1];
    // 積集合: 全カレンダで休日の日だけを休日にする
    let commonHolidays = null;
    for (const calendarId of calendarIds) {
      const dayRows = await loadCalendarDays(calendarId);
      const calHolidays = new Set();
      dayRows.forEach((day) => {
        const dateStr = day.target_date;
        if (!dateStr) return;
        if (dateStr < start || dateStr > end) return;
        if (isNonWorkingCalendarDay(day)) {
          calHolidays.add(dateStr);
        }
      });
      if (commonHolidays === null) {
        commonHolidays = calHolidays;
      } else {
        commonHolidays = new Set([...commonHolidays].filter((d) => calHolidays.has(d)));
      }
    }
    holidays.value = commonHolidays && commonHolidays.size ? commonHolidays : fallback;
  } catch (e) {
    console.error("休日判定の取得に失敗:", e);
    holidays.value = fallback;
  }
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
  if (props.mode === "purchase" && purchaseTargetProductIds.value.length) {
    params.product__in = purchaseTargetProductIds.value.join(",");
  }
  return params;
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
    if (props.mode === "purchase") {
      purchaseTargetProductIds.value = await resolvePurchaseCompatibleProductIds();
      if (lineFilter.value.trim() && purchaseTargetProductIds.value.length === 0) {
        backlogs.value = [];
        lineDemands.value = [];
        await loadHolidayColumns();
        return;
      }
    } else {
      purchaseTargetProductIds.value = [];
    }

    if (props.mode === "purchase" && hasFilter.value) {
      try {
        await api.lineBacklogs.seedProgressBacklogsFromDemand({
          start_date: columns.value[0],
          end_date: columns.value[columns.value.length - 1],
          line_search: lineFilter.value.trim(),
          process_search: processFilter.value.trim(),
          product_search: productFilter.value.trim(),
        });
      } catch (e) {
        console.error("進度表示用Backlog補完に失敗:", e);
      }
    }

    const demandParams = {
      plan_date__gte: columns.value[0],
      plan_date__lte: columns.value[columns.value.length - 1],
      page_size: 5000,
    };
    if (lineFilter.value.trim()) demandParams.line_search = lineFilter.value.trim();
    if (processFilter.value.trim()) demandParams.process_search = processFilter.value.trim();
    if (productFilter.value.trim()) demandParams.product_search = productFilter.value.trim();
    const [backlogRes, demandRes] = await Promise.all([
      api.lineBacklogs.getLineBacklogs(getBacklogParams()),
      api.lineDemands.list(demandParams),
    ]);
    applyBacklogs(backlogRes.data || []);
    const demandPayload = demandRes?.data || [];
    await loadHolidayColumns();
    let normalizedDemands = Array.isArray(demandPayload) ? demandPayload : demandPayload.results || [];
    if (props.mode === "purchase" && purchaseTargetProductIds.value.length) {
      const targetSet = new Set(purchaseTargetProductIds.value);
      normalizedDemands = normalizedDemands.filter((d) => targetSet.has(Number(d.product)));
    }
    lineDemands.value = normalizedDemands;
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

const recalculateVisibleProducts = async () => {
  const targets = getDisplayedLineTargets();
  if (!targets.length) {
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
        api.lineBacklogs.recalculateInventoryForProducts({
          line_id: target.line_id,
          start_date: start,
          end_date: end,
          include_progress: true,
          product_ids: target.product_ids,
        })
      )
    );
    await load();
  } catch (e) {
    console.error(e);
    error.value = e?.response?.data?.detail || e?.message || "表示品番の再計算に失敗しました";
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
    const targets = getDisplayedLineTargets();
    if (!targets.length) {
      alert("再計算対象の品番がありません。");
      return;
    }
    const end = columns.value[columns.value.length - 1];
    await Promise.all(
      targets.map((target) => {
        const productIds = Array.isArray(target.product_ids) ? target.product_ids : [];
        return resolveCalcStartDateForProducts(productIds, startDate.value).then((calcStartDate) => {
          const effectiveStart = calcStartDate < startDate.value ? calcStartDate : startDate.value;
          return api.lineBacklogs.recalculateInventoryDeep({
            line_id: target.line_id,
            start_date: effectiveStart,
            end_date: end,
            product_ids: target.product_ids,
            progress_only: true,
          }).catch((e) => console.error('過去から再計算に失敗:', target.line_id, e));
        }
        );
      })
    );
    await load();
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || "過去から再計算に失敗しました";
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

const createEmptyCell = () => ({
  forecast: 0,
  firm: 0,
  plan: 0,
  actual: 0,
  adjust: 0,
  progress: 0,
  plannedProgress: 0,
});

const isHiddenStCoproductParent = (row) => {
  const code = String(row?.product_code || "").trim().toUpperCase();
  return Boolean(row?.is_virtual_set) && code.startsWith("ST");
};

const groups = computed(() => {
  if (!backlogs.value.length) return [];
  const start = columns.value[0];
  const end = columns.value[columns.value.length - 1];
  const lineKeyword = lineFilter.value.trim().toLowerCase();
  const processKeyword = processFilter.value.trim().toLowerCase();
  const productKeyword = productFilter.value.trim().toLowerCase();

  const filtered = backlogs.value.filter((d) => {
    if (isHiddenStCoproductParent(d)) return false;
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
    if (isHiddenStCoproductParent(d)) return false;
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
    const specialDisplayOrder = resolveSpecialDisplayOrder(d);
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
        is_virtual_set: Boolean(d.is_virtual_set),
        special_display_order: specialDisplayOrder,
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
    if (d.is_virtual_set) g.is_virtual_set = true;
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

const formatLine = (group) => {
  const code = group.line_code || "";
  const name = group.line_name || "";
  if (code && name) return `${code} ${name}`;
  return code || name || "-";
};

const openWhereUsed = (group) => {
  if (!group.product_id) return
  window.open(`/masters/where-used?productId=${group.product_id}`, '_blank')
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

  // ヘッダー行
  const headerRow = ['ライン', '工程', '品番', '品名', '項目', ...columns.value.map(formatDateSlash)];
  lines.push(headerRow.map(escapeCsv).join(','));

  // データ行（ライン・工程・品番・品名は各グループの最初の行のみ出力）
  for (const g of groups.value) {
    rowDefs.forEach((row, idx) => {
      const isFirst = idx === 0;
      const cells = [
        isFirst ? (formatLine(g)) : '',
        isFirst ? (`${g.process_code || ''}${g.process_name ? ' ' + g.process_name : ''}`.trim()) : '',
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
  link.download = `進度のみ_${filterSuffix}_${start}_${end}.csv`;
  link.click();
  URL.revokeObjectURL(url);
};

const getCellClass = (group, date, rowKey) => {
  const val = Number(getValue(group, date, rowKey) || 0);
  const classes = [];
  if (isHoliday(date)) {
    classes.push("holiday");
  }
  if (rowKey === "adjust" && val < 0) classes.push("negative");
  if ((rowKey === "progress" || rowKey === "plannedProgress") && val < 0) classes.push("negative-strong");
  
  return classes.join(" ");
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
  border: 1px solid #e2e8f0;
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
  background: #fff;
}
.cell.negative:not(.holiday) {
  background: #fff2f2;
  color: #c53030;
  font-weight: 700;
}
.cell.negative-strong {
  background: #ffe4e6;
  color: #b91c1c;
  font-weight: 700;
}
.cell.holiday {
  background: #fff0f6;
}
.cell.holiday.negative {
  background: #ffe0e0; /* 休日かつマイナスの場合は少し濃い赤 */
  color: #c53030;
  font-weight: 700;
}
.cell.holiday.negative-strong {
  background: #ffc0c0;
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

