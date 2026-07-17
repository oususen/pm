<template>
  <div class="adjust-screen">
    <div class="caption">[SSE0030] {{ title }} <DataSourceDialog :title="title" :sources="dsSources" /></div>
    <div class="toolbar">
      <label class="toolbar-field">
        <span>実行日</span>
        <input v-model="adjustDate" type="date" />
      </label>
      <label v-if="activeTab === 'single'" class="toolbar-field">
        <span>調整対象日</span>
        <input
          v-model="adjustmentDate"
          type="date"
          :title="form.productId ? '調整したい日を選択してください。表示開始日は品番LTから自動計算されます' : '調整したい日を選択してください'"
          @change="handleSingleAdjustmentDateChange"
        />
      </label>
    </div>

    <div class="tabs">
      <button class="tab" :class="{ active: activeTab === 'single' }" type="button" @click="activeTab = 'single'">個別</button>
      <button class="tab" :class="{ active: activeTab === 'batch' }" type="button" @click="activeTab = 'batch'">一括</button>
    </div>

    <!-- 個別タブ -->
    <div class="main" v-if="activeTab === 'single'">
      <section class="left-pane">
        <div class="panel">
          <div class="row">
            <label>品番</label>
            <input
              v-model="form.productCode"
              type="text"
              @keyup.enter="resolveByProductCode"
            />
          </div>
          <div class="row"><label>品名</label><input v-model="form.productName" type="text" /></div>
          <div class="row"><label>部品番号</label><input v-model="form.partNo" type="text" /></div>
        </div>

        <div class="panel">
          <div class="panel-title">工程情報</div>
          <div class="process-list-wrap" v-if="processCandidates.length">
            <table class="process-list">
              <thead>
                <tr>
                  <th>工程順位</th>
                  <th>工程CD</th>
                  <th>工程名</th>
                  <th>ラインCD</th>
                  <th>ライン名</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="item in processCandidates"
                  :key="item.key"
                  :class="{ selected: selectedProcessKey === item.key }"
                  @click="selectProcessCandidate(item)"
                >
                  <td>{{ item.stepNo }}</td>
                  <td>{{ item.processCode }}</td>
                  <td>{{ item.processName }}</td>
                  <td>{{ item.lineCode }}</td>
                  <td>{{ item.lineName }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="row row-3">
            <label>工程順位</label>
            <input v-model="form.processOrder" type="number" />
            <input v-model="form.processCode" type="text" placeholder="工程CD" />
          </div>
          <div class="row">
            <label>工程名</label>
            <input v-model="form.processName" type="text" />
          </div>
          <div class="row">
            <label>ラインCD</label>
            <input v-model="form.lineCode" type="text" placeholder="ラインCD" />
          </div>
          <div class="row">
            <label>ライン名</label>
            <input v-model="form.lineName" type="text" />
          </div>
          <div class="row">
            <label>表示開始日</label>
            <input
              v-model="displayStartDate"
              type="date"
              :max="adjustmentDate"
              @change="reload"
            />
          </div>
          <!-- 補正ガイド（STOCK / PROGRESS タイプ）-->
          <div v-if="isGuideType && form.productId && form.lineId" class="stock-helper">
            <div class="sh-title">{{ guideTitle }}</div>
            <ol class="sh-steps">
              <li>
                <span>{{ guideStep1Label }}</span>
                <button type="button" class="btn btn-step" @click="recalcThenReload" :disabled="adjustWorking">
                  {{ adjustWorking ? '処理中...' : guideStep1Btn }}
                </button>
              </li>
              <li>
                <span>{{ guideStep2Label }}</span>
                <div class="sh-fields">
                  <div class="row">
                    <label>{{ guideSystemLabel }}</label>
                    <span class="sh-value">{{ systemStockToday !== null ? systemStockToday : '—' }}</span>
                  </div>
                  <div class="row">
                    <label>{{ guideActualLabel }}</label>
                    <input v-model.number="actualStockToday" type="number" :placeholder="guideActualPlaceholder" />
                  </div>
                  <div class="row">
                    <label>差分（調整値）</label>
                    <span class="sh-value" :class="{ negative: stockDiff < 0 }">
                      {{ stockDiff !== null ? (stockDiff >= 0 ? '+' : '') + stockDiff : '—' }}
                    </span>
                  </div>
                </div>
              </li>
              <li>
                <span>{{ guideStep3Label }}</span>
                <button type="button" class="btn btn-step btn-step-final" @click="applyAndRecalc" :disabled="stockDiff === null || adjustWorking">
                  {{ adjustWorking ? '処理中...' : guideApplyBtn }}
                </button>
              </li>
            </ol>
          </div>

          <div class="adjust-note">
            <p>※ 調整対象日は手入力で選択します。表示開始日は調整対象日と品番のリードタイムから自動計算されます。</p>
            <template v-if="props.adjustType === 'STOCK'">
              <p>※ 在庫は日々累積で繰り越されるため、調整対象日に値を入れることで以降の全日に反映されます。</p>
              <p>※ 在庫補正の正しい手順：<strong>在庫再計算 → 実在庫入力 → 調整保存 → 再計算</strong>（上記ガイドを使用）。</p>
            </template>
            <template v-else-if="props.adjustType === 'PLANNED_STOCK'">
              <p>※ 計画在庫は日々累積で繰り越されるため、調整対象日に値を入れることで以降の全日に反映されます。</p>
              <p>※ 計画在庫補正の正しい手順：<strong>計画在庫再計算 → 実計画在庫入力 → 調整保存 → 再計算</strong>（上記ガイドを使用）。</p>
            </template>
            <template v-else-if="props.adjustType === 'PROGRESS'">
              <p>※ 進度は日々累積で繰り越されるため、調整対象日に値を入れることで以降の全日に反映されます。</p>
              <p>※ 進度補正の正しい手順：<strong>進度再計算 → 実進度入力 → 調整保存 → 再計算</strong>（上記ガイドを使用）。</p>
            </template>
            <p>※ 調整値は「調整マスタ（production_line_backlog_adjustment）」に保存されます。再計算のたびに読み込まれ、{{ reflectionLabel }}に反映され続けます。</p>
          </div>
        </div>
      </section>

      <section class="right-pane">
        <table class="grid">
          <thead>
            <tr>
              <th>日付</th>
              <th>{{ forecastHeaderLabel }}</th>
              <th>{{ firmHeaderLabel }}</th>
              <th>{{ inboundHeaderLabel }}</th>
              <th v-if="showPlanColumn">{{ planHeaderLabel }}</th>
              <th>{{ adjustHeaderLabel }}</th>
              <th v-if="showStockColumn">在庫</th>
              <th>{{ currentAdjustHeaderLabel }}</th>
              <th>{{ metricHeaderLabel }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td :colspan="showPlanColumn ? (showStockColumn ? 9 : 8) : (showStockColumn ? 8 : 7)" class="center">読込中...</td>
            </tr>
            <tr v-for="row in dateRows" :key="row.date" :class="{ holiday: isHoliday(row.date) }">
              <td :class="{ holidayText: isHoliday(row.date) }">{{ row.date }}</td>
              <td>{{ row.plan }}</td>
              <td>{{ row.firm }}</td>
              <td>{{ row.inbound }}</td>
              <td v-if="showPlanColumn">{{ row.planQty }}</td>
              <td>{{ row.adjust }}</td>
              <td v-if="showStockColumn">{{ row.stock != null ? row.stock : '-' }}</td>
              <td>
                <input
                  class="qty-input"
                  type="number"
                  :value="row.currentAdjust"
                  :readonly="row.date !== adjustmentDate"
                  :class="{ 'qty-input-locked': row.date !== adjustmentDate }"
                  @input="row.date === adjustmentDate && onAdjustInput(row.date, $event)"
                />
              </td>
              <td :class="{ negative: row.progress < 0 }">{{ row.progress }}</td>
            </tr>
          </tbody>
        </table>

        <div class="actions">
          <button
            v-if="!(isGuideType && form.productId && form.lineId)"
            class="btn primary" type="button" @click="saveCurrentDate"
          >登録</button>
          <button class="btn" type="button" @click="reload">再読込</button>
        </div>
      </section>
    </div>

    <!-- 一括タブ -->
    <div class="batch-pane" v-if="activeTab === 'batch'">
      <div class="batch-toolbar">
        <div class="batch-search-mode">
          <label><input type="radio" v-model="batchSearchMode" value="process" /> 工程CD</label>
          <label><input type="radio" v-model="batchSearchMode" value="line" /> ラインCD</label>
        </div>
        <div class="row" style="max-width:260px">
          <label>調整対象日</label>
          <input
            v-model="batchTargetDate"
            type="date"
            @change="handleBatchTargetDateChange"
          />
        </div>
        <div class="row" style="max-width:400px">
          <label>{{ batchSearchMode === 'process' ? '工程CD' : 'ラインCD' }}</label>
          <input
            v-model="batchSearchCode"
            type="text"
            :placeholder="batchSearchMode === 'process' ? '工程コードを入力' : 'ラインコードを入力'"
            @keyup.enter="loadBatchProducts"
          />
        </div>
        <button class="btn" type="button" @click="batchRecalcThenReload" :disabled="batchWorking || !batchSearchCode">
          ① {{ guideStep1Btn }}
        </button>
        <button class="btn primary" type="button" @click="batchApplyAndRecalc" :disabled="batchWorking || !batchProducts.length || !hasBatchDiff">
          ② {{ guideApplyBtn }}
        </button>
      </div>

      <div v-if="batchWorking" class="center">処理中...</div>
      <div v-else-if="batchError" class="center" style="color:#c00">{{ batchError }}</div>
      <div v-else-if="batchLineInfo">
        <p class="batch-line-name">{{ batchInfoLabel }}</p>
        <p class="batch-guide">調整対象日: {{ batchTargetDate }}。{{ batchGuideActualLabel }}を入力すると差分が自動計算されます。② ボタンで一括保存・再計算されます。</p>
        <table class="grid">
          <thead>
            <tr>
              <th>品番</th>
              <th>品名</th>
              <th>ライン</th>
              <th v-if="batchSearchMode === 'line'">工程CD</th>
              <th>調整対象日</th>
              <th>現在調整値</th>
              <th>{{ batchGuideSystemLabel }}</th>
              <th>{{ batchGuideActualLabel }}</th>
              <th>差分（調整値）</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!batchProducts.length">
              <td :colspan="batchSearchMode === 'line' ? 9 : 8" class="center">品番が見つかりません</td>
            </tr>
            <tr v-for="(row, idx) in batchProducts" :key="`${row.product_id}-${row.line_id}`">
              <td>{{ row.product_code }}</td>
              <td>{{ row.product_name }}</td>
              <td>{{ row.line_code }}</td>
              <td v-if="batchSearchMode === 'line'">{{ row.process_code || '-' }}</td>
              <td>{{ row.target_date || row.calc_start_date }}</td>
              <td>{{ row.adjust_qty }}</td>
              <td>{{ row.value_today !== null && row.value_today !== undefined ? row.value_today : '—' }}</td>
              <td>
                <input
                  class="qty-input"
                  type="number"
                  v-model.number="batchActualInputs[idx]"
                  :placeholder="guideActualPlaceholder"
                />
              </td>
              <td :class="{ negative: batchDiff(row, idx) < 0 }">
                {{ batchDiff(row, idx) !== null ? (batchDiff(row, idx) >= 0 ? '+' : '') + batchDiff(row, idx) : '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatISODate } from '@/utils/dateUtil'
import { onMounted, reactive, ref, computed } from "vue";
import api from "@/api/client";
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const props = defineProps({
  title: { type: String, default: "生産進度調整入力" },
  description: { type: String, default: "" },
  adjustType: { type: String, required: true },
});

const dsSources = computed(() => {
  const descMap = {
    STOCK: '在庫調整値',
    PLANNED_STOCK: '計画在庫調整値',
    PROGRESS: '進度調整値',
    PLANNED_PROGRESS: '計画進度調整値',
  }
  const desc = descMap[props.adjustType] || '調整値'
  return [
    { op: '読み書き', table: 'production_line_backlog_adjustment', desc },
    { op: '読み取り', table: 'line_backlog', desc: '在庫・進度・計画データ参照' },
    { op: '読み取り', table: 't_line_demand', desc: '需要データ参照' },
  ]
})

const today = formatISODate(new Date());
const adjustDate = ref(today);
const displayStartDate = ref(today);
const adjustmentDate = ref(today); // LTから自動計算される調整可能日（この行だけ入力可）
const activeTab = ref("single");

// 在庫差分ヘルパー（STOCKタイプのみ）
const systemStockToday = ref(null);
const actualStockToday = ref(null);
const adjustWorking = ref(false);
const stockDiff = computed(() =>
  actualStockToday.value !== null && systemStockToday.value !== null
    ? actualStockToday.value - systemStockToday.value
    : null
);

const previewDiff = () => {};

const applyStockDiff = () => {
  if (stockDiff.value === null) return;
  dateRows.value = dateRows.value.map((row) =>
    row.date === adjustmentDate.value
      ? { ...row, currentAdjust: stockDiff.value }
      : row
  );
  applyProgressPreview();
};

// ① 在庫再計算してリロード
const recalcThenReload = async () => {
  if (!form.lineId) return;
  adjustWorking.value = true;
  try {
    const endDateObj = new Date(displayStartDate.value || today);
    endDateObj.setDate(endDateObj.getDate() + 29);
    await api.lineBacklogs.recalculateInventory({
      line_id: form.lineId,
      start_date: displayStartDate.value || today,
      end_date: formatISODate(endDateObj),
      product_ids: form.productId ? [form.productId] : undefined,
    });
    await reload();
  } catch (e) {
    alert(e?.response?.data?.detail || '在庫再計算に失敗しました');
  } finally {
    adjustWorking.value = false;
  }
};

// ③ 差分を調整対象日に適用して保存 → 再計算 → リロード
const applyAndRecalc = async () => {
  if (stockDiff.value === null || !form.lineId) return;
  adjustWorking.value = true;
  try {
    // 既存の調整値に今回の差分を加算（上書きではなく累積）
    const existingAdjust = rowsByDate.value[adjustmentDate.value] || 0;
    const totalAdjust = existingAdjust + stockDiff.value;
    // グリッドに反映
    dateRows.value = dateRows.value.map((row) =>
      row.date === adjustmentDate.value
        ? { ...row, currentAdjust: totalAdjust }
        : row
    );
    applyProgressPreview();
    // 調整マスタに保存（累積値で上書き）
    await api.lineBacklogAdjustments.save({
      line_code: form.lineCode,
      product_code: form.productCode,
      process_code: form.processCode || '',
      plan_date: adjustmentDate.value,
      adjust_type: props.adjustType,
      adjust_qty: totalAdjust,
      reason: `${props.adjustType} ${guideReasonPrefix}（${guideActualWord}${actualStockToday.value} − システム${systemStockToday.value}、累計${totalAdjust}）`,
    });
    // 再計算して反映
    const endDateObj = new Date(displayStartDate.value || today);
    endDateObj.setDate(endDateObj.getDate() + 29);
    await api.lineBacklogs.recalculateInventory({
      line_id: form.lineId,
      start_date: displayStartDate.value || today,
      end_date: formatISODate(endDateObj),
      product_ids: form.productId ? [form.productId] : undefined,
    });
    actualStockToday.value = null;
    await reload();
  } catch (e) {
    alert(e?.response?.data?.detail || '処理に失敗しました');
  } finally {
    adjustWorking.value = false;
  }
};

// 一括タブ用
const batchSearchMode = ref("process");
const batchSearchCode = ref("");
const batchTargetDate = ref(today);
const batchProcessCode = computed(() => batchSearchMode.value === 'process' ? batchSearchCode.value : '');
const batchLineCode = computed(() => batchSearchMode.value === 'line' ? batchSearchCode.value : '');
const batchLineInfo = ref(null);
const batchProducts = ref([]);
const batchActualInputs = ref({});  // 実在庫入力 {index: number}
const batchWorking = ref(false);
const batchError = ref("");
const batchInfoLabel = computed(() => {
  const info = batchLineInfo.value;
  if (!info) return '';
  if (batchSearchMode.value === 'line') {
    return `${info.line_code} — ${info.line_name}`;
  }
  return `${info.process_code} — ${info.process_name}`;
});

// 行ごとの差分（実測値 - システム値）。同一品番が複数ラインに存在しうるためindexで管理
const batchDiff = (row, idx) => {
  const actual = batchActualInputs.value[idx];
  if (actual === null || actual === undefined || actual === '') return null;
  if (row.value_today === null || row.value_today === undefined) return null;
  return actual - row.value_today;
};

// 1件以上差分が入力されているか
const hasBatchDiff = computed(() =>
  batchProducts.value.some((row, idx) => batchDiff(row, idx) !== null)
);
const loading = ref(false);
const resolvingProduct = ref(false);
const rowsByDate = ref({});
const metricsByDate = ref({});
const holidays = ref(new Set());
const dateRows = ref([]);
const processCandidates = ref([]);
const selectedProcessKey = ref("");
const lineCodeIdCache = ref(new Map());
const processCodeIdCache = ref(new Map());

const form = reactive({
  productId: null,
  productCode: "",
  productName: "",
  partNo: "",
  processOrder: 10,
  processId: null,
  processCode: "",
  processName: "",
  lineId: null,
  lineCode: "",
  lineName: "",
});

const applyProcessToForm = (item) => {
  selectedProcessKey.value = item.key;
  form.processOrder = Number(item.stepNo || 10);
  form.processId = item.processId || null;
  form.processCode = item.processCode || "";
  form.processName = item.processName || "";
  form.lineId = item.lineId || null;
  form.lineCode = item.lineCode || "";
  form.lineName = item.lineName || "";
};

const syncSingleDisplayStartDate = async (productId) => {
  if (!productId) return;
  try {
    const calcRes = await api.lineBacklogs.getCalcStartDate({
      product_id: productId,
      base_date: adjustmentDate.value,
    });
    if (calcRes.data?.calc_start_date) {
      displayStartDate.value = calcRes.data.calc_start_date;
    }
  } catch (_) {
    // 表示開始日は取得失敗時に現状維持
  }
};

const selectProcessCandidate = async (item) => {
  applyProcessToForm(item);
  await reload();
};

const setProcessCandidates = (items = []) => {
  processCandidates.value = items;
  if (!items.length) {
    selectedProcessKey.value = "";
    form.processOrder = 10;
    form.processId = null;
    form.processCode = "";
    form.processName = "";
    form.lineId = null;
    form.lineCode = "";
    form.lineName = "";
    return;
  }
  if (items.length === 1) {
    applyProcessToForm(items[0]);
    return;
  }
  selectedProcessKey.value = "";
  form.processOrder = 10;
  form.processId = null;
  form.processCode = "";
  form.processName = "";
  form.lineId = null;
  form.lineCode = "";
  form.lineName = "";
};

const resolveLineIdByCode = async (lineCode) => {
  const code = String(lineCode || "").trim();
  if (!code) return null;
  if (lineCodeIdCache.value.has(code)) return lineCodeIdCache.value.get(code);
  try {
    const res = await api.lines.getLines({ page_size: 500 });
    const rows = normalizeList(res.data);
    const matched = rows.find((row) => String(row.line_code || "").trim() === code);
    const id = matched?.id || null;
    lineCodeIdCache.value.set(code, id);
    return id;
  } catch (e) {
    return null;
  }
};

const resolveProcessIdByCode = async (processCode) => {
  const code = String(processCode || "").trim();
  if (!code) return null;
  if (processCodeIdCache.value.has(code)) return processCodeIdCache.value.get(code);
  try {
    const res = await api.processes.getProcesses({ search: code, page_size: 100 });
    const rows = normalizeList(res.data);
    const matched = rows.find((row) => String(row.process_code || "").trim() === code);
    const id = matched?.id || null;
    processCodeIdCache.value.set(code, id);
    return id;
  } catch (e) {
    return null;
  }
};

const buildRows = () => {
  const start = new Date(displayStartDate.value || today);
  const rows = [];
  for (let i = 0; i < 30; i += 1) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    const key = formatISODate(d);
    const saved = rowsByDate.value[key] || 0;
    const metrics = metricsByDate.value[key] || {};
    rows.push({
      date: key,
      plan: Number(metrics.plan || 0),
      firm: Number(metrics.firm || 0),
      inbound: Number(metrics.inbound || 0),
      planQty: Number(metrics.planQty || 0),
      adjust: saved,
      currentAdjust: saved,
      progress: Number(metrics.progress || 0),
      baseProgress: Number(metrics.progress || 0),
      stock: metrics.stock != null ? Number(metrics.stock) : null,
    });
  }
  dateRows.value = rows;
  applyProgressPreview();
};

const normalizeList = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
};

const isWeekend = (dateStr) => {
  const d = new Date(dateStr);
  const day = d.getDay();
  return day === 0 || day === 6;
};

const isHoliday = (dateStr) => holidays.value.has(dateStr) || isWeekend(dateStr);

const loadHolidays = async (startDate, endDate) => {
  const fallback = new Set();
  const start = new Date(startDate);
  const end = new Date(endDate);
  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    const key = formatISODate(d);
    if (isWeekend(key)) fallback.add(key);
  }
  try {
    const res = await api.calendars.getCalendars({ search: "daiso", page_size: 1 });
    const rows = Array.isArray(res.data?.results) ? res.data.results : Array.isArray(res.data) ? res.data : [];
    const daisoCalendar = rows.find((row) => String(row.calendar_code || "").toLowerCase() === "daiso");
    if (!daisoCalendar?.id) {
      holidays.value = fallback;
      return;
    }
    const daysRes = await api.calendars.getCalendarDays(daisoCalendar.id, { page_size: 5000 });
    const days = Array.isArray(daysRes.data?.results) ? daysRes.data.results : Array.isArray(daysRes.data) ? daysRes.data : [];
    const displayedDateSet = new Set();
    for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
      displayedDateSet.add(formatISODate(d));
    }
    const holidaySet = new Set(
      days
        .filter((day) => day?.is_working_day === false && displayedDateSet.has(day.target_date))
        .map((day) => day.target_date)
    );
    holidays.value = holidaySet.size > 0 ? new Set([...fallback, ...holidaySet]) : fallback;
  } catch (e) {
    holidays.value = fallback;
  }
};

