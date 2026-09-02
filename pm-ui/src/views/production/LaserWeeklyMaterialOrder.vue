<template>
  <section class="order-panel">
    <h3 class="collapsible-header" @click="showOrder = !showOrder">
      {{ showOrder ? "▼" : "▶" }} 材料発注・進度
    </h3>
    <div v-show="showOrder">
      <p>佐藤商事の手数を入力すると、残りの自数を名成鋼機へ自動配分します。</p>
      <div class="actions">
        <button class="btn primary" @click="save">進度を保存</button
        ><button class="btn" @click="openDownload('SATO')">
          佐藤商事注文書</button
        ><button class="btn" @click="openDownload('MEISEI')">
          名成鋼機注文書
        </button>
      </div>
      <div
        v-if="downloadDialog"
        class="download-modal"
        @click.self="downloadDialog = false"
      >
        <section class="download-dialog">
          <h3>
            {{ downloadSupplier === "SATO" ? "佐藤商事" : "名成鋼機" }}注文書
          </h3>
          <label>開始日<input v-model="downloadStartDate" type="date" /></label
          ><label>終了日<input v-model="downloadEndDate" type="date" /></label>
          <div class="dialog-actions">
            <button class="btn primary" @click="download">出力</button
            ><button class="btn" @click="downloadDialog = false">
              キャンセル
            </button>
          </div>
        </section>
      </div>
      <table>
        <colgroup>
          <col
            v-for="(width, index) in fixedColumnWidths"
            :key="`fixed-${index}`"
            :style="{ width }"
          />
          <template v-for="week in weekGroups" :key="`cols-${week.key}`"
            ><template v-for="day in week.days" :key="`cols-${day}`"
              ><col class="col-value" />
              <col class="col-value" />
              <col class="col-manual" />
              <col class="col-value"
            /></template>
            <col class="col-value" />
            <col class="col-value" />
            <col class="col-manual" />
            <col class="col-value"
          /></template>
        </colgroup>
        <thead>
          <tr>
            <th rowspan="2">材料コード</th>
            <th rowspan="2">材料名</th>
            <th rowspan="2">仕入先</th>
            <th class="initial-cell" rowspan="2">期首</th>
            <template v-for="week in weekGroups" :key="week.key"
              ><th
                v-for="day in week.days"
                :key="day"
                class="date-end"
                colspan="4"
              >
                {{ dayLabel(day) }}
              </th>
              <th class="week-total week-end" colspan="4">週合計</th></template
            >
          </tr>
          <tr>
            <template v-for="week in weekGroups" :key="`${week.key}-labels`"
              ><template v-for="day in week.days" :key="`${day}-labels`"
                ><th>需要</th>
                <th>自数</th>
                <th class="manual-cell">手数</th>
                <th class="date-end">進度</th></template
              >
              <th class="week-total">需要</th>
              <th class="week-total">自数</th>
              <th class="week-total manual-cell">手数</th>
              <th class="week-total week-end">進度</th></template
            >
          </tr>
        </thead>
        <tbody>
          <template
            v-for="(material, materialIndex) in materials"
            :key="material.material_id"
            ><tr
              v-for="supplier in supplierRows(material)"
              :key="`${material.material_id}-${supplier.code}`"
              :class="`material-group-${materialIndex % 2}`"
            >
              <td>{{ material.material_code }}</td>
              <td>{{ material.material_name }}</td>
              <td>{{ supplier.name }}</td>
              <td
                v-if="supplier.code === 'SATO' || !hasSato(material)"
                class="initial-cell"
                :rowspan="hasSato(material) ? 2 : 1"
              >
                <input
                  class="initial-input"
                  v-model.number="initial(material).value"
                  :disabled="initial(material).locked"
                  step="1"
                  type="number"
                /><button
                  class="lock-btn"
                  :class="{ locked: initial(material).locked }"
                  @click="toggleLock(material)"
                >
                  {{ initial(material).locked ? "固定" : "入力" }}
                </button>
              </td>
              <template
                v-for="week in weekGroups"
                :key="`${supplier.code}-${week.key}`"
                ><template
                  v-for="day in week.days"
                  :key="`${supplier.code}-${day}`"
                  ><td>{{ number(demand(material, day)) }}</td>
                  <td>{{ number(automatic(material, day, supplier.code)) }}</td>
                  <td class="manual-cell">
                    <input
                      class="manual-input"
                      v-model.number="
                        entry(material, day)[
                          supplier.code === 'SATO' ? 'sato_lots' : 'meisei_lots'
                        ]
                      "
                      min="0"
                      step="1"
                      type="number"
                    />
                  </td>
                  <td
                    :class="[
                      progressClass(material, day, supplier.code),
                      'date-end',
                    ]"
                  >
                    {{ number(progress(material, day, supplier.code)) }}
                  </td></template
                >
                <td class="week-total">
                  {{
                    number(weeklyValue(material, week, supplier.code, "demand"))
                  }}
                </td>
                <td class="week-total">
                  {{
                    number(
                      weeklyValue(material, week, supplier.code, "automatic"),
                    )
                  }}
                </td>
                <td class="week-total manual-cell">
                  {{
                    number(weeklyValue(material, week, supplier.code, "manual"))
                  }}
                </td>
                <td
                  :class="[
                    progressClass(
                      material,
                      week.days[week.days.length - 1],
                      supplier.code,
                    ),
                    'week-total',
                    'week-end',
                  ]"
                >
                  {{
                    number(
                      progress(
                        material,
                        week.days[week.days.length - 1],
                        supplier.code,
                      ),
                    )
                  }}
                </td></template
              >
            </tr></template
          >
        </tbody>
      </table>
    </div>
  </section>
