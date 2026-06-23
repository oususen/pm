<template>
  <div class="call-center-page">
    <div class="page-header">
      <div class="page-heading">
        <h2 class="page-title">社内通話</h2>
        <button
          v-if="incomingSessions.length"
          type="button"
          class="incoming-summary-button"
          @click="focusIncomingSession(incomingSessions[0])"
        >
          <span class="incoming-summary-label">着信中</span>
          <span class="incoming-summary-name">{{ incomingSessions[0].caller_name }}</span>
          <span class="incoming-summary-type">{{ incomingSessions[0].call_type === 'video' ? 'ビデオ通話' : '音声通話' }}</span>
          <span class="incoming-summary-time">{{ formatDateTime(incomingSessions[0].initiated_at) }}</span>
        </button>
      </div>
      <div class="header-actions">
        <button class="btn secondary-btn" type="button" @click="reloadAll" :disabled="loading">
          再読込
        </button>
        <button class="btn secondary-btn" type="button" @click="goNotificationList">
          通知一覧
        </button>
      </div>
    </div>

    <div class="layout">
      <aside class="sidebar">
        <section class="panel">
          <div class="caller-row">
            <div class="panel-title compact">発信</div>
            <label class="field-label inline-label" for="peer-select">相手</label>
          </div>
          <div v-if="environmentWarning" class="warning-box">
            {{ environmentWarning }}
          </div>
          <select id="peer-select" v-model="selectedPeerId" class="select">
            <option value="">選択してください</option>
            <option v-for="user in users" :key="user.id" :value="String(user.id)">
              {{ formatUserLabel(user) }}
            </option>
          </select>
          <div class="action-row">
            <button class="btn voice-btn" type="button" @click="startCall('voice')" :disabled="!selectedPeerId || busy">
              音声発信
            </button>
            <button class="btn video-btn" type="button" @click="startCall('video')" :disabled="!selectedPeerId || busy">
              ビデオ発信
            </button>
          </div>
        </section>

        <section class="panel">
          <div class="panel-title">最近の通話</div>
          <div v-if="recentSessions.length" class="session-list">
            <div v-for="session in recentSessions" :key="session.id" class="session-entry">
              <button
                type="button"
                class="session-card"
                :class="{ active: currentSession?.id === session.id }"
                @click="selectSession(session)"
              >
                <strong>{{ counterpartName(session) }}</strong>
                <span>{{ session.call_type === 'video' ? 'ビデオ通話' : '音声通話' }} / {{ statusLabel(session.status) }}</span>
                <span>{{ formatDateTime(session.initiated_at) }}</span>
              </button>
              <div
                v-if="canUseRecordingFeatures && session.has_recording && session.recording?.file_url"
                class="session-recording"
              >
                <span class="session-recording-label">録音あり</span>
                <audio controls preload="none" :src="session.recording.file_url" @click.stop></audio>
              </div>
            </div>
          </div>
          <div v-else class="empty">履歴はありません。</div>
        </section>

      </aside>

      <main class="main-panel">
        <section class="call-stage">
          <div class="stage-header">
            <div class="stage-status-line">
              <div class="stage-subtitle">
                {{ currentSession ? `${currentSession.call_type === 'video' ? 'ビデオ通話' : '音声通話'}` : '相手を選択して発信してください。' }}
              </div>
              <div class="status-badge" :class="statusClass">
                {{ statusMessage }}
              </div>
            </div>
            <div v-if="canUseRecordingFeatures" class="recording-status-group">
              <div v-if="showRecordingBadge" class="recording-badge">
                <span class="recording-dot"></span>
                録音中
              </div>
              <div v-if="recordingStatusText" class="recording-status-text">
                {{ recordingStatusText }}
              </div>
              <button
                v-if="canRetryRecordingUpload"
                class="btn secondary-btn retry-btn"
                type="button"
                @click="retryRecordingUpload"
                :disabled="busy || recordingUploadInFlight"
              >
                録音再送
              </button>
            </div>
          </div>

          <div class="media-grid" :class="{ single: !showRemoteVideo }">
            <div
              class="video-card remote"
              @touchstart="handleRemoteTouchStart"
              @touchmove="handleRemoteTouchMove"
              @touchend="handleRemoteTouchEnd"
              @touchcancel="handleRemoteTouchEnd"
            >
              <video
                ref="remoteVideoRef"
                autoplay
                playsinline
                :style="remoteVideoStyle"
              ></video>
            </div>
            <div class="video-card local">
              <video ref="localVideoRef" autoplay muted playsinline :class="{ mirrored: isFrontCameraActive }"></video>
              <div v-if="hasVideoTrack" class="camera-facing-badge">
                {{ currentCameraLabel }}
              </div>
              <div v-if="!showLocalVideo" class="video-placeholder small">
                <div class="placeholder-name">自分</div>
                <div class="placeholder-note">カメラオフ</div>
              </div>
            </div>
          </div>

          <div class="control-row">
            <button class="btn secondary-btn" type="button" @click="toggleMic" :disabled="!localStream">
              {{ micEnabled ? 'マイクOFF' : 'マイクON' }}
            </button>
            <button class="btn secondary-btn" type="button" @click="toggleCamera" :disabled="!hasVideoTrack">
              {{ cameraEnabled ? 'カメラOFF' : 'カメラON' }}
            </button>
            <button
              v-if="hasVideoTrack && canSwitchCamera"
              class="btn secondary-btn"
              type="button"
              @click="switchCameraFacing"
              :disabled="busy || switchingCamera"
            >
              {{ currentFacingModeLabel }}
            </button>
            <button
              v-if="canAcceptCurrentSession"
              class="btn accept-btn"
              type="button"
              @click="acceptCurrentSession"
              :disabled="busy"
            >
              応答
            </button>
            <button
              v-if="canDeclineCurrentSession"
              class="btn decline-btn"
              type="button"
              @click="declineCurrentSession"
              :disabled="busy"
            >
              辞退
            </button>
            <button
              v-if="canFinishCurrentSession"
              class="btn finish-btn"
              type="button"
              @click="finishCurrentSession"
              :disabled="busy"
            >
              終了
            </button>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import api from "@/api/client";
import { authState } from "@/auth";
import { CALL_RECORDING_ALLOWED_USERS_KEY, parseAllowedRecordingUsernames } from "@/utils/callRecordingAccess";

const router = useRouter();
const route = useRoute();

const users = ref([]);
const sessions = ref([]);
const selectedPeerId = ref("");
const currentSession = ref(null);
const loading = ref(false);
const busy = ref(false);
const statusMessage = ref("待機中");
const environmentWarning = ref("");

