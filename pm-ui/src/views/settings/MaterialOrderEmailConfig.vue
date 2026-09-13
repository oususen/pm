<template>
  <div class="page">
    <div class="toolbar">
      <h2>注文書メール設定</h2>
      <button class="btn primary" :disabled="saving || !canEdit || !selectedSupplier" @click="save">
        {{ saving ? "保存中..." : "保存" }}
      </button>
    </div>
    <div class="type-tabs">
      <button :class="['tab', { active: emailType === 'material' }]" @click="emailType = 'material'">材料注文書</button>
      <button :class="['tab', { active: emailType === 'proposal' }]" @click="emailType = 'proposal'">外作・購入品注文</button>
    </div>

    <div class="split-layout">
      <section class="list-panel">
        <h3>設定対象一覧</h3>
        <table class="target-table">
          <thead>
            <tr>
              <th>仕入先</th>
              <th>CC</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="supplier in supplierOptions"
              :key="supplier.value"
              :class="{ active: String(supplier.value) === String(selectedSupplier) }"
              @click="selectSupplier(supplier.value)"
            >
              <td>{{ supplier.label }}</td>
              <td>{{ ccCountLabel(supplier.value) }}</td>
            </tr>
            <tr v-if="!supplierOptions.length">
              <td colspan="2" class="empty-cell">対象仕入先がありません</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="detail-panel">
        <template v-if="selectedSupplier">
          <div class="detail-title">
            <h3>{{ selectedSupplierLabel }}</h3>
            <span class="type-badge">{{ emailTypeLabel }}</span>
          </div>

          <label class="field">
            <span>本文</span>
            <textarea v-model="form.body" rows="10" placeholder="メール本文を入力"></textarea>
          </label>
          <p class="hint">使用可能: {{ placeholderHint }}</p>

          <div class="field">
            <span>CCユーザー</span>
            <UserChipSelect
              v-model="form.cc_users"
              :user-list="users"
              placeholder="社員コード/氏名/ユーザー名で検索してCCに追加"
            />
          </div>
        </template>
        <p v-else class="empty-detail">左の一覧から仕入先を選択してください。</p>

        <p v-if="message" class="message">{{ message }}</p>
        <p v-if="error" class="error">{{ error }}</p>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import api from "@/api/client";
import { authState } from "@/auth";
import { hasPermission } from "@/router";
import UserChipSelect from "@/views/purchase/UserChipSelect.vue";

const materialSupplierOptions = [
  { value: "MEISEI", label: "名成鋼機" },
  { value: "SATO", label: "佐藤商事" },
];

const defaultMaterialBody = `{supplier_name} 御中

いつもお世話になっております。
材料注文書を送付いたします。添付PDFをご確認ください。
このメールは送信専用です。ご返信はCC宛先へお願いします。

ダイソウ工業株式会社`;

const defaultProposalBody = `{supplier_name} 御中

お世話になっております。
発注書を送付いたします。

注文書番号: {proposal_no}
発注日: {order_date}
希望納入日: {desired_delivery_date}

添付のPDFをご確認のうえ、手配をお願いいたします。

------------------------------
ダイソウ工業株式会社
{created_by_name}

ご不明な点がございましたら下記までご連絡ください。
Email:{created_by_email}

このメールは送信専用です。ご返信はCC宛先へお願いします。`;

const emailType = ref("material");
const selectedSupplier = ref("MEISEI");
const materialConfigs = ref({});
const proposalConfigs = ref({});
const users = ref([]);
const suppliers = ref([]);
const saving = ref(false);
const loading = ref(false);
const message = ref("");
const error = ref("");
const form = reactive({
  body: defaultMaterialBody,
  cc_users: [],
});

const normalizeList = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
};

const supplierOptions = computed(() => {
  if (emailType.value === "material") return materialSupplierOptions;
  return suppliers.value.map((supplier) => ({
    value: supplier.id,
    label: `${supplier.supplier_code || ""} ${supplier.supplier_name || ""}`.trim(),
  }));
});

const selectedSupplierLabel = computed(() => supplierOptions.value.find((row) => String(row.value) === String(selectedSupplier.value))?.label || "");
const emailTypeLabel = computed(() => (emailType.value === "material" ? "材料注文書" : "外作・購入品注文"));
const currentConfig = computed(() => {
  if (emailType.value === "material") return materialConfigs.value[selectedSupplier.value] || null;
  return proposalConfigs.value[Number(selectedSupplier.value)] || null;
});
const canEdit = computed(() => hasPermission(authState.user, "settings.material_order_email_config", "edit"));
const placeholderHint = computed(() =>
  emailType.value === "material"
    ? "{supplier_name}=仕入先名、{start_date}=注文書開始日、{end_date}=注文書終了日"
    : "{supplier_name}=仕入先名、{proposal_no}=注文書番号、{order_date}=発注日、{desired_delivery_date}=希望納入日、{created_by_name}=作成者名、{created_by_email}=作成者メール"
);
const defaultBody = computed(() => (emailType.value === "material" ? defaultMaterialBody : defaultProposalBody));

const getConfigBySupplier = (supplierValue) => {
  if (emailType.value === "material") return materialConfigs.value[supplierValue] || null;
  return proposalConfigs.value[Number(supplierValue)] || null;
};

const ccCountLabel = (supplierValue) => {
  const count = getConfigBySupplier(supplierValue)?.cc_users?.length || 0;
  return count ? `${count}人` : "未設定";
};

