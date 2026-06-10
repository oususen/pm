<template>
  <div class="notification-sources">
    <h2 class="page-title">通知入力 <DataSourceDialog title="通知入力" :sources="dsSources" /></h2>
    <p class="page-note">
      時限設定を忘れないように設定してください。<br/>
      ・有効終了日なしの通知は作成から5日後に非表示、10日後にDB削除されます<br/>
      ・有効終了日ありの通知は終了日経過で非表示、5日後にDB削除されます
    </p>

    <div v-if="!canView" class="no-permission">
      権限がありません。
    </div>

    <template v-else>
      <div class="form-card" :class="{ disabled: !canEdit }">
        <h3 class="section-title">知らせの登録</h3>
        <div class="form-grid">
          <div class="form-field">
            <label class="label-required">タイトル</label>
            <input
              v-model="form.title"
              type="text"
              placeholder="例: 生産実績"
              :disabled="!canEdit"
              class="input"
            />
          </div>
          <div class="form-field">
            <label class="label-required">種別</label>
            <select v-model="form.category" :disabled="!canEdit" class="input">
              <option v-for="opt in categoryOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
          <div class="form-field">
            <label class="label-required">カテゴリ</label>
            <select v-model="form.domain" :disabled="!canEdit" class="input">
              <option v-for="opt in domainOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
          <div class="form-field">
            <label>対象事業部</label>
            <select v-model="form.target_divisions" multiple :disabled="!canEdit" class="input">
              <option v-for="dept in divisionOptions" :key="dept.id" :value="dept.id">
                {{ dept.name }}
              </option>
            </select>
          </div>
          <div class="form-field">
            <label>対象係</label>
            <select
              v-model="form.target_groups"
              multiple
              :disabled="!canEdit || !form.target_divisions.length"
              class="input"
            >
              <option v-for="dept in filteredGroupOptions" :key="dept.id" :value="dept.id">
                {{ dept.name }}
              </option>
            </select>
          </div>
          <div class="form-field">
            <label>対象班</label>
            <select
              v-model="form.target_teams"
              multiple
              :disabled="!canEdit || !form.target_groups.length"
              class="input"
            >
              <option v-for="dept in filteredTeamOptions" :key="dept.id" :value="dept.id">
                {{ dept.name }}
              </option>
            </select>
          </div>
          <div class="form-field">
            <label>対象役職</label>
            <select
              v-model="form.target_positions"
              multiple
              :disabled="!canEdit"
              class="input"
            >
              <option v-for="pos in positions" :key="pos" :value="pos">
                {{ getPositionLabel(pos) }}
              </option>
            </select>
          </div>
          <div class="form-field">
            <label>対象ユーザー（個別指定）</label>
            <select
              v-model="form.target_users"
              multiple
              :disabled="!canEdit"
              class="input"
            >
              <option v-for="user in userOptions" :key="user.id" :value="user.id">
                {{ user.name }}
              </option>
            </select>
          </div>
          <div class="form-field">
            <label>有効開始日</label>
            <input
              v-model="form.valid_from"
              type="date"
              :disabled="!canEdit"
              class="input"
            />
          </div>
          <div class="form-field">
            <label>有効終了日</label>
            <input
              v-model="form.valid_to"
              type="date"
              :disabled="!canEdit"
              class="input"
            />
          </div>
          <div class="form-field">
            <label>表示順（通常は10。上に固定したい場合は9以下に設定）</label>
            <input
              v-model.number="form.display_order"
              type="number"
              min="0"
              step="1"
              :disabled="!canEdit"
              class="input"
            />
          </div>
          <div class="form-field full">
            <label>説明</label>
            <textarea
              v-model="form.description"
              rows="3"
              placeholder="説明を入力"
              :disabled="!canEdit"
              class="input textarea"
            ></textarea>
          </div>
          <div class="form-field">
            <label class="label-required">入力者</label>
            <input
              v-model="form.operator_name"
              type="text"
              placeholder="入力者名を入力"
              :disabled="!canEdit"
              class="input"
            />
          </div>
        </div>
        <div class="form-actions">
          <button
            class="btn primary"
            type="button"
            @click="submitForm"
            :disabled="!canEdit"
          >
            {{ isEditing ? '更新' : '登録' }}
          </button>
          <button
            class="btn secondary"
            type="button"
            @click="resetForm"
            :disabled="!canEdit"
          >
            クリア
          </button>
        </div>
        <div v-if="errorMessage" class="error-text">{{ errorMessage }}</div>
      </div>

      <div class="list-card">
        <h3 class="section-title">登録済み一覧</h3>
        <table class="source-table">
          <thead>
            <tr>
              <th>表示順</th>
              <th>タイトル</th>
              <th>カテゴリ</th>
              <th>種別</th>
              <th>作成日</th>
              <th>有効開始日</th>
              <th>有効終了日</th>
              <th>対象者</th>
              <th>未閲覧者</th>
              <th>入力者</th>
              <th>説明</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in sortedSources" :key="item.id">
              <td>{{ item.display_order }}</td>
              <td>{{ item.title }}</td>
              <td>{{ getDomainLabel(item.domain) }}</td>
              <td>{{ getCategoryLabel(item.category) }}</td>
              <td>{{ formatDateTime(item.created_at) }}</td>
              <td>{{ item.valid_from || '-' }}</td>
              <td>{{ item.valid_to || '-' }}</td>
              <td>{{ getTargetLabel(item) }}</td>
              <td class="unread-users">{{ getUnreadUsersLabel(item) }}</td>
              <td>{{ item.operator_name || '-' }}</td>
              <td class="description">{{ item.description || '-' }}</td>
              <td class="actions">
                <button class="btn link" type="button" @click="editSource(item)" :disabled="!canEdit">
                  編集
                </button>
                <button class="btn link danger" type="button" @click="removeSource(item)" :disabled="!canEdit">
                  削除
                </button>
              </td>
            </tr>
            <tr v-if="!sortedSources.length">
              <td colspan="12" class="empty">登録済みの知らせ源はありません。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { authState } from "@/auth";
