export const getPortalLoginUrl = () => {
  const portalUrl = import.meta.env.VITE_PORTAL_URL || 'http://localhost:3002'
  return `${portalUrl}/login`
}
