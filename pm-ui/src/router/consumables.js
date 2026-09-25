export default [
  {
    path: "/consumables",
    name: "ConsumableMenu",
    component: () => import("@/views/consumables/ConsumableMenu.vue"),
    meta: { pageTitle: "消耗品メニュー", resource: "consumables", allowChildResources: true },
  },
  {
    path: "/consumables/inventory",
    name: "ConsumableInventory",
    component: () => import("@/views/consumables/ConsumableInventory.vue"),
    meta: { pageTitle: "消耗品 在庫一覧", resource: "consumables.inventory" },
  },
  {
    path: "/consumables/operations",
    name: "ConsumableOperations",
    component: () => import("@/views/consumables/ConsumableOperations.vue"),
    meta: { pageTitle: "消耗品 入出庫", resource: "consumables.operations" },
  },
  {
    path: "/consumables/requests",
    name: "ConsumableRequests",
    component: () => import("@/views/consumables/ConsumableRequests.vue"),
    meta: { pageTitle: "消耗品 注文依頼", resource: "consumables.dispatch" },
  },
  {
    path: "/consumables/dispatch-orders",
    name: "ConsumableDispatchOrders",
    component: () => import("@/views/consumables/ConsumableDispatchOrders.vue"),
    meta: { pageTitle: "消耗品 注文書", resource: "consumables.dispatch" },
  },
  {
    path: "/consumables/history",
    name: "ConsumableHistory",
    component: () => import("@/views/consumables/ConsumableHistory.vue"),
    meta: { pageTitle: "消耗品 入出庫履歴", resource: "consumables.history" },
  },
  {
    path: "/consumables/masters",
    name: "ConsumableMasters",
    component: () => import("@/views/consumables/ConsumableMasters.vue"),
    meta: { pageTitle: "消耗品マスタ", resource: "consumables.masters" },
  },
];