const resolveByProductCode = async () => {
  const productCode = String(form.productCode || "").trim();
  if (!productCode || resolvingProduct.value) return;
  const normalizedInputCode = productCode.toUpperCase();

  resolvingProduct.value = true;
  try {
    const productRes = await api.products.getProducts({ search: productCode, page_size: 20 });
    const products = normalizeList(productRes.data);
    const normalizeCode = (value) => String(value || "").trim().toUpperCase();
    const product =
      products.find((p) => normalizeCode(p.product_code) === normalizedInputCode) ||
      products.find((p) => normalizeCode(p.product_code).startsWith(normalizedInputCode)) ||
      products[0];

    if (!product) {
      alert("品番に該当する製品が見つかりません。");
      form.productId = null;
      form.productName = "";
      form.partNo = "";
      processCandidates.value = [];
      selectedProcessKey.value = "";
      adjustmentDate.value = today;
      systemStockToday.value = null;
      actualStockToday.value = null;
      return;
    }

    form.productCode = product.product_code || productCode;
    form.productName = product.product_name || "";
    form.partNo = product.product_code || "";
    form.productId = product.id || null;
    processCandidates.value = [];
    selectedProcessKey.value = "";

    // 表示開始日は「調整対象日 + 品番LT」を基準に再計算する。調整対象日は上書きしない。
    await syncSingleDisplayStartDate(product.id);

    // 購入品/外作部品はBOMの調達区分を優先して候補化する
    const allBomItemRes = await api.bomItems.getBOMItems({
      child_product: product.id,
      page_size: 100,
    });
    const allBomItems = normalizeList(allBomItemRes.data);
    const purchaseLike = allBomItems.filter(
      (item) => ["BUY", "SUBCON"].includes(String(item.sourcing_type || "").toUpperCase()) || !!item.supplier
    );
    if (purchaseLike.length) {
      const withMaster = await Promise.all(
        purchaseLike.map(async (item, idx) => {
          let processCode = "";
          let processName = "";
          let lineCode = "";
          let lineName = "";
          if (item.process) {
            const processRes = await api.processes.getProcess(item.process);
            processCode = processRes?.data?.process_code || "";
            processName = processRes?.data?.process_name || "";
          }
          if (item.line) {
            const lineRes = await api.lines.getLine(item.line);
            lineCode = lineRes?.data?.line_code || "";
            lineName = lineRes?.data?.line_name || "";
          }
          if (item.supplier) {
            const supplierRes = await api.suppliers.getSupplier(item.supplier);
            const supplierCode = supplierRes?.data?.supplier_code || "";
            const supplierName = supplierRes?.data?.supplier_name || "";
            if (!lineCode) lineCode = supplierCode;
            if (!lineName) lineName = supplierName;
          }
          return {
            key: `${processCode || item.process || ""}::${lineCode || item.line || ""}::${idx}`,
            stepNo: 10 + idx,
            processId: item.process || null,
            processCode: processCode || (String(item.sourcing_type || "").toUpperCase() === "BUY" ? "PURCHASE" : ""),
            processName: processName || (String(item.sourcing_type || "").toUpperCase() === "BUY" ? "購買" : ""),
            lineId: item.line || null,
            lineCode,
            lineName,
          };
        })
      );
      const valid = withMaster.filter((x) => x.processCode || x.lineCode || x.lineName);
      // process + line の組み合わせで重複排除
      const seen = new Set();
      const unique = valid.filter((x) => {
        const k = `${x.processId || x.processCode}::${x.lineId || x.lineCode}`;
        if (seen.has(k)) return false;
        seen.add(k);
        return true;
      });
      if (unique.length) {
        setProcessCandidates(unique);
        if (unique.length > 1) {
          metricsByDate.value = {};
          rowsByDate.value = {};
          buildRows();
          alert("この品番は複数工程があります。左側一覧から調整したい工程を選択してください。");
          return;
        }
        await reload();
        return;
      }
    }

    const routingRes = await api.routings.getRoutings({
      product: product.id,
      is_active: true,
      is_default: true,
    });
    let routings = normalizeList(routingRes.data);
    if (!routings.length) {
      const fallbackRes = await api.routings.getRoutings({ product: product.id, is_active: true });
      routings = normalizeList(fallbackRes.data);
    }
    const routing = routings[0];

    if (!routing?.id) {
      const bomItemRes = await api.bomItems.getBOMItems({
        child_product: product.id,
        sourcing_type: "MAKE",
        page_size: 20,
      });
      const bomItems = normalizeList(bomItemRes.data);
      const withMaster = await Promise.all(
        bomItems.map(async (item) => {
          let processCode = "";
          let processName = "";
          let lineCode = "";
          let lineName = "";
          if (item.process) {
            const processRes = await api.processes.getProcess(item.process);
            processCode = processRes?.data?.process_code || "";
            processName = processRes?.data?.process_name || "";
          }
          if (item.line) {
            const lineRes = await api.lines.getLine(item.line);
            lineCode = lineRes?.data?.line_code || "";
            lineName = lineRes?.data?.line_name || "";
          }
          return {
            ...item,
            processCode,
            processName,
            lineCode,
            lineName,
            key: `${processCode}::${lineCode}`,
          };
        })
      );
      const valid = withMaster.filter((x) => x.processCode || x.lineCode);
      const uniqueMap = new Map();
      valid.forEach((x) => {
        if (!uniqueMap.has(x.key)) uniqueMap.set(x.key, x);
      });
      const uniqueCandidates = Array.from(uniqueMap.values()).map((x, idx) => ({
        key: x.key,
        // BOM明細には工程順位が無いことがあるため、IDを順位として流用しない
        stepNo: Number(x.step_no || 10 + idx),
        processId: x.process || null,
        processCode: x.processCode || "",
        processName: x.processName || "",
        lineId: x.line || null,
        lineCode: x.lineCode || "",
        lineName: x.lineName || "",
      }));
      uniqueCandidates.sort(
        (a, b) =>
          a.stepNo - b.stepNo ||
          String(a.processCode || "").localeCompare(String(b.processCode || "")) ||
          String(a.lineCode || "").localeCompare(String(b.lineCode || ""))
      );
      setProcessCandidates(uniqueCandidates);
      if (uniqueCandidates.length > 1) {
        alert("この部番は複数工程があります。左側一覧から調整したい工程を選択してください。");
      }

      if (product.process) {
        const processRes = await api.processes.getProcess(product.process);
        if (!form.processId) form.processId = processRes?.data?.id || null;
        if (!form.processCode) form.processCode = processRes?.data?.process_code || "";
        if (!form.processName) form.processName = processRes?.data?.process_name || "";
      }
      if (product.line) {
        const lineRes = await api.lines.getLine(product.line);
        if (!form.lineId) form.lineId = lineRes?.data?.id || null;
        if (!form.lineCode) form.lineCode = lineRes?.data?.line_code || "";
        if (!form.lineName) form.lineName = lineRes?.data?.line_name || "";
      }
      await reload();
      return;
    }

    const stepRes = await api.routings.getRoutingSteps({ routing: routing.id, page_size: 5000 });
    const steps = normalizeList(stepRes.data)
      .filter((step) => Number(step.output_product || 0) === Number(product.id))
      .sort((a, b) => Number(a.step_no || 0) - Number(b.step_no || 0));
    const candidateRows = [];
    for (const step of steps) {
      let processCode = "";
      let processName = "";
      let lineCode = "";
      let lineName = "";
      if (step.process) {
        const processRes = await api.processes.getProcess(step.process);
        processCode = processRes?.data?.process_code || "";
        processName = processRes?.data?.process_name || "";
      }
      if (step.line) {
        const lineRes = await api.lines.getLine(step.line);
        lineCode = lineRes?.data?.line_code || "";
        lineName = lineRes?.data?.line_name || "";
      }
      candidateRows.push({
        key: `${step.process || ""}::${step.line || ""}::${step.step_no || 0}`,
        stepNo: Number(step.step_no || 0),
        processId: step.process || null,
        processCode,
        processName,
        lineId: step.line || null,
        lineCode,
        lineName,
      });
    }
    const uniq = new Map();
    candidateRows.forEach((x) => {
      if (!uniq.has(x.key)) uniq.set(x.key, x);
    });
    setProcessCandidates(Array.from(uniq.values()).sort((a, b) => a.stepNo - b.stepNo));
    if (processCandidates.value.length > 1) {
      metricsByDate.value = {};
      rowsByDate.value = {};
      buildRows();
      alert("この品番は複数工程があります。左側一覧から調整したい工程を選択してください。");
      return;
    }

    await reload();
  } catch (e) {
    alert(e?.response?.data?.detail || "品番情報の取得に失敗しました。");
  } finally {
    resolvingProduct.value = false;
  }
};

