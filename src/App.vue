<template>
  <div id="app">
    <header v-if="showHeader" class="top-header">
      <div class="header-content">
        <h1>🏥 {{ pageTitle }}</h1>
        <div class="user-actions">
          <RouterLink
            v-for="button in navButtons"
            :key="button.to"
            :to="button.to"
            class="header-btn"
          >
            {{ button.label }}
          </RouterLink>
          <button
            v-if="showFeatureRequestButton"
            @click="openFeatureRequestModal"
            class="feature-request-btn"
          >
            FEATURE REQUEST
          </button>
          <span class="user-name">{{ userName }}</span>
          <button @click="handleLogout" class="logout-btn">Logout</button>
        </div>
      </div>
    </header>
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
import { computed, ref, watch, onMounted } from 'vue'
import { RouterView, RouterLink, useRoute, useRouter } from 'vue-router'
import { logout } from '@/store'

type NavButton = {
  label: string
  to: string
}

const route = useRoute()
const router = useRouter()
const currentUser = ref<{ name?: string; username?: string; role?: string } | null>(null)
const showFeatureRequestModal = ref(false)
const featureRequestDescription = ref('')
const featureRequestError = ref('')
const featureRequestSuccess = ref(false)
const featureRequestIssueUrl = ref('')
const featureRequestIssueNumber = ref(0)
const isSubmittingFeatureRequest = ref(false)

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
  // Show header for all authenticated routes
  return !!currentUser.value && route.path !== '/'
})

const userName = computed(() => {
  if (!currentUser.value) return ''
  return currentUser.value.name || currentUser.value.username || ''
})

const pageTitle = computed(() => {
  if (route.path.startsWith('/profile')) return 'My Profile'
  if (route.path.startsWith('/patients')) return 'Patients'
  if (route.path.startsWith('/doctor')) return 'Doctor Dashboard'
  if (route.path.startsWith('/patient')) return 'Patient Dashboard'
  return 'Hudson Health System'
})

const navButtons = computed<NavButton[]>(() => {
  if (!currentUser.value) return []
  if (currentUser.value.role === 'doctor') {
    return [
      { label: 'Home', to: '/doctor' },
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

function getFeatureRequestPage(): string {
  if (globalThis.window !== undefined) {
    return `${globalThis.window.location.pathname}${globalThis.window.location.search}${globalThis.window.location.hash}`
  }
  return '/doctor'
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
        title: 'Doctor Feature Request',
        description,
        page: featureRequestPage.value,
        route_name: String(route.name || 'DoctorDashboard')
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
  logout()
  localStorage.removeItem('sessionToken')
  localStorage.removeItem('currentUser')
  currentUser.value = null
  router.push('/')
}

onMounted(() => {
  loadUser()
})

watch(
  () => route.fullPath,
  () => {
    loadUser()
  }
)
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background-color: #f5f5f5;
  color: #333;
}

#app {
  min-height: 100vh;
}

.top-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-content h1 {
  margin: 0;
  font-size: 1.4rem;
}

.user-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.user-name {
  font-weight: 600;
}

.header-btn {
  padding: 0.5rem 1rem;
  background: rgba(255,255,255,0.2);
  color: white;
  border: 1px solid white;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
  text-decoration: none;
}

.header-btn:hover {
  background: rgba(255,255,255,0.3);
}

.header-btn.router-link-active {
  background: rgba(255,255,255,0.35);
  font-weight: 700;
}

.logout-btn {
  padding: 0.5rem 1rem;
  background: rgba(255,255,255,0.2);
  color: white;
  border: 1px solid white;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
}

.logout-btn:hover {
  background: rgba(255,255,255,0.3);
}

.feature-request-btn {
  padding: 0.5rem 0.85rem;
  background: #ffffff;
  color: #4c1d95;
  border: 1px solid #c4b5fd;
  border-radius: 999px;
  font-weight: 700;
  font-size: 0.78rem;
  letter-spacing: 0.05em;
  transition: all 0.2s;
}

.feature-request-btn:hover {
  background: #e9d5ff;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
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
</style>
