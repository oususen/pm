import { ref } from 'vue'

export const requestDialogOpen = ref(false)
export const requestDialogInitialValues = ref({ subject: '', body: '', requestType: 'request' })

export const openRequestDialog = (initialValues = {}) => {
  requestDialogInitialValues.value = {
    subject: typeof initialValues.subject === 'string' ? initialValues.subject : '',
    body: typeof initialValues.body === 'string' ? initialValues.body : '',
    requestType: typeof initialValues.requestType === 'string' ? initialValues.requestType : 'request',
  }
  requestDialogOpen.value = true
}

export const closeRequestDialog = () => {
  requestDialogOpen.value = false
  requestDialogInitialValues.value = { subject: '', body: '', requestType: 'request' }
}

export const requestHistoryOpen = ref(false)

export const openRequestHistory = () => {
  requestHistoryOpen.value = true
}

export const closeRequestHistory = () => {
  requestHistoryOpen.value = false
}
