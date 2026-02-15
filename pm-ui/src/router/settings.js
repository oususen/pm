const settings = [
  {
    path: "/settings",
    name: "SettingsMenu",
    component: () => import("@/views/settings/SettingsMenu.vue"),
    meta: { pageTitle: "設定", resource: "settings" },
  },
  {
    path: "/settings/profile",
    name: "Profile",
    component: () => import("@/views/settings/Profile.vue"),
    meta: { pageTitle: "プロフィール編集" },
  },
  {
    path: "/settings/users",
    name: "UserManagement",
    component: () => import("@/views/settings/UserManagement.vue"),
    meta: { pageTitle: "ユーザー管理", resource: "users" },
  },
  {
    path: "/settings/permission-templates",
    name: "PermissionTemplates",
    component: () => import("@/views/settings/PermissionTemplates.vue"),
    meta: { pageTitle: "権限テンプレート", resource: "settings" },
  },
  {
    path: "/settings/smtp",
    name: "SmtpConfigSettings",
    component: () => import("@/views/settings/SmtpConfigSettings.vue"),
    meta: { pageTitle: "SMTP設定", resource: "settings" },
  },
  {
    path: "/settings/purchase-plan-lock",
    name: "PurchasePlanLockSetting",
    component: () => import("@/views/settings/PurchasePlanLockSetting.vue"),
    meta: { pageTitle: "仕入計画ロック設定", resource: "settings" },
  },
  {
    path: "/settings/production-plan-lock",
    name: "ProductionPlanLockSetting",
    component: () => import("@/views/settings/ProductionPlanLockSetting.vue"),
    meta: { pageTitle: "生産計画ロック設定", resource: "settings" },
  },
  {
    path: "/settings/scheduled-tasks",
    name: "ScheduledTasks",
    component: () => import("@/views/settings/ScheduledTasks.vue"),
    meta: { pageTitle: "定時タスク設定", resource: "settings" },
  },
  {
    path: "/settings/stocktake-init",
    name: "StocktakeInit",
    component: () => import("@/views/settings/StocktakeInit.vue"),
    meta: { pageTitle: "棚卸初期化", resource: "settings" },
  },
];

export default settings;
