import { createRouter, createWebHistory } from "vue-router";
import MasterMenu from "../pages/MasterMenu.vue";
import ProductMaster from "../pages/ProductMaster.vue";
import CustomerMaster from "../pages/CustomerMaster.vue";
import SupplierMaster from "../pages/SupplierMaster.vue";
import ProcessMaster from "../pages/ProcessMaster.vue";
import LineMaster from "../pages/LineMaster.vue";
import CalendarMaster from "../pages/CalendarMaster.vue";
import BOMMaster from "../pages/BOMMaster.vue";
import OrderList from "../pages/OrderList.vue";
import CSVUpload from "../pages/CSVUpload.vue";

const routes = [
  { path: "/", redirect: "/masters" },
  { path: "/masters", name: "MasterMenu", component: MasterMenu },
  { path: "/masters/product", name: "ProductMaster", component: ProductMaster },
  { path: "/masters/customer", name: "CustomerMaster", component: CustomerMaster },
  { path: "/masters/supplier", name: "SupplierMaster", component: SupplierMaster },
  { path: "/masters/process", name: "ProcessMaster", component: ProcessMaster },
  { path: "/masters/line", name: "LineMaster", component: LineMaster },
  { path: "/masters/calendar", name: "CalendarMaster", component: CalendarMaster },
  { path: "/masters/bom", name: "BOMMaster", component: BOMMaster },
  { path: "/orders", name: "OrderList", component: OrderList },
  { path: "/csv-upload", name: "CSVUpload", component: CSVUpload },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
