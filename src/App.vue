<template>
  <div id="app">
    <header v-if="showHeader" class="top-header">
      <div class="header-content">
        <div class="header-left">
          <button
            v-if="navButtons.length > 0"
            class="hamburger-btn"
            aria-label="Open navigation menu"
            @click="toggleSidebar"
          >
            ☰
          </button>
          <h1>🏥 {{ pageTitle }}</h1>
        </div>
        <div class="user-actions">
          <button
            v-if="showFeatureRequestButton"
            @click="openFeatureRequestModal"
            class="feature-request-btn"
          >
            FEATURE REQUEST
          </button>
          <span v-if="adminSession" class="admin-role-badge">ADMIN</span>
          <span class="user-name">{{ userName }}</span>
          <div
            v-if="isProviderUser"
            ref="providerNotificationRef"
            class="provider-notification-wrapper"
          >
            <button
              class="notification-btn"
              :aria-expanded="showProviderNotifications"
              aria-haspopup="menu"
              aria-label="Provider alerts"
              @click="toggleProviderNotifications"
            >
              <span class="notification-icon" aria-hidden="true">🔔</span>
              <span
                v-if="unreadProviderAlertCount > 0"
                class="notification-badge"
              >
                {{ unreadProviderAlertCount }}
              </span>
            </button>
            <div v-if="showProviderNotifications" class="notification-dropdown">
              <div class="notification-dropdown-header">Alerts</div>
              <div v-if="providerAlertLoadError" class="notification-status error">
                {{ providerAlertLoadError }}
              </div>
              <div v-else-if="providerAlerts.length === 0" class="notification-status">
                No alerts right now.
              </div>
              <ul v-else class="notification-list">
                <li
                  v-for="alert in providerAlerts"
                  :key="alert.id"
                  class="notification-item"
                >
                  <div class="notification-title">{{ alert.title }}</div>
                  <div class="notification-meta">
                    {{ alert.patientName }} • {{ formatAlertDateTime(alert.eventDate, alert.startTime) }}
                  </div>
                </li>
              </ul>
            </div>
          </div>
          <button @click="handleLogout" class="logout-btn">Logout</button>
        </div>
      </div>
    </header>
    <div
      v-if="showHeader && showSidebar && navButtons.length > 0"
      class="sidebar-overlay"
      @click="closeSidebar"
    ></div>
    <aside
      v-if="showHeader && showSidebar && navButtons.length > 0"
      class="app-sidebar"
      aria-label="Application navigation"
    >
      <nav class="sidebar-nav">
        <RouterLink
          v-for="button in navButtons"
          :key="button.to"
          :to="button.to"
          class="sidebar-link"
          @click="closeSidebar"
        >
          {{ button.label }}
        </RouterLink>
      </nav>
    </aside>
    <div v-if="showFeatureRequestModal" class="modal-overlay" @click="closeFeatureRequestModal">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h2>Submit Feature Request</h2>
          <button @click="closeFeatureRequestModal" class="close-btn">✕</button>
        </div>
        <div class="modal-content">
          <div class="form-group">
            <label for="feature-request-description">Description</label>
            <p class="feature-request-help">Describe what you need and why — a GitHub issue will be created for the dev team to review.</p>
            <textarea
              id="feature-request-description"
              v-model="featureRequestDescription"
              class="feature-request-textarea"
              placeholder="Describe the problem, desired behavior, and who it helps..."
            ></textarea>
          </div>

          <div class="feature-request-page">Page: {{ featureRequestPage }}</div>

          <div v-if="featureRequestError" class="feature-request-error">
            {{ featureRequestError }}
          </div>
          <div v-if="featureRequestSuccess" class="feature-request-success">
            <span>Issue created — </span>
            <a :href="featureRequestIssueUrl" target="_blank" rel="noopener" class="feature-request-issue-link">
              #{{ featureRequestIssueNumber }}: view on GitHub →
            </a>
          </div>

          <div class="modal-actions">
            <button class="btn-primary" @click="submitFeatureRequest" :disabled="isSubmittingFeatureRequest">
              {{ isSubmittingFeatureRequest ? 'Submitting...' : 'Submit Request' }}
            </button>
            <button class="btn-secondary" @click="closeFeatureRequestModal" :disabled="isSubmittingFeatureRequest">
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
    <RouterView />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { RouterView, RouterLink, useRoute, useRouter } from 'vue-router'
