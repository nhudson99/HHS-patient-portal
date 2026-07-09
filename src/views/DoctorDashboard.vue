<template>
  <div class="doctor-dashboard">
    <!-- Calendar controls -->
    <div class="dashboard-header">
      <div class="controls">
        <div class="view-switcher">
          <button 
            @click="viewMode = 'day'"
            :class="{ active: viewMode === 'day' }"
            class="view-btn"
          >
            Day
          </button>
          <button 
            @click="viewMode = 'week'"
            :class="{ active: viewMode === 'week' }"
            class="view-btn"
          >
            Week
          </button>
          <button 
            @click="viewMode = 'month'"
            :class="{ active: viewMode === 'month' }"
            class="view-btn"
          >
            Month
          </button>
        </div>

        <div class="date-navigation">
          <button @click="previousPeriod" class="nav-btn">← Previous</button>
          <button @click="goToToday" class="nav-btn">Today</button>
          <button @click="nextPeriod" class="nav-btn">Next →</button>
          <span class="current-date">{{ formatDateRange() }}</span>
        </div>
      </div>
    </div>

    <!-- Calendar View -->
    <div class="calendar-container">
      <!-- Day View -->
      <div v-if="viewMode === 'day'" class="day-view">
        <div class="day-header">
          <h2>{{ formatDate(currentDate, 'EEEE, MMMM d, yyyy') }}</h2>
        </div>
        <div class="day-grid" @contextmenu.prevent>
          <div 
            v-for="hour in Array.from({ length: 24 }, (_, i) => i)"
            :key="`hour-${hour}`"
            class="hour-slot"
            @click="selectTimeSlot(hour, 0)"
            @contextmenu="showContextMenuForNewEvent($event)"
          >
            <div class="hour-label">{{ formatHour(hour) }}</div>
            <div class="events-container">
              <div 
                v-for="event in getEventsForTime(hour)"
                :key="event.id"
                class="event"
                :style="{ backgroundColor: event.color }"
                @click.stop="selectEvent(event)"
                @contextmenu.stop="showEventContextMenu($event, event)"
              >
                <div class="event-title">{{ event.title }}</div>
                <div class="event-time">{{ event.start_time || 'All day' }}</div>
                <button
                  v-if="isAppointmentEvent(event) && getAppointmentStatus(event) === 'pending'"
                  class="confirm-btn"
                  @click.stop="confirmAppointment(event)"
                >
                  ✓ Confirm
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Week View -->
      <div v-if="viewMode === 'week'" class="week-view">
        <div class="week-grid">
          <div 
            v-for="day in getWeekDays()"
            :key="day.toISOString()"
            class="day-column"
          >
            <div class="day-header">
              <div class="day-name">{{ formatDate(day, 'EEE') }}</div>
              <div class="day-date">{{ formatDate(day, 'd') }}</div>
            </div>
            <div 
              class="day-events"
              @click="selectDay(day)"
                @contextmenu.prevent="showContextMenuForNewEvent($event, day)"
            >
              <div 
                v-for="event in getEventsForDate(day)"
                :key="event.id"
                class="event"
                :style="{ backgroundColor: event.color }"
                @click.stop="selectEvent(event)"
                @contextmenu.stop="showEventContextMenu($event, event)"
              >
                <div class="event-title">{{ event.title }}</div>
                <div v-if="event.start_time" class="event-time">{{ formatEventTime(event.start_time) }}</div>
                <button
                  v-if="isAppointmentEvent(event) && getAppointmentStatus(event) === 'pending'"
                  class="confirm-btn"
                  @click.stop="confirmAppointment(event)"
                >
                  ✓ Confirm
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Month View -->
      <div v-if="viewMode === 'month'" class="month-view">
        <div class="month-header">
          <h2>{{ formatDate(currentDate, 'MMMM yyyy') }}</h2>
        </div>
        <div class="calendar-grid">
          <div class="weekday-header" v-for="day in ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']" :key="day">
            {{ day }}
          </div>
          <div 
            v-for="day in getMonthDays()"
            :key="day.toISOString()"
            class="calendar-day"
            :class="{ 'other-month': day.getMonth() !== currentDate.getMonth(), 'today': isToday(day) }"
            @click="selectDay(day)"
            @contextmenu.prevent="showContextMenuForNewEvent($event, day)"
          >
            <div class="day-number">{{ day.getDate() }}</div>
            <div class="day-events">
              <div 
                v-for="event in getEventsForDate(day)"
                :key="event.id"
                class="event"
                :style="{ backgroundColor: event.color }"
                @click.stop="selectEvent(event)"
                @contextmenu.stop="showEventContextMenu($event, event)"
              >
                <span class="event-dot">•</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Event Modal -->
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

    <!-- Context Menu -->
    <div 
      v-if="showContextMenu"
      class="context-menu"
      :style="{ top: contextMenuY + 'px', left: contextMenuX + 'px' }"
    >
      <div class="menu-item" @click="openNewEventModal">Add Event</div>
      <div v-if="contextEvent" class="menu-divider"></div>
      <div v-if="contextEvent" class="menu-item" @click="openEventForEdit">Edit</div>
      <div v-if="contextEvent" class="menu-item delete" @click="confirmDeleteEvent">Delete</div>
    </div>

    <!-- Confirm Dialog -->
    <div v-if="showConfirmDelete" class="modal-overlay" @click="showConfirmDelete = false">
      <div class="modal small" @click.stop>
        <div class="modal-content">
          <p>Are you sure you want to delete this event?</p>
          <div class="modal-actions">
            <button @click="deleteEvent" class="btn-danger">Delete</button>
            <button @click="showConfirmDelete = false" class="btn-secondary">Cancel</button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { 
  format, 
  startOfWeek, 
  endOfWeek, 
  eachDayOfInterval,
  startOfMonth,
  endOfMonth,
  isToday,
  addDays,
  subDays,
  addWeeks,
  subWeeks,
  addMonths,
  subMonths,
  parse
} from 'date-fns'

