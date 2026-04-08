<template>
  <div class="actual-progress-page">
    <h2 class="page-title">実進度求め</h2>
    <p class="page-desc">実進度 = 全状態在庫合計（部品換算） - 完成品別需要窓合計（明日〜完成品別累積LT）</p>

    <section class="panel">
      <h3 class="panel-title">対象部品</h3>
      <div class="target-grid">
        <div class="form-row">
          <label>品番</label>
          <input
            v-model.trim="targetPart.productCode"
            type="text"
            placeholder="品番を入力"
            @keyup.enter="resolveTargetPart"
          />
          <button class="btn" type="button" @click="resolveTargetPart" :disabled="resolvingTargetPart">
            {{ resolvingTargetPart ? "検索中..." : "検索" }}
          </button>
          <button
            class="btn"
            type="button"
            @click="applyTargetPartData"
            :disabled="!targetPart.id || loadingTargetData"
          >
            {{ loadingTargetData ? "反映中..." : "対象部品を反映" }}
          </button>
        </div>
        <div class="form-row">
          <label>品名</label>
          <input :value="targetPart.productName" type="text" readonly />
        </div>
        <div class="form-row">
          <label>部品番号</label>
          <input :value="targetPart.partNo" type="text" readonly />
        </div>
      </div>
      <p v-if="!targetPart.id" class="target-warning">対象部品を選択してから計算してください。</p>
      <p v-else-if="loadingTargetData" class="target-info">対象部品データを反映中です。</p>
      <p v-else-if="targetSyncMessage" class="target-info">{{ targetSyncMessage }}</p>
    </section>

    <section class="panel">
      <h3 class="panel-title">設定</h3>
      <div class="form-row">
        <label>基準日（棚卸日）</label>
        <input v-model="baseDate" type="date" />
      </div>
      <div class="result-grid">
        <div class="metric">
          <div class="metric-label">全状態在庫合計</div>
          <div class="metric-value">{{ totalStockConverted }}</div>
        </div>
        <div class="metric">
          <div class="metric-label">完成品別需要窓合計</div>
          <div class="metric-value">{{ totalDemandWindow }}</div>
        </div>
        <div class="metric metric-main">
          <div class="metric-label">実進度</div>
          <div
            v-if="targetPart.id"
            class="metric-value"
            :class="{ negative: actualProgress < 0 }"
          >
            {{ actualProgress }}
          </div>
          <div v-else class="metric-value metric-placeholder">-</div>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h3 class="panel-title">完成品設定（累積LT）</h3>
        <button class="btn" type="button" @click="addParent">行追加</button>
      </div>
      <table class="grid">
        <thead>
          <tr>
            <th>完成品コード</th>
            <th>完成品名</th>
            <th>累積LT(日)</th>
            <th>需要開始日</th>
            <th>需要終了日</th>
            <th>需要窓合計</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, index) in parentRows" :key="`p-${index}`">
            <td><input v-model.trim="row.parentCode" type="text" /></td>
            <td><input v-model.trim="row.parentName" type="text" /></td>
            <td><input v-model.number="row.cumulativeLtDays" type="number" min="0" step="1" /></td>
            <td>{{ parentWindowStart(row) || "-" }}</td>
            <td>{{ parentWindowEnd(row) || "-" }}</td>
            <td>{{ resolveParentDemandTotal(row.parentCode) }}</td>
            <td><button class="btn btn-danger" type="button" @click="removeParent(index)">削除</button></td>
          </tr>
          <tr v-if="!parentRows.length">
            <td colspan="7" class="empty">完成品設定がありません</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h3 class="panel-title">在庫（部品換算）</h3>
        <div class="panel-actions">
          <button class="btn" type="button" @click="exportInventoryListXlsx" :disabled="!inventoryRows.length">
            Excel出力
          </button>
          <button class="btn" type="button" @click="addInventory">行追加</button>
        </div>
      </div>
      <table class="grid">
        <thead>
          <tr>
            <th>関連品（自品＋中間品＋完成品）</th>
            <th>品名</th>
            <th>階層</th>
            <th>状態</th>
            <th>在庫数量</th>
            <th>部品換算係数</th>
            <th>部品換算在庫</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, index) in inventoryRows" :key="`i-${index}`">
            <td><input v-model.trim="row.familyCode" type="text" /></td>
            <td><input v-model.trim="row.familyName" type="text" /></td>
            <td><input v-model.trim="row.levelName" type="text" /></td>
            <td><input v-model.trim="row.stateName" type="text" /></td>
            <td><input v-model.number="row.stockQty" type="number" step="1" /></td>
            <td><input v-model.number="row.conversionFactor" type="number" min="0" step="0.001" /></td>
            <td>{{ stockConverted(row) }}</td>
            <td><button class="btn btn-danger" type="button" @click="removeInventory(index)">削除</button></td>
          </tr>
          <tr v-if="!inventoryRows.length">
            <td colspan="8" class="empty">在庫データがありません</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h3 class="panel-title">需要（完成品別・日別）</h3>
        <button class="btn" type="button" @click="addDemand">行追加</button>
      </div>
      <p v-if="unresolvedParentCodes.length" class="target-warning">
        完成品係数未設定: {{ unresolvedParentCodes.join(", ") }}（在庫（部品換算）の「関連品（自品＋中間品＋完成品）」と完全一致で設定してください）
      </p>
      <table class="grid">
        <thead>
          <tr>
            <th>完成品コード</th>
            <th>日付</th>
            <th>注文数量</th>
            <th>完成品累積LT</th>
            <th>完成品係数</th>
            <th>需要窓判定</th>
            <th>需要窓数量</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, index) in demandRows" :key="`d-${index}`">
            <td><input v-model.trim="row.parentCode" type="text" /></td>
            <td><input v-model="row.orderDate" type="date" /></td>
            <td><input v-model.number="row.orderQty" type="number" step="1" /></td>
            <td>{{ resolveParentLt(row.parentCode) }}</td>
            <td>{{ resolveParentConversionFactor(row.parentCode) ?? "未設定" }}</td>
            <td>{{ isDemandInWindow(row) ? "1" : "0" }}</td>
            <td>{{ demandWindowQty(row) }}</td>
            <td><button class="btn btn-danger" type="button" @click="removeDemand(index)">削除</button></td>
          </tr>
          <tr v-if="!demandRows.length">
            <td colspan="8" class="empty">需要データがありません</td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import * as XLSX from "xlsx";
