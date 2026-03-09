const orders = [
  {
    path: "/orders/menu",
    name: "OrderMenu",
    component: () => import("@/views/orders/OrderMenu.vue"),
    meta: { pageTitle: "受注管理メニュー", manualPath: "README.md", resource: "orders" },
  },
  {
    path: "/orders/kubota-naiji-analysis",
    name: "KubotaNaijiAnalysis",
    component: () => import("@/views/orders/KubotaNaijiAnalysis.vue"),
    meta: { pageTitle: "クボタ内示変化推移分析", manualPath: "受注/クボタ内示変化推移分析.md", resource: "orders" },
  },
  {
    path: "/orders",
    name: "OrderList",
    component: () => import("@/views/orders/OrderList.vue"),
    meta: { pageTitle: "受注一覧", manualPath: "受注/受注一覧.md", resource: "orders" },
  },
  {
    path: "/csv-upload",
    name: "CSVUpload",
    component: () => import("@/views/orders/CSVUpload.vue"),
    meta: { pageTitle: "CSV Upload", manualPath: "受注/受注取込.md", resource: "orders", permission: "edit" },
  },
];

export default orders;
