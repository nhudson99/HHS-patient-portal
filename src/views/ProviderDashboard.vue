<template>
  <div class="provider-dashboard">
    <div class="dashboard-header">
      <div class="header-main">
        <h1>Provider Day Schedule</h1>
        <p>View provider availability across the clinic. Patient details are shown only for your own schedule.</p>
      </div>
      <div class="date-navigation">
        <button @click="previousDay" class="nav-btn">← Previous</button>
        <button @click="goToToday" class="nav-btn">Today</button>
        <button @click="nextDay" class="nav-btn">Next →</button>
        <input
          :value="selectedDate"
          @input="onDateInput"
          type="date"
          class="date-input"
          aria-label="Selected schedule day"
        />
        <button @click="openNewEventModal" class="btn-primary add-event-btn">Add Event</button>
      </div>
    </div>

    <div class="schedule-container">
      <div class="schedule-header">
        <h2>{{ formatDate(currentDate, 'EEEE, MMMM d, yyyy') }}</h2>
      </div>

      <div v-if="isLoading" class="status-message">Loading day schedule...</div>
      <div v-else-if="loadError" class="status-message error-message">{{ loadError }}</div>

      <div v-else-if="dayEvents.length === 0" class="status-message empty-message">
        No appointments or events scheduled for this day.
      </div>

      <div v-else class="provider-columns" @contextmenu.prevent>
        <div v-for="provider in providerColumns" :key="provider.key" class="provider-column">
          <div class="provider-column-header">{{ provider.label }}</div>
          <div class="provider-events">
            <div
              v-for="event in provider.events"
              :key="event.id"
              class="schedule-item"
              :class="{ 'schedule-item--other': !event.is_own_event }"
            >
              <div class="event-topline">
                <span class="event-dot" :style="{ backgroundColor: event.color }"></span>
                <span class="event-title">{{ event.title }}</span>
              </div>
              <div class="event-meta">
                <span><strong>Time:</strong> {{ getEventTimeLabel(event) }}</span>
                <span v-if="event.is_own_event && event.patient_name"><strong>Patient:</strong> {{ event.patient_name }}</span>
                <span><strong>Type:</strong> {{ formatEventType(event.event_type) }}</span>
                <span v-if="isAppointmentEvent(event) && getAppointmentStatus(event)">
                  <strong>Status:</strong> {{ getAppointmentStatus(event) }}
                </span>
              </div>
              <p v-if="event.is_own_event && event.description" class="event-description">{{ event.description }}</p>
              <div v-if="event.is_own_event" class="actions-column">
                <button
                  v-if="isAppointmentEvent(event) && getAppointmentStatus(event) === 'pending'"
                  class="confirm-btn"
                  @click="confirmAppointment(event)"
                >
                  Confirm
                </button>
                <button
                  v-if="!isAppointmentEvent(event)"
                  class="btn-secondary action-btn"
                  @click="selectEvent(event)"
                >
                  Edit
                </button>
                <button
                  v-if="!isAppointmentEvent(event)"
                  class="btn-danger action-btn"
                  @click="deleteEvent(event)"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showEventModal" class="modal-overlay" @click="closeEventModal">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h2>{{ editingEvent ? 'Edit Event' : 'New Event' }}</h2>
          <button @click="closeEventModal" class="close-btn">✕</button>
        </div>
        <div class="modal-content">
          <div class="form-group">
            <label>Title *</label>
            <input v-model="eventForm.title" type="text" placeholder="Event title" />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Date *</label>
              <input v-model="eventForm.event_date" type="date" />
            </div>
            <div class="form-group">
              <label>Type *</label>
              <select v-model="eventForm.event_type">
                <option value="appointment">Appointment</option>
                <option value="reminder">Reminder</option>
                <option value="note">Note</option>
                <option value="blocked_time">Blocked Time</option>
                <option value="meeting">Meeting</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Start Time</label>
              <input v-model="eventForm.start_time" type="time" />
            </div>
            <div class="form-group">
              <label>End Time</label>
              <input v-model="eventForm.end_time" type="time" />
            </div>
          </div>

          <div class="form-group">
            <label>
              <input v-model="eventForm.is_all_day" type="checkbox" />
              All Day Event
            </label>
          </div>

          <div class="form-group">
            <label>Description</label>
            <textarea v-model="eventForm.description" placeholder="Event description"></textarea>
          </div>

          <div class="form-group">
            <label>Color</label>
            <div class="color-picker">
              <div
                v-for="color in colorOptions"
                :key="color"
                class="color-option"
                :style="{ backgroundColor: color }"
                :class="{ selected: eventForm.color === color }"
                @click="eventForm.color = color"
              ></div>
            </div>
          </div>

          <div class="modal-actions">
            <button @click="saveEvent" class="btn-primary">Save Event</button>
            <button @click="closeEventModal" class="btn-secondary">Cancel</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { addDays, format, parse } from 'date-fns'

