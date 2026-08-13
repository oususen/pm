<template>
  <div v-if="isReady" class="recording-list-page">
    <h2 class="page-title">通話録音一覧</h2>
    <div class="list-card">
      <div class="list-header">
        <div class="list-note">保存済みの通話録音を確認します。</div>
        <div class="header-actions">
          <button class="btn secondary-btn" type="button" @click="reload" :disabled="loading">
            再読込
          </button>
          <button class="btn link-btn" type="button" @click="goCallCenter">
            通話画面
          </button>
          <button class="btn link-btn" type="button" @click="goNotificationList">
            通知一覧
          </button>
        </div>
      </div>

      <div class="filter-row">
        <label class="filter-field">
          <span>発信者名</span>
          <input v-model.trim="callerKeyword" type="text" class="text-input" placeholder="発信者名で検索" />
        </label>
        <label class="filter-field">
          <span>着信者名</span>
          <input v-model.trim="calleeKeyword" type="text" class="text-input" placeholder="着信者名で検索" />
        </label>
        <label class="filter-field">
          <span>録音登録者名</span>
          <input v-model.trim="recordedByKeyword" type="text" class="text-input" placeholder="録音登録者名で検索" />
        </label>
        <label class="filter-field">
          <span>通話種別</span>
          <select v-model="callTypeFilter" class="select-input">
            <option value="">初期値無し</option>
            <option value="voice">音声通話</option>
            <option value="video">ビデオ通話</option>
          </select>
        </label>
      </div>

      <div class="summary-row">
        <span v-if="hasLoaded">件数: {{ filteredSessions.length }} / {{ recordedSessions.length }}</span>
        <span v-else>初期表示では録音データを表示しません。必要時に再読込してください。</span>
      </div>

      <table class="recording-table">
        <thead>
          <tr>
            <th>通話日時</th>
            <th>発信者</th>
            <th>着信者</th>
            <th>通話種別</th>
            <th>状態</th>
            <th>録音時間</th>
            <th>ファイルサイズ</th>
            <th>録音登録者</th>
            <th>再生</th>
            <th>文字起こし</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="session in filteredSessions" :key="session.id">
            <tr class="recording-row" @click="toggleTranscript(session.id)">
              <td>{{ formatDateTime(session.initiated_at) }}</td>
              <td>{{ session.caller_name || "-" }}</td>
              <td>{{ session.callee_name || "-" }}</td>
              <td>{{ session.call_type === "video" ? "ビデオ通話" : "音声通話" }}</td>
              <td>{{ statusLabel(session.status) }}</td>
              <td>{{ formatDuration(session.recording?.duration_seconds) }}</td>
              <td>{{ formatFileSize(session.recording?.file_size) }}</td>
              <td>{{ session.recording?.recorded_by_name || "-" }}</td>
              <td class="audio-cell" @click.stop>
                <audio
                  v-if="session.recording?.file_url"
                  controls
                  preload="metadata"
                  :src="session.recording.file_url"
                ></audio>
                <span v-else>-</span>
              </td>
              <td class="transcribe-cell" @click.stop>
                <button
                  v-if="session.recording?.file_url"
                  class="btn transcribe-btn"
                  :disabled="anyTranscribing"
                  @click="triggerTranscribe(session)"
                >
                  {{ session.recording?.transcript_status === 'processing' ? '処理中' : '実行' }}
                </button>
                <span v-else>-</span>
              </td>
            </tr>
            <tr v-if="expandedSessionId === session.id" class="transcript-row">
              <td colspan="10">
                <div class="transcript-box">
                  <div class="transcript-header">
                    <span class="transcript-label">文字起こし</span>
                    <span v-if="session.recording?.transcript_language" class="transcript-lang">
                      言語: {{ session.recording.transcript_language }}
                    </span>
                  </div>
                  <div v-if="session.recording?.transcript_status === 'pending'" class="transcript-status">
                    処理待ち...
                  </div>
                  <div v-else-if="session.recording?.transcript_status === 'processing'" class="transcript-status">
                    文字起こし中...
                  </div>
                  <div v-else-if="session.recording?.transcript_status === 'failed'" class="transcript-status error">
                    文字起こしに失敗しました
                  </div>
                  <div v-else-if="session.recording?.transcript" class="transcript-text">
                    {{ session.recording.transcript }}
                  </div>
                  <div v-else class="transcript-status">
                    文字起こしデータがありません
                  </div>
                </div>
              </td>
            </tr>
          </template>
          <tr v-if="!hasLoaded">
            <td colspan="10" class="empty">再読込を押すまで録音データは表示しません。</td>
          </tr>
          <tr v-else-if="!filteredSessions.length">
            <td colspan="10" class="empty">録音データはありません。</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { authState } from "@/auth";
