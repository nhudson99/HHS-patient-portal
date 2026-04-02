<template>
  <div class="checkin-container">
    <div class="checkin-card">
      <div class="logo">🏥</div>
      <h2>Patient Check-In</h2>
      <p class="subtitle">Hudson Health System</p>

      <div v-if="isLoggedInPatient && !checkedIn" class="logged-in-checkin">
        <div v-if="loading" class="loading-state">
          <p>Loading your appointment...</p>
        </div>

        <div v-else-if="nextAppointment" class="appointment-info">
          <h3>Your Next Appointment</h3>
          <div class="appointment-card">
            <div class="detail-row">
              <span class="label">Date &amp; Time:</span>
              <span class="value">{{ formatDateTime(nextAppointment.appointment_date) }}</span>
            </div>
            <div v-if="nextAppointment.doctor_name" class="detail-row">
              <span class="label">Doctor:</span>
              <span class="value">Dr. {{ nextAppointment.doctor_name }}</span>
            </div>
            <div class="detail-row">
              <span class="label">Reason:</span>
              <span class="value">{{ nextAppointment.reason }}</span>
            </div>
            <div class="detail-row">
              <span class="label">Status:</span>
              <span class="value status-badge" :class="nextAppointment.status">
                {{ nextAppointment.status.toUpperCase() }}
              </span>
            </div>
          </div>
          <button @click="handleLoggedInCheckIn" class="kiosk-btn primary" :disabled="loading">
            {{ loading ? 'Checking In...' : 'Check In Now' }}
          </button>
          <button @click="router.push('/patient')" class="kiosk-btn secondary">Back to Dashboard</button>
        </div>

        <div v-else-if="!loading" class="no-appointment">
          <p>{{ error || 'No upcoming appointments found.' }}</p>
          <button @click="router.push('/patient')" class="kiosk-btn secondary">Back to Dashboard</button>
        </div>
      </div>

      <div v-if="!isLoggedInPatient && !showGuestForm && !showCredentialLogin && !checkedIn" class="checkin-options">
        <p class="option-text">Already have an account?</p>
        <button @click="showCredentialLogin = true" class="kiosk-btn primary">Check In with Credentials</button>

        <div class="divider"><span>OR</span></div>

        <p class="option-text">No account? Use guest check-in</p>
        <button @click="showGuestForm = true" class="kiosk-btn secondary">Check In as Guest</button>
      </div>

      <form v-if="showGuestForm && !checkedIn" @submit.prevent="handleGuestCheckIn" class="kiosk-form">
        <h3>Guest Check-In</h3>
        <p class="form-instruction">Please enter the same details as the kiosk check-in form.</p>

        <div class="form-group">
          <label for="fullName">Full Name</label>
          <input id="fullName" v-model="guestForm.fullName" type="text" placeholder="First and Last Name" required />
        </div>

        <div class="form-group">
          <label for="birthday">Date of Birth</label>
          <input id="birthday" v-model="guestForm.birthday" type="date" required />
        </div>

        <div class="form-group">
          <label for="appointmentTime">Appointment Time (optional)</label>
          <input id="appointmentTime" v-model="guestForm.appointmentTime" type="time" />
        </div>

        <div v-if="error" class="error-message">{{ error }}</div>

        <button type="submit" class="kiosk-btn primary" :disabled="loading">
          {{ loading ? 'Looking up your appointment...' : 'Check In' }}
        </button>
        <button type="button" @click="closeGuestForm" class="kiosk-btn secondary" :disabled="loading">Back</button>
      </form>

      <form v-if="showCredentialLogin && !checkedIn" @submit.prevent="handleCredentialCheckIn" class="kiosk-form">
        <h3>Check In with Account</h3>
        <p class="form-instruction">Sign in and we will check you into your next appointment.</p>

        <div class="form-group">
          <label for="username">Username</label>
          <input id="username" v-model="credentialForm.username" type="text" placeholder="Enter username" required />
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <input id="password" v-model="credentialForm.password" type="password" placeholder="Enter password" required />
        </div>

        <div v-if="error" class="error-message">{{ error }}</div>

        <button type="submit" class="kiosk-btn primary" :disabled="loading">
          {{ loading ? 'Signing in...' : 'Check In' }}
        </button>
        <button type="button" @click="closeCredentialForm" class="kiosk-btn secondary" :disabled="loading">Back</button>
      </form>

      <div v-if="checkedIn" class="confirmation">
        <div class="success-icon">✓</div>
        <h2>Check-In Successful!</h2>
        <p class="confirmation-message">
          <template v-if="appointmentInfo">You are checked in for your appointment.</template>
          <template v-else>We could not find your appointment on file. A staff member has been notified and will assist you shortly.</template>
        </p>

        <div v-if="appointmentInfo" class="appointment-details">
          <div class="detail-row">
            <span class="label">Date &amp; Time:</span>
            <span class="value">{{ formatDateTime(appointmentInfo.appointment_date) }}</span>
          </div>
          <div v-if="appointmentInfo.doctor_name" class="detail-row">
            <span class="label">Doctor:</span>
            <span class="value">Dr. {{ appointmentInfo.doctor_name }}</span>
          </div>
          <div class="detail-row">
            <span class="label">Reason:</span>
            <span class="value">{{ appointmentInfo.reason }}</span>
          </div>
        </div>

        <button @click="isLoggedInPatient ? router.push('/patient') : goToLogin()" class="kiosk-btn primary">
          {{ isLoggedInPatient ? 'Back to Dashboard' : 'Done' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/api'
import { getCurrentUser, setCurrentUser } from '@/store'

const router = useRouter()
const showGuestForm = ref(false)
const showCredentialLogin = ref(false)
const checkedIn = ref(false)
const error = ref('')
const loading = ref(false)
const appointmentInfo = ref<any>(null)
const nextAppointment = ref<any>(null)
const isLoggedInPatient = ref(false)

const guestForm = ref({
  fullName: '',
  birthday: '',
  appointmentTime: ''
})

const credentialForm = ref({
  username: '',
  password: ''
})

onMounted(async () => {
  const currentUser = getCurrentUser()
  if (currentUser && currentUser.role === 'patient') {
    isLoggedInPatient.value = true
    await fetchNextAppointment()
  }
})

const fetchNextAppointment = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('sessionToken')
    const response = await fetch('/api/appointments/patient', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })

    if (response.ok) {
      const data = await response.json()
      const appointments = data.appointments || []
      const now = new Date()
      const upcomingAppointments = appointments
        .filter((apt: any) => new Date(apt.appointment_date) >= now)
        .sort((a: any, b: any) => new Date(a.appointment_date).getTime() - new Date(b.appointment_date).getTime())

      if (upcomingAppointments.length > 0) {
        nextAppointment.value = upcomingAppointments[0]
      } else {
        error.value = 'No upcoming appointments found.'
      }
    } else {
      error.value = 'Unable to fetch appointment information.'
    }
  } catch (err) {
    console.error('Error fetching appointment:', err)
    error.value = 'Unable to fetch appointment information.'
  } finally {
    loading.value = false
  }
}

