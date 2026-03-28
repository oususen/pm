const inventory = [
  {
    path: "/inventory",
    name: "InventoryMenu",
    component: () => import("@/views/inventory/InventoryMenu.vue"),
    meta: { pageTitle: "在庫管理", resource: "inventory" },
  },
  {
    path: "/inventory/adjustments",
    name: "InventoryAdjustmentMenu",
    component: () => import("@/views/inventory/InventoryAdjustmentMenu.vue"),
    meta: { pageTitle: "在庫調整メニュー", resource: "inventory" },
  },
  {
    path: "/inventory/adjustments/progress",
    name: "InventoryProgressAdjustment",
    component: () => import("@/views/inventory/adjustments/ProgressAdjustment.vue"),
    meta: { pageTitle: "進度調整", resource: "inventory" },
  },
  {
    path: "/inventory/adjustments/stock",
    name: "InventoryStockAdjustment",
    component: () => import("@/views/inventory/adjustments/StockAdjustment.vue"),
    meta: { pageTitle: "在庫調整", resource: "inventory" },
  },
  {
    path: "/inventory/adjustments/history",
    name: "InventoryAdjustmentHistory",
    component: () => import("@/views/inventory/adjustments/AdjustmentHistory.vue"),
    meta: { pageTitle: "調整履歴", resource: "inventory" },
  },
];

export default inventory;