import { hasPermission } from "@/router";
import api from "@/api/client";
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 't_notification_source', desc: '通知元データの一覧取得・登録・更新・削除' },
  { op: '読み取り', table: 't_department', desc: '事業部・係・班の取得' },
  { op: '読み取り', table: 't_user', desc: 'ユーザー一覧の取得' },
  { op: '読み取り', table: 't_department_position', desc: '役職一覧の取得' },
]

const canView = computed(() => hasPermission(authState.user, "notifications", "view"));
const canEdit = computed(() => hasPermission(authState.user, "notifications", "edit"));

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

const sources = ref([]);
const errorMessage = ref("");
const departments = ref([]);
const positions = ref([]);
const users = ref([]);
const keepPositionOnDeptChange = ref(false);
const defaultOperatorName = computed(() => {
  const user = authState.user;
  if (!user) return "";
  const fullName = `${user.last_name || ""} ${user.first_name || ""}`.trim();
  return fullName || user.username || user.email || "";
});
const form = ref({
  id: null,
  title: "",
  category: "progress",
  domain: "production",
  target_divisions: [],
  target_groups: [],
  target_teams: [],
  target_positions: [],
  target_users: [],
  valid_from: "",
  valid_to: "",
  display_order: 10,
  description: "",
  operator_name: defaultOperatorName.value,
});

const toId = (value) => (value === null || value === undefined ? "" : String(value));

const parentMap = computed(() => {
  const map = new Map();
  departments.value.forEach((dept) => {
    map.set(toId(dept.id), toId(dept.parent));
  });
  return map;
});

const departmentLevelMap = computed(() => {
  const map = new Map();
  departments.value.forEach((dept) => {
    map.set(toId(dept.id), dept.level);
  });
  return map;
});

const isDescendantOf = (childId, ancestorId) => {
  let cursor = toId(childId);
  const target = toId(ancestorId);
  if (!cursor || !target) return false;
  const seen = new Set();
  while (cursor && !seen.has(cursor)) {
    seen.add(cursor);
    const parent = parentMap.value.get(cursor);
    if (!parent) return false;
    if (parent === target) return true;
    cursor = parent;
  }
  return false;
};

