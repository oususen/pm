import { ref } from 'vue'

export const aiDrawerOpen = ref(false)
export const aiDrawerCollapsed = ref(false)
export const aiDrawerSourcePath = ref('')

export const openAIDrawer = (path) => {
  aiDrawerSourcePath.value = String(path || '')
  aiDrawerOpen.value = true
  aiDrawerCollapsed.value = false
}

export const collapseAIDrawer = () => {
  aiDrawerCollapsed.value = true
}

export const closeAIDrawer = () => {
  aiDrawerOpen.value = false
  aiDrawerCollapsed.value = false
}
