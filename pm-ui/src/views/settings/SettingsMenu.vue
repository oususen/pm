<template>
  <div class="master-menu">
    <h2 class="page-title">設定</h2>

    <div class="menu-sections">
      <section
        v-for="(section, index) in groupedTiles"
        :key="section.key"
        class="menu-section"
        :class="{ 'has-divider': index > 0 }"
      >
        <h3 class="section-title">{{ section.label }}</h3>
        <div class="master-grid">
          <RouterLink
            v-for="tile in section.items"
            :key="tile.to"
            :to="tile.to"
            class="master-tile"
          >
            <div class="icon-box">{{ tile.icon }}</div>
            <div class="label">{{ tile.label }}</div>
          </RouterLink>
        </div>
      </section>
    </div>

    <p class="helper-text">
      設定メニューから各機能に遷移します。
    </p>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { authState } from "@/auth";
import { hasPermission } from "@/router";

const SECTION_ORDER = ["user", "lock", "task", "kubota", "system"];
const SECTION_LABELS = {
  user: "ユーザー・権限",
  lock: "計画ロック",
  task: "タスク・自動化",
  kubota: "クボタ堺",
  system: "システム",
};

const hasExplicitPermission = (user, resource, level = "view") => {
  if (!user || !resource) return false;
  if (user.is_superuser) return true;

  const permissions = Array.isArray(user.effective_permissions)
    ? user.effective_permissions
    : [];
  const perm = permissions.find((item) => item.resource === resource);
  if (!perm) return false;
  if (level === "edit") return Boolean(perm.can_edit);
  return Boolean(perm.can_view || perm.can_edit);
};

const hasPermissionEntry = (user, resource) => {
  if (!user || !resource) return false;
  const permissions = Array.isArray(user.effective_permissions)
    ? user.effective_permissions
    : [];
  return permissions.some((item) => item.resource === resource);
};

const canAccessSetting = (resource, level = "view") => {
  const user = authState.user;
  if (!user) return false;

  if (hasPermissionEntry(user, resource)) {
    return hasExplicitPermission(user, resource, level);
  }
  return hasPermission(user, "settings", level);
};

const tiles = computed(() => {
  const list = [
    { to: "/settings/profile", label: "プロフィール編集", icon: "👤", category: "user", resource: "settings.profile" },
    { to: "/settings/users", label: "ユーザー管理", icon: "👤", category: "user", resource: "settings.users" },
    { to: "/settings/departments", label: "組織管理", icon: "🏢", category: "user", resource: "settings.departments" },
    { to: "/settings/user-permissions", label: "ユーザー権限編集", icon: "🛡️", category: "user", resource: "settings.user_permissions" },
    { to: "/settings/permission-templates", label: "権限テンプレート", icon: "📝", category: "user", resource: "settings.permission_templates" },
    { to: "/settings/purchase-plan-lock", label: "仕入計画ロック設定", icon: "🔒", category: "lock", resource: "settings.purchase_plan_lock" },
    { to: "/settings/production-plan-lock", label: "生産計画ロック設定", icon: "🔒", category: "lock", resource: "settings.production_plan_lock" },
    { to: "/settings/kubota-sakai-due-plan-lock", label: "クボタ堺納期調整ロック設定", icon: "🔒", category: "lock", resource: "settings.production_plan_lock" },
    { to: "/settings/task-settings", label: "タスク設定", icon: "⏰", category: "task", resource: "settings.scheduled_tasks" },
    { to: "/settings/stocktake-init", label: "棚卸初期化", icon: "📦", category: "task", resource: "settings.stocktake_init" },
    { to: "/settings/kubota-import", label: "クボタ堺取り込み通知", icon: "🔔", category: "kubota", resource: "settings" },
    { to: "/settings/kubota-sakai-config", label: "クボタ堺便計画設定", icon: "🚛", category: "kubota", resource: "settings.kubota_sakai_config" },
    { to: "/settings/smtp", label: "SMTP設定", icon: "📧", category: "system", resource: "settings.smtp" },
    { to: "/settings/lock-date", label: "締め日管理", icon: "📅", category: "system", resource: "settings.lock_date" },
    { to: "/settings/android-app", label: "Androidアプリ配布", icon: "📱", category: "system", resource: "settings" },
    { to: "/settings/system", label: "システム設定", icon: "⚙️", category: "system", resource: "settings" },
  ];

  return list.filter((tile) => canAccessSetting(tile.resource, "view"));
});

const groupedTiles = computed(() => {
  const buckets = SECTION_ORDER.map((key) => ({
    key,
    label: SECTION_LABELS[key],
    items: [],
  }));
  const indexMap = Object.fromEntries(SECTION_ORDER.map((key, i) => [key, i]));
  for (const tile of tiles.value) {
    const key = tile.category && indexMap[tile.category] !== undefined ? tile.category : "system";
    buckets[indexMap[key]].items.push(tile);
  }
  return buckets.filter((section) => section.items.length);
});
</script>

<style scoped>
.master-menu {
  padding: 16px;
}
.menu-sections {
  display: grid;
  gap: 14px;
}
.menu-section.has-divider {
  border-top: 1px solid #dbe2ea;
  padding-top: 14px;
}
.section-title {
  margin: 0 0 8px;
  font-size: 14px;
  color: #334155;
}
.master-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}
.master-tile {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px;
  min-height: 72px;
  text-decoration: none;
  color: inherit;
  background: #fff;
  display: grid;
  gap: 6px;
  align-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
}
.master-tile .icon-box {
  font-size: 22px;
}
.master-tile .label {
  font-weight: 700;
}
.helper-text {
  margin-top: 10px;
  color: #64748b;
}
@media (max-width: 1400px) {
  .master-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
@media (max-width: 1100px) {
  .master-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 800px) {
  .master-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 520px) {
  .master-grid {
    grid-template-columns: 1fr;
  }
}
</style>
