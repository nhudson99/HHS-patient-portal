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

    <!-- ── ID photo capture ── -->
    <div v-else-if="screen === 'photo'" class="kiosk-card photo-card">
      <h2>Photo ID</h2>
      <p class="kiosk-instruction">
        {{ capturedBlob
          ? 'Review your ID photo, then save it to your profile.'
          : 'Hold your photo ID in front of the camera, then take a picture.' }}
      </p>

      <div class="camera-frame">
        <video
          v-show="!capturedBlob && cameraReady"
          ref="videoEl"
          class="camera-preview"
          autoplay
          playsinline
          muted
        ></video>
        <img
          v-if="capturedPreviewUrl"
          :src="capturedPreviewUrl"
          alt="Captured ID preview"
          class="camera-preview"
        />
        <div v-if="!capturedBlob && !cameraReady && !cameraError" class="camera-placeholder">
          Starting camera…
        </div>
        <div v-if="cameraError && !capturedBlob" class="camera-placeholder error">
          {{ cameraError }}
        </div>
        <canvas ref="canvasEl" class="capture-canvas" aria-hidden="true"></canvas>
      </div>

      <p v-if="photoError" class="kiosk-error">{{ photoError }}</p>

      <template v-if="!capturedBlob">
        <button
          type="button"
          class="kiosk-btn primary"
          :disabled="!cameraReady || uploadingPhoto"
          @click="capturePhoto"
        >
          Take Photo
        </button>
        <label class="kiosk-btn secondary file-fallback">
          Use Gallery / File
          <input
            type="file"
            accept="image/jpeg,image/png,image/*"
            capture="environment"
            class="sr-only"
            @change="onFileSelected"
          />
        </label>
        <button type="button" class="kiosk-btn secondary" :disabled="uploadingPhoto" @click="skipPhoto">
          Skip
        </button>
      </template>

      <template v-else>
        <button
          type="button"
          class="kiosk-btn primary"
          :disabled="uploadingPhoto"
          @click="uploadIdPhoto"
        >
          {{ uploadingPhoto ? 'Saving…' : 'Save ID Photo' }}
        </button>
        <button type="button" class="kiosk-btn secondary" :disabled="uploadingPhoto" @click="retakePhoto">
          Retake
        </button>
        <button type="button" class="kiosk-btn secondary" :disabled="uploadingPhoto" @click="skipPhoto">
          Skip
        </button>
      </template>
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
        <div v-if="idPhotoSaved" class="summary-row">
          <span class="summary-label">ID Photo</span>
          <span class="summary-value">Saved to your profile</span>
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
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'

// ── State ─────────────────────────────────────────────────────────────────────
type Screen = 'welcome' | 'form' | 'photo' | 'success'

const screen = ref<Screen>('welcome')
const loading = ref(false)
const appointmentInfo = ref<any>(null)
const checkedInName = ref('')
const idPhotoSaved = ref(false)

const form = ref({ fullName: '', dob: '', appointmentTime: '' })

// ── Photo capture ─────────────────────────────────────────────────────────────
const videoEl = ref<HTMLVideoElement | null>(null)
const canvasEl = ref<HTMLCanvasElement | null>(null)
const cameraReady = ref(false)
const cameraError = ref('')
const photoError = ref('')
const capturedBlob = ref<Blob | null>(null)
const capturedPreviewUrl = ref('')
const uploadingPhoto = ref(false)

let mediaStream: MediaStream | null = null

async function startCamera() {
  stopCamera()
  cameraError.value = ''
  cameraReady.value = false

  if (!navigator.mediaDevices?.getUserMedia) {
    cameraError.value = 'Camera is not available on this device. You can upload a photo instead.'
    return
  }

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: 'environment' },
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    })
    await nextTick()
    if (videoEl.value) {
      videoEl.value.srcObject = mediaStream
      await videoEl.value.play()
      cameraReady.value = true
    }
  } catch (err) {
    console.error('Camera start failed:', err)
    cameraError.value = 'Unable to access the camera. You can upload a photo instead.'
  }
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

function clearCapturedPhoto() {
  capturedBlob.value = null
  if (capturedPreviewUrl.value) {
    URL.revokeObjectURL(capturedPreviewUrl.value)
    capturedPreviewUrl.value = ''
  }
}

function capturePhoto() {
  photoError.value = ''
  const video = videoEl.value
  const canvas = canvasEl.value
  if (!video || !canvas || !cameraReady.value) return

  const width = video.videoWidth || 1280
  const height = video.videoHeight || 720
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    photoError.value = 'Could not capture photo. Please try again.'
    return
  }
  ctx.drawImage(video, 0, 0, width, height)
  canvas.toBlob(
    (blob) => {
      if (!blob) {
        photoError.value = 'Could not capture photo. Please try again.'
        return
      }
      clearCapturedPhoto()
      capturedBlob.value = blob
      capturedPreviewUrl.value = URL.createObjectURL(blob)
      stopCamera()
      resetInactivityTimer()
    },
    'image/jpeg',
    0.85,
  )
}

function onFileSelected(event: Event) {
  photoError.value = ''
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  if (!file.type.startsWith('image/')) {
    photoError.value = 'Please select a JPEG or PNG image.'
    input.value = ''
    return
  }

  clearCapturedPhoto()
  capturedBlob.value = file
  capturedPreviewUrl.value = URL.createObjectURL(file)
  stopCamera()
  input.value = ''
  resetInactivityTimer()
}