const localVideoRef = ref(null);
const remoteVideoRef = ref(null);
const localStream = ref(null);
const remoteStream = ref(null);
const peerConnection = ref(null);
const lastSignalId = ref(0);
const signalTimerId = ref(null);
const sessionTimerId = ref(null);
const connectionStateTimerId = ref(null);
const micEnabled = ref(true);
const cameraEnabled = ref(true);
const preferredFacingMode = ref("user");
const switchingCamera = ref(false);
const currentVideoDeviceId = ref("");
const availableVideoInputCount = ref(0);
const remoteVideoScale = ref(1);
const remotePinchStartDistance = ref(0);
const remotePinchStartScale = ref(1);
const mediaRecorder = ref(null);
const recordingState = ref("idle");
const recordingErrorMessage = ref("");
const recordingMimeType = ref("");
const recordingStartedAt = ref(null);
const recordingEndedAt = ref(null);
const pendingRecordingBlob = ref(null);
const pendingRecordingSessionId = ref(null);
const pendingRecordingMimeType = ref("");
const pendingRecordingDurationSeconds = ref(null);
const recordingUploadInFlight = ref(false);

let CALL_SESSION_POLLING_MS = 3000;
let CALL_SIGNAL_POLLING_MS = 1500;

let recordingAudioContext = null;
let recordingDestination = null;
let localRecordingSource = null;
let remoteRecordingSources = new Map();
let recordingChunks = [];
let recordingStopPromise = null;
let recordingStopResolver = null;
let stopUploadAfterRecording = false;
let stopRecordingSessionId = null;

const turnUrl = (import.meta.env.VITE_TURN_URL || "").trim();
const turnUsername = (import.meta.env.VITE_TURN_USERNAME || "").trim();
const turnCredential = (import.meta.env.VITE_TURN_CREDENTIAL || "").trim();
const recordingAllowedUsers = ref([]);
const rtcIceServers = [{ urls: "stun:stun.l.google.com:19302" }];
if (turnUrl && turnUsername && turnCredential) {
  rtcIceServers.push({
    urls: turnUrl,
    username: turnUsername,
    credential: turnCredential,
  });
}
const CONNECTION_DISCONNECTED_GRACE_MS = 5000;
const rtcConfig = {
  iceServers: rtcIceServers,
  iceTransportPolicy: "all",
  iceCandidatePoolSize: 2,
};

const myUserId = computed(() => authState.user?.id ?? null);
const canUseRecordingFeatures = computed(() => {
  const username = String(authState.user?.username || "").toLowerCase();
  return recordingAllowedUsers.value.includes(username);
});

const recentSessions = computed(() => sessions.value.slice(0, 12));

const incomingSessions = computed(() => {
  return sessions.value.filter(
    (session) => session.status === "ringing" && Number(session.callee) === Number(myUserId.value)
  );
});

const canAcceptCurrentSession = computed(() => {
  return (
    currentSession.value &&
    currentSession.value.status === "ringing" &&
    Number(currentSession.value.callee) === Number(myUserId.value)
  );
});

const canDeclineCurrentSession = computed(() => {
  return (
    currentSession.value &&
    ["ringing", "accepted"].includes(currentSession.value.status)
  );
});

const canFinishCurrentSession = computed(() => {
  return currentSession.value && ["ringing", "accepted"].includes(currentSession.value.status);
});

const hasVideoTrack = computed(() => {
  return Boolean(localStream.value?.getVideoTracks()?.length);
});

const currentFacingModeLabel = computed(() => {
  return preferredFacingMode.value === "environment" ? "前面へ切替" : "背面へ切替";
});

const canSwitchCamera = computed(() => {
  return availableVideoInputCount.value > 1;
});

const currentTrackFacingMode = computed(() => {
  const track = localStream.value?.getVideoTracks?.()[0] || null;
  return getTrackFacingMode(track);
});

const isFrontCameraActive = computed(() => {
  return String(currentTrackFacingMode.value || "").toLowerCase() === "user";
});

const currentCameraLabel = computed(() => {
  if (!hasVideoTrack.value) return "";
  return isFrontCameraActive.value ? "前面カメラ" : "背面カメラ";
});

const showLocalVideo = computed(() => {
  return Boolean(localStream.value?.getVideoTracks()?.some((track) => track.enabled));
});

const showRemoteVideo = computed(() => {
  return Boolean(remoteStream.value?.getVideoTracks()?.length);
});

const remoteVideoStyle = computed(() => {
  return {
    transform: `scale(${remoteVideoScale.value})`,
    transformOrigin: "center center",
  };
});

const remotePlaceholder = computed(() => {
  if (!currentSession.value) return "未接続";
  return counterpartName(currentSession.value);
});

const statusClass = computed(() => {
  const session = currentSession.value;
  if (!session) return "idle";
  if (session.status === "accepted") return "live";
  if (session.status === "ringing") return "ringing";
  return "closed";
});

const showRecordingBadge = computed(() => {
  return Boolean(currentSession.value) && recordingState.value === "recording";
});

const recordingStatusText = computed(() => {
  if (recordingUploadInFlight.value) {
    return "録音アップロード中";
  }
  if (recordingState.value === "failed") {
    return recordingErrorMessage.value || "録音アップロードに失敗しました";
  }
  if (currentSession.value?.has_recording) {
    return "録音保存済み";
  }
  if (recordingState.value === "recording") {
    return "通話を録音しています";
  }
  return "";
});

const canRetryRecordingUpload = computed(() => {
  return (
    Boolean(pendingRecordingBlob.value) &&
    Boolean(currentSession.value?.id) &&
    Number(pendingRecordingSessionId.value) === Number(currentSession.value?.id) &&
    !recordingUploadInFlight.value
  );
});

const formatUserLabel = (user) => {
  const name = displayName(user);
  const dept = user.profile?.division_name || user.profile?.department_name || "";
  return dept ? `${name} (${dept})` : name;
};

const displayName = (user) => {
  const last = user?.last_name || "";
  const first = user?.first_name || "";
  const full = `${last}${first}`.trim();
  return full || user?.username || "-";
};

const counterpartName = (session) => {
  if (!session) return "-";
  return Number(session.caller) === Number(myUserId.value) ? session.callee_name : session.caller_name;
};

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

const formatApiDateTime = (value) => {
  if (!(value instanceof Date) || Number.isNaN(value.getTime())) return "";
  const y = value.getFullYear();
  const m = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  const hh = String(value.getHours()).padStart(2, "0");
  const mm = String(value.getMinutes()).padStart(2, "0");
  const ss = String(value.getSeconds()).padStart(2, "0");
  return `${y}-${m}-${day}T${hh}:${mm}:${ss}`;
};

const goNotificationList = () => {
  router.push("/notifications");
};

const updateVideoBindings = () => {
  if (localVideoRef.value) {
    localVideoRef.value.srcObject = localStream.value;
    localVideoRef.value.play().catch(() => {});
  }
  if (remoteVideoRef.value) {
    remoteVideoRef.value.srcObject = remoteStream.value;
    remoteVideoRef.value.play().catch(() => {});
  }
};

const getTouchDistance = (touches) => {
  if (!touches || touches.length < 2) return 0;
  const [first, second] = touches;
  const dx = first.clientX - second.clientX;
  const dy = first.clientY - second.clientY;
  return Math.hypot(dx, dy);
};

