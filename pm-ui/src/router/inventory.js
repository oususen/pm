const inventory = [
  {
    path: "/inventory",
    name: "InventoryMenu",
    component: () => import("@/views/inventory/InventoryMenu.vue"),
    meta: { pageTitle: "在庫管理" },
  },
];

export default inventory;