interface DashboardEvent {
  id: string
  doctor_id: string
  patient_id?: string
  event_type: string
  title: string
  description?: string
  event_date: string
  start_time?: string
  end_time?: string
  color: string
  is_all_day: boolean
  provider_name?: string
  patient_name?: string
  appointment_status?: string
  is_own_event?: boolean
  created_at: string
  updated_at: string
}

interface ProviderColumn {
  key: string
  label: string
  events: DashboardEvent[]
}

interface EventForm {
  title: string
  event_date: string
  event_type: string
  description: string
  start_time?: string
  end_time?: string
  patient_id?: string
  color: string
  is_all_day: boolean
}

const currentDate = ref(new Date())
const events = ref<DashboardEvent[]>([])
const showEventModal = ref(false)
const editingEvent = ref<DashboardEvent | null>(null)
const isLoading = ref(false)
const loadError = ref('')

const colorOptions = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4']

const eventForm = ref<EventForm>({
  title: '',
  event_date: formatDate(new Date(), 'yyyy-MM-dd'),
  event_type: 'appointment',
  description: '',
  color: '#3b82f6',
  is_all_day: false
})

const selectedDate = computed(() => formatDate(currentDate.value, 'yyyy-MM-dd'))

const dayEvents = computed(() => {
  const dateStr = formatDate(currentDate.value, 'yyyy-MM-dd')
  return events.value
    .filter((event) => event.event_date === dateStr)
    .sort((left, right) => getSortTime(left).localeCompare(getSortTime(right)))
})

const providerColumns = computed<ProviderColumn[]>(() => {
  const grouped = new Map<string, ProviderColumn>()
  for (const event of dayEvents.value) {
    const providerLabel = event.provider_name?.trim() || 'Unknown provider'
    const providerKey = `${event.doctor_id || 'unknown'}::${providerLabel}`
    if (!grouped.has(providerKey)) {
      grouped.set(providerKey, {
        key: providerKey,
        label: providerLabel,
        events: []
      })
    }
    grouped.get(providerKey)?.events.push(event)
  }

  return Array.from(grouped.values())
    .sort((left, right) => left.label.localeCompare(right.label))
    .map((provider) => ({
      ...provider,
      events: [...provider.events].sort((left, right) => {
        const timeCompare = getSortTime(left).localeCompare(getSortTime(right))
        if (timeCompare !== 0) return timeCompare
        return left.title.localeCompare(right.title)
      })
    }))
})

function formatDate(date: Date | string, fmt: string): string {
  const parsed = typeof date === 'string' ? parse(date, 'yyyy-MM-dd', new Date()) : date
  return format(parsed, fmt)
}

function onDateInput(event: Event) {
  const value = (event.target as HTMLInputElement | null)?.value || ''
  if (!value) {
    return
  }
  currentDate.value = parse(value, 'yyyy-MM-dd', new Date())
}

function previousDay() {
  currentDate.value = addDays(currentDate.value, -1)
}

function nextDay() {
  currentDate.value = addDays(currentDate.value, 1)
}

function goToToday() {
  currentDate.value = new Date()
}

