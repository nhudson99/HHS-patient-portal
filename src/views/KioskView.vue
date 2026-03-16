<template>
  <div class="kiosk-container" @click="resetInactivityTimer" @keydown="resetInactivityTimer">

    <!-- ── Welcome / entry screen ── -->
    <div v-if="screen === 'welcome'" class="kiosk-card">
      <div class="kiosk-logo">🏥</div>
      <h1>Welcome</h1>
      <p class="kiosk-subtitle">Hudson Health System</p>
      <p class="kiosk-instruction">Touch the button below to begin your check-in</p>
      <button class="kiosk-btn primary big" @click="screen = 'form'">
        Start Check-In
      </button>
    </div>

    <!-- ── Name + DOB form ── -->
    <div v-else-if="screen === 'form'" class="kiosk-card">
      <div class="kiosk-logo">📋</div>
      <h2>Patient Check-In</h2>
      <p class="kiosk-instruction">Please enter your full name and date of birth</p>

      <form @submit.prevent="handleCheckIn" class="kiosk-form">
        <div class="form-group">
          <label for="fullName">Full Name</label>
          <input
            id="fullName"
            v-model="form.fullName"
            type="text"
            placeholder="First and Last Name"
            autocomplete="off"
            required
          />
        </div>

        <div class="form-group">
          <label for="dob">Date of Birth</label>
          <input
            id="dob"
            v-model="form.dob"
            type="date"
            required
          />
        </div>

        <div v-if="errorMsg" class="kiosk-error">{{ errorMsg }}</div>

        <button type="submit" class="kiosk-btn primary" :disabled="loading">
          {{ loading ? 'Looking up your appointment…' : 'Check In' }}
        </button>
        <button type="button" class="kiosk-btn secondary" @click="reset">
          Cancel
        </button>
      </form>
    </div>

    <!-- ── Success / confirmation screen ── -->
    <div v-else-if="screen === 'success'" class="kiosk-card success-card">
      <div class="success-icon">✓</div>
      <h2>You're Checked In!</h2>

      <div class="appointment-summary">
        <div class="summary-row">
          <span class="summary-label">Name</span>
          <span class="summary-value">{{ checkedInName }}</span>
        </div>
        <div v-if="appointmentInfo" class="summary-row">
          <span class="summary-label">Date &amp; Time</span>
          <span class="summary-value">{{ formatDateTime(appointmentInfo.appointment_date) }}</span>
        </div>
        <div v-if="appointmentInfo?.doctor_name" class="summary-row">
          <span class="summary-label">Doctor</span>
          <span class="summary-value">Dr. {{ appointmentInfo.doctor_name }}</span>
        </div>
        <div v-if="appointmentInfo?.reason" class="summary-row">
          <span class="summary-label">Reason</span>
          <span class="summary-value">{{ appointmentInfo.reason }}</span>
        </div>
      </div>

      <p class="kiosk-instruction">Please have a seat — a staff member will be with you shortly.</p>

      <button class="kiosk-btn primary big" @click="reset">Done</button>

      <div class="countdown-bar-wrap">
        <div
          class="countdown-bar"
          :style="{ width: countdownPct + '%' }"
          :class="{ urgent: countdownSecs <= 3 }"
        ></div>
        <span class="countdown-label">Returning to home in {{ countdownSecs }}s</span>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'

// ── State ─────────────────────────────────────────────────────────────────────
type Screen = 'welcome' | 'form' | 'success'

const screen = ref<Screen>('welcome')
const loading = ref(false)
const errorMsg = ref('')
const appointmentInfo = ref<any>(null)
const checkedInName = ref('')

const form = ref({ fullName: '', dob: '' })

// ── Countdown (success screen only) ──────────────────────────────────────────
const RESET_AFTER_SECS = 10
const countdownSecs = ref(RESET_AFTER_SECS)
const countdownPct = computed(() => (countdownSecs.value / RESET_AFTER_SECS) * 100)

let countdownTimer: ReturnType<typeof setInterval> | null = null
let inactivityTimer: ReturnType<typeof setTimeout> | null = null

const INACTIVITY_MS = 10_000 // 10 s of no interaction resets from any screen

function startCountdown() {
  countdownSecs.value = RESET_AFTER_SECS
  clearInterval(countdownTimer!)
  countdownTimer = setInterval(() => {
    countdownSecs.value -= 1
    if (countdownSecs.value <= 0) reset()
  }, 1000)
}

function stopCountdown() {
  clearInterval(countdownTimer!)
  countdownTimer = null
}

// ── Inactivity reset (fires from form/welcome if user walks away) ─────────────
function resetInactivityTimer() {
  clearTimeout(inactivityTimer!)
  if (screen.value !== 'welcome') {
    inactivityTimer = setTimeout(() => reset(), INACTIVITY_MS)
  }
}

function clearInactivityTimer() {
  clearTimeout(inactivityTimer!)
  inactivityTimer = null
}

// ── Reset to welcome ──────────────────────────────────────────────────────────
function reset() {
  stopCountdown()
  clearInactivityTimer()
  screen.value = 'welcome'
  form.value = { fullName: '', dob: '' }
  errorMsg.value = ''
  appointmentInfo.value = null
  checkedInName.value = ''
  loading.value = false
}