const handleSingleAdjustmentDateChange = async () => {
  if (form.productId) {
    await syncSingleDisplayStartDate(form.productId);
  }
  await reload();
};

const getMetricValueForType = (item) => {
  if (props.adjustType === "STOCK") return Number(item.stock_qty || 0);
  if (props.adjustType === "PLANNED_STOCK") return Number(item.planned_stock_qty || 0);
  if (props.adjustType === "PLANNED_PROGRESS") return Number(item.planned_progress_qty || 0);
  return Number(item.progress_qty || 0);
};

const isStockType = props.adjustType === "STOCK" || props.adjustType === "PLANNED_STOCK";
const showStockColumn = props.adjustType === "PLANNED_STOCK";
const isPlannedProgressType = props.adjustType === "PLANNED_PROGRESS";
const isProgressType = props.adjustType === "PROGRESS";
const showPlanColumn = isStockType || isPlannedProgressType || isProgressType;
const forecastHeaderLabel = isStockType ? "計需" : "内示";
const firmHeaderLabel = isStockType ? "実需" : "確定";
const inboundHeaderLabel = "実績";
const planHeaderLabel = "計画";
const adjustHeaderLabel = "調整値";
const currentAdjustHeaderLabel = "今回調整値";
const metricHeaderLabel =
  props.adjustType === "STOCK"
    ? "在庫"
    : props.adjustType === "PLANNED_STOCK"
    ? "計画在庫"
    : props.adjustType === "PLANNED_PROGRESS"
    ? "計画進度"
    : "進度";
