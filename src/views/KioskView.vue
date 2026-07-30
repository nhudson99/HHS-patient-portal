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

      <form @submit.prevent="handleLookup" class="kiosk-form">
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

        <div class="form-group">
          <label for="appointmentTime">Appointment Time (optional)</label>
          <input
            id="appointmentTime"
            v-model="form.appointmentTime"
            type="time"
          />
        </div>

        <button type="submit" class="kiosk-btn primary" :disabled="loading">
          {{ loading ? 'Looking up your appointment…' : 'Check In' }}
        </button>
        <button type="button" class="kiosk-btn secondary" @click="reset">
          Cancel
        </button>
      </form>
    </div>

    <!-- ── Profile photo capture ── -->
    <div v-else-if="screen === 'photo'" class="kiosk-card photo-card">
      <h2>Update Profile Photo</h2>
      <p class="kiosk-instruction">
        Look at the camera and take a photo for your patient profile. You can skip this step.
      </p>

      <div class="camera-frame">
        <video
          v-show="!capturedDataUrl"
          ref="videoEl"
          class="camera-preview mirror"
          autoplay
          playsinline
          muted
        ></video>
        <img
          v-if="capturedDataUrl"
          :src="capturedDataUrl"
          alt="Captured profile photo"
          class="camera-preview"
        />
        <canvas ref="canvasEl" class="capture-canvas"></canvas>
      </div>

      <div v-if="!capturedDataUrl" class="photo-actions">
        <button type="button" class="kiosk-btn primary" :disabled="!cameraReady || uploading" @click="takePhoto">
          Take Photo
        </button>
        <button type="button" class="kiosk-btn secondary" :disabled="uploading" @click="skipPhoto">
          Skip
        </button>
      </div>
      <div v-else class="photo-actions">
        <button type="button" class="kiosk-btn primary" :disabled="uploading || !capturedBlob" @click="usePhoto">
          {{ uploading ? 'Saving…' : 'Use Photo' }}
        </button>
        <button type="button" class="kiosk-btn secondary" :disabled="uploading" @click="retakePhoto">
          Retake
        </button>
        <button type="button" class="kiosk-btn secondary" :disabled="uploading" @click="skipPhoto">
          Skip
        </button>
      </div>
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
          <span class="summary-label">Provider</span>
          <span class="summary-value">Dr. {{ appointmentInfo.doctor_name }}</span>
        </div>
        <div v-if="appointmentInfo?.reason" class="summary-row">
          <span class="summary-label">Reason</span>
          <span class="summary-value">{{ appointmentInfo.reason }}</span>
        </div>
      </div>

      <p class="kiosk-instruction">
        <template v-if="appointmentInfo">Please have a seat — a staff member will be with you shortly.</template>
        <template v-else>We couldn't find your appointment on file. A staff member has been notified and will be with you shortly.</template>
      </p>

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
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'

// ── State ─────────────────────────────────────────────────────────────────────
type Screen = 'welcome' | 'form' | 'photo' | 'success'

const screen = ref<Screen>('welcome')
const loading = ref(false)
const uploading = ref(false)
const appointmentInfo = ref<any>(null)
const checkedInName = ref('')
const cameraReady = ref(false)
const capturedDataUrl = ref<string | null>(null)
const capturedBlob = ref<Blob | null>(null)

const form = ref({ fullName: '', dob: '', appointmentTime: '' })

const videoEl = ref<HTMLVideoElement | null>(null)
const canvasEl = ref<HTMLCanvasElement | null>(null)
let mediaStream: MediaStream | null = null

// ── Countdown (success screen only) ──────────────────────────────────────────
const RESET_AFTER_SECS = 10
const countdownSecs = ref(RESET_AFTER_SECS)
const countdownPct = computed(() => (countdownSecs.value / RESET_AFTER_SECS) * 100)

let countdownTimer: ReturnType<typeof setInterval> | null = null
let inactivityTimer: ReturnType<typeof setTimeout> | null = null

const INACTIVITY_MS = 10_000
const PHOTO_INACTIVITY_MS = 60_000

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

// ── Inactivity reset (fires from form/welcome/photo if user walks away) ───────
function resetInactivityTimer() {
  clearTimeout(inactivityTimer!)
  if (screen.value === 'welcome') return
  const delay = screen.value === 'photo' ? PHOTO_INACTIVITY_MS : INACTIVITY_MS
  inactivityTimer = setTimeout(() => reset(), delay)
}

function clearInactivityTimer() {
  clearTimeout(inactivityTimer!)
  inactivityTimer = null
}

function stopCamera() {
  if (mediaStream) {
    for (const track of mediaStream.getTracks()) {
      track.stop()
    }
    mediaStream = null
  }
  if (videoEl.value) {
    videoEl.value.srcObject = null
  }
  cameraReady.value = false
}

function clearCapture() {
  capturedDataUrl.value = null
  capturedBlob.value = null
}

// ── Reset to welcome ──────────────────────────────────────────────────────────
function reset() {
  stopCountdown()
  clearInactivityTimer()
  stopCamera()
  clearCapture()
  screen.value = 'welcome'
  form.value = { fullName: '', dob: '', appointmentTime: '' }
  appointmentInfo.value = null
  checkedInName.value = ''
  loading.value = false
  uploading.value = false
}

function goToSuccess(name: string, appointment: any | null) {
  stopCamera()
  clearCapture()
  checkedInName.value = name
  appointmentInfo.value = appointment
  screen.value = 'success'
  clearInactivityTimer()
  startCountdown()
}

