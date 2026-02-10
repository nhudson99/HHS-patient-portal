<template>
  <div class="checkin-container">
    <div class="checkin-card">
      <div class="logo">
        <h1>🏥</h1>
      </div>
      <h2>Patient Check-In</h2>
      <p class="subtitle">Hudson Health System</p>

      <!-- Check-in with credentials -->
      <div v-if="!showGuestForm && !checkedIn" class="checkin-options">
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
            <span class="label">Patient:</span>
            <span class="value">{{ appointmentInfo.patientName }}</span>
          </div>
          <div class="detail-row">
            <span class="label">Doctor:</span>
            <span class="value">{{ appointmentInfo.doctorName }}</span>
          </div>
          <div class="detail-row">
            <span class="label">Time:</span>
            <span class="value">{{ appointmentInfo.time }}</span>
          </div>
        </div>
        <button @click="goToLogin" class="done-button">Done</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { 
  findAppointmentByPatientInfo,
  checkInForAppointment,
  authenticateUser,
  getAppointmentsForPatient
} from '@/store'
import type { Appointment } from '@/types'

const router = useRouter()
const showGuestForm = ref(false)
const showCredentialLogin = ref(false)
const checkedIn = ref(false)
const error = ref('')
const appointmentInfo = ref<Appointment | null>(null)

const guestForm = ref({
  fullName: '',
  birthday: ''
})

const credentialForm = ref({
  username: '',
  password: ''
})

const handleGuestCheckIn = () => {
  error.value = ''
  
  // Find appointment by patient info
  const appointment = findAppointmentByPatientInfo(
    guestForm.value.fullName,
    guestForm.value.birthday
  )
  
  if (appointment) {
    // Check in for the appointment
    if (checkInForAppointment(appointment.id)) {
      appointmentInfo.value = appointment
      checkedIn.value = true
    } else {
      error.value = 'Unable to check in. Please try again.'
    }
  } else {
    error.value = 'No appointment found for today with the provided information. Please verify your name and date of birth.'
  }
}

const handleCredentialCheckIn = () => {
  error.value = ''
  
  const user = authenticateUser(
    credentialForm.value.username,
    credentialForm.value.password
  )
  
  if (user && user.role === 'patient') {
    // Find today's appointment for this patient
    const today = new Date().toISOString().split('T')[0]
    const appointments = getAppointmentsForPatient(user.id)
    const todayAppointment = appointments.find(apt => apt.date === today)
    
    if (todayAppointment) {
      if (checkInForAppointment(todayAppointment.id)) {
        appointmentInfo.value = todayAppointment
        checkedIn.value = true
      } else {
        error.value = 'Unable to check in. Please try again.'
      }
    } else {
      error.value = 'No appointment found for today.'
    }
  } else {
    error.value = 'Invalid credentials or not a patient account.'
  }
}

const goToLogin = () => {
  router.push('/')
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
  padding: 12px;
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
</style>