import api from "@/api/client";

const today = new Date().toISOString().slice(0, 10);
const baseDate = ref(today);
const resolvingTargetPart = ref(false);
const loadingTargetData = ref(false);
const targetSyncMessage = ref("");
const targetPart = reactive({
  id: null,
  productCode: "",
  productName: "",
  partNo: "",
});

const parentRows = ref([]);

const inventoryRows = ref([]);

const demandRows = ref([]);
const workdayMap = ref(new Map());
const workdayLoaded = ref(false);
const workdayLoading = ref(false);
const customerWorkdayMaps = new Map();
const customerWorkdayLoading = new Map();

const toNum = (value, fallback = 0) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
};

const toRound3 = (value) => Number(toNum(value).toFixed(3));

const normalizeCode = (value) => String(value || "").trim();
const normalizeCodeKey = (value) => String(value || "").trim().toUpperCase();
const isCoproductCode = (value) => normalizeCodeKey(value).startsWith("ST");

const normalizeLtDays = (value) => Math.max(0, Math.ceil(toNum(value, 0)));

const parseDate = (dateStr) => {
  if (!dateStr) return null;
  const parts = String(dateStr).split("-");
  if (parts.length !== 3) return null;
  const y = Number(parts[0]);
  const m = Number(parts[1]);
  const d = Number(parts[2]);
  if (!y || !m || !d) return null;
  return new Date(Date.UTC(y, m - 1, d));
};

