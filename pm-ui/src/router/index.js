import { createRouter, createWebHistory } from "vue-router";
import Dashboard from "../views/Dashboard.vue";
import masters from "./masters";
import orders from "./orders";
import production from "./production";
import purchase from "./purchase";
import shipping from "./shipping";
import inventory from "./inventory";
import quality from "./quality";
import manual from "./manual";
import settings from "./settings";
import Login from "../views/auth/Login.vue";
import { ensureAuth } from "../auth";

const root = [
  {
    path: "/",
    component: Dashboard,
    meta: { pageTitle: "ダッシュボード - DAISO管理システム" }
  }
];

const authRoutes = [
  {
    path: "/login",
    component: Login,
    meta: { pageTitle: "ログイン - DAISO管理システム", public: true, hideLayout: true },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes: [
    ...root,
    ...authRoutes,
    ...masters,
    ...orders,
    ...production,
    ...purchase,
    ...shipping,
    ...inventory,
    ...quality,
    ...settings,
    ...manual,
  ],
});

const DEFAULT_TITLE = "pm-ui";

const hasPermission = (user, resource, level = "view") => {
  if (!resource) return true;
  if (!user) return false;
  if (user.is_superuser) return true;
  const permissions = Array.isArray(user.effective_permissions)
    ? user.effective_permissions
    : [];
  const perm = permissions.find((item) => item.resource === resource);
  if (!perm) return false;
  if (level === "edit") return Boolean(perm.can_edit);
  return Boolean(perm.can_view || perm.can_edit);
};

router.afterEach((to) => {
  const pageTitle = to.meta?.pageTitle;
  document.title = pageTitle || DEFAULT_TITLE;
});

router.beforeEach(async (to) => {
  if (to.meta?.public) return true;

  const user = await ensureAuth();
  if (!user) {
    return { path: "/login", query: { next: to.fullPath } };
  }

  const resource = to.meta?.resource;
  const level = to.meta?.permission || "view";
  if (!hasPermission(user, resource, level)) {
    return { path: "/" };
  }

  return true;
});

export default router;
