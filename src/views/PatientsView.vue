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

        <div class="detail-note">
          Future enhancement: editable patient details and clinical history.
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { Patient } from '@/types'

const patients = ref<Patient[]>([])
const selectedPatientId = ref<string | null>(null)
const loading = ref(false)
const error = ref('')

const selectedPatient = computed(() =>
  patients.value.find(p => p.id === selectedPatientId.value) || null
)

function selectPatient(patient: Patient) {
  selectedPatientId.value = patient.id
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

onMounted(() => {
  loadPatients()
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

@media (max-width: 900px) {
  .content.split {
    grid-template-columns: 1fr;
  }
}
</style>
