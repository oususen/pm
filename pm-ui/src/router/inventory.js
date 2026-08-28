const inventory = [
  {
    path: "/inventory",
    name: "InventoryMenu",
    component: () => import("@/views/inventory/InventoryMenu.vue"),
    meta: {
      pageTitle: "在庫管理",
      manualPath: "在庫/在庫管理メニュー.md",
      resource: "inventory",
      allowChildResources: true,
    },
  },
  {
    path: "/inventory/adjustments",
    name: "InventoryAdjustmentMenu",
    component: () => import("@/views/inventory/InventoryAdjustmentMenu.vue"),
    meta: { pageTitle: "在庫調整メニュー", manualPath: "在庫/在庫調整メニュー.md", resource: "inventory" },
  },
  {
    path: "/inventory/stocktake-input",
    name: "InventoryStocktakeInput",
    component: () => import("@/views/inventory/StocktakeInput.vue"),
    meta: {
      pageTitle: "棚卸現物入力",
      manualPath: "在庫/棚卸現物入力.md",
      resource: "stocktake",
      fallbackToParent: false,
    },
  },
  {
    path: "/inventory/stocktake-results",
    name: "InventoryStocktakeResults",
    component: () => import("@/views/inventory/StocktakeResults.vue"),
    meta: {
      pageTitle: "棚卸結果確認",
      resource: "stocktake",
      fallbackToParent: false,
    },
  },
  {
    path: "/inventory/stocktake-layout",
    name: "InventoryStocktakeLayout",
    component: () => import("@/views/inventory/StocktakeLayoutEditor.vue"),
    meta: {
      pageTitle: "棚卸レイアウト編集",
      manualPath: "在庫/棚卸レイアウト編集.md",
      resource: "stocktake.layout",
      fallbackToParent: false,
    },
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
    path: "/inventory/adjustments/planned-stock",
    name: "InventoryPlannedStockAdjustment",
    component: () => import("@/views/inventory/adjustments/PlannedStockAdjustment.vue"),
    meta: { pageTitle: "計画在庫調整", resource: "inventory" },
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