// ── API: look up appointment then check in ────────────────────────────────────
async function handleCheckIn() {
  errorMsg.value = ''
  loading.value = true

  try {
    // Step 1: find the patient's next upcoming appointment by name + DOB
    const lookupRes = await fetch('/api/appointments/kiosk/lookup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_name: form.value.fullName.trim(),
        date_of_birth: form.value.dob,
      }),
    })

    if (!lookupRes.ok) {
      const err = await lookupRes.json()
      errorMsg.value = err.error || 'No upcoming appointment found for that name and date of birth.'
      return
    }

    const { appointment } = await lookupRes.json()

    // Step 2: check in via the no-auth guest endpoint
    const checkinRes = await fetch(`/api/appointments/${appointment.id}/checkin-guest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_name: form.value.fullName.trim(),
        date_of_birth: form.value.dob,
      }),
    })

    if (!checkinRes.ok) {
      const err = await checkinRes.json()
      errorMsg.value = err.error || 'Unable to complete check-in. Please see the front desk.'
      return
    }

    checkedInName.value = form.value.fullName.trim()
    appointmentInfo.value = appointment
    screen.value = 'success'
    clearInactivityTimer()
    startCountdown()

  } catch (e) {
    console.error('Kiosk check-in error:', e)
    errorMsg.value = 'A network error occurred. Please try again or see the front desk.'
  } finally {
    loading.value = false
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatDateTime(dateStr: string) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return (
    d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }) +
    ' at ' +
    d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  )
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(() => {
  window.addEventListener('mousemove', resetInactivityTimer)
  window.addEventListener('touchstart', resetInactivityTimer)
})

onUnmounted(() => {
  stopCountdown()
  clearInactivityTimer()
  window.removeEventListener('mousemove', resetInactivityTimer)
  window.removeEventListener('touchstart', resetInactivityTimer)
})
</script>

<style scoped>
/* ── Layout ────────────────────────────────────────────────────────────────── */
.kiosk-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(160deg, #1a237e 0%, #283593 50%, #3949ab 100%);
  padding: 24px;
  user-select: none;
}

.kiosk-card {
  background: #ffffff;
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
  padding: 56px 48px;
  max-width: 560px;
  width: 100%;
  text-align: center;
  animation: fadeSlideIn 0.3s ease-out;
}

@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── Typography ────────────────────────────────────────────────────────────── */
.kiosk-logo {
  font-size: 64px;
  margin-bottom: 12px;
  line-height: 1;
}

h1 {
  font-size: 2.4rem;
  font-weight: 700;
  color: #1a237e;
  margin: 0 0 6px;
}

h2 {
  font-size: 1.9rem;
  font-weight: 700;
  color: #1a237e;
  margin: 0 0 10px;
}

.kiosk-subtitle {
  font-size: 1.1rem;
  color: #546e7a;
  margin: 0 0 28px;
}

.kiosk-instruction {
  font-size: 1.05rem;
  color: #546e7a;
  margin: 0 0 28px;
  line-height: 1.5;
}

/* ── Buttons ───────────────────────────────────────────────────────────────── */
.kiosk-btn {
  display: block;
  width: 100%;
  padding: 16px;
  border: none;
  border-radius: 10px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
  margin-bottom: 12px;
}

.kiosk-btn:last-child { margin-bottom: 0; }

.kiosk-btn:active { transform: scale(0.98); }

.kiosk-btn.primary {
  background: linear-gradient(135deg, #1a237e 0%, #3949ab 100%);
  color: #fff;
  box-shadow: 0 4px 14px rgba(26, 35, 126, 0.4);
}

.kiosk-btn.primary:hover:not(:disabled) {
  box-shadow: 0 6px 20px rgba(26, 35, 126, 0.55);
  transform: translateY(-2px);
}

.kiosk-btn.primary:disabled {
  opacity: 0.65;
  cursor: wait;
}

.kiosk-btn.secondary {
  background: #f0f2f5;
  color: #546e7a;
  box-shadow: none;
}

.kiosk-btn.secondary:hover {
  background: #e3e6ec;
}

.kiosk-btn.big {
  padding: 20px;
  font-size: 1.25rem;
}

/* ── Form ──────────────────────────────────────────────────────────────────── */
.kiosk-form { text-align: left; }

.form-group {
  margin-bottom: 22px;
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
  font-size: 1.05rem;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

input:focus {
  outline: none;
  border-color: #3949ab;
}

.kiosk-error {
  background: #fff3f3;
  border: 1px solid #f5c6c6;
  color: #c62828;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 18px;
  font-size: 0.95rem;
  line-height: 1.4;
}

/* ── Success card ──────────────────────────────────────────────────────────── */
.success-card h2 {
  color: #2e7d32;
}

.success-icon {
  width: 90px;
  height: 90px;
  background: linear-gradient(135deg, #43a047 0%, #2e7d32 100%);
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 52px;
  margin: 0 auto 20px;
  box-shadow: 0 6px 20px rgba(46, 125, 50, 0.45);
  animation: popIn 0.35s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

@keyframes popIn {
  from { transform: scale(0); opacity: 0; }
  to   { transform: scale(1); opacity: 1; }
}

.appointment-summary {
  background: #f8f9fa;
  border-radius: 10px;
  padding: 16px 20px;
  margin: 0 0 24px;
  text-align: left;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 8px 0;
  border-bottom: 1px solid #e8eaf0;
}

.summary-row:last-child { border-bottom: none; }

.summary-label {
  font-weight: 600;
  color: #546e7a;
  white-space: nowrap;
  font-size: 0.9rem;
}

.summary-value {
  color: #263238;
  text-align: right;
  font-size: 0.9rem;
}

/* ── Countdown bar ─────────────────────────────────────────────────────────── */
.countdown-bar-wrap {
  margin-top: 24px;
  position: relative;
}

.countdown-bar {
  height: 6px;
  background: #3949ab;
  border-radius: 4px;
  transition: width 1s linear, background 0.3s;
  margin-bottom: 6px;
}

.countdown-bar.urgent { background: #e53935; }

.countdown-label {
  font-size: 0.85rem;
  color: #90a4ae;
}
</style>