</template>
<script setup>
import { computed, ref, watch } from "vue";
import api from "@/api/client";
const props = defineProps({
  startDate: { type: String, required: true },
  dates: { type: Array, required: true },
  materials: { type: Array, required: true },
});
const emit = defineEmits(["message"]);
const suppliers = [
  { code: "SATO", name: "佐藤商事" },
  { code: "MEISEI", name: "名成鋼機" },
];
const iso = (date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
const fixedColumnWidths = ["145px", "145px", "50px", "52px"];
const weekGroups = computed(() => {
  const groups = new Map();
  props.dates.forEach((day) => {
    const d = new Date(`${day}T00:00:00`);
    d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
    const key = d.toISOString().slice(0, 10);
    if (!groups.has(key)) groups.set(key, { key, days: [] });
    groups.get(key).days.push(day);
  });
  return [...groups.values()];
});
const dayLabel = (day) =>
  `${day.slice(5)}(${["日", "月", "火", "水", "木", "金", "土"][new Date(`${day}T00:00:00`).getDay()]})`;
const satoMaterialCodes = new Set([
  "SPHCT2.3X1524X3048",
  "SS400T8.0X1219X2810",
]);
const hasSato = (material) =>
  satoMaterialCodes.has(
    String(material.material_code || "")
      .replace(/\s/g, "")
      .toUpperCase(),
  );
const supplierRows = (material) =>
  hasSato(material)
    ? suppliers
    : suppliers.filter((supplier) => supplier.code === "MEISEI");
const entries = ref({});
const initials = ref({});
const showOrder = ref(true);
const downloadDialog = ref(false);
const downloadSupplier = ref("");
const downloadStartDate = ref("");
const downloadEndDate = ref("");
const key = (material, day) => `${material.material_id}:${day}`;
const entry = (material, day) =>
  entries.value[key(material, day)] ||
  (entries.value[key(material, day)] = {
    sato_lots: 0,
    meisei_lots: Math.ceil(demand(material, day)),
  });
const initial = (material) =>
  initials.value[material.material_id] ||
  (initials.value[material.material_id] = { value: 0, locked: false });
const demand = (material, day) =>
  Number(material.daily[day] || 0) / Number(material.order_lot_multiple || 1);
const automatic = (material, day, supplier) =>
  supplier === "SATO"
    ? 0
    : Math.max(
        demand(material, day) - Number(entry(material, day).sato_lots || 0),
        0,
      );
const manual = (material, day, supplier) => {
  const value = entry(material, day)[
    supplier === "SATO" ? "sato_lots" : "meisei_lots"
  ];
  return supplier === "MEISEI" && value === undefined
    ? Math.ceil(automatic(material, day, supplier))
    : Number(value || 0);
};
const progress = (material, day, supplier) => {
  let total = Number(initial(material).value || 0);
  for (const currentDay of props.dates) {
    total +=
      manual(material, currentDay, supplier) -
      automatic(material, currentDay, supplier);
    if (currentDay === day) break;
  }
  return total;
};
const progressClass = (material, day, supplier) => {
  const value = progress(material, day, supplier);
  return value > 0 ? "ahead" : value < 0 ? "behind" : "";
};
const weeklyValue = (material, week, supplier, field) =>
  week.days.reduce(
    (sum, day) =>
      sum +
      ({
        demand: demand(material, day),
        automatic: automatic(material, day, supplier),
        manual: manual(material, day, supplier),
      }[field] || 0),
    0,
  );
const number = (value) =>
  Number(value || 0).toFixed(Math.abs(Number(value || 0)) < 0.1 ? 2 : 1);
const load = async () => {
  if (!props.startDate) return;
  const [orders, initialProgress] = await Promise.all([
    api.laserWeeklyPlans.getMaterialOrderProgress(props.startDate),
    api.laserWeeklyPlans.getMaterialInitialProgress(props.startDate),
  ]);
  const next = {};
  orders.data.forEach((item) => {
    const value = next[`${item.material_id}:${item.required_date}`] || {};
    value[item.supplier === "SATO" ? "sato_lots" : "meisei_lots"] =
      item.order_lots;
    next[`${item.material_id}:${item.required_date}`] = value;
  });
  props.materials.forEach((material) =>
    props.dates.forEach((day) => {
      const value = next[key(material, day)] || { sato_lots: 0 };
      if (value.meisei_lots === undefined)
        value.meisei_lots = Math.ceil(
          Math.max(demand(material, day) - Number(value.sato_lots || 0), 0),
        );
      next[key(material, day)] = value;
    }),
  );
  entries.value = next;
  initials.value = Object.fromEntries(
    initialProgress.data.map((item) => [
      item.material_id,
      { value: item.initial_progress, locked: item.is_locked },
    ]),
  );
};
const save = async () => {
  const items = props.materials.flatMap((material) =>
    props.dates
      .map((required_date) => ({
        material_id: material.material_id,
        required_date,
        delivery_date: required_date,
        required_sheets: Number(material.daily[required_date] || 0),
        lot_multiple: Number(material.order_lot_multiple || 1),
        sato_enabled: hasSato(material),
        sato_lots: Number(entry(material, required_date).sato_lots || 0),
        meisei_lots: Number(entry(material, required_date).meisei_lots || 0),
      }))
      .filter((item) => item.required_sheets > 0),
  );
  const initialItems = props.materials.map((material) => ({
    material_id: material.material_id,
    initial_progress: Number(initial(material).value || 0),
    is_locked: initial(material).locked,
  }));
  await Promise.all([
    api.laserWeeklyPlans.saveMaterialOrderProgress(props.startDate, items),
    api.laserWeeklyPlans.saveMaterialInitialProgress(
      props.startDate,
      initialItems,
    ),
  ]);
  emit("message", "材料発注進度を保存しました。");
  await load();
};
const toggleLock = async (material) => {
  initial(material).locked = !initial(material).locked;
  await api.laserWeeklyPlans.saveMaterialInitialProgress(props.startDate, [
    {
      material_id: material.material_id,
      initial_progress: Number(initial(material).value || 0),
      is_locked: initial(material).locked,
    },
  ]);
};
const openDownload = (supplier) => {
  const start = new Date(`${props.startDate}T00:00:00`);
  start.setDate(start.getDate() + 7);
  const end = new Date(start);
  end.setDate(end.getDate() + 4);
  downloadSupplier.value = supplier;
  downloadStartDate.value = iso(start);
  downloadEndDate.value = iso(end);
  downloadDialog.value = true;
};
const download = async () => {
  if (
    !downloadStartDate.value ||
    !downloadEndDate.value ||
    downloadEndDate.value < downloadStartDate.value
  ) {
    emit("message", "出力期間を正しく指定してください。");
    return;
  }
  try {
    await save();
    const response = await api.laserWeeklyPlans.exportMaterialOrderExcel(
      props.startDate,
      downloadSupplier.value,
      downloadStartDate.value,
      downloadEndDate.value,
    );
    const url = URL.createObjectURL(response.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = `材料注文書_${downloadSupplier.value}_${downloadStartDate.value}_${downloadEndDate.value}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
    downloadDialog.value = false;
  } catch (e) {
    let detail = e.response?.data?.detail;
    if (!detail && e.response?.data instanceof Blob) {
      try {
        detail = JSON.parse(await e.response.data.text()).detail;
      } catch {}
    }
    emit("message", detail || "注文書を出力できませんでした。");
  }
};
watch(() => [props.startDate, props.materials], load, {
  immediate: true,
  deep: true,
});
</script>
<style scoped>
.order-panel {
  margin-top: 14px;
  overflow: auto;
}
.collapsible-header {
  margin: 0 0 4px;
  font-size: 14px;
  cursor: pointer;
  user-select: none;
  color: #334155;
}
.order-panel p {
  font-size: 12px;
}
.actions {
  position: sticky;
  top: 0;
  left: 0;
  z-index: 10;
  display: flex;
  gap: 8px;
  width: max-content;
  margin-bottom: 8px;
  padding: 4px 0;
  background: #eef3f8;
}
.btn {
  border: 1px solid #94a3b8;
  background: #fff;
  border-radius: 4px;
  padding: 5px 8px;
  cursor: pointer;
}
.primary {
  background: #0f766e;
  color: #fff;
  border-color: #0f766e;
}
.download-modal {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: center;
  background: rgba(15, 23, 42, 0.35);
}
.download-dialog {
  display: grid;
  gap: 10px;
  width: 270px;
  padding: 16px;
  background: #fff;
  border-radius: 6px;
}
.download-dialog h3 {
  margin: 0;
}
.download-dialog label {
  display: grid;
  gap: 3px;
  font-size: 12px;
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.order-panel table {
  border-collapse: collapse;
  table-layout: fixed;
  width: max-content;
  font-size: 12px;
}
.col-value {
  width: 38px;
}
.col-manual {
  width: 30px;
}
.order-panel th,
.order-panel td {
  border: 1px solid #cbd5e1;
  padding: 2px;
  white-space: nowrap;
  text-align: right;
  overflow: hidden;
}
.order-panel th {
  background: #e2e8f0;
}
.order-panel td:nth-child(-n + 3) {
  text-align: left;
}
.material-group-0 td {
  background: #f8fafc;
}
.material-group-1 td {
  background: #eff7df;
}
.order-panel th:nth-child(1),
.order-panel td:nth-child(1) {
  position: sticky;
  left: 0;
  z-index: 2;
}
.order-panel th:nth-child(2),
.order-panel td:nth-child(2) {
  position: sticky;
  left: 145px;
  z-index: 2;
}
.order-panel th:nth-child(3),
.order-panel td:nth-child(3) {
  position: sticky;
  left: 290px;
  z-index: 2;
}
.order-panel thead th:nth-child(-n + 3) {
  z-index: 4;
}
.initial-cell {
  position: sticky;
  left: 340px;
  z-index: 3;
  border-right: 3px solid #111827 !important;
}
.initial-cell::after {
  position: absolute;
  top: -1px;
  right: 0;
  bottom: -1px;
  width: 3px;
  content: "";
  pointer-events: none;
  background: #111827;
}
.order-panel thead .initial-cell {
  z-index: 5;
}
.manual-cell {
  width: 30px;
  min-width: 30px;
  max-width: 30px;
}
.week-total {
  background: #dbeafe !important;
  font-weight: 700;
}
.order-panel th.week-total {
  background: #93c5fd !important;
}
.initial-input,
.manual-input {
  width: 28px;
  min-width: 0;
  max-width: 28px;
  padding: 0;
}
.order-panel input {
  height: 24px;
  box-sizing: border-box;
  text-align: right;
}
.initial-input::-webkit-inner-spin-button,
.manual-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.initial-input,
.manual-input {
  -moz-appearance: textfield;
}
.date-end {
  border-right: 3px solid #111827 !important;
}
.week-end {
  border-right: 3px solid #dc2626 !important;
}
.lock-btn {
  display: block;
  width: 28px;
  min-width: 0;
  padding: 0;
  font-size: 9px;
  line-height: 16px;
}
.lock-btn.locked {
  background: #0f766e;
  color: #fff;
  border-color: #0f766e;
}
.ahead {
  color: #059669;
  font-weight: 700;
}
.behind {
  color: #dc2626;
  font-weight: 700;
}
</style>