async function completeCheckIn(appointment: any) {
  const patientName = form.value.fullName.trim()
  try {
    const checkinRes = await fetch(`/api/appointments/${appointment.id}/checkin-guest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_name: patientName,
        date_of_birth: form.value.dob,
        appointment_time: form.value.appointmentTime,
      }),
    })
    goToSuccess(patientName, checkinRes.ok ? appointment : null)
  } catch (e) {
    console.error('Kiosk check-in error:', e)
    goToSuccess(patientName, null)
  }
}

async function startFrontCamera(): Promise<boolean> {
  if (!navigator.mediaDevices?.getUserMedia) {
    return false
  }

  // Front-facing only — do not fall back to any/rear camera on dual-camera tablets
  const attempts: MediaStreamConstraints[] = [
    { video: { facingMode: { exact: 'user' } }, audio: false },
    { video: { facingMode: 'user' }, audio: false },
  ]

  for (const constraints of attempts) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      mediaStream = stream
      await nextTick()
      if (videoEl.value) {
        videoEl.value.srcObject = stream
        await videoEl.value.play().catch(() => undefined)
      }
      cameraReady.value = true
      return true
    } catch {
      // try next front-facing constraint
    }
  }
  return false
}

async function openPhotoStep(appointment: any) {
  appointmentInfo.value = appointment
  clearCapture()
  screen.value = 'photo'
  resetInactivityTimer()
  await nextTick()
  const ok = await startFrontCamera()
  if (!ok) {
    // Auto-skip when camera is unavailable
    await completeCheckIn(appointment)
  }
}

// ── API: look up appointment, then photo step or success ──────────────────────
async function handleLookup() {
  loading.value = true

  const patientName = form.value.fullName.trim()

  try {
    const lookupRes = await fetch('/api/appointments/kiosk/lookup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_name: patientName,
        date_of_birth: form.value.dob,
        appointment_time: form.value.appointmentTime,
      }),
    })

    if (!lookupRes.ok) {
      goToSuccess(patientName, null)
      return
    }

    const { appointment } = await lookupRes.json()
    await openPhotoStep(appointment)
  } catch (e) {
    console.error('Kiosk check-in error:', e)
    goToSuccess(patientName, null)
  } finally {
    loading.value = false
  }
}

async function takePhoto() {
  const video = videoEl.value
  const canvas = canvasEl.value
  if (!video || !canvas || !cameraReady.value) return

  const width = video.videoWidth || 640
  const height = video.videoHeight || 480
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  // Draw un-mirrored frame (preview is CSS-mirrored only)
  ctx.drawImage(video, 0, 0, width, height)

  const dataUrl = canvas.toDataURL('image/jpeg', 0.92)
  const blob = await new Promise<Blob | null>((resolve) => {
    canvas.toBlob((result) => resolve(result), 'image/jpeg', 0.92)
  })

  if (!blob) {
    // Fallback: derive blob from data URL so Use Photo is never enabled without bytes
    try {
      const res = await fetch(dataUrl)
      capturedBlob.value = await res.blob()
      capturedDataUrl.value = dataUrl
    } catch (e) {
      console.error('Failed to capture photo blob:', e)
      clearCapture()
      return
    }
  } else {
    capturedBlob.value = blob
    capturedDataUrl.value = dataUrl
  }
  resetInactivityTimer()
}

async function retakePhoto() {
  clearCapture()
  resetInactivityTimer()
  if (!mediaStream) {
    const ok = await startFrontCamera()
    if (!ok) {
      await skipPhoto()
    }
  }
}

async function uploadCapturedPhoto(appointment: any): Promise<boolean> {
  if (!capturedBlob.value || !appointment?.patient_id) return false

  const body = new FormData()
  body.append('file', capturedBlob.value, 'profile-photo.jpg')
  body.append('patient_name', form.value.fullName.trim())
  body.append('date_of_birth', form.value.dob)

  try {
    const res = await fetch(`/api/patients/${appointment.patient_id}/profile-photo/kiosk`, {
      method: 'POST',
      body,
    })
    return res.ok
  } catch (e) {
    console.error('Profile photo upload error:', e)
    return false
  }
}

async function usePhoto() {
  if (!appointmentInfo.value) return
  uploading.value = true
  try {
    // Upload failure must not block check-in
    await uploadCapturedPhoto(appointmentInfo.value)
    await completeCheckIn(appointmentInfo.value)
  } finally {
    uploading.value = false
  }
}

async function skipPhoto() {
  if (!appointmentInfo.value) {
    goToSuccess(form.value.fullName.trim(), null)
    return
  }
  uploading.value = true
  try {
    await completeCheckIn(appointmentInfo.value)
  } finally {
    uploading.value = false
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
  globalThis.addEventListener('mousemove', resetInactivityTimer)
  globalThis.addEventListener('touchstart', resetInactivityTimer)
})

onUnmounted(() => {
  stopCountdown()
  clearInactivityTimer()
  stopCamera()
  globalThis.removeEventListener('mousemove', resetInactivityTimer)
  globalThis.removeEventListener('touchstart', resetInactivityTimer)
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

.photo-card {
  max-width: 640px;
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

/* ── Camera ────────────────────────────────────────────────────────────────── */
.camera-frame {
  position: relative;
  width: 100%;
  aspect-ratio: 4 / 3;
  background: #0f172a;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 20px;
}

.camera-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.camera-preview.mirror {
  transform: scaleX(-1);
}

.capture-canvas {
  display: none;
}

.photo-actions {
  display: flex;
  flex-direction: column;
  gap: 0;
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
  background: #1e40af;
  color: #ffffff;
  cursor: wait;
}

.kiosk-btn.secondary {
  background: #f0f2f5;
  color: #334155;
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

/* ── Success card ──────────────────────────────────────────────────────────── */
.success-card h2 {
  color: #2e7d32;
}

.success-icon {
  width: 90px;
  height: 90px;
  background: linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%);
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
