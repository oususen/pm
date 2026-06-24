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
import notifications from "./notifications";
import engineeringChange from "./engineeringChange";
import tasks from "./tasks";
import overtime from "./overtime";
import outsource from "./outsource";
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
    ...notifications,
    ...engineeringChange,
    ...tasks,
    ...overtime,
    ...outsource,
    ...manual,
  ],
});

const DEFAULT_TITLE = "pm-ui";
const CHUNK_RELOAD_KEY = "pm-ui:chunk-reload";

export const hasPermission = (user, resource, level = "view") => {
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

const getExplicitPermission = (user, resource, level = "view") => {
  if (!resource || !user) return null;
  const permissions = Array.isArray(user.effective_permissions)
    ? user.effective_permissions
    : [];
  const perm = permissions.find((item) => item.resource === resource);
  if (!perm) return null;
  if (level === "edit") return Boolean(perm.can_edit);
  return Boolean(perm.can_view || perm.can_edit);
};

export const canAccessRouteResource = (
  user,
  resource,
  level = "view",
  fallbackResource = null,
  fallbackToParent = true,
) => {
  if (!resource) return true;
  if (!user) return false;
  if (user.is_superuser) return true;

  const explicit = getExplicitPermission(user, resource, level);
  if (explicit !== null) return explicit;

  if (fallbackResource) {
    const legacy = getExplicitPermission(user, fallbackResource, level);
    if (legacy !== null) return legacy;
  }

  if (!fallbackToParent) return false;

  const parentResource = String(resource).split(".")[0];
  if (parentResource && parentResource !== resource) {
    const parent = getExplicitPermission(user, parentResource, level);
    if (parent !== null) return parent;
  }

  return false;
};

router.afterEach((to) => {
  const pageTitle = to.meta?.pageTitle;
  document.title = pageTitle || DEFAULT_TITLE;
});

router.onError((error, to) => {
  const message = String(error?.message || "");
  const isChunkLoadError =
    message.includes("Failed to fetch dynamically imported module") ||
    message.includes("Importing a module script failed") ||
    message.includes("Loading chunk") ||
    message.includes("ChunkLoadError");

  if (!isChunkLoadError) {
    console.error("router error:", error);
    return;
  }

  const targetPath = to?.fullPath || window.location.pathname || "/";
  const reloadedPath = sessionStorage.getItem(CHUNK_RELOAD_KEY);
  if (reloadedPath === targetPath) {
    sessionStorage.removeItem(CHUNK_RELOAD_KEY);
    console.error("chunk reload failed after retry:", error);
    return;
  }

  // デプロイ直後の古いchunk参照を1回だけ自動復旧する
  sessionStorage.setItem(CHUNK_RELOAD_KEY, targetPath);
  window.location.assign(targetPath);
});

router.beforeEach(async (to) => {
  if (to.meta?.public) return true;

  const user = await ensureAuth();
  if (!user) {
    return { path: "/login", query: { next: to.fullPath } };
  }

  const resource = to.meta?.resource;
  const level = to.meta?.permission || "view";
  const fallbackResource = to.meta?.fallbackResource || null;
  const fallbackToParent = to.meta?.fallbackToParent !== false;
  if (!canAccessRouteResource(user, resource, level, fallbackResource, fallbackToParent)) {
    return { path: "/" };
  }

  return true;
});

export default router;
