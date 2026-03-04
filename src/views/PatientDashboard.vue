<template>
  <div class="dashboard">
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
        <div v-if="appointmentsLoading" class="empty-state">
          <p>Loading appointments...</p>
        </div>
        <div v-else-if="appointments.length === 0" class="empty-state">
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
                <span class="date">{{ formatDateTime(appointment.appointment_date) }}</span>
              </div>
              <span class="status-badge" :class="appointment.status">
                {{ appointment.status.toUpperCase() }}
              </span>
            </div>
            <div class="appointment-body">
              <h3>{{ appointment.doctor_name ? `Dr. ${appointment.doctor_name}` : 'Doctor Appointment' }}</h3>
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
              <option 
                v-for="doctor in doctors" 
                :key="doctor.id"
                :value="doctor.id"
              >
                Dr. {{ doctor.name }}
              </option>
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

          <div v-if="requestError" class="error-message">
            {{ requestError }}
          </div>

          <div v-if="requestSuccess" class="success-message">
            ✓ Appointment request submitted successfully! It will appear in your appointments list as pending.
          </div>
        </form>
      </div>

      <!-- Medical Documents Tab -->
      <div v-if="activeTab === 'documents'" class="tab-content">
        <h2>Medical Documents</h2>
        <div v-if="documentsLoading" class="empty-state">
          <p>Loading documents...</p>
        </div>
        <div v-else-if="documents.length === 0" class="empty-state">
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
                <span class="document-icon">{{ getDocumentIcon(document.document_type) }}</span>
                <h3>{{ document.title }}</h3>
              </div>
              <span class="document-date">{{ formatDateTime(document.document_date) }}</span>
            </div>
            <div class="document-type">{{ formatDocumentType(document.document_type) }}</div>
            <div v-if="document.description" class="document-description">{{ document.description }}</div>
            <div class="document-actions">
              <button 
                @click="downloadDocument(document)"
                class="download-link"
              >
                📥 Download {{ getFileExtension(document.file_name) }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const activeTab = ref('appointments')
const appointments = ref<any[]>([])
const documents = ref<any[]>([])
const doctors = ref<any[]>([])
const requestSuccess = ref(false)
const requestError = ref('')
const appointmentsLoading = ref(false)
const documentsLoading = ref(false)
const doctorsLoading = ref(false)

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
    const dateA = new Date(a.appointment_date)
    const dateB = new Date(b.appointment_date)
    return dateB.getTime() - dateA.getTime()
  })
})

const sortedDocuments = computed(() => {
  return [...documents.value].sort((a, b) => {
    const dateA = new Date(a.document_date || a.created_at)
    const dateB = new Date(b.document_date || b.created_at)
    return dateB.getTime() - dateA.getTime()
  })
})

// Load appointments from API
const loadAppointments = async () => {
  appointmentsLoading.value = true
  try {
    const response = await fetch('/api/appointments/patient', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })
    
    if (!response.ok) {
      console.error('Failed to load appointments')
      return
    }
    
    const data = await response.json()
    appointments.value = data.appointments || []
  } catch (err) {
    console.error('Load appointments error:', err)
  } finally {
    appointmentsLoading.value = false
  }
}

// Load documents from API
const loadDocuments = async () => {
  if (!localStorage.getItem('sessionToken')) return
  
  documentsLoading.value = true
  try {
    // Get the current patient's own record
    const patientResponse = await fetch('/api/patients/me', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })
    
    if (!patientResponse.ok) {
      console.error('Failed to get patient info')
      return
    }
    
    const patientData = await patientResponse.json()
    const currentPatient = patientData.patient
    
    if (!currentPatient) return
    
    const response = await fetch(`/api/documents/${currentPatient.id}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })
    
    if (!response.ok) {
      console.error('Failed to load documents')
      return
    }
    
    const data = await response.json()
    documents.value = data.documents || []
  } catch (err) {
    console.error('Load documents error:', err)
  } finally {
    documentsLoading.value = false
  }
}

// Load available doctors
const loadDoctors = async () => {
  doctorsLoading.value = true
  try {
    const response = await fetch('/api/patients/doctors', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })
    
    if (!response.ok) return

    const data = await response.json()
    doctors.value = (data.doctors || []).map((doctor: any) => ({
      id: doctor.id,
      name: `${doctor.first_name} ${doctor.last_name}`
    }))
  } catch (err) {
    console.error('Load doctors error:', err)
  } finally {
    doctorsLoading.value = false
  }
}

const handleAppointmentRequest = async () => {
  if (!localStorage.getItem('sessionToken') || !appointmentForm.value.doctorId) {
    requestError.value = 'Please fill in all fields'
    return
  }
  
  try {
    requestError.value = ''
    
    const response = await fetch('/api/appointments/request', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      },
      body: JSON.stringify({
        doctor_id: appointmentForm.value.doctorId,
        appointment_date: appointmentForm.value.date,
        appointment_time: appointmentForm.value.time,
        reason: appointmentForm.value.reason
      })
    })
    
    if (!response.ok) {
      const error = await response.json()
      requestError.value = error.error || 'Failed to request appointment'
      return
    }
    
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
    await loadAppointments()
    
    // Switch to appointments tab
    setTimeout(() => {
      activeTab.value = 'appointments'
    }, 2000)
  } catch (err) {
    requestError.value = 'An error occurred while requesting appointment'
    console.error('Appointment request error:', err)
  }
}

const downloadDocument = async (doc: any) => {
  try {
    const response = await fetch(`/api/documents/download/${doc.id}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })
    
    if (!response.ok) {
      console.error('Failed to download document')
      return
    }
    
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = doc.title || doc.file_name || 'document'
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  } catch (err) {
    console.error('Download error:', err)
  }
}

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return '—'
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  }) + ' at ' + date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatDocumentType = (type: string) => {
  const types: Record<string, string> = {
    lab_result: 'Laboratory Result',
    prescription: 'Prescription',
    imaging: 'Imaging Report',
    document: 'Document',
    other: 'Other Document'
  }
  return types[type] || type
}

const getDocumentIcon = (type: string) => {
  const icons: Record<string, string> = {
    lab_result: '🧪',
    prescription: '💊',
    imaging: '🔬',
    document: '📄',
    other: '📋'
  }
  return icons[type] || '📄'
}

const getFileExtension = (fileName: string) => {
  if (!fileName) return 'File'
  const parts = fileName.split('.')
  if (parts.length > 1) {
    return parts[parts.length - 1].toUpperCase()
  }
  return 'File'
}

const loadData = async () => {
  await Promise.all([
    loadAppointments(),
    loadDocuments(),
    loadDoctors()
  ])
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

.error-message {
  margin-top: 20px;
  padding: 15px;
  background: #ffebee;
  color: #c62828;
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
  margin-bottom: 15px;
}

.document-actions {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.download-link {
  display: inline-block;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 8px 16px;
  border-radius: 6px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  transition: transform 0.2s, box-shadow 0.2s;
}

.download-link:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.download-link:active {
  transform: translateY(0);
}
</style>