const clampScale = (value) => {
  return Math.min(3, Math.max(1, value));
};

const handleRemoteTouchStart = (event) => {
  if (event.touches.length !== 2) return;
  remotePinchStartDistance.value = getTouchDistance(event.touches);
  remotePinchStartScale.value = remoteVideoScale.value;
};

const handleRemoteTouchMove = (event) => {
  if (event.touches.length !== 2 || !remotePinchStartDistance.value) return;
  event.preventDefault();
  const nextDistance = getTouchDistance(event.touches);
  if (!nextDistance) return;
  const ratio = nextDistance / remotePinchStartDistance.value;
  remoteVideoScale.value = clampScale(remotePinchStartScale.value * ratio);
};

const handleRemoteTouchEnd = () => {
  if (remotePinchStartDistance.value && remoteVideoScale.value < 1.02) {
    remoteVideoScale.value = 1;
  }
  remotePinchStartDistance.value = 0;
  remotePinchStartScale.value = remoteVideoScale.value;
};

const stopTracks = (stream) => {
  if (!stream) return;
  stream.getTracks().forEach((track) => track.stop());
};

const closeRecordingContext = async () => {
  if (localRecordingSource) {
    localRecordingSource.disconnect();
    localRecordingSource = null;
  }
  remoteRecordingSources.forEach((source) => {
    source.disconnect();
  });
  remoteRecordingSources = new Map();
  if (recordingAudioContext) {
    try {
      await recordingAudioContext.close();
    } catch (_error) {
      // close失敗時も録音終了処理を優先する
    }
  }
  recordingAudioContext = null;
  recordingDestination = null;
};

const createAudioOnlyStream = (stream) => {
  const audioTracks = stream?.getAudioTracks?.() || [];
  if (!audioTracks.length) return null;
  return new MediaStream(audioTracks);
};

const attachLocalAudioToRecorder = () => {
  if (!recordingAudioContext || !recordingDestination || !localStream.value || localRecordingSource) return;
  const audioOnlyStream = createAudioOnlyStream(localStream.value);
  if (!audioOnlyStream) return;
  localRecordingSource = recordingAudioContext.createMediaStreamSource(audioOnlyStream);
  localRecordingSource.connect(recordingDestination);
};

const attachRemoteAudioToRecorder = (stream) => {
  if (!recordingAudioContext || !recordingDestination || !stream?.id || remoteRecordingSources.has(stream.id)) return;
  const audioOnlyStream = createAudioOnlyStream(stream);
  if (!audioOnlyStream) return;
  const remoteSource = recordingAudioContext.createMediaStreamSource(audioOnlyStream);
  remoteSource.connect(recordingDestination);
  remoteRecordingSources.set(stream.id, remoteSource);
};

const selectRecordingMimeType = () => {
  if (typeof window === "undefined" || typeof window.MediaRecorder === "undefined") return "";
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
  ];
  return candidates.find((candidate) => window.MediaRecorder.isTypeSupported?.(candidate)) || "";
};

const clearPendingRecording = () => {
  pendingRecordingBlob.value = null;
  pendingRecordingSessionId.value = null;
  pendingRecordingMimeType.value = "";
  pendingRecordingDurationSeconds.value = null;
  recordingErrorMessage.value = "";
};

const uploadPendingRecording = async (sessionId) => {
  if (!canUseRecordingFeatures.value) {
    clearPendingRecording();
    return;
  }
  if (!pendingRecordingBlob.value || !sessionId) return;

  recordingUploadInFlight.value = true;
  recordingErrorMessage.value = "";
  try {
    const extension = pendingRecordingMimeType.value.includes("mp4") ? "mp4" : "webm";
    const formData = new FormData();
    formData.append(
      "file",
      pendingRecordingBlob.value,
      `call-recording-${sessionId}.${extension}`
    );
    formData.append("mime_type", pendingRecordingMimeType.value || pendingRecordingBlob.value.type || "application/octet-stream");
    formData.append("file_size", String(pendingRecordingBlob.value.size || 0));
    if (recordingStartedAt.value) {
      formData.append("recording_started_at", formatApiDateTime(recordingStartedAt.value));
    }
    if (recordingEndedAt.value) {
      formData.append("recording_ended_at", formatApiDateTime(recordingEndedAt.value));
    }
    if (pendingRecordingDurationSeconds.value != null) {
      formData.append("duration_seconds", String(pendingRecordingDurationSeconds.value));
    }

    await api.notifications.uploadCallRecording(sessionId, formData);
    clearPendingRecording();
    recordingState.value = "uploaded";
    await loadSessions();
    if (currentSession.value?.id === sessionId) {
      await refreshCurrentSession();
    }
  } catch (error) {
    console.error("録音アップロード失敗", error);
    recordingState.value = "failed";
    recordingErrorMessage.value = "録音アップロードに失敗しました。再送してください。";
  } finally {
    recordingUploadInFlight.value = false;
  }
};

const beginCallRecording = async (session) => {
  if (!session) return;
  if (!canUseRecordingFeatures.value) {
    recordingState.value = "idle";
    return;
  }
  if (typeof window === "undefined") {
    return;
  }
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (typeof window.MediaRecorder === "undefined" || typeof AudioContextClass === "undefined") {
    recordingState.value = "failed";
    recordingErrorMessage.value = "このブラウザでは録音に対応していません。";
    return;
  }
  if (recordingState.value === "recording") return;

  await closeRecordingContext();
  clearPendingRecording();

  recordingAudioContext = new AudioContextClass();
  recordingDestination = recordingAudioContext.createMediaStreamDestination();
  recordingChunks = [];
  recordingStartedAt.value = new Date();
  recordingEndedAt.value = null;
  recordingMimeType.value = selectRecordingMimeType();

  attachLocalAudioToRecorder();
  if (remoteStream.value) {
    attachRemoteAudioToRecorder(remoteStream.value);
  }

  const recorderOptions = recordingMimeType.value ? { mimeType: recordingMimeType.value } : undefined;
  const recorder = new window.MediaRecorder(recordingDestination.stream, recorderOptions);
  mediaRecorder.value = recorder;
  recordingState.value = "recording";
  recordingErrorMessage.value = "";

  recorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) {
      recordingChunks.push(event.data);
    }
  };

  recorder.onstop = async () => {
    const targetSessionId = stopRecordingSessionId || session.id;
    const endedAt = recordingEndedAt.value || new Date();
    recordingEndedAt.value = endedAt;
    const mimeType = recordingMimeType.value || recorder.mimeType || "application/octet-stream";
    const blob = recordingChunks.length ? new Blob(recordingChunks, { type: mimeType }) : null;
    if (blob) {
      pendingRecordingBlob.value = blob;
      pendingRecordingSessionId.value = targetSessionId;
      pendingRecordingMimeType.value = mimeType;
      pendingRecordingDurationSeconds.value = recordingStartedAt.value
        ? Math.max((endedAt.getTime() - recordingStartedAt.value.getTime()) / 1000, 0)
        : null;
    } else {
      recordingState.value = "idle";
    }

    mediaRecorder.value = null;
    recordingChunks = [];
    await closeRecordingContext();

    if (stopUploadAfterRecording && blob && targetSessionId) {
      await uploadPendingRecording(targetSessionId);
    }

    if (recordingStopResolver) {
      recordingStopResolver();
    }
    recordingStopPromise = null;
    recordingStopResolver = null;
    stopUploadAfterRecording = false;
    stopRecordingSessionId = null;
  };

  recorder.start(1000);
};

