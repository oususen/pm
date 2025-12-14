const shipping = [
  {
    path: "/shipping/menu",
    name: "ShippingMenu",
    component: () => import("@/views/shipping/ShippingMenu.vue"),
  },
  {
    path: "/shipping/instruction",
    name: "ShippingInstruction",
    component: () => import("@/views/shipping/ShippingInstruction.vue"),
  },
  {
    path: "/shipping/actual",
    name: "ShippingActual",
    component: () => import("@/views/shipping/ShippingActual.vue"),
  },
];

export default shipping;
