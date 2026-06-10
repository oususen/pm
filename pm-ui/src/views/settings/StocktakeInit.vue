<template>
  <div class="settings-container">
    <h2 class="page-title">棚卸初期化 <DataSourceDialog title="棚卸初期化" :sources="dsSources" /></h2>

    <div class="card">
      <div class="field">
        <label>棚卸日</label>
        <div class="input-row">
          <input type="date" v-model="stocktakeDate" :disabled="running || !canEdit" />
        </div>
        <p class="helper">棚卸実施日を指定します。基準日は棚卸日と同じになります。</p>
      </div>

      <div class="field">
        <label>棚卸Excel</label>
        <div class="input-row">
          <input
            type="file"
            accept=".xlsx,.csv"
            @change="onFileChange"
            :disabled="running || !canEdit"
          />
        </div>
        <p class="helper">
          フォーマット: 製品番号, 製品名(任意), 数量
          （同一品番が複数行の場合はサーバー側で合算）
        </p>
      </div>

      <div class="actions">
        <button class="btn" @click="downloadTemplate" :disabled="running">テンプレートDL</button>
        <button class="btn primary" @click="importStocktakeExcel" :disabled="running || !canEdit">
          {{ importing ? "取込中..." : "1. 棚卸Excelを取込（在庫反映）" }}
        </button>
      </div>

      <div v-if="importResult" class="result-box">
        <div class="result-title">取込結果</div>
        <div class="result-row">棚卸日: {{ importResult.stocktake_date }}</div>
        <div class="result-row">適用基準日: {{ importResult.baseline_date }}</div>
        <div class="result-row">取込行数: {{ importResult.loaded_rows }}</div>
        <div class="result-row">品番数: {{ importResult.product_count }}</div>
        <div class="result-row">
          在庫反映:
          新規 {{ importResult.allocation_created }} / 更新 {{ importResult.allocation_updated }}
        </div>
        <div class="result-row">
          backlog反映:
          新規 {{ importResult.backlog_created }} / 更新 {{ importResult.backlog_updated }}
        </div>
        <div v-if="importResult.unmapped_product_codes?.length" class="result-row warning-row">
          ルーティング未設定品番: {{ importResult.unmapped_product_codes.join(", ") }}
        </div>
      </div>
    </div>

    <div class="card">
      <div class="field">
        <label>計算終了日</label>
        <div class="input-row">
          <input type="date" v-model="endDate" :disabled="running || !canEdit" />
        </div>
        <p class="helper">在庫・計画在庫・進度をこの日付まで再計算します。デフォルト: 昨日</p>
        <p class="helper">※ 棚卸日 + 最大LT営業日 以降の日付にしてください。</p>
      </div>

      <div class="actions">
        <button class="btn primary" @click="initializeAll" :disabled="running || !canEdit">
          {{ initializing ? "計算中..." : "2. 在庫・計画在庫・進度 初期化計算" }}
        </button>
      </div>

      <div v-if="initResult" class="result-box">
        <div class="result-title">初期化計算結果</div>
        <div class="result-row">棚卸日: {{ initResult.stocktake_date }}</div>
        <div class="result-row">適用基準日: {{ initResult.baseline_date }}</div>
        <div class="result-row">計算終了日: {{ initResult.end_date }}</div>
        <div class="result-row">対象ライン数: {{ initResult.line_count }}</div>
        <div class="result-row">進度更新件数: {{ initResult.updated_count ?? 0 }}</div>
        <div class="result-row">最終品: {{ initResult.final_count ?? 0 }}</div>
        <div class="result-row">子部品: {{ initResult.child_count ?? 0 }}</div>
      </div>
    </div>

    <div v-if="!canEdit" class="helper warning">この操作を実行する権限がありません。</div>

    <div v-if="running" class="processing-overlay">
      <div class="overlay-box">{{ importing ? "棚卸Excelを取り込んでいます..." : "初期化計算を実行しています..." }}</div>
    </div>
  </div>
</template>

<script setup>
import { formatISODate } from '@/utils/dateUtil'
import { computed, ref } from "vue";
import api from "@/api/client";
import { authState } from "@/auth";
import { hasPermission } from "@/router";
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 'production_stocktake_*', desc: '棚卸データ取込・初期化計算' },
  { op: '読み書き', table: 'line_backlog', desc: '在庫・計画在庫反映' },
]

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";
const templateUrl = `${API_BASE_URL}/line-backlogs/download_stocktake_template/`;
const getBusinessYesterday = () => {
  const now = new Date();
  // 8時区切り: 8時前は業務日付が前日→その前日=一昨日
  const offset = now.getHours() < 8 ? 2 : 1;
  const d = new Date(now);
  d.setDate(d.getDate() - offset);
  return formatISODate(d);
};