const isDescendantOfAny = (childId, ancestorIds) => {
  return ancestorIds.some((ancestorId) => isDescendantOf(childId, ancestorId));
};

const filterIdsByOptions = (ids, options) => {
  const allowed = new Set(options.map((opt) => String(opt.id)));
  return ids.filter((id) => allowed.has(String(id)));
};

const divisionOptions = computed(() =>
  departments.value.filter((dept) => dept.level === "division")
);
const groupOptions = computed(() =>
  departments.value.filter((dept) => dept.level === "group")
);
const teamOptions = computed(() =>
  departments.value.filter((dept) => dept.level === "team")
);
const filteredGroupOptions = computed(() =>
  groupOptions.value.filter((dept) => isDescendantOfAny(dept.id, form.value.target_divisions))
);
const filteredTeamOptions = computed(() =>
  teamOptions.value.filter((dept) => isDescendantOfAny(dept.id, form.value.target_groups))
);

const getUserLevelIds = (user) => {
  const profile = user?.profile || {};
  const division = profile.division_id ?? profile.division ?? null;
  const group = profile.group_id ?? profile.group ?? null;
  const team = profile.team_id ?? profile.team ?? null;
  if (division || group || team) {
    return { division, group, team };
  }
  const department = profile.department_id ?? profile.department ?? null;
  if (!department) {
    return { division, group, team };
  }
  const level = departmentLevelMap.value.get(toId(department));
  return {
    division: level === "division" ? department : division,
    group: level === "group" ? department : group,
    team: level === "team" ? department : team,
  };
};

const normalizeName = (value) => (value || "").replace(/\s+/g, "").trim();

const operatorCandidates = computed(() => {
  const user = authState.user;
  if (!user) return [];
  const fullWithSpace = `${user.last_name || ""} ${user.first_name || ""}`.trim();
  const fullNoSpace = `${user.last_name || ""}${user.first_name || ""}`.trim();
  return [fullWithSpace, fullNoSpace, user.username, user.email].filter(Boolean);
});

const isOperator = (item) => {
  const operator = (item?.operator_name || "").trim();
  if (!operator) return false;
  const normalized = normalizeName(operator);
  return operatorCandidates.value.some((candidate) => normalizeName(candidate) === normalized);
};

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

const matchesUserTarget = (targetUsers, userId) => {
  if (!targetUsers.length) return false;
  return targetUsers.some((id) => String(id) === String(userId));
};

const matchesUserDepartmentSelection = (user) => {
  const { division, group, team } = getUserLevelIds(user);
  if (form.value.target_teams.length) {
    return form.value.target_teams.some((id) => toId(id) === toId(team));
  }
  if (form.value.target_groups.length) {
    return form.value.target_groups.some((id) => toId(id) === toId(group));
  }
  if (form.value.target_divisions.length) {
    return form.value.target_divisions.some((id) => toId(id) === toId(division));
  }
  return true;
};

const matchesUserPositionSelection = (user) => {
  const targetPositions = form.value.target_positions;
  if (!targetPositions.length) return true;
  const userPosition = user?.profile?.role || user?.profile?.position || "";
  if (!userPosition) return false;
  return targetPositions.some((pos) => String(pos) === String(userPosition));
};

const userOptions = computed(() => {
  const filteredUsers = users.value.filter((u) => {
    if (!u) return false;
    if (!matchesUserDepartmentSelection(u)) return false;
    if (!matchesUserPositionSelection(u)) return false;
    return true;
  });
  const selectedIds = new Set(form.value.target_users.map((id) => toId(id)));
  const selectedUsers = users.value.filter((u) => selectedIds.has(toId(u.id)));
  const merged = [...filteredUsers, ...selectedUsers].filter(
    (u, index, list) => list.findIndex((item) => toId(item.id) === toId(u.id)) === index
  );
  return merged.map((u) => {
    const fullName = `${u.last_name || ""}${u.first_name || ""}`.trim();
    return {
      id: u.id,
      name: fullName || u.username || u.email || `ID: ${u.id}`,
    };
  });
});