const formatDate = (dateObj) => {
  const y = dateObj.getUTCFullYear();
  const m = String(dateObj.getUTCMonth() + 1).padStart(2, "0");
  const d = String(dateObj.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
};

const normalizeDateString = (value) => {
  const raw = String(value || "").trim();
  if (!raw) return "";
  const datePart = raw.split(" ")[0].split("T")[0];
  const normalized = datePart.replaceAll("/", "-");
  const parsed = parseDate(normalized);
  if (!parsed) return "";
  return formatDate(parsed);
};

const addDays = (dateStr, days) => {
  const d = parseDate(dateStr);
  if (!d) return "";
  d.setUTCDate(d.getUTCDate() + Number(days || 0));
  return formatDate(d);
};

const isWeekend = (dateStr) => {
  const d = parseDate(dateStr);
  if (!d) return false;
  const dow = d.getUTCDay();
  return dow === 0 || dow === 6;
};

const isWorkingDay = (dateStr) => {
  if (!dateStr) return false;
  const defined = workdayMap.value.get(dateStr);
  if (typeof defined === "boolean") return defined;
  return !isWeekend(dateStr);
};

const addWorkingDays = (dateStr, days) => {
  const base = parseDate(dateStr);
  if (!base) return "";
  const delta = Number(days || 0);
  if (delta === 0) return formatDate(base);

  const step = delta > 0 ? 1 : -1;
  let remaining = Math.abs(delta);
  let cursor = formatDate(base);

  while (remaining > 0) {
    cursor = addDays(cursor, step);
    if (isWorkingDay(cursor)) remaining -= 1;
  }
  return cursor;
};

const isWorkingDayByCalendar = (dateStr, calendarId = null) => {
  if (calendarId && customerWorkdayMaps.has(calendarId)) {
    const map = customerWorkdayMaps.get(calendarId);
    const defined = map?.get(dateStr);
    if (typeof defined === "boolean") return defined;
  }
  return isWorkingDay(dateStr);
};

const addWorkingDaysByCalendar = (dateStr, days, calendarId = null) => {
  const base = parseDate(dateStr);
  if (!base) return "";
  const delta = Number(days || 0);
  if (delta === 0) return formatDate(base);

  const step = delta > 0 ? 1 : -1;
  let remaining = Math.abs(delta);
  let cursor = formatDate(base);

  while (remaining > 0) {
    cursor = addDays(cursor, step);
    if (isWorkingDayByCalendar(cursor, calendarId)) remaining -= 1;
  }
  return cursor;
};

const normalizeList = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
};

const ensureWorkdayCalendar = async () => {
  if (workdayLoaded.value || workdayLoading.value) return;
  workdayLoading.value = true;
  try {
    const res = await api.calendars.getCalendars({ search: "daiso", page_size: 20 });
    const rows = normalizeList(res.data);
    const daisoCalendar = rows.find(
      (row) =>
        String(row.calendar_code || "").toLowerCase() === "daiso" ||
        String(row.calendar_name || "").includes("ダイソウ")
    );
    if (!daisoCalendar?.id) {
      workdayMap.value = new Map();
      return;
    }

    const dayRes = await api.calendars.getCalendarDays(daisoCalendar.id, { page_size: 5000 });
    const dayRows = normalizeList(dayRes.data);
    const map = new Map();
    dayRows.forEach((day) => {
      const dateStr = String(day.target_date || "");
      if (!dateStr) return;
      if (day.is_working_day === true || day.is_working_day === false) {
        map.set(dateStr, Boolean(day.is_working_day));
      }
    });
    workdayMap.value = map;
  } catch (e) {
    console.error("カレンダ取得エラー:", e);
    workdayMap.value = new Map();
  } finally {
    workdayLoaded.value = true;
    workdayLoading.value = false;
  }
};

const ensureCustomerWorkdayCalendar = async (calendarId) => {
  if (!calendarId) return;
  if (customerWorkdayMaps.has(calendarId)) return;
  if (customerWorkdayLoading.has(calendarId)) {
    await customerWorkdayLoading.get(calendarId);
    return;
  }

  const promise = (async () => {
    try {
      const dayRes = await api.calendars.getCalendarDays(calendarId, { page_size: 5000 });
      const dayRows = normalizeList(dayRes.data);
      const map = new Map();
      dayRows.forEach((day) => {
        const dateStr = String(day.target_date || "");
        if (!dateStr) return;
        if (day.is_working_day === true || day.is_working_day === false) {
          map.set(dateStr, Boolean(day.is_working_day));
        }
      });
      customerWorkdayMaps.set(calendarId, map);
    } catch (e) {
      console.error("顧客カレンダ取得エラー:", e);
      customerWorkdayMaps.set(calendarId, new Map());
    }
  })();

  customerWorkdayLoading.set(calendarId, promise);
  try {
    await promise;
  } finally {
    customerWorkdayLoading.delete(calendarId);
  }
};

