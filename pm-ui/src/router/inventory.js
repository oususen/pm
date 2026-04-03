const inventory = [
  {
    path: "/inventory",
    name: "InventoryMenu",
    component: () => import("@/views/inventory/InventoryMenu.vue"),
    meta: { pageTitle: "在庫管理", manualPath: "在庫/在庫管理メニュー.md", resource: "inventory" },
  },
  {
    path: "/inventory/adjustments",
    name: "InventoryAdjustmentMenu",
    component: () => import("@/views/inventory/InventoryAdjustmentMenu.vue"),
    meta: { pageTitle: "在庫調整メニュー", manualPath: "在庫/在庫調整メニュー.md", resource: "inventory" },
  },
  {
    path: "/inventory/adjustments/progress",
    name: "InventoryProgressAdjustment",
    component: () => import("@/views/inventory/adjustments/ProgressAdjustment.vue"),
    meta: { pageTitle: "進度調整", manualPath: "在庫/進度調整.md", resource: "inventory" },
  },
  {
    path: "/inventory/adjustments/stock",
    name: "InventoryStockAdjustment",
    component: () => import("@/views/inventory/adjustments/StockAdjustment.vue"),
    meta: { pageTitle: "在庫調整", manualPath: "在庫/在庫調整.md", resource: "inventory" },
  },
  {
    path: "/inventory/adjustments/history",
    name: "InventoryAdjustmentHistory",
    component: () => import("@/views/inventory/adjustments/AdjustmentHistory.vue"),
    meta: { pageTitle: "調整履歴", manualPath: "在庫/調整履歴.md", resource: "inventory" },
  },
  {
    path: "/inventory/actual-progress",
    name: "InventoryActualProgressCalculator",
    component: () => import("@/views/inventory/ActualProgressCalculator.vue"),
    meta: { pageTitle: "実進度求め", manualPath: "在庫/実進度求め.md", resource: "inventory" },
  },
];

export default inventory;