const selectedDepartmentIds = computed(() => {
  const merged = new Set();
  form.value.target_divisions.forEach((id) => merged.add(id));
  form.value.target_groups.forEach((id) => merged.add(id));
  form.value.target_teams.forEach((id) => merged.add(id));
  return Array.from(merged);
});

const isEditing = computed(() => form.value.id !== null);

const isWithinRange = (item) => {
  const today = new Date();
  const todayYmd = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const from = item.valid_from ? new Date(item.valid_from) : null;
  const to = item.valid_to ? new Date(item.valid_to) : null;
  if (from && todayYmd < from) return false;
  if (to && todayYmd > to) return false;
  return true;
};

const filteredSources = computed(() => {
  const user = authState.user;
  if (!user) return [];
  const userId = user.id;
  const { division, group, team } = getUserLevelIds(user);
  const userPosition = user?.profile?.role || user?.profile?.position || "";
  return sources.value.filter((item) => {
    if (!item) return false;
    if (isOperator(item)) return true;
    if (!isWithinRange(item)) return false;
    const targetDepartments = Array.isArray(item.target_departments) ? item.target_departments : [];
    const targetPositions = Array.isArray(item.target_positions) ? item.target_positions : [];
    const targetUsers = Array.isArray(item.target_users) ? item.target_users : [];
    const hasTargetUsers = targetUsers.length > 0;
    if (hasTargetUsers && !matchesUserTarget(targetUsers, userId)) return false;
    if (!targetDepartments.length && !targetPositions.length && !targetUsers.length) return true;
    if (!matchesDepartmentTarget(targetDepartments, { division, group, team })) return false;
    if (!matchesPositionTarget(targetPositions, userPosition)) return false;
    return true;
  });
});