const resolveTargetPart = async () => {
  const code = String(targetPart.productCode || "").trim();
  if (!code || resolvingTargetPart.value) return;
  resolvingTargetPart.value = true;
  targetSyncMessage.value = "";
  try {
    const res = await api.products.getProducts({ search: code, page_size: 20 });
    const rows = normalizeList(res.data);
    const normalized = code.toUpperCase();
    const selected =
      rows.find((r) => String(r.product_code || "").trim().toUpperCase() === normalized) ||
      rows.find((r) => String(r.product_code || "").trim().toUpperCase().startsWith(normalized)) ||
      rows[0];

    if (!selected) {
      alert("品番に該当する部品が見つかりません。");
      targetPart.id = null;
      targetPart.productName = "";
      targetPart.partNo = "";
      return;
    }
    targetPart.id = selected.id || null;
    targetPart.productCode = selected.product_code || code;
    targetPart.productName = selected.product_name || "";
    targetPart.partNo = selected.product_code || "";
    await applyTargetPartData();
  } catch (e) {
    alert(e?.response?.data?.detail || "部品情報の取得に失敗しました。");
  } finally {
    resolvingTargetPart.value = false;
  }
};

const collectWhereUsedCodes = (parents, set = new Set()) => {
  if (!Array.isArray(parents) || !parents.length) return set;
  parents.forEach((item) => {
    const code = normalizeCode(item?.parent_product_code);
    if (code) set.add(code);
    if (Array.isArray(item?.parents) && item.parents.length) {
      collectWhereUsedCodes(item.parents, set);
    }
  });
  return set;
};

const resolveSelfLtDays = (item) => {
  const raw = item?.parent_self_lt_days;
  if (raw !== null && raw !== undefined && raw !== "") {
    return normalizeLtDays(raw);
  }
  return normalizeLtDays(item?.resolved_lead_time_days ?? item?.lead_time_days);
};

const buildAncestorsFromTree = (parents, productByCode, baseSelfLtDays = 0) => {
  const ancestorMap = new Map();

  const walk = (nodes, depth, parentFactor, cumulativeLt) => {
    if (!Array.isArray(nodes) || !nodes.length) return;
    nodes.forEach((item) => {
      const parentCode = normalizeCode(item?.parent_product_code);
      if (!parentCode) return;
      const parentMeta = productByCode.get(parentCode);
      const nodeQty = toNum(item?.quantity || 0);
      const nodeFactor = toRound3(parentFactor * nodeQty);
      const nodeSelfLtDays = resolveSelfLtDays(item);
      const nodeCumulativeLt = toNum(cumulativeLt + nodeSelfLtDays);
      const isFinal = Boolean(item?.is_final_product || parentMeta?.is_final_product);

      const existing = ancestorMap.get(parentCode);
      if (existing) {
        existing.conversionFactor = toRound3(existing.conversionFactor + nodeFactor);
        existing.cumulativeLtDays = Math.max(existing.cumulativeLtDays, nodeCumulativeLt);
        existing.depth = Math.min(existing.depth, depth);
        existing.isFinal = existing.isFinal || isFinal;
        if (!existing.parentId && item?.parent_product_id) existing.parentId = Number(item.parent_product_id);
        if (!existing.parentName && item?.parent_product_name) existing.parentName = item.parent_product_name;
      } else {
        ancestorMap.set(parentCode, {
          parentId: Number(item?.parent_product_id || 0) || null,
          parentCode,
          parentName: item?.parent_product_name || parentMeta?.product_name || "",
          conversionFactor: nodeFactor,
          cumulativeLtDays: nodeCumulativeLt,
          depth,
          isFinal,
        });
      }

      if (Array.isArray(item?.parents) && item.parents.length) {
        walk(item.parents, depth + 1, nodeFactor, nodeCumulativeLt);
      }
    });
  };

  walk(parents, 1, 1, normalizeLtDays(baseSelfLtDays));
  return Array.from(ancestorMap.values());
};