const recalculationLabel =
  props.adjustType === "STOCK" || props.adjustType === "PLANNED_STOCK" ? "在庫再計算" : "進度再計算";
const reflectionLabel =
  props.adjustType === "STOCK"
    ? "在庫"
    : props.adjustType === "PLANNED_STOCK"
    ? "計画在庫"
    : props.adjustType === "PLANNED_PROGRESS"
    ? "計画進度"
    : "進度";

// 補正ガイドを表示するタイプ（STOCK / PROGRESS / PLANNED_STOCK）
const isGuideType = props.adjustType === "STOCK" || props.adjustType === "PROGRESS" || props.adjustType === "PLANNED_STOCK";
const _guideWord =
  props.adjustType === "STOCK" ? "在庫"
  : props.adjustType === "PLANNED_STOCK" ? "計画在庫"
  : "進度";
const guideTitle = `${_guideWord}補正ガイド`;
const guideStep1Label = `① ${_guideWord}を最新化`;
const guideStep1Btn = `${_guideWord}再計算して確認`;
const guideSystemLabel = computed(() => `システム${_guideWord}（${adjustmentDate.value}）`);
const guideActualLabel = computed(() => (
  props.adjustType === "STOCK"
    ? `実在庫（${adjustmentDate.value}）`
    : props.adjustType === "PLANNED_STOCK"
    ? `実計画在庫（${adjustmentDate.value}）`
    : `実進度（${adjustmentDate.value}）`
));
const batchGuideSystemLabel = computed(() => `システム${_guideWord}（${batchTargetDate.value}）`);
const batchGuideActualLabel = computed(() => (
  props.adjustType === "STOCK"
    ? `実在庫（${batchTargetDate.value}）`
    : props.adjustType === "PLANNED_STOCK"
    ? `実計画在庫（${batchTargetDate.value}）`
    : `実進度（${batchTargetDate.value}）`
));
const guideActualPlaceholder = props.adjustType === "PROGRESS" ? "実績値を入力" : "実測値を入力";
const guideStep2Label = props.adjustType === "STOCK" ? "② 実在庫を入力して差分を確認" : props.adjustType === "PLANNED_STOCK" ? "② 実計画在庫を入力して差分を確認" : "② 実進度を入力して差分を確認";
const guideStep3Label = "③ 差分を調整対象日に適用して再計算";
const guideApplyBtn = "調整を保存して再計算";
const guideReasonPrefix = `${_guideWord}補正`;
const guideActualWord = props.adjustType === "STOCK" ? "実在庫" : props.adjustType === "PLANNED_STOCK" ? "実計画在庫" : "実進度";