interface Event {
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
  created_at: string
  updated_at: string
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

const viewMode = ref<'day' | 'week' | 'month'>('week')
const currentDate = ref(new Date())
const events = ref<Event[]>([])
const showEventModal = ref(false)
const showConfirmDelete = ref(false)
const showContextMenu = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const contextEvent = ref<Event | null>(null)
const editingEvent = ref<Event | null>(null)

const colorOptions = [
  '#3b82f6',
  '#ef4444',
  '#10b981',
  '#f59e0b',
  '#8b5cf6',
  '#ec4899',
  '#06b6d4',
]

const eventForm = ref<EventForm>({
  title: '',
  event_date: formatDate(new Date(), 'yyyy-MM-dd'),
  event_type: 'appointment',
  description: '',
  color: '#3b82f6',
  is_all_day: false,
})

// Helper functions
function formatDate(date: Date | string, fmt: string): string {
  const d = typeof date === 'string' ? parse(date, 'yyyy-MM-dd', new Date()) : date
  return format(d, fmt)
}

function formatDateRange(): string {
  if (viewMode.value === 'day') {
    return formatDate(currentDate.value, 'MMMM d, yyyy')
  } else if (viewMode.value === 'week') {
    const start = startOfWeek(currentDate.value)
    const end = endOfWeek(currentDate.value)
    return `${formatDate(start, 'MMM d')} - ${formatDate(end, 'MMM d, yyyy')}`
  } else {
    return formatDate(currentDate.value, 'MMMM yyyy')
  }
}

function formatHour(hour: number): string {
  return format(new Date(2024, 0, 1, hour), 'h a')
}

function getWeekDays(): Date[] {
  const start = startOfWeek(currentDate.value)
  const end = endOfWeek(currentDate.value)
  return eachDayOfInterval({ start, end })
}

function getMonthDays(): Date[] {
  const start = startOfMonth(currentDate.value)
  const end = endOfMonth(currentDate.value)
  const weekStart = startOfWeek(start)
  const weekEnd = endOfWeek(end)
  return eachDayOfInterval({ start: weekStart, end: weekEnd })
}

function getEventsForDate(date: Date): Event[] {
  const dateStr = formatDate(date, 'yyyy-MM-dd')
  return events.value.filter(e => e.event_date === dateStr)
}

function getEventsForTime(hour: number): Event[] {
  const dateStr = formatDate(currentDate.value, 'yyyy-MM-dd')
  return events.value.filter(e => {
    if (e.event_date !== dateStr) return false
    if (!e.start_time) return false
    const eventHour = parseInt(e.start_time.split(':')[0])
    return eventHour === hour
  })
}

function previousPeriod() {
  if (viewMode.value === 'day') {
    currentDate.value = subDays(currentDate.value, 1)
  } else if (viewMode.value === 'week') {
    currentDate.value = subWeeks(currentDate.value, 1)
  } else {
    currentDate.value = subMonths(currentDate.value, 1)
  }
}

function nextPeriod() {
  if (viewMode.value === 'day') {
    currentDate.value = addDays(currentDate.value, 1)
  } else if (viewMode.value === 'week') {
    currentDate.value = addWeeks(currentDate.value, 1)
  } else {
    currentDate.value = addMonths(currentDate.value, 1)
  }
}

function goToToday() {
  currentDate.value = new Date()
}

function selectDay(date: Date) {
  currentDate.value = date
  viewMode.value = 'day'
}

function selectTimeSlot(hour: number, minute: number) {
  eventForm.value = {
    title: '',
    event_date: formatDate(currentDate.value, 'yyyy-MM-dd'),
    event_type: 'appointment',
    description: '',
    start_time: `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`,
    color: '#3b82f6',
    is_all_day: false,
  }
  editingEvent.value = null
  showEventModal.value = true
}

function selectEvent(event: Event) {
  editingEvent.value = event
  // Map Event to EventForm, ensuring description is always a string
  eventForm.value = {
    title: event.title,
    event_date: event.event_date,
    event_type: event.event_type,
    description: event.description ?? '',
    start_time: event.start_time,
    end_time: event.end_time,
    patient_id: event.patient_id,
    color: event.color,
    is_all_day: event.is_all_day,
  }
  showEventModal.value = true
}

function openNewEventModal() {
  eventForm.value = {
    title: '',
    event_date: formatDate(currentDate.value, 'yyyy-MM-dd'),
    event_type: 'appointment',
    description: '',
    color: '#3b82f6',
    is_all_day: false,
  }
  editingEvent.value = null
  showEventModal.value = true
  closeContextMenus()
}

function openEventForEdit() {
  if (contextEvent.value) {
    selectEvent(contextEvent.value)
  }
  closeContextMenus()
}

function closeEventModal() {
  showEventModal.value = false
  editingEvent.value = null
}

function showEventContextMenu(e: MouseEvent, event: Event) {
  e.preventDefault()
  contextEvent.value = event
  contextMenuX.value = e.clientX
  contextMenuY.value = e.clientY
  showContextMenu.value = true
}

function showContextMenuForNewEvent(e: MouseEvent, day?: Date) {
  e.preventDefault()
  if (day) {
    currentDate.value = day
  }
  contextEvent.value = null
  contextMenuX.value = e.clientX
  contextMenuY.value = e.clientY
  showContextMenu.value = true
}

function closeContextMenus() {
  showContextMenu.value = false
  contextEvent.value = null
}

function confirmDeleteEvent() {
  if (contextEvent.value) {
    showConfirmDelete.value = true
  }
  closeContextMenus()
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
          'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
        },
        body: payload,
      })

      if (!response.ok) {
        alert('Failed to update event')
        return
      }

      const data = await response.json()
      if (editingEvent.value) {
        const index = events.value.findIndex(e => e.id === editingEvent.value!.id)
        if (index !== -1) {
          events.value[index] = data.event
        }
      }
    } else {
      const response = await fetch('/api/events', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
        },
        body: payload,
      })

      if (!response.ok) {
        alert('Failed to create event')
        return
      }

      const data = await response.json()
      events.value.push(data.event)
    }

    closeEventModal()
  } catch (error) {
    console.error('Error saving event:', error)
    alert('Failed to save event')
  }
}

