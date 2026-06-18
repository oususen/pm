<template>
  <div class="call-center-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">社内通話</h2>
        <p class="page-note">音声通話とビデオ通話を行います。</p>
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
          <div class="panel-title">発信</div>
          <div v-if="environmentWarning" class="warning-box">
            {{ environmentWarning }}
          </div>
          <label class="field-label" for="peer-select">相手</label>
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
          <p class="helper">着信時はこの画面を開いたままにしてください。</p>
        </section>

        <section class="panel">
          <div class="panel-title">着信中</div>
          <div v-if="incomingSessions.length" class="session-list">
            <button
              v-for="session in incomingSessions"
              :key="session.id"
              type="button"
              class="session-card incoming"
              @click="focusIncomingSession(session)"
            >
              <strong>{{ session.caller_name }}</strong>
              <span>{{ session.call_type === 'video' ? 'ビデオ通話' : '音声通話' }}</span>
              <span>{{ formatDateTime(session.initiated_at) }}</span>
            </button>
          </div>
          <div v-else class="empty">着信はありません。</div>
        </section>

        <section class="panel">
          <div class="panel-title">最近の通話</div>
          <div v-if="recentSessions.length" class="session-list">
            <button
              v-for="session in recentSessions"
              :key="session.id"
              type="button"
              class="session-card"
              :class="{ active: currentSession?.id === session.id }"
              @click="selectSession(session)"
            >
              <strong>{{ counterpartName(session) }}</strong>
              <span>{{ session.call_type === 'video' ? 'ビデオ通話' : '音声通話' }} / {{ statusLabel(session.status) }}</span>
              <span>{{ formatDateTime(session.initiated_at) }}</span>
            </button>
          </div>
          <div v-else class="empty">履歴はありません。</div>
        </section>
      </aside>

      <main class="main-panel">
        <section class="call-stage">
          <div class="stage-header">
            <div>
              <div class="stage-title">
                {{ currentSession ? counterpartName(currentSession) : '通話未選択' }}
              </div>
              <div class="stage-subtitle">
                {{ currentSession ? `${currentSession.call_type === 'video' ? 'ビデオ通話' : '音声通話'} / ${statusLabel(currentSession.status)}` : '相手を選択して発信してください。' }}
              </div>
            </div>
            <div class="status-badge" :class="statusClass">
              {{ statusMessage }}
            </div>
          </div>

          <div class="media-grid" :class="{ single: !showRemoteVideo }">
            <div class="video-card remote">
              <video ref="remoteVideoRef" autoplay playsinline></video>
              <div v-if="!showRemoteVideo" class="video-placeholder">
                <div class="placeholder-name">{{ remotePlaceholder }}</div>
                <div class="placeholder-note">相手の映像または音声を待機中</div>
              </div>
            </div>
            <div class="video-card local">
              <video ref="localVideoRef" autoplay muted playsinline></video>
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
              v-if="hasVideoTrack"
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
const micEnabled = ref(true);
const cameraEnabled = ref(true);
const preferredFacingMode = ref("user");
const switchingCamera = ref(false);
const currentVideoDeviceId = ref("");

const rtcConfig = {
  iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
};

const myUserId = computed(() => authState.user?.id ?? null);

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

const showLocalVideo = computed(() => {
  return Boolean(localStream.value?.getVideoTracks()?.some((track) => track.enabled));
});

const showRemoteVideo = computed(() => {
  return Boolean(remoteStream.value?.getVideoTracks()?.length);
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

const stopTracks = (stream) => {
  if (!stream) return;
  stream.getTracks().forEach((track) => track.stop());
};

const closePeerConnection = () => {
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

const listVideoInputDevices = async () => {
  if (!navigator.mediaDevices?.enumerateDevices) return "";
  const devices = await navigator.mediaDevices.enumerateDevices();
  return devices.filter((device) => device.kind === "videoinput");
};

const getFallbackCameraDeviceId = async (targetFacingMode, currentTrack = null) => {
  const videoInputs = await listVideoInputDevices();
  if (!videoInputs.length) return "";

  const currentDeviceId =
    currentVideoDeviceId.value ||
    currentTrack?.getSettings?.().deviceId ||
    currentTrack?.getConstraints?.().deviceId ||
    "";

  const matchedDevice = videoInputs.find(
    (device) => device.deviceId !== currentDeviceId && isFacingModeMatch(device.label, targetFacingMode)
  );
  if (matchedDevice) return matchedDevice.deviceId;

  const fallbackDevice = videoInputs.find((device) => device.deviceId !== currentDeviceId);
  return fallbackDevice?.deviceId || "";
};

const getNextCameraDevice = async (targetFacingMode, currentTrack = null) => {
  const videoInputs = await listVideoInputDevices();
  if (!videoInputs.length) return { deviceId: "", facingMode: targetFacingMode };

  const currentDeviceId =
    currentVideoDeviceId.value ||
    currentTrack?.getSettings?.().deviceId ||
    currentTrack?.getConstraints?.().deviceId ||
    "";

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
        facingMode: { ideal: targetFacingMode },
      },
    });
  } catch (error) {
    const fallbackDeviceId = await getFallbackCameraDeviceId(targetFacingMode, currentTrack);
    if (!fallbackDeviceId) {
      const nextCamera = await getNextCameraDevice(targetFacingMode, currentTrack);
      if (!nextCamera.deviceId) {
        throw error;
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
    video: needVideo
      ? {
          facingMode: preferredFacingMode.value,
        }
      : false,
  });
  localStream.value = stream;
  currentVideoDeviceId.value = stream.getVideoTracks?.()[0]?.getSettings?.().deviceId || "";
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
      statusMessage.value = "接続中";
    } else if (state === "disconnected" || state === "failed") {
      statusMessage.value = "接続が切れました";
    } else if (state === "closed") {
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
    statusMessage.value = "相手が通話を終了しました";
    stopSignalPolling();
    closePeerConnection();
    resetMedia();
    await refreshCurrentSession();
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
  }, 1500);
};

