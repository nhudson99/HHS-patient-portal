<template>
  <div class="patients-page">
    <div class="content" :class="{ split: selectedPatient }">
      <aside class="patients-list">
        <div class="list-header">
          <h2>All Patients</h2>
          <span class="count">{{ patients.length }}</span>
        </div>
  <button class="add-patient-btn" @click="showAddPatientModal = true">+ New Patient</button>

        <div v-if="loading" class="state">Loading patients...</div>
        <div v-else-if="error" class="state error">{{ error }}</div>
        <div v-else-if="patients.length === 0" class="state">No patients found.</div>

        <button
          v-for="patient in patients"
          :key="patient.id"
          class="patient-item"
          :class="{ active: patient.id === selectedPatient?.id }"
          @click="selectPatient(patient)"
        >
          <div class="patient-name">
            {{ patient.first_name }} {{ patient.last_name }}
          </div>
          <div class="patient-meta">
            DOB: {{ formatDate(patient.date_of_birth) }}
          </div>
        </button>
      </aside>

      <section class="patient-detail" v-if="selectedPatient">
        <div class="detail-header">
          <h2>{{ selectedPatient.first_name }} {{ selectedPatient.last_name }}</h2>
          <span class="badge" :class="{ linked: !!selectedPatient.user_id }">
            {{ selectedPatient.user_id ? 'Portal Linked' : 'No Portal Account' }}
          </span>
        </div>

        <div class="detail-grid">
          <div class="detail-card">
            <p class="detail-label">Date of Birth</p>
            <div>{{ formatDate(selectedPatient.date_of_birth) }}</div>
          </div>
          <div class="detail-card">
            <p class="detail-label">Phone</p>
            <div>{{ selectedPatient.phone }}</div>
          </div>
          <div class="detail-card">
            <p class="detail-label">Address</p>
            <div>{{ selectedPatient.address || '—' }}</div>
          </div>
          <div class="detail-card">
            <p class="detail-label">Emergency Contact</p>
            <div>
              {{ selectedPatient.emergency_contact_name || '—' }}
              <span v-if="selectedPatient.emergency_contact_phone">
                ({{ selectedPatient.emergency_contact_phone }})
              </span>
            </div>
          </div>
          <div class="detail-card" v-if="selectedPatient.portal_email">
            <p class="detail-label">Portal Email</p>
            <div>{{ selectedPatient.portal_email }}</div>
          </div>
        </div>

        <div class="properties-section">
          <div class="properties-header">
            <h3>Notes</h3>
            <button class="add-btn" @click="openAddProperty">+ Add</button>
          </div>

          <div v-if="propertiesLoading" class="state">Loading properties...</div>
          <div v-else-if="propertiesError" class="state error">{{ propertiesError }}</div>
          <div v-else-if="patientProperties.length === 0" class="state">No properties yet.</div>

          <div class="accordion" v-else>
            <div
              v-for="prop in patientProperties"
              :key="prop.property_id"
              class="accordion-item"
            >
              <button class="accordion-header" @click="toggleProperty(prop.property_id)">
                <span>{{ prop.name }}</span>
                <span class="accordion-actions">
                  <span class="toggle-indicator">
                    {{ expandedProperties.has(prop.property_id) ? '−' : '+' }}
                  </span>
                  <button class="delete-btn" @click.stop="confirmDelete(prop)">Delete</button>
                </span>
              </button>
              <div v-if="expandedProperties.has(prop.property_id)" class="accordion-body">
                {{ prop.description || '—' }}
              </div>
            </div>
          </div>
        </div>

        <!-- Documents Section -->
        <div class="documents-section">
          <div class="documents-header">
            <h3>Documents</h3>
            <button class="add-btn" @click="triggerFileUpload">+ Upload</button>
            <input
              ref="fileInput"
              type="file"
              multiple
              style="display: none"
              @change="handleFileUpload"
            />
          </div>

          <div v-if="documentsLoading" class="state">Loading documents...</div>
          <div v-else-if="documentsError" class="state error">{{ documentsError }}</div>
          <div v-else-if="documents.length === 0" class="state">No documents yet.</div>

          <div class="documents-list" v-else>
            <div
              v-for="doc in documents"
              :key="doc.id"
              class="document-item"
            >
              <div class="document-info">
                <a
                  :href="`/api/documents/download/${doc.id}`"
                  class="document-link"
                  @click.prevent="downloadDocument(doc)"
                >
                  <span class="doc-icon">📄</span>
                  {{ doc.title }}
                </a>
                <span class="document-size">{{ formatFileSize(doc.file_size) }}</span>
              </div>
              <div class="document-actions">
                <button class="icon-btn rename-btn" @click="openRenameDialog(doc)" title="Rename">
                  ✏️
                </button>
                <button class="icon-btn delete-btn-icon" @click="confirmDeleteDocument(doc)" title="Delete">
                  🗑️
                </button>
              </div>
            </div>
          </div>

          <div v-if="uploadProgress" class="upload-progress">
            <span>Uploading...</span>
          </div>
        </div>

        <div class="detail-note">
          Future enhancement: editable patient details and clinical history.
        </div>
      </section>
    </div>

    <!-- Add Patient Modal -->
    <div v-if="showAddPatientModal" class="modal-overlay" @click="showAddPatientModal = false">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h2>Add New Patient</h2>
          <button class="close-btn" @click="showAddPatientModal = false">✕</button>
        </div>
        <div class="modal-content">
          <div v-if="addPatientError" class="error-banner">{{ addPatientError }}</div>
          <div v-if="addPatientSuccess" class="success-banner">
            Patient created. Temporary password: <strong>{{ newPatientPassword }}</strong>
            <br /><small>Share this with the patient — they will be prompted to change it on first login.</small>
          </div>
          <template v-if="!addPatientSuccess">
            <div class="form-row">
              <div class="form-group">
                <label>First Name *</label>
                <input v-model="addPatientForm.firstName" type="text" placeholder="First name" />
              </div>
              <div class="form-group">
                <label>Last Name *</label>
                <input v-model="addPatientForm.lastName" type="text" placeholder="Last name" />
              </div>
            </div>
            <div class="form-group">
              <label>Username *</label>
              <input v-model="addPatientForm.username" type="text" placeholder="Portal login username" />
            </div>
            <div class="form-group">
              <label>Email *</label>
              <input v-model="addPatientForm.email" type="email" placeholder="Patient email" />
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Date of Birth</label>
                <input v-model="addPatientForm.dateOfBirth" type="date" />
              </div>
              <div class="form-group">
                <label>Phone</label>
                <input v-model="addPatientForm.phone" type="tel" placeholder="Phone number" />
              </div>
            </div>
            <div class="form-group">
              <label>Address</label>
              <input v-model="addPatientForm.address" type="text" placeholder="Street address" />
            </div>
          </template>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="closeAddPatientModal">{{ addPatientSuccess ? 'Close' : 'Cancel' }}</button>
          <button v-if="!addPatientSuccess" class="btn-primary" :disabled="addPatientSaving" @click="submitAddPatient">
            {{ addPatientSaving ? 'Creating...' : 'Create Patient' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showAddDialog" class="modal-overlay" @click="closeAddDialog">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h2>New Property</h2>
          <button class="close-btn" @click="closeAddDialog">✕</button>
        </div>
        <div class="modal-content">
          <div class="form-group">
            <label for="property-name">Name *</label>
            <input id="property-name" v-model="propertyForm.name" type="text" placeholder="Property name" />
          </div>
          <div class="form-group">
            <label for="property-description">Description</label>
            <textarea
              id="property-description"
              v-model="propertyForm.description"
              rows="4"
              placeholder="Detailed notes"
            ></textarea>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="closeAddDialog">Cancel</button>
          <button class="btn-primary" @click="saveProperty">Save</button>
        </div>
      </div>
    </div>

    <div v-if="showDeleteConfirm" class="modal-overlay" @click="cancelDelete">
      <div class="modal small" @click.stop>
        <div class="modal-content">
          <p>Delete property "{{ pendingDelete?.name }}"?</p>
          <div class="modal-actions">
            <button class="btn-danger" @click="deleteProperty">Delete</button>
            <button class="btn-secondary" @click="cancelDelete">Cancel</button>
          </div>
        </div>
      </div>
    </div>

        <!-- Rename Document Modal -->
    <div v-if="showRenameDialog" class="modal-overlay" @click="closeRenameDialog">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h2>Rename Document</h2>
          <button class="close-btn" @click="closeRenameDialog">✕</button>
        </div>
        <div class="modal-content">
          <div class="form-group">
            <label for="rename-document-title">Title</label>
            <input id="rename-document-title" v-model="renameForm.title" type="text" placeholder="Document title" />
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="closeRenameDialog">Cancel</button>
          <button class="btn-primary" @click="renameDocument">Save</button>
        </div>
      </div>
    </div>

    <!-- Delete Document Confirmation -->
    <div v-if="showDeleteDocConfirm" class="modal-overlay" @click="cancelDeleteDocument">
      <div class="modal small" @click.stop>
        <div class="modal-content">
          <p>Delete document "{{ pendingDeleteDoc?.title }}"?</p>
          <div class="modal-actions">
            <button class="btn-danger" @click="deleteDocument">Delete</button>
            <button class="btn-secondary" @click="cancelDeleteDocument">Cancel</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { Patient, PatientProperty, PatientDocument } from '@/types'
import { logout } from '@/store'

const patients = ref<Patient[]>([])
const router = useRouter()
const selectedPatientId = ref<string | null>(null)
const loading = ref(false)
const error = ref('')
const patientProperties = ref<PatientProperty[]>([])
const propertiesLoading = ref(false)
const propertiesError = ref('')
const expandedProperties = ref<Set<number>>(new Set())
const showAddDialog = ref(false)
const showDeleteConfirm = ref(false)
const pendingDelete = ref<PatientProperty | null>(null)
const propertyForm = ref({
  name: '',
  description: ''
})

// Add patient state
const showAddPatientModal = ref(false)
const addPatientSaving = ref(false)
const addPatientError = ref('')
const addPatientSuccess = ref(false)
const newPatientPassword = ref('')
const addPatientForm = ref({
  firstName: '',
  lastName: '',
  username: '',
  email: '',
  dateOfBirth: '',
  phone: '',
  address: '',
})

function closeAddPatientModal() {
  showAddPatientModal.value = false
  addPatientSuccess.value = false
  addPatientError.value = ''
  newPatientPassword.value = ''
  addPatientForm.value = { firstName: '', lastName: '', username: '', email: '', dateOfBirth: '', phone: '', address: '' }
}

async function submitAddPatient() {
  addPatientError.value = ''
  const f = addPatientForm.value
  if (!f.firstName || !f.lastName || !f.username || !f.email) {
    addPatientError.value = 'First name, last name, username, and email are required.'
    return
  }
  addPatientSaving.value = true
  try {
    const response = await fetch('/api/patients', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`,
      },
      body: JSON.stringify(f),
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      addPatientError.value = data.error || 'Failed to create patient.'
      return
    }
    newPatientPassword.value = data.temporaryPassword || ''
    addPatientSuccess.value = true
    await loadPatients()
  } catch {
    addPatientError.value = 'Network error while creating patient.'
  } finally {
    addPatientSaving.value = false
  }
}
// Documents state
const documents = ref<PatientDocument[]>([])
const documentsLoading = ref(false)
const documentsError = ref('')
const uploadProgress = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const showRenameDialog = ref(false)
const showDeleteDocConfirm = ref(false)
const pendingDeleteDoc = ref<PatientDocument | null>(null)
const renameForm = ref({
  id: '',
  title: ''
})

const selectedPatient = computed(() =>
  patients.value.find(p => p.id === selectedPatientId.value) || null
)

function selectPatient(patient: Patient) {
  selectedPatientId.value = patient.id
}

function toggleProperty(propertyId: number) {
  const next = new Set(expandedProperties.value)
  if (next.has(propertyId)) {
    next.delete(propertyId)
  } else {
    next.add(propertyId)
  }
  expandedProperties.value = next
}

function openAddProperty() {
  propertyForm.value = { name: '', description: '' }
  showAddDialog.value = true
}

function closeAddDialog() {
  showAddDialog.value = false
}

function confirmDelete(prop: PatientProperty) {
  pendingDelete.value = prop
  showDeleteConfirm.value = true
}

function cancelDelete() {
  pendingDelete.value = null
  showDeleteConfirm.value = false
}

function formatDate(dateStr: string) {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
}

async function handleAuthFailure(response: Response): Promise<boolean> {
  if (response.status !== 401) {
    return false
  }

  logout()
  await router.replace('/')
  return true
}

async function loadPatients() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetch('/api/patients', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })

    if (await handleAuthFailure(response)) {
      return
    }

    if (!response.ok) {
      error.value = 'Failed to load patients'
      return
    }

    const data = await response.json()
    patients.value = data.patients || []
  } catch (err) {
    console.error('Failed to load patients:', err)
    error.value = 'Failed to load patients'
  } finally {
    loading.value = false
  }
}

async function loadProperties() {
  if (!selectedPatientId.value) {
    patientProperties.value = []
    return
  }

  propertiesLoading.value = true
  propertiesError.value = ''
  try {
    const response = await fetch(`/api/patient-properties/${selectedPatientId.value}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })

    if (await handleAuthFailure(response)) {
      return
    }

    if (!response.ok) {
      propertiesError.value = 'Failed to load properties'
      return
    }

    const data = await response.json()
    patientProperties.value = data.properties || []
    expandedProperties.value = new Set()
  } catch (err) {
    console.error('Failed to load properties:', err)
    propertiesError.value = 'Failed to load properties'
  } finally {
    propertiesLoading.value = false
  }
}

async function saveProperty() {
  if (!selectedPatientId.value || !propertyForm.value.name.trim()) return

  try {
    const response = await fetch(`/api/patient-properties/${selectedPatientId.value}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      },
      body: JSON.stringify({
        name: propertyForm.value.name.trim(),
        description: propertyForm.value.description
      })
    })

    if (await handleAuthFailure(response)) {
      return
    }

    if (!response.ok) {
      propertiesError.value = 'Failed to add property'
      return
    }

    const data = await response.json()
    patientProperties.value = [...patientProperties.value, data.property]
    expandedProperties.value = new Set(expandedProperties.value).add(data.property.property_id)
    showAddDialog.value = false
  } catch (err) {
    console.error('Failed to add property:', err)
    propertiesError.value = 'Failed to add property'
  }
}

async function deleteProperty() {
  if (!selectedPatientId.value || !pendingDelete.value) return

  try {
    const response = await fetch(
      `/api/patient-properties/${selectedPatientId.value}/${pendingDelete.value.property_id}`,
      {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
        }
      }
    )

    if (await handleAuthFailure(response)) {
      return
    }

    if (!response.ok) {
      propertiesError.value = 'Failed to delete property'
      return
    }

    patientProperties.value = patientProperties.value.filter(
      prop => prop.property_id !== pendingDelete.value?.property_id
    )
    cancelDelete()
  } catch (err) {
    console.error('Failed to delete property:', err)
    propertiesError.value = 'Failed to delete property'
  }
}

onMounted(() => {
  loadPatients()
})

watch(selectedPatientId, () => {
  loadProperties()
  loadDocuments()
})

// Document functions
async function loadDocuments() {
  if (!selectedPatientId.value) {
    documents.value = []
    return
  }

  documentsLoading.value = true
  documentsError.value = ''
  try {
    const response = await fetch(`/api/documents/${selectedPatientId.value}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })

    if (await handleAuthFailure(response)) {
      return
    }

    if (!response.ok) {
      documentsError.value = 'Failed to load documents'
      return
    }

    const data = await response.json()
    documents.value = data.documents || []
  } catch (err) {
    console.error('Failed to load documents:', err)
    documentsError.value = 'Failed to load documents'
  } finally {
    documentsLoading.value = false
  }
}