const reload = async () => {
  loading.value = true;
  try {
    if (form.productId && processCandidates.value.length > 1 && !form.processId) {
      metricsByDate.value = {};
      systemStockToday.value = null;
      return;
    }
    if (!form.lineId && form.lineCode) {
      form.lineId = await resolveLineIdByCode(form.lineCode);
    }
    if (!form.processId && form.processCode) {
      form.processId = await resolveProcessIdByCode(form.processCode);
    }

    const res = await api.lineBacklogAdjustments.list({
      adjust_type: props.adjustType,
      line_code: form.lineCode || undefined,
      product_code: form.productCode || undefined,
      process_code: form.processCode || undefined,
    });
    const map = {};
    const items = Array.isArray(res.data) ? res.data : [];
    items.forEach((item) => {
      map[item.plan_date] = Number(item.adjust_qty || 0);
    });
    rowsByDate.value = map;

    const startDate = displayStartDate.value || today;
    const endDateObj = new Date(startDate);
    endDateObj.setDate(endDateObj.getDate() + 29);
    const endDate = formatISODate(endDateObj);
    await loadHolidays(startDate, endDate);

    if (form.lineId && form.productId) {
      const backlogParams = {
        line: form.lineId,
        product: form.productId,
        process: form.processId || undefined,
        plan_date__gte: startDate,
        plan_date__lte: endDate,
      };
      const demandParams = {
        line: form.lineId,
        product: form.productId,
        plan_date__gte: startDate,
        plan_date__lte: endDate,
        page_size: 5000,
      };
      if (form.processCode) {
        demandParams.process_search = form.processCode;
      }
      const [backlogRes, demandRes] = await Promise.all([
        api.lineBacklogs.getLineBacklogs(backlogParams),
        api.lineDemands.list(demandParams),
      ]);
      const backlogItems = Array.isArray(backlogRes.data) ? backlogRes.data : [];
      const demandItems = normalizeList(demandRes.data).filter(
        (item) => !form.processId || Number(item.process || 0) === Number(form.processId)
      );
      const metricMap = {};
      // LineBacklogから実績・計画・進度・在庫を取得
      backlogItems.forEach((item) => {
        const key = item.plan_date;
        if (!metricMap[key]) {
          metricMap[key] = { plan: 0, firm: 0, inbound: 0, planQty: 0, progress: 0 };
        }
        metricMap[key].inbound += Number(item.actual_qty || 0);
        metricMap[key].planQty += Number(item.plan_qty || 0);
        metricMap[key].progress += getMetricValueForType(item);
        metricMap[key].stock = Number(item.stock_qty || 0);
      });
      // LineDemandから内示・確定を取得
      demandItems.forEach((item) => {
        const key = item.plan_date;
        if (!metricMap[key]) {
          metricMap[key] = { plan: 0, firm: 0, inbound: 0, planQty: 0, progress: 0 };
        }
        metricMap[key].plan += Number(item.forecast_qty || 0);
        metricMap[key].firm += Number(item.firm_qty || 0);
      });
      metricsByDate.value = metricMap;

      // 調整対象日のシステム値を取得（STOCK: stock_qty, PROGRESS: progress_qty）
      if (isGuideType) {
        const targetDate = adjustmentDate.value || today;
        if (metricMap[targetDate]?.progress !== undefined) {
          systemStockToday.value = metricMap[targetDate].progress;
        } else {
          // 調整対象日がグリッド範囲外 → 単独で取得
          try {
            const todayRes = await api.lineBacklogs.getLineBacklogs({
              line: form.lineId,
              product: form.productId,
              plan_date__gte: targetDate,
              plan_date__lte: targetDate,
            });
            const todayItems = Array.isArray(todayRes.data) ? todayRes.data : [];
            const todayVal = todayItems.reduce((sum, item) => sum + getMetricValueForType(item), 0);
            systemStockToday.value = todayItems.length ? todayVal : null;
          } catch (_) {
            systemStockToday.value = null;
          }
        }
      }
    } else {
      metricsByDate.value = {};
      systemStockToday.value = null;
    }
  } finally {
    buildRows();
    loading.value = false;
  }
};

