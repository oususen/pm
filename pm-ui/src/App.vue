<template>
  <div class="app-root" :class="{ 'dev-env': isDev }">
    <!-- 開発環境バナー -->
    <div v-if="isDev && showLayout" class="dev-banner">開発環境</div>
    <!-- グローバルナビゲーション -->
    <GlobalNavigation v-if="showLayout" :is-mobile="isMobile" :today-text="todayText" />

    <div class="app-body">
      <main class="app-main">
        <RouterView />
      </main>
    </div>
    <AIChatDrawer v-if="showLayout" />
    <AIFloatingButton v-if="showLayout" />
    <RequestDialog v-if="showLayout" />
    <RequestHistoryDialog v-if="showLayout" />

  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from "vue";
import { RouterView, useRoute } from "vue-router";
import GlobalNavigation from "./components/GlobalNavigation.vue";
import AIChatDrawer from "./components/AIChatDrawer.vue";
import AIFloatingButton from "./components/AIFloatingButton.vue";
import RequestDialog from "./components/RequestDialog.vue";
import RequestHistoryDialog from "./components/RequestHistoryDialog.vue";
import { aiDrawerOpen, aiDrawerSourcePath } from "./composables/aiDrawer";

const todayText = computed(() => {
  const d = new Date();
  const youbi = ["日", "月", "火", "水", "木", "金", "土"][d.getDay()];
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日（${youbi}曜日）`;
});

const isMobile = ref(false);
let mediaQuery = null;

const route = useRoute();
const showLayout = computed(() => !route.meta?.hideLayout && route.query.embed !== 'tablet');

// ドロワーを開いたまま画面遷移した場合も、AIの起点画面を現在の画面に合わせる。
watch(() => route.fullPath, (path) => {
  if (aiDrawerOpen.value) aiDrawerSourcePath.value = path;
});

// 開発環境かどうか判定（本番IP以外は全て開発環境）
const isDev = computed(() => {
  const host = window.location.hostname;
  return host !== '10.0.1.232';
});

const syncMobileState = () => {
  if (!mediaQuery) return;
  isMobile.value = mediaQuery.matches;
};

onMounted(() => {
  mediaQuery = window.matchMedia("(max-width: 768px)");
  syncMobileState();
  mediaQuery.addEventListener("change", syncMobileState);
});

onBeforeUnmount(() => {
  if (mediaQuery) {
    mediaQuery.removeEventListener("change", syncMobileState);
  }
});
</script>

<style>
/* 開発環境の背景色 */
.dev-env,
.dev-env .app-body,
.dev-env .app-main {
  background-color: #fffde7 !important; /* 薄い黄色 */
}

.dev-env {
  min-height: 100vh;
}

/* 開発環境バナー */
.dev-banner {
  background-color: #ff9800;
  color: white;
  text-align: center;
  padding: 4px 0;
  font-weight: bold;
  font-size: 14px;
  position: sticky;
  top: 0;
  z-index: 9999;
}

@media print {
  .dev-banner,
  .global-nav {
    display: none !important;
  }

  .app-root,
  .app-body,
  .app-main {
    display: block !important;
    height: auto !important;
    min-height: 0 !important;
    overflow: visible !important;
    background: #fff !important;
  }
}
</style>
