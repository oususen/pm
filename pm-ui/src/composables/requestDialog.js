import { ref } from 'vue'

export const requestDialogOpen = ref(false)

export const openRequestDialog = () => {
  requestDialogOpen.value = true
}

export const closeRequestDialog = () => {
  requestDialogOpen.value = false
}

export const requestHistoryOpen = ref(false)

export const openRequestHistory = () => {
  requestHistoryOpen.value = true
}

export const closeRequestHistory = () => {
  requestHistoryOpen.value = false
}