const onAdjustInput = (date, event) => {
  const value = Number(event.target.value || 0);
  // 入力中の行を保存対象日に自動同期する
  adjustDate.value = date;
  dateRows.value = dateRows.value.map((row) =>
    row.date === date ? { ...row, currentAdjust: value } : row
  );
  applyProgressPreview();
};

const applyProgressPreview = () => {
  const sorted = [...dateRows.value].sort((a, b) => String(a.date).localeCompare(String(b.date)));
  let carry = 0;
  const map = new Map();
  sorted.forEach((row) => {
    const delta = Number(row.currentAdjust || 0) - Number(row.adjust || 0);
    carry += delta;
    map.set(row.date, Number(row.baseProgress || 0) + carry);
  });
  dateRows.value = dateRows.value.map((row) => ({
    ...row,
    progress: map.get(row.date) ?? Number(row.baseProgress || 0),
  }));
};

const saveCurrentDate = async () => {
  if (!form.lineCode || !form.productCode || !adjustmentDate.value) {
    alert("ラインCD・品番・調整日を入力してください。");
    return;
  }
  const target = dateRows.value.find((row) => row.date === adjustmentDate.value);
  const adjustQty = Number(target?.currentAdjust || 0);
  try {
    await api.lineBacklogAdjustments.save({
      line_code: form.lineCode,
      product_code: form.productCode,
      process_code: form.processCode || "",
      plan_date: adjustmentDate.value,
      adjust_type: props.adjustType,
      adjust_qty: adjustQty,
      reason: `${props.adjustType} UI入力`,
    });
    await reload();
  } catch (e) {
    alert(e?.response?.data?.detail || "保存に失敗しました。");
  }
};

