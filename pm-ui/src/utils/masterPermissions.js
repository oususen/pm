import { authState } from '@/auth'
import { hasPermission } from '@/router'

export const canAccessMasterResource = (resource, level = 'view') => {
  const user = authState.user
  if (!user || !resource) return false
  if (user.is_superuser) return true

  const permissions = Array.isArray(user.effective_permissions)
    ? user.effective_permissions
    : []

  if (permissions.some((item) => item.resource === resource)) {
    return hasPermission(user, resource, level)
  }
  return hasPermission(user, 'masters', level)
}
