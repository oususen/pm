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
          <option :value="7">7日</option>
          <option :value="14">14日</option>
          <option :value="21">21日</option>
          <option :value="30">30日</option>
          <option :value="60">60日</option>
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
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import api from "@/api/client";

const productFilter = ref("");
const startDate = ref(formatDate(new Date()));
const horizon = ref(30); // デフォルト30日
const loading = ref(false);
const error = ref("");
const orderLines = ref([]);
const backlogs = ref([]);

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

    // YD60009848のデバッグ
    if (productCode.includes('9848')) {
      console.log("[9848] due_date:", order.due_date, "→ dueDate:", dueDate, "qty:", order.quantity, "type:", order.order_type);
    }

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

    // 受注タイプ別に集計
    if (order.order_type === "FORECAST") {
      cell.forecast += qty;
    } else {
      // FIRM または未設定の場合は確定として扱う
      cell.firm += qty;
    }
  }

  // backlogから実績と調整を取得
  const backlogMap = new Map();
  for (const b of backlogs.value) {
    if (!b.product_code || !b.plan_date) continue;
    const key = `${b.product_code}__${b.plan_date}`;
    const current = backlogMap.get(key) || { actual: 0, adjust: 0 };
    current.actual += Number(b.actual_shipment_qty || 0);
    current.adjust += Number(b.adjust_qty || 0);
    backlogMap.set(key, current);
  }

  console.log("[ShippingProgress] 処理件数:", processedCount, "スキップ:", skippedCount);
  console.log("[ShippingProgress] グループ数:", map.size);

  // YD60009848のグループ詳細を確認
  if (map.has('YD60009848')) {
    const g = map.get('YD60009848');
    console.log("[9848] グループ詳細:");
    console.log("[9848] product_name:", g.product_name);
    console.log("[9848] cells:", g.cells);
    console.log("[9848] cells keys:", Object.keys(g.cells));
  }

  // サマリー計算
  return Array.from(map.values()).map((g) => {
    let totalForecast = 0;
    let totalFirm = 0;
    let totalActual = 0;
    let totalAdjust = 0;

    // 各日付のデータに実績・調整を追加
    for (const [date, cell] of Object.entries(g.cells)) {
      const backlog = backlogMap.get(`${g.product_code}__${date}`);
      if (backlog) {
        cell.actual = backlog.actual;
        cell.adjust = backlog.adjust;
      }

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
    backlogs.value = []; // LineBacklog APIは使用しない

    // 開始日を受注データの最も古い納期に自動設定
    if (orderLines.value.length > 0) {
      const dates = orderLines.value
        .map(o => o.due_date)
        .filter(d => d)
        .sort();
      if (dates.length > 0) {
        startDate.value = dates[0];
      }
    }

    console.log("[ShippingProgress] データロード完了");
    console.log("[ShippingProgress] 受注明細件数:", orderLines.value.length);
    console.log("[ShippingProgress] バックログ件数:", backlogs.value.length);
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

onMounted(load);
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
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
