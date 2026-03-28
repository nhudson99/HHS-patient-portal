/**
 * Microsoft Authentication Library (MSAL) configuration
 * Used exclusively for /admin SSO login via hudsonitconsulting.com Azure AD tenant.
 *
 * Required env vars (set in .env, injected via Vite):
 *   VITE_AZURE_CLIENT_ID  – App (client) ID from Azure Portal
 *   VITE_AZURE_TENANT_ID  – Directory (tenant) ID from Azure Portal
 */

import { PublicClientApplication, type Configuration } from '@azure/msal-browser'

const clientId = (import.meta.env.VITE_AZURE_CLIENT_ID as string | undefined)?.trim() || ''
const tenantId = (import.meta.env.VITE_AZURE_TENANT_ID as string | undefined)?.trim() || ''
const configuredRedirectUri = (import.meta.env.VITE_AZURE_REDIRECT_URI as string | undefined)?.trim()

const resolveRedirectUri = (): string => {
  const runtimeAdminUrl = `${globalThis.location.origin}/admin`

  if (!configuredRedirectUri) {
    return runtimeAdminUrl
  }

  try {
    const parsedUrl = new URL(configuredRedirectUri)
    const runtimeOrigin = globalThis.location.origin

    // Safety: never redirect across origins from the currently loaded app.
    // This prevents local testing from jumping to production when dist was built
    // with a production VITE_AZURE_REDIRECT_URI.
    if (parsedUrl.origin !== runtimeOrigin) {
      return runtimeAdminUrl
    }

    return parsedUrl.toString()
  } catch {
    return runtimeAdminUrl
  }
}

const redirectUri = resolveRedirectUri()

if (!clientId || !tenantId) {
  console.warn(
    '[msal] VITE_AZURE_CLIENT_ID or VITE_AZURE_TENANT_ID not set. ' +
    'Admin SSO will not function until these are configured.'
  )
}

const msalConfig: Configuration = {
  auth: {
    clientId: clientId || 'MISSING_CLIENT_ID',
    authority: `https://login.microsoftonline.com/${tenantId || 'common'}`,
    redirectUri
  },
  cache: {
    cacheLocation: 'sessionStorage'
  }
}

// Singleton MSAL instance — shared across the admin views
export const msalInstance = new PublicClientApplication(msalConfig)

// Scopes requested — openid/profile/email are enough to verify the domain
export const loginRequest = {
  scopes: ['openid', 'profile', 'email']
}
