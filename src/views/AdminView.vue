<template>
  <div class="admin-shell">

    <!-- ─── Sign-in screen ─── -->
    <div v-if="!adminSession" class="admin-login-page">
      <div class="admin-login-card">
        <div class="admin-logo">🏥</div>
        <h1>HHS Admin Portal</h1>
        <p class="admin-subtitle">
          Sign in with your <strong>@hudsonitconsulting.com</strong> Microsoft account
        </p>

        <div v-if="loginError" class="admin-error">
          <span class="error-icon">⚠️</span>
          {{ loginError }}
        </div>

        <button
          class="ms-signin-btn"
          :disabled="isSigningIn"
          @click="signIn"
        >
          <span v-if="isSigningIn" class="spinner" />
          <svg v-else class="ms-logo" viewBox="0 0 21 21" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <rect x="1"  y="1"  width="9" height="9" fill="#f25022"/>
            <rect x="11" y="1"  width="9" height="9" fill="#7fba00"/>
            <rect x="1"  y="11" width="9" height="9" fill="#00a4ef"/>
            <rect x="11" y="11" width="9" height="9" fill="#ffb900"/>
          </svg>
          {{ isSigningIn ? 'Signing in…' : 'Sign in with Microsoft' }}
        </button>

        <RouterLink to="/" class="back-link">← Back to portal</RouterLink>
      </div>
    </div>

    <!-- ─── Admin dashboard ─── -->
    <div v-else class="admin-dashboard">
      <header class="admin-header">
        <div class="admin-header-inner">
          <h1>🏥 HHS Admin</h1>
          <div class="admin-user-info">
            <span class="admin-badge">ADMIN</span>
            <span class="admin-username">{{ adminSession.name || adminSession.email }}</span>
            <button class="admin-logout-btn" @click="signOut">Sign out</button>
          </div>
        </div>
      </header>

      <main class="admin-main">
        <div class="admin-welcome">
          <h2>Welcome, {{ adminSession.name || adminSession.email }}</h2>
          <p class="admin-email">{{ adminSession.email }}</p>
        </div>

        <div class="admin-cards">
          <div class="admin-card">
            <div class="card-icon">👥</div>
            <h3>Users</h3>
            <p>Manage portal users, roles and account status.</p>
            <button class="card-btn" disabled>Coming soon</button>
          </div>
          <div class="admin-card">
            <div class="card-icon">📋</div>
            <h3>Audit Logs</h3>
            <p>View HIPAA audit trail and compliance reports.</p>
            <button class="card-btn" disabled>Coming soon</button>
          </div>
          <div class="admin-card">
            <div class="card-icon">⚙️</div>
            <h3>Settings</h3>
            <p>Configure portal settings and integrations.</p>
            <button class="card-btn" disabled>Coming soon</button>
          </div>
        </div>
      </main>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { msalInstance, loginRequest } from '@/plugins/msal'
import { RouterLink } from 'vue-router'
import type { AuthenticationResult, AccountInfo } from '@azure/msal-browser'

const ALLOWED_DOMAIN = 'hudsonitconsulting.com'
const STORAGE_KEY = 'adminSession'

interface AdminSession {
  email: string
  name: string
  idToken: string
}

const isSigningIn = ref(false)
const loginError = ref('')
const adminSession = ref<AdminSession | null>(null)

function getEmailFromResult(result: AuthenticationResult): string {
  return (
    result.account?.username ??
    (result.idTokenClaims as Record<string, string>)?.email ??
    (result.idTokenClaims as Record<string, string>)?.preferred_username ??
    (result.idTokenClaims as Record<string, string>)?.upn ??
    ''
  ).toLowerCase()
}

function hasAuthCallbackInUrl(): boolean {
  const search = new URLSearchParams(window.location.search)
  if (search.has('code') || search.has('error') || search.has('state') || search.has('session_state')) {
    return true
  }

  const hash = window.location.hash
  return hash.includes('code=') || hash.includes('error=') || hash.includes('state=')
}

function normalizeAdminUrl(): void {
  const target = '/admin'
  if (window.location.pathname !== target || window.location.search || window.location.hash) {
    window.history.replaceState({}, document.title, target)
  }
}

async function clearMsalAccount(account?: AccountInfo): Promise<void> {
  if (!account) {
    return
  }

  await msalInstance.logoutRedirect({
    account,
    postLogoutRedirectUri: `${window.location.origin}/admin`
  }).catch(() => {})
}

async function completeSignIn(result: AuthenticationResult): Promise<boolean> {
  const email = getEmailFromResult(result)

  if (!email.endsWith(`@${ALLOWED_DOMAIN}`)) {
    loginError.value = `Access denied. Only @${ALLOWED_DOMAIN} accounts are allowed.`
    await clearMsalAccount(result.account ?? undefined)
    return false
  }

  const verifyRes = await fetch('/api/admin/verify-token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ idToken: result.idToken })
  })

  if (!verifyRes.ok) {
    const body = await verifyRes.json().catch(() => ({}))
    loginError.value = body.error ?? 'Server rejected the login. Please try again.'
    return false
  }

  const data = await verifyRes.json()
  const session: AdminSession = {
    email: data.email ?? email,
    name: data.name ?? result.account?.name ?? email,
    idToken: result.idToken
  }

  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session))
  adminSession.value = session
  normalizeAdminUrl()
  return true
}

