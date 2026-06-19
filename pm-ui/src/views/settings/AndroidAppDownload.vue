<template>
  <div class="app-download-page">
    <div class="hero-card">
      <div class="hero-copy">
        <p class="eyebrow">Android社内配布</p>
        <h1 class="page-title">Androidアプリ配布</h1>
        <p class="lead">
          社内向けの Android アプリをここから配布します。PWA より待機時通知に強い運用を目指す場合の配布窓口です。
        </p>
        <div class="hero-actions">
          <a
            :href="downloadUrl"
            class="primary-btn"
            :class="{ disabled: !hasDownloadUrl }"
            :download="suggestedFilename"
            @click.prevent="handleDownload"
          >
            APKをダウンロード
          </a>
          <button type="button" class="secondary-btn" @click="copyDownloadUrl">
            URLをコピー
          </button>
        </div>
        <p v-if="message" class="message" :class="{ error: messageType === 'error' }">{{ message }}</p>
      </div>

      <div class="meta-card">
        <div class="meta-row">
          <span class="meta-label">対象端末</span>
          <span class="meta-value">Android</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">配布版</span>
          <span class="meta-value">{{ releaseLabel }}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">配布URL</span>
          <span class="meta-value meta-url">{{ displayDownloadUrl }}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">形式</span>
          <span class="meta-value">APK 直接配布</span>
        </div>
      </div>
    </div>

    <div class="content-grid">
      <section class="panel">
        <h2>インストール手順</h2>
        <ol class="steps">
          <li>この画面の「APKをダウンロード」を押します。</li>
          <li>ダウンロード完了後、通知またはファイル管理から APK を開きます。</li>
          <li>初回のみ「この提供元を許可」を有効化してインストールします。</li>
          <li>インストール後、ホーム画面のアプリアイコンから起動します。</li>
        </ol>
      </section>

      <section class="panel">
        <h2>運用メモ</h2>
        <ul class="notes">
          <li>APK本体は `VITE_ANDROID_APP_DOWNLOAD_URL` で差し替えできます。</li>
          <li>未設定時は `/downloads/app-debug.apk` を参照します。</li>
          <li>社内配布ページなので Google Play 公開は不要です。</li>
          <li>更新時は APK 差し替え後、この画面の案内文だけで再配布できます。</li>
        </ul>
      </section>

      <section class="panel qr-panel">
        <h2>QRコード</h2>
        <div v-if="qrCodeDataUrl" class="qr-frame">
          <img :src="qrCodeDataUrl" alt="APKダウンロードQRコード" class="qr-image" />
        </div>
        <p class="qr-caption">スマホでこの QR を読み取ると配布URLを開けます。</p>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import QRCode from "qrcode";

const configuredDownloadUrl = (import.meta.env.VITE_ANDROID_APP_DOWNLOAD_URL || "").trim();
const configuredReleaseLabel = (import.meta.env.VITE_ANDROID_APP_RELEASE_LABEL || "").trim();
const defaultDownloadPath = "/downloads/app-debug.apk";

const qrCodeDataUrl = ref("");
const message = ref("");
const messageType = ref("info");

const hasWindow = typeof window !== "undefined";

const downloadUrl = computed(() => {
  if (configuredDownloadUrl) return configuredDownloadUrl;
  if (!hasWindow) return defaultDownloadPath;
  return new URL(defaultDownloadPath, window.location.origin).toString();
});

const hasDownloadUrl = computed(() => Boolean(downloadUrl.value));
const releaseLabel = computed(() => configuredReleaseLabel || "latest");
const displayDownloadUrl = computed(() => configuredDownloadUrl || defaultDownloadPath);
const suggestedFilename = computed(() => {
  const normalized = releaseLabel.value.replace(/[^0-9A-Za-z._-]/g, "-");
  return normalized && normalized !== "latest" ? `app-debug-${normalized}.apk` : "app-debug.apk";
});

const buildQrCode = async () => {
  try {
    qrCodeDataUrl.value = await QRCode.toDataURL(downloadUrl.value, {
      width: 240,
      margin: 1,
      color: {
        dark: "#15304b",
        light: "#f8fbff",
      },
    });
  } catch (error) {
    console.error("QRコード生成に失敗しました", error);
  }
};

