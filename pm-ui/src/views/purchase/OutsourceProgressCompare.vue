<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">外作注文書・進度表比較</h1>
        <p class="page-subtitle">外作注文書PDFと進度表PDFまたはExcelを突合せ、比較表Excelを出力します。</p>
      </div>
      <button class="btn-primary" :disabled="!canCompare || comparing" @click="compareFiles">
        {{ comparing ? "比較中..." : "比較表Excel出力" }}
      </button>
    </div>

    <div class="compare-grid">
      <section class="upload-panel">
        <div class="panel-heading">
          <span class="step">1</span>
          <h2>外作注文書PDF</h2>
        </div>
        <label class="drop-zone" :class="{ filled: orderFile }">
          <input type="file" accept="application/pdf,.pdf" @change="onFileChange($event, 'order')" />
          <span class="file-label">{{ orderFile ? orderFile.name : "PDFを選択" }}</span>
          <span class="file-meta">{{ orderFile ? formatSize(orderFile.size) : "外作注文書を指定" }}</span>
        </label>
      </section>

      <section class="upload-panel">
        <div class="panel-heading">
          <span class="step">2</span>
          <h2>進度表</h2>
        </div>
        <div class="file-type-switch">
          <label><input v-model="progressSourceType" type="radio" value="pdf" /> PDF</label>
          <label><input v-model="progressSourceType" type="radio" value="excel" /> Excel</label>
        </div>
        <label class="drop-zone" :class="{ filled: progressFile }">
          <input :key="progressSourceType" type="file" :accept="progressAccept" @change="onFileChange($event, 'progress')" />
          <span class="file-label">{{ progressFile ? progressFile.name : progressPlaceholder }}</span>
          <span class="file-meta">{{ progressFile ? formatSize(progressFile.size) : progressMeta }}</span>
        </label>
      </section>
    </div>

    <div v-if="message" class="message" :class="messageType">{{ message }}</div>

    <section class="result-panel">
      <h2>出力シート</h2>
      <div class="sheet-list">
        <div class="sheet-item">
          <strong>品番違い</strong>
          <span>Gあり品番 / Gなし品番 / 需要有無</span>
        </div>
        <div class="sheet-item">
          <strong>数量差分</strong>
          <span>日付別、内示・確定別、品番ごと背景色</span>
        </div>
        <div class="sheet-item">
          <strong>その他差分</strong>
          <span>品名差分など</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import api from "@/api/client";

const orderFile = ref(null);
const progressFile = ref(null);
const progressSourceType = ref("pdf");
const comparing = ref(false);
const message = ref("");
const messageType = ref("info");

const canCompare = computed(() => orderFile.value && progressFile.value);
const progressAccept = computed(() =>
  progressSourceType.value === "pdf"
    ? "application/pdf,.pdf"
    : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,.xlsx,.xlsm"
);
const progressPlaceholder = computed(() => (progressSourceType.value === "pdf" ? "PDFを選択" : "Excelを選択"));
const progressMeta = computed(() => (progressSourceType.value === "pdf" ? "進度表PDFを指定" : "進度表Excelを指定"));

const onFileChange = (event, type) => {
  const file = event.target?.files?.[0] || null;
  if (type === "order") orderFile.value = file;
  if (type === "progress") progressFile.value = file;
  message.value = "";
};

const formatSize = (size) => {
  if (!size) return "";
  if (size < 1024 * 1024) return `${Math.ceil(size / 1024)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
};

const downloadBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};

const compareFiles = async () => {
  if (!canCompare.value) return;
  comparing.value = true;
  message.value = "";
  try {
    const form = new FormData();
    form.append("order_pdf", orderFile.value);
    if (progressSourceType.value === "pdf") {
      form.append("progress_pdf", progressFile.value);
    } else {
      form.append("progress_excel", progressFile.value);
    }
    const res = await api.client.post("/purchase-receiving/outsource-progress-compare/", form, {
      responseType: "blob",
    });
    const today = new Date().toISOString().slice(0, 10);
    downloadBlob(res.data, `外作注文書_進度表_比較表_${today}.xlsx`);
    messageType.value = "success";
    message.value = "比較表Excelを出力しました。";
  } catch (error) {
    messageType.value = "error";
    message.value = `比較表Excelの作成に失敗しました。${progressSourceType.value === "pdf" ? "PDF" : "Excel"}の種類を確認してください。`;
  } finally {
    comparing.value = false;
  }
};

watch(progressSourceType, () => {
  progressFile.value = null;
  message.value = "";
});
</script>

<style scoped>
.page-container {
  padding: 16px;
  display: grid;
  gap: 14px;
}
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.page-title {
  margin: 0;
  font-size: 22px;
}
.page-subtitle {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
}
.btn-primary {
  border: 0;
  border-radius: 6px;
  background: #0f766e;
  color: #fff;
  font-weight: 700;
  padding: 9px 14px;
  cursor: pointer;
  white-space: nowrap;
}
.btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.compare-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.upload-panel,
.result-panel {
  border: 1px solid #dbe2ea;
  border-radius: 8px;
  background: #fff;
  padding: 12px;
}
.panel-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.panel-heading h2,
.result-panel h2 {
  margin: 0;
  font-size: 15px;
}
.step {
  display: inline-grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #e0f2fe;
  color: #075985;
  font-size: 12px;
  font-weight: 700;
}
.drop-zone {
  min-height: 92px;
  border: 1px dashed #94a3b8;
  border-radius: 8px;
  display: grid;
  place-items: center;
  gap: 4px;
  padding: 12px;
  cursor: pointer;
  background: #f8fafc;
}
.file-type-switch {
  display: flex;
  gap: 14px;
  margin-bottom: 10px;
  font-size: 13px;
}
.file-type-switch label {
  display: flex;
  align-items: center;
  gap: 4px;
}
.drop-zone.filled {
  border-color: #0f766e;
  background: #ecfdf5;
}
.drop-zone input {
  display: none;
}
.file-label {
  font-weight: 700;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-meta {
  color: #64748b;
  font-size: 12px;
}
.message {
  border-radius: 6px;
  padding: 9px 11px;
  font-weight: 700;
}
.message.success {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}
.message.error {
  background: #fff1f2;
  color: #be123c;
  border: 1px solid #fecdd3;
}
.sheet-list {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}
.sheet-item {
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid #edf2f7;
  padding-bottom: 8px;
}
.sheet-item strong {
  min-width: 90px;
}
.sheet-item span {
  color: #64748b;
  font-size: 13px;
}
@media (max-width: 760px) {
  .page-header,
  .sheet-item {
    display: grid;
  }
  .compare-grid {
    grid-template-columns: 1fr;
  }
}
</style>
