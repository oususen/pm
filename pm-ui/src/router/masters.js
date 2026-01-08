const masters = [
  {
    path: "/masters",
    name: "MasterMenu",
    component: () => import("@/views/masters/MasterMenu.vue"),
    meta: { pageTitle: "マスタメンテ" },
  },
  {
    path: "/masters/product",
    name: "ProductMaster",
    component: () => import("@/views/masters/ProductMaster.vue"),
    meta: { pageTitle: "製品マスタ" },
  },
  {
    path: "/masters/product-group",
    name: "ProductGroupMaster",
    component: () => import("@/views/masters/ProductGroupMaster.vue"),
    meta: { pageTitle: "製品グループマスタ" },
  },
  {
    path: "/masters/container-capacity",
    name: "ContainerCapacityMaster",
    component: () => import("@/views/masters/ContainerCapacityMaster.vue"),
    meta: { pageTitle: "容器マスタ" },
  },
  {
    path: "/masters/customer",
    name: "CustomerMaster",
    component: () => import("@/views/masters/CustomerMaster.vue"),
    meta: { pageTitle: "得意先マスタ" },
  },
  {
    path: "/masters/supplier",
    name: "SupplierMaster",
    component: () => import("@/views/masters/SupplierMaster.vue"),
    meta: { pageTitle: "仕入先マスタ" },
  },
  {
    path: "/masters/process",
    name: "ProcessMaster",
    component: () => import("@/views/masters/ProcessMaster.vue"),
    meta: { pageTitle: "工程マスタ" },
  },
  {
    path: "/masters/line",
    name: "LineMaster",
    component: () => import("@/views/masters/LineMaster.vue"),
    meta: { pageTitle: "ラインマスタ" },
  },
  {
    path: "/masters/calendar",
    name: "CalendarMaster",
    component: () => import("@/views/masters/CalendarMaster.vue"),
    meta: { pageTitle: "カレンダマスタ" },
  },
  {
    path: "/masters/work-pattern",
    name: "WorkPatternMaster",
    component: () => import("@/views/masters/WorkPatternMaster.vue"),
    meta: { pageTitle: "勤務パターンマスタ" },
  },
  {
    path: "/masters/bom",
    name: "BOMMaster",
    component: () => import("@/views/masters/BOMMaster.vue"),
    meta: { pageTitle: "構成マスタ（BOM）" },
  },
];

export default masters;