import { logout, adminSession, clearAdminSession } from '@/store'

type NavButton = {
  label: string
  to: string
}

type ProviderAlert = {
  id: string
  title: string
  patientName: string
  eventDate: string
  startTime: string
}

type ProviderAlertEventRow = {
  id?: string
  event_type?: string
  appointment_status?: string
  patient_name?: string
  event_date?: string
  start_time?: string
}

const route = useRoute()
const router = useRouter()
const currentUser = ref<{ name?: string; username?: string; role?: string } | null>(null)
const showSidebar = ref(false)
const showFeatureRequestModal = ref(false)
const featureRequestDescription = ref('')
const featureRequestError = ref('')
const featureRequestSuccess = ref(false)
const featureRequestIssueUrl = ref('')
const featureRequestIssueNumber = ref(0)
const isSubmittingFeatureRequest = ref(false)
const showProviderNotifications = ref(false)
const providerNotificationRef = ref<HTMLElement | null>(null)
const providerAlerts = ref<ProviderAlert[]>([])
const providerAlertLoadError = ref('')
const readProviderAlertIds = ref<Set<string>>(new Set())
let providerAlertIntervalId: ReturnType<typeof globalThis.setInterval> | null = null

const PROVIDER_ALERT_LOOKAHEAD_DAYS = 14
const PROVIDER_ALERT_REFRESH_MS = 60000

const loadUser = () => {
  const userStr = localStorage.getItem('currentUser')
  if (!userStr) {
    currentUser.value = null
    return
  }

  try {
    currentUser.value = JSON.parse(userStr)
  } catch {
    currentUser.value = null
  }
}

const showHeader = computed(() => {
  // Show header for all authenticated routes (portal or admin)
  return (!!currentUser.value || !!adminSession.value) && route.path !== '/'
})

const userName = computed(() => {
  if (adminSession.value) return adminSession.value.name || adminSession.value.email
  if (!currentUser.value) return ''
  return currentUser.value.name || currentUser.value.username || ''
})

const pageTitle = computed(() => {
  if (adminSession.value) return 'HHS Admin'
  if (route.path.startsWith('/profile')) return 'My Profile'
  if (route.path.startsWith('/patients')) return 'Patients'
  if (route.path.startsWith('/provider') || route.path.startsWith('/doctor')) return 'Provider Dashboard'
  if (route.path.startsWith('/patient')) return 'Patient Dashboard'
  return 'Hudson Health System'
})

const navButtons = computed<NavButton[]>(() => {
  if (adminSession.value) return []
  if (!currentUser.value) return []
  if (currentUser.value.role === 'doctor') {
    return [
      { label: 'Home', to: '/provider' },
      { label: 'Patients', to: '/patients' },
      { label: 'Profile', to: '/profile' }
    ]
  }
  if (currentUser.value.role === 'patient') {
    return [
      { label: 'Home', to: '/patient' },
      { label: 'Check In', to: '/checkin' },
      { label: 'Profile', to: '/profile' }
    ]
  }
  return []
})

const showFeatureRequestButton = computed(() => {
  return !!currentUser.value && currentUser.value.role === 'doctor' && showHeader.value
})

const isProviderUser = computed(() => {
  return !!currentUser.value && currentUser.value.role === 'doctor' && !adminSession.value
})

const unreadProviderAlertCount = computed(() => {
  return providerAlerts.value.filter((alert) => !readProviderAlertIds.value.has(alert.id)).length
})

function getProviderAlertStorageKey(): string {
  const user = currentUser.value
  if (!user) {
    return ''
  }
  const identifier = user.username || user.name || 'provider'
  return `providerReadAlerts:${identifier}`
}

function loadReadProviderAlertIds() {
  const storageKey = getProviderAlertStorageKey()
  if (!storageKey) {
    readProviderAlertIds.value = new Set()
    return
  }

  const raw = localStorage.getItem(storageKey)
  if (!raw) {
    readProviderAlertIds.value = new Set()
    return
  }

  try {
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed)) {
      readProviderAlertIds.value = new Set(parsed.filter((id) => typeof id === 'string'))
      return
    }
    readProviderAlertIds.value = new Set()
  } catch {
    readProviderAlertIds.value = new Set()
  }
}

