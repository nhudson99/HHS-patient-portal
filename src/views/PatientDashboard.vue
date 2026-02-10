<template>
  <div class="dashboard">
    <header class="header">
      <div class="header-content">
        <h1>🏥 Patient Portal</h1>
        <div class="user-info">
          <span>Welcome, {{ currentUser?.name }}</span>
          <button @click="handleLogout" class="logout-button">Logout</button>
        </div>
      </div>
    </header>

    <div class="main-content">
      <div class="tabs">
        <button 
          @click="activeTab = 'appointments'" 
          :class="{ active: activeTab === 'appointments' }"
          class="tab-button"
        >
          📅 My Appointments
        </button>
        <button 
          @click="activeTab = 'request'" 
          :class="{ active: activeTab === 'request' }"
          class="tab-button"
        >
          ➕ Request Appointment
        </button>
        <button 
          @click="activeTab = 'documents'" 
          :class="{ active: activeTab === 'documents' }"
          class="tab-button"
        >
          📄 Medical Documents
        </button>
      </div>

      <!-- My Appointments Tab -->
      <div v-if="activeTab === 'appointments'" class="tab-content">
        <h2>My Appointments</h2>
        <div v-if="appointments.length === 0" class="empty-state">
          <p>No appointments scheduled</p>
        </div>
        <div v-else class="appointments-list">
          <div 
            v-for="appointment in sortedAppointments" 
            :key="appointment.id"
            class="appointment-card"
            :class="appointment.status"
          >
            <div class="appointment-header">
              <div class="appointment-date">
                <span class="date">{{ formatDate(appointment.date) }}</span>
                <span class="time">{{ appointment.time }}</span>
              </div>
              <span class="status-badge" :class="appointment.status">
                {{ appointment.status.toUpperCase() }}
              </span>
            </div>
            <div class="appointment-body">
              <h3>Dr. {{ appointment.doctorName }}</h3>
              <p class="reason">{{ appointment.reason }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Request Appointment Tab -->
      <div v-if="activeTab === 'request'" class="tab-content">
        <h2>Request New Appointment</h2>
        <form @submit.prevent="handleAppointmentRequest" class="appointment-form">
          <div class="form-group">
            <label for="doctor">Select Doctor</label>
            <select id="doctor" v-model="appointmentForm.doctorId" required>
              <option value="">Choose a doctor...</option>
              <option value="1">Dr. Sarah Johnson</option>
            </select>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label for="date">Date</label>
              <input 
                id="date" 
                v-model="appointmentForm.date" 
                type="date" 
                :min="minDate"
                required 
              />
            </div>

            <div class="form-group">
              <label for="time">Time</label>
              <input 
                id="time" 
                v-model="appointmentForm.time" 
                type="time" 
                required 
              />
            </div>
          </div>

          <div class="form-group">
            <label for="reason">Reason for Visit</label>
            <textarea 
              id="reason" 
              v-model="appointmentForm.reason" 
              rows="4"
              placeholder="Please describe the reason for your appointment..."
              required
            ></textarea>
          </div>

          <button type="submit" class="submit-button">Submit Request</button>

          <div v-if="requestSuccess" class="success-message">
            ✓ Appointment request submitted successfully! It will appear in your appointments list as pending.
          </div>
        </form>
      </div>

      <!-- Medical Documents Tab -->
      <div v-if="activeTab === 'documents'" class="tab-content">
        <h2>Medical Documents</h2>
        <div v-if="documents.length === 0" class="empty-state">
          <p>No medical documents available</p>
        </div>
        <div v-else class="documents-list">
          <div 
            v-for="document in sortedDocuments" 
            :key="document.id"
            class="document-card"
          >
            <div class="document-header">
              <div>
                <span class="document-icon">{{ getDocumentIcon(document.type) }}</span>
                <h3>{{ document.title }}</h3>
              </div>
              <span class="document-date">{{ formatDate(document.date) }}</span>
            </div>
            <div class="document-type">{{ formatDocumentType(document.type) }}</div>
            <div class="document-content">{{ document.content }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  getCurrentUser, 
  getAppointmentsForPatient, 
  getDocumentsForPatient,
  createAppointmentRequest,
  getDoctorName,
  logout 
} from '@/store'
import type { Appointment, MedicalDocument } from '@/types'

const router = useRouter()
const currentUser = ref(getCurrentUser())
const activeTab = ref('appointments')
const appointments = ref<Appointment[]>([])
const documents = ref<MedicalDocument[]>([])
const requestSuccess = ref(false)

const appointmentForm = ref({
  doctorId: '',
  date: '',
  time: '',
  reason: ''
})

const minDate = computed(() => {
  const today = new Date()
  return today.toISOString().split('T')[0]
})

const sortedAppointments = computed(() => {
  return [...appointments.value].sort((a, b) => {
    const dateA = new Date(a.date + ' ' + a.time)
    const dateB = new Date(b.date + ' ' + b.time)
    return dateB.getTime() - dateA.getTime()
  })
})

const sortedDocuments = computed(() => {
  return [...documents.value].sort((a, b) => {
    const dateA = new Date(a.date)
    const dateB = new Date(b.date)
    return dateB.getTime() - dateA.getTime()
  })
})

const loadData = () => {
  if (currentUser.value) {
    appointments.value = getAppointmentsForPatient(currentUser.value.id)
    documents.value = getDocumentsForPatient(currentUser.value.id)
  }
}

const handleAppointmentRequest = () => {
  if (currentUser.value && appointmentForm.value.doctorId) {
    const doctorId = parseInt(appointmentForm.value.doctorId)
    createAppointmentRequest(
      currentUser.value.id,
      currentUser.value.name,
      doctorId,
      getDoctorName(doctorId),
      appointmentForm.value.date,
      appointmentForm.value.time,
      appointmentForm.value.reason
    )
    
    // Reset form
    appointmentForm.value = {
      doctorId: '',
      date: '',
      time: '',
      reason: ''
    }
    
    // Show success message
    requestSuccess.value = true
    setTimeout(() => {
      requestSuccess.value = false
    }, 5000)
    
    // Reload appointments
    loadData()
    
    // Switch to appointments tab
    setTimeout(() => {
      activeTab.value = 'appointments'
    }, 2000)
  }
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric' 
  })
}

