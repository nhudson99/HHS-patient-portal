<template>
  <div class="checkin-container">
    <div class="checkin-card">
      <div class="logo">
        <h1>🏥</h1>
      </div>
      <h2>Patient Check-In</h2>
      <p class="subtitle">Hudson Health System</p>

      <!-- Logged-in patient view with next appointment -->
      <div v-if="isLoggedInPatient && !checkedIn" class="logged-in-checkin">
        <div v-if="loading" class="loading-state">
          <p>Loading your appointment...</p>
        </div>
        <div v-else-if="nextAppointment" class="appointment-info">
          <h3>Your Next Appointment</h3>
          <div class="appointment-card">
            <div class="detail-row">
              <span class="label">Date & Time:</span>
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
          <button @click="handleLoggedInCheckIn" class="checkin-button" :disabled="loading">
            {{ loading ? 'Checking In...' : 'Check In Now' }}
          </button>
          <button @click="router.push('/patient')" class="back-button">Back to Dashboard</button>
        </div>
        <div v-else-if="!loading" class="no-appointment">
          <p>{{ error || 'No upcoming appointments found.' }}</p>
          <button @click="router.push('/patient')" class="back-button">Back to Dashboard</button>
        </div>
      </div>

      <!-- Check-in with credentials (for non-logged-in users) -->
      <div v-if="!isLoggedInPatient && !showGuestForm && !checkedIn" class="checkin-options">
        <p class="option-text">Already have an account?</p>
        <button @click="showCredentialLogin = true" class="option-button">
          Check In with Credentials
        </button>
        
        <div class="divider">
          <span>OR</span>
        </div>
        
        <p class="option-text">Don't have an account?</p>
        <button @click="showGuestForm = true" class="option-button guest">
          Check In as Guest
        </button>
      </div>

      <!-- Guest check-in form -->
      <form v-if="showGuestForm && !checkedIn" @submit.prevent="handleGuestCheckIn" class="checkin-form">
        <h3>Guest Check-In</h3>
        <p class="form-instruction">Please provide your information to check in for your appointment</p>
        
        <div class="form-group">
          <label for="fullName">Full Name</label>
          <input
            id="fullName"
            v-model="guestForm.fullName"
            type="text"
            placeholder="Enter your full name"
            required
          />
        </div>

        <div class="form-group">
          <label for="birthday">Date of Birth</label>
          <input
            id="birthday"
            v-model="guestForm.birthday"
            type="date"
            required
          />
        </div>

        <button type="submit" class="checkin-button">Check In</button>
        <button type="button" @click="showGuestForm = false" class="back-button">Back</button>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>
      </form>

      <!-- Credential login form -->
      <form v-if="showCredentialLogin && !checkedIn" @submit.prevent="handleCredentialCheckIn" class="checkin-form">
        <h3>Check In with Account</h3>
        
        <div class="form-group">
          <label for="username">Username</label>
          <input
            id="username"
            v-model="credentialForm.username"
            type="text"
            placeholder="Enter username"
            required
          />
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="credentialForm.password"
            type="password"
            placeholder="Enter password"
            required
          />
        </div>

        <button type="submit" class="checkin-button">Check In</button>
        <button type="button" @click="showCredentialLogin = false" class="back-button">Back</button>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>
      </form>

      <!-- Check-in confirmation -->
      <div v-if="checkedIn" class="confirmation">
        <div class="success-icon">✓</div>
        <h2>Check-In Successful!</h2>
        <p class="confirmation-message">
          You are checked in for your appointment.
        </p>
        <div v-if="appointmentInfo" class="appointment-details">
          <div class="detail-row">
            <span class="label">Date & Time:</span>
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
        <button @click="isLoggedInPatient ? router.push('/patient') : goToLogin()" class="done-button">
          {{ isLoggedInPatient ? 'Back to Dashboard' : 'Done' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getCurrentUser } from '@/store'

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
  birthday: ''
})

const credentialForm = ref({
  username: '',
  password: ''
})

// Check if user is logged in as patient and fetch their next appointment
onMounted(async () => {
  const currentUser = getCurrentUser()
  if (currentUser && currentUser.role === 'patient') {
    isLoggedInPatient.value = true
    await fetchNextAppointment()
  }
})

// Fetch the next scheduled appointment for logged-in patient
const fetchNextAppointment = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('sessionToken')
    const response = await fetch('/api/appointments/patient', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (response.ok) {
      const data = await response.json()
      const appointments = data.appointments || []
      
      // Find next upcoming appointment (not in past, earliest first)
      const now = new Date()
      const upcomingAppointments = appointments
        .filter((apt: any) => new Date(apt.appointment_date) >= now)
        .sort((a: any, b: any) => new Date(a.appointment_date).getTime() - new Date(b.appointment_date).getTime())
      
      if (upcomingAppointments.length > 0) {
        nextAppointment.value = upcomingAppointments[0]
      } else {
        error.value = 'No upcoming appointments found.'
      }
    }
  } catch (err) {
    console.error('Error fetching appointment:', err)
    error.value = 'Unable to fetch appointment information.'
  } finally {
    loading.value = false
  }
}