const stocktakeDate = ref("");
const endDate = ref(getBusinessYesterday());
const importing = ref(false);
const initializing = ref(false);
const selectedFile = ref(null);
const importResult = ref(null);
const initResult = ref(null);

const running = computed(() => importing.value || initializing.value);
const canEdit = computed(() => {
  const user = authState.user;
  if (!user) return false;
  if (user.is_staff || user.is_superuser) return true;

  const permissions = Array.isArray(user.effective_permissions)
    ? user.effective_permissions
    : [];
  if (permissions.some((item) => item.resource === "settings.stocktake_init")) {
    return hasPermission(user, "settings.stocktake_init", "edit");
  }
  return hasPermission(user, "settings", "edit");
});

const onFileChange = (event) => {
  selectedFile.value = event.target.files?.[0] || null;
};

const downloadTemplate = () => {
  window.open(templateUrl, "_blank");
};

const importStocktakeExcel = async () => {
  if (!canEdit.value || running.value) return;
  if (!stocktakeDate.value) {
    alert("棚卸日を入力してください。");
    return;
  }
  if (!selectedFile.value) {
    alert("棚卸ExcelまたはCSVファイルを選択してください。");
    return;
  }
  if (!confirm(`棚卸日 ${stocktakeDate.value} で棚卸取込を実行しますか？`)) return;

  importing.value = true;
  initResult.value = null;
  try {
    const formData = new FormData();
    formData.append("file", selectedFile.value);
    formData.append("stocktake_date", stocktakeDate.value);
    const res = await api.lineBacklogs.importStocktakeExcel(formData);
    importResult.value = res.data || null;
    alert("棚卸Excelの取込が完了しました。");
  } catch (e) {
    console.error("棚卸Excel取込に失敗しました", e);
    const data = e?.response?.data;
    let msg = data?.detail || "棚卸Excel取込に失敗しました。";
    if (data?.missing_product_codes?.length) {
      msg += "\n\n未登録品番:\n" + data.missing_product_codes.join(", ");
    }
    alert(msg);
  } finally {
    importing.value = false;
  }
};

const initializeAll = async () => {
  if (!canEdit.value || running.value) return;
  if (!stocktakeDate.value) {
    alert("棚卸日を入力してください。");
    return;
  }
  if (!endDate.value) {
    alert("計算終了日を入力してください。");
    return;
  }
  if (!confirm(`棚卸日 ${stocktakeDate.value} / 終了日 ${endDate.value} で初期化計算を実行しますか？`)) return;

  initializing.value = true;
  try {
    const res = await api.lineBacklogs.initializeStocktake({
      stocktake_date: stocktakeDate.value,
      end_date: endDate.value,
    });
    initResult.value = res.data || null;
    alert("在庫・計画在庫・進度の初期化計算が完了しました。");
  } catch (e) {
    console.error("初期化計算に失敗しました", e);
    alert(e?.response?.data?.detail || "初期化計算に失敗しました。");
  } finally {
    initializing.value = false;
  }
};
</script>

<style scoped>
.settings-container {
  position: relative;
  padding: 10px 12px 16px;
  background: #eef2f6;
  min-height: 100%;
  color: #1f2a44;
  font-family: "Segoe UI", "Hiragino Kaku Gothic ProN", Meiryo, sans-serif;
}

.page-title {
  margin: 0 0 10px;
  font-size: 16px;
  font-weight: 700;
}

.card {
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 10px;
  max-width: 760px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field label {
  font-size: 12px;
  color: #444;
}

.input-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-row input[type="date"] {
  width: 180px;
  padding: 6px 8px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}

.helper {
  margin: 0;
  font-size: 12px;
  color: #666;
}

.helper.warning {
  color: #b45309;
}

.actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.btn {
  padding: 6px 10px;
  border: 1px solid #b5c1d2;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}

.btn.primary {
  background: #4a7ae5;
  color: #fff;
  border-color: #3865c7;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.result-box {
  margin-top: 14px;
  border-top: 1px solid #e5e9ef;
  padding-top: 10px;
  font-size: 12px;
}

.result-title {
  font-weight: 700;
  margin-bottom: 6px;
}

.result-row {
  margin-bottom: 4px;
}

.warning-row {
  color: #b45309;
}

.processing-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.72);
}

.overlay-box {
  border: 1px solid #d1d8e3;
  background: #fff;
  padding: 10px 14px;
  border-radius: 4px;
  font-size: 13px;
}
</style>




