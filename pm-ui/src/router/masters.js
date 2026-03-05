const masters = [
  {
    path: "/masters",
    name: "MasterMenu",
    component: () => import("@/views/masters/MasterMenu.vue"),
    meta: { pageTitle: "マスタメンテ", resource: "masters" },
  },
  {
    path: "/masters/product",
    name: "ProductMaster",
    component: () => import("@/views/masters/ProductMaster.vue"),
    meta: { pageTitle: "製品マスタ", resource: "masters" },
  },
  {
    path: "/masters/product-group",
    name: "ProductGroupMaster",
    component: () => import("@/views/masters/ProductGroupMaster.vue"),
    meta: { pageTitle: "製品グループマスタ", resource: "masters" },
  },
  {
    path: "/masters/container-capacity",
    name: "ContainerCapacityMaster",
    component: () => import("@/views/masters/ContainerCapacityMaster.vue"),
    meta: { pageTitle: "容器マスタ", resource: "masters" },
  },
  {
    path: "/masters/equipment",
    name: "EquipmentMaster",
    component: () => import("@/views/masters/EquipmentMaster.vue"),
    meta: { pageTitle: "設備マスタ", resource: "masters" },
  },
  {
    path: "/masters/customer",
    name: "CustomerMaster",
    component: () => import("@/views/masters/CustomerMaster.vue"),
    meta: { pageTitle: "得意先マスタ", resource: "masters" },
  },
  {
    path: "/masters/supplier",
    name: "SupplierMaster",
    component: () => import("@/views/masters/SupplierMaster.vue"),
    meta: { pageTitle: "仕入先マスタ", resource: "masters" },
  },
  {
    path: "/masters/process",
    name: "ProcessMaster",
    component: () => import("@/views/masters/ProcessMaster.vue"),
    meta: { pageTitle: "工程マスタ", resource: "masters" },
  },
  {
    path: "/masters/line",
    name: "LineMaster",
    component: () => import("@/views/masters/LineMaster.vue"),
    meta: { pageTitle: "ラインマスタ", resource: "masters" },
  },
  {
    path: "/masters/calendar",
    name: "CalendarMaster",
    component: () => import("@/views/masters/CalendarMaster.vue"),
    meta: { pageTitle: "カレンダマスタ", resource: "masters" },
  },
  {
    path: "/masters/work-pattern",
    name: "WorkPatternMaster",
    component: () => import("@/views/masters/WorkPatternMaster.vue"),
    meta: { pageTitle: "勤務パターンマスタ", resource: "masters" },
  },
  {
    path: "/masters/bom",
    name: "BOMMaster",
    component: () => import("@/views/masters/BOMMaster.vue"),
    meta: { pageTitle: "構成マスタ（BOM）", resource: "masters" },
  },
  {
    path: "/masters/routing",
    name: "RoutingMaster",
    component: () => import("@/views/masters/RoutingMaster.vue"),
    meta: { pageTitle: "ルーティングマスタ", resource: "masters" },
  },
  {
    path: "/masters/contact",
    name: "ContactMaster",
    component: () => import("@/views/masters/ContactMaster.vue"),
    meta: { pageTitle: "連絡先マスタ", resource: "masters" },
  },
];

export default masters;