function triggerFileUpload() {
  fileInput.value?.click()
}

async function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const files = target.files
  
  if (!files || files.length === 0 || !selectedPatientId.value) return
  
  uploadProgress.value = true
  documentsError.value = ''
  
  try {
    const formData = new FormData()
    for (const file of Array.from(files)) {
      formData.append('files', file)
    }
    
    const response = await fetch(`/api/documents/${selectedPatientId.value}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      },
      body: formData
    })

    if (await handleAuthFailure(response)) {
      return
    }
    
    if (!response.ok) {
      const data = await response.json()
      documentsError.value = data.error || 'Failed to upload files'
      return
    }
    
    const data = await response.json()
    documents.value = [...data.documents, ...documents.value]
    
    if (data.errors && data.errors.length > 0) {
      documentsError.value = data.errors.join(', ')
    }
  } catch (err) {
    console.error('Failed to upload files:', err)
    documentsError.value = 'Failed to upload files'
  } finally {
    uploadProgress.value = false
    // Reset file input
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  }
}

async function downloadDocument(doc: PatientDocument) {
  try {
    const response = await fetch(`/api/documents/download/${doc.id}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })

    if (await handleAuthFailure(response)) {
      return
    }
    
    if (!response.ok) {
      documentsError.value = 'Failed to download document'
      return
    }
    
    const blob = await response.blob()
    const url = globalThis.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = doc.title || doc.file_name
    document.body.appendChild(a)
    a.click()
    globalThis.URL.revokeObjectURL(url)
    a.remove()
  } catch (err) {
    console.error('Failed to download document:', err)
    documentsError.value = 'Failed to download document'
  }
}