async function deleteEvent() {
  try {
    if (!contextEvent.value || !contextEvent.value.id) return

    const response = await fetch(`/api/events/${contextEvent.value.id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      },
    })

    if (!response.ok) {
      alert('Failed to delete event')
      return
    }

    events.value = events.value.filter(e => e.id !== contextEvent.value!.id)
    showConfirmDelete.value = false
    closeContextMenus()
  } catch (error) {
    console.error('Error deleting event:', error)
    alert('Failed to delete event')
  }
}

function isAppointmentEvent(event: Event): boolean {
  return typeof event.id === 'string' && event.id.startsWith('apt-')
}

function getAppointmentStatus(event: Event): string {
  // Title format is "Patient Name (status)"
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

async function confirmAppointment(event: Event) {
  if (!isAppointmentEvent(event)) return
  const appointmentId = event.id.replace('apt-', '')

  try {
    const response = await fetch(`/api/appointments/${appointmentId}/confirm`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      alert(data.error || 'Failed to confirm appointment')
      return
    }

    // Reload events to reflect the status change
    await loadEvents()
  } catch (error) {
    console.error('Error confirming appointment:', error)
    alert('Failed to confirm appointment')
  }
}

async function loadEvents() {
  try {
    // Use a range that covers month view (which includes surrounding weeks)
    const monthStart = startOfMonth(currentDate.value)
    const monthEnd = endOfMonth(currentDate.value)
    const weekStart = startOfWeek(currentDate.value)
    const weekEnd = endOfWeek(currentDate.value)
    
    // Use the earlier of monthStart/weekStart and later of monthEnd/weekEnd
    const rangeStartDate = new Date(Math.min(monthStart.getTime(), weekStart.getTime()))
    const rangeEndDate = new Date(Math.max(monthEnd.getTime(), weekEnd.getTime()))
    const start = formatDate(rangeStartDate, 'yyyy-MM-dd')
    const end = formatDate(rangeEndDate, 'yyyy-MM-dd')

    const response = await fetch(`/api/events?start_date=${start}&end_date=${end}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })

    if (response.ok) {
      const data = await response.json()
      events.value = data.events || []
    }
  } catch (error) {
    console.error('Error loading events:', error)
  }
}

