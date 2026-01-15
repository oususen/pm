const purchase = [
  {
    path: "/purchase/menu",
    name: "PurchaseMenu",
    component: () => import("@/views/purchase/PurchaseMenu.vue"),
    meta: { pageTitle: "仕入れ管理メニュー", resource: "purchase" },
  },
  {
    path: "/purchase/plan-input",
    name: "PurchasePlanInput",
    component: () => import("@/views/purchase/PurchasePlanInput.vue"),
    meta: { pageTitle: "仕入れ計画", resource: "purchase" },
  },
  {
    path: "/purchase/inventory",
    name: "PurchaseInventory",
    component: () => import("@/views/inventory/PurchaseInventory.vue"),
    meta: { pageTitle: "仕入れ在庫/残量", resource: "purchase" },
  },
];

export default purchase;
