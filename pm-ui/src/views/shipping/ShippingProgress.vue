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
          v-model="productFilter"
          placeholder="品番/品名で絞り込み"
        />
        <input type="date" v-model="startDate" />
        <select v-model.number="horizon">
          <option :value="30">30日</option>
          <option :value="60">60日</option>
          <option :value="90">90日</option>
        </select>
        <button @click="load" :disabled="loading">更新</button>
      </div>
    </div>

    <div class="page-body">
      <div class="list-area">
        <div v-if="loading" class="loading">読込中...</div>
        <div v-else-if="error" class="no-data">エラー: {{ error }}</div>
        <div v-else>
          <div v-if="groups.length" class="group-list">
            <div v-for="g in pagedGroups" :key="g.key" class="group-card">
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
                <table class="matrix-table">
                  <thead>
                    <tr>
                      <th class="label-col">項目</th>
                      <th v-for="d in columns" :key="d" class="day-col">{{ formatDateHeader(d) }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <th class="label-col">内示</th>
                      <td
                        v-for="d in columns"
                        :key="`forecast-${d}`"
                        class="cell"
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
                        :class="{ negative: getValue(g, d, 'adjust') < 0 }"
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
import { computed, onMounted, ref, watch } from "vue";
import api from "@/api/client";

const productFilter = ref("");
const defaultStart = new Date();
defaultStart.setDate(defaultStart.getDate() - 1);
const startDate = ref(formatDate(defaultStart));
const horizon = ref(30);
const loading = ref(false);
const error = ref("");
const orderLines = ref([]);
const currentPage = ref(1);
const pageSize = ref(20);

function formatDate(date) {
  // 日付文字列の場合はそのまま返す（YYYY-MM-DD形式）
  if (typeof date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(date)) {
    return date;
  }
  // Date オブジェクトの場合は変換
  const d = new Date(date);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function formatDateHeader(dateStr) {
  const d = new Date(dateStr);
  const m = d.getMonth() + 1;
  const day = d.getDate();
  return `${m}/${day}`;
}

const columns = computed(() => {
  const start = new Date(startDate.value);
  const cols = [];
  for (let i = 0; i < horizon.value; i++) {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    cols.push(formatDate(d));
  }
  return cols;
});

const groups = computed(() => {
  if (!orderLines.value.length) {
    console.log("[ShippingProgress] 受注明細データなし");
    return [];
  }

  console.log("[ShippingProgress] グループ化開始");
  console.log("[ShippingProgress] 期間範囲:", columns.value[0], "～", columns.value[columns.value.length - 1]);

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
    const dueDate = formatDate(order.due_date);
    const productCode = order.product_code;

    // 製品フィルタ
    if (productFilter.value) {
      const filter = productFilter.value.toLowerCase();
      const text = `${order.product_code || ""}${order.product_name || ""}`.toLowerCase();
      if (!text.includes(filter)) {
        skippedCount++;
        continue;
      }
    }

    processedCount++;

    // グループ作成
    if (!map.has(productCode)) {
      map.set(productCode, {
        key: productCode,
        product_code: order.product_code,
        product_name: order.product_name,
        cells: {},
        summary: { forecast: 0, firm: 0, actual: 0, adjust: 0, progressRate: "-" },
      });
    }

    const group = map.get(productCode);

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
    const actualQty = Number(order.actual_shipment_qty || 0);

    // 受注タイプ別に集計
    if (order.order_type === "FORECAST") {
      cell.forecast += qty;
    } else {
      // FIRM または未設定の場合は確定として扱う
      cell.firm += qty;
    }
    cell.actual += actualQty;
  }

  console.log("[ShippingProgress] 処理件数:", processedCount, "スキップ:", skippedCount);
  console.log("[ShippingProgress] グループ数:", map.size);

  // サマリー計算
  const result = Array.from(map.values()).map((g) => {
    let totalForecast = 0;
    let totalFirm = 0;
    let totalActual = 0;
    let totalAdjust = 0;

    // 各日付のデータに実績・調整を追加
    for (const [date, cell] of Object.entries(g.cells)) {
      totalForecast += cell.forecast;
      totalFirm += cell.firm;
      totalActual += cell.actual;
      totalAdjust += cell.adjust;
    }

    // サマリーの累積進度計算
    // 累積進度 = 0 - 合計需要 + 合計実績 + 合計調整
    const totalDemand = totalFirm > 0 ? totalFirm : totalForecast;
    const cumulativeProgress = 0 - totalDemand + totalActual + totalAdjust;

    g.summary = {
      forecast: totalForecast,
      firm: totalFirm,
      actual: totalActual,
      adjust: totalAdjust,
      progressRate: cumulativeProgress.toLocaleString(),
    };

    return g;
  });

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

const getProgressRate = (group, date) => {
  // 累積進度を計算
  // 累積進度(本日) = 累積進度(前日) - 確定(ないときは内示) + 実績 + 調整

  let cumulativeProgress = 0;

  // 日付順にソートして累積計算
  const sortedDates = columns.value;
  const currentIndex = sortedDates.indexOf(date);

  if (currentIndex === -1) return "-";

  // 初日から本日まで累積計算
  for (let i = 0; i <= currentIndex; i++) {
    const d = sortedDates[i];
    const firm = getValue(group, d, "firm");
    const forecast = getValue(group, d, "forecast");
    const actual = getValue(group, d, "actual");
    const adjust = getValue(group, d, "adjust");

    // 需要（確定優先、なければ内示）
    const demand = firm > 0 ? firm : forecast;

    // 累積進度 = 前日累積進度 - 需要 + 実績 + 調整
    cumulativeProgress = cumulativeProgress - demand + actual + adjust;
  }

  return cumulativeProgress.toLocaleString();
};

const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    const orderLinesRes = await api.orders.listOrderLines({ page_size: 10000 });

    const normalizeList = (payload) => {
      return Array.isArray(payload) ? payload : payload.results || [];
    };

    orderLines.value = normalizeList(orderLinesRes.data || []);
    // 開始日は初期値（今日の日付）のまま
    // 理由：過去のデータがある場合でも、現在から未来を表示したい
    // ユーザーは手動で開始日を変更して過去のデータも確認できる

    console.log("[ShippingProgress] データロード完了");
    console.log("[ShippingProgress] 受注明細件数:", orderLines.value.length);
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

const changePage = (page) => {
  const target = Math.min(Math.max(page, 1), totalPages.value);
  if (target === currentPage.value) return;
  currentPage.value = target;
};

watch([productFilter, startDate, horizon], () => {
  currentPage.value = 1;
});

watch(pageSize, () => {
  currentPage.value = 1;
});

watch(groups, () => {
  if (currentPage.value > totalPages.value) {
    currentPage.value = totalPages.value;
  }
});

onMounted(load);
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
.group-card {
  display: grid;
  grid-template-columns: 240px 1fr;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}
.info-block {
  padding: 12px;
  border-right: 1px solid #e5e7eb;
  background: #f9fafb;
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
  overflow: auto;
}
.matrix-table {
  border-collapse: collapse;
  width: 100%;
  min-width: 800px;
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
.label-col {
  position: sticky;
  left: 0;
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