const resolveOrderLineQty = (item) => toNum(item?.quantity || 0);

const resolveOrderType = (item) =>
  String(item?.effective_order_type || item?.order_type || "").trim().toUpperCase();

const fetchProductsByCodes = async (codes) => {
  const uniqueCodes = Array.from(new Set(codes.map((code) => normalizeCode(code)).filter(Boolean)));
  if (!uniqueCodes.length) return [];
  const res = await api.products.getProductsByCodesIn(uniqueCodes);
  return normalizeList(res.data);
};

const applyTargetPartData = async () => {
  if (!targetPart.id || loadingTargetData.value) return;
  loadingTargetData.value = true;
  targetSyncMessage.value = "";
  try {
    await ensureWorkdayCalendar();
    const whereUsedRes = await api.products.getWhereUsed(targetPart.id, true, baseDate.value);
    const parentTree = whereUsedRes?.data?.parents || [];
    const targetSelfLtDays = normalizeLtDays(whereUsedRes?.data?.self_info?.self_lt_days || 0);

    const allCodes = [targetPart.productCode, ...Array.from(collectWhereUsedCodes(parentTree))];
    const productRows = await fetchProductsByCodes(allCodes);
    const productByCode = new Map(
      productRows
        .map((row) => [normalizeCode(row.product_code), row])
        .filter(([code]) => Boolean(code))
    );

    const ancestors = buildAncestorsFromTree(parentTree, productByCode, targetSelfLtDays)
      .filter((row) => row.parentCode)
      .sort((a, b) => {
        if (a.depth !== b.depth) return a.depth - b.depth;
        return a.parentCode.localeCompare(b.parentCode);
      });

    const finalParents = ancestors
      .filter((row) => row.isFinal)
      .sort((a, b) => a.parentCode.localeCompare(b.parentCode));

    // 対象部品自身が最終品の場合、自分を完成品設定に追加
    const selfIsFinal = Boolean(whereUsedRes?.data?.self_info?.is_final_product);
    const selfAsParent = selfIsFinal
      ? [
          {
            parentId: Number(targetPart.id),
            parentCode: targetPart.productCode,
            parentName: targetPart.productName,
            cumulativeLtDays: Math.max(targetSelfLtDays, 1),
          },
        ]
      : [];

    parentRows.value = [
      ...selfAsParent,
      ...finalParents.map((row) => ({
        parentId: row.parentId,
        parentCode: row.parentCode,
        parentName: row.parentName,
        cumulativeLtDays: toNum(row.cumulativeLtDays),
      })),
    ];

    const inventoryAncestors = ancestors.filter((row) => !isCoproductCode(row.parentCode));

    const stockProductIds = [targetPart.id, ...inventoryAncestors.map((row) => row.parentId)]
      .filter((id) => Number.isFinite(Number(id)))
      .map((id) => Number(id));
    const uniqueStockIds = Array.from(new Set(stockProductIds));
    const stockByProduct = new Map();

    if (uniqueStockIds.length) {
      const stockRes = await api.lineBacklogs.getLineBacklogs({
        product__in: uniqueStockIds.join(","),
        plan_date: baseDate.value,
        include_order_split: true,
        page_size: 5000,
      });
      const stockRows = normalizeList(stockRes.data);
      stockRows.forEach((item) => {
        const productId = Number(item.product || 0) || null;
        if (!productId) return;
        const cur = stockByProduct.get(productId) || 0;
        stockByProduct.set(productId, toRound3(cur + toNum(item.stock_qty || 0)));
      });
    }

    const selfStock = stockByProduct.get(Number(targetPart.id)) || 0;
    const autoInventoryRows = [
      {
        productId: Number(targetPart.id),
        familyCode: targetPart.productCode,
        familyName: targetPart.productName,
        levelName: "自工程",
        stateName: "対象部品在庫",
        stockQty: toRound3(selfStock),
        conversionFactor: 1,
      },
    ];
    inventoryAncestors.forEach((row) => {
      autoInventoryRows.push({
        productId: row.parentId,
        familyCode: row.parentCode,
        familyName: row.parentName,
        levelName: `親階層${row.depth}`,
        stateName: row.isFinal ? "親在庫(最終品)" : "親在庫",
        stockQty: toRound3(stockByProduct.get(Number(row.parentId)) || 0),
        conversionFactor: toRound3(row.conversionFactor),
      });
    });
    inventoryRows.value = autoInventoryRows;

    const demandAgg = new Map();
    await Promise.all(
      parentRows.value.map(async (row) => {
        const parentId = Number(row.parentId || 0) || null;
        const ltDays = toNum(row.cumulativeLtDays || 0);
        if (!parentId || ltDays <= 0) return;
        const fetchStart = addDays(baseDate.value, 1);
        const fetchEnd = addDays(baseDate.value, Math.max(ltDays, 0) + 45);
        const orderRes = await api.orders.listOrderLines({
          product: parentId,
          order_type: "FIRM,FORECAST",
          due_date__gte: fetchStart,
          due_date__lte: fetchEnd,
          page_size: 5000,
        });

        const orderLines = normalizeList(orderRes.data);
        const calendarIds = Array.from(
          new Set(
            orderLines
              .map((item) => Number(item?.customer_calendar_id || 0))
              .filter((id) => Number.isFinite(id) && id > 0)
          )
        );
        await Promise.all(calendarIds.map((id) => ensureCustomerWorkdayCalendar(id)));

        const preferredQtyByCustomerDate = new Map();
        const windowByCalendar = new Map();

        orderLines.forEach((item) => {
          const dueDate = normalizeDateString(item?.due_date);
          if (!dueDate) return;

          const orderType = resolveOrderType(item);
          if (orderType !== "FIRM" && orderType !== "FORECAST") return;

          const qty = resolveOrderLineQty(item);
          if (qty === 0) return;

          const calendarId = Number(item?.customer_calendar_id || 0) || 0;
          if (!windowByCalendar.has(calendarId)) {
            windowByCalendar.set(calendarId, {
              start: addWorkingDaysByCalendar(baseDate.value, 1, calendarId || null),
              end: addWorkingDaysByCalendar(baseDate.value, ltDays, calendarId || null),
            });
          }
          const win = windowByCalendar.get(calendarId);
          if (!win?.start || !win?.end) return;
          if (dueDate < win.start || dueDate > win.end) return;

          const customerCode = normalizeCode(item?.customer_code) || "_";
          const shipToCode = normalizeCode(item?.ship_to_code) || "_";
          const key = `${customerCode}__${shipToCode}__${dueDate}`;
          const cur = preferredQtyByCustomerDate.get(key) || { firm: 0, forecast: 0 };
          if (orderType === "FIRM") {
            cur.firm = toRound3(cur.firm + qty);
          } else {
            cur.forecast = toRound3(cur.forecast + qty);
          }
          preferredQtyByCustomerDate.set(key, cur);
        });

        preferredQtyByCustomerDate.forEach((v, key) => {
          const sepIdx = key.lastIndexOf("__");
          const rawOrderDate = sepIdx >= 0 ? key.slice(sepIdx + 2) : "";
          const orderDate = normalizeDateString(rawOrderDate);
          if (!orderDate) return;
          const selectedQty = v.firm > 0 ? v.firm : v.forecast;
          if (selectedQty === 0) return;
          const aggKey = `${row.parentCode}__${orderDate}`;
          const cur = demandAgg.get(aggKey) || 0;
          demandAgg.set(aggKey, toRound3(cur + selectedQty));
        });
      })
    );

    demandRows.value = Array.from(demandAgg.entries())
      .map(([key, orderQty]) => {
        const [parentCode, orderDate] = key.split("__");
        return {
          parentCode,
          orderDate,
          orderQty: toRound3(orderQty),
        };
      })
      .sort((a, b) => {
        if (a.orderDate !== b.orderDate) return a.orderDate.localeCompare(b.orderDate);
        return a.parentCode.localeCompare(b.parentCode);
      });

    targetSyncMessage.value = `反映完了: 完成品${parentRows.value.length}件 / 在庫${inventoryRows.value.length}件 / 需要${demandRows.value.length}件`;
  } catch (e) {
    console.error("対象部品反映エラー:", e);
    targetSyncMessage.value = "";
    alert(e?.response?.data?.detail || "対象部品の自動反映に失敗しました。");
  } finally {
    loadingTargetData.value = false;
  }
};

