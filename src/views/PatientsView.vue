<template>
  <div class="patients-page">
    <header class="page-header">
      <div class="header-content">
        <h1>Patients</h1>
        <p class="subtitle">Browse and view patient profiles</p>
      </div>
    </header>

    <div class="content" :class="{ split: selectedPatient }">
      <aside class="patients-list">
        <div class="list-header">
          <h2>All Patients</h2>
          <span class="count">{{ patients.length }}</span>
        </div>

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
            <label>Date of Birth</label>
            <div>{{ formatDate(selectedPatient.date_of_birth) }}</div>
          </div>
          <div class="detail-card">
            <label>Phone</label>
            <div>{{ selectedPatient.phone }}</div>
          </div>
          <div class="detail-card">
            <label>Address</label>
            <div>{{ selectedPatient.address || '—' }}</div>
          </div>
          <div class="detail-card">
            <label>Emergency Contact</label>
            <div>
              {{ selectedPatient.emergency_contact_name || '—' }}
              <span v-if="selectedPatient.emergency_contact_phone">
                ({{ selectedPatient.emergency_contact_phone }})
              </span>
            </div>
          </div>
          <div class="detail-card" v-if="selectedPatient.portal_email">
            <label>Portal Email</label>
            <div>{{ selectedPatient.portal_email }}</div>
          </div>
        </div>

        <div class="properties-section">
          <div class="properties-header">
            <h3>Patient Properties</h3>
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

        <div class="detail-note">
          Future enhancement: editable patient details and clinical history.
        </div>
      </section>
    </div>

    <div v-if="showAddDialog" class="modal-overlay" @click="closeAddDialog">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h2>New Property</h2>
          <button class="close-btn" @click="closeAddDialog">✕</button>
        </div>
        <div class="modal-content">
          <div class="form-group">
            <label>Name *</label>
            <input v-model="propertyForm.name" type="text" placeholder="Property name" />
          </div>
          <div class="form-group">
            <label>Description</label>
            <textarea
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import type { Patient, PatientProperty } from '@/types'

const patients = ref<Patient[]>([])
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

async function loadPatients() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetch('/api/patients', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })

    if (!response.ok) {
      error.value = 'Failed to load patients'
      return
    }

    const data = await response.json()
    patients.value = data.patients || []
  } catch (err) {
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

    if (!response.ok) {
      propertiesError.value = 'Failed to load properties'
      return
    }

    const data = await response.json()
    patientProperties.value = data.properties || []
    expandedProperties.value = new Set()
  } catch (err) {
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

    if (!response.ok) {
      propertiesError.value = 'Failed to add property'
      return
    }

    const data = await response.json()
    patientProperties.value = [...patientProperties.value, data.property]
    expandedProperties.value = new Set(expandedProperties.value).add(data.property.property_id)
    showAddDialog.value = false
  } catch (err) {
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

    if (!response.ok) {
      propertiesError.value = 'Failed to delete property'
      return
    }

    patientProperties.value = patientProperties.value.filter(
      prop => prop.property_id !== pendingDelete.value?.property_id
    )
    cancelDelete()
  } catch (err) {
    propertiesError.value = 'Failed to delete property'
  }
}

onMounted(() => {
  loadPatients()
})

watch(selectedPatientId, () => {
  loadProperties()
})
</script>

<style scoped>
.patients-page {
  min-height: 100vh;
  background: #f5f7fb;
}

.page-header {
  background: white;
  border-bottom: 1px solid #e5e7eb;
  padding: 1.5rem 2rem;
}

.header-content h1 {
  margin: 0;
  font-size: 1.75rem;
}

.subtitle {
  margin: 0.25rem 0 0;
  color: #6b7280;
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
  color: #dc2626;
  padding: 0.35rem 0.7rem;
  border-radius: 6px;
  font-size: 0.85rem;
  cursor: pointer;
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

@media (max-width: 900px) {
  .content.split {
    grid-template-columns: 1fr;
  }
}
</style>
