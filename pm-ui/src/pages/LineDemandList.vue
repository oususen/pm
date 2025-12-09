<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">ライン需要一覧</h2>
      <div class="page-actions">
        <button @click="load" :disabled="loading">再読込</button>
      </div>
    </div>

    <div class="page-content">
      <div v-if="loading">読込中...</div>
      <div v-else-if="error" class="no-data">エラー: {{ error }}</div>
      <div v-else>
        <table class="data-table" v-if="items.length">
          <thead>
            <tr>
              <th>日付</th>
              <th>ライン</th>
              <th>品番</th>
              <th>確定</th>
              <th>内示</th>
              <th>計画</th>
              <th>実績</th>
              <th>計画進度</th>
              <th>実績進度</th>
              <th>受注番号</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td>{{ item.plan_date }}</td>
              <td>{{ item.line_name || item.line }}</td>
              <td>{{ item.product_code }}</td>
              <td class="num">{{ formatQty(item.firm_qty) }}</td>
              <td class="num">{{ formatQty(item.forecast_qty) }}</td>
              <td class="num">{{ formatQty(item.plan_qty) }}</td>
              <td class="num">{{ formatQty(item.actual_qty) }}</td>
              <td class="num">{{ formatProgress(item.plan_progress) }}</td>
              <td class="num">{{ formatProgress(item.actual_progress) }}</td>
              <td>{{ item.order_numbers }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="no-data">データがありません</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import api from "../api/client";

const items = ref([]);
const loading = ref(false);
const error = ref("");

const formatQty = (v) => {
  if (v === null || v === undefined) return "";
  return Number(v).toLocaleString();
};

const formatProgress = (v) => {
  if (v === null || v === undefined) return "";
  return `${(Number(v) * 100).toFixed(1)}%`;
};

const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    const res = await api.lineDemands.list();
    const payload = res.data || [];
    items.value = Array.isArray(payload) ? payload : payload.results || [];
  } catch (e) {
    error.value = e?.message || "読み込みに失敗しました";
  } finally {
    loading.value = false;
  }
};

onMounted(load);
</script>

<style scoped>
.num {
  text-align: right;
}
</style>