function openRenameDialog(doc: PatientDocument) {
  renameForm.value = { id: doc.id, title: doc.title }
  showRenameDialog.value = true
}

function closeRenameDialog() {
  showRenameDialog.value = false
}

async function renameDocument() {
  if (!renameForm.value.title.trim()) return
  
  try {
    const response = await fetch(`/api/documents/${renameForm.value.id}/rename`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      },
      body: JSON.stringify({ title: renameForm.value.title.trim() })
    })

    if (await handleAuthFailure(response)) {
      return
    }
    
    if (!response.ok) {
      documentsError.value = 'Failed to rename document'
      return
    }
    
    const data = await response.json()
    const idx = documents.value.findIndex(d => d.id === renameForm.value.id)
    if (idx !== -1) {
      documents.value[idx] = data.document
    }
    showRenameDialog.value = false
  } catch (err) {
    console.error('Failed to rename document:', err)
    documentsError.value = 'Failed to rename document'
  }
}

function confirmDeleteDocument(doc: PatientDocument) {
  pendingDeleteDoc.value = doc
  showDeleteDocConfirm.value = true
}

function cancelDeleteDocument() {
  pendingDeleteDoc.value = null
  showDeleteDocConfirm.value = false
}

async function deleteDocument() {
  if (!pendingDeleteDoc.value) return
  
  try {
    const response = await fetch(`/api/documents/${pendingDeleteDoc.value.id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })

    if (await handleAuthFailure(response)) {
      return
    }
    
    if (!response.ok) {
      documentsError.value = 'Failed to delete document'
      return
    }
    
    documents.value = documents.value.filter(d => d.id !== pendingDeleteDoc.value?.id)
    cancelDeleteDocument()
  } catch (err) {
    console.error('Failed to delete document:', err)
    documentsError.value = 'Failed to delete document'
  }
}

function formatFileSize(bytes: number): string {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  while (bytes >= 1024 && i < units.length - 1) {
    bytes /= 1024
    i++
  }
  return `${bytes.toFixed(1)} ${units[i]}`
}
</script>

<style scoped>
.patients-page {
  min-height: 100vh;
  background: #f5f7fb;
}

.content {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
  padding: 1.5rem 2rem 2rem;
}

.content.split {
  grid-template-columns: 320px 1fr;
}

.patients-list {
  background: white;
  border-radius: 10px;
  padding: 1rem;
  box-shadow: 0 2px 6px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.list-header h2 {
  margin: 0;
  font-size: 1.1rem;
}

.count {
  background: #eef2ff;
  color: #4338ca;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.85rem;
}

.patient-item {
  text-align: left;
  border: 1px solid #e5e7eb;
  background: #fafafa;
  border-radius: 8px;
  padding: 0.75rem 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
}

.patient-item:hover {
  border-color: #6366f1;
  background: #eef2ff;
}

.patient-item.active {
  border-color: #4f46e5;
  background: #e0e7ff;
}

.patient-name {
  font-weight: 600;
}

.patient-meta {
  color: #6b7280;
  font-size: 0.85rem;
}

.state {
  padding: 0.75rem;
  color: #6b7280;
  font-size: 0.9rem;
}

.state.error {
  color: #dc2626;
}

.patient-detail {
  background: white;
  border-radius: 10px;
  padding: 1.5rem;
  box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.detail-header h2 {
  margin: 0;
}

.badge {
  padding: 0.3rem 0.7rem;
  border-radius: 999px;
  font-size: 0.8rem;
  background: #f3f4f6;
  color: #6b7280;
}

.badge.linked {
  background: #dcfce7;
  color: #15803d;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}

.detail-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 0.9rem;
}

.detail-card label {
  display: block;
  color: #6b7280;
  font-size: 0.8rem;
  margin-bottom: 0.35rem;
}

.detail-note {
  margin-top: 1.5rem;
  color: #6b7280;
  font-size: 0.9rem;
}

.properties-section {
  margin-top: 2rem;
}

.properties-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.properties-header h3 {
  margin: 0;
}

.add-btn {
  border: 1px solid #c7d2fe;
  background: #eef2ff;
  color: #4338ca;
  border-radius: 6px;
  padding: 0.4rem 0.8rem;

  .add-patient-btn {
    display: block;
    width: calc(100% - 2rem);
    margin: 0.75rem 1rem 0;
    padding: 0.55rem 1rem;
    background: #4f46e5;
    color: #fff;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.9rem;
    cursor: pointer;
    transition: background 0.2s;
  }
  .add-patient-btn:hover {
    background: #4338ca;
  }

  .error-banner {
    background: #fef2f2;
    border: 1px solid #fca5a5;
    color: #b91c1c;
    border-radius: 6px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    font-size: 0.9rem;
  }

  .success-banner {
    background: #f0fdf4;
    border: 1px solid #86efac;
    color: #166534;
    border-radius: 6px;
    padding: 0.75rem 1rem;
    font-size: 0.9rem;
    line-height: 1.6;
  }
  font-weight: 600;
  cursor: pointer;
}

.accordion {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.accordion-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.accordion-header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: #f9fafb;
  border: none;
  cursor: pointer;
  font-weight: 600;
}

.accordion-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.toggle-indicator {
  font-size: 1.2rem;
  font-weight: 700;
}

.delete-btn {
  border: none;
  background: #fee2e2;
  color: #991b1b;
  padding: 0.35rem 0.7rem;
  border-radius: 6px;
  font-size: 0.85rem;
  cursor: pointer;
}

.detail-label {
  font-weight: 600;
  color: #374151;
  margin: 0 0 0.25rem;
}

.accordion-body {
  padding: 0.9rem 1rem;
  background: white;
  color: #374151;
  line-height: 1.4;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.modal {
  background: white;
  border-radius: 10px;
  width: 420px;
  max-width: 90%;
  padding: 1rem;
  box-shadow: 0 8px 20px rgba(0,0,0,0.2);
}

.modal.small {
  width: 320px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.2rem;
}

.close-btn {
  border: none;
  background: transparent;
  font-size: 1.2rem;
  cursor: pointer;
}

.modal-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.form-group input,
.form-group textarea {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 0.5rem 0.6rem;
}

.btn-primary {
  background: #4338ca;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
}

.btn-danger {
  background: #dc2626;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
}

/* Documents Section */
.documents-section {
  margin-top: 2rem;
}

.documents-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.documents-header h3 {
  margin: 0;
}

.documents-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.document-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.document-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  min-width: 0;
}

.document-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #4338ca;
  text-decoration: none;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.document-link:hover {
  text-decoration: underline;
}

.doc-icon {
  flex-shrink: 0;
}

.document-size {
  color: #6b7280;
  font-size: 0.8rem;
  flex-shrink: 0;
}

.document-actions {
  display: flex;
  gap: 0.5rem;
}

.icon-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0.35rem 0.5rem;
  border-radius: 6px;
  font-size: 1rem;
  transition: background 0.15s;
}

.icon-btn:hover {
  background: #e5e7eb;
}

.rename-btn:hover {
  background: #dbeafe;
}

.delete-btn-icon:hover {
  background: #fee2e2;
}

.upload-progress {
  margin-top: 0.75rem;
  padding: 0.5rem;
  background: #eef2ff;
  border-radius: 6px;
  color: #4338ca;
  font-size: 0.9rem;
  text-align: center;
}

@media (max-width: 900px) {
  .content {
    padding: 1rem;
  }

  .content.split {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 600px) {
  .content {
    padding: 0.75rem;
    gap: 0.75rem;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
