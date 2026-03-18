<template>
  <div class="profile-page">
    <div class="profile-layout">
      <section class="profile-card account-card">
        <p class="eyebrow">Account</p>
        <h2>My Profile</h2>
        <p class="description">
          Review your account details and update your password any time.
        </p>

        <div class="account-grid">
          <div class="account-item">
            <span class="label">Username</span>
            <span class="value">{{ currentUser?.username || '—' }}</span>
          </div>
          <div class="account-item">
            <span class="label">Email</span>
            <span class="value">{{ currentUser?.email || '—' }}</span>
          </div>
          <div class="account-item">
            <span class="label">Role</span>
            <span class="value role-pill">{{ formattedRole }}</span>
          </div>
        </div>
      </section>

      <section class="profile-card password-card">
        <div class="card-header">
          <div>
            <p class="eyebrow">Security</p>
            <h3>Change Password</h3>
          </div>
          <RouterLink :to="homeRoute" class="back-link">Back to Home</RouterLink>
        </div>

        <div v-if="isForcedPasswordChange" class="info-banner">
          You signed in with a temporary password. Set a new password to continue.
        </div>

        <form class="password-form" @submit.prevent="handlePasswordChange">
          <div class="form-group">
            <label for="currentPassword">Current Password</label>
            <input
              id="currentPassword"
              v-model="form.currentPassword"
              type="password"
              autocomplete="current-password"
              required
            />
          </div>

          <div class="form-group">
            <label for="newPassword">New Password</label>
            <input
              id="newPassword"
              v-model="form.newPassword"
              type="password"
              autocomplete="new-password"
              minlength="8"
              required
            />
            <p class="field-help">Use at least 8 characters.</p>
          </div>

          <div class="form-group">
            <label for="confirmPassword">Confirm New Password</label>
            <input
              id="confirmPassword"
              v-model="form.confirmPassword"
              type="password"
              autocomplete="new-password"
              minlength="8"
              required
            />
          </div>

          <div v-if="errorMessage" class="message error-message">{{ errorMessage }}</div>
          <div v-if="successMessage" class="message success-message">{{ successMessage }}</div>

          <div class="form-actions">
            <button type="submit" class="primary-btn" :disabled="isSubmitting">
              {{ isSubmitting ? 'Saving...' : 'Update Password' }}
            </button>
          </div>
        </form>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { authApi } from '@/api'

type StoredUser = {
  id?: string | number
  username?: string
  email?: string
  role?: 'doctor' | 'patient' | string
}

const route = useRoute()
const router = useRouter()

const storedUser = localStorage.getItem('currentUser')
let parsedUser: StoredUser | null = null

if (storedUser) {
  try {
    parsedUser = JSON.parse(storedUser) as StoredUser
  } catch {
    parsedUser = null
  }
}

const currentUser = computed(() => parsedUser)
const formattedRole = computed(() => {
  const role = currentUser.value?.role
  if (!role) return 'Unknown'
  return role.charAt(0).toUpperCase() + role.slice(1)
})
const homeRoute = computed(() => currentUser.value?.role === 'doctor' ? '/doctor' : '/patient')
const isForcedPasswordChange = computed(() => route.query.password === 'required')

const form = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const errorMessage = computed(() => state.errorMessage)
const successMessage = computed(() => state.successMessage)

const state = reactive({
  isSubmitting: false,
  errorMessage: '',
  successMessage: ''
})

const isSubmitting = computed(() => state.isSubmitting)

function resetMessages() {
  state.errorMessage = ''
  state.successMessage = ''
}

async function handlePasswordChange() {
  resetMessages()

  if (form.newPassword.length < 8) {
    state.errorMessage = 'New password must be at least 8 characters.'
    return
  }

  if (form.newPassword !== form.confirmPassword) {
    state.errorMessage = 'New password and confirmation do not match.'
    return
  }

  if (form.currentPassword === form.newPassword) {
    state.errorMessage = 'New password must be different from the current password.'
    return
  }

  state.isSubmitting = true

  try {
    const response = await authApi.changePassword(form.currentPassword, form.newPassword)

    if (response.error) {
      state.errorMessage = response.error
      return
    }

    state.successMessage = response.data?.message || 'Password updated successfully.'
    form.currentPassword = ''
    form.newPassword = ''
    form.confirmPassword = ''

    if (isForcedPasswordChange.value) {
      window.setTimeout(() => {
        router.push(homeRoute.value)
      }, 1200)
    }
  } catch (error) {
    console.error('Password update failed:', error)
    state.errorMessage = 'Unable to update password right now. Please try again.'
  } finally {
    state.isSubmitting = false
  }
}
</script>

<style scoped>
.profile-page {
  padding: 2rem;
  min-height: calc(100vh - 88px);
  background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
}

.profile-layout {
  max-width: 960px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(260px, 1fr) minmax(360px, 1.3fr);
  gap: 1.5rem;
}

.profile-card {
  background: #ffffff;
  border-radius: 16px;
  padding: 1.75rem;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
}

.eyebrow {
  margin: 0 0 0.5rem;
  color: #6366f1;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.description {
  margin: 0.75rem 0 1.5rem;
  color: #475569;
  line-height: 1.5;
}

.account-grid {
  display: grid;
  gap: 1rem;
}

.account-item {
  padding: 1rem;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #f8fafc;
}

.label {
  display: block;
  margin-bottom: 0.35rem;
  color: #64748b;
  font-size: 0.85rem;
  font-weight: 600;
}

.value {
  color: #0f172a;
  font-size: 1rem;
  font-weight: 600;
}

.role-pill {
  display: inline-flex;
  align-items: center;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  background: #e0e7ff;
  color: #4338ca;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;
}

.card-header h3,
.account-card h2 {
  margin: 0;
  color: #0f172a;
}

.back-link {
  color: #4f46e5;
  font-weight: 600;
  text-decoration: none;
}

.back-link:hover {
  text-decoration: underline;
}

.info-banner {
  margin-bottom: 1rem;
  padding: 0.85rem 1rem;
  border-radius: 12px;
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
}

.password-form {
  display: grid;
  gap: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.45rem;
  color: #334155;
  font-weight: 600;
}

.form-group input {
  width: 100%;
  padding: 0.8rem 0.9rem;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  font-size: 1rem;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
}

.field-help {
  margin: 0.45rem 0 0;
  color: #64748b;
  font-size: 0.85rem;
}

.message {
  padding: 0.85rem 1rem;
  border-radius: 10px;
  font-weight: 500;
}

.error-message {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.success-message {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}

.primary-btn {
  border: none;
  border-radius: 10px;
  padding: 0.85rem 1.3rem;
  background: linear-gradient(135deg, #6366f1 0%, #7c3aed 100%);
  color: #ffffff;
  font-size: 0.98rem;
  font-weight: 700;
}

.primary-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

@media (max-width: 840px) {
  .profile-page {
    padding: 1rem;
  }

  .profile-layout {
    grid-template-columns: 1fr;
  }

  .card-header {
    flex-direction: column;
  }

  .form-actions {
    justify-content: stretch;
  }

  .primary-btn {
    width: 100%;
  }
}
</style>