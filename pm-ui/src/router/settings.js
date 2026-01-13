const settings = [
  {
    path: "/settings",
    name: "SettingsMenu",
    component: () => import("@/views/settings/SettingsMenu.vue"),
    meta: { pageTitle: "設定" },
  },
  {
    path: "/settings/users",
    name: "UserManagement",
    component: () => import("@/views/settings/UserManagement.vue"),
    meta: { pageTitle: "ユーザー管理" },
  },
];

export default settings;