const joinSession = async (session, { createOffer }) => {
  lastSignalId.value = 0;
  await ensureLocalStream(session.call_type);
  createPeerConnection(session);
  updateVideoBindings();
  currentSession.value = session;
  statusMessage.value = createOffer ? "呼出中" : "接続準備中";
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
  busy.value = true;
  try {
    await api.notifications.declineCall(currentSession.value.id);
    statusMessage.value = "辞退しました";
    stopSignalPolling();
    closePeerConnection();
    resetMedia();
    await loadSessions();
  } catch (error) {
    console.error("辞退失敗", error);
    window.alert(error?.response?.data?.detail || "辞退に失敗しました。");
  } finally {
    busy.value = false;
  }
};

const finishCurrentSession = async () => {
  if (!currentSession.value) return;
  busy.value = true;
  try {
    await api.notifications.finishCall(currentSession.value.id);
    statusMessage.value = "終了しました";
  } catch (error) {
    console.error("終了失敗", error);
    window.alert(error?.response?.data?.detail || "終了に失敗しました。");
  } finally {
    stopSignalPolling();
    closePeerConnection();
    resetMedia();
    await loadSessions();
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
  switchingCamera.value = true;
  const nextFacingMode = preferredFacingMode.value === "environment" ? "user" : "environment";
  const previousFacingMode = preferredFacingMode.value;
  const currentAudioTracks = localStream.value.getAudioTracks();
  const currentVideoTrack = localStream.value.getVideoTracks()[0] || null;

  try {
    preferredFacingMode.value = nextFacingMode;
    const nextCamera = await getNextCameraDevice(preferredFacingMode.value, currentVideoTrack);
    const videoStream = nextCamera.deviceId
      ? await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: {
            deviceId: { exact: nextCamera.deviceId },
          },
        })
      : await openVideoStreamForFacingMode(preferredFacingMode.value, currentVideoTrack);
    const nextVideoTrack = videoStream.getVideoTracks()[0];
    if (!nextVideoTrack) {
      throw new Error("video_track_not_found");
    }
    nextVideoTrack.enabled = cameraEnabled.value;

    const nextStream = new MediaStream([
      ...currentAudioTracks,
      nextVideoTrack,
    ]);

    await replacePeerConnectionTrack("video", nextVideoTrack, currentVideoTrack, nextStream);

    if (currentVideoTrack) {
      localStream.value.removeTrack(currentVideoTrack);
      currentVideoTrack.stop();
    }

    localStream.value = nextStream;
    currentVideoDeviceId.value = nextVideoTrack.getSettings?.().deviceId || nextCamera.deviceId || "";
    updateVideoBindings();
  } catch (error) {
    preferredFacingMode.value = previousFacingMode;
    console.error("カメラ切替失敗", error);
    window.alert("カメラの切替に失敗しました。端末が背面カメラ切替に対応していない可能性があります。");
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
  await reloadAll();
  stopSessionPolling();
  sessionTimerId.value = window.setInterval(async () => {
    await loadSessions();
    if (currentSession.value) {
      await refreshCurrentSession();
    }
  }, 3000);
});

onBeforeUnmount(() => {
  stopSignalPolling();
  stopSessionPolling();
  closePeerConnection();
  resetMedia();
});
</script>

<style scoped>
.call-center-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.page-title {
  margin: 0;
  font-size: 24px;
  color: #10243f;
}

.page-note {
  margin: 4px 0 0;
  color: #5c6b82;
  font-size: 13px;
}

.header-actions,
.action-row,
.control-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.layout {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 16px;
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
  padding: 14px;
  margin-bottom: 14px;
}

.panel-title {
  font-size: 15px;
  font-weight: 700;
  color: #10243f;
  margin-bottom: 10px;
}

.field-label {
  display: block;
  font-size: 12px;
  color: #51627c;
  margin-bottom: 6px;
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
  gap: 8px;
}

.session-card {
  border: 1px solid #d8e0eb;
  border-radius: 10px;
  background: #f7f9fc;
  text-align: left;
  padding: 10px;
  cursor: pointer;
  display: grid;
  gap: 4px;
}

.session-card.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.session-card.incoming {
  border-color: #f59e0b;
  background: #fff7e8;
}

.stage-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e3e8f0;
}

.stage-title {
  font-size: 22px;
  font-weight: 700;
  color: #10243f;
}

.stage-subtitle {
  margin-top: 4px;
  color: #61728a;
  font-size: 13px;
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
  gap: 12px;
  padding: 16px;
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

.video-card.local {
  min-height: 180px;
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
  padding: 0 16px 16px;
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

  .media-grid,
  .media-grid.single {
    grid-template-columns: 1fr;
  }

  .page-header,
  .stage-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
