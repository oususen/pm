import { createRouter, createWebHistory } from "vue-router";
import MasterMenu from "../pages/MasterMenu.vue";
import ProductMaster from "../pages/ProductMaster.vue";
import CalendarMaster from "../pages/CalendarMaster.vue";
import CustomerMaster from "../pages/CustomerMaster.vue";
import BomMaster from "../pages/BomMaster.vue";

const routes = [
  { path: "/", redirect: "/masters" },
  { path: "/masters", name: "MasterMenu", component: MasterMenu },
  { path: "/masters/product", name: "ProductMaster", component: ProductMaster },
  { path: "/masters/calendar", name: "CalendarMaster", component: CalendarMaster },
  { path: "/masters/customer", name: "CustomerMaster", component: CustomerMaster },
  { path: "/masters/bom", name: "BomMaster", component: BomMaster },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
