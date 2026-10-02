const engineeringChange = [
  {
    path: "/engineering-change/menu",
    name: "EngineeringChangeMenu",
    component: () => import("@/views/engineering-change/EngineeringChangeMenu.vue"),
    meta: { pageTitle: "設変メニュー", manualPath: "設変/設変管理.md", resource: "engineering_change" },
  },
  {
    path: "/engineering-change/new",
    name: "EngineeringChangeNew",
    component: () => import("@/views/engineering-change/EngineeringChangeNew.vue"),
    meta: { pageTitle: "設変 - 新規", manualPath: "設変/設変管理.md", resource: "engineering_change" },
  },
  {
    path: "/engineering-change/change",
    name: "EngineeringChangeTile",
    component: () => import("@/views/engineering-change/EngineeringChangeTile.vue"),
    meta: { pageTitle: "設変タイル", manualPath: "設変/設変管理.md", resource: "engineering_change" },
  },
  {
    path: "/engineering-change/discontinuation",
    name: "DiscontinuationManagement",
    component: () => import("@/views/engineering-change/DiscontinuationManagement.vue"),
    meta: { pageTitle: "打ち切り管理", resource: "engineering_change" },
  },
];

export default engineeringChange;