const stopCallRecording = async (session, { upload = true } = {}) => {
  const targetSessionId = Number(session?.id || pendingRecordingSessionId.value || currentSession.value?.id || 0);
  if (!targetSessionId) return;

  if (recordingStopPromise) {
    await recordingStopPromise;
    if (upload && pendingRecordingBlob.value && Number(pendingRecordingSessionId.value) === targetSessionId) {
      await uploadPendingRecording(targetSessionId);
    }
    return;
  }

  const recorder = mediaRecorder.value;
  if (recorder && recorder.state !== "inactive") {
    recordingEndedAt.value = new Date();
    stopUploadAfterRecording = upload;
    stopRecordingSessionId = targetSessionId;
    recordingStopPromise = new Promise((resolve) => {
      recordingStopResolver = resolve;
    });
    recorder.stop();
    await recordingStopPromise;
    return;
  }

  if (upload && pendingRecordingBlob.value && Number(pendingRecordingSessionId.value) === targetSessionId) {
    await uploadPendingRecording(targetSessionId);
  }
};

const finalizeCallUi = async (session, { statusText = "", uploadRecording = true, refreshSession = true } = {}) => {
  await stopCallRecording(session, { upload: uploadRecording });
  stopSignalPolling();
  closePeerConnection();
  resetMedia();
  if (statusText) {
    statusMessage.value = statusText;
  }
  await loadSessions();
  if (refreshSession && currentSession.value?.id) {
    await refreshCurrentSession();
  }
};

const retryRecordingUpload = async () => {
  if (!canRetryRecordingUpload.value || !currentSession.value?.id) return;
  await uploadPendingRecording(currentSession.value.id);
};

const closePeerConnection = () => {
  stopConnectionStateTimer();
  if (peerConnection.value) {
    peerConnection.value.onicecandidate = null;
    peerConnection.value.ontrack = null;
    peerConnection.value.onconnectionstatechange = null;
    peerConnection.value.close();
    peerConnection.value = null;
  }
  remoteStream.value = null;
  updateVideoBindings();
};

const resetMedia = () => {
  stopTracks(localStream.value);
  stopTracks(remoteStream.value);
  localStream.value = null;
  remoteStream.value = null;
  micEnabled.value = true;
  cameraEnabled.value = true;
  updateVideoBindings();
};

const stopSignalPolling = () => {
  if (signalTimerId.value) {
    window.clearInterval(signalTimerId.value);
    signalTimerId.value = null;
  }
};

const stopSessionPolling = () => {
  if (sessionTimerId.value) {
    window.clearInterval(sessionTimerId.value);
    sessionTimerId.value = null;
  }
};

const stopConnectionStateTimer = () => {
  if (connectionStateTimerId.value) {
    window.clearTimeout(connectionStateTimerId.value);
    connectionStateTimerId.value = null;
  }
};

const getPeerUserId = (session = currentSession.value) => {
  if (!session) return null;
  return Number(session.caller) === Number(myUserId.value) ? session.callee : session.caller;
};

const isSecureMediaContext = () => {
  if (typeof window === "undefined") return false;
  if (window.isSecureContext) return true;
  const hostname = window.location.hostname || "";
  return hostname === "localhost" || hostname === "127.0.0.1";
};

const getMediaEnvironmentError = () => {
  if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
    return "このブラウザではマイク・カメラ取得に対応していません。";
  }
  if (!isSecureMediaContext()) {
    return "音声通話・ビデオ通話は HTTPS または localhost で開いてください。現在の HTTP 接続ではマイク・カメラを利用できません。";
  }
  return "";
};

const getMediaErrorMessage = (error, callType) => {
  const mediaLabel = callType === "video" ? "マイク・カメラ" : "マイク";
  if (!error) {
    return `${mediaLabel}の取得に失敗しました。`;
  }
  if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
    return `${mediaLabel}の利用が拒否されました。ブラウザの権限設定を確認してください。`;
  }
  if (error.name === "NotFoundError" || error.name === "DevicesNotFoundError") {
    return `${mediaLabel}に必要なデバイスが見つかりません。`;
  }
  if (error.name === "NotReadableError" || error.name === "TrackStartError") {
    return `${mediaLabel}が他のアプリで使用中のため取得できません。`;
  }
  if (error.name === "SecurityError") {
    return "音声通話・ビデオ通話は HTTPS または localhost で開いてください。";
  }
  return `${mediaLabel}の取得に失敗しました。`;
};

const isFacingModeMatch = (label, facingMode) => {
  const normalized = String(label || "").toLowerCase();
  if (!normalized) return false;
  if (facingMode === "environment") {
    return ["back", "rear", "environment", "world", "背面", "リア", "後"].some((word) =>
      normalized.includes(word)
    );
  }
  return ["front", "user", "face", "前面", "フロント"].some((word) => normalized.includes(word));
};

const pickDeviceByFacingMode = (videoInputs, facingMode, excludedDeviceId = "") => {
  const candidates = videoInputs.filter((device) => device.deviceId && device.deviceId !== excludedDeviceId);
  if (!candidates.length) return "";

  const matchedDevice = candidates.find((device) => isFacingModeMatch(device.label, facingMode));
  if (matchedDevice) return matchedDevice.deviceId;

  if (!excludedDeviceId && candidates.length >= 2) {
    return facingMode === "environment"
      ? candidates[candidates.length - 1].deviceId
      : candidates[0].deviceId;
  }

  return candidates[0].deviceId;
};

const listVideoInputDevices = async () => {
  if (!navigator.mediaDevices?.enumerateDevices) return [];
  const devices = await navigator.mediaDevices.enumerateDevices();
  return devices.filter((device) => device.kind === "videoinput");
};

const refreshVideoInputCount = async () => {
  const videoInputs = await listVideoInputDevices();
  availableVideoInputCount.value = videoInputs.length;
  return videoInputs;
};

const getTrackDeviceId = (track) => {
  const settingsDeviceId = track?.getSettings?.().deviceId || "";
  const constrainedDeviceId = track?.getConstraints?.().deviceId;
  if (typeof constrainedDeviceId === "string") return constrainedDeviceId;
  if (constrainedDeviceId?.exact) return constrainedDeviceId.exact;
  if (constrainedDeviceId?.ideal) return constrainedDeviceId.ideal;
  return settingsDeviceId;
};

