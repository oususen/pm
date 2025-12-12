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
import OrderMenu from "../pages/OrderMenu.vue";
import ProductionMenu from "../pages/ProductionMenu.vue";
import LineDemandList from "../pages/LineDemandList.vue";
import ProductionProgress from "../pages/ProductionProgress.vue";
import ProductionInventory from "../pages/ProductionInventory.vue";
import ProductionPlanInput from "../pages/ProductionPlanInput.vue";
import ShippingMenu from "../pages/ShippingMenu.vue";
import ShippingInstruction from "../pages/ShippingInstruction.vue";
import ShippingActual from "../pages/ShippingActual.vue";
import PurchaseMenu from "../pages/PurchaseMenu.vue";
import PurchasePlanInput from "../pages/PurchasePlanInput.vue";
import StockAllocationList from "../pages/StockAllocationList.vue";
import StockAllocationForm from "../pages/StockAllocationForm.vue";
import ProductionOrderList from "../pages/ProductionOrderList.vue";
import ProductionOrderForm from "../pages/ProductionOrderForm.vue";
import ProcessActualEntry from "../pages/ProcessActualEntry.vue";

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
  { path: "/orders/menu", name: "OrderMenu", component: OrderMenu },
  { path: "/orders", name: "OrderList", component: OrderList },
  { path: "/csv-upload", name: "CSVUpload", component: CSVUpload },
  { path: "/production/menu", name: "ProductionMenu", component: ProductionMenu },
  { path: "/production/line-demands", name: "LineDemandList", component: LineDemandList },
  { path: "/production/progress", name: "ProductionProgress", component: ProductionProgress },
  { path: "/production/plan-input", name: "ProductionPlanInput", component: ProductionPlanInput },
  { path: "/production/inventory", name: "ProductionInventory", component: ProductionInventory },
  { path: "/production/stock-allocations", name: "StockAllocationList", component: StockAllocationList },
  { path: "/production/stock-allocations/new", name: "StockAllocationCreate", component: StockAllocationForm },
  { path: "/production/stock-allocations/:id/edit", name: "StockAllocationEdit", component: StockAllocationForm, props: true },
  { path: "/production/orders", name: "ProductionOrderList", component: ProductionOrderList },
  { path: "/production/orders/new", name: "ProductionOrderCreate", component: ProductionOrderForm },
  { path: "/production/orders/:id/edit", name: "ProductionOrderEdit", component: ProductionOrderForm, props: true },
  { path: "/production/orders/:id/actuals", name: "ProcessActualEntry", component: ProcessActualEntry, props: true },
  { path: "/purchase/menu", name: "PurchaseMenu", component: PurchaseMenu },
  { path: "/purchase/plan-input", name: "PurchasePlanInput", component: PurchasePlanInput },
  { path: "/shipping/menu", name: "ShippingMenu", component: ShippingMenu },
  { path: "/shipping/instruction", name: "ShippingInstruction", component: ShippingInstruction },
  { path: "/shipping/actual", name: "ShippingActual", component: ShippingActual },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
