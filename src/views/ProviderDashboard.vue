<template>
  <div class="provider-dashboard">
    <div class="dashboard-header">
      <div class="header-main">
        <h1>Scheduling Assistant</h1>
        <p>Clinic-wide day board. Patient details are shown only for your own schedule.</p>
      </div>
      <div class="toolbar">
        <button @click="goToToday" class="nav-btn today-btn">Today</button>
        <div class="date-navigation">
          <button @click="previousDay" class="nav-btn arrow-btn" aria-label="Previous day">←</button>
          <span class="current-date-label">{{ formattedDisplayDate }}</span>
          <button @click="nextDay" class="nav-btn arrow-btn" aria-label="Next day">→</button>
          <input
            :value="selectedDate"
            @input="onDateInput"
            type="date"
            class="date-input"
            aria-label="Selected schedule day"
          />
        </div>
        <div class="toolbar-actions">
          <label class="patient-search">
            <span class="sr-only">Search for Patient</span>
            <input
              v-model="patientSearch"
              type="search"
              class="patient-search-input"
              placeholder="Search for Patient"
              aria-label="Search for Patient"
            />
          </label>
          <button @click="openNewEventModal" class="btn-primary add-event-btn">Add Event</button>
        </div>
      </div>
    </div>

    <div class="schedule-container">
      <div v-if="isLoading" class="status-message">Loading day schedule...</div>
      <div v-else-if="loadError" class="status-message error-message">{{ loadError }}</div>

      <div v-else class="schedule-board" @contextmenu.prevent>
        <div class="board-scroll">
          <div class="board-header-row" :style="boardGridStyle">
            <div class="time-axis-spacer" aria-hidden="true"></div>
            <div
              v-for="provider in providerColumns"
              :key="`header-${provider.key}`"
              class="provider-column-header"
              :style="providerHeaderStyle(provider)"
            >
              {{ provider.label }} ({{ provider.layoutEvents.length }})
            </div>
            <div class="time-axis-spacer" aria-hidden="true"></div>
          </div>

          <div class="board-body" :style="{ ...boardGridStyle, height: `${gridHeight}px` }">
            <div class="time-axis time-axis--left">
              <div
                v-for="slot in timeSlots"
                :key="`left-${slot.minutes}`"
                class="time-slot-label"
                :class="{ 'time-slot-label--hour': slot.isHour }"
                :style="{ height: `${SLOT_HEIGHT_PX}px` }"
              >
                <span v-if="slot.isHour">{{ slot.hourLabel }}</span>
                <span v-else class="minute-marker">{{ slot.minuteLabel }}</span>
              </div>
            </div>

            <div
              v-for="provider in providerColumns"
              :key="provider.key"
              class="provider-column"
              :style="providerColumnStyle(provider)"
            >
              <div class="column-grid-lines" aria-hidden="true">
                <div
                  v-for="slot in timeSlots"
                  :key="`line-${provider.key}-${slot.minutes}`"
                  class="grid-line"
                  :class="{ 'grid-line--hour': slot.isHour }"
                  :style="{ height: `${SLOT_HEIGHT_PX}px` }"
                ></div>
              </div>

              <button
                v-for="item in provider.layoutEvents"
                :key="item.event.id"
                type="button"
                class="schedule-block"
                :class="scheduleBlockClasses(item.event)"
                :style="scheduleBlockStyle(item)"
                @click="selectScheduleEvent(item.event)"
              >
                <div class="block-title">{{ displayEventTitle(item.event) }}</div>
                <div class="block-meta">{{ getEventTimeLabel(item.event) }}</div>
                <div class="block-meta">{{ formatEventType(item.event.event_type) }}</div>
                <div
                  v-if="item.event.is_own_event && item.event.description"
                  class="block-description"
                >
                  {{ item.event.description }}
                </div>
                <div
                  v-if="isAppointmentEvent(item.event) && getAppointmentStatus(item.event)"
                  class="block-meta"
                >
                  {{ getAppointmentStatus(item.event) }}
                </div>
              </button>
            </div>

            <div class="time-axis time-axis--right">
              <div
                v-for="slot in timeSlots"
                :key="`right-${slot.minutes}`"
                class="time-slot-label"
                :class="{ 'time-slot-label--hour': slot.isHour }"
                :style="{ height: `${SLOT_HEIGHT_PX}px` }"
              >
                <span v-if="slot.isHour">{{ slot.hourLabel }}</span>
                <span v-else class="minute-marker">{{ slot.minuteLabel }}</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="providerColumns.length === 0" class="status-message empty-message">
          No providers available to display.
        </div>
      </div>

      <div v-if="selectedEvent" class="selection-panel">
        <div class="selection-panel-main">
          <div class="selection-title">{{ displayEventTitle(selectedEvent) }}</div>
          <div class="selection-meta">
            <span>{{ getEventTimeLabel(selectedEvent) }}</span>
            <span>{{ formatEventType(selectedEvent.event_type) }}</span>
            <span v-if="selectedEvent.provider_name">{{ selectedEvent.provider_name }}</span>
            <span v-if="isAppointmentEvent(selectedEvent) && getAppointmentStatus(selectedEvent)">
              Status: {{ getAppointmentStatus(selectedEvent) }}
            </span>
          </div>
          <p v-if="selectedEvent.is_own_event && selectedEvent.description" class="selection-description">
            {{ selectedEvent.description }}
          </p>
        </div>
        <div class="selection-actions">
          <template v-if="selectedEvent.is_own_event">
            <button
              v-if="isAppointmentEvent(selectedEvent) && getAppointmentStatus(selectedEvent) === 'pending'"
              class="confirm-btn"
              @click="confirmAppointment(selectedEvent)"
            >
              Confirm
            </button>
            <button
              v-if="!isAppointmentEvent(selectedEvent)"
              class="btn-secondary action-btn"
              @click="selectEvent(selectedEvent)"
            >
              Edit
            </button>
            <button
              v-if="!isAppointmentEvent(selectedEvent)"
              class="btn-danger action-btn"
              @click="deleteEvent(selectedEvent)"
            >
              Delete
            </button>
          </template>
          <button class="btn-secondary action-btn" @click="clearSelectedEvent">Close</button>
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

