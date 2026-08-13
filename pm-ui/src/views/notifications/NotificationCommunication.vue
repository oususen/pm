<template>
  <div class="communication-page">
    <div class="tab-bar">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        class="tab-btn"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>
    <NotificationCallCenter v-if="activeTab === 'call'" />
    <NotificationSourceInput v-if="activeTab === 'message'" />
  </div>
</template>

<script setup>
import { ref } from "vue";
import NotificationCallCenter from "./NotificationCallCenter.vue";
import NotificationSourceInput from "./NotificationSourceInput.vue";

const tabs = [
  { id: "call", label: "通話" },
  { id: "message", label: "メッセージ" },
];

const activeTab = ref("call");
</script>

<style scoped>
.communication-page {
  padding: 0;
}

.tab-bar {
  display: flex;
  gap: 0;
  margin-bottom: 8px;
  padding: 0 20px;
  border-bottom: 2px solid #e2e8f0;
}

.tab-btn {
  padding: 10px 24px;
  font-size: 14px;
  font-weight: 600;
  color: #64748b;
  background: none;
  border: none;
  border-bottom: 3px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}

.tab-btn:hover {
  color: #1e40af;
}

.tab-btn.active {
  color: #2563eb;
  border-bottom-color: #2563eb;
}
</style>