watch(currentDate, () => {
  loadEvents()
})

onMounted(() => {
  loadEvents()
  document.addEventListener('click', closeContextMenus)
})
</script>

<style scoped>
.doctor-dashboard {
  background: #f5f5f5;
  min-height: 100vh;
}


.dashboard-header {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 2rem;
  background: white;
  padding: 1.5rem 2rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  gap: 1rem;
}

.controls {
  display: flex;
  gap: 2rem;
  align-items: center;
}

.view-switcher {
  display: flex;
  gap: 0.5rem;
}

.view-btn {
  padding: 0.5rem 1rem;
  border: 2px solid #ddd;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
}

.view-btn.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.view-btn:hover {
  border-color: #3b82f6;
}

.date-navigation {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.nav-btn {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
}

.nav-btn:hover {
  background: #f5f5f5;
}

.current-date {
  min-width: 200px;
  font-weight: 600;
  color: #333;
}

.calendar-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  overflow-x: clip;
  overflow-y: auto;
  max-height: 70vh;
  margin: 0 2rem 2rem 2rem;
}

.day-view {
  padding: 1.5rem;
  max-height: 65vh;
  overflow-y: auto;
}

.day-header {
  margin-bottom: 1.5rem;
  text-align: center;
}

.day-grid {
  display: grid;
  gap: 0.5rem;
}

.hour-slot {
  display: grid;
  grid-template-columns: 80px 1fr;
  gap: 1rem;
  padding: 1rem;
  background: #fafafa;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.3s;
  min-height: 80px;
}

.hour-slot:hover {
  background: #f0f0f0;
}

.hour-label {
  font-weight: 600;
  color: #666;
  font-size: 0.9rem;
}

.events-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: flex-start;
}

.week-view {
  padding: 1.5rem;
  max-height: 65vh;
  overflow-y: auto;
}

.week-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 1rem;
}

.day-column {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  background: #fafafa;
  border-radius: 4px;
}

.day-header {
  text-align: center;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #ddd;
}

.day-name {
  font-weight: 600;
  color: #666;
  font-size: 0.9rem;
}

.day-date {
  font-size: 1.2rem;
  font-weight: bold;
  color: #333;
}

