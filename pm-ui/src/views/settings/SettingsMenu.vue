<template>
  <div class="master-menu">
    <h2 class="page-title">設定</h2>

    <div class="master-grid">
      <RouterLink v-if="canAccessSetting('settings.profile', 'view')" to="/settings/profile" class="master-tile">
        <div class="icon-box">👤</div>
        <div class="label">プロフィール編集</div>
      </RouterLink>
      <RouterLink v-if="canAccessSetting('settings.users', 'view')" to="/settings/users" class="master-tile">
        <div class="icon-box">👤</div>
        <div class="label">ユーザー管理</div>
      </RouterLink>
      <RouterLink v-if="canAccessSetting('settings.user_permissions', 'view')" to="/settings/user-permissions" class="master-tile">
        <div class="icon-box">🛡️</div>
        <div class="label">ユーザー権限編集</div>
      </RouterLink>
      <RouterLink v-if="canAccessSetting('settings.permission_templates', 'view')" to="/settings/permission-templates" class="master-tile">
        <div class="icon-box">👤</div>
        <div class="label">権限テンプレート</div>
      </RouterLink>
      <RouterLink v-if="canAccessSetting('settings.smtp', 'view')" to="/settings/smtp" class="master-tile">
        <div class="icon-box">📧</div>
        <div class="label">SMTP設定</div>
      </RouterLink>
      <RouterLink v-if="canAccessSetting('settings.purchase_plan_lock', 'view')" to="/settings/purchase-plan-lock" class="master-tile">
        <div class="icon-box">🔒</div>
        <div class="label">仕入計画ロック設定</div>
      </RouterLink>
      <RouterLink v-if="canAccessSetting('settings.production_plan_lock', 'view')" to="/settings/production-plan-lock" class="master-tile">
        <div class="icon-box">🔒</div>
        <div class="label">生産計画ロック設定</div>
      </RouterLink>
      <RouterLink v-if="canAccessSetting('settings.scheduled_tasks', 'view')" to="/settings/task-settings" class="master-tile">
        <div class="icon-box">⏰</div>
        <div class="label">タスク設定</div>
      </RouterLink>
      <RouterLink v-if="canAccessSetting('settings.stocktake_init', 'view')" to="/settings/stocktake-init" class="master-tile">
        <div class="icon-box">📦</div>
        <div class="label">棚卸初期化</div>
      </RouterLink>
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
</script>
