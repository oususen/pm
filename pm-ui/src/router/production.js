const production = [
  {
    path: "/production/menu",
    name: "ProductionMenu",
    component: () => import("@/views/production/ProductionMenu.vue"),
    meta: { pageTitle: "生産管理メニュー" },
  },
  {
    path: "/production/line-demands",
    name: "LineDemandList",
    component: () => import("@/views/production/LineDemandList.vue"),
    meta: { pageTitle: "ライン需要一覧" },
  },
  {
    path: "/production/line-calendars",
    name: "LineCalendar",
    component: () => import("@/views/production/LineCalendar.vue"),
    meta: { pageTitle: "ライン勤務カレンダ" },
  },
  {
    path: "/production/progress",
    name: "ProductionProgress",
    component: () => import("@/views/production/ProductionProgress.vue"),
    meta: { pageTitle: "進捗管理" },
  },
  {
    path: "/production/plan-input",
    name: "ProductionPlanInput",
    component: () => import("@/views/production/ProductionPlanInput.vue"),
    meta: { pageTitle: "生産計画入力" },
  },
  {
    path: "/production/inventory",
    name: "ProductionInventory",
    component: () => import("@/views/production/ProductionInventory.vue"),
    meta: { pageTitle: "在庫 / 残量一覧" },
  },
  {
    path: "/production/stock-allocations",
    name: "StockAllocationList",
    component: () => import("@/views/production/StockAllocationList.vue"),
    meta: { pageTitle: "在庫引当一覧" },
  },
  {
    path: "/production/stock-allocations/new",
    name: "StockAllocationCreate",
    component: () => import("@/views/production/StockAllocationForm.vue"),
    meta: { pageTitle: "在庫引当 新規登録" },
  },
  {
    path: "/production/stock-allocations/:id/edit",
    name: "StockAllocationEdit",
    component: () => import("@/views/production/StockAllocationForm.vue"),
    props: true,
    meta: { pageTitle: "在庫引当 編集" },
  },
  {
    path: "/production/orders",
    name: "ProductionOrderList",
    component: () => import("@/views/production/ProductionOrderList.vue"),
    meta: { pageTitle: "製造指示一覧" },
  },
  {
    path: "/production/orders/new",
    name: "ProductionOrderCreate",
    component: () => import("@/views/production/ProductionOrderForm.vue"),
    meta: { pageTitle: "製造指示 新規登録" },
  },
  {
    path: "/production/orders/:id/edit",
    name: "ProductionOrderEdit",
    component: () => import("@/views/production/ProductionOrderForm.vue"),
    props: true,
    meta: { pageTitle: "製造指示 編集" },
  },
  {
    path: "/production/orders/:id/actuals",
    name: "ProcessActualEntry",
    component: () => import("@/views/production/ProcessActualEntry.vue"),
    props: true,
    meta: { pageTitle: "工程実績入力" },
  },
  {
    path: "/production/sequence-board",
    name: "ProductionSequenceBoard",
    component: () => import("@/views/production/ProductionSequenceBoard.vue"),
    meta: { pageTitle: "日次ミックス順序ボード（7品固定運転向け）" },
  },
  {
    path: "/production/line-monitor",
    name: "LineRealtimeMonitor",
    component: () => import("@/views/production/LineRealtimeMonitor.vue"),
    meta: { pageTitle: "ライン稼働監視" },
  },
  {
    path: "/production/mobile-input",
    name: "MobileLineInput",
    component: () => import("@/views/production/MobileLineInput.vue"),
    meta: { pageTitle: "ライン作業記録" },
  },
  {
    path: "/production/mobile-process-input",
    name: "MobileProcessInput",
    component: () => import("@/views/production/MobileProcessInput.vue"),
    meta: {
      pageTitle: "工程作業記録",
      allowedRecordTypes: ["PRODUCTION", "EQUIPMENT_STATE"],
    },
  },
  {
    path: "/production/scrap-record",
    name: "ScrapRecordInput",
    component: () => import("@/views/production/MobileProcessInput.vue"),
    meta: {
      pageTitle: "仕損品記録",
      allowedRecordTypes: ["SCRAP"],
    },
  },
  {
    path: "/production/process-gantt",
    name: "ProcessGanttView",
    component: () => import("@/views/production/ProcessGanttView.vue"),
    meta: { pageTitle: "工程ガント" },
  },
  {
    path: "/production/scrap-history",
    name: "ScrapHistory",
    component: () => import("@/views/production/ScrapHistory.vue"),
    meta: { pageTitle: "仕損履歴" },
  },
];

export default production;
