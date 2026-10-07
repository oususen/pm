<template>
  <section class="order-panel">
    <h3 class="collapsible-header" @click="showOrder = !showOrder">
      {{ showOrder ? "▼" : "▶" }} 材料発注・進度
    </h3>
    <div v-show="showOrder">
      <p>佐藤商事の手数を入力すると、残りの自数を名成鋼機へ自動配分します。手数は上段がロット数(L)、下段が端数枚数(枚)です。</p>
      <p v-if="hasAnyApproval" class="approval-status">
        最新期間: {{ approvalPeriodLabel }} / 佐藤商事: {{ supplierStatusLabel('SATO') }} / 名成鋼機: {{ supplierStatusLabel('MEISEI') }}
      </p>
      <div class="order-period">
        <label>注文書期間<input v-model="orderStartDate" type="date" :min="props.dates[0]" :max="props.dates[props.dates.length - 1]" :disabled="orderPeriodLocked" /></label>
        <span>〜</span>
        <label><input v-model="orderEndDate" type="date" :min="orderStartDate" :max="props.dates[props.dates.length - 1]" :disabled="orderPeriodLocked" /></label>
      </div>
      <div class="actions">
        <div class="action-group creator-group">
          <span class="action-group-title">作成者</span>
          <button class="btn creator-btn" @click="openSaveDialog" :disabled="saving || !hasEditableDate">
            {{ saving ? "保存中..." : "変更を保存" }}</button
          ><button class="btn creator-btn" @click="createApproval('SATO')" :disabled="isCreateOrderDisabled('SATO')">
            {{ createOrderButtonLabel("SATO") }}</button
          ><button class="btn creator-btn" @click="createApproval('MEISEI')" :disabled="isCreateOrderDisabled('MEISEI')">
            {{ createOrderButtonLabel("MEISEI") }}</button
          ><button v-if="canSubmitApproval('SATO')" class="btn creator-btn" @click="submitApproval('SATO')" :disabled="approvalBusy">
            佐藤商事確認依頼</button
          ><button v-if="canSubmitApproval('MEISEI')" class="btn creator-btn" @click="submitApproval('MEISEI')" :disabled="approvalBusy">
            名成鋼機確認依頼</button
          ><button v-if="canReopenApproval('SATO')" class="btn creator-btn" @click="reopenApproval('SATO')" :disabled="approvalBusy">
            佐藤商事修正</button
          ><button v-if="canReopenApproval('MEISEI')" class="btn creator-btn" @click="reopenApproval('MEISEI')" :disabled="approvalBusy">
            名成鋼機修正</button
          ><button class="btn creator-btn" @click="openAdjustmentDialog('SATO')" :disabled="approvalBusy">
            佐藤商事納期調整</button
          ><button class="btn creator-btn" @click="openAdjustmentDialog('MEISEI')" :disabled="approvalBusy">
            名成鋼機納期調整</button
          ><button v-if="canSaveAdjustment('SATO')" class="btn creator-btn" @click="saveAdjustment('SATO')" :disabled="saving">
            佐藤商事納期調整保存</button
          ><button v-if="canSaveAdjustment('MEISEI')" class="btn creator-btn" @click="saveAdjustment('MEISEI')" :disabled="saving">
            名成鋼機納期調整保存</button
          ><button class="btn creator-btn" @click="showManualAdd = !showManualAdd" :disabled="approvalLocked">
            手動追加
          </button>
          <span v-if="!loadingCreatorPermission && !canCreateMaterialOrder" class="creator-permission-note">注文書作成権限がありません</span>
        </div>
        <div v-if="hasReviewerActions" class="action-group reviewer-group">
          <span class="action-group-title">確認者</span>
          <button v-if="canConfirm('SATO')" class="btn reviewer-btn" @click="confirmApproval('SATO')" :disabled="approvalBusy">
            佐藤商事確認</button
          ><button v-if="canConfirm('MEISEI')" class="btn reviewer-btn" @click="confirmApproval('MEISEI')" :disabled="approvalBusy">
            名成鋼機確認</button
          ><button v-if="canConfirm('SATO')" class="btn reject-btn" @click="rejectApproval('SATO')" :disabled="approvalBusy">
            佐藤商事却下</button
          ><button v-if="canConfirm('MEISEI')" class="btn reject-btn" @click="rejectApproval('MEISEI')" :disabled="approvalBusy">
            名成鋼機却下</button>
        </div>
        <div v-if="hasApproverActions" class="action-group approver-group">
          <span class="action-group-title">承認者</span>
          <button v-if="canApprove('SATO')" class="btn approver-btn" @click="approveApproval('SATO')" :disabled="approvalBusy">
            佐藤商事承認</button
          ><button v-if="canApprove('MEISEI')" class="btn approver-btn" @click="approveApproval('MEISEI')" :disabled="approvalBusy">
            名成鋼機承認</button
          ><button v-if="canApprove('SATO')" class="btn reject-btn" @click="rejectApproval('SATO')" :disabled="approvalBusy">
            佐藤商事却下</button
          ><button v-if="canApprove('MEISEI')" class="btn reject-btn" @click="rejectApproval('MEISEI')" :disabled="approvalBusy">
            名成鋼機却下</button
          ><button v-if="canSendOrder('SATO')" class="btn approver-btn" @click="sendOrder('SATO')" :disabled="approvalBusy">
            佐藤商事送信</button
          ><button v-if="canSendOrder('MEISEI')" class="btn approver-btn" @click="sendOrder('MEISEI')" :disabled="approvalBusy">
            名成鋼機送信</button>
        </div>
        <div class="action-group common-group">
          <span class="action-group-title">共通</span>
          <button class="btn common-btn" @click="openDownload('SATO', 'pdf')">
            佐藤商事注文書開く</button
          ><button class="btn common-btn" @click="openDownload('SATO', 'excel')">
            佐藤商事Excel</button
          ><button class="btn common-btn" @click="openDownload('MEISEI', 'pdf')">
            名成鋼機注文書開く</button
          ><button class="btn common-btn" @click="openDownload('MEISEI', 'excel')">
            名成鋼機Excel</button
          ><button class="btn common-btn" @click="openEmailConfig">
            メール設定</button>
        </div>
        <div v-if="hasSystemActions" class="action-group system-group">
          <span class="action-group-title">システム管理者</span>
          <button class="btn system-btn" @click="resetApproval" :disabled="approvalBusy">
            承認リセット</button>
        </div>
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
        <label>枚/ロット<input v-model.number="manualLotMultiple" type="number" min="0" style="width:60px;" /></label>
        <label>端数枚数<input v-model.number="manualSheets" type="number" min="0" style="width:60px;" /></label>
        <button class="btn primary" @click="addManualOrder" :disabled="approvalLocked || !manualMaterialId || !manualDeliveryDate || (manualLots === 0 && manualSheets === 0)">登録</button>
      </div>
      <div
        v-if="downloadDialog"
        class="download-modal"
        @click.self="downloadDialog = false"
      >
        <section class="download-dialog">
          <h3>
            {{ downloadSupplier === "SATO" ? "佐藤商事" : "名成鋼機" }}注文書{{ downloadFormat === "pdf" ? "PDF" : "Excel" }}
          </h3>
          <label>開始日<input v-model="downloadStartDate" type="date" /></label
          ><label>終了日<input v-model="downloadEndDate" type="date" /></label>
          <div class="dialog-actions">
            <button class="btn primary" @click="download">{{ downloadFormat === "pdf" ? "開く" : "出力" }}</button
            ><button class="btn" @click="downloadDialog = false">
              キャンセル
            </button>
          </div>
        </section>
      </div>
      <div
        v-if="adjustmentDialog"
        class="download-modal"
        @click.self="adjustmentDialog = false"
      >
        <section class="download-dialog">
          <h3>{{ supplierName(adjustmentSupplier) }}納期調整</h3>
          <label>開始日<input v-model="adjustmentStartDate" type="date" :min="props.dates[0]" :max="props.dates[props.dates.length - 1]" /></label
          ><label>終了日<input v-model="adjustmentEndDate" type="date" :min="adjustmentStartDate" :max="props.dates[props.dates.length - 1]" /></label>
          <div class="dialog-actions">
            <button class="btn primary" @click="startAdjustment" :disabled="approvalBusy">
              調整開始</button
            ><button class="btn" @click="adjustmentDialog = false" :disabled="approvalBusy">
              キャンセル
            </button>
          </div>
        </section>
      </div>
      <div
        v-if="saveDialog"
        class="download-modal"
        @click.self="saveDialog = false"
      >
        <section class="save-dialog">
          <h3>手数変更を保存</h3>
          <div class="save-week-buttons">
            <button
              v-for="week in saveWeekOptions"
              :key="week.key"
              class="btn"
              :class="{ primary: selectedSaveWeekKeys.includes(week.key) }"
              type="button"
              @click="toggleSaveWeek(week.key)"
            >
              {{ week.shortLabel }}
            </button>
            <button
              class="btn"
              :class="{ primary: allSaveWeeksSelected }"
              type="button"
              @click="toggleAllSaveWeeks(true)"
            >
              全期間
            </button>
          </div>
          <div class="dialog-actions">
            <button class="btn primary" @click="save" :disabled="saving || !canSaveSelectedDates">
              保存</button
            ><button class="btn" @click="saveDialog = false" :disabled="saving">
              キャンセル
            </button>
          </div>
        </section>
      </div>
      <div class="material-filters">
        <label>材料コード<select v-model="filterMaterialCode">
          <option value="">全て</option>
          <option v-for="code in filterMaterialCodeOptions" :key="code" :value="code">{{ code }}</option>
        </select></label>
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
                :class="{ 'holiday-work': props.holidayWorkDates.includes(day) }"
              >
                {{ dayLabel(day) }}
              </th>
              <th class="week-total week-end" colspan="4">週合計</th></template
            >
          </tr>
          <tr>
            <template v-for="week in weekGroups" :key="`${week.key}-labels`"
              ><template v-for="day in week.days" :key="`${day}-labels`"
                ><th :class="{ 'holiday-work': props.holidayWorkDates.includes(day) }">需要</th>
                <th :class="{ 'holiday-work': props.holidayWorkDates.includes(day) }">自数</th>
                <th class="manual-cell" :class="{ 'holiday-work': props.holidayWorkDates.includes(day) }">手数</th>
                <th class="date-end" :class="{ 'holiday-work': props.holidayWorkDates.includes(day) }">進度</th></template
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
            v-for="(material, materialIndex) in filteredMaterials"
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
                  :disabled="approvalLocked || initial(material).locked"
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
                        :disabled="isDateLocked(day, supplier.code)"
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
                        :disabled="isDateLocked(day, supplier.code)"
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
                  <button class="del-btn" @click="deleteManualRow(row.id)" :disabled="approvalLocked" title="削除">×</button>
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
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import api from "@/api/client";
import { authState } from "@/auth";
const props = defineProps({
  startDate: { type: String, required: true },
  dates: { type: Array, required: true },
  holidayWorkDates: { type: Array, default: () => [] },
  materials: { type: Array, required: true },
});
const emit = defineEmits(["message"]);
const router = useRouter();
const suppliers = [
  { code: "SATO", name: "佐藤商事" },
  { code: "MEISEI", name: "名成鋼機" },
];
const openEmailConfig = () => {
  router.push("/settings/material-order-email-config");
};
const iso = (date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
const filterMaterialCode = ref("");
const filterMaterialCodeOptions = computed(() =>
  [...new Set(props.materials.map((m) => m.material_code))].sort(),
);
const filteredMaterials = computed(() =>
  filterMaterialCode.value
    ? props.materials.filter((m) => m.material_code === filterMaterialCode.value)
    : props.materials,
);
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
const saveWeekOptions = computed(() =>
  weekGroups.value.map((week, index) => ({
    key: week.key,
    shortLabel: `${index + 1}週目`,
    label: `${index + 1}週目 ${week.days[0]?.slice(5).replace("-", "/")}～${week.days[week.days.length - 1]?.slice(5).replace("-", "/")}`,
    days: week.days,
  })),
);
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
// 現在の開始週でDBに保存済みの「材料ID:必要日」。全項目0でも保存対象にして0へ更新するため。
const savedOrderKeys = ref(new Set());
const initials = ref({});
const showOrder = ref(true);
const saving = ref(false);
const saveDialog = ref(false);
const selectedSaveWeekKeys = ref([]);
const approvals = ref({ SATO: null, MEISEI: null });
const overlappingApprovals = ref([]);
const approvalBusy = ref(false);
const materialOrderRoute = ref(null);
const loadingCreatorPermission = ref(true);
const defaultOrderStart = () => {
  const start = new Date(`${props.startDate}T00:00:00`);
  const dayIndex = (start.getDay() + 6) % 7;
  start.setDate(start.getDate() + 7 - dayIndex);
  return iso(start);
};
const defaultOrderEnd = () => {
  const start = new Date(`${defaultOrderStart()}T00:00:00`);
  start.setDate(start.getDate() + 4);
  return iso(start);
};
const orderStartDate = ref('');
const orderEndDate = ref('');
const supplierName = (supplier) => (supplier === "SATO" ? "佐藤商事" : "名成鋼機");
const supplierApproval = (supplier) => approvals.value?.[supplier] || null;
const supplierApprovalList = computed(() => [supplierApproval("SATO"), supplierApproval("MEISEI")].filter(Boolean));
const hasAnyApproval = computed(() => supplierApprovalList.value.length > 0);
const setSupplierApproval = (data) => {
  const supplier = data?.context?.supplier;
  if (!supplier) return;
  approvals.value = { ...approvals.value, [supplier]: data };
};
const approvalPeriodLabel = computed(() => {
  const context = supplierApprovalList.value[0]?.context || {};
  const start = context.lock_start_date || orderStartDate.value;
  const end = context.lock_end_date || orderEndDate.value;
  if (!start && !end) return "-";
  return `${start || "-"} ～ ${end || "-"}`;
});
const supplierStatusLabel = (supplier) => {
  const row = supplierApproval(supplier);
  if (!row) return "未作成";
  const editing = row.status === 'created' && row.context?.order_created === false ? " / 修正中" : "";
  const adjusting = row.context?.material_order_adjustments?.[supplier]?.editing ? " / 納期調整中" : "";
  const sent = row.context?.material_order_sent_files?.[supplier] ? " / 送信済" : "";
  const saved = row.context?.material_order_pdf_files?.[supplier] ? " / PDF保存済" : "";
  return `${row.status_label || row.status}（${row.current_stage_label || row.current_stage}）${editing}${adjusting}${saved}${sent}`;
};
const isAdjustmentEditingDate = (row, day) => {
  const supplier = row?.context?.supplier;
  const adjustment = supplier ? row?.context?.material_order_adjustments?.[supplier] : null;
  return Boolean(
    adjustment?.editing &&
    adjustment.lock_start_date &&
    adjustment.lock_end_date &&
    day >= adjustment.lock_start_date &&
    day <= adjustment.lock_end_date,
  );
};
const isApprovalDateLocked = (row, day) => {
  if (!row) return false;
  if (!['created', 'reviewing', 'approved', 'sent'].includes(row.status)) return false;
  if (row.status === 'created' && row.context?.order_created === false) return false;
  if (isAdjustmentEditingDate(row, day)) return false;
  const start = row.context?.lock_start_date || orderStartDate.value;
  const end = row.context?.lock_end_date || orderEndDate.value;
  return Boolean(start && end && day >= start && day <= end);
};
const isDateLocked = (day, supplier = null) => {
  if (supplier) return isApprovalDateLocked(supplierApproval(supplier), day) || overlappingApprovals.value.some((row) => isApprovalDateLocked(row, day));
  return supplierApprovalList.value.some((row) => isApprovalDateLocked(row, day)) || overlappingApprovals.value.some((row) => isApprovalDateLocked(row, day));
};
const approvalLocked = computed(() => supplierApprovalList.value.some((row) => ['reviewing', 'approved', 'sent'].includes(row.status)));
const orderPeriodLocked = computed(() => supplierApprovalList.value.some(
  (row) => ['reviewing', 'approved', 'sent'].includes(row.status) || (row.status === 'created' && row.context?.order_created !== false),
));
const isAnySupplierDateEditable = (day) => suppliers.some((supplier) => !isDateLocked(day, supplier.code));
const hasEditableDate = computed(() => props.dates.some((day) => isAnySupplierDateEditable(day)));
const allSaveWeeksSelected = computed(() =>
  saveWeekOptions.value.length > 0 && selectedSaveWeekKeys.value.length === saveWeekOptions.value.length,
);
const selectedSaveDates = computed(() => {
  const keys = new Set(selectedSaveWeekKeys.value);
  return saveWeekOptions.value
    .filter((week) => keys.has(week.key))
    .flatMap((week) => week.days);
});
const canSaveSelectedDates = computed(() =>
  selectedSaveDates.value.length > 0 && selectedSaveDates.value.some((day) => isAnySupplierDateEditable(day)),
);
const toggleAllSaveWeeks = (checked) => {
  selectedSaveWeekKeys.value = checked ? saveWeekOptions.value.map((week) => week.key) : [];
};
const toggleSaveWeek = (weekKey) => {
  selectedSaveWeekKeys.value = selectedSaveWeekKeys.value.includes(weekKey)
    ? selectedSaveWeekKeys.value.filter((key) => key !== weekKey)
    : [...selectedSaveWeekKeys.value, weekKey];
};
const openSaveDialog = () => {
  saveDialog.value = true;
};
const currentUserId = computed(() => Number(authState.user?.id || 0));
const profileDepartmentField = {
  division: 'division',
  group: 'group',
  team: 'team',
  unit: 'unit',
};
const profileDepartmentId = (profile, level) => {
  const field = profileDepartmentField[level];
  if (!field) return null;
  return profile?.[`${field}_id`] ?? profile?.[field] ?? null;
};
const canCreateMaterialOrder = computed(() => {
  const route = materialOrderRoute.value;
  const user = authState.user;
  if (!route || !route.is_active || !user?.id) return false;

  const authorizedUsers = (route.creator_authorized_users || []).map(Number);
  if (authorizedUsers.includes(Number(user.id))) return true;

  const allowedUsers = (route.creator_allowed_users || []).map(Number);
  if (allowedUsers.length) return allowedUsers.includes(Number(user.id));

  const profile = user.profile || {};
  if (String(profile.role || '') !== String(route.creator_role || '')) return false;

  if (!route.creator_department) return true;
  return Number(profileDepartmentId(profile, route.creator_department_level)) === Number(route.creator_department);
});
const loadMaterialOrderRoute = async () => {
  loadingCreatorPermission.value = true;
  try {
    const response = await api.accounts.getApprovalRoutes({ search: 'laser_material_order' });
    const routes = Array.isArray(response.data) ? response.data : response.data?.results || [];
    materialOrderRoute.value = routes.find((route) => route.item_key === 'laser_material_order') || null;
  } catch {
    materialOrderRoute.value = null;
  } finally {
    loadingCreatorPermission.value = false;
  }
};
const canResetApproval = computed(() => authState.user?.username === "admin" || authState.user?.is_superuser === true);
const hasPendingTask = (row, taskType) => Boolean(row?.tasks?.some(
  (task) => task.status === "PENDING" && task.task_type === taskType && Number(task.assigned_to) === currentUserId.value,
));
const hasSavedOrderPdf = (supplier) => Boolean(supplierApproval(supplier)?.context?.material_order_pdf_files?.[supplier]);
const hasSentOrderPdf = (supplier) => Boolean(supplierApproval(supplier)?.context?.material_order_sent_files?.[supplier]);
const canSubmitApproval = (supplier) => {
  const row = supplierApproval(supplier);
  return row && ['created', 'rejected'].includes(row.status) && row.context?.order_created !== false;
};
const canReopenApproval = (supplier) => {
  const row = supplierApproval(supplier);
  return row?.status === 'created' && row.context?.order_created !== false;
};
const canSaveAdjustment = (supplier) => {
  const row = supplierApproval(supplier);
  return Boolean(row?.context?.material_order_adjustments?.[supplier]?.editing);
};
const createOrderButtonLabel = (supplier) => {
  const row = supplierApproval(supplier);
  const prefix = supplierName(supplier);
  return row?.status === "rejected" || row?.context?.order_created === false
    ? `${prefix}注文書再作成`
    : `${prefix}注文書作成`;
};
const canSendOrder = (supplier) => {
  const row = supplierApproval(supplier);
  return ['approved', 'sent'].includes(row?.status) && hasSavedOrderPdf(supplier) && !hasSentOrderPdf(supplier);
};
const isCreateOrderDisabled = (supplier) => {
  const row = supplierApproval(supplier);
  return !canCreateMaterialOrder.value ||
    loadingCreatorPermission.value ||
    approvalBusy.value ||
    row?.status === 'reviewing' ||
    row?.status === 'approved' ||
    row?.status === 'sent' ||
    (hasSavedOrderPdf(supplier) && row?.status !== 'rejected' && row?.context?.order_created !== false);
};
const canConfirm = (supplier) => {
  const row = supplierApproval(supplier);
  return row?.status === "reviewing" && ['reviewer1', 'reviewer2'].includes(row.current_stage) && hasPendingTask(row, `${row.current_stage.toUpperCase()}_REVIEW`);
};
const canApprove = (supplier) => {
  const row = supplierApproval(supplier);
  return row?.status === "reviewing" && row.current_stage === "approver" && hasPendingTask(row, "APPROVER_APPROVE");
};
const hasReviewerActions = computed(() => canConfirm("SATO") || canConfirm("MEISEI"));
const hasApproverActions = computed(() =>
  canApprove("SATO") || canApprove("MEISEI") || canSendOrder("SATO") || canSendOrder("MEISEI"),
);
const hasSystemActions = computed(() => canResetApproval.value);
const downloadDialog = ref(false);
const downloadSupplier = ref("");
const downloadFormat = ref("pdf");
const downloadStartDate = ref("");
const downloadEndDate = ref("");
const adjustmentDialog = ref(false);
const adjustmentSupplier = ref("MEISEI");
const adjustmentStartDate = ref("");
const adjustmentEndDate = ref("");
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
  const [orders, initialProgress, approvalResponse] = await Promise.all([
    api.laserWeeklyPlans.getMaterialOrderProgress(props.startDate, props.dates[0] || '', props.dates[props.dates.length - 1] || ''),
    api.laserWeeklyPlans.getMaterialInitialProgress(props.startDate),
    api.laserWeeklyPlans.getMaterialOrderApproval(props.startDate, props.dates[0] || '', props.dates[props.dates.length - 1] || ''),
  ]);
  const approvalMap = approvalResponse.data?.approvals || {};
  approvals.value = { SATO: approvalMap.SATO || null, MEISEI: approvalMap.MEISEI || null };
  overlappingApprovals.value = approvalResponse.data?.overlapping_approvals || [];
  const firstApproval = approvals.value.SATO || approvals.value.MEISEI || null;
  orderStartDate.value = firstApproval?.context?.lock_start_date || defaultOrderStart();
  orderEndDate.value = firstApproval?.context?.lock_end_date || defaultOrderEnd();
  const next = {};
  savedOrderKeys.value = new Set(
    (orders.data.items || []).map((item) => `${item.material_id}:${item.required_date}`),
  );
  const applyOrderItem = (item, target) => {
    const k = `${item.material_id}:${item.required_date}`;
    const value = target[k] || { sato_sheets: 0, meisei_sheets: 0 };
    if (item.supplier === "SATO") {
      value.sato_lots = item.order_lots;
      value.sato_sheets = item.order_sheets || 0;
    } else {
      value.meisei_lots = item.order_lots;
      value.meisei_sheets = item.order_sheets || 0;
    }
    target[k] = value;
  };
  (orders.data.overlapping_items || []).forEach((item) => applyOrderItem(item, next));
  (orders.data.items || []).forEach((item) => applyOrderItem(item, next));
  // 注文書作成済み期間は、開始週を切り替えても注文書ロック時の手数を優先する。
  (orders.data.locked_items || []).forEach((item) => applyOrderItem(item, next));
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
const targetSaveDates = (startDate = null, endDate = null) =>
  props.dates.filter((day) => (!startDate || day >= startDate) && (!endDate || day <= endDate));
const buildMaterialOrderItems = (saveDates = props.dates) =>
  props.materials.flatMap((material) =>
    saveDates
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
      // 保存済みの行は、手数を0に戻した場合も送って0へ更新する。
      .filter((item) =>
        item.required_sheets > 0 || item.sato_lots || item.meisei_lots || item.sato_sheets || item.meisei_sheets ||
        savedOrderKeys.value.has(`${item.material_id}:${item.required_date}`),
      ),
  );
const buildInitialItems = () =>
  props.materials.map((material) => ({
      material_id: material.material_id,
      initial_progress: Number(initial(material).value || 0),
      is_locked: initial(material).locked,
    }));
const buildDailyProgressItems = (targetDates = props.dates) =>
  props.materials.flatMap((material) =>
    targetDates.map((day) => ({
      material_id: material.material_id,
      progress_date: day,
      progress: combinedProgress(material, day),
    })),
  );
const saveMaterialOrderChanges = async (saveDates = props.dates) => {
  await Promise.all([
      api.laserWeeklyPlans.saveMaterialOrderProgress(props.startDate, buildMaterialOrderItems(saveDates)),
      api.laserWeeklyPlans.saveMaterialInitialProgress(
        props.startDate,
        buildInitialItems(),
      ),
      api.laserWeeklyPlans.saveMaterialDailyProgress(buildDailyProgressItems(saveDates)),
    ]);
  // 保存対象に週末を含む週だけ、翌週の期首へ引き継ぐ。
  const savedDates = new Set(saveDates);
  const carryovers = weekGroups.value.flatMap((week) => {
    const lastDay = week.days[week.days.length - 1];
    if (!savedDates.has(lastDay)) return [];
    return props.materials.map((material) => ({
      material_id: material.material_id,
      week_end_date: lastDay,
      progress: combinedProgress(material, lastDay),
    }));
  });
  await api.laserWeeklyPlans.saveMaterialWeekCarryover(carryovers);
};
const save = async () => {
  saving.value = true;
  try {
    if (!selectedSaveDates.value.length) {
      emit("message", "保存対象の週を選択してください。");
      return;
    }
    await saveMaterialOrderChanges(selectedSaveDates.value);
    emit("message", `材料発注進度を保存しました。対象日数: ${selectedSaveDates.value.length}`);
    saveDialog.value = false;
    await load();
  } catch (e) {
    emit("message", e?.response?.data?.detail || "保存に失敗しました。");
  } finally {
    saving.value = false;
  }
};
const submitApproval = async (supplier) => {
  approvalBusy.value = true;
  try {
    const result = await api.accounts.submitApprovalRequest(supplierApproval(supplier).id);
    setSupplierApproval(result.data);
    emit("message", `${supplierName(supplier)}の確認依頼を送信しました。`);
  } catch (e) {
    emit("message", e?.response?.data?.detail || "確認依頼に失敗しました。");
  } finally {
    approvalBusy.value = false;
  }
};
const createApproval = async (supplier) => {
  if (!canCreateMaterialOrder.value) {
    emit("message", "注文書作成権限がありません。");
    return;
  }
  approvalBusy.value = true;
  try {
    if (!orderStartDate.value || !orderEndDate.value || orderEndDate.value < orderStartDate.value) {
      emit("message", "注文書期間を正しく指定してください。");
      return;
    }
    await saveMaterialOrderChanges(targetSaveDates(orderStartDate.value, orderEndDate.value));
    const result = await api.laserWeeklyPlans.createMaterialOrderApproval(props.startDate, orderStartDate.value, orderEndDate.value, supplier);
    setSupplierApproval(result.data);
    emit("message", `${supplierName(supplier)}の変更を保存し、注文書PDFをサーバーに保存しました。`);
  } catch (e) {
    emit("message", e?.response?.data?.detail || "作成済み処理に失敗しました。");
  } finally {
    approvalBusy.value = false;
  }
};
const reopenApproval = async (supplier) => {
  if (!confirm(`${supplierName(supplier)}注文書を修正状態に戻しますか？`)) return;
  approvalBusy.value = true;
  try {
    const result = await api.laserWeeklyPlans.reopenMaterialOrderApproval(props.startDate, orderStartDate.value, orderEndDate.value, supplier);
    setSupplierApproval(result.data);
    emit("message", `${supplierName(supplier)}注文書を修正できる状態に戻しました。修正後は注文書を再作成してください。`);
  } catch (e) {
    emit("message", e?.response?.data?.detail || "注文書修正に失敗しました。");
  } finally {
    approvalBusy.value = false;
  }
};
const openAdjustmentDialog = (supplier) => {
  const ok = confirm(
    `${supplierName(supplier)}の納期調整を開始します。\n\n` +
    '・元の注文書PDFは削除しません。\n' +
    '・承認フローは流れません。\n' +
    '・調整保存時に「納期変更」のPDFを別ファイルで作成します。\n\n' +
    '続行しますか？',
  );
  if (!ok) return;
  adjustmentSupplier.value = supplier;
  adjustmentStartDate.value = defaultOrderStart();
  adjustmentEndDate.value = defaultOrderEnd();
  adjustmentDialog.value = true;
};
const startAdjustment = async () => {
  const supplier = adjustmentSupplier.value;
  if (!adjustmentStartDate.value || !adjustmentEndDate.value || adjustmentEndDate.value < adjustmentStartDate.value) {
    emit("message", "納期調整期間を正しく指定してください。");
    return;
  }
  approvalBusy.value = true;
  try {
    const result = await api.laserWeeklyPlans.adjustMaterialOrderApproval(
      props.startDate,
      adjustmentStartDate.value,
      adjustmentEndDate.value,
      supplier,
    );
    setSupplierApproval(result.data);
    orderStartDate.value = adjustmentStartDate.value;
    orderEndDate.value = adjustmentEndDate.value;
    adjustmentDialog.value = false;
    emit("message", `${supplierName(supplier)}の納期調整期間を編集できる状態にしました。調整後は納期調整保存を押してください。`);
  } catch (e) {
    emit("message", e?.response?.data?.detail || "納期調整開始に失敗しました。");
  } finally {
    approvalBusy.value = false;
  }
};
const saveAdjustment = async (supplier) => {
  const row = supplierApproval(supplier);
  const adjustment = row?.context?.material_order_adjustments?.[supplier] || {};
  const start = adjustment.lock_start_date || row?.context?.lock_start_date || orderStartDate.value;
  const end = adjustment.lock_end_date || row?.context?.lock_end_date || orderEndDate.value;
  if (!start || !end || end < start) {
    emit("message", "納期調整期間を正しく指定してください。");
    return;
  }
  saving.value = true;
  try {
    const saveDates = targetSaveDates(start, end);
    await saveMaterialOrderChanges(saveDates);
    const result = await api.laserWeeklyPlans.saveMaterialOrderAdjustment(props.startDate, start, end, supplier);
    setSupplierApproval(result.data?.approval);
    emit("message", `${supplierName(supplier)}の納期調整を保存し、納期変更PDFを作成しました。対象日数: ${saveDates.length}`);
    await load();
  } catch (e) {
    emit("message", e?.response?.data?.detail || "納期調整保存に失敗しました。");
  } finally {
    saving.value = false;
  }
};
const sendOrder = async (supplier) => {
  approvalBusy.value = true;
  try {
    const result = await api.laserWeeklyPlans.sendMaterialOrder(props.startDate, supplier, orderStartDate.value, orderEndDate.value);
    setSupplierApproval(result.data);
    emit("message", `${supplierName(supplier)}へ注文書を送信しました。`);
  } catch (e) {
    emit("message", e?.response?.data?.detail || "注文書送信に失敗しました。");
  } finally {
    approvalBusy.value = false;
  }
};
const resetApproval = async () => {
  if (!confirm("この注文書期間の材料発注承認・タスク・保存PDFをリセットしますか？")) return;
  approvalBusy.value = true;
  try {
    const result = await api.laserWeeklyPlans.resetMaterialOrderApproval(props.startDate, orderStartDate.value, orderEndDate.value);
    approvals.value = { SATO: null, MEISEI: null };
    orderStartDate.value = defaultOrderStart();
    orderEndDate.value = defaultOrderEnd();
    emit("message", `注文書期間の承認をリセットしました。削除件数: ${result.data?.deleted_count ?? 0}`);
  } catch (e) {
    emit("message", e?.response?.data?.detail || "承認リセットに失敗しました。");
  } finally {
    approvalBusy.value = false;
  }
};
const confirmApproval = async (supplier) => {
  approvalBusy.value = true;
  try {
    const result = await api.accounts.confirmApprovalRequest(supplierApproval(supplier).id);
    setSupplierApproval(result.data);
    emit("message", `${supplierName(supplier)}を確認しました。`);
  } catch (e) {
    emit("message", e?.response?.data?.detail || "確認に失敗しました。");
  } finally {
    approvalBusy.value = false;
  }
};
const approveApproval = async (supplier) => {
  approvalBusy.value = true;
  try {
    const result = await api.accounts.approveApprovalRequest(supplierApproval(supplier).id);
    setSupplierApproval(result.data);
    emit("message", `${supplierName(supplier)}を承認しました。`);
  } catch (e) {
    emit("message", e?.response?.data?.detail || "承認に失敗しました。");
  } finally {
    approvalBusy.value = false;
  }
};
const rejectApproval = async (supplier) => {
  const row = supplierApproval(supplier);
  const reason = window.prompt("却下理由を入力してください。", row?.reject_reason || "");
  if (reason === null) return;
  approvalBusy.value = true;
  try {
    const result = await api.accounts.rejectApprovalRequest(row.id, reason);
    setSupplierApproval(result.data);
    emit("message", `${supplierName(supplier)}を却下しました。`);
  } catch (e) {
    emit("message", e?.response?.data?.detail || "却下に失敗しました。");
  } finally {
    approvalBusy.value = false;
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

onMounted(() => {
  loadManualMaterialOptions();
  loadMaterialOrderRoute();
});

const openDownload = (supplier, format = "pdf") => {
  const start = new Date(`${props.startDate}T00:00:00`);
  start.setDate(start.getDate() + 7);
  const end = new Date(start);
  end.setDate(end.getDate() + 4);
  downloadSupplier.value = supplier;
  downloadFormat.value = format;
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
    const exportMethod = downloadFormat.value === "excel"
      ? api.laserWeeklyPlans.exportMaterialOrderExcel
      : api.laserWeeklyPlans.exportMaterialOrderPdf;
    const extension = downloadFormat.value === "excel" ? "xlsx" : "pdf";
    const response = await exportMethod(
      props.startDate,
      downloadSupplier.value,
      downloadStartDate.value,
      downloadEndDate.value,
    );
    const url = URL.createObjectURL(response.data);
    if (downloadFormat.value === "pdf") {
      window.open(url, "_blank", "noopener");
      downloadDialog.value = false;
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      return;
    }
    const a = document.createElement("a");
    a.href = url;
    a.download = `材料注文書_${downloadSupplier.value}_${downloadStartDate.value}_${downloadEndDate.value}.${extension}`;
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
watch(saveWeekOptions, (weeks) => {
  const validKeys = new Set(weeks.map((week) => week.key));
  selectedSaveWeekKeys.value = selectedSaveWeekKeys.value.filter((key) => validKeys.has(key));
}, {
  immediate: true,
});
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
  align-items: stretch;
  gap: 8px;
  width: max-content;
  margin-bottom: 8px;
  padding: 4px 0;
  background: #eef3f8;
}
.action-group {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 6px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #fff;
}
.action-group-title {
  min-width: 52px;
  font-size: 11px;
  font-weight: 700;
  text-align: center;
  white-space: nowrap;
}
.creator-group {
  border-color: #8ec7ad;
  background: #ecfdf5;
}
.creator-permission-note {
  color: #b91c1c;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}
.reviewer-group {
  border-color: #f0c66d;
  background: #fffbeb;
}
.approver-group {
  border-color: #9ab5e8;
  background: #eff6ff;
}
.common-group {
  border-color: #c4b5fd;
  background: #f5f3ff;
}
.system-group {
  border-color: #f3a2a2;
  background: #fef2f2;
}
.save-week-buttons {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin: 4px 0 8px;
}
.save-dialog {
  display: grid;
  gap: 10px;
  min-width: 240px;
  padding: 16px;
  background: #fff;
  border-radius: 6px;
}
.save-dialog h3 {
  margin: 0;
  font-size: 14px;
}
.btn {
  border: 1px solid #94a3b8;
  background: #fff;
  border-radius: 4px;
  padding: 5px 8px;
  cursor: pointer;
  white-space: nowrap;
}
.creator-btn {
  color: #065f46;
  border-color: #34d399;
  background: #d1fae5;
}
.reviewer-btn {
  color: #7c2d12;
  border-color: #f59e0b;
  background: #fef3c7;
}
.approver-btn {
  color: #1e3a8a;
  border-color: #60a5fa;
  background: #dbeafe;
}
.common-btn {
  color: #4c1d95;
  border-color: #a78bfa;
  background: #ede9fe;
}
.system-btn,
.reject-btn {
  color: #7f1d1d;
  border-color: #f87171;
  background: #fee2e2;
}
.primary {
  background: #0f766e;
  color: #fff;
  border-color: #0f766e;
}
.btn:disabled,
.creator-btn:disabled,
.reviewer-btn:disabled,
.approver-btn:disabled,
.common-btn:disabled,
.system-btn:disabled,
.reject-btn:disabled {
  color: #94a3b8;
  border-color: #cbd5e1;
  background: #e5e7eb;
  cursor: not-allowed;
  opacity: 0.75;
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
.material-filters {
  display: flex;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 12px;
}
.material-filters select {
  margin-left: 4px;
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
.order-panel thead th.holiday-work {
  background: #fed7aa;
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
