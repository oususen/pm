const shipping = [
  {
    path: "/shipping/menu",
    name: "ShippingMenu",
    component: () => import("@/views/shipping/ShippingMenu.vue"),
    meta: { pageTitle: "出荷管理メニュー" },
  },
  {
    path: "/shipping/instruction",
    name: "ShippingInstruction",
    component: () => import("@/views/shipping/ShippingInstruction.vue"),
    meta: { pageTitle: "出荷指示" },
  },
  {
    path: "/shipping/actual",
    name: "ShippingActual",
    component: () => import("@/views/shipping/ShippingActual.vue"),
    meta: { pageTitle: "出荷実績" },
  },
  {
    path: "/shipping/progress",
    name: "ShippingProgress",
    component: () => import("@/views/shipping/ShippingProgress.vue"),
    meta: { pageTitle: "出荷進度照会" },
  },
  {
    path: "/shipping/order-document",
    name: "ShippingOrderDocument",
    component: () => import("@/views/shipping/ShippingOrderDocument.vue"),
    meta: { pageTitle: "出荷指示書" },
  },
];

export default shipping;