const parentMap = computed(() => {
  const map = new Map();
  parentRows.value.forEach((row) => {
    const key = normalizeCodeKey(row.parentCode);
    if (!key) return;
    map.set(key, Number(row.cumulativeLtDays || 0));
  });
  return map;
});

const parentFactorMap = computed(() => {
  const map = new Map();
  inventoryRows.value.forEach((row) => {
    const key = normalizeCodeKey(row.familyCode);
    if (!key) return;
    if (map.has(key)) return;
    map.set(key, toRound3(toNum(row.conversionFactor, 0)));
  });
  return map;
});

const resolveParentLt = (parentCode) => {
  const key = normalizeCodeKey(parentCode);
  if (!key) return 0;
  return Number(parentMap.value.get(key) || 0);
};

const resolveParentConversionFactor = (parentCode) => {
  const key = normalizeCodeKey(parentCode);
  if (!key) return null;
  if (!parentFactorMap.value.has(key)) return null;
  return Number(parentFactorMap.value.get(key));
};

const unresolvedParentCodes = computed(() => {
  const set = new Set();
  parentRows.value.forEach((row) => {
    const code = normalizeCode(row.parentCode);
    if (!code) return;
    const lt = resolveParentLt(code);
    if (lt <= 0) return;
    if (resolveParentConversionFactor(code) !== null) return;
    set.add(code);
  });
  return Array.from(set).sort((a, b) => a.localeCompare(b));
});

