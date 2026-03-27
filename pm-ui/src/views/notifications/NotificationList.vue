<template>
  <div class="notification-list-page">
    <h2 class="page-title">通知一覧</h2>

    <div class="list-card">
      <div class="list-header">
        <div class="list-note">通知の一覧を表示します。</div>
        <button class="btn confirm-all-btn" type="button" @click="handleMarkAllRead" :disabled="!unreadCount">
          すべて確認済み
        </button>
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
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="item in sortedNotifications" :key="item.id">
            <tr class="row-main" :class="{ 'unread': !item.is_read }" @click="toggleRow(item.id)">
              <td>{{ item.display_order }}</td>
              <td>{{ item.title }}</td>
              <td>{{ getDomainLabel(item.domain) }}</td>
              <td>{{ getCategoryLabel(item.category) }}</td>
              <td>{{ item.valid_from || '-' }}</td>
              <td>{{ item.valid_to || '-' }}</td>
              <td>{{ getTargetLabel(item) }}</td>
              <td>{{ item.operator_name || '-' }}</td>
              <td class="action-cell">
                <button
                  v-if="!item.is_read"
                  class="btn confirm-btn-inline"
                  type="button"
                  @click.stop="handleMarkRead(item.id)"
                >
                  ✓ 確認
                </button>
                <span v-else class="confirmed-label">確認済み</span>
              </td>
            </tr>
            <tr v-if="expandedIds.has(item.id)" class="row-detail">
              <td colspan="10">
                <div class="detail-grid">
                  <div class="detail-item">
                    <span class="detail-label">タイトル</span>
                    <span class="detail-value">{{ item.title }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">カテゴリ</span>
                    <span class="detail-value">{{ getDomainLabel(item.domain) }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">種別</span>
                    <span class="detail-value">{{ getCategoryLabel(item.category) }}</span>
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
                    <span class="detail-value" v-html="item.description || '-'"></span>
                  </div>
                  <div class="detail-item full detail-actions">
                    <button
                      v-if="isPurchaseOrderNotification(item)"
                      class="btn task-link-btn"
                      type="button"
                      @click.stop="openTaskInbox(item)"
                    >
                      📌 タスクへ
                    </button>
                    <button
                      v-if="!item.is_read"
                      class="btn confirm-btn"
                      @click.stop="handleMarkRead(item.id)"
                    >
                      ✓ 確認した
                    </button>
                    <span v-else class="confirmed-label">✓ 確認済み</span>
                  </div>
                </div>
              </td>
            </tr>
          </template>
          <tr v-if="!sortedNotifications.length">
            <td colspan="10" class="empty">通知はありません。</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { authState } from "@/auth";
import api from "@/api/client";

const router = useRouter();
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

const positionLabelMap = {
  manager: "事業部長・課長",
  chief: "係長",
  supervisor: "班長",
  leader: "リーダー",
  staff: "一般",
};

const toId = (value) => (value === null || value === undefined ? "" : String(value));

const departmentLevelMap = computed(() => {
  const map = new Map();
  departments.value.forEach((dept) => {
    map.set(toId(dept.id), dept.level);
  });
  return map;
});

const getTargetLevelSets = (targetDepartments) => {
  const team = new Set();
  const group = new Set();
  const division = new Set();
  targetDepartments.forEach((deptId) => {
    const id = toId(deptId);
    const level = departmentLevelMap.value.get(id);
    if (level === "team") team.add(id);
    if (level === "group") group.add(id);
    if (level === "division") division.add(id);
  });
  return { team, group, division };
};

const matchesDepartmentTarget = (targetDepartments, userLevels) => {
  if (!targetDepartments.length) return true;
  const { team, group, division } = getTargetLevelSets(targetDepartments);
  const userTeam = toId(userLevels.team);
  const userGroup = toId(userLevels.group);
  const userDivision = toId(userLevels.division);
  if (team.size) return team.has(userTeam);
  if (group.size) return group.has(userGroup);
  if (division.size) return division.has(userDivision);
  return false;
};

const matchesPositionTarget = (targetPositions, userPosition) => {
  if (!targetPositions.length) return true;
  if (!userPosition) return false;
  return targetPositions.some((pos) => String(pos) === String(userPosition));
};

const parseLocalDate = (value) => {
  if (!value) return null;
  const matched = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value));
  if (matched) {
    return new Date(Number(matched[1]), Number(matched[2]) - 1, Number(matched[3]));
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed;
};

const isWithinRange = (item) => {
  const now = new Date();
  const todayYmd = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const from = parseLocalDate(item.valid_from);
  const to = parseLocalDate(item.valid_to);
  if (from && todayYmd < from) return false;
  if (to && todayYmd > to) return false;
  return true;
};

const matchesUserTarget = (targetUsers, userId) => {
  if (!targetUsers.length) return false;
  return targetUsers.some((id) => String(id) === String(userId));
};

const filteredNotifications = computed(() => {
  const userId = authState.user?.id;
  const userDivisionId = authState.user?.profile?.division_id ?? authState.user?.profile?.division ?? null;
  const userGroupId = authState.user?.profile?.group_id ?? authState.user?.profile?.group ?? null;
  const userTeamId = authState.user?.profile?.team_id ?? authState.user?.profile?.team ?? null;
  const userPosition = authState.user?.profile?.role || "";
  return notifications.value.filter((item) => {
    if (!item) return false;
    if (!isWithinRange(item)) return false;
    const targetDepartments = Array.isArray(item.target_departments) ? item.target_departments : [];
    const targetPositions = Array.isArray(item.target_positions) ? item.target_positions : [];
    const targetUsers = Array.isArray(item.target_users) ? item.target_users : [];

    const hasTargetUsers = targetUsers.length > 0;
    if (hasTargetUsers && !matchesUserTarget(targetUsers, userId)) return false;

    // 部署・役職・ユーザーが未指定の場合は全員対象
    if (!targetDepartments.length && !targetPositions.length && !targetUsers.length) return true;

    // 部署・役職でのマッチ判定
    if (!matchesDepartmentTarget(targetDepartments, {
      division: userDivisionId,
      group: userGroupId,
      team: userTeamId,
    })) return false;
    if (!matchesPositionTarget(targetPositions, userPosition)) return false;
    return true;
  });
});

const sortedNotifications = computed(() => {
  return [...filteredNotifications.value].sort((a, b) => {
    const aOrder = Number(a.display_order ?? 10);
    const bOrder = Number(b.display_order ?? 10);
    if (aOrder !== bOrder) return aOrder - bOrder;
    const aDate = a.created_at ? new Date(a.created_at).getTime() : 0;
    const bDate = b.created_at ? new Date(b.created_at).getTime() : 0;
    if (aDate !== bDate) return bDate - aDate;
    return (b.id || 0) - (a.id || 0);
  });
});

const unreadCount = computed(() => filteredNotifications.value.filter((item) => !item.is_read).length);

const getDomainLabel = (domain) => {
  const found = domainOptions.find((opt) => opt.value === domain);
  return found ? found.label : domain;
};

const getCategoryLabel = (category) => {
  const found = categoryOptions.find((opt) => opt.value === category);
  return found ? found.label : category;
};

const getPositionLabel = (position) => {
  const key = String(position || "").trim();
  return positionLabelMap[key] || key;
};

const getTargetLabel = (item) => {
  const deptNames = Array.isArray(item.target_department_names) ? item.target_department_names : [];
  const posList = Array.isArray(item.target_positions) ? item.target_positions : [];
  const userNames = Array.isArray(item.target_user_names) ? item.target_user_names : [];
  const deptText = deptNames.length ? deptNames.join(" / ") : "";
  const posText = posList.length ? posList.map((pos) => getPositionLabel(pos)).join(" / ") : "";
  const userText = userNames.length ? userNames.join(" / ") : "";
  if (deptText && posText && userText) return `${deptText} / ${posText} / ${userText}`;
  if (deptText && posText) return `${deptText} / ${posText}`;
  if (deptText && userText) return `${deptText} / ${userText}`;
  if (posText && userText) return `${posText} / ${userText}`;
  if (deptText) return deptText;
  if (posText) return posText;
  if (userText) return userText;
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

const isPurchaseOrderNotification = (item) => {
  const domain = String(item?.domain || "").toUpperCase();
  return domain === "PURCHASE_ORDER";
};

const openTaskInbox = () => {
  router.push("/tasks");
};

const handleMarkRead = async (id) => {
  try {
    await api.notifications.markRead(id);
    // 通知リストを再読み込み
    await loadNotifications();
  } catch (error) {
    console.error("確認処理に失敗しました:", error);
  }
};

const handleMarkAllRead = async () => {
  const targetIds = filteredNotifications.value.filter((item) => !item.is_read).map((item) => item.id);
  if (!targetIds.length) return;
  try {
    await api.notifications.markAllRead(targetIds);
    await loadNotifications();
  } catch (error) {
    console.error("一括確認処理に失敗しました:", error);
  }
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

.action-cell {
  white-space: nowrap;
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

.row-main.unread td {
  color: #2563eb;
  font-weight: 500;
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

/* HTMLテーブルを含む説明欄の余白調整 */
.detail-value :deep(table) {
  margin-top: 4px;
}

.detail-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #e2e8f0;
}

.task-link-btn {
  background: #2563eb;
  color: #fff;
}

.task-link-btn:hover {
  background: #1d4ed8;
}

.confirm-btn {
  background: #10b981;
  color: #fff;
}

.confirm-btn:hover {
  background: #059669;
}

.confirm-btn-inline {
  background: #10b981;
  color: #fff;
  padding: 4px 10px;
  font-size: 12px;
}

.confirm-btn-inline:hover {
  background: #059669;
}

.confirm-all-btn {
  background: #0f766e;
  color: #fff;
}

.confirm-all-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

.confirmed-label {
  color: #10b981;
  font-size: 13px;
  font-weight: 500;
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