const sortedSources = computed(() => {
  return [...filteredSources.value].sort((a, b) => {
    const aDate = a.created_at ? new Date(a.created_at).getTime() : 0;
    const bDate = b.created_at ? new Date(b.created_at).getTime() : 0;
    if (aDate !== bDate) return bDate - aDate;
    return (b.id || 0) - (a.id || 0);
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

const getPositionLabel = (position) => {
  const key = String(position || "").trim();
  return positionLabelMap[key] || key;
};

const getTargetLabel = (item) => {
  const deptNames = Array.isArray(item.target_department_names) ? item.target_department_names : [];
  const posList = Array.isArray(item.target_positions) ? item.target_positions : [];
  const userNames = Array.isArray(item.target_user_names) ? item.target_user_names : [];
  const parts = [];
  if (deptNames.length) parts.push(deptNames.join(' / '));
  if (posList.length) parts.push(posList.map((pos) => getPositionLabel(pos)).join(' / '));
  if (userNames.length) parts.push(userNames.join(' / '));
  return parts.length ? parts.join(' / ') : '-';
};

const getUnreadUsersLabel = (item) => {
  const users = Array.isArray(item.unread_users) ? item.unread_users : [];
  if (!users.length) return "-";
  return users.join(", ");
};

const formatDateTime = (value) => {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
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

const loadUsers = async () => {
  try {
    const collected = [];
    let page = 1;
    let hasNext = true;
    while (hasNext) {
      const res = await api.accounts.getUsers({
        is_active: true,
        ordering: "last_name,first_name",
        page_size: 500,
        page,
      });
      const data = res.data;
      if (Array.isArray(data)) {
        collected.push(...data);
        hasNext = false;
        break;
      }
      const list = Array.isArray(data?.results) ? data.results : [];
      collected.push(...list);
      hasNext = Boolean(data?.next);
      page += 1;
      if (!data?.next) break;
    }
    users.value = collected;
  } catch (error) {
    console.error("ユーザー一覧の取得に失敗しました:", error);
    users.value = [];
  }
};

const loadPositions = async (departmentIds) => {
  if (!departmentIds || !departmentIds.length) {
    positions.value = [];
    return;
  }
  try {
    const requests = departmentIds.map((id) =>
      api.accounts.getDepartmentPositions({ department: id })
    );
    const responses = await Promise.all(requests);
    const merged = new Set();
    responses.forEach((res) => {
      const list = Array.isArray(res.data) ? res.data : [];
      list.forEach((pos) => merged.add(pos));
    });
    const mergedList = Array.from(merged);
    if (mergedList.length) {
      positions.value = mergedList;
      return;
    }
    const fallback = await api.accounts.getPositions();
    positions.value = Array.isArray(fallback.data) ? fallback.data : [];
  } catch (error) {
    console.error("役職一覧の取得に失敗しました:", error);
    positions.value = [];
  }
};

const loadSources = async () => {
  try {
    const res = await api.notifications.list({ ordering: "display_order,id" });
    const data = res.data?.results || res.data || [];
    sources.value = Array.isArray(data) ? data : [];
  } catch (error) {
    console.error("通知の読み込みに失敗しました:", error);
    sources.value = [];
  }
};

const resetForm = () => {
  form.value = {
    id: null,
    title: "",
    category: "progress",
    domain: "production",
    target_divisions: [],
    target_groups: [],
    target_teams: [],
    target_positions: [],
    target_users: [],
    valid_from: "",
    valid_to: "",
    display_order: 10,
    description: "",
    operator_name: defaultOperatorName.value,
  };
  keepPositionOnDeptChange.value = false;
  errorMessage.value = "";
};

const submitForm = async () => {
  if (!canEdit.value) return;
  const name = (form.value.title || "").trim();
  const category = (form.value.category || "").trim();
  const domain = form.value.domain;
  const targetDepartments = selectedDepartmentIds.value;
  const targetPositions = form.value.target_positions;
  if (!name || !category || !domain) {
    errorMessage.value = "必須項目を入力してください。";
    return;
  }

  errorMessage.value = "";
  const payload = {
    title: name,
    category,
    domain,
    target_departments: targetDepartments,
    target_positions: targetPositions,
    target_users: form.value.target_users,
    valid_from: form.value.valid_from || null,
    valid_to: form.value.valid_to || null,
    display_order: Number(form.value.display_order || 0),
    description: (form.value.description || "").trim(),
    operator_name: (form.value.operator_name || "").trim() || defaultOperatorName.value,
  };
  try {
    if (isEditing.value) {
      await api.notifications.update(form.value.id, payload);
    } else {
      await api.notifications.create(payload);
    }
    await loadSources();
    resetForm();
  } catch (error) {
    console.error("通知の登録に失敗しました:", error);
    errorMessage.value = "登録に失敗しました。";
  }
};

const editSource = async (item) => {
  if (!canEdit.value) return;
  if (!departments.value.length) {
    await loadDepartments();
  }
  keepPositionOnDeptChange.value = true;
  const targetDepartments = Array.isArray(item.target_departments) ? item.target_departments : [];
  const divisions = [];
  const groups = [];
  const teams = [];
  targetDepartments.forEach((id) => {
    const dept = departments.value.find((d) => String(d.id) === String(id));
    if (!dept) return;
    if (dept.level === "division") divisions.push(dept.id);
    if (dept.level === "group") groups.push(dept.id);
    if (dept.level === "team") teams.push(dept.id);
  });
  form.value = {
    id: item.id,
    title: item.title,
    category: item.category || "progress",
    domain: item.domain,
    target_divisions: divisions,
    target_groups: groups,
    target_teams: teams,
    target_positions: Array.isArray(item.target_positions) ? item.target_positions : [],
    target_users: Array.isArray(item.target_users) ? item.target_users : [],
    valid_from: item.valid_from || "",
    valid_to: item.valid_to || "",
    display_order: item.display_order,
    description: item.description || "",
    operator_name: item.operator_name || defaultOperatorName.value,
  };
  errorMessage.value = "";
};

const removeSource = async (item) => {
  if (!canEdit.value) return;
  if (!window.confirm("この通知を削除しますか？")) return;
  try {
    await api.notifications.delete(item.id);
    await loadSources();
  } catch (error) {
    console.error("通知の削除に失敗しました:", error);
  }
  if (form.value.id === item.id) {
    resetForm();
  }
};

onMounted(() => {
  loadSources();
  loadDepartments();
  loadUsers();
  if (!(form.value.operator_name || "").trim()) {
    form.value.operator_name = defaultOperatorName.value;
  }
});

watch(
  () => authState.user,
  () => {
    if (!(form.value.operator_name || "").trim()) {
      form.value.operator_name = defaultOperatorName.value;
    }
  }
);

watch(
  () => form.value.target_divisions,
  (val) => {
    const filteredGroups = filterIdsByOptions(form.value.target_groups, filteredGroupOptions.value);
    if (filteredGroups.length !== form.value.target_groups.length) {
      form.value.target_groups = filteredGroups;
    }
    const filteredTeams = filterIdsByOptions(form.value.target_teams, filteredTeamOptions.value);
    if (filteredTeams.length !== form.value.target_teams.length) {
      form.value.target_teams = filteredTeams;
    }
  }
);

watch(
  () => form.value.target_groups,
  () => {
    const filteredTeams = filterIdsByOptions(form.value.target_teams, filteredTeamOptions.value);
    if (filteredTeams.length !== form.value.target_teams.length) {
      form.value.target_teams = filteredTeams;
    }
  }
);

watch(
  () => selectedDepartmentIds.value,
  async (val) => {
    if (!keepPositionOnDeptChange.value) {
      form.value.target_positions = [];
    }
    await loadPositions(val);
    if (keepPositionOnDeptChange.value) {
      keepPositionOnDeptChange.value = false;
    }
  }
);
</script>

<style scoped>
.notification-sources {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}

.page-title {
  margin: 0 0 6px 0;
  font-size: 22px;
  font-weight: 700;
  color: #1f2a44;
}

.page-note {
  margin: 0 0 16px 0;
  font-size: 13px;
  color: #64748b;
}

.no-permission {
  padding: 16px;
  border: 1px solid #f2c9c9;
  border-radius: 8px;
  background: #fff5f5;
  color: #b91c1c;
  font-weight: 600;
}

.form-card,
.list-card {
  background: #fff;
  border-radius: 10px;
  padding: 16px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
  margin-bottom: 16px;
}

.form-card.disabled {
  opacity: 0.7;
}

.section-title {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 700;
  color: #1f2a44;
}

.form-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.form-field.full {
  grid-column: 1 / -1;
}

label {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #1f2a44;
}

.label-required::after {
  content: " *";
  color: #ef4444;
}

.input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
  font-family: inherit;
}
.input[multiple] {
  min-height: 120px;
}

.textarea {
  resize: vertical;
}

.form-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.btn {
  border: none;
  border-radius: 6px;
  padding: 8px 14px;
  font-size: 13px;
  cursor: pointer;
}

.btn.primary {
  background: #2563eb;
  color: #fff;
}

.btn.secondary {
  background: #e2e8f0;
  color: #1f2a44;
}

.btn.link {
  background: transparent;
  color: #2563eb;
  padding: 0 6px;
}

.btn.link.danger {
  color: #b91c1c;
}

.error-text {
  margin-top: 8px;
  color: #b91c1c;
  font-size: 12px;
  font-weight: 600;
}

.source-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.source-table th,
.source-table td {
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 6px;
}

.source-table th {
  background: #f8fafc;
  font-weight: 700;
  color: #1f2a44;
}

.description {
  max-width: 200px;
  color: #475569;
}

.unread-users {
  max-width: 180px;
  color: #b91c1c;
  font-size: 12px;
}

.actions {
  white-space: nowrap;
}

.empty {
  text-align: center;
  padding: 16px;
  color: #94a3b8;
}

@media (max-width: 768px) {
  .notification-sources {
    padding: 16px;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .source-table {
    font-size: 12px;
  }
}
</style>