interface ClinicProvider {
  id: string
  first_name?: string
  last_name?: string
}

interface LaidOutEvent {
  event: DashboardEvent
  lane: number
  laneCount: number
  visibleStart: number
  visibleEnd: number
}

interface ProviderColumn {
  key: string
  doctorId: string
  label: string
  colorIndex: number
  layoutEvents: LaidOutEvent[]
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

interface TimeSlot {
  minutes: number
  isHour: boolean
  hourLabel: string
  minuteLabel: string
}

const START_HOUR = 7
const END_HOUR = 20
const SLOT_MINUTES = 15
const SLOT_HEIGHT_PX = 18
const DEFAULT_DURATION_MINUTES = 30
const GRID_START_MINUTES = START_HOUR * 60
const GRID_END_MINUTES = END_HOUR * 60

const PROVIDER_HEADER_COLORS = [
  '#6b7280',
  '#86efac',
  '#fde047',
  '#c4b5fd',
  '#fdba74',
  '#67e8f9',
  '#86efac',
  '#e7e5e4'
]

const PROVIDER_COLUMN_TINTS = [
  '#f3f4f6',
  '#f0fdf4',
  '#fefce8',
  '#f5f3ff',
  '#fff7ed',
  '#ecfeff',
  '#f0fdf4',
  '#fafaf9'
]

const currentDate = ref(new Date())
const events = ref<DashboardEvent[]>([])
const providers = ref<ClinicProvider[]>([])
const patientSearch = ref('')
const selectedEvent = ref<DashboardEvent | null>(null)
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

const formattedDisplayDate = computed(() => format(currentDate.value, 'MMMM do, yyyy'))

const timeSlots = computed<TimeSlot[]>(() => {
  const slots: TimeSlot[] = []
  for (let minutes = GRID_START_MINUTES; minutes < GRID_END_MINUTES; minutes += SLOT_MINUTES) {
    const hour = Math.floor(minutes / 60)
    const minute = minutes % 60
    slots.push({
      minutes,
      isHour: minute === 0,
      hourLabel: formatHourLabel(hour),
      minuteLabel: String(minute).padStart(2, '0')
    })
  }
  return slots
})

const gridHeight = computed(() => timeSlots.value.length * SLOT_HEIGHT_PX)

const dayEvents = computed(() => {
  const dateStr = formatDate(currentDate.value, 'yyyy-MM-dd')
  const query = patientSearch.value.trim().toLowerCase()

  return events.value
    .filter((event) => event.event_date === dateStr)
    .filter((event) => matchesPatientSearch(event, query))
    .sort((left, right) => getSortTime(left).localeCompare(getSortTime(right)))
})

const providerColumns = computed<ProviderColumn[]>(() => {
  const eventsByDoctor = new Map<string, DashboardEvent[]>()
  for (const event of dayEvents.value) {
    const doctorId = String(event.doctor_id || 'unknown')
    if (!eventsByDoctor.has(doctorId)) {
      eventsByDoctor.set(doctorId, [])
    }
    eventsByDoctor.get(doctorId)?.push(event)
  }

  const columns: ProviderColumn[] = []
  const seen = new Set<string>()

  providers.value.forEach((provider, index) => {
    const doctorId = String(provider.id)
    seen.add(doctorId)
    const label = formatProviderName(provider)
    columns.push({
      key: doctorId,
      doctorId,
      label,
      colorIndex: index % PROVIDER_HEADER_COLORS.length,
      layoutEvents: layoutProviderEvents(eventsByDoctor.get(doctorId) || [])
    })
  })

  for (const [doctorId, providerEvents] of eventsByDoctor.entries()) {
    if (seen.has(doctorId)) {
      continue
    }
    const label = providerEvents[0]?.provider_name?.trim() || 'Unknown provider'
    columns.push({
      key: doctorId,
      doctorId,
      label,
      colorIndex: columns.length % PROVIDER_HEADER_COLORS.length,
      layoutEvents: layoutProviderEvents(providerEvents)
    })
  }

  return columns.sort((left, right) => left.label.localeCompare(right.label))
})

const visibleEventIds = computed(() => {
  const ids = new Set<string>()
  for (const column of providerColumns.value) {
    for (const item of column.layoutEvents) {
      ids.add(item.event.id)
    }
  }
  return ids
})

const boardGridStyle = computed(() => ({
  '--provider-count': String(Math.max(providerColumns.value.length, 1))
}))

function formatDate(date: Date | string, fmt: string): string {
  const parsed = typeof date === 'string' ? parse(date, 'yyyy-MM-dd', new Date()) : date
  return format(parsed, fmt)
}

function formatProviderName(provider: ClinicProvider): string {
  const name = `${provider.first_name || ''} ${provider.last_name || ''}`.trim()
  return name || 'Unknown provider'
}

function matchesPatientSearch(event: DashboardEvent, query: string): boolean {
  if (!query) {
    return true
  }
  // Keep other providers' redacted availability visible on the clinic-wide board.
  if (!event.is_own_event) {
    return true
  }
  const haystack = `${event.patient_name || ''} ${event.title || ''}`.toLowerCase()
  return haystack.includes(query)
}

function formatHourLabel(hour: number): string {
  const ampm = hour >= 12 ? 'PM' : 'AM'
  let displayHour = hour % 12
  if (displayHour === 0) {
    displayHour = 12
  }
  return `${displayHour} ${ampm}`
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
  if (event.is_all_day || !event.start_time) {
    return '00:00'
  }
  return event.start_time.slice(0, 5)
}

function parseTimeToMinutes(timeStr?: string): number | null {
  if (!timeStr) {
    return null
  }
  const [h, m] = timeStr.split(':')
  const hour = Number.parseInt(h, 10)
  const minute = Number.parseInt(m || '0', 10)
  if (Number.isNaN(hour) || Number.isNaN(minute)) {
    return null
  }
  return hour * 60 + minute
}

function getEventStartMinutes(event: DashboardEvent): number {
  if (event.is_all_day) {
    return GRID_START_MINUTES
  }
  if (!event.start_time) {
    return GRID_START_MINUTES
  }
  return parseTimeToMinutes(event.start_time) ?? GRID_START_MINUTES
}

function getEventEndMinutes(event: DashboardEvent): number {
  if (event.is_all_day) {
    return GRID_END_MINUTES
  }
  const start = getEventStartMinutes(event)
  const end = parseTimeToMinutes(event.end_time)
  if (end != null && end > start) {
    return end
  }
  return start + DEFAULT_DURATION_MINUTES
}

/** Clamp to the visible grid window; null if the event does not intersect it. */
function getVisibleRange(event: DashboardEvent): { start: number; end: number } | null {
  const rawStart = getEventStartMinutes(event)
  const rawEnd = getEventEndMinutes(event)
  if (rawEnd <= GRID_START_MINUTES || rawStart >= GRID_END_MINUTES) {
    return null
  }
  const start = Math.max(rawStart, GRID_START_MINUTES)
  const end = Math.min(rawEnd, GRID_END_MINUTES)
  if (end <= start) {
    return null
  }
  return { start, end }
}

function eventsOverlap(
  left: { start: number; end: number },
  right: { start: number; end: number }
): boolean {
  return left.start < right.end && right.start < left.end
}

function layoutProviderEvents(providerEvents: DashboardEvent[]): LaidOutEvent[] {
  const visible = providerEvents
    .map((event) => {
      const range = getVisibleRange(event)
      if (!range) {
        return null
      }
      return {
        event,
        visibleStart: range.start,
        visibleEnd: range.end
      }
    })
    .filter((item): item is { event: DashboardEvent; visibleStart: number; visibleEnd: number } => item != null)
    .sort((left, right) => {
      if (left.visibleStart !== right.visibleStart) {
        return left.visibleStart - right.visibleStart
      }
      if (left.visibleEnd !== right.visibleEnd) {
        return left.visibleEnd - right.visibleEnd
      }
      return left.event.title.localeCompare(right.event.title)
    })

  if (visible.length === 0) {
    return []
  }

  const laneEnds: number[] = []
  const provisional: Array<{
    event: DashboardEvent
    visibleStart: number
    visibleEnd: number
    lane: number
  }> = []

  for (const item of visible) {
    let lane = laneEnds.findIndex((end) => end <= item.visibleStart)
    if (lane === -1) {
      lane = laneEnds.length
      laneEnds.push(item.visibleEnd)
    } else {
      laneEnds[lane] = item.visibleEnd
    }
    provisional.push({ ...item, lane })
  }

  // Within each overlapping cluster, laneCount is the max lane index + 1.
  return provisional.map((item) => {
    const cluster = new Set<string>([item.event.id])
    let changed = true
    while (changed) {
      changed = false
      for (const candidate of provisional) {
        if (cluster.has(candidate.event.id)) {
          continue
        }
        const overlapsCluster = provisional.some(
          (member) =>
            cluster.has(member.event.id)
            && eventsOverlap(
              { start: member.visibleStart, end: member.visibleEnd },
              { start: candidate.visibleStart, end: candidate.visibleEnd }
            )
        )
        if (overlapsCluster) {
          cluster.add(candidate.event.id)
          changed = true
        }
      }
    }

    let maxLane = 0
    for (const member of provisional) {
      if (cluster.has(member.event.id)) {
        maxLane = Math.max(maxLane, member.lane)
      }
    }

    return {
      event: item.event,
      lane: item.lane,
      laneCount: maxLane + 1,
      visibleStart: item.visibleStart,
      visibleEnd: item.visibleEnd
    }
  })
}

function getEventTimeLabel(event: DashboardEvent): string {
  if (event.is_all_day || !event.start_time) {
    return 'All day'
  }
  const startLabel = formatEventTime(event.start_time)
  if (!event.end_time) {
    return startLabel
  }
  return `${startLabel} – ${formatEventTime(event.end_time)}`
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

function displayEventTitle(event: DashboardEvent): string {
  if (event.is_own_event && event.patient_name) {
    return event.patient_name.toUpperCase()
  }
  if (event.is_own_event && isAppointmentEvent(event)) {
    return event.title.replace(/\s*\([^)]+\)$/, '').toUpperCase()
  }
  return event.title
}

function providerHeaderStyle(provider: ProviderColumn) {
  return {
    backgroundColor: PROVIDER_HEADER_COLORS[provider.colorIndex],
    color: '#1f2937'
  }
}

function providerColumnStyle(provider: ProviderColumn) {
  return {
    backgroundColor: PROVIDER_COLUMN_TINTS[provider.colorIndex]
  }
}

function scheduleBlockClasses(event: DashboardEvent) {
  return {
    'schedule-block--other': !event.is_own_event,
    'schedule-block--blocked': event.event_type === 'blocked_time',
    'schedule-block--meeting': event.event_type === 'meeting',
    'schedule-block--all-day': event.is_all_day,
    'schedule-block--selected': selectedEvent.value?.id === event.id
  }
}

function scheduleBlockStyle(item: LaidOutEvent) {
  const top = ((item.visibleStart - GRID_START_MINUTES) / SLOT_MINUTES) * SLOT_HEIGHT_PX
  const height = Math.max(
    ((item.visibleEnd - item.visibleStart) / SLOT_MINUTES) * SLOT_HEIGHT_PX,
    SLOT_HEIGHT_PX
  )
  const laneCount = Math.max(item.laneCount, 1)
  const widthPercent = 100 / laneCount
  const leftPercent = item.lane * widthPercent
  const background = item.event.color || '#dbeafe'

  return {
    top: `${top}px`,
    height: `${height}px`,
    left: `calc(${leftPercent}% + 2px)`,
    width: `calc(${widthPercent}% - 4px)`,
    right: 'auto',
    backgroundColor: background,
    zIndex: item.event.is_all_day ? 1 : 2 + item.lane
  }
}

function selectScheduleEvent(event: DashboardEvent) {
  selectedEvent.value = event
}

function clearSelectedEvent() {
  selectedEvent.value = null
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
    await loadSchedule()
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
    if (selectedEvent.value?.id === event.id) {
      clearSelectedEvent()
    }
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

    await loadSchedule()
  } catch (error) {
    console.error('Error confirming appointment:', error)
    alert('Failed to confirm appointment')
  }
}

