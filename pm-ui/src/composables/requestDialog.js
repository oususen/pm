import { ref } from 'vue'

export const requestDialogOpen = ref(false)

export const openRequestDialog = () => {
  requestDialogOpen.value = true
}

export const closeRequestDialog = () => {
  requestDialogOpen.value = false
}