import api from "@/api/client";
import { CALL_RECORDING_ALLOWED_USERS_KEY, parseAllowedRecordingUsernames } from "@/utils/callRecordingAccess";

const router = useRouter();
const recordingAllowedUsers = ref([]);

const loading = ref(false);
const sessions = ref([]);
const callerKeyword = ref("");
const calleeKeyword = ref("");
const recordedByKeyword = ref("");
const callTypeFilter = ref("");
const hasLoaded = ref(false);
const isReady = ref(false);
const expandedSessionId = ref(null);
const isTranscribing = ref(false);

const anyTranscribing = computed(() => {
  return isTranscribing.value || recordedSessions.value.some(s => s.recording?.transcript_status === 'processing');
});

const canUseRecordingFeatures = computed(() => {
  const username = String(authState.user?.username || "").toLowerCase();
  return recordingAllowedUsers.value.includes(username);
});

const recordedSessions = computed(() => {
  return sessions.value.filter((session) => session?.has_recording && session?.recording?.file_url);
});

const filteredSessions = computed(() => {
  const normalizedCaller = callerKeyword.value.toLowerCase();
  const normalizedCallee = calleeKeyword.value.toLowerCase();
  const normalizedRecordedBy = recordedByKeyword.value.toLowerCase();
  return recordedSessions.value.filter((session) => {
    if (callTypeFilter.value && session.call_type !== callTypeFilter.value) return false;
    if (normalizedCaller && !String(session.caller_name || "").toLowerCase().includes(normalizedCaller)) return false;
    if (normalizedCallee && !String(session.callee_name || "").toLowerCase().includes(normalizedCallee)) return false;
    if (normalizedRecordedBy && !String(session.recording?.recorded_by_name || "").toLowerCase().includes(normalizedRecordedBy)) return false;
    return true;
  });
});

const statusLabel = (status) => {
  const labels = {
    ringing: "呼出中",
    accepted: "通話中",
    declined: "辞退",
    ended: "終了",
    missed: "不在",
    canceled: "キャンセル",
  };
  return labels[status] || status;
};

const formatDateTime = (value) => {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "-";
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${y}-${m}-${day} ${hh}:${mm}`;
};

const formatDuration = (seconds) => {
  if (seconds == null || Number.isNaN(Number(seconds))) return "-";
  const total = Math.max(Math.round(Number(seconds)), 0);
  const mm = String(Math.floor(total / 60)).padStart(2, "0");
  const ss = String(total % 60).padStart(2, "0");
  return `${mm}:${ss}`;
};

const formatFileSize = (bytes) => {
  const size = Number(bytes || 0);
  if (!size) return "-";
  if (size >= 1024 * 1024) {
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }
  if (size >= 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${size} B`;
};

const loadSessions = async () => {
  if (!canUseRecordingFeatures.value) {
    sessions.value = [];
    return;
  }
  const res = await api.notifications.listCallSessions({
    status: "ringing,accepted,declined,ended,missed,canceled",
  });
  const data = res.data?.results || res.data || [];
  sessions.value = Array.isArray(data) ? data : [];
};

const loadRecordingSettings = async () => {
  try {
    const res = await api.systemSettings.getAll();
    const rawValue = res.data?.[CALL_RECORDING_ALLOWED_USERS_KEY]?.value || "";
    recordingAllowedUsers.value = parseAllowedRecordingUsernames(rawValue);
  } catch (error) {
    console.error("録音設定の取得に失敗しました", error);
    recordingAllowedUsers.value = [];
  }
};