const loadBatchProducts = async () => {
  if (!batchSearchCode.value) return;
  batchWorking.value = true;
  batchError.value = "";
  batchLineInfo.value = null;
  batchProducts.value = [];
  batchActualInputs.value = {};
  try {
    const params = { adjust_type: props.adjustType };
    if (batchSearchMode.value === 'line') {
      params.line_code = batchSearchCode.value;
    } else {
      params.process_code = batchSearchCode.value;
    }
    params.target_date = batchTargetDate.value;
    const res = await api.lineBacklogs.getBatchAdjustInfo(params);
    batchLineInfo.value = res.data;
    batchProducts.value = res.data.products || [];
  } catch (e) {
    batchError.value = e?.response?.data?.detail || "取得に失敗しました";
  } finally {
    batchWorking.value = false;
  }
};

const handleBatchTargetDateChange = async () => {
  batchActualInputs.value = {};
  if (batchSearchCode.value) {
    await loadBatchProducts();
  }
};

const getBatchRecalcRange = () => {
  const startDate = batchTargetDate.value || today;
  const startDateObj = new Date(startDate);
  const todayPlus30Obj = new Date(today);
  todayPlus30Obj.setDate(todayPlus30Obj.getDate() + 30);
  const endDateObj = startDateObj > todayPlus30Obj ? new Date(startDateObj) : todayPlus30Obj;
  if (startDateObj > todayPlus30Obj) {
    endDateObj.setDate(endDateObj.getDate() + 30);
  }
  return {
    startDate,
    endDate: formatISODate(endDateObj),
  };
};

// 一括再計算の共通ロジック
// - PROGRESS/PLANNED_PROGRESS: 工程の製品をline_idでグループ化して進度のみ再計算
// - STOCK/PLANNED_STOCK: 全関連ラインを対象に在庫のみ再計算（進度スキップ）
const executeBatchRecalc = async () => {
  const { startDate, endDate } = getBatchRecalcRange();

  const isProgressType = props.adjustType === "PROGRESS" || props.adjustType === "PLANNED_PROGRESS";

  if (isProgressType) {
    // 工程の製品だけを line_id でグループ化して進度のみ再計算
    const productsByLine = {};
    for (const p of batchProducts.value) {
      if (!productsByLine[p.line_id]) productsByLine[p.line_id] = [];
      productsByLine[p.line_id].push(p.product_id);
    }
    await Promise.all(
      Object.entries(productsByLine).map(([lid, pids]) =>
        api.lineBacklogs.recalculateInventory({
          line_id: Number(lid),
          start_date: startDate,
          end_date: endDate,
          product_ids: pids,
          progress_only: true,
        })
      )
    );
  } else {
    // 在庫系: 工程の対象品のみ、line_idでグループ化して在庫のみ再計算（進度スキップ）
    const productsByLine = {};
    for (const p of batchProducts.value) {
      if (!productsByLine[p.line_id]) productsByLine[p.line_id] = [];
      productsByLine[p.line_id].push(p.product_id);
    }
    await Promise.all(
      Object.entries(productsByLine).map(([lid, pids]) =>
        api.lineBacklogs.recalculateInventory({
          line_id: Number(lid),
          start_date: startDate,
          end_date: endDate,
          product_ids: pids,
          include_progress: false,
        })
      )
    );
  }
};