async function loadProviders() {
  try {
    const response = await fetch('/api/patients/doctors', {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })

    if (!response.ok) {
      return
    }

    const data = await response.json()
    providers.value = data.doctors || []
  } catch (error) {
    console.error('Error loading providers:', error)
  }
}

async function loadEvents() {
  const day = formatDate(currentDate.value, 'yyyy-MM-dd')

  const response = await fetch(`/api/events?start_date=${day}&end_date=${day}&include_all_providers=true`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem('sessionToken')}`
    }
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.error || 'Failed to load events')
  }

  const data = await response.json()
  events.value = data.events || []
}

async function loadSchedule() {
  isLoading.value = true
  loadError.value = ''

  try {
    await Promise.all([loadProviders(), loadEvents()])
    if (selectedEvent.value && !visibleEventIds.value.has(selectedEvent.value.id)) {
      clearSelectedEvent()
    }
  } catch (error) {
    console.error('Error loading schedule:', error)
    loadError.value = error instanceof Error ? error.message : 'Failed to load events'
  } finally {
    isLoading.value = false
  }
}

watch(currentDate, () => {
  loadSchedule()
})

watch(visibleEventIds, (ids) => {
  if (selectedEvent.value && !ids.has(selectedEvent.value.id)) {
    clearSelectedEvent()
  }
})

onMounted(() => {
  loadSchedule()
})
</script>

<style scoped>
.provider-dashboard {
  background: #eef1f4;
  min-height: 100vh;
  padding-bottom: 2rem;
}

.dashboard-header {
  background: white;
  margin-bottom: 1rem;
  padding: 1rem 1.25rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.header-main h1 {
  margin: 0;
  font-size: 1.45rem;
  color: #1a3a5c;
}

.header-main p {
  margin: 0.3rem 0 0.85rem 0;
  color: #4b5563;
  font-size: 0.92rem;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1rem;
  align-items: center;
  justify-content: space-between;
}

.date-navigation,
.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.nav-btn {
  padding: 0.45rem 0.8rem;
  border: 1px solid #c5ced8;
  background: white;
  border-radius: 3px;
  cursor: pointer;
  font-weight: 600;
  color: #1f2937;
}

.nav-btn:hover {
  background: #f3f4f6;
}

.today-btn {
  background: #1a3a5c;
  color: white;
  border-color: #1a3a5c;
}

.today-btn:hover {
  background: #152e49;
}

.arrow-btn {
  color: #2563eb;
  font-size: 1.05rem;
  min-width: 2.25rem;
}

.current-date-label {
  font-weight: 700;
  color: #111827;
  min-width: 10rem;
  text-align: center;
}

.date-input {
  padding: 0.45rem 0.65rem;
  border: 1px solid #c5ced8;
  border-radius: 3px;
}

.patient-search-input {
  min-width: 14rem;
  padding: 0.45rem 0.7rem;
  border: 1px solid #c5ced8;
  border-radius: 3px;
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

.schedule-container {
  margin: 0 1rem;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  overflow: hidden;
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

.schedule-board {
  display: flex;
  flex-direction: column;
}

.board-scroll {
  overflow-x: auto;
  overflow-y: auto;
  max-height: calc(100vh - 220px);
}

.board-header-row,
.board-body {
  display: grid;
  grid-template-columns: 64px repeat(var(--provider-count, 1), minmax(170px, 1fr)) 64px;
  min-width: max-content;
  width: 100%;
}

.board-header-row {
  position: sticky;
  top: 0;
  z-index: 5;
  border-bottom: 1px solid #9ca3af;
}

.time-axis-spacer {
  background: #f8fafc;
  border-right: 1px solid #d1d5db;
  border-left: 1px solid #d1d5db;
  min-width: 64px;
}

.provider-column-header {
  padding: 0.55rem 0.65rem;
  font-weight: 700;
  font-size: 0.92rem;
  text-align: center;
  border-right: 1px solid #9ca3af;
  white-space: nowrap;
}

.board-body {
  position: relative;
}

.time-axis {
  background: #f8fafc;
  border-right: 1px solid #d1d5db;
  border-left: 1px solid #d1d5db;
}

.time-slot-label {
  box-sizing: border-box;
  padding: 0 0.35rem;
  font-size: 0.72rem;
  color: #4b5563;
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  border-top: 1px solid transparent;
}

.time-slot-label--hour {
  font-weight: 700;
  color: #111827;
  border-top-color: #9ca3af;
}

.minute-marker {
  color: #9ca3af;
  font-size: 0.65rem;
}

.provider-column {
  position: relative;
  border-right: 1px solid #9ca3af;
  min-width: 170px;
}

.column-grid-lines {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.grid-line {
  box-sizing: border-box;
  border-top: 1px solid #e5e7eb;
}

.grid-line--hour {
  border-top-color: #9ca3af;
}

.schedule-block {
  position: absolute;
  box-sizing: border-box;
  z-index: 2;
  border: 1px solid rgba(31, 41, 55, 0.25);
  border-radius: 2px;
  padding: 0.2rem 0.35rem;
  text-align: left;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 1px 1px rgba(0, 0, 0, 0.06);
}

.schedule-block:hover,
.schedule-block--selected {
  outline: 2px solid #1d4ed8;
  z-index: 8 !important;
}

.schedule-block--other {
  border-style: dashed;
  opacity: 0.95;
}

.schedule-block--blocked {
  border: 2px solid #dc2626;
  background-image: repeating-linear-gradient(
    -45deg,
    rgba(254, 226, 226, 0.55),
    rgba(254, 226, 226, 0.55) 6px,
    rgba(254, 242, 242, 0.85) 6px,
    rgba(254, 242, 242, 0.85) 12px
  );
}

.schedule-block--meeting {
  border-color: #7c3aed;
}

.schedule-block--all-day {
  border-style: solid;
  border-color: #4b5563;
  opacity: 0.88;
}

.block-title {
  font-size: 0.72rem;
  font-weight: 800;
  line-height: 1.15;
  color: #111827;
  word-break: break-word;
}

.block-meta,
.block-description {
  font-size: 0.68rem;
  line-height: 1.2;
  color: #1f2937;
  margin-top: 0.1rem;
}

.block-description {
  color: #374151;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.selection-panel {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: center;
  padding: 0.85rem 1rem;
  border-top: 1px solid #d1d5db;
  background: #f8fafc;
}

.selection-title {
  font-weight: 700;
  color: #111827;
}

.selection-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 0.25rem;
  color: #4b5563;
  font-size: 0.9rem;
}

.selection-description {
  margin: 0.4rem 0 0 0;
  color: #374151;
}

.selection-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
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
  .toolbar {
    align-items: stretch;
  }

  .patient-search-input {
    min-width: 0;
    width: 100%;
  }

  .board-scroll {
    max-height: calc(100vh - 280px);
  }
}
</style>