function getSortTime(event: DashboardEvent): string {
  if (!event.start_time) {
    return '00:00'
  }
  return event.start_time.slice(0, 5)
}

function getEventTimeLabel(event: DashboardEvent): string {
  if (event.is_all_day || !event.start_time) {
    return 'All day'
  }
  return formatEventTime(event.start_time)
}

function formatEventType(type: string): string {
  return type
    .split('_')
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ')
}

function isAppointmentEvent(event: DashboardEvent): boolean {
  return typeof event.id === 'string' && event.id.startsWith('apt-')
}

function getAppointmentStatus(event: DashboardEvent): string {
  if (event.appointment_status) {
    return event.appointment_status
  }
  const match = event.title.match(/\(([^)]+)\)$/)
  return match ? match[1] : ''
}

function formatEventTime(timeStr: string): string {
  if (!timeStr) return ''
  const [h, m] = timeStr.split(':')
  const hour = Number.parseInt(h, 10)
  const ampm = hour >= 12 ? 'PM' : 'AM'
  let displayHour = hour
  if (displayHour === 0) {
    displayHour = 12
  } else if (displayHour > 12) {
    displayHour -= 12
  }
  return `${displayHour}:${m} ${ampm}`
}

function openNewEventModal() {
  eventForm.value = {
    title: '',
    event_date: formatDate(currentDate.value, 'yyyy-MM-dd'),
    event_type: 'appointment',
    description: '',
    color: '#3b82f6',
    is_all_day: false
  }
  editingEvent.value = null
  showEventModal.value = true
}

function selectEvent(event: DashboardEvent) {
  editingEvent.value = event
  eventForm.value = {
    title: event.title,
    event_date: event.event_date,
    event_type: event.event_type,
    description: event.description ?? '',
    start_time: event.start_time,
    end_time: event.end_time,
    patient_id: event.patient_id,
    color: event.color,
    is_all_day: event.is_all_day
  }
  showEventModal.value = true
}

function closeEventModal() {
  showEventModal.value = false
  editingEvent.value = null
}

async function saveEvent() {
  try {
    if (!eventForm.value.title) {
      alert('Please enter a title')
      return
    }

    const payload = JSON.stringify(eventForm.value)

    if (editingEvent.value && editingEvent.value.id) {
      const response = await fetch(`/api/events/${editingEvent.value.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('sessionToken')}`
        },
        body: payload
      })

      if (!response.ok) {
        alert('Failed to update event')
        return
      }

    } else {
      const response = await fetch('/api/events', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('sessionToken')}`
        },
        body: payload
      })

      if (!response.ok) {
        alert('Failed to create event')
        return
      }

    }

    closeEventModal()
    await loadEvents()
  } catch (error) {
    console.error('Error saving event:', error)
    alert('Failed to save event')
  }
}

async function deleteEvent(event: DashboardEvent) {
  if (isAppointmentEvent(event)) {
    return
  }

  if (!confirm('Are you sure you want to delete this event?')) {
    return
  }

  try {
    const response = await fetch(`/api/events/${event.id}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })

    if (!response.ok) {
      alert('Failed to delete event')
      return
    }

    events.value = events.value.filter((item) => item.id !== event.id)
  } catch (error) {
    console.error('Error deleting event:', error)
    alert('Failed to delete event')
  }
}