// Check in for logged-in patient's next appointment
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
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    })

    if (response.ok) {
      appointmentInfo.value = nextAppointment.value
      checkedIn.value = true
    } else {
      const errorData = await response.json()
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
  
  try {
    // Find patient and get their appointments
    const patientsResponse = await fetch('/api/patients', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })

    if (!patientsResponse.ok) {
      error.value = 'Unable to verify patient information.'
      return
    }

    // For guest check-in, we'll need to use the guest endpoint
    // This is a simplified version - in production you'd match by name/DOB
    error.value = 'Guest check-in requires name and date of birth matching.'
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
    // Login first
    const loginResponse = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username: credentialForm.value.username,
        password: credentialForm.value.password
      })
    })

    if (!loginResponse.ok) {
      error.value = 'Invalid credentials.'
      return
    }

    const loginData = await loginResponse.json()
    localStorage.setItem('sessionToken', loginData.sessionToken)
    
    // Now fetch and check in for their next appointment
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.checkin-card {
  background: white;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  max-width: 500px;
  width: 100%;
}

.logo {
  text-align: center;
  font-size: 48px;
  margin-bottom: 10px;
}

h2 {
  text-align: center;
  color: #333;
  margin-bottom: 5px;
  font-size: 28px;
}

h3 {
  color: #333;
  margin-bottom: 10px;
  font-size: 20px;
}

.subtitle {
  text-align: center;
  color: #666;
  margin-bottom: 30px;
  font-size: 16px;
}

.checkin-options {
  text-align: center;
}

.option-text {
  color: #666;
  margin-bottom: 15px;
  font-size: 14px;
}

.option-button {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 20px;
  transition: transform 0.2s;
}

.option-button:hover {
  transform: translateY(-2px);
}

.option-button.guest {
  background: linear-gradient(135deg, #42a5f5 0%, #478ed1 100%);
}

.divider {
  text-align: center;
  margin: 25px 0;
  position: relative;
}

.divider::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  width: 100%;
  height: 1px;
  background: #ddd;
}

.divider span {
  background: white;
  padding: 0 15px;
  color: #999;
  font-size: 14px;
  position: relative;
  z-index: 1;
}

.checkin-form {
  margin-top: 20px;
}

.form-instruction {
  color: #666;
  font-size: 14px;
  margin-bottom: 20px;
  line-height: 1.5;
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  margin-bottom: 5px;
  color: #555;
  font-weight: 500;
}

input {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.3s;
}

input:focus {
  outline: none;
  border-color: #667eea;
}

.checkin-button {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 10px;
  transition: transform 0.2s;
}

.checkin-button:hover {
  transform: translateY(-2px);
}

.back-button {
  width: 100%;
  padding: 12px;
  background: #f5f5f5;
  color: #666;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  transition: background 0.3s;
}

.back-button:hover {
  background: #e0e0e0;
}

.error-message {
  margin-top: 15px;
  padding: 10px;
  background: #fee;
  color: #c33;
  border-radius: 6px;
  text-align: center;
  font-size: 14px;
}

.confirmation {
  text-align: center;
  padding: 20px 0;
}

.success-icon {
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, #66bb6a 0%, #4caf50 100%);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48px;
  margin: 0 auto 20px;
  animation: scaleIn 0.3s ease-out;
}

@keyframes scaleIn {
  from {
    transform: scale(0);
  }
  to {
    transform: scale(1);
  }
}

.confirmation h2 {
  color: #4caf50;
  margin-bottom: 15px;
}

.confirmation-message {
  color: #666;
  font-size: 16px;
  margin-bottom: 25px;
  line-height: 1.6;
}

.appointment-details {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 25px;
  text-align: left;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #e0e0e0;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-row .label {
  font-weight: 600;
  color: #555;
}

.detail-row .value {
  color: #333;
}

.done-button {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  transition: transform 0.2s;
}

.done-button:hover {
  transform: translateY(-2px);
}

.logged-in-checkin {
  margin-top: 20px;
}

.appointment-card {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin: 20px 0;
  border: 1px solid #e0e0e0;
}

.loading-state,
.no-appointment {
  text-align: center;
  padding: 40px 20px;
  color: #666;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.status-badge.pending {
  background: #fff3e0;
  color: #f57c00;
}

.status-badge.confirmed {
  background: #e8f5e9;
  color: #2e7d32;
}

.checkin-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
