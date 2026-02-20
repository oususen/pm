const engineeringChange = [
  {
    path: "/engineering-change/menu",
    name: "EngineeringChangeMenu",
    component: () => import("@/views/engineering-change/EngineeringChangeMenu.vue"),
    meta: { pageTitle: "設変新規管理メニュー", resource: "engineering_change" },
  },
  {
    path: "/engineering-change/new",
    name: "EngineeringChangeNew",
    component: () => import("@/views/engineering-change/EngineeringChangeNew.vue"),
    meta: { pageTitle: "設変新規管理 - 新規", resource: "engineering_change" },
  },
  {
    path: "/engineering-change/change",
    name: "EngineeringChangeTile",
    component: () => import("@/views/engineering-change/EngineeringChangeTile.vue"),
    meta: { pageTitle: "設変タイル", resource: "engineering_change" },
  },
];

export default engineeringChange;
