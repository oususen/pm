const shipping = [
  {
    path: "/shipping/menu",
    name: "ShippingMenu",
    component: () => import("@/views/shipping/ShippingMenu.vue"),
    meta: { pageTitle: "出荷管理メニュー", manualPath: "README.md" },
  },
  {
    path: "/shipping/instruction",
    name: "ShippingInstruction",
    component: () => import("@/views/shipping/ShippingInstruction.vue"),
    meta: { pageTitle: "出荷指示", manualPath: "出荷/出荷指示.md" },
  },
  {
    path: "/shipping/actual",
    name: "ShippingActual",
    component: () => import("@/views/shipping/ShippingActual.vue"),
    meta: { pageTitle: "出荷実績", manualPath: "出荷/出荷実績.md" },
  },
  {
    path: "/shipping/progress",
    name: "ShippingProgress",
    component: () => import("@/views/shipping/ShippingProgress.vue"),
    meta: { pageTitle: "出荷進度照会", manualPath: "出荷/出荷進度照会.md" },
  },
  {
    path: "/shipping/order-document",
    name: "ShippingOrderDocument",
    component: () => import("@/views/shipping/ShippingOrderDocument.vue"),
    meta: { pageTitle: "出荷指示書", manualPath: "出荷/出荷指示書.md" },
  },
];

export default shipping;
