const orders = [
  {
    path: "/orders/menu",
    name: "OrderMenu",
    component: () => import("@/views/orders/OrderMenu.vue"),
  },
  {
    path: "/orders",
    name: "OrderList",
    component: () => import("@/views/orders/OrderList.vue"),
  },
  {
    path: "/csv-upload",
    name: "CSVUpload",
    component: () => import("@/views/orders/CSVUpload.vue"),
  },
];

export default orders;
