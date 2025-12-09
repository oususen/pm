<template>
  <div class="master-menu">
    <h2 class="page-title">受注管理メニュー</h2>

    <div class="master-grid">
      <RouterLink to="/orders" class="master-tile">
        <div class="icon-box">📑</div>
        <div class="label">受注一覧</div>
      </RouterLink>

      <RouterLink to="/csv-upload" class="master-tile">
        <div class="icon-box">📤</div>
        <div class="label">受注取込</div>
      </RouterLink>

      <div class="master-tile">
        <div class="icon-box">🛠️</div>
        <div class="label">ライン展開</div>
        <button
          class="action-btn"
          :disabled="running"
          @click="runExpand"
        >
          {{ running ? '展開中...' : '展開実行' }}
        </button>
        <div v-if="message" class="status-text">{{ message }}</div>
        <ul v-if="warnings.length" class="warn-list">
          <li v-for="(w, idx) in warnings" :key="idx">{{ w }}</li>
        </ul>
      </div>
    </div>

    <p class="helper-text">
      展開実行でOPEN受注をライン別需要に再生成します。
    </p>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { RouterLink } from "vue-router";
import api from "../api/client";

const running = ref(false);
const message = ref("");
const warnings = ref([]);

const runExpand = async () => {
  if (running.value) return;
  running.value = true;
  message.value = "";
  warnings.value = [];

  try {
    const res = await api.lineDemands.expand(true);
    const data = res.data || {};
    message.value = `展開完了: created=${data.created ?? 0}, cleared=${data.cleared ?? 0}`;
    warnings.value = data.warnings || [];
  } catch (e) {
    const detail = e?.response?.data?.error || e.message || "unknown error";
    message.value = `展開エラー: ${detail}`;
  } finally {
    running.value = false;
  }
};
</script>

<style scoped>
.action-btn {
  width: 100%;
  padding: 8px 0;
  background: #284b8f;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.status-text {
  margin-top: 6px;
  font-size: 12px;
  color: #1a3a7a;
}

.warn-list {
  margin: 6px 0 0;
  padding-left: 16px;
  color: #a05a00;
  font-size: 12px;
}
</style>
