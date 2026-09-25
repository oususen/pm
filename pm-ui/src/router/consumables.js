export default [
  {
    path: "/consumables",
    name: "ConsumableMenu",
    component: () => import("@/views/consumables/ConsumableMenu.vue"),
    meta: { pageTitle: "消耗品メニュー", manualPath: "消耗品/消耗品メニュー.md", resource: "consumables", allowChildResources: true },
  },
  {
    path: "/consumables/inventory",
    name: "ConsumableInventory",
    component: () => import("@/views/consumables/ConsumableInventory.vue"),
    meta: { pageTitle: "消耗品 在庫一覧", manualPath: "消耗品/在庫一覧.md", resource: "consumables.inventory" },
  },
  {
    path: "/consumables/operations",
    name: "ConsumableOperations",
    component: () => import("@/views/consumables/ConsumableOperations.vue"),
    meta: { pageTitle: "消耗品 入出庫", manualPath: "消耗品/入出庫.md", resource: "consumables.operations" },
  },
  {
    path: "/consumables/requests",
    name: "ConsumableRequests",
    component: () => import("@/views/consumables/ConsumableRequests.vue"),
    meta: { pageTitle: "消耗品 注文依頼", manualPath: "消耗品/注文依頼.md", resource: "consumables.dispatch" },
  },
  {
    path: "/consumables/dispatch-orders",
    name: "ConsumableDispatchOrders",
    component: () => import("@/views/consumables/ConsumableDispatchOrders.vue"),
    meta: { pageTitle: "消耗品 注文書", manualPath: "消耗品/注文書.md", resource: "consumables.dispatch" },
  },
  {
    path: "/consumables/history",
    name: "ConsumableHistory",
    component: () => import("@/views/consumables/ConsumableHistory.vue"),
    meta: { pageTitle: "消耗品 入出庫履歴", manualPath: "消耗品/入出庫履歴.md", resource: "consumables.history" },
  },
  {
    path: "/consumables/masters",
    name: "ConsumableMasters",
    component: () => import("@/views/consumables/ConsumableMasters.vue"),
    meta: { pageTitle: "消耗品マスタ", manualPath: "消耗品/消耗品マスタ.md", resource: "consumables.masters" },
  },
];
