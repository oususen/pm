<template>
  <div class="app-root" :class="{ 'dev-env': isDev }">
    <!-- 開発環境バナー -->
    <div v-if="isDev" class="dev-banner">開発環境</div>
    <!-- グローバルナビゲーション -->
    <GlobalNavigation v-if="showLayout" :is-mobile="isMobile" :today-text="todayText" />

    <div class="app-body">
      <main class="app-main">
        <RouterView />
      </main>
    </div>

    <footer v-if="showLayout" class="app-footer">
      <span>ダイウン工業株式会社 / 王 崇栓</span>
      <span>データベース: mysql</span>
      <button class="logout-btn" @click="handleLogout">F12: ログアウト</button>
    </footer>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from "vue";
import { RouterView, useRoute, useRouter } from "vue-router";
import GlobalNavigation from "./components/GlobalNavigation.vue";
import { logout } from "./auth";

const todayText = computed(() => {
  const d = new Date();
  const youbi = ["日", "月", "火", "水", "木", "金", "土"][d.getDay()];
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日（${youbi}曜日）`;
});

const isMobile = ref(false);
let mediaQuery = null;

const route = useRoute();
const router = useRouter();

const showLayout = computed(() => !route.meta?.hideLayout);

// 開発環境かどうか判定（本番IP以外は全て開発環境）
const isDev = computed(() => {
  const host = window.location.hostname;
  return host !== '10.0.1.232';
});

const syncMobileState = () => {
  if (!mediaQuery) return;
  isMobile.value = mediaQuery.matches;
};

const handleLogout = async () => {
  await logout();
  router.replace("/login");
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
</style>
