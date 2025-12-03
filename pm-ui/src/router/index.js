import { createRouter, createWebHistory } from "vue-router";
import MasterMenu from "../pages/MasterMenu.vue";
import ProductMaster from "../pages/ProductMaster.vue";
import CustomerMaster from "../pages/CustomerMaster.vue";

const routes = [
  { path: "/", redirect: "/masters" },
  { path: "/masters", name: "MasterMenu", component: MasterMenu },
  { path: "/masters/product", name: "ProductMaster", component: ProductMaster },
  { path: "/masters/customer", name: "CustomerMaster", component: CustomerMaster },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