function saveReadProviderAlertIds() {
  const storageKey = getProviderAlertStorageKey()
  if (!storageKey) {
    return
  }
  localStorage.setItem(storageKey, JSON.stringify(Array.from(readProviderAlertIds.value)))
}

function formatDateForApi(date: Date): string {
  return date.toISOString().slice(0, 10)
}

function formatAlertDateTime(eventDate: string, startTime: string): string {
  if (!startTime) {
    return eventDate
  }
  const [hourValue, minuteValue] = startTime.split(':')
  const hour = Number.parseInt(hourValue, 10)
  const minute = Number.parseInt(minuteValue, 10)
  if (Number.isNaN(hour) || Number.isNaN(minute)) {
    return `${eventDate} ${startTime}`
  }
  const suffix = hour >= 12 ? 'PM' : 'AM'
  const normalizedHour = hour % 12 === 0 ? 12 : hour % 12
  const normalizedMinute = minute.toString().padStart(2, '0')
  return `${eventDate} ${normalizedHour}:${normalizedMinute} ${suffix}`
}

function stopProviderAlertPolling() {
  if (providerAlertIntervalId !== null) {
    globalThis.clearInterval(providerAlertIntervalId)
    providerAlertIntervalId = null
  }
}

function startProviderAlertPolling() {
  stopProviderAlertPolling()
  providerAlertIntervalId = globalThis.setInterval(() => {
    loadProviderAlerts()
  }, PROVIDER_ALERT_REFRESH_MS)
}

function markProviderAlertsAsRead() {
  if (providerAlerts.value.length === 0) {
    return
  }
  const updatedReadIds = new Set(readProviderAlertIds.value)
  for (const alert of providerAlerts.value) {
    updatedReadIds.add(alert.id)
  }
  readProviderAlertIds.value = updatedReadIds
  saveReadProviderAlertIds()
}

function toggleProviderNotifications() {
  showProviderNotifications.value = !showProviderNotifications.value
  if (showProviderNotifications.value) {
    markProviderAlertsAsRead()
  }
}

function closeProviderNotifications() {
  showProviderNotifications.value = false
}

function handleClickOutsideNotifications(event: MouseEvent) {
  const target = event.target as Node | null
  if (!target || !providerNotificationRef.value) {
    return
  }
  if (!providerNotificationRef.value.contains(target)) {
    closeProviderNotifications()
  }
}

async function loadProviderAlerts() {
  if (!isProviderUser.value) {
    providerAlerts.value = []
    providerAlertLoadError.value = ''
    return
  }

  providerAlertLoadError.value = ''
  const startDate = new Date()
  const endDate = new Date()
  endDate.setDate(endDate.getDate() + PROVIDER_ALERT_LOOKAHEAD_DAYS)

  try {
    const response = await fetch(
      `/api/events?start_date=${formatDateForApi(startDate)}&end_date=${formatDateForApi(endDate)}`,
      {
        headers: {
          Authorization: `******'sessionToken')}`,
        },
      }
    )

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      providerAlertLoadError.value = data.error || 'Unable to load alerts'
      return
    }

    const data = await response.json()
    const eventRows: ProviderAlertEventRow[] = Array.isArray(data.events) ? data.events : []
    providerAlerts.value = eventRows
      .filter((event) => event.event_type === 'appointment' && event.appointment_status === 'pending')
      .map((event) => ({
        id: String(event.id || ''),
        title: 'Pending appointment request',
        patientName: event.patient_name || 'Patient',
        eventDate: String(event.event_date || ''),
        startTime: String(event.start_time || ''),
      }))
      .filter((event) => event.id.length > 0)
      .sort((left, right) => {
        const leftStamp = `${left.eventDate} ${left.startTime}`
        const rightStamp = `${right.eventDate} ${right.startTime}`
        return leftStamp.localeCompare(rightStamp)
      })
  } catch (error) {
    console.error('Provider alert loading error:', error)
    providerAlertLoadError.value = 'Unable to load alerts'
  }
}

function getFeatureRequestPage(): string {
  if (globalThis.window !== undefined) {
    return `${globalThis.window.location.pathname}${globalThis.window.location.search}${globalThis.window.location.hash}`
  }
  return '/provider'
}

