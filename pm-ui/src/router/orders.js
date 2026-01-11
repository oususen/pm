const orders = [
  {
    path: "/orders/menu",
    name: "OrderMenu",
    component: () => import("@/views/orders/OrderMenu.vue"),
    meta: { pageTitle: "受注管理メニュー", manualPath: "README.md" },
  },
  {
    path: "/orders",
    name: "OrderList",
    component: () => import("@/views/orders/OrderList.vue"),
    meta: { pageTitle: "受注一覧", manualPath: "受注/受注一覧.md" },
  },
  {
    path: "/csv-upload",
    name: "CSVUpload",
    component: () => import("@/views/orders/CSVUpload.vue"),
    meta: { pageTitle: "CSV Upload", manualPath: "受注/受注取込.md" },
  },
];

export default orders;