async function confirmAppointment(event: DashboardEvent) {
  if (!isAppointmentEvent(event)) {
    return
  }

  const appointmentId = event.id.replace('apt-', '')

  try {
    const response = await fetch(`/api/appointments/${appointmentId}/confirm`, {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      alert(data.error || 'Failed to confirm appointment')
      return
    }

    await loadEvents()
  } catch (error) {
    console.error('Error confirming appointment:', error)
    alert('Failed to confirm appointment')
  }
}

async function loadEvents() {
  isLoading.value = true
  loadError.value = ''

  const day = formatDate(currentDate.value, 'yyyy-MM-dd')

  try {
    const response = await fetch(`/api/events?start_date=${day}&end_date=${day}&include_all_providers=true`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      loadError.value = data.error || 'Failed to load events'
      return
    }

    const data = await response.json()
    events.value = data.events || []
  } catch (error) {
    console.error('Error loading events:', error)
    loadError.value = 'Failed to load events'
  } finally {
    isLoading.value = false
  }
}

watch(currentDate, () => {
  loadEvents()
})

onMounted(() => {
  loadEvents()
})
</script>

<style scoped>
.provider-dashboard {
  background: #f5f5f5;
  min-height: 100vh;
  padding-bottom: 2rem;
}

.dashboard-header {
  background: white;
  margin-bottom: 1.5rem;
  padding: 1.25rem 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
}

.header-main h1 {
  margin: 0;
  font-size: 1.6rem;
}

.header-main p {
  margin: 0.35rem 0 1rem 0;
  color: #4b5563;
}

.date-navigation {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.nav-btn {
  padding: 0.5rem 0.9rem;
  border: 1px solid #d1d5db;
  background: white;
  border-radius: 4px;
  cursor: pointer;
}

.nav-btn:hover {
  background: #f3f4f6;
}

.date-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
}

.schedule-container {
  margin: 0 1.5rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.schedule-header {
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.schedule-header h2 {
  margin: 0;
  font-size: 1.2rem;
}

.status-message {
  padding: 2rem 1.5rem;
  color: #4b5563;
  text-align: center;
}

.error-message {
  color: #b91c1c;
}

.empty-message {
  color: #6b7280;
}

.provider-columns {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
  padding: 1rem 1.5rem 1.5rem;
}

.provider-column {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fafafa;
  overflow: hidden;
}

.provider-column-header {
  padding: 0.75rem 0.9rem;
  background: #e0ecff;
  color: #1e3a8a;
  font-weight: 700;
  border-bottom: 1px solid #dbeafe;
}

.provider-events {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.75rem;
}

.schedule-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  padding: 0.75rem;
}

.schedule-item--other {
  background: #f9fafb;
  border-style: dashed;
}

.schedule-item--other .event-title {
  color: #4b5563;
}

.event-topline {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}

.event-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.event-title {
  font-weight: 600;
  color: #111827;
}

.event-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  font-size: 0.9rem;
  color: #374151;
}

.event-description {
  margin: 0.5rem 0 0 0;
  color: #4b5563;
}

.actions-column {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.65rem;
}

.action-btn,
.confirm-btn {
  padding: 0.45rem 0.7rem;
  border-radius: 4px;
  border: 1px solid transparent;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
}

.confirm-btn {
  background: #047857;
  color: white;
}

.confirm-btn:hover {
  background: #065f46;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 8px;
  max-width: 520px;
  width: 92%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 25px rgba(0, 0, 0, 0.15);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #e5e7eb;
}

.close-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 1.2rem;
  color: #6b7280;
}

.modal-content {
  padding: 1.25rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 0.65rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
}

.form-group textarea {
  min-height: 90px;
  resize: vertical;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.color-picker {
  display: flex;
  gap: 0.65rem;
  flex-wrap: wrap;
}

.color-option {
  width: 34px;
  height: 34px;
  border-radius: 4px;
  cursor: pointer;
  border: 2px solid #e5e7eb;
}

.color-option.selected {
  border-color: #111827;
}

.modal-actions {
  margin-top: 1rem;
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.btn-primary,
.btn-secondary,
.btn-danger {
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  padding: 0.5rem 0.8rem;
}

.btn-primary {
  background: #2563eb;
  color: white;
}

.btn-primary:hover {
  background: #1d4ed8;
}

.btn-secondary {
  background: #f3f4f6;
  color: #111827;
  border-color: #d1d5db;
}

.btn-secondary:hover {
  background: #e5e7eb;
}

.btn-danger {
  background: #dc2626;
  color: white;
}

.btn-danger:hover {
  background: #b91c1c;
}

@media (max-width: 900px) {
  .provider-columns {
    grid-template-columns: 1fr;
    padding: 0.75rem 1rem 1rem;
  }

  .actions-column {
    justify-content: flex-start;
  }
}
</style>
