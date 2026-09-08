<template>
  <section class="order-panel">
    <h3 class="collapsible-header" @click="showOrder = !showOrder">
      {{ showOrder ? "▼" : "▶" }} 材料発注・進度
    </h3>
    <div v-show="showOrder">
      <p>佐藤商事の手数を入力すると、残りの自数を名成鋼機へ自動配分します。手数は上段がロット数(L)、下段が端数枚数(枚)です。</p>
      <div class="actions">
        <button class="btn primary" @click="save" :disabled="saving">
          {{ saving ? "保存中..." : "変更を保存" }}</button
        ><button class="btn" @click="openDownload('SATO')">
          佐藤商事注文書</button
        ><button class="btn" @click="openDownload('MEISEI')">
          名成鋼機注文書</button
        ><button class="btn" @click="showManualAdd = !showManualAdd">
          手動追加
        </button>
      </div>
      <div v-if="showManualAdd" class="manual-add-form">
        <label>材料<select v-model="manualMaterialId" style="max-width:220px;">
          <option value="">-- 選択 --</option>
          <option v-for="m in manualMaterialOptions" :key="m.id" :value="m.id">{{ m.product_code }} {{ m.product_name }}</option>
        </select></label>
        <label>仕入先<select v-model="manualSupplier">
          <option value="MEISEI">名成鋼機</option>
          <option value="SATO">佐藤商事</option>
        </select></label>
        <label>納期<input v-model="manualDeliveryDate" type="date" /></label>
        <label>ロット数<input v-model.number="manualLots" type="number" min="0" style="width:60px;" /></label>
        <label>倍数<input v-model.number="manualLotMultiple" type="number" min="0" style="width:60px;" /></label>
        <label>端数枚数<input v-model.number="manualSheets" type="number" min="0" style="width:60px;" /></label>
        <button class="btn primary" @click="addManualOrder" :disabled="!manualMaterialId || !manualDeliveryDate || (manualLots === 0 && manualSheets === 0)">登録</button>
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
              <td><span class="mat-code-wrap"><span>{{ material.material_code }}</span><span class="mat-unit-labels"><span>L</span><span>枚</span></span></span></td>
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
                  <td class="manual-cell mat-manual-cell"
                    :data-tip="`${material.material_code} ${supplier.name}`"
                  >
                    <div class="mat-inputs-wrap">
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
                        @focus="$event.target.select()"
                      /><input
                        class="sheets-input"
                        v-model.number="
                          entry(material, day)[
                            supplier.code === 'SATO' ? 'sato_sheets' : 'meisei_sheets'
                          ]
                        "
                        min="0"
                        step="1"
                        type="number"
                        @focus="$event.target.select()"
                      />
                    </div>
                  </td>
                  <td
                    v-if="supplier.code === 'SATO' || !hasSato(material)"
                    :rowspan="hasSato(material) ? 2 : 1"
                    :class="[
                      combinedProgressClass(material, day),
                      'date-end',
                    ]"
                  >
                    {{ number(combinedProgress(material, day)) }}
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
                  v-if="supplier.code === 'SATO' || !hasSato(material)"
                  :rowspan="hasSato(material) ? 2 : 1"
                  :class="[
                    combinedProgressClass(
                      material,
                      week.days[week.days.length - 1],
                    ),
                    'week-total',
                    'week-end',
                  ]"
                >
                  {{
                    number(
                      combinedProgress(
                        material,
                        week.days[week.days.length - 1],
                      ),
                    )
                  }}
                </td></template
              >
            </tr></template
          ><template v-for="row in manualRows" :key="`manual-${row.id}`">
            <tr class="manual-row">
              <td>{{ row.material_code }} <span class="manual-tag">手動</span></td>
              <td>{{ row.material_name }}</td>
              <td>{{ row.supplier_label }}</td>
              <td class="initial-cell">-</td>
              <template v-for="week in weekGroups" :key="`m-${row.id}-${week.key}`">
                <template v-for="day in week.days" :key="`m-${row.id}-${day}`">
                  <td colspan="3">
                    <template v-if="day === row.delivery_date">
                      {{ row.order_lots }}L<span v-if="row.order_sheets" class="sheets-label">+{{ row.order_sheets }}枚</span>
                    </template>
                  </td>
                  <td class="date-end"></td>
                </template>
                <td class="week-total" colspan="3"></td>
                <td class="week-total week-end">
                  <button class="del-btn" @click="deleteManualRow(row.id)" title="削除">×</button>
                </td>
              </template>
            </tr>
          </template>
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
const saving = ref(false);
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
    sato_sheets: 0,
    meisei_sheets: 0,
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
const combinedProgress = (material, day) => {
  let total = Number(initial(material).value || 0);
  for (const currentDay of props.dates) {
    const satoManual = manual(material, currentDay, "SATO");
    const meiseiManual = manual(material, currentDay, "MEISEI");
    total += satoManual + meiseiManual - demand(material, currentDay);
    if (currentDay === day) break;
  }
  return total;
};
const combinedProgressClass = (material, day) => {
  const value = combinedProgress(material, day);
  return value > 0 ? "ahead" : value < 0 ? "behind" : "";
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
    const value = next[`${item.material_id}:${item.required_date}`] || { sato_sheets: 0, meisei_sheets: 0 };
    if (item.supplier === "SATO") {
      value.sato_lots = item.order_lots;
      value.sato_sheets = item.order_sheets || 0;
    } else {
      value.meisei_lots = item.order_lots;
      value.meisei_sheets = item.order_sheets || 0;
    }
    next[`${item.material_id}:${item.required_date}`] = value;
  });
  props.materials.forEach((material) =>
    props.dates.forEach((day) => {
      const value = next[key(material, day)] || { sato_lots: 0, sato_sheets: 0, meisei_sheets: 0 };
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
  await loadManualRows();
};
const save = async () => {
  saving.value = true;
  try {
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
          sato_sheets: Number(entry(material, required_date).sato_sheets || 0),
          meisei_sheets: Number(entry(material, required_date).meisei_sheets || 0),
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
  } catch (e) {
    emit("message", e?.response?.data?.detail || "保存に失敗しました。");
  } finally {
    saving.value = false;
  }
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

const showManualAdd = ref(false);
const manualRows = ref([]);
const manualMaterialOptions = ref([]);
const manualMaterialId = ref("");
const manualSupplier = ref("MEISEI");
const manualDeliveryDate = ref("");
const manualLots = ref(0);
const manualLotMultiple = ref(100);
const manualSheets = ref(0);

const loadManualRows = async () => {
  if (!props.dates.length) return;
  try {
    const res = await api.laserWeeklyPlans.getMaterialOrderSummary(
      props.dates[0],
      props.dates[props.dates.length - 1],
    );
    const rows = (res?.data?.rows || []).flatMap((row) =>
      (res?.data?.dates || [])
        .filter((d) => {
          const daily = row.daily[d];
          return daily && daily.manual_ids?.length;
        })
        .map((d) => ({
          id: row.daily[d].manual_ids[0],
          material_id: row.material_id,
          material_code: row.material_code,
          material_name: row.material_name,
          supplier: row.supplier,
          supplier_label: row.supplier_label,
          delivery_date: d,
          order_lots: row.daily[d].order_lots,
          order_sheets: row.daily[d].order_sheets,
        })),
    );
    manualRows.value = rows;
  } catch {
    manualRows.value = [];
  }
};

const loadManualMaterialOptions = async () => {
  try {
    manualMaterialOptions.value = await api.products.getAllProducts({ category: "MATERIAL" });
  } catch {
    manualMaterialOptions.value = [];
  }
};

const addManualOrder = async () => {
  try {
    await api.laserWeeklyPlans.createMaterialOrderManual({
      material_id: manualMaterialId.value,
      supplier: manualSupplier.value,
      delivery_date: manualDeliveryDate.value,
      order_lots: manualLots.value || 0,
      lot_multiple: manualLotMultiple.value || 0,
      order_sheets: manualSheets.value || 0,
    });
    manualLots.value = 0;
    manualSheets.value = 0;
    emit("message", "手動発注を登録しました。");
    await loadManualRows();
  } catch (e) {
    emit("message", e?.response?.data?.detail || "手動追加に失敗しました。");
  }
};

const deleteManualRow = async (id) => {
  if (!confirm("手動行を削除しますか？")) return;
  try {
    await api.laserWeeklyPlans.deleteMaterialOrderManual(id);
    await loadManualRows();
    emit("message", "手動行を削除しました。");
  } catch (e) {
    emit("message", e?.response?.data?.detail || "削除に失敗しました。");
  }
};

loadManualMaterialOptions();

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
.mat-manual-cell {
  position: relative;
  overflow: visible !important;
}
.mat-inputs-wrap {
  display: flex;
  flex-direction: column;
}
.mat-code-wrap {
  display: flex;
  align-items: center;
  gap: 4px;
}
.mat-unit-labels {
  display: flex;
  flex-direction: column;
  font-size: 8px;
  color: #dc2626;
  line-height: 1.2;
}
.mat-manual-cell:hover::after,
.mat-manual-cell:focus-within::after {
  content: attr(data-tip);
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  background: #333;
  color: #fff;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 3px;
  white-space: nowrap;
  z-index: 100;
  pointer-events: none;
}
.week-total {
  background: #dbeafe !important;
  font-weight: 700;
}
.order-panel th.week-total {
  background: #93c5fd !important;
}
.initial-input {
  width: 28px;
  min-width: 0;
  max-width: 28px;
  padding: 0;
}
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
.sheets-input {
  width: 28px;
  min-width: 0;
  max-width: 28px;
  padding: 0;
  font-size: 10px;
  -moz-appearance: textfield;
}
.sheets-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.sheets-input::placeholder {
  font-size: 9px;
  color: #a78bfa;
}
.manual-add-form {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  flex-wrap: wrap;
  padding: 6px 0;
  font-size: 12px;
}
.manual-add-form label {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.manual-add-form select,
.manual-add-form input {
  height: 28px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 0 4px;
}
.manual-row td {
  background: #fefce8 !important;
}
.manual-tag {
  font-size: 9px;
  font-weight: 700;
  color: #fff;
  background: #f97316;
  padding: 0 3px;
  border-radius: 3px;
}
.sheets-label {
  font-size: 10px;
  color: #7c3aed;
}
.del-btn {
  border: none;
  background: #ef4444;
  color: #fff;
  border-radius: 3px;
  cursor: pointer;
  font-size: 11px;
  padding: 0 4px;
  line-height: 18px;
}
</style>