const parentWindowStart = (row) => {
  if (!row || !Number(row.cumulativeLtDays || 0)) return addWorkingDays(baseDate.value, 1);
  return addWorkingDays(baseDate.value, 1);
};

const parentWindowEnd = (row) => {
  const lt = Number(row?.cumulativeLtDays || 0);
  if (lt <= 0) return "";
  return addWorkingDays(baseDate.value, lt);
};

const stockConverted = (row) =>
  Number((Number(row.stockQty || 0) * Number(row.conversionFactor || 0)).toFixed(3));

const sanitizeFileName = (value) => String(value || "").replace(/[\\/:*?"<>|]/g, "_");

const exportInventoryListXlsx = () => {
  const rows = inventoryRows.value.filter((row) => normalizeCode(row.familyCode));
  if (!rows.length) {
    alert("出力対象の在庫データがありません。");
    return;
  }

  const headers = [
    "関連品コード",
    "品名",
    "階層",
    "状態",
    "机上在庫",
    "棚卸在庫",
    "部品換算係数",
    "部品換算在庫",
  ];
  const body = rows.map((row) => [
    normalizeCode(row.familyCode),
    String(row.familyName || "").trim(),
    String(row.levelName || "").trim(),
    String(row.stateName || "").trim(),
    toNum(row.stockQty),
    "",
    toNum(row.conversionFactor),
    stockConverted(row),
  ]);

  const ws = XLSX.utils.aoa_to_sheet([headers, ...body]);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "棚卸リスト");

  const partCode = sanitizeFileName(targetPart.productCode || "対象部品");
  const dateLabel = sanitizeFileName(baseDate.value || today);
  XLSX.writeFile(wb, `棚卸リスト_${partCode}_${dateLabel}.xlsx`);
};

const totalStockConverted = computed(() =>
  Number(inventoryRows.value.reduce((sum, row) => sum + stockConverted(row), 0).toFixed(3))
);

const isDemandInWindow = (row) => {
  const orderDate = normalizeDateString(row?.orderDate);
  if (!orderDate) return false;
  const lt = resolveParentLt(row.parentCode);
  if (lt <= 0) return false;
  const start = addWorkingDays(baseDate.value, 1);
  const end = addWorkingDays(baseDate.value, lt);
  return orderDate >= start && orderDate <= end;
};

const demandWindowQty = (row) => {
  if (!isDemandInWindow(row)) return 0;
  const factor = resolveParentConversionFactor(row.parentCode);
  if (factor === null) return 0;
  return Number((Number(row.orderQty || 0) * factor).toFixed(3));
};

const parentDemandTotals = computed(() => {
  const totals = new Map();
  demandRows.value.forEach((row) => {
    const key = normalizeCodeKey(row.parentCode);
    if (!key) return;
    const qty = demandWindowQty(row);
    if (qty === 0) return;
    const cur = Number(totals.get(key) || 0);
    totals.set(key, Number((cur + qty).toFixed(3)));
  });
  return totals;
});

const resolveParentDemandTotal = (parentCode) => {
  const key = normalizeCodeKey(parentCode);
  if (!key) return 0;
  return Number(parentDemandTotals.value.get(key) || 0);
};

const totalDemandWindow = computed(() =>
  Number(demandRows.value.reduce((sum, row) => sum + demandWindowQty(row), 0).toFixed(3))
);

const actualProgress = computed(() =>
  Number((totalStockConverted.value - totalDemandWindow.value).toFixed(3))
);

const addParent = () => {
  parentRows.value.push({ parentCode: "", parentName: "", cumulativeLtDays: 0 });
};

const removeParent = (index) => {
  parentRows.value.splice(index, 1);
};

const addInventory = () => {
  inventoryRows.value.push({
    familyCode: "",
    familyName: "",
    levelName: "",
    stateName: "",
    stockQty: 0,
    conversionFactor: 1,
  });
};

const removeInventory = (index) => {
  inventoryRows.value.splice(index, 1);
};

const addDemand = () => {
  demandRows.value.push({ parentCode: "", orderDate: baseDate.value, orderQty: 0 });
};

const removeDemand = (index) => {
  demandRows.value.splice(index, 1);
};

onMounted(() => {
  ensureWorkdayCalendar();
});
</script>

<style scoped>
.actual-progress-page {
  padding: 12px 10px 18px;
  background: #efefdc;
  min-height: 100%;
}
.page-title {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 700;
  color: #111827;
}
.page-desc {
  margin: 0 0 12px;
  color: #334155;
  font-size: 14px;
}
.panel {
  background: #f8fafc;
  border: 1px solid #c7ced9;
  border-radius: 10px;
  padding: 10px;
  margin-bottom: 12px;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.panel-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.panel-title {
  margin: 0 0 8px;
  font-size: 18px;
  color: #0f172a;
}
.form-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.target-grid .form-row {
  max-width: 820px;
}
.form-row label {
  font-weight: 700;
  min-width: 70px;
}
.target-warning {
  margin: 0;
  color: #b91c1c;
  font-size: 13px;
}
.target-info {
  margin: 0;
  color: #0f172a;
  font-size: 13px;
}
.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 260px));
  gap: 8px;
}
.metric {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 8px 10px;
  background: #ffffff;
}
.metric-main {
  background: #dcfce7;
}
.metric-label {
  font-size: 12px;
  color: #475569;
}
.metric-value {
  font-size: 26px;
  font-weight: 700;
  color: #0f172a;
}
.metric-placeholder {
  color: #64748b;
}
.negative {
  color: #b91c1c;
}
.grid {
  width: 100%;
  border-collapse: collapse;
  background: #ffffff;
}
.grid th,
.grid td {
  border: 1px solid #cbd5e1;
  padding: 6px;
  font-size: 13px;
}
.grid th {
  background: #3f5f73;
  color: #ffffff;
  text-align: center;
}
.grid input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 4px 6px;
}
.empty {
  text-align: center;
  color: #64748b;
}
.btn {
  border: 1px solid #94a3b8;
  background: #e2e8f0;
  color: #0f172a;
  border-radius: 6px;
  padding: 4px 10px;
  cursor: pointer;
}
.btn:hover {
  background: #d6dee8;
}
.btn-danger {
  border-color: #fca5a5;
  background: #fee2e2;
  color: #991b1b;
}
.btn-danger:hover {
  background: #fecaca;
}
@media (max-width: 800px) {
  .page-title {
    font-size: 20px;
  }
  .panel-title {
    font-size: 16px;
  }
}
</style>