const getTrackFacingMode = (track) => {
  const settingsFacingMode = track?.getSettings?.().facingMode;
  const constrainedFacingMode = track?.getConstraints?.().facingMode;
  if (typeof constrainedFacingMode === "string") return constrainedFacingMode;
  if (constrainedFacingMode?.exact) return constrainedFacingMode.exact;
  if (constrainedFacingMode?.ideal) return constrainedFacingMode.ideal;
  return settingsFacingMode || "";
};

const openVideoStreamByDeviceId = async (deviceId) => {
  return navigator.mediaDevices.getUserMedia({
    audio: false,
    video: {
      deviceId: { exact: deviceId },
    },
  });
};

const waitForCameraRelease = (ms = 180) => {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
};

const isSameVideoInputTrack = (nextTrack, currentTrack) => {
  const nextDeviceId = getTrackDeviceId(nextTrack);
  const currentDeviceId = getTrackDeviceId(currentTrack);
  if (nextDeviceId && currentDeviceId) {
    return nextDeviceId === currentDeviceId;
  }
  return false;
};

const getFallbackCameraDeviceId = async (targetFacingMode, currentTrack = null) => {
  const videoInputs = await refreshVideoInputCount();
  if (!videoInputs.length) return "";

  const currentDeviceId =
    currentVideoDeviceId.value ||
    currentTrack?.getSettings?.().deviceId ||
    currentTrack?.getConstraints?.().deviceId ||
    "";

  return pickDeviceByFacingMode(videoInputs, targetFacingMode, currentDeviceId);
};

const getNextCameraDevice = async (targetFacingMode, currentTrack = null) => {
  const videoInputs = await refreshVideoInputCount();
  if (!videoInputs.length) return { deviceId: "", facingMode: targetFacingMode };

  const currentDeviceId =
    currentVideoDeviceId.value ||
    currentTrack?.getSettings?.().deviceId ||
    currentTrack?.getConstraints?.().deviceId ||
    "";

  const preferredDeviceId = pickDeviceByFacingMode(videoInputs, targetFacingMode, currentDeviceId);
  if (preferredDeviceId) {
    return { deviceId: preferredDeviceId, facingMode: targetFacingMode };
  }

  const currentIndex = videoInputs.findIndex((device) => device.deviceId === currentDeviceId);
  if (currentIndex >= 0 && videoInputs.length > 1) {
    const nextIndex = (currentIndex + 1) % videoInputs.length;
    return { deviceId: videoInputs[nextIndex].deviceId, facingMode: targetFacingMode };
  }

  const fallbackDeviceId = await getFallbackCameraDeviceId(targetFacingMode, currentTrack);
  return { deviceId: fallbackDeviceId, facingMode: targetFacingMode };
};

const openVideoStreamForFacingMode = async (targetFacingMode, currentTrack = null) => {
  const baseConstraints = { audio: false };
  try {
    return await navigator.mediaDevices.getUserMedia({
      ...baseConstraints,
      video: {
        facingMode: { exact: targetFacingMode },
      },
    });
  } catch (exactError) {
    try {
      return await navigator.mediaDevices.getUserMedia({
        ...baseConstraints,
        video: {
          facingMode: { ideal: targetFacingMode },
        },
      });
    } catch (idealError) {
      const fallbackDeviceId = await getFallbackCameraDeviceId(targetFacingMode, currentTrack);
      if (!fallbackDeviceId) {
        const nextCamera = await getNextCameraDevice(targetFacingMode, currentTrack);
        if (!nextCamera.deviceId) {
          throw idealError;
        }
        return navigator.mediaDevices.getUserMedia({
          ...baseConstraints,
          video: {
            deviceId: { exact: nextCamera.deviceId },
          },
        });
      }
      return navigator.mediaDevices.getUserMedia({
        ...baseConstraints,
        video: {
          deviceId: { exact: fallbackDeviceId },
        },
      });
    }
  }
};

const openPreferredVideoStream = async (targetFacingMode, currentTrack = null) => {
  const tryOpen = async () => {
    const stream = await openVideoStreamForFacingMode(targetFacingMode, currentTrack);
    const track = stream.getVideoTracks()[0];
    if (!track || isTrackMatchingFacingMode(track, targetFacingMode)) {
      return stream;
    }

    stopTracks(stream);
    const videoInputs = await refreshVideoInputCount();
    const preferredDeviceId = pickDeviceByFacingMode(videoInputs, targetFacingMode, getTrackDeviceId(currentTrack));
    if (!preferredDeviceId) {
      throw new Error("preferred_camera_not_found");
    }
    return openVideoStreamByDeviceId(preferredDeviceId);
  };

  try {
    return await tryOpen();
  } catch (error) {
    if (error?.name === "NotReadableError") {
      await waitForCameraRelease();
      return tryOpen();
    }
    throw error;
  }
};

const isTrackMatchingFacingMode = (track, facingMode) => {
  const detectedFacingMode = String(getTrackFacingMode(track) || "").toLowerCase();
  if (detectedFacingMode) {
    if (facingMode === "environment") {
      return ["environment", "rear", "back"].some((word) => detectedFacingMode.includes(word));
    }
    return ["user", "front", "face"].some((word) => detectedFacingMode.includes(word));
  }
  return false;
};

const ensureLocalStream = async (callType) => {
  const environmentError = getMediaEnvironmentError();
  if (environmentError) {
    environmentWarning.value = environmentError;
    const secureError = new Error(environmentError);
    secureError.name = "SecurityError";
    throw secureError;
  }

  const needVideo = callType === "video";
  if (localStream.value) {
    const hasVideo = localStream.value.getVideoTracks().length > 0;
    if (needVideo === hasVideo) {
      updateVideoBindings();
      return localStream.value;
    }
    stopTracks(localStream.value);
    localStream.value = null;
  }

  const stream = await navigator.mediaDevices.getUserMedia({
    audio: true,
    video: false,
  });
  if (needVideo) {
    const videoStream = await openPreferredVideoStream(preferredFacingMode.value, null);
    const videoTrack = videoStream.getVideoTracks?.()[0] || null;
    if (videoTrack) {
      stream.addTrack(videoTrack);
    }
  }
  localStream.value = stream;
  const videoTrack = stream.getVideoTracks?.()[0] || null;
  const videoInputs = await refreshVideoInputCount();
  currentVideoDeviceId.value =
    getTrackDeviceId(videoTrack) ||
    pickDeviceByFacingMode(videoInputs, preferredFacingMode.value) ||
    "";
  environmentWarning.value = "";
  micEnabled.value = true;
  cameraEnabled.value = needVideo;
  updateVideoBindings();
  return stream;
};

const replacePeerConnectionTrack = async (kind, nextTrack, previousTrack = null, stream = localStream.value) => {
  const sender = peerConnection.value?.getSenders().find((item) => item.track?.kind === kind);
  if (sender) {
    await sender.replaceTrack(nextTrack || null);
    return;
  }
  if (nextTrack && peerConnection.value && stream) {
    peerConnection.value.addTrack(nextTrack, stream);
    if (previousTrack) {
      previousTrack.stop();
    }
  }
};

