<template>
  <div class="settings-container">
    <h2 class="page-title">孤立ライン実績メンテナンス</h2>
    <p class="helper">
      ルーティングの入力ミスや、後からのライン/工程変更により、現行の有効ルーティングには存在しない
      (製品×ライン×工程)の組み合わせで残ってしまった LineBacklog/LineDemand を検出・削除します。
    </p>

    <div class="card">
      <div class="input-row">
        <label>{{ productCodeLabel }}</label>
        <input type="text" v-model.trim="productCode" placeholder="例: YD40007722-11SG" :disabled="loading" @keyup.enter="loadReport" />
        <div class="toggle-group" role="group" aria-label="連産品表示切替">
          <button
            type="button"
            class="btn toggle-btn"
            :class="{ active: !includeStCoproduct }"
            :disabled="loading"
            @click="includeStCoproduct = false"
          >
            連産品除く
          </button>
          <button
            type="button"
            class="btn toggle-btn"
            :class="{ active: includeStCoproduct }"
            :disabled="loading"
            @click="includeStCoproduct = true"
          >
            連産品含む
          </button>
        </div>
        <button class="btn primary" @click="loadReport" :disabled="loading">
          {{ loading ? "検索中..." : "検索/スキャン実行" }}
        </button>
      </div>
      <p v-if="report && !productCode" class="helper warning">
        {{ includeStCoproduct
          ? "製品コード未指定で全製品を対象に検索しました（連産品含む、データ量によっては時間がかかる場合があります）。"
          : "製品コード未指定で全製品を対象に検索しました（連産品除く、データ量によっては時間がかかる場合があります）。" }}
      </p>
    </div>

    <div v-if="report && !canEdit" class="helper warning">この機能の削除操作を実行する権限がありません（閲覧のみ可能です）。</div>

    <template v-if="report">
      <div v-for="section in sections" :key="section.key" class="card" :class="{ 'warn-card': section.warn }">
        <div class="table-title">
          {{ section.title }}
          <span class="count-badge">{{ filteredRows(section).length }} / {{ section.rows.length }}件</span>
        </div>
        <div v-if="section.rows.length" class="filter-row">
          <label>ライン</label>
          <select v-model="filters[section.key].line" class="filter-select">
            <option value="">全て</option>
            <option v-for="l in lineOptions(section)" :key="l" :value="l">{{ l }}</option>
          </select>
          <template v-if="section.kind === 'backlog'">
            <label>工程</label>
            <select v-model="filters[section.key].process" class="filter-select">
              <option value="">全て</option>
              <option v-for="p in processOptions(section)" :key="p" :value="p">{{ p }}</option>
            </select>
          </template>
        </div>
        <p v-if="!section.rows.length" class="helper">該当なし</p>
        <table v-else class="group-table">
          <thead>
            <tr>
              <th v-if="canEdit">
                <input type="checkbox" :checked="isAllChecked(section)" @change="toggleAll(section, $event.target.checked)" />
              </th>
              <th>製品コード</th>
              <th>製品名</th>
              <th>ライン</th>
              <th v-if="section.kind === 'backlog'">工程</th>
              <th>件数</th>
              <th>期間</th>
              <th>{{ section.kind === "backlog" ? "進度/実績/調整 合計" : "内示/確定/実績 合計" }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="g in filteredRows(section)" :key="rowKey(section.kind, g)">
              <td v-if="canEdit">
                <input
                  type="checkbox"
                  :checked="section.selected.has(rowKey(section.kind, g))"
                  @change="toggleRow(section, g, $event.target.checked)"
                />
              </td>
              <td>{{ g.product_code }}</td>
              <td>{{ g.product_name }}</td>
              <td>{{ g.line_name }}({{ g.line_code }})</td>
              <td v-if="section.kind === 'backlog'">{{ g.process_code }}</td>
              <td>{{ g.count }}</td>
              <td>{{ g.min_date }}〜{{ g.max_date }}</td>
              <td v-if="section.kind === 'backlog'">{{ g.sums.progress_qty }} / {{ g.sums.actual_qty }} / {{ g.sums.adjust_qty }}</td>
              <td v-else>{{ g.sums.forecast_qty }} / {{ g.sums.firm_qty }} / {{ g.sums.actual_qty }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="section.rows.length && section.forceHint" class="helper warning">
          ※ チェックした行は「{{ section.forceHint }}」として処理されます（数値が残っていても削除します）。
        </p>
      </div>

      <div class="card actions-card" v-if="hasAnyRows">
        <button class="btn danger" @click="runFix" :disabled="!canEdit || applying || !hasAnySelected">
          {{ applying ? "削除実行中..." : "選択した行を削除" }}
        </button>
        <span class="helper">選択中: {{ selectedCount }}件</span>
      </div>

      <div v-if="!hasAnyRows" class="card">
        <p class="helper">孤立グループは見つかりませんでした。</p>
      </div>

      <div v-if="fixResult" class="result-box card">
        <div class="result-title">削除結果</div>
        <div class="result-row">LineBacklog削除: {{ fixResult.deleted_backlog }}件</div>
        <div class="result-row">LineDemand削除: {{ fixResult.deleted_demand }}件</div>
        <div v-if="fixResult.skipped?.length" class="result-row warning-row">
          <div>スキップ:</div>
          <div v-for="(msg, i) in fixResult.skipped" :key="i">{{ msg }}</div>
        </div>
      </div>
    </template>

    <div v-if="loading || applying" class="processing-overlay">
      <div class="overlay-box">{{ applying ? "削除を実行しています..." : "検索しています..." }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import api from "@/api/client";
import { authState } from "@/auth";
import { hasPermission } from "@/router";

const RESOURCE = "settings.orphan_backlog_maintenance";

const canEdit = computed(() => {
  const user = authState.user;
  if (!user) return false;
  if (user.is_staff || user.is_superuser) return true;
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : [];
  if (permissions.some((item) => item.resource === RESOURCE)) {
    return hasPermission(user, RESOURCE, "edit");
  }
  return hasPermission(user, "settings", "edit");
});

const productCode = ref("");
const includeStCoproduct = ref(false);
const loading = ref(false);
const applying = ref(false);
const report = ref(null);
const fixResult = ref(null);

const productCodeLabel = computed(() => (
  includeStCoproduct.value
    ? "製品コード（任意・空欄で全製品スキャン: 連産品含む）"
    : "製品コード（任意・空欄で全製品スキャン: 連産品除く）"
));

const selected = reactive({
  backlogGhost: new Set(),
  backlogResidual: new Set(),
  demandGhost: new Set(),
  demandResidual: new Set(),
});

const filters = reactive({
  backlogGhost: { line: '', process: '' },
  backlogResidual: { line: '', process: '' },
  demandGhost: { line: '' },
  demandResidual: { line: '' },
});

const lineOptions = (section) => {
  const set = new Set(section.rows.map((g) => `${g.line_name}(${g.line_code})`));
  return [...set].sort();
};

const processOptions = (section) => {
  const set = new Set(section.rows.map((g) => g.process_code).filter(Boolean));
  return [...set].sort();
};

const filteredRows = (section) => {
  let rows = section.rows;
  const f = filters[section.key];
  if (f.line) rows = rows.filter((g) => `${g.line_name}(${g.line_code})` === f.line);
  if (f.process) rows = rows.filter((g) => g.process_code === f.process);
  return rows;
};

const rowKey = (kind, g) => (kind === "backlog" ? `${g.product_id}|${g.line_id}|${g.process_id}` : `${g.product_id}|${g.line_id}`);

const sections = computed(() => {
  if (!report.value) return [];
  return [
    {
      key: "backlogGhost",
      title: "LineBacklog ゴースト行（全項目ゼロ・削除して安全）",
      kind: "backlog",
      rows: report.value.backlog_ghosts,
      selected: selected.backlogGhost,
      forceHint: "",
      warn: false,
    },
    {
      key: "backlogResidual",
      title: "LineBacklog 要確認行（数値が残存・強制削除には確認が必要）",
      kind: "backlog",
      rows: report.value.backlog_residuals,
      selected: selected.backlogResidual,
      forceHint: "強制削除",
      warn: true,
    },
    {
      key: "demandGhost",
      title: "LineDemand ゴースト行（全項目ゼロ・削除して安全）",
      kind: "demand",
      rows: report.value.demand_ghosts,
      selected: selected.demandGhost,
      forceHint: "",
      warn: false,
    },
    {
      key: "demandResidual",
      title: "LineDemand 要確認行（数値が残存・強制削除には確認が必要）",
      kind: "demand",
      rows: report.value.demand_residuals,
      selected: selected.demandResidual,
      forceHint: "強制削除",
      warn: true,
    },
  ];
});

const hasAnyRows = computed(() => sections.value.some((s) => s.rows.length > 0));
const selectedCount = computed(() =>
  Object.values(selected).reduce((sum, set) => sum + set.size, 0)
);
const hasAnySelected = computed(() => selectedCount.value > 0);

const isAllChecked = (section) => {
  const rows = filteredRows(section);
  return rows.length > 0 && rows.every((g) => section.selected.has(rowKey(section.kind, g)));
};

const toggleAll = (section, checked) => {
  filteredRows(section).forEach((g) => {
    const key = rowKey(section.kind, g);
    if (checked) section.selected.add(key);
    else section.selected.delete(key);
  });
};

const toggleRow = (section, g, checked) => {
  const key = rowKey(section.kind, g);
  if (checked) section.selected.add(key);
  else section.selected.delete(key);
};

const loadReport = async () => {
  loading.value = true;
  fixResult.value = null;
  try {
    const params = {
      include_st_coproduct: includeStCoproduct.value,
    };
    if (productCode.value) {
      params.product_code = productCode.value;
    }
    const res = await api.orphanBacklog.getReport(params);
    report.value = res.data;
    // ゴースト行はデフォルトで全選択、要確認行はデフォルト未選択
    selected.backlogGhost = new Set(report.value.backlog_ghosts.map((g) => rowKey("backlog", g)));
    selected.backlogResidual = new Set();
    selected.demandGhost = new Set(report.value.demand_ghosts.map((g) => rowKey("demand", g)));
    selected.demandResidual = new Set();
  } catch (e) {
    console.error("孤立ライン実績の検索に失敗しました", e);
    alert(e?.response?.data?.detail || "検索に失敗しました。");
  } finally {
    loading.value = false;
  }
};

const runFix = async () => {
  if (!canEdit.value || applying.value || !hasAnySelected.value) return;
  const residualCount = selected.backlogResidual.size + selected.demandResidual.size;
  const msg = residualCount
    ? `要確認行(数値残存)を${residualCount}件含みます。本当に削除しますか？この操作は取り消せません。`
    : "選択した行を削除しますか？この操作は取り消せません。";
  if (!confirm(msg)) return;

  applying.value = true;
  try {
    const backlogTargets = [
      ...report.value.backlog_ghosts
        .filter((g) => selected.backlogGhost.has(rowKey("backlog", g)))
        .map((g) => ({ product_id: g.product_id, line_id: g.line_id, process_id: g.process_id, force: false })),
      ...report.value.backlog_residuals
        .filter((g) => selected.backlogResidual.has(rowKey("backlog", g)))
        .map((g) => ({ product_id: g.product_id, line_id: g.line_id, process_id: g.process_id, force: true })),
    ];
    const demandTargets = [
      ...report.value.demand_ghosts
        .filter((g) => selected.demandGhost.has(rowKey("demand", g)))
        .map((g) => ({ product_id: g.product_id, line_id: g.line_id, force: false })),
      ...report.value.demand_residuals
        .filter((g) => selected.demandResidual.has(rowKey("demand", g)))
        .map((g) => ({ product_id: g.product_id, line_id: g.line_id, force: true })),
    ];

    const res = await api.orphanBacklog.runFix({ backlog_targets: backlogTargets, demand_targets: demandTargets });
    fixResult.value = res.data;
    await loadReport();
  } catch (e) {
    console.error("孤立ライン実績の削除に失敗しました", e);
    alert(e?.response?.data?.detail || "削除に失敗しました。");
  } finally {
    applying.value = false;
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
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 700;
}

.card {
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 10px;
}

.warn-card {
  border-color: #e0b25a;
}

.input-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.input-row label {
  font-size: 12px;
  color: #444;
}

.input-row input[type="text"] {
  width: 240px;
  padding: 6px 8px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}

.helper {
  margin: 4px 0 0;
  font-size: 12px;
  color: #666;
}

.helper.warning {
  color: #b45309;
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

.toggle-group {
  display: inline-flex;
  border: 1px solid #b5c1d2;
  border-radius: 4px;
  overflow: hidden;
}

.toggle-btn {
  border: 0;
  border-radius: 0;
  min-width: 88px;
}

.toggle-btn + .toggle-btn {
  border-left: 1px solid #b5c1d2;
}

.toggle-btn.active {
  background: #1f6feb;
  color: #fff;
}

.btn.danger {
  background: #d64545;
  color: #fff;
  border-color: #b5342f;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.actions-card {
  display: flex;
  align-items: center;
  gap: 12px;
}

.table-title {
  font-weight: 700;
  font-size: 13px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.count-badge {
  font-weight: 400;
  font-size: 11px;
  color: #666;
  background: #eef2f6;
  border-radius: 10px;
  padding: 1px 8px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-size: 12px;
}

.filter-row label {
  color: #555;
}

.filter-select {
  padding: 3px 6px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
  font-size: 12px;
}

.group-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.group-table th,
.group-table td {
  border: 1px solid #e5e9ef;
  padding: 4px 6px;
  text-align: left;
  white-space: nowrap;
}

.group-table th {
  background: #f5f7fa;
}

.result-box {
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
