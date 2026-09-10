<template>
  <div class="page">
    <div class="toolbar">
      <h2>材料注文書メール設定</h2>
      <button class="btn primary" :disabled="saving" @click="save">
        {{ saving ? "保存中..." : "保存" }}
      </button>
    </div>

    <section class="panel">
      <label class="field">
        <span>仕入先</span>
        <select v-model="selectedSupplier">
          <option v-for="supplier in supplierOptions" :key="supplier.value" :value="supplier.value">
            {{ supplier.label }}
          </option>
        </select>
      </label>

      <label class="field">
        <span>本文</span>
        <textarea v-model="form.body" rows="10" placeholder="メール本文を入力"></textarea>
      </label>
      <p class="hint">
        使用可能: {supplier_name}=仕入先名、{start_date}=注文書開始日、{end_date}=注文書終了日
      </p>

      <div class="field">
        <span>CCユーザー</span>
        <UserChipSelect
          v-model="form.cc_users"
          :user-list="users"
          placeholder="社員コード/氏名/ユーザー名で検索してCCに追加"
        />
      </div>

      <p v-if="message" class="message">{{ message }}</p>
      <p v-if="error" class="error">{{ error }}</p>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import api from "@/api/client";
import UserChipSelect from "@/views/purchase/UserChipSelect.vue";

const supplierOptions = [
  { value: "MEISEI", label: "名成鋼機" },
  { value: "SATO", label: "佐藤商事" },
];

const defaultBody = `{supplier_name} 御中

いつもお世話になっております。
材料注文書を送付いたします。添付PDFをご確認ください。
このメールは送信専用です。ご返信はCC宛先へお願いします。

ダイソウ工業株式会社`;

const selectedSupplier = ref("MEISEI");
const configs = ref({});
const users = ref([]);
const saving = ref(false);
const loading = ref(false);
const message = ref("");
const error = ref("");
const form = reactive({
  body: defaultBody,
  cc_users: [],
});

const normalizeList = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
};

const currentConfig = computed(() => configs.value[selectedSupplier.value] || null);

const applyCurrentConfig = () => {
  const row = currentConfig.value;
  form.body = row?.body || defaultBody;
  form.cc_users = Array.isArray(row?.cc_users) ? [...row.cc_users] : [];
  message.value = "";
  error.value = "";
};

const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    const [configRes, userRes] = await Promise.all([
      api.laserWeeklyPlans.getMaterialOrderEmailConfigs(),
      api.accounts.getUsers({ is_active: true }),
    ]);
    configs.value = Object.fromEntries(normalizeList(configRes.data).map((row) => [row.supplier, row]));
    users.value = normalizeList(userRes.data);
    applyCurrentConfig();
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || "読込に失敗しました。";
  } finally {
    loading.value = false;
  }
};

const save = async () => {
  saving.value = true;
  message.value = "";
  error.value = "";
  try {
    const payload = {
      supplier: selectedSupplier.value,
      body: form.body || "",
      cc_users: form.cc_users,
    };
    const { data } = await api.laserWeeklyPlans.updateMaterialOrderEmailConfig(selectedSupplier.value, payload);
    configs.value = { ...configs.value, [data.supplier]: data };
    message.value = "保存しました。";
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || "保存に失敗しました。";
  } finally {
    saving.value = false;
  }
};

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
.panel {
  display: grid;
  gap: 10px;
  max-width: 960px;
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 6px;
  padding: 12px;
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
}
textarea {
  resize: vertical;
  line-height: 1.5;
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