const reload = async () => {
  if (!canUseRecordingFeatures.value) return;
  loading.value = true;
  try {
    await loadSessions();
    hasLoaded.value = true;
  } catch (error) {
    console.error("録音一覧の読み込みに失敗しました", error);
    window.alert("録音一覧の読み込みに失敗しました。");
  } finally {
    loading.value = false;
  }
};

const toggleTranscript = (sessionId) => {
  expandedSessionId.value = expandedSessionId.value === sessionId ? null : sessionId;
};

const triggerTranscribe = async (session) => {
  if (!session?.id || isTranscribing.value) return;
  isTranscribing.value = true;
  if (session.recording) {
    session.recording.transcript_status = 'processing';
    session.recording.transcript = '';
    session.recording.transcript_language = '';
  }
  try {
    await api.notifications.transcribeRecording(session.id);
  } catch (error) {
    console.error("文字起こしリクエスト失敗", error);
    window.alert("文字起こしリクエストに失敗しました。");
    if (session.recording) {
      session.recording.transcript_status = 'failed';
    }
  } finally {
    isTranscribing.value = false;
  }
};

const goCallCenter = () => {
  router.push("/notifications/calls");
};

const goNotificationList = () => {
  router.push("/notifications");
};

onMounted(async () => {
  await loadRecordingSettings();
  if (!canUseRecordingFeatures.value) {
    sessions.value = [];
    hasLoaded.value = false;
    router.replace("/notifications");
    return;
  }
  isReady.value = true;
});
</script>

<style scoped>
.recording-list-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: 20px;
}

.page-title {
  margin: 0 0 16px;
  font-size: 22px;
  font-weight: 700;
  color: #1f2a44;
}

.list-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.list-note {
  font-size: 13px;
  color: #64748b;
}

.header-actions,
.filter-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-row {
  margin-bottom: 12px;
}

.filter-field {
  display: grid;
  gap: 6px;
  min-width: 180px;
  font-size: 12px;
  color: #334155;
}

.text-input,
.select-input {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  background: #fff;
}

.summary-row {
  margin-bottom: 10px;
  font-size: 12px;
  color: #64748b;
}

.recording-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.recording-table th,
.recording-table td {
  text-align: left;
  padding: 10px 8px;
  border-bottom: 1px solid #e2e8f0;
  vertical-align: middle;
}

.recording-table th {
  background: #f8fafc;
  color: #1f2a44;
  font-weight: 700;
}

.audio-cell {
  min-width: 240px;
}

.audio-cell audio {
  width: 100%;
  height: 32px;
}

.recording-row {
  cursor: pointer;
}

.recording-row:hover {
  background: #f1f5f9;
}

.transcript-row td {
  padding: 0 8px 10px;
  border-bottom: 1px solid #e2e8f0;
}

.transcript-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
}

.transcript-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.transcript-label {
  font-size: 12px;
  font-weight: 700;
  color: #1f2a44;
}

.transcript-lang {
  font-size: 11px;
  color: #64748b;
}

.transcript-text {
  font-size: 13px;
  color: #334155;
  line-height: 1.7;
  white-space: pre-wrap;
}

.transcript-status {
  font-size: 12px;
  color: #94a3b8;
}

.transcript-status.error {
  color: #dc2626;
}

.transcribe-cell {
  text-align: center;
}

.transcribe-btn {
  background: #059669;
  padding: 5px 10px;
  font-size: 12px;
}

.transcribe-btn:disabled {
  background: #94a3b8;
}

.empty {
  text-align: center;
  padding: 18px;
  color: #94a3b8;
}

.btn {
  border: none;
  border-radius: 8px;
  padding: 9px 14px;
  font-size: 13px;
  cursor: pointer;
  color: #fff;
}

.secondary-btn {
  background: #475569;
}

.link-btn {
  background: #2563eb;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 900px) {
  .recording-list-page {
    padding: 16px;
  }

  .list-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .recording-table {
    font-size: 12px;
  }

  .audio-cell {
    min-width: 180px;
  }
}
</style>