.day-events {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;
  cursor: pointer;
  transition: background 0.3s;
  padding: 0.5rem;
  border-radius: 4px;
}

.day-events:hover {
  background: #f0f0f0;
}

.month-view {
  padding: 1.5rem;
  max-height: 65vh;
  overflow-y: auto;
}

.month-header {
  text-align: center;
  margin-bottom: 1.5rem;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 0.5rem;
}

.weekday-header {
  text-align: center;
  font-weight: 600;
  padding: 0.75rem;
  background: #f0f0f0;
  border-radius: 4px;
}

.calendar-day {
  min-height: 100px;
  padding: 0.5rem;
  background: #fafafa;
  border-radius: 4px;
  border: 1px solid #ddd;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  flex-direction: column;
}

.calendar-day:hover {
  background: #f0f0f0;
  border-color: #3b82f6;
}

.calendar-day.today {
  background: #ecf5ff;
  border-color: #3b82f6;
  border-width: 2px;
}

.calendar-day.other-month {
  background: #f9f9f9;
  color: #999;
}

.day-number {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.event {
  padding: 0.5rem;
  border-radius: 4px;
  color: white;
  font-size: 0.85rem;
  cursor: pointer;
  transition: transform 0.3s, box-shadow 0.3s;
}

.event:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}

.confirm-btn {
  margin-top: 4px;
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.9);
  color: #047857;
  border: 1px solid #047857;
  border-radius: 3px;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.confirm-btn:hover {
  background: #047857;
  color: white;
}

.event-time {
  font-size: 0.75rem;
  opacity: 1;
  color: #f8fafc;
}

.event-title {
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.event-time {
  font-size: 0.75rem;
  opacity: 0.9;
}

.event-dot {
  font-size: 1.2rem;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 8px;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 25px rgba(0,0,0,0.15);
}

.modal.small {
  max-width: 300px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #ddd;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #999;
}

.close-btn:hover {
  color: #333;
}

.modal-content {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #333;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: inherit;
  font-size: 1rem;
  box-sizing: border-box;
}

.form-group textarea {
  resize: vertical;
  min-height: 100px;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.color-picker {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.color-option {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  border: 2px solid #ddd;
  cursor: pointer;
  transition: all 0.3s;
}

.color-option:hover {
  transform: scale(1.1);
}

.color-option.selected {
  border-color: #333;
  box-shadow: 0 0 0 2px white, 0 0 0 4px #333;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #ddd;
}


.btn-primary,
.btn-secondary,
.btn-danger {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover {
  background: #2563eb;
}

.btn-secondary {
  background: #e5e7eb;
  color: #333;
}

.btn-secondary:hover {
  background: #d1d5db;
}

.btn-danger {
  background: #ef4444;
  color: white;
}

.btn-danger:hover {
  background: #dc2626;
}

.context-menu {
  position: fixed;
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-shadow: 0 10px 15px rgba(0,0,0,0.2);
  z-index: 1001;
  min-width: 150px;
}

.menu-item {
  padding: 0.75rem 1rem;
  cursor: pointer;
  transition: background 0.3s;
}

.menu-item:hover {
  background: #f5f5f5;
}

.menu-item.delete {
  color: #ef4444;
}

.menu-item.delete:hover {
  background: #fee2e2;
}

.menu-divider {
  height: 1px;
  background: #ddd;
  margin: 0.25rem 0;
}

@media (max-width: 768px) {
  .dashboard-header {
    flex-direction: column;
    gap: 0.75rem;
    padding: 1rem;
  }

  .controls {
    flex-direction: column;
    width: 100%;
    gap: 0.75rem;
  }

  .view-switcher {
    width: 100%;
    justify-content: center;
  }

  .view-btn {
    flex: 1;
    text-align: center;
  }

  .date-navigation {
    width: 100%;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.4rem;
  }

  .current-date {
    min-width: unset;
    width: 100%;
    text-align: center;
    font-size: 0.9rem;
    order: -1;
  }

  .calendar-container {
    margin: 0 0.75rem 1.5rem;
    overflow-x: auto;
    max-height: none;
  }

  .week-view,
  .month-view,
  .day-view {
    min-width: 640px;
    max-height: none;
  }

  .modal {
    width: 95%;
  }
}
</style>