const createPeerConnection = (session) => {
  closePeerConnection();

  const pc = new RTCPeerConnection(rtcConfig);
  peerConnection.value = pc;
  remoteStream.value = new MediaStream();
  updateVideoBindings();

  localStream.value?.getTracks().forEach((track) => {
    pc.addTrack(track, localStream.value);
  });

  pc.ontrack = (event) => {
    event.streams[0]?.getTracks().forEach((track) => {
      if (!remoteStream.value.getTracks().some((item) => item.id === track.id)) {
        remoteStream.value.addTrack(track);
      }
    });
    if (event.streams?.[0]) {
      attachRemoteAudioToRecorder(event.streams[0]);
    }
    updateVideoBindings();
  };

  pc.onicecandidate = async (event) => {
    if (!event.candidate || !currentSession.value || currentSession.value.id !== session.id) return;
    try {
      await api.notifications.sendCallSignal(session.id, {
        target_user: getPeerUserId(session),
        signal_type: "ice_candidate",
        payload: event.candidate.toJSON(),
      });
    } catch (error) {
      console.error("ICE送信失敗", error);
    }
  };

  pc.onconnectionstatechange = () => {
    const state = pc.connectionState;
    if (state === "connected") {
      stopConnectionStateTimer();
      statusMessage.value = "接続中";
    } else if (state === "disconnected") {
      statusMessage.value = "接続が不安定です";
      stopConnectionStateTimer();
      connectionStateTimerId.value = window.setTimeout(() => {
        if (pc.connectionState === "disconnected") {
          statusMessage.value = "接続が切れました";
        }
      }, CONNECTION_DISCONNECTED_GRACE_MS);
    } else if (state === "failed") {
      stopConnectionStateTimer();
      statusMessage.value = "接続が切れました";
    } else if (state === "closed") {
      stopConnectionStateTimer();
      statusMessage.value = "終了";
    }
  };

  return pc;
};

const loadUsers = async () => {
  const res = await api.accounts.getUsers({ is_active: true, ordering: "username", page_size: 0 });
  const data = res.data?.results || res.data || [];
  users.value = Array.isArray(data) ? data.filter((user) => Number(user.id) !== Number(myUserId.value)) : [];
};

const loadRecordingSettings = async () => {
  try {
    const res = await api.systemSettings.getAll();
    const rawValue = res.data?.[CALL_RECORDING_ALLOWED_USERS_KEY]?.value || "";
    recordingAllowedUsers.value = parseAllowedRecordingUsernames(rawValue);
  } catch (error) {
    console.error("録音設定の取得失敗", error);
    recordingAllowedUsers.value = [];
  }
};

const loadCallPollingSettings = async () => {
  try {
    const res = await api.systemSettings.getAll();
    const data = res.data || {};
    if (data.call_polling_sec?.value) {
      const sec = parseInt(data.call_polling_sec.value, 10);
      if (sec > 0) {
        CALL_SESSION_POLLING_MS = sec * 1000;
      }
    }
    if (data.call_signal_polling_ms?.value) {
      const ms = parseInt(data.call_signal_polling_ms.value, 10);
      if (ms > 0) {
        CALL_SIGNAL_POLLING_MS = ms;
      }
    }
  } catch (error) {
    console.error("通話ポーリング設定の取得失敗", error);
  }
};

const loadSessions = async () => {
  const res = await api.notifications.listCallSessions({
    status: "ringing,accepted,declined,ended,missed,canceled",
  });
  const data = res.data?.results || res.data || [];
  sessions.value = Array.isArray(data) ? data : [];
  if (currentSession.value) {
    const refreshed = sessions.value.find((item) => item.id === currentSession.value.id);
    if (refreshed) {
      currentSession.value = refreshed;
    }
  }
};

const refreshCurrentSession = async () => {
  if (!currentSession.value) return;
  try {
    const res = await api.notifications.getCallSession(currentSession.value.id);
    currentSession.value = res.data;
  } catch (error) {
    console.error("通話状態更新失敗", error);
  }
};

const reloadAll = async () => {
  loading.value = true;
  try {
    await Promise.all([loadUsers(), loadSessions()]);
    await maybeOpenSessionFromQuery();
  } finally {
    loading.value = false;
  }
};

const selectSession = (session) => {
  currentSession.value = session;
  statusMessage.value = statusLabel(session.status);
};

const focusIncomingSession = (session) => {
  currentSession.value = session;
  statusMessage.value = "着信中";
};

const sendOffer = async (session) => {
  const pc = peerConnection.value;
  const offer = await pc.createOffer({
    offerToReceiveAudio: true,
    offerToReceiveVideo: session.call_type === "video",
  });
  await pc.setLocalDescription(offer);
  await api.notifications.sendCallSignal(session.id, {
    target_user: getPeerUserId(session),
    signal_type: "offer",
    payload: {
      type: offer.type,
      sdp: offer.sdp,
    },
  });
};

const handleSignal = async (signal) => {
  if (!peerConnection.value || !currentSession.value) return;
  const pc = peerConnection.value;

  if (signal.signal_type === "offer") {
    if (!pc.currentRemoteDescription) {
      await pc.setRemoteDescription(new RTCSessionDescription(signal.payload));
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      await api.notifications.sendCallSignal(currentSession.value.id, {
        target_user: getPeerUserId(currentSession.value),
        signal_type: "answer",
        payload: {
          type: answer.type,
          sdp: answer.sdp,
        },
      });
    }
    return;
  }

  if (signal.signal_type === "answer") {
    if (!pc.currentRemoteDescription) {
      await pc.setRemoteDescription(new RTCSessionDescription(signal.payload));
    }
    return;
  }

  if (signal.signal_type === "ice_candidate") {
    if (signal.payload?.candidate) {
      await pc.addIceCandidate(new RTCIceCandidate(signal.payload));
    }
    return;
  }

  if (signal.signal_type === "hangup") {
    await finalizeCallUi(currentSession.value, {
      statusText: "相手が通話を終了しました",
      uploadRecording: true,
      refreshSession: true,
    });
  }
};

const pollSignals = async () => {
  if (!currentSession.value) return;
  try {
    const res = await api.notifications.getCallSignals(currentSession.value.id, {
      after_id: lastSignalId.value,
    });
    const data = Array.isArray(res.data) ? res.data : [];
    for (const signal of data) {
      lastSignalId.value = Math.max(lastSignalId.value, Number(signal.id || 0));
      await handleSignal(signal);
    }
  } catch (error) {
    console.error("シグナル取得失敗", error);
  }
};

const startSignalPolling = () => {
  stopSignalPolling();
  signalTimerId.value = window.setInterval(() => {
    pollSignals();
  }, CALL_SIGNAL_POLLING_MS);
};

const joinSession = async (session, { createOffer }) => {
  lastSignalId.value = 0;
  await ensureLocalStream(session.call_type);
  createPeerConnection(session);
  updateVideoBindings();
  currentSession.value = session;
  statusMessage.value = createOffer ? "呼出中" : "接続準備中";
  await beginCallRecording(session);
  startSignalPolling();
  if (createOffer) {
    await sendOffer(session);
  } else {
    await pollSignals();
  }
};