const setMessage = (text, type = "info") => {
  message.value = text;
  messageType.value = type;
};

const handleDownload = () => {
  if (!hasDownloadUrl.value) {
    setMessage("配布URLが未設定です。", "error");
    return;
  }
  window.location.href = downloadUrl.value;
};

const copyDownloadUrl = async () => {
  try {
    await navigator.clipboard.writeText(downloadUrl.value);
    setMessage("配布URLをコピーしました。");
  } catch (error) {
    console.error("配布URLのコピーに失敗しました", error);
    setMessage("URLのコピーに失敗しました。", "error");
  }
};

onMounted(buildQrCode);
</script>

<style scoped>
.app-download-page {
  min-height: 100%;
  padding: 18px;
  background:
    radial-gradient(circle at top left, rgba(248, 198, 77, 0.18), transparent 28%),
    linear-gradient(180deg, #f7f1cf 0%, #f2f6fa 100%);
}

.hero-card {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) minmax(280px, 0.9fr);
  gap: 18px;
  padding: 22px;
  border: 1px solid #d8e1ea;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 40px rgba(21, 48, 75, 0.08);
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #5e7c1c;
}

.page-title {
  margin: 0;
  font-size: 32px;
  line-height: 1.1;
  color: #15304b;
}

.lead {
  margin: 12px 0 0;
  max-width: 720px;
  font-size: 14px;
  line-height: 1.7;
  color: #44566c;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
}

.primary-btn,
.secondary-btn {
  min-height: 42px;
  padding: 0 18px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.primary-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  color: #fff;
  border: none;
  background: linear-gradient(135deg, #1f7a45 0%, #2d9a5d 100%);
  box-shadow: 0 10px 24px rgba(31, 122, 69, 0.24);
}

.secondary-btn {
  border: 1px solid #c8d4df;
  background: #fff;
  color: #15304b;
}

.primary-btn:hover,
.secondary-btn:hover {
  transform: translateY(-1px);
}

.primary-btn.disabled {
  opacity: 0.55;
  pointer-events: none;
}

.message {
  margin: 12px 0 0;
  font-size: 13px;
  color: #1f7a45;
}

.message.error {
  color: #c0362c;
}

.meta-card {
  display: grid;
  gap: 10px;
  padding: 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, #17324d 0%, #224869 100%);
  color: #f8fbff;
}

.meta-row {
  display: grid;
  gap: 4px;
}

.meta-label {
  font-size: 11px;
  opacity: 0.72;
}

.meta-value {
  font-size: 14px;
  font-weight: 700;
  word-break: break-word;
}

.meta-url {
  font-size: 12px;
  font-family: Consolas, monospace;
}

.content-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 18px;
}

.panel {
  padding: 18px;
  border: 1px solid #d8e1ea;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 14px 28px rgba(21, 48, 75, 0.05);
}

.panel h2 {
  margin: 0 0 12px;
  font-size: 16px;
  color: #15304b;
}

.steps,
.notes {
  margin: 0;
  padding-left: 18px;
  color: #44566c;
  font-size: 13px;
  line-height: 1.8;
}

.qr-panel {
  display: grid;
  align-content: start;
  justify-items: center;
}

.qr-frame {
  padding: 12px;
  border-radius: 16px;
  background: #f8fbff;
  border: 1px solid #d8e1ea;
}

.qr-image {
  display: block;
  width: 220px;
  max-width: 100%;
}

.qr-caption {
  margin: 10px 0 0;
  font-size: 12px;
  color: #5f6f82;
  text-align: center;
}

@media (max-width: 1100px) {
  .hero-card,
  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .app-download-page {
    padding: 12px;
  }

  .hero-card,
  .panel {
    padding: 16px;
    border-radius: 16px;
  }

  .page-title {
    font-size: 24px;
  }

  .hero-actions {
    flex-direction: column;
  }

  .primary-btn,
  .secondary-btn {
    width: 100%;
  }
}
</style>
