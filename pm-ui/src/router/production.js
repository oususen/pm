const production = [
  {
    path: "/production/menu",
    name: "ProductionMenu",
    component: () => import("@/views/production/ProductionMenu.vue"),
  },
  {
    path: "/production/line-demands",
    name: "LineDemandList",
    component: () => import("@/views/production/LineDemandList.vue"),
  },
  {
    path: "/production/line-calendars",
    name: "LineCalendar",
    component: () => import("@/views/production/LineCalendar.vue"),
  },
  {
    path: "/production/progress",
    name: "ProductionProgress",
    component: () => import("@/views/production/ProductionProgress.vue"),
  },
  {
    path: "/production/plan-input",
    name: "ProductionPlanInput",
    component: () => import("@/views/production/ProductionPlanInput.vue"),
  },
  {
    path: "/production/inventory",
    name: "ProductionInventory",
    component: () => import("@/views/production/ProductionInventory.vue"),
  },
  {
    path: "/production/stock-allocations",
    name: "StockAllocationList",
    component: () => import("@/views/production/StockAllocationList.vue"),
  },
  {
    path: "/production/stock-allocations/new",
    name: "StockAllocationCreate",
    component: () => import("@/views/production/StockAllocationForm.vue"),
  },
  {
    path: "/production/stock-allocations/:id/edit",
    name: "StockAllocationEdit",
    component: () => import("@/views/production/StockAllocationForm.vue"),
    props: true,
  },
  {
    path: "/production/orders",
    name: "ProductionOrderList",
    component: () => import("@/views/production/ProductionOrderList.vue"),
  },
  {
    path: "/production/orders/new",
    name: "ProductionOrderCreate",
    component: () => import("@/views/production/ProductionOrderForm.vue"),
  },
  {
    path: "/production/orders/:id/edit",
    name: "ProductionOrderEdit",
    component: () => import("@/views/production/ProductionOrderForm.vue"),
    props: true,
  },
  {
    path: "/production/orders/:id/actuals",
    name: "ProcessActualEntry",
    component: () => import("@/views/production/ProcessActualEntry.vue"),
    props: true,
  },
  {
    path: "/production/sequence-board",
    name: "ProductionSequenceBoard",
    component: () => import("@/views/production/ProductionSequenceBoard.vue"),
  },
];

export default production;
