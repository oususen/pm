const purchase = [
  {
    path: "/purchase/menu",
    name: "PurchaseMenu",
    component: () => import("@/views/purchase/PurchaseMenu.vue"),
  },
  {
    path: "/purchase/plan-input",
    name: "PurchasePlanInput",
    component: () => import("@/views/purchase/PurchasePlanInput.vue"),
  },
];

export default purchase;