// ① 在庫/進度再計算 → 品番リスト再取得
const batchRecalcThenReload = async () => {
  if (!batchSearchCode.value) return;
  batchWorking.value = true;
  batchError.value = "";
  try {
    await executeBatchRecalc();
    await loadBatchProducts();
  } catch (e) {
    batchError.value = e?.response?.data?.detail || "再計算に失敗しました";
    batchWorking.value = false;
  }
};

// ② 差分を累積保存 → 再計算 → 再取得
const batchApplyAndRecalc = async () => {
  if (!batchProducts.value.length) return;
  batchWorking.value = true;
  batchError.value = "";
  try {
    await Promise.all(
      batchProducts.value.map((row, idx) => {
        const diff = batchDiff(row, idx);
        if (diff === null) return Promise.resolve();
        const totalAdjust = (row.adjust_qty || 0) + diff;
        return api.lineBacklogAdjustments.save({
          line_code: row.line_code,
          product_code: row.product_code,
          process_code: row.process_code || batchProcessCode.value,
          plan_date: row.target_date || batchTargetDate.value,
          adjust_type: props.adjustType,
          adjust_qty: totalAdjust,
          reason: `${props.adjustType} 一括${guideReasonPrefix}（${guideActualWord}${batchActualInputs.value[idx]} − システム${row.value_today}、累計${totalAdjust}）`,
        }).catch((e) => console.error('一括保存エラー:', row.product_code, e));
      })
    );
    await executeBatchRecalc();
    batchActualInputs.value = {};
    await loadBatchProducts();
  } catch (e) {
    batchError.value = e?.response?.data?.detail || "処理に失敗しました";
    batchWorking.value = false;
  }
};

onMounted(() => {
  buildRows();
  reload();
});
</script>

<style scoped>
.adjust-screen {
  padding: 8px 10px;
  background: #cfd2d3;
  min-height: 100%;
  color: #111;
  font-size: 12px;
}
.caption {
  margin-bottom: 6px;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.toolbar-field {
  display: flex;
  align-items: center;
  gap: 6px;
}
.toolbar-field span {
  background: #4f6f82;
  color: #fff;
  padding: 4px 10px;
}
.tabs {
  border-bottom: 1px solid #9aa3a9;
  margin-bottom: 8px;
}
.tab {
  border: 1px solid #9aa3a9;
  border-bottom: none;
  background: #d6d6d6;
  padding: 4px 10px;
  margin-right: 4px;
}
.tab.active {
  background: #efefef;
}
.main {
  display: grid;
  grid-template-columns: 45% 55%;
  gap: 10px;
}
.left-pane {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.panel {
  background: #bfc1c2;
  border: 1px solid #8d9498;
  padding: 8px;
}
.panel-title {
  background: #4f6f82;
  color: #fff;
  padding: 3px 8px;
  margin: -8px -8px 8px;
}
.process-list-wrap {
  max-height: 120px;
  overflow: auto;
  border: 1px solid #8d9498;
  margin-bottom: 6px;
}
.process-list {
  width: 100%;
  border-collapse: collapse;
}
.process-list th,
.process-list td {
  border: 1px solid #8a8f92;
  padding: 2px 4px;
  background: #ecebd2;
}
.process-list thead th {
  background: #4f6f82;
  color: #fff;
}
.process-list tbody tr {
  cursor: pointer;
}
.process-list tbody tr.selected td {
  background: #cbe8ff;
}
.row {
  display: grid;
  grid-template-columns: 80px 1fr;
  gap: 4px;
  margin-bottom: 4px;
}
.row.row-3 {
  grid-template-columns: 80px 70px 1fr;
}
.row label {
  background: #4f6f82;
  color: #fff;
  text-align: center;
  padding: 3px;
}
.adjust-note {
  margin-top: 8px;
  border: 1px solid #8d9498;
  background: #ecebd2;
  padding: 6px 8px;
  line-height: 1.5;
}
.adjust-note p {
  margin: 0;
}
.row input,
.toolbar input,
.toolbar select {
  border: 1px solid #7d868b;
  background: #f4efc8;
  padding: 2px 4px;
}
.grid {
  width: 100%;
  border-collapse: collapse;
  background: #d4d4d4;
}
.grid th {
  background: #4f6f82;
  color: #fff;
  border: 1px solid #7d868b;
  padding: 3px 4px;
}
.grid td {
  border: 1px solid #8a8f92;
  padding: 2px 4px;
  background: #efeec7;
}
.grid tr.holiday td {
  background: #ffe6e6;
}
.holidayText {
  color: #d60000;
  font-weight: 700;
}
.qty-input {
  width: 100%;
  border: 1px solid #7d868b;
  background: #d6f4f7;
}
.qty-input-locked {
  background: #e8e8e8;
  color: #888;
  cursor: not-allowed;
}
.stock-helper {
  margin-top: 8px;
  border: 1px solid #5a8fa8;
  background: #e8f4fb;
  padding: 8px;
}
.sh-title {
  font-weight: bold;
  color: #1f3a4e;
  margin-bottom: 6px;
  font-size: 11px;
  letter-spacing: 0.05em;
}
.sh-steps {
  margin: 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 11px;
}
.sh-steps li {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.sh-fields {
  padding-left: 4px;
}
.sh-value {
  font-weight: bold;
  padding: 2px 4px;
}
.btn-step {
  align-self: flex-start;
  background: #e5e5e5;
  color: #111;
  border: 1px solid #6d7478;
  padding: 3px 10px;
  cursor: pointer;
  font-size: 11px;
  &:disabled { opacity: 0.4; cursor: not-allowed; }
}
.btn-step-final {
  background: #d7f0ff;
}
.negative {
  color: #ff2d2d;
  font-weight: 700;
}
.actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}
.btn {
  border: 1px solid #6d7478;
  background: #e5e5e5;
  padding: 4px 10px;
}
.btn.primary {
  background: #d7f0ff;
}
.center {
  text-align: center;
}
.batch-pane {
  padding: 8px;
}
.batch-toolbar {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.batch-search-mode {
  display: flex;
  gap: 12px;
  align-items: center;
  font-size: 13px;
  padding-bottom: 4px;
}
.batch-search-mode label {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 3px;
}
.batch-line-name {
  margin: 0 0 6px;
  font-weight: bold;
  color: #1f3a4e;
}
.batch-guide {
  margin: 0 0 8px;
  color: #444;
  font-size: 11px;
}
@media (max-width: 900px) {
  .main {
    grid-template-columns: 1fr;
  }
}
</style>
