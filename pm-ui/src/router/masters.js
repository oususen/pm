const masters = [
  {
    path: "/masters",
    name: "MasterMenu",
    component: () => import("@/views/masters/MasterMenu.vue"),
  },
  {
    path: "/masters/product",
    name: "ProductMaster",
    component: () => import("@/views/masters/ProductMaster.vue"),
  },
  {
    path: "/masters/customer",
    name: "CustomerMaster",
    component: () => import("@/views/masters/CustomerMaster.vue"),
  },
  {
    path: "/masters/supplier",
    name: "SupplierMaster",
    component: () => import("@/views/masters/SupplierMaster.vue"),
  },
  {
    path: "/masters/process",
    name: "ProcessMaster",
    component: () => import("@/views/masters/ProcessMaster.vue"),
  },
  {
    path: "/masters/line",
    name: "LineMaster",
    component: () => import("@/views/masters/LineMaster.vue"),
  },
  {
    path: "/masters/calendar",
    name: "CalendarMaster",
    component: () => import("@/views/masters/CalendarMaster.vue"),
  },
  {
    path: "/masters/bom",
    name: "BOMMaster",
    component: () => import("@/views/masters/BOMMaster.vue"),
  },
];

export default masters;