const applyCurrentConfig = () => {
  const row = currentConfig.value;
  form.body = row?.body || defaultBody.value;
  form.cc_users = Array.isArray(row?.cc_users) ? [...row.cc_users] : [];
  message.value = "";
  error.value = "";
};

const ensureSelectedSupplier = () => {
  if (emailType.value === "material") {
    if (!materialSupplierOptions.some((row) => row.value === selectedSupplier.value)) selectedSupplier.value = "MEISEI";
    return;
  }
  const firstSupplier = suppliers.value[0];
  if (!supplierOptions.value.some((row) => Number(row.value) === Number(selectedSupplier.value))) {
    selectedSupplier.value = firstSupplier?.id || null;
  }
};

const selectSupplier = (value) => {
  selectedSupplier.value = value;
};

const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    const [materialRes, proposalRes, userRes, supplierRes] = await Promise.all([
      api.laserWeeklyPlans.getMaterialOrderEmailConfigs(),
      api.purchaseOrderProposals.getEmailConfigs(),
      api.accounts.getUsers({ is_active: true, page_size: 1000 }),
      api.suppliers.getSuppliers({ page_size: 10000 }),
    ]);
    materialConfigs.value = Object.fromEntries(normalizeList(materialRes.data).map((row) => [row.supplier, row]));
    proposalConfigs.value = Object.fromEntries(normalizeList(proposalRes.data).map((row) => [Number(row.supplier), row]));
    users.value = normalizeList(userRes.data);
    suppliers.value = normalizeList(supplierRes.data);
    ensureSelectedSupplier();
    applyCurrentConfig();
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || "読込に失敗しました。";
  } finally {
    loading.value = false;
  }
};

const save = async () => {
  if (!canEdit.value) {
    error.value = "保存権限がありません。";
    return;
  }
  if (!selectedSupplier.value) {
    error.value = "仕入先を選択してください。";
    return;
  }
  saving.value = true;
  message.value = "";
  error.value = "";
  try {
    const payload = {
      supplier: selectedSupplier.value,
      body: form.body || "",
      cc_users: form.cc_users,
    };
    if (emailType.value === "material") {
      const { data } = await api.laserWeeklyPlans.updateMaterialOrderEmailConfig(selectedSupplier.value, payload);
      materialConfigs.value = { ...materialConfigs.value, [data.supplier]: data };
    } else {
      const { data } = await api.purchaseOrderProposals.updateEmailConfig(selectedSupplier.value, payload);
      proposalConfigs.value = { ...proposalConfigs.value, [Number(data.supplier)]: data };
    }
    message.value = "保存しました。";
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || "保存に失敗しました。";
  } finally {
    saving.value = false;
  }
};

watch(emailType, () => {
  ensureSelectedSupplier();
  applyCurrentConfig();
});
watch(selectedSupplier, applyCurrentConfig);
onMounted(load);
</script>

<style scoped>
.page {
  padding: 10px 12px 16px;
  background: #eef2f6;
  min-height: 100%;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}
h2 {
  margin: 0;
  font-size: 16px;
}
.type-tabs {
  display: flex;
  gap: 0;
  margin-bottom: 10px;
}
.tab {
  padding: 7px 20px;
  font-size: 13px;
  font-weight: 700;
  border: 1px solid #c5cfde;
  background: #e8eef9;
  color: #475569;
  cursor: pointer;
}
.tab:first-child {
  border-radius: 6px 0 0 6px;
}
.tab:last-child {
  border-radius: 0 6px 6px 0;
  border-left: none;
}
.tab.active {
  background: #047857;
  color: #fff;
  border-color: #047857;
}
.split-layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 10px;
}
.list-panel,
.detail-panel {
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 6px;
  padding: 10px;
}
.list-panel h3,
.detail-title h3 {
  margin: 0;
  font-size: 15px;
}
.list-panel h3 {
  margin-bottom: 8px;
}
.target-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.target-table th,
.target-table td {
  border: 1px solid #cbd5e1;
  padding: 7px 8px;
  text-align: left;
}
.target-table th {
  background: #e8eef9;
}
.target-table tbody tr {
  cursor: pointer;
}
.target-table tbody tr.active {
  background: #dbeafe;
}
.empty-cell,
.empty-detail {
  color: #64748b;
  font-size: 13px;
}
.detail-panel {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: flex-start;
  gap: 10px;
}
.detail-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.type-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  background: #e0f2fe;
  color: #0369a1;
  font-size: 12px;
  font-weight: 700;
}
.field {
  display: grid;
  gap: 5px;
  font-size: 13px;
  font-weight: 700;
}
select,
textarea {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 6px 8px;
  font-size: 13px;
  font-weight: 400;
  box-sizing: border-box;
}
textarea {
  resize: vertical;
  line-height: 1.5;
  min-height: 260px;
}
.detail-panel .field {
  flex: 0 0 auto;
}
.hint {
  margin: -4px 0 0;
  font-size: 12px;
  color: #64748b;
}
.message {
  margin: 0;
  color: #047857;
  font-size: 13px;
}
.error {
  margin: 0;
  color: #dc2626;
  font-size: 13px;
}
.btn {
  border: 1px solid #9aa8bd;
  background: #fff;
  border-radius: 4px;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 13px;
}
.btn.primary {
  background: #047857;
  color: #fff;
  border-color: #047857;
}
.btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
</style>
