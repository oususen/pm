const settings = [
  {
    path: "/settings",
    name: "SettingsMenu",
    component: () => import("@/views/settings/SettingsMenu.vue"),
    meta: { pageTitle: "設定", resource: "settings" },
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
];

export default settings;