const featureRequestPage = ref(getFeatureRequestPage())

function openFeatureRequestModal() {
  featureRequestPage.value = getFeatureRequestPage()
  featureRequestError.value = ''
  featureRequestSuccess.value = false
  featureRequestIssueUrl.value = ''
  featureRequestIssueNumber.value = 0
  showFeatureRequestModal.value = true
}

function closeFeatureRequestModal() {
  if (isSubmittingFeatureRequest.value) return
  showFeatureRequestModal.value = false
}

function toggleSidebar() {
  showSidebar.value = !showSidebar.value
}

function closeSidebar() {
  showSidebar.value = false
}

async function submitFeatureRequest() {
  featureRequestError.value = ''
  featureRequestSuccess.value = false

  const description = featureRequestDescription.value.trim()
  if (description.length < 10) {
    featureRequestError.value = 'Please provide at least 10 characters so engineering can action this request.'
    return
  }

  isSubmittingFeatureRequest.value = true

  try {
    const response = await fetch('/api/feature-requests', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      },
      body: JSON.stringify({
        title: 'Provider Feature Request',
        description,
        page: featureRequestPage.value,
        route_name: String(route.name || 'ProviderDashboard')
      })
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
      featureRequestError.value = data.error || 'Unable to submit request right now.'
      return
    }

    featureRequestIssueUrl.value = data.issue?.url || ''
    featureRequestIssueNumber.value = data.issue?.number || 0
    featureRequestSuccess.value = true
    featureRequestDescription.value = ''
  } catch (error) {
    console.error('Feature request submission error:', error)
    featureRequestError.value = 'Network error while submitting request.'
  } finally {
    isSubmittingFeatureRequest.value = false
  }
}

const handleLogout = () => {
  if (adminSession.value) {
    clearAdminSession()
    router.push('/admin')
    return
  }
  logout()
  currentUser.value = null
  router.push('/')
}

onMounted(() => {
  loadUser()
  loadReadProviderAlertIds()
  if (isProviderUser.value) {
    loadProviderAlerts()
    startProviderAlertPolling()
  }
  globalThis.document.addEventListener('click', handleClickOutsideNotifications)
})

watch(
  () => route.fullPath,
  () => {
    closeSidebar()
    closeProviderNotifications()
    loadUser()
    loadReadProviderAlertIds()
    if (isProviderUser.value) {
      loadProviderAlerts()
    }
  }
)

watch(
  isProviderUser,
  (isProvider) => {
    closeProviderNotifications()
    if (isProvider) {
      loadReadProviderAlertIds()
      loadProviderAlerts()
      startProviderAlertPolling()
      return
    }
    stopProviderAlertPolling()
    providerAlerts.value = []
    providerAlertLoadError.value = ''
  },
  { immediate: false }
)

onBeforeUnmount(() => {
  stopProviderAlertPolling()
  globalThis.document.removeEventListener('click', handleClickOutsideNotifications)
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background-color: #f0f4f8;
  color: #111827;
}

#app {
  min-height: 100vh;
}

.top-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: #1a3a5c;
  color: white;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0.75rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.header-content h1 {
  margin: 0;
  font-size: 1.4rem;
}

.hamburger-btn {
  width: 2.2rem;
  height: 2.2rem;
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 6px;
  background: transparent;
  color: #fff;
  font-size: 1.1rem;
  line-height: 1;
  transition: background 0.2s;
}

.hamburger-btn:hover {
  background: rgba(255, 255, 255, 0.12);
}

.user-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.user-name {
  font-weight: 600;
}

.app-sidebar {
  position: fixed;
  top: 0;
  left: 0;
  z-index: 2200;
  width: 280px;
  max-width: 80vw;
  height: 100vh;
  background: #0f2740;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  padding: 4.5rem 1rem 1rem;
}

.sidebar-overlay {
  position: fixed;
  inset: 0;
  z-index: 2100;
  background: rgba(0, 0, 0, 0.45);
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.sidebar-link {
  display: block;
  padding: 0.7rem 0.85rem;
  color: rgba(255, 255, 255, 0.9);
  text-decoration: none;
  border-radius: 6px;
  border: 1px solid transparent;
}

.sidebar-link:hover {
  background: rgba(255, 255, 255, 0.12);
}

.sidebar-link.router-link-active {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.35);
  font-weight: 600;
}