onMounted(async () => {
  loginError.value = ''
  isSigningIn.value = hasAuthCallbackInUrl()

  await msalInstance.initialize()

  try {
    const redirectResult = await msalInstance.handleRedirectPromise()
    if (redirectResult) {
      await completeSignIn(redirectResult)
      isSigningIn.value = false
      return
    }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    loginError.value = msg || 'Unable to process Microsoft callback.'
    normalizeAdminUrl()
    isSigningIn.value = false
    return
  }

  if (hasAuthCallbackInUrl()) {
    loginError.value = 'Unable to complete Microsoft sign-in callback. Please try again.'
    normalizeAdminUrl()
  }

  const stored = sessionStorage.getItem(STORAGE_KEY)
  if (stored) {
    try {
      adminSession.value = JSON.parse(stored) as AdminSession
    } catch {
      sessionStorage.removeItem(STORAGE_KEY)
    }
  }

  isSigningIn.value = false
})

async function signIn() {
  loginError.value = ''
  isSigningIn.value = true

  try {
    await msalInstance.loginRedirect(loginRequest)
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    loginError.value = msg || 'Sign-in failed. Please try again.'
    console.error('[AdminView] MSAL error:', err)
    isSigningIn.value = false
  }
}

async function signOut() {
  sessionStorage.removeItem(STORAGE_KEY)
  adminSession.value = null

  const accounts = msalInstance.getAllAccounts()
  if (accounts.length > 0) {
    await msalInstance.logoutRedirect({
      account: accounts[0],
      postLogoutRedirectUri: `${window.location.origin}/admin`
    }).catch(() => {})
  }
}
</script>

<style scoped>
/* ── Shell ───────────────────────────────────────────────────────────────── */
.admin-shell {
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f0f4f8;
}

/* ── Login page ──────────────────────────────────────────────────────────── */
.admin-login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e3a5f 0%, #0f6cbd 100%);
}

.admin-login-card {
  background: #fff;
  border-radius: 12px;
  padding: 48px 40px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
  text-align: center;
}

.admin-logo {
  font-size: 48px;
  margin-bottom: 12px;
}

.admin-login-card h1 {
  font-size: 24px;
  font-weight: 700;
  color: #1e3a5f;
  margin: 0 0 8px;
}

.admin-subtitle {
  color: #6b7280;
  font-size: 14px;
  margin: 0 0 28px;
  line-height: 1.5;
}

.admin-error {
  background: #fff0f0;
  border: 1px solid #fca5a5;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 20px;
  font-size: 14px;
  color: #b91c1c;
  text-align: left;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.error-icon {
  flex-shrink: 0;
}

/* Microsoft sign-in button — follows Microsoft brand guidelines */
.ms-signin-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  width: 100%;
  padding: 12px 20px;
  background: #fff;
  border: 1px solid #8c8c8c;
  border-radius: 4px;
  font-size: 15px;
  font-weight: 600;
  color: #5e5e5e;
  cursor: pointer;
  transition: background 0.15s, box-shadow 0.15s;
}

.ms-signin-btn:hover:not(:disabled) {
  background: #f3f3f3;
  box-shadow: 0 2px 6px rgba(0,0,0,0.12);
}

.ms-signin-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.ms-logo {
  width: 21px;
  height: 21px;
  flex-shrink: 0;
}

.spinner {
  display: inline-block;
  width: 18px;
  height: 18px;
  border: 2px solid #ccc;
  border-top-color: #0f6cbd;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.back-link {
  display: inline-block;
  margin-top: 24px;
  font-size: 13px;
  color: #6b7280;
  text-decoration: none;
}

.back-link:hover {
  color: #0f6cbd;
  text-decoration: underline;
}

/* ── Admin dashboard ─────────────────────────────────────────────────────── */
.admin-dashboard {
  min-height: 100vh;
}

.admin-header {
  background: linear-gradient(90deg, #1e3a5f 0%, #0f6cbd 100%);
  padding: 0 24px;
}

.admin-header-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
}

.admin-header h1 {
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  margin: 0;
}

.admin-user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.admin-badge {
  background: rgba(255,255,255,0.2);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  padding: 3px 8px;
  border-radius: 4px;
}

.admin-username {
  color: #e2e8f0;
  font-size: 14px;
}

.admin-logout-btn {
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.3);
  color: #fff;
  border-radius: 6px;
  padding: 6px 14px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
}

.admin-logout-btn:hover {
  background: rgba(255,255,255,0.25);
}

.admin-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 24px;
}

.admin-welcome {
  margin-bottom: 36px;
}

.admin-welcome h2 {
  font-size: 26px;
  font-weight: 700;
  color: #1e3a5f;
  margin: 0 0 4px;
}

.admin-email {
  color: #6b7280;
  font-size: 14px;
  margin: 0;
}

.admin-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 24px;
}

.admin-card {
  background: #fff;
  border-radius: 12px;
  padding: 28px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-icon {
  font-size: 32px;
}

.admin-card h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1e3a5f;
  margin: 0;
}

.admin-card p {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
  flex: 1;
}

.card-btn {
  margin-top: 12px;
  padding: 8px 16px;
  background: #e5e7eb;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  color: #9ca3af;
  cursor: not-allowed;
  align-self: flex-start;
}
</style>
