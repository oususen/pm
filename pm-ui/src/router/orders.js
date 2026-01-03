const orders = [
  {
    path: "/orders/menu",
    name: "OrderMenu",
    component: () => import("@/views/orders/OrderMenu.vue"),
    meta: { pageTitle: "受注管理メニュー" },
  },
  {
    path: "/orders",
    name: "OrderList",
    component: () => import("@/views/orders/OrderList.vue"),
    meta: { pageTitle: "受注一覧" },
  },
  {
    path: "/csv-upload",
    name: "CSVUpload",
    component: () => import("@/views/orders/CSVUpload.vue"),
    meta: { pageTitle: "CSV Upload" },
  },
];

export default orders;