.logout-btn {
  padding: 0.45rem 1rem;
  background: transparent;
  color: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.2s, color 0.2s;
}

.logout-btn:hover {
  background: rgba(239, 68, 68, 0.25);
  border-color: rgba(239, 68, 68, 0.6);
  color: #fff;
}

.provider-notification-wrapper {
  position: relative;
}

.notification-btn {
  position: relative;
  width: 2.25rem;
  height: 2.25rem;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 999px;
  color: rgba(255, 255, 255, 0.9);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, border-color 0.2s;
}

.notification-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.5);
}

.notification-icon {
  font-size: 1rem;
  line-height: 1;
}

.notification-badge {
  position: absolute;
  top: -0.3rem;
  right: -0.35rem;
  min-width: 1.2rem;
  height: 1.2rem;
  padding: 0 0.25rem;
  border-radius: 999px;
  background: #ef4444;
  color: #fff;
  font-size: 0.72rem;
  font-weight: 700;
  line-height: 1.2rem;
  text-align: center;
}

.notification-dropdown {
  position: absolute;
  top: calc(100% + 0.5rem);
  right: 0;
  width: min(320px, 80vw);
  max-height: 360px;
  overflow-y: auto;
  background: #fff;
  color: #111827;
  border-radius: 8px;
  border: 1px solid #d1d5db;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.22);
  z-index: 3000;
}

.notification-dropdown-header {
  padding: 0.7rem 0.9rem;
  border-bottom: 1px solid #e5e7eb;
  font-size: 0.95rem;
  font-weight: 700;
}

.notification-status {
  padding: 0.8rem 0.9rem;
  font-size: 0.9rem;
  color: #374151;
}

.notification-status.error {
  color: #b91c1c;
}

.notification-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.notification-item {
  padding: 0.75rem 0.9rem;
  border-top: 1px solid #f3f4f6;
}

.notification-title {
  font-weight: 600;
  font-size: 0.88rem;
  color: #111827;
}

.notification-meta {
  margin-top: 0.25rem;
  color: #4b5563;
  font-size: 0.8rem;
}

.admin-role-badge {
  background: #ef4444;
  color: #fff;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  padding: 2px 8px;
  border-radius: 4px;
}

.feature-request-btn {
  padding: 0.4rem 0.9rem;
  background: transparent;
  color: rgba(255, 255, 255, 0.85);
  border: 1px dashed rgba(255, 255, 255, 0.4);
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.78rem;
  letter-spacing: 0.04em;
  transition: background 0.2s;
}

.feature-request-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 3000;
}

.modal {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 560px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #ddd;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.25rem;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
}

.modal-content {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.feature-request-help {
  margin: 0 0 0.4rem;
  color: #6b7280;
  font-size: 0.9rem;
}

.feature-request-textarea {
  width: 100%;
  min-height: 140px;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.feature-request-page {
  margin-top: 0.5rem;
  color: #6b7280;
  font-size: 0.85rem;
}

.feature-request-error {
  margin-top: 0.9rem;
  padding: 0.65rem 0.8rem;
  border-radius: 6px;
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
  font-size: 0.9rem;
}

.feature-request-success {
  margin-top: 0.9rem;
  padding: 0.65rem 0.8rem;
  border-radius: 6px;
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
  font-size: 0.9rem;
}

.feature-request-issue-link {
  color: #065f46;
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #ddd;
}

.btn-primary,
.btn-secondary {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
}

.btn-primary {
  background: #4f46e5;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #4338ca;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #5a6268;
}

.btn-primary:disabled,
.btn-secondary:disabled {
  background: #334155;
  color: #e2e8f0;
  cursor: not-allowed;
}

button {
  cursor: pointer;
  font-family: inherit;
}

input, select, textarea {
  font-family: inherit;
}

@media (max-width: 880px) {
  .header-content {
    padding: 0.75rem 1rem;
  }

  .header-content h1 {
    font-size: 1.05rem;
  }

  .user-actions {
    gap: 0.4rem;
    flex-wrap: wrap;
    justify-content: flex-end;
  }
}
</style>