const startCall = async (callType) => {
  if (!selectedPeerId.value) return;
  busy.value = true;
  try {
    await ensureLocalStream(callType);
    const res = await api.notifications.startCall({
      callee_id: Number(selectedPeerId.value),
      call_type: callType,
    });
    const session = res.data;
    await loadSessions();
    await joinSession(session, { createOffer: true });
  } catch (error) {
    console.error("発信失敗", error);
    window.alert(error?.response?.data?.detail || getMediaErrorMessage(error, callType));
    if (!error?.response) {
      statusMessage.value = "待機中";
    }
  } finally {
    busy.value = false;
  }
};

const acceptCurrentSession = async () => {
  if (!currentSession.value) return;
  busy.value = true;
  try {
    await ensureLocalStream(currentSession.value.call_type);
    const res = await api.notifications.acceptCall(currentSession.value.id);
    await joinSession(res.data, { createOffer: false });
    await loadSessions();
  } catch (error) {
    console.error("応答失敗", error);
    window.alert(error?.response?.data?.detail || getMediaErrorMessage(error, currentSession.value?.call_type));
  } finally {
    busy.value = false;
  }
};

const declineCurrentSession = async () => {
  if (!currentSession.value) return;
  const session = currentSession.value;
  busy.value = true;
  try {
    await api.notifications.declineCall(session.id);
    await finalizeCallUi(session, {
      statusText: "辞退しました",
      uploadRecording: true,
      refreshSession: false,
    });
  } catch (error) {
    console.error("辞退失敗", error);
    window.alert(error?.response?.data?.detail || "辞退に失敗しました。");
  } finally {
    busy.value = false;
  }
};

const finishCurrentSession = async () => {
  if (!currentSession.value) return;
  const session = currentSession.value;
  busy.value = true;
  try {
    await api.notifications.finishCall(session.id);
    await finalizeCallUi(session, {
      statusText: "終了しました",
      uploadRecording: true,
      refreshSession: false,
    });
  } catch (error) {
    console.error("終了失敗", error);
    window.alert(error?.response?.data?.detail || "終了に失敗しました。");
  } finally {
    busy.value = false;
  }
};

const toggleMic = () => {
  if (!localStream.value) return;
  micEnabled.value = !micEnabled.value;
  localStream.value.getAudioTracks().forEach((track) => {
    track.enabled = micEnabled.value;
  });
};

const toggleCamera = () => {
  if (!localStream.value) return;
  cameraEnabled.value = !cameraEnabled.value;
  localStream.value.getVideoTracks().forEach((track) => {
    track.enabled = cameraEnabled.value;
  });
};

const switchCameraFacing = async () => {
  if (!localStream.value || !hasVideoTrack.value || switchingCamera.value) return;
  if (!canSwitchCamera.value) return;
  switchingCamera.value = true;
  const nextFacingMode = preferredFacingMode.value === "environment" ? "user" : "environment";
  const previousFacingMode = preferredFacingMode.value;
  const currentAudioTracks = localStream.value.getAudioTracks();
  const currentVideoTrack = localStream.value.getVideoTracks()[0] || null;

  try {
    preferredFacingMode.value = nextFacingMode;
    if (currentVideoTrack) {
      currentVideoTrack.stop();
      await waitForCameraRelease();
    }
    let nextCamera = await getNextCameraDevice(preferredFacingMode.value, currentVideoTrack);
    let videoStream = await openPreferredVideoStream(preferredFacingMode.value, currentVideoTrack);
    let nextVideoTrack = videoStream.getVideoTracks()[0];
    if (!nextVideoTrack) {
      throw new Error("video_track_not_found");
    }

    if (
      !isTrackMatchingFacingMode(nextVideoTrack, preferredFacingMode.value) ||
      isSameVideoInputTrack(nextVideoTrack, currentVideoTrack)
    ) {
      stopTracks(videoStream);
      nextCamera = await getNextCameraDevice(preferredFacingMode.value, null);
      if (!nextCamera.deviceId) {
        preferredFacingMode.value = previousFacingMode;
        return;
      }
      videoStream = await openVideoStreamByDeviceId(nextCamera.deviceId);
      nextVideoTrack = videoStream.getVideoTracks()[0];
      if (!nextVideoTrack) {
        throw new Error("video_track_not_found");
      }
    }

    nextVideoTrack.enabled = cameraEnabled.value;

    const nextStream = new MediaStream([
      ...currentAudioTracks,
      nextVideoTrack,
    ]);

    await replacePeerConnectionTrack("video", nextVideoTrack, null, nextStream);

    if (currentVideoTrack) {
      localStream.value.removeTrack(currentVideoTrack);
    }
    localStream.value = nextStream;
    const videoInputs = await refreshVideoInputCount();
    currentVideoDeviceId.value =
      getTrackDeviceId(nextVideoTrack) ||
      nextCamera.deviceId ||
      pickDeviceByFacingMode(videoInputs, preferredFacingMode.value) ||
      "";
    updateVideoBindings();
  } catch (error) {
    preferredFacingMode.value = previousFacingMode;
    console.error("カメラ切替失敗", error);
    if (currentVideoTrack) {
      try {
        await waitForCameraRelease();
        const restoredVideoStream = await openPreferredVideoStream(previousFacingMode, null);
        const restoredVideoTrack = restoredVideoStream.getVideoTracks()[0];
        if (restoredVideoTrack) {
          restoredVideoTrack.enabled = cameraEnabled.value;
          const restoredStream = new MediaStream([
            ...currentAudioTracks,
            restoredVideoTrack,
          ]);
          await replacePeerConnectionTrack("video", restoredVideoTrack, null, restoredStream);
          localStream.value = restoredStream;
          const videoInputs = await refreshVideoInputCount();
          currentVideoDeviceId.value =
            getTrackDeviceId(restoredVideoTrack) ||
            pickDeviceByFacingMode(videoInputs, previousFacingMode.value) ||
            "";
          updateVideoBindings();
        }
      } catch (restoreError) {
        console.error("カメラ復元失敗", restoreError);
      }
    }
  } finally {
    switchingCamera.value = false;
  }
};

const maybeOpenSessionFromQuery = async () => {
  const sessionId = Number(route.query.session || 0);
  if (!sessionId) return;
  const found = sessions.value.find((session) => session.id === sessionId);
  if (found) {
    currentSession.value = found;
    statusMessage.value = found.status === "ringing" ? "着信中" : statusLabel(found.status);
  }
};

watch([localVideoRef, remoteVideoRef], () => {
  updateVideoBindings();
});

onMounted(async () => {
  environmentWarning.value = getMediaEnvironmentError();
  await Promise.all([loadRecordingSettings(), loadCallPollingSettings(), reloadAll()]);
  stopSessionPolling();
  sessionTimerId.value = window.setInterval(async () => {
    await loadSessions();
    if (currentSession.value) {
      await refreshCurrentSession();
    }
  }, CALL_SESSION_POLLING_MS);
});