const formatDocumentType = (type: string) => {
  const types: Record<string, string> = {
    lab_result: 'Laboratory Result',
    prescription: 'Prescription',
    imaging: 'Imaging Report',
    other: 'Other Document'
  }
  return types[type] || type
}

const getDocumentIcon = (type: string) => {
  const icons: Record<string, string> = {
    lab_result: '🧪',
    prescription: '💊',
    imaging: '🔬',
    other: '📋'
  }
  return icons[type] || '📄'
}

const handleLogout = () => {
  logout()
  router.push('/')
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: #f5f7fa;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px 0;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header h1 {
  font-size: 28px;
  margin: 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.logout-button {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid white;
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 14px;
  transition: background 0.3s;
}

.logout-button:hover {
  background: rgba(255, 255, 255, 0.3);
}

.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 30px 20px;
}

.tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.tab-button {
  background: white;
  border: 2px solid #ddd;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  color: #666;
  transition: all 0.3s;
}

.tab-button:hover {
  border-color: #667eea;
  color: #667eea;
}

.tab-button.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
}

.tab-content {
  background: white;
  padding: 30px;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.tab-content h2 {
  margin-bottom: 20px;
  color: #333;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
  font-size: 16px;
}

.appointments-list, .documents-list {
  display: grid;
  gap: 15px;
}

.appointment-card {
  background: #f8f9fa;
  border-left: 4px solid #667eea;
  padding: 20px;
  border-radius: 8px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.appointment-card:hover {
  transform: translateX(5px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.appointment-card.pending {
  border-left-color: #ffa726;
  background: #fff8e1;
}

.appointment-card.confirmed {
  border-left-color: #66bb6a;
  background: #f1f8f4;
}

.appointment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.appointment-date {
  display: flex;
  flex-direction: column;
}

.date {
  font-weight: 600;
  color: #333;
  font-size: 16px;
}

.time {
  color: #666;
  font-size: 14px;
}

.status-badge {
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.status-badge.pending {
  background: #ffa726;
  color: white;
}

.status-badge.confirmed {
  background: #66bb6a;
  color: white;
}

.appointment-body h3 {
  margin-bottom: 8px;
  color: #333;
}

.reason {
  color: #666;
  font-size: 14px;
}

.appointment-form {
  max-width: 600px;
}

.form-group {
  margin-bottom: 20px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

label {
  display: block;
  margin-bottom: 8px;
  color: #555;
  font-weight: 500;
}

input, select, textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.3s;
}

input:focus, select:focus, textarea:focus {
  outline: none;
  border-color: #667eea;
}

textarea {
  resize: vertical;
}

.submit-button {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 12px 30px;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  transition: transform 0.2s;
}

.submit-button:hover {
  transform: translateY(-2px);
}

.success-message {
  margin-top: 20px;
  padding: 15px;
  background: #e8f5e9;
  color: #2e7d32;
  border-radius: 6px;
  font-size: 14px;
}

.document-card {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  transition: transform 0.2s, box-shadow 0.2s;
}

.document-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.document-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.document-header > div {
  display: flex;
  align-items: center;
  gap: 10px;
}

.document-icon {
  font-size: 24px;
}

.document-header h3 {
  margin: 0;
  color: #333;
  font-size: 18px;
}

.document-date {
  color: #999;
  font-size: 14px;
}

.document-type {
  display: inline-block;
  background: #667eea;
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  margin-bottom: 12px;
}

.document-content {
  color: #666;
  line-height: 1.6;
  font-size: 14px;
}
</style>