async function retakePhoto() {
  photoError.value = ''
  clearCapturedPhoto()
  await startCamera()
  resetInactivityTimer()
}

async function uploadIdPhoto() {
  if (!capturedBlob.value) return

  uploadingPhoto.value = true
  photoError.value = ''
  resetInactivityTimer()

  try {
    const formData = new FormData()
    const filename = capturedBlob.value instanceof File
      ? capturedBlob.value.name || 'id-photo.jpg'
      : 'id-photo.jpg'
    formData.append('photo', capturedBlob.value, filename)
    formData.append('patient_name', form.value.fullName.trim())
    formData.append('date_of_birth', form.value.dob)

    const res = await fetch('/api/documents/kiosk/id-photo', {
      method: 'POST',
      body: formData,
    })

    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      photoError.value = data.error || 'Failed to save ID photo. Please try again or skip.'
      return
    }

    idPhotoSaved.value = true
    goToSuccess()
  } catch (e) {
    console.error('ID photo upload error:', e)
    photoError.value = 'Failed to save ID photo. Please try again or skip.'
  } finally {
    uploadingPhoto.value = false
  }
}

function skipPhoto() {
  goToSuccess()
}

function goToSuccess() {
  stopCamera()
  clearCapturedPhoto()
  photoError.value = ''
  cameraError.value = ''
  screen.value = 'success'
  clearInactivityTimer()
  startCountdown()
}

watch(screen, async (next) => {
  if (next === 'photo') {
    clearCapturedPhoto()
    photoError.value = ''
    await startCamera()
    resetInactivityTimer()
  } else {
    stopCamera()
  }
})

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

// ── Inactivity reset (fires from form/photo if user walks away) ─────────────
function resetInactivityTimer() {
  clearTimeout(inactivityTimer!)
  if (screen.value !== 'welcome' && screen.value !== 'success') {
    const timeout = screen.value === 'photo' ? PHOTO_INACTIVITY_MS : INACTIVITY_MS
    inactivityTimer = setTimeout(() => reset(), timeout)
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
  stopCamera()
  clearCapturedPhoto()
  screen.value = 'welcome'
  form.value = { fullName: '', dob: '', appointmentTime: '' }
  appointmentInfo.value = null
  checkedInName.value = ''
  idPhotoSaved.value = false
  loading.value = false
  uploadingPhoto.value = false
  photoError.value = ''
  cameraError.value = ''
}

// ── API: look up appointment then check in ────────────────────────────────────
async function handleCheckIn() {
  loading.value = true

  const patientName = form.value.fullName.trim()

  try {
    // Step 1: find the patient's next upcoming appointment by name + DOB
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
      // Patient not found — alert already sent server-side; show success anyway
      // Skip photo step — no patient profile to attach an ID photo to
      checkedInName.value = patientName
      appointmentInfo.value = null
      goToSuccess()
      return
    }

    const { appointment } = await lookupRes.json()

    // Step 2: check in via the no-auth guest endpoint
    const checkinRes = await fetch(`/api/appointments/${appointment.id}/checkin-guest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_name: patientName,
        date_of_birth: form.value.dob,
        appointment_time: form.value.appointmentTime,
      }),
    })

    checkedInName.value = patientName
    // Show what we found even if the final checkin call failed
    appointmentInfo.value = checkinRes.ok ? appointment : null

    // Step 3: capture ID photo for the matched patient profile
    screen.value = 'photo'
    resetInactivityTimer()

  } catch (e) {
    console.error('Kiosk check-in error:', e)
    // Network/unexpected error — still send to success to avoid confusing patients
    checkedInName.value = patientName
    appointmentInfo.value = null
    goToSuccess()
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
  globalThis.addEventListener('mousemove', resetInactivityTimer)
  globalThis.addEventListener('touchstart', resetInactivityTimer)
})

onUnmounted(() => {
  stopCountdown()
  clearInactivityTimer()
  stopCamera()
  clearCapturedPhoto()
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
  padding: 40px 36px;
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
  box-sizing: border-box;
  text-align: center;
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
  opacity: 0.85;
}

.kiosk-btn.secondary {
  background: #f0f2f5;
  color: #334155;
  box-shadow: none;
}

.kiosk-btn.secondary:hover:not(:disabled) {
  background: #e3e6ec;
}

.kiosk-btn.secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.kiosk-btn.big {
  padding: 20px;
  font-size: 1.25rem;
}

.file-fallback {
  cursor: pointer;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
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

.camera-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  color: #cbd5e1;
  font-size: 1rem;
  line-height: 1.4;
}

.camera-placeholder.error {
  color: #fecaca;
}

.capture-canvas {
  display: none;
}

/* ── Form ──────────────────────────────────────────────────────────────────── */
.kiosk-form { text-align: left; }

.form-group {
  margin-bottom: 22px;
}

.kiosk-form label {
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

@media (max-width: 600px) {
  .kiosk-card {
    padding: 36px 24px;
  }

  .photo-card {
    padding: 28px 20px;
  }

  h1 { font-size: 2rem; }
  h2 { font-size: 1.5rem; }
}
</style>
