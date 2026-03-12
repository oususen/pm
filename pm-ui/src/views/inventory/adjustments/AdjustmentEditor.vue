<template>
  <div class="adjust-screen">
    <div class="caption">[SSE0030] {{ title }}</div>
    <div class="toolbar">
      <label class="toolbar-field">
        <span>調整日</span>
        <input v-model="adjustDate" type="date" />
      </label>
      <label class="toolbar-field">
        <span>処理方法</span>
        <select v-model="processMode">
          <option value="single">1:個別</option>
          <option value="batch">2:一括</option>
        </select>
      </label>
    </div>

    <div class="tabs">
      <button class="tab active" type="button">個別</button>
      <button class="tab" type="button">一括</button>
    </div>

    <div class="main">
      <section class="left-pane">
        <div class="panel">
          <div class="row">
            <label>品番</label>
            <input
              v-model="form.productCode"
              type="text"
              @blur="resolveByProductCode"
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
            <input v-model="displayStartDate" type="date" @change="reload" />
          </div>
          <div class="adjust-note">
            <p>※ この画面の調整値は「調整マスタ（production_line_backlog_adjustment）」に保存されます。</p>
            <p>※ 在庫残量一覧の「調整」（LineBacklog.adjust_qty）とは別管理です。</p>
            <p>※ 調整値は {{ recalculationLabel }} 実行後に {{ reflectionLabel }} へ反映されます。</p>
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
              <th>{{ currentAdjustHeaderLabel }}</th>
              <th>{{ metricHeaderLabel }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td :colspan="showPlanColumn ? 8 : 7" class="center">読込中...</td>
            </tr>
            <tr v-for="row in dateRows" :key="row.date" :class="{ holiday: isHoliday(row.date) }">
              <td :class="{ holidayText: isHoliday(row.date) }">{{ row.date }}</td>
              <td>{{ row.plan }}</td>
              <td>{{ row.firm }}</td>
              <td>{{ row.inbound }}</td>
              <td v-if="showPlanColumn">{{ row.planQty }}</td>
              <td>{{ row.adjust }}</td>
              <td>
                <input
                  class="qty-input"
                  type="number"
                  :value="row.currentAdjust"
                  @input="onAdjustInput(row.date, $event)"
                />
              </td>
              <td :class="{ negative: row.progress < 0 }">{{ row.progress }}</td>
            </tr>
          </tbody>
        </table>

        <div class="actions">
          <button class="btn primary" type="button" @click="saveCurrentDate">登録</button>
          <button class="btn" type="button" @click="reload">再読込</button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import api from "@/api/client";

const props = defineProps({
  title: { type: String, default: "生産進度調整入力" },
  description: { type: String, default: "" },
  adjustType: { type: String, required: true },
});

const today = new Date().toISOString().slice(0, 10);
const adjustDate = ref(today);
const displayStartDate = ref(today);
const processMode = ref("single");
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

const selectProcessCandidate = async (item) => {
  applyProcessToForm(item);
  await reload();
};

const setProcessCandidates = (items = []) => {
  processCandidates.value = items;
  if (!items.length) {
    selectedProcessKey.value = "";
    return;
  }
  applyProcessToForm(items[0]);
};

const resolveLineIdByCode = async (lineCode) => {
  const code = String(lineCode || "").trim();
  if (!code) return null;
  if (lineCodeIdCache.value.has(code)) return lineCodeIdCache.value.get(code);
  try {
    const res = await api.lines.getLines();
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
    const key = d.toISOString().slice(0, 10);
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
    const key = d.toISOString().slice(0, 10);
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
      displayedDateSet.add(d.toISOString().slice(0, 10));
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
      return;
    }

    form.productCode = product.product_code || productCode;
    form.productName = product.product_name || "";
    form.partNo = product.product_code || "";
    form.productId = product.id || null;
    processCandidates.value = [];
    selectedProcessKey.value = "";

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
      if (valid.length) {
        setProcessCandidates(valid);
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

    await reload();
  } catch (e) {
    alert(e?.response?.data?.detail || "品番情報の取得に失敗しました。");
  } finally {
    resolvingProduct.value = false;
  }
};

const getMetricValueForType = (item) => {
  if (props.adjustType === "STOCK") return Number(item.stock_qty || 0);
  if (props.adjustType === "PLANNED_STOCK") return Number(item.planned_stock_qty || 0);
  if (props.adjustType === "PLANNED_PROGRESS") return Number(item.planned_progress_qty || 0);
  return Number(item.progress_qty || 0);
};

const isStockType = props.adjustType === "STOCK" || props.adjustType === "PLANNED_STOCK";
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

const reload = async () => {
  loading.value = true;
  try {
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
    const endDate = endDateObj.toISOString().slice(0, 10);
    await loadHolidays(startDate, endDate);

    if (form.lineId && form.productId) {
      const backlogRes = await api.lineBacklogs.getLineBacklogs({
        line: form.lineId,
        product: form.productId,
        process: form.processId || undefined,
        plan_date__gte: startDate,
        plan_date__lte: endDate,
      });
      const backlogItems = Array.isArray(backlogRes.data) ? backlogRes.data : [];
      const metricMap = {};
      backlogItems.forEach((item) => {
        const key = item.plan_date;
        if (!metricMap[key]) {
          metricMap[key] = { plan: 0, firm: 0, inbound: 0, planQty: 0, progress: 0 };
        }
        metricMap[key].plan += Number(item.demand_qty_plan || 0);
        metricMap[key].firm += Number(item.firm_order_qty ?? item.actual_shipment_qty ?? 0);
        metricMap[key].inbound += Number(item.actual_qty || 0);
        metricMap[key].planQty += Number(item.plan_qty || 0);
        metricMap[key].progress += getMetricValueForType(item);
      });
      metricsByDate.value = metricMap;
    } else {
      metricsByDate.value = {};
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
  if (!form.lineCode || !form.productCode || !adjustDate.value) {
    alert("ラインCD・品番・調整日を入力してください。");
    return;
  }
  const target = dateRows.value.find((row) => row.date === adjustDate.value);
  const adjustQty = Number(target?.currentAdjust || 0);
  try {
    await api.lineBacklogAdjustments.save({
      line_code: form.lineCode,
      product_code: form.productCode,
      process_code: form.processCode || "",
      plan_date: adjustDate.value,
      adjust_type: props.adjustType,
      adjust_qty: adjustQty,
      reason: `${props.adjustType} UI入力`,
    });
    await reload();
  } catch (e) {
    alert(e?.response?.data?.detail || "保存に失敗しました。");
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
@media (max-width: 900px) {
  .main {
    grid-template-columns: 1fr;
  }
}
</style>
