<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">在庫 / 残量一覧</h2>
      <div class="page-actions">
        <input
          type="text"
          v-model="lineFilter"
          placeholder="ラインコード/名称で絞り込み"
        />
        <input type="date" v-model="startDate" @change="onStartChange" />
        <select v-model.number="horizon">
          <option :value="5">5日</option>
          <option :value="7">7日</option>
          <option :value="14">14日</option>
        </select>
        <button @click="load" :disabled="loading">更新</button>
      </div>
    </div>

    <div class="page-content">
      <div v-if="loading">読込中...</div>
      <div v-else-if="error" class="no-data">エラー: {{ error }}</div>
      <div v-else>
        <table class="data-table" v-if="rows.length">
          <thead>
            <tr>
              <th style="min-width: 180px;">ライン / 品目</th>
              <th v-for="d in columns" :key="d">{{ d }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.key">
              <td>{{ r.label }}</td>
              <td v-for="d in columns" :key="d" class="num">
                <template v-if="r.cells[d]">
                  <div>計画: {{ fmt(r.cells[d].plan) }}</div>
                  <div>実績: {{ fmt(r.cells[d].actual) }}</div>
                  <div>残: {{ fmt(r.cells[d].remaining) }}</div>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else class="no-data">データがありません</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import api from "@/api/client";
import { addDays, formatISODate, parseISODate } from "@/utils/dateUtil";

const lineFilter = ref("");
const startDate = ref(formatISODate(new Date()));
const horizon = ref(7);
const loading = ref(false);
const error = ref("");
const demands = ref([]);
let userSetStart = false;
const onStartChange = () => {
  userSetStart = true;
};

const columns = computed(() => {
  const start = parseISODate(startDate.value);
  const cols = [];
  for (let i = 0; i < horizon.value; i++) {
    cols.push(formatISODate(addDays(start, i)));
  }
  return cols;
});

const rows = computed(() => {
  if (!demands.value.length) return [];
  const filtered = demands.value.filter((d) => {
    const within =
      d.plan_date >= columns.value[0] &&
      d.plan_date <= columns.value[columns.value.length - 1];
    const lineText = `${d.line_name || ""}${d.line || ""}`.toLowerCase();
    const okLine =
      !lineFilter.value ||
      lineText.includes(lineFilter.value.trim().toLowerCase());
    return within && okLine;
  });

  const map = new Map();
  for (const d of filtered) {
    const key = `${d.line || d.line_name || ""}__${d.product_code}`;
    if (!map.has(key)) {
      map.set(key, {
        key,
        label: `${d.line_name || d.line} / ${d.product_code}`,
        cells: {},
      });
    }
    const row = map.get(key);
    const plan = Number(d.plan_qty || 0);
    const actual = Number(d.actual_qty || 0);
    row.cells[d.plan_date] = {
      plan,
      actual,
      remaining: plan - actual,
    };
  }
  return Array.from(map.values());
});

const fmt = (n) => (n === null || n === undefined ? "" : n.toLocaleString());

const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    const res = await api.lineDemands.list();
    const payload = res.data || [];
    demands.value = Array.isArray(payload) ? payload : payload.results || [];
    if (!userSetStart && demands.value.length) {
      const minDate = demands.value
        .map((d) => d.plan_date)
        .sort()[0];
      if (minDate) {
        startDate.value = minDate;
      }
    }
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
  min-width: 140px;
}

input,
select {
  padding: 4px 6px;
  font-size: 12px;
}
</style>