const handleLoggedInCheckIn = async () => {
  if (!nextAppointment.value) {
    error.value = 'No appointment available for check-in.'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const token = localStorage.getItem('sessionToken')
    const response = await fetch(`/api/appointments/${nextAppointment.value.id}/checkin`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    })

    if (response.ok) {
      appointmentInfo.value = nextAppointment.value
      checkedIn.value = true
    } else {
      const errorData = await response.json().catch(() => ({}))
      error.value = errorData.error || 'Unable to check in. Please try again.'
    }
  } catch (err) {
    console.error('Check-in error:', err)
    error.value = 'An error occurred during check-in.'
  } finally {
    loading.value = false
  }
}

const handleGuestCheckIn = async () => {
  error.value = ''
  loading.value = true

  const patientName = guestForm.value.fullName.trim()

  try {
    const lookupRes = await fetch('/api/appointments/kiosk/lookup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_name: patientName,
        date_of_birth: guestForm.value.birthday,
        appointment_time: guestForm.value.appointmentTime
      })
    })

    if (!lookupRes.ok) {
      appointmentInfo.value = null
      checkedIn.value = true
      return
    }

    const { appointment } = await lookupRes.json()

    const checkinRes = await fetch(`/api/appointments/${appointment.id}/checkin-guest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_name: patientName,
        date_of_birth: guestForm.value.birthday,
        appointment_time: guestForm.value.appointmentTime
      })
    })

    appointmentInfo.value = checkinRes.ok ? appointment : null
    checkedIn.value = true
  } catch (err) {
    console.error('Guest check-in error:', err)
    error.value = 'An error occurred during check-in.'
  } finally {
    loading.value = false
  }
}

const handleCredentialCheckIn = async () => {
  error.value = ''
  loading.value = true

  try {
    const loginResponse = await authApi.login(credentialForm.value.username, credentialForm.value.password)

    if (loginResponse.error || !loginResponse.data) {
      error.value = loginResponse.error || 'Invalid credentials.'
      return
    }

    localStorage.setItem('sessionToken', loginResponse.data.sessionToken)
    localStorage.setItem('currentUser', JSON.stringify(loginResponse.data.user))
    setCurrentUser(loginResponse.data.user as any)

    isLoggedInPatient.value = loginResponse.data.user.role === 'patient'
    await fetchNextAppointment()
    if (nextAppointment.value) {
      await handleLoggedInCheckIn()
    }
  } catch (err) {
    console.error('Credential check-in error:', err)
    error.value = 'An error occurred during check-in.'
  } finally {
    loading.value = false
  }
}

const closeGuestForm = () => {
  showGuestForm.value = false
  error.value = ''
}

const closeCredentialForm = () => {
  showCredentialLogin.value = false
  error.value = ''
}

const goToLogin = () => {
  router.push('/')
}

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return '—'
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  }) + ' at ' + date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.checkin-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(160deg, #1a237e 0%, #283593 50%, #3949ab 100%);
  padding: 24px;
}

.checkin-card {
  background: #ffffff;
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
  padding: 42px 36px;
  max-width: 560px;
  width: 100%;
}

.logo {
  text-align: center;
  font-size: 60px;
  line-height: 1;
  margin-bottom: 12px;
}

h2 {
  text-align: center;
  font-size: 2rem;
  font-weight: 700;
  color: #1a237e;
  margin: 0;
}

h3 {
  font-size: 1.45rem;
  font-weight: 700;
  color: #1a237e;
  margin: 0 0 8px;
}

.subtitle {
  text-align: center;
  color: #546e7a;
  margin: 10px 0 24px;
}

.kiosk-form {
  text-align: left;
}

.form-group {
  margin-bottom: 18px;
}

label {
  display: block;
  font-weight: 600;
  color: #37474f;
  margin-bottom: 6px;
  font-size: 0.95rem;
}

input {
  width: 100%;
  padding: 14px 16px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

input:focus {
  outline: none;
  border-color: #3949ab;
}

.kiosk-btn {
  display: block;
  width: 100%;
  padding: 14px;
  border: none;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
  margin-bottom: 12px;
}

.kiosk-btn:last-child {
  margin-bottom: 0;
}

.kiosk-btn.primary {
  background: linear-gradient(135deg, #1a237e 0%, #3949ab 100%);
  color: #fff;
  box-shadow: 0 4px 14px rgba(26, 35, 126, 0.4);
}

.kiosk-btn.primary:hover:not(:disabled) {
  box-shadow: 0 6px 20px rgba(26, 35, 126, 0.55);
  transform: translateY(-2px);
}

.kiosk-btn.secondary {
  background: #f0f2f5;
  color: #334155;
}

.kiosk-btn.secondary:hover:not(:disabled) {
  background: #e3e6ec;
}

.kiosk-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.form-instruction,
.option-text {
  color: #546e7a;
  margin: 0 0 18px;
  line-height: 1.5;
}

.divider {
  text-align: center;
  margin: 18px 0;
  position: relative;
}

.divider::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  width: 100%;
  height: 1px;
  background: #d5dbe3;
}

.divider span {
  background: white;
  padding: 0 12px;
  color: #708090;
  font-size: 0.85rem;
  position: relative;
}

.error-message {
  background: #fff3f3;
  border: 1px solid #f5c6c6;
  color: #c62828;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 14px;
  font-size: 0.92rem;
}

.confirmation {
  text-align: center;
}

.success-icon {
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%);
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48px;
  margin: 0 auto 18px;
}

.confirmation-message {
  color: #546e7a;
  margin: 0 0 18px;
  line-height: 1.5;
}

.appointment-card,
.appointment-details {
  background: #f8f9fa;
  padding: 18px;
  border-radius: 10px;
  margin-bottom: 16px;
  border: 1px solid #e0e0e0;
  text-align: left;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #e0e0e0;
}

.detail-row:last-child {
  border-bottom: none;
}

.label {
  font-weight: 600;
  color: #475569;
}

.value {
  color: #111827;
  text-align: right;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.status-badge.pending {
  background: #fff3e0;
  color: #9a5a00;
}

.status-badge.confirmed {
  background: #e8f5e9;
  color: #2e7d32;
}

.loading-state,
.no-appointment {
  text-align: center;
  padding: 28px 12px;
  color: #546e7a;
}

@media (max-width: 480px) {
  .checkin-container {
    padding: 12px;
  }

  .checkin-card {
    padding: 28px 20px;
    border-radius: 14px;
  }

  h2 {
    font-size: 1.6rem;
  }

  .detail-row {
    flex-direction: column;
    gap: 2px;
  }

  .value {
    text-align: left;
  }
}
</style>
