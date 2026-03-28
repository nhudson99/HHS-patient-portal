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
      <main class="admin-main">
        <div class="admin-welcome">
          <h2>Welcome, {{ adminSession.name || adminSession.email }}</h2>
          <p class="admin-email">{{ adminSession.email }}</p>
        </div>

        <div class="admin-tabs">
          <button
            class="tab-btn"
            :class="{ active: activeSection === 'doctors' }"
            @click="activeSection = 'doctors'"
          >
            Doctors
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeSection === 'patients' }"
            @click="activeSection = 'patients'"
          >
            Patients
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeSection === 'logs' }"
            @click="activeSection = 'logs'"
          >
            Error Logs
          </button>
        </div>

        <div v-if="actionMessage" class="admin-success-banner">{{ actionMessage }}</div>
        <div v-if="actionError" class="admin-error-banner">{{ actionError }}</div>

        <section v-if="activeSection === 'doctors'" class="admin-section">
          <div class="section-header">
            <h3>Doctors</h3>
            <div class="section-actions">
              <button class="section-btn" @click="resetDoctorForm">Add Doctor</button>
              <button class="section-btn secondary" @click="loadDoctors">Refresh</button>
            </div>
          </div>

          <form class="entity-form" @submit.prevent="submitDoctor">
            <h4>{{ editingDoctorId ? 'Edit Doctor' : 'Add Doctor' }}</h4>
            <div class="form-grid">
              <input v-model="doctorForm.username" :disabled="!!editingDoctorId" placeholder="Username" required />
              <input v-model="doctorForm.email" placeholder="Email" type="email" required />
              <input v-model="doctorForm.firstName" placeholder="First Name" required />
              <input v-model="doctorForm.lastName" placeholder="Last Name" required />
              <input v-model="doctorForm.specialty" placeholder="Specialty" required />
              <input v-model="doctorForm.licenseNumber" placeholder="License Number" required />
              <input v-model="doctorForm.licenseState" placeholder="License State" />
              <input v-model="doctorForm.phone" placeholder="Phone" />
              <input v-model="doctorForm.officeAddress" placeholder="Office Address" class="span-2" />
            </div>
            <label class="checkbox-row">
              <input type="checkbox" v-model="doctorForm.isActive" />
              Active account
            </label>
            <div class="form-actions">
              <button class="section-btn" type="submit">{{ editingDoctorId ? 'Save Doctor' : 'Create Doctor' }}</button>
              <button class="section-btn secondary" type="button" @click="resetDoctorForm">Cancel</button>
            </div>
          </form>

          <div v-if="newDoctorPassword" class="temp-password">
            Temporary doctor password: <strong>{{ newDoctorPassword }}</strong>
          </div>

          <div class="table-wrap">
            <table class="entity-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Specialty</th>
                  <th>License</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="doctor in doctors" :key="doctor.id">
                  <td>{{ doctor.first_name }} {{ doctor.last_name }}</td>
                  <td>{{ doctor.email }}</td>
                  <td>{{ doctor.specialty }}</td>
                  <td>{{ doctor.license_number }}</td>
                  <td>{{ doctor.is_active ? 'Active' : 'Disabled' }}</td>
                  <td class="actions-cell">
                    <button class="link-btn" @click="editDoctor(doctor)">Edit</button>
                    <button class="link-btn danger" @click="removeDoctor(doctor)">Delete</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section v-if="activeSection === 'patients'" class="admin-section">
          <div class="section-header">
            <h3>Patients</h3>
            <div class="section-actions">
              <button class="section-btn" @click="resetPatientForm">Add Patient</button>
              <button class="section-btn secondary" @click="loadPatients">Refresh</button>
            </div>
          </div>

          <form class="entity-form" @submit.prevent="submitPatient">
            <h4>{{ editingPatientId ? 'Edit Patient' : 'Add Patient' }}</h4>
            <div class="form-grid">
              <input v-model="patientForm.username" :disabled="!!editingPatientId" placeholder="Username" required />
              <input v-model="patientForm.email" placeholder="Email" type="email" required />
              <input v-model="patientForm.firstName" placeholder="First Name" required />
              <input v-model="patientForm.lastName" placeholder="Last Name" required />
              <input v-model="patientForm.dateOfBirth" type="date" placeholder="Date of Birth" />
              <input v-model="patientForm.phone" placeholder="Phone" />
              <input v-model="patientForm.address" placeholder="Address" class="span-2" />
              <input v-model="patientForm.city" placeholder="City" />
              <input v-model="patientForm.state" placeholder="State" />
              <input v-model="patientForm.zipCode" placeholder="Zip Code" />
              <input v-model="patientForm.emergencyContactName" placeholder="Emergency Contact Name" />
              <input v-model="patientForm.emergencyContactPhone" placeholder="Emergency Contact Phone" />
            </div>
            <label class="checkbox-row">
              <input type="checkbox" v-model="patientForm.isActive" />
              Active account
            </label>
            <div class="form-actions">
              <button class="section-btn" type="submit">{{ editingPatientId ? 'Save Patient' : 'Create Patient' }}</button>
              <button class="section-btn secondary" type="button" @click="resetPatientForm">Cancel</button>
            </div>
          </form>

          <div v-if="newPatientPassword" class="temp-password">
            Temporary patient password: <strong>{{ newPatientPassword }}</strong>
          </div>

          <div class="table-wrap">
            <table class="entity-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>DOB</th>
                  <th>Phone</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="patient in patients" :key="patient.id">
                  <td>{{ patient.first_name }} {{ patient.last_name }}</td>
                  <td>{{ patient.email }}</td>
                  <td>{{ formatDate(patient.date_of_birth) }}</td>
                  <td>{{ patient.phone || '—' }}</td>
                  <td>{{ patient.is_active ? 'Active' : 'Disabled' }}</td>
                  <td class="actions-cell">
                    <button class="link-btn" @click="editPatient(patient)">Edit</button>
                    <button class="link-btn danger" @click="removePatient(patient)">Delete</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section v-if="activeSection === 'logs'" class="admin-section">
          <div class="section-header">
            <h3>Error Logs</h3>
            <div class="section-actions">
              <button class="section-btn secondary" @click="loadErrorLogs">Refresh</button>
            </div>
          </div>

          <div class="table-wrap">
            <table class="entity-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>User</th>
                  <th>Action</th>
                  <th>Status</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="log in errorLogs" :key="log.id">
                  <td>{{ formatDateTime(log.created_at) }}</td>
                  <td>{{ log.username || 'system' }}</td>
                  <td>{{ log.action || 'n/a' }}</td>
                  <td>{{ log.status || 'error' }}</td>
                  <td>{{ log.error_message || 'No message' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { msalInstance, loginRequest } from '@/plugins/msal'
import { RouterLink } from 'vue-router'
import type { AuthenticationResult, AccountInfo } from '@azure/msal-browser'
import { adminSession, setAdminSession } from '@/store'

const ALLOWED_DOMAIN = 'hudsonitconsulting.com'

interface DoctorRecord {
  id: string
  first_name: string
  last_name: string
  specialty: string
  license_number: string
  license_state?: string
  phone?: string
  office_address?: string
  email: string
  is_active: boolean
  username?: string
}

interface PatientRecord {
  id: string
  first_name: string
  last_name: string
  date_of_birth?: string
  phone?: string
  email: string
  is_active: boolean
  username?: string
  address?: string
  city?: string
  state?: string
  zip_code?: string
  emergency_contact_name?: string
  emergency_contact_phone?: string
}

interface ErrorLogRecord {
  id: string
  username?: string
  action?: string
  status?: string
  error_message?: string
  created_at?: string
}

interface DoctorForm {
  username: string
  email: string
  firstName: string
  lastName: string
  specialty: string
  licenseNumber: string
  licenseState: string
  phone: string
  officeAddress: string
  isActive: boolean
}

interface PatientForm {
  username: string
  email: string
  firstName: string
  lastName: string
  dateOfBirth: string
  phone: string
  address: string
  city: string
  state: string
  zipCode: string
  emergencyContactName: string
  emergencyContactPhone: string
  isActive: boolean
}

const isSigningIn = ref(false)
const loginError = ref('')
const activeSection = ref<'doctors' | 'patients' | 'logs'>('doctors')
const doctors = ref<DoctorRecord[]>([])
const patients = ref<PatientRecord[]>([])
const errorLogs = ref<ErrorLogRecord[]>([])
const editingDoctorId = ref<string>('')
const editingPatientId = ref<string>('')
const actionError = ref('')
const actionMessage = ref('')
const newDoctorPassword = ref('')
const newPatientPassword = ref('')

const doctorForm = ref<DoctorForm>(createDoctorForm())
const patientForm = ref<PatientForm>(createPatientForm())

function createDoctorForm(): DoctorForm {
  return {
    username: '',
    email: '',
    firstName: '',
    lastName: '',
    specialty: '',
    licenseNumber: '',
    licenseState: '',
    phone: '',
    officeAddress: '',
    isActive: true
  }
}

function createPatientForm(): PatientForm {
  return {
    username: '',
    email: '',
    firstName: '',
    lastName: '',
    dateOfBirth: '',
    phone: '',
    address: '',
    city: '',
    state: '',
    zipCode: '',
    emergencyContactName: '',
    emergencyContactPhone: '',
    isActive: true
  }
}

function authHeaders(): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${adminSession.value?.idToken ?? ''}`
  }
}

async function apiRequest(url: string, options: RequestInit = {}) {
  const requestHeaders = (options.headers as Record<string, string> | undefined)

  const res = await fetch(url, {
    ...options,
    headers: {
      ...requestHeaders,
      ...authHeaders()
    }
  })

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.error || `Request failed (${res.status})`)
  }

  return res.json()
}

async function loadDoctors() {
  const data = await apiRequest('/api/admin/doctors')
  doctors.value = data.doctors ?? []
}

async function loadPatients() {
  const data = await apiRequest('/api/admin/patients')
  patients.value = data.patients ?? []
}

async function loadErrorLogs() {
  const data = await apiRequest('/api/admin/error-logs?limit=150')
  errorLogs.value = data.logs ?? []
}

async function loadAdminData() {
  if (!adminSession.value) {
    return
  }
  actionError.value = ''
  try {
    await Promise.all([loadDoctors(), loadPatients(), loadErrorLogs()])
  } catch (err: unknown) {
    actionError.value = err instanceof Error ? err.message : 'Failed to load admin data.'
  }
}

function clearActionBanners() {
  actionError.value = ''
  actionMessage.value = ''
}

function resetDoctorForm() {
  editingDoctorId.value = ''
  doctorForm.value = createDoctorForm()
}

function resetPatientForm() {
  editingPatientId.value = ''
  patientForm.value = createPatientForm()
}

function editDoctor(doctor: DoctorRecord) {
  editingDoctorId.value = doctor.id
  doctorForm.value = {
    username: doctor.username ?? '',
    email: doctor.email,
    firstName: doctor.first_name,
    lastName: doctor.last_name,
    specialty: doctor.specialty,
    licenseNumber: doctor.license_number,
    licenseState: doctor.license_state ?? '',
    phone: doctor.phone ?? '',
    officeAddress: doctor.office_address ?? '',
    isActive: doctor.is_active
  }
}

function editPatient(patient: PatientRecord) {
  editingPatientId.value = patient.id
  patientForm.value = {
    username: patient.username ?? '',
    email: patient.email,
    firstName: patient.first_name,
    lastName: patient.last_name,
    dateOfBirth: patient.date_of_birth?.slice(0, 10) ?? '',
    phone: patient.phone ?? '',
    address: patient.address ?? '',
    city: patient.city ?? '',
    state: patient.state ?? '',
    zipCode: patient.zip_code ?? '',
    emergencyContactName: patient.emergency_contact_name ?? '',
    emergencyContactPhone: patient.emergency_contact_phone ?? '',
    isActive: patient.is_active
  }
}

async function submitDoctor() {
  clearActionBanners()
  newDoctorPassword.value = ''

  try {
    if (editingDoctorId.value) {
      await apiRequest(`/api/admin/doctors/${editingDoctorId.value}`, {
        method: 'PUT',
        body: JSON.stringify(doctorForm.value)
      })
      actionMessage.value = 'Doctor updated successfully.'
    } else {
      const created = await apiRequest('/api/admin/doctors', {
        method: 'POST',
        body: JSON.stringify(doctorForm.value)
      })
      actionMessage.value = 'Doctor created successfully.'
      newDoctorPassword.value = created.temporaryPassword ?? ''
    }

    resetDoctorForm()
    await loadDoctors()
  } catch (err: unknown) {
    actionError.value = err instanceof Error ? err.message : 'Failed to save doctor.'
  }
}

async function submitPatient() {
  clearActionBanners()
  newPatientPassword.value = ''

  try {
    if (editingPatientId.value) {
      await apiRequest(`/api/admin/patients/${editingPatientId.value}`, {
        method: 'PUT',
        body: JSON.stringify(patientForm.value)
      })
      actionMessage.value = 'Patient updated successfully.'
    } else {
      const created = await apiRequest('/api/admin/patients', {
        method: 'POST',
        body: JSON.stringify(patientForm.value)
      })
      actionMessage.value = 'Patient created successfully.'
      newPatientPassword.value = created.temporaryPassword ?? ''
    }

    resetPatientForm()
    await loadPatients()
  } catch (err: unknown) {
    actionError.value = err instanceof Error ? err.message : 'Failed to save patient.'
  }
}

async function removeDoctor(doctor: DoctorRecord) {
  clearActionBanners()
  if (!confirm(`Delete doctor ${doctor.first_name} ${doctor.last_name}?`)) {
    return
  }

  try {
    await apiRequest(`/api/admin/doctors/${doctor.id}`, { method: 'DELETE' })
    actionMessage.value = 'Doctor deleted successfully.'
    await loadDoctors()
  } catch (err: unknown) {
    actionError.value = err instanceof Error ? err.message : 'Failed to delete doctor.'
  }
}

async function removePatient(patient: PatientRecord) {
  clearActionBanners()
  if (!confirm(`Delete patient ${patient.first_name} ${patient.last_name}?`)) {
    return
  }

  try {
    await apiRequest(`/api/admin/patients/${patient.id}`, { method: 'DELETE' })
    actionMessage.value = 'Patient deleted successfully.'
    await loadPatients()
  } catch (err: unknown) {
    actionError.value = err instanceof Error ? err.message : 'Failed to delete patient.'
  }
}

function formatDate(value?: string): string {
  if (!value) {
    return '—'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleDateString()
}

function formatDateTime(value?: string): string {
  if (!value) {
    return '—'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

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
  const search = new URLSearchParams(globalThis.location.search)
  if (search.has('code') || search.has('error') || search.has('state') || search.has('session_state')) {
    return true
  }

  const hash = globalThis.location.hash
  return hash.includes('code=') || hash.includes('error=') || hash.includes('state=')
}

function normalizeAdminUrl(): void {
  const target = '/admin'
  if (globalThis.location.pathname !== target || globalThis.location.search || globalThis.location.hash) {
    globalThis.history.replaceState(null, document.title, target)
  }
}

async function clearMsalAccount(account?: AccountInfo): Promise<void> {
  if (!account) {
    return
  }

  await msalInstance.logoutRedirect({
    account,
      postLogoutRedirectUri: `${globalThis.location.origin}/admin`
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
    const body = await verifyRes.json().catch(() => null)
    loginError.value = body.error ?? 'Server rejected the login. Please try again.'
    return false
  }

  const data = await verifyRes.json()
  const session = {
    email: data.email ?? email,
    name: data.name ?? result.account?.name ?? email,
    idToken: result.idToken
  }

  setAdminSession(session)
  await loadAdminData()
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

  // adminSession is initialized from sessionStorage by the store at module load.
  if (adminSession.value) {
    await loadAdminData()
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

.admin-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
}

.tab-btn {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #fff;
  color: #1e3a5f;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.tab-btn.active {
  background: #0f6cbd;
  color: #fff;
  border-color: #0f6cbd;
}

.admin-success-banner,
.admin-error-banner {
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 14px;
  font-size: 13px;
}

.admin-success-banner {
  background: #ecfdf5;
  border: 1px solid #86efac;
  color: #166534;
}

.admin-error-banner {
  background: #fff1f2;
  border: 1px solid #fda4af;
  color: #9f1239;
}

.admin-section {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.section-header h3 {
  margin: 0;
  color: #1e3a5f;
}

.section-actions {
  display: flex;
  gap: 8px;
}

.section-btn {
  border: none;
  border-radius: 7px;
  background: #0f6cbd;
  color: #fff;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.section-btn.secondary {
  background: #e2e8f0;
  color: #1e293b;
}

.entity-form {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 14px;
}

.entity-form h4 {
  margin: 0 0 10px;
  font-size: 14px;
  color: #334155;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.form-grid input {
  border: 1px solid #cbd5e1;
  border-radius: 7px;
  padding: 8px 10px;
  font-size: 13px;
}

.span-2 {
  grid-column: span 2;
}

.checkbox-row {
  margin-top: 10px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #334155;
}

.form-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.temp-password {
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 12px;
  font-size: 13px;
}

.table-wrap {
  overflow-x: auto;
}

.entity-table {
  width: 100%;
  border-collapse: collapse;
}

.entity-table th,
.entity-table td {
  border-bottom: 1px solid #e2e8f0;
  padding: 10px 8px;
  text-align: left;
  font-size: 13px;
  color: #334155;
  vertical-align: top;
}

.entity-table th {
  font-size: 12px;
  text-transform: uppercase;
  color: #64748b;
  letter-spacing: 0.04em;
}

.actions-cell {
  white-space: nowrap;
}

.link-btn {
  border: none;
  background: transparent;
  color: #0f6cbd;
  cursor: pointer;
  font-size: 12px;
  padding: 0;
  margin-right: 10px;
}

.link-btn.danger {
  color: #dc2626;
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
  background: #cbd5e1;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  color: #334155;
  cursor: not-allowed;
  align-self: flex-start;
}
</style>