onBeforeUnmount(() => {
  stopSignalPolling();
  stopSessionPolling();
  if (mediaRecorder.value?.state && mediaRecorder.value.state !== "inactive") {
    stopUploadAfterRecording = false;
    mediaRecorder.value.stop();
  }
  closePeerConnection();
  resetMedia();
  closeRecordingContext();
});
</script>

<style scoped>
.call-center-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 0;
}

.page-heading {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.page-title {
  margin: 0;
  font-size: 12px;
  color: #10243f;
}

.incoming-summary-button {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  font-size: 12px;
  color: #5c6b82;
  flex-wrap: wrap;
  border: 1px solid #d8bf2f;
  border-radius: 999px;
  background: #fff7b8;
  padding: 6px 12px;
  cursor: pointer;
  text-align: left;
  animation: incoming-blink 1.1s ease-in-out infinite;
}

.incoming-summary-label {
  color: #8a6d00;
  font-weight: 700;
}

.incoming-summary-name {
  color: #10243f;
  font-weight: 700;
}

@keyframes incoming-blink {
  0%,
  100% {
    background: #fff7b8;
    border-color: #d8bf2f;
    box-shadow: 0 0 0 rgba(216, 191, 47, 0);
  }
  50% {
    background: #f1d94a;
    border-color: #c4a900;
    box-shadow: 0 0 0 4px rgba(196, 169, 0, 0.2);
  }
}

.header-actions,
.action-row,
.control-row {
  display: flex;
  column-gap: 8px;
  row-gap: 0;
  flex-wrap: wrap;
}

.layout {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  column-gap: 16px;
  row-gap: 0;
}

.sidebar,
.main-panel {
  min-width: 0;
}

.panel,
.call-stage {
  background: #fff;
  border: 1px solid #d8e0eb;
  border-radius: 14px;
  box-shadow: 0 8px 24px rgba(16, 36, 63, 0.06);
}

.panel {
  padding: 0 14px;
  margin-bottom: 0;
}

.panel-title {
  font-size: 15px;
  font-weight: 700;
  color: #10243f;
  margin-bottom: 10px;
}

.panel-title.compact {
  margin-bottom: 0;
}

.caller-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.field-label {
  display: block;
  font-size: 12px;
  color: #51627c;
  margin-bottom: 6px;
}

.inline-label {
  margin-bottom: 0;
}

.select {
  width: 100%;
  border: 1px solid #c5d0dd;
  border-radius: 8px;
  padding: 10px;
  font-size: 14px;
  margin-bottom: 10px;
}

.helper,
.empty {
  color: #73839a;
  font-size: 12px;
}

.warning-box {
  margin-bottom: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #fff4d6;
  color: #9a6700;
  font-size: 12px;
  line-height: 1.5;
}

.session-list {
  display: grid;
  gap: 0;
}

.session-entry {
  display: grid;
  gap: 6px;
}

.session-card {
  border: 1px solid #d8e0eb;
  border-radius: 10px;
  background: #f7f9fc;
  text-align: left;
  padding: 0 10px;
  cursor: pointer;
  display: grid;
  gap: 0;
}

.session-card.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.session-card.incoming {
  border-color: #f59e0b;
  background: #fff7e8;
}

.session-recording {
  display: grid;
  gap: 4px;
  padding: 0 8px 10px;
}

.session-recording-label {
  font-size: 11px;
  font-weight: 700;
  color: #b91c1c;
}

.session-recording audio {
  width: 100%;
  height: 32px;
}

.stage-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  padding: 0 16px;
  border-bottom: 1px solid #e3e8f0;
}

.stage-status-line {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.stage-subtitle {
  color: #61728a;
  font-size: 13px;
}

.recording-status-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.recording-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  border-radius: 999px;
  background: #fee2e2;
  color: #b91c1c;
  font-size: 12px;
  font-weight: 700;
}

.recording-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #dc2626;
  animation: recording-pulse 1.1s ease-in-out infinite;
}

.recording-status-text {
  font-size: 12px;
  color: #51627c;
}

.retry-btn {
  padding: 8px 12px;
}

@keyframes recording-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}

.status-badge {
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.status-badge.idle {
  background: #eef2f7;
  color: #51627c;
}

.status-badge.ringing {
  background: #fff4d6;
  color: #9a6700;
}

.status-badge.live {
  background: #dff7ea;
  color: #0f766e;
}

.status-badge.closed {
  background: #fce7e7;
  color: #b91c1c;
}

.media-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  column-gap: 12px;
  row-gap: 0;
  padding: 0 16px;
}

.media-grid.single {
  grid-template-columns: minmax(0, 1fr) 220px;
}

.video-card {
  position: relative;
  min-height: 220px;
  border-radius: 12px;
  background: linear-gradient(135deg, #0f172a, #1e293b 60%, #334155);
  overflow: hidden;
}

.video-card video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.video-card.remote {
  touch-action: none;
}

.video-card.local video.mirrored {
  transform: scaleX(-1);
}

.video-card.local video {
  object-fit: contain;
  background: #0f172a;
}

.video-card.local {
  min-height: 180px;
}

.camera-facing-badge {
  position: absolute;
  top: 10px;
  left: 10px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.72);
  color: #f8fbff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.video-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #e2e8f0;
  text-align: center;
  padding: 16px;
}

.video-placeholder.small {
  background: rgba(15, 23, 42, 0.7);
}

.placeholder-name {
  font-size: 20px;
  font-weight: 700;
}

.placeholder-note {
  margin-top: 8px;
  font-size: 12px;
  color: #cbd5e1;
}

.control-row {
  padding: 0 16px;
}

.btn {
  border: none;
  border-radius: 8px;
  padding: 10px 14px;
  color: #fff;
  cursor: pointer;
  font-size: 13px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.secondary-btn {
  background: #475569;
}

.voice-btn {
  background: #0f766e;
}

.video-btn {
  background: #2563eb;
}

.accept-btn {
  background: #15803d;
}

.decline-btn,
.finish-btn {
  background: #dc2626;
}

@media (max-width: 960px) {
  .layout {
    grid-template-columns: 1fr;
  }

  .sidebar {
    display: contents;
  }

  .main-panel {
    order: 2;
  }

  .sidebar .panel:first-child {
    order: 1;
  }

  .sidebar .panel:nth-child(2) {
    order: 3;
  }

  .sidebar .panel:nth-child(3) {
    order: 4;
  }

  .media-grid,
  .media-grid.single {
    grid-template-columns: 1fr;
  }

  .video-card.remote {
    min-height: 52vh;
  }

  .video-card.local {
    min-height: 22vh;
    max-height: 28vh;
  }

  .page-header,
  .stage-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .stage-status-line {
    align-items: flex-start;
  }

  .page-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 6px;
  }

  .incoming-summary-button {
    width: 100%;
    border-radius: 12px;
  }
}
</style>
