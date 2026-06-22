export const CALL_RECORDING_ALLOWED_USERS_KEY = "notifications.call_recording_allowed_usernames"

export const parseAllowedRecordingUsernames = (value) => {
  return String(value || "")
    .split(/[\s,]+/)
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean)
}

export const serializeAllowedRecordingUsernames = (usernames) => {
  return [...new Set((Array.isArray(usernames) ? usernames : [])
    .map((item) => String(item || "").trim().toLowerCase())
    .filter(Boolean))]
    .join(",")
}
