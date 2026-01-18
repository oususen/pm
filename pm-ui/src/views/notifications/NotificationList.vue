<template>
  <div class="notification-list-page">
    <h2 class="page-title">通知一覧</h2>

    <div class="list-card">
      <div class="list-header">
        <div class="list-note">通知の一覧を表示します。</div>
      </div>

      <table class="notification-table">
        <thead>
          <tr>
            <th>表示順</th>
            <th>タイトル</th>
            <th>カテゴリ</th>
            <th>種別</th>
            <th>有効開始日</th>
            <th>有効終了日</th>
            <th>対象者</th>
            <th>入力者</th>
            <th>説明</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="item in sortedNotifications" :key="item.id">
            <tr class="row-main" @click="toggleRow(item.id)">
              <td>{{ item.display_order }}</td>
              <td>{{ item.title }}</td>
              <td>{{ getCategoryLabel(item.category) }}</td>
              <td>{{ getDomainLabel(item.domain) }}</td>
              <td>{{ item.valid_from || '-' }}</td>
              <td>{{ item.valid_to || '-' }}</td>
              <td>{{ getTargetLabel(item) }}</td>
              <td>{{ item.operator_name || '-' }}</td>
              <td class="description">{{ item.description || '-' }}</td>
            </tr>
            <tr v-if="expandedIds.has(item.id)" class="row-detail">
              <td colspan="9">
                <div class="detail-grid">
                  <div class="detail-item">
                    <span class="detail-label">タイトル</span>
                    <span class="detail-value">{{ item.title }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">カテゴリ</span>
                    <span class="detail-value">{{ getCategoryLabel(item.category) }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">種別</span>
                    <span class="detail-value">{{ getDomainLabel(item.domain) }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">対象者</span>
                    <span class="detail-value">{{ getTargetLabel(item) }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">有効期間</span>
                    <span class="detail-value">
                      {{ formatDateRange(item.valid_from, item.valid_to) }}
                    </span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">入力者</span>
                    <span class="detail-value">{{ item.operator_name || '-' }}</span>
                  </div>
                  <div class="detail-item full">
                    <span class="detail-label">説明</span>
                    <span class="detail-value">{{ item.description || '-' }}</span>
                  </div>
                </div>
              </td>
            </tr>
          </template>
          <tr v-if="!sortedNotifications.length">
            <td colspan="9" class="empty">通知はありません。</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { authState } from "@/auth";
import api from "@/api/client";

const notifications = ref([]);
const expandedIds = ref(new Set());
const departments = ref([]);

const domainOptions = [
  { value: "production", label: "生産" },
  { value: "quality", label: "品質" },
  { value: "inventory", label: "在庫" },
  { value: "purchase", label: "購買" },
  { value: "shipping", label: "出荷" },
  { value: "equipment", label: "設備" },
  { value: "common", label: "共通" },
];

const categoryOptions = [
  { value: "progress", label: "進捗" },
  { value: "delay", label: "遅延" },
  { value: "abnormal", label: "異常" },
  { value: "quality_issue", label: "品質不良" },
  { value: "inventory_shortage", label: "在庫不足" },
  { value: "process_change", label: "工程変更" },
  { value: "maintenance", label: "保全" },
  { value: "shipping_issue", label: "出荷トラブル" },
  { value: "other", label: "その他" },
];

const toId = (value) => (value === null || value === undefined ? "" : String(value));

const parentMap = computed(() => {
  const map = new Map();
  departments.value.forEach((dept) => {
    map.set(toId(dept.id), toId(dept.parent));
  });
  return map;
});

const isDescendantOrSelf = (childId, ancestorId) => {
  const child = toId(childId);
  const ancestor = toId(ancestorId);
  if (!child || !ancestor) return false;
  let cursor = child;
  const seen = new Set();
  while (cursor && !seen.has(cursor)) {
    if (cursor === ancestor) return true;
    seen.add(cursor);
    const parent = parentMap.value.get(cursor);
    if (!parent) return false;
    cursor = parent;
  }
  return false;
};

const matchesDepartmentTarget = (targetDepartments, userDepartmentId) => {
  if (!targetDepartments.length) return true;
  if (!userDepartmentId) return false;
  return targetDepartments.some((deptId) => isDescendantOrSelf(userDepartmentId, deptId));
};

const matchesPositionTarget = (targetPositions, userPosition) => {
  if (!targetPositions.length) return true;
  if (!userPosition) return false;
  return targetPositions.some((pos) => String(pos) === String(userPosition));
};

const isWithinRange = (item) => {
  const today = new Date();
  const todayYmd = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const from = item.valid_from ? new Date(item.valid_from) : null;
  const to = item.valid_to ? new Date(item.valid_to) : null;
  if (from && todayYmd < from) return false;
  if (to && todayYmd > to) return false;
  return true;
};

const filteredNotifications = computed(() => {
  const userDeptId = authState.user?.profile?.department || null;
  const userPosition = authState.user?.profile?.position || "";
  return notifications.value.filter((item) => {
    if (!item) return false;
    if (!isWithinRange(item)) return false;
    const targetDepartments = Array.isArray(item.target_departments) ? item.target_departments : [];
    const targetPositions = Array.isArray(item.target_positions) ? item.target_positions : [];
    if (!matchesDepartmentTarget(targetDepartments, userDeptId)) return false;
    if (!matchesPositionTarget(targetPositions, userPosition)) return false;
    return true;
  });
});

const sortedNotifications = computed(() => {
  return [...filteredNotifications.value].sort((a, b) => {
    const aOrder = Number(a.display_order || 0);
    const bOrder = Number(b.display_order || 0);
    if (aOrder !== bOrder) return aOrder - bOrder;
    return (a.title || "").localeCompare(b.title || "");
  });
});

const getDomainLabel = (domain) => {
  const found = domainOptions.find((opt) => opt.value === domain);
  return found ? found.label : domain;
};

const getCategoryLabel = (category) => {
  const found = categoryOptions.find((opt) => opt.value === category);
  return found ? found.label : category;
};

const getTargetLabel = (item) => {
  const deptNames = Array.isArray(item.target_department_names) ? item.target_department_names : [];
  const posList = Array.isArray(item.target_positions) ? item.target_positions : [];
  const deptText = deptNames.length ? deptNames.join(" / ") : "";
  const posText = posList.length ? posList.join(" / ") : "";
  if (deptText && posText) return `${deptText} / ${posText}`;
  if (deptText) return deptText;
  if (posText) return posText;
  return "-";
};

const loadNotifications = async () => {
  try {
    const res = await api.notifications.list({ ordering: "display_order,id" });
    const data = res.data?.results || res.data || [];
    notifications.value = Array.isArray(data) ? data : [];
  } catch (error) {
    console.error("通知の読み込みに失敗しました:", error);
    notifications.value = [];
  }
};

const loadDepartments = async () => {
  try {
    const res = await api.accounts.getDepartments({ ordering: "display_id,name" });
    const data = res.data?.results || res.data || [];
    departments.value = Array.isArray(data) ? data : [];
  } catch (error) {
    console.error("部署一覧の取得に失敗しました:", error);
    departments.value = [];
  }
};

const toggleRow = (id) => {
  const next = new Set(expandedIds.value);
  if (next.has(id)) {
    next.delete(id);
  } else {
    next.add(id);
  }
  expandedIds.value = next;
};

const formatDateRange = (from, to) => {
  if (from && to) return `${from} 〜 ${to}`;
  if (from) return `${from} 〜`;
  if (to) return `〜 ${to}`;
  return "-";
};

onMounted(() => {
  loadNotifications();
  loadDepartments();
});
</script>

<style scoped>
.notification-list-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 20px;
}

.page-title {
  margin: 0 0 16px 0;
  font-size: 22px;
  font-weight: 700;
  color: #1f2a44;
}

.list-card {
  background: #fff;
  border-radius: 10px;
  padding: 16px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.list-note {
  font-size: 13px;
  color: #64748b;
}

.btn {
  border: none;
  border-radius: 6px;
  padding: 8px 14px;
  font-size: 13px;
  cursor: pointer;
  text-decoration: none;
}

.edit-btn {
  background: #2563eb;
  color: #fff;
}

.notification-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.notification-table th,
.notification-table td {
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 6px;
}

.notification-table th {
  background: #f8fafc;
  font-weight: 700;
  color: #1f2a44;
}

.description {
  max-width: 220px;
  color: #475569;
}

.empty {
  text-align: center;
  padding: 16px;
  color: #94a3b8;
}

.row-main {
  cursor: pointer;
}

.row-main:hover {
  background: #f8fafc;
}

.row-detail td {
  background: #f1f5f9;
}

.detail-grid {
  display: grid;
  gap: 8px 16px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  padding: 10px 0;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.detail-item.full {
  grid-column: 1 / -1;
}

.detail-label {
  font-size: 11px;
  color: #64748b;
}

.detail-value {
  font-size: 13px;
  color: #1f2a44;
}

@media (max-width: 768px) {
  .notification-list-page {
    padding: 16px;
  }

  .list-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .notification-table {
    font-size: 12px;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
