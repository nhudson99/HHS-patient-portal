<template>
  <div class="dashboard">
    <header class="header">
      <div class="header-content">
        <h1>🏥 Doctor Dashboard</h1>
        <div class="user-info">
          <span>Welcome, {{ currentUser?.name }}</span>
          <button @click="handleLogout" class="logout-button">Logout</button>
        </div>
      </div>
    </header>

    <div class="main-content">
      <div class="stats-cards">
        <div class="stat-card">
          <div class="stat-icon">📅</div>
          <div class="stat-info">
            <div class="stat-value">{{ appointments.length }}</div>
            <div class="stat-label">Total Appointments</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">⏳</div>
          <div class="stat-info">
            <div class="stat-value">{{ pendingCount }}</div>
            <div class="stat-label">Pending Requests</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">✅</div>
          <div class="stat-info">
            <div class="stat-value">{{ confirmedCount }}</div>
            <div class="stat-label">Confirmed</div>
          </div>
        </div>
      </div>

      <div class="calendar-section">
        <h2>Appointment Calendar</h2>
        <div class="calendar">
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
              <div class="status-badges">
                <span v-if="appointment.checkedIn" class="checkin-badge">CHECKED IN</span>
                <span class="status-badge" :class="appointment.status">
                  {{ appointment.status.toUpperCase() }}
                </span>
              </div>
            </div>
            <div class="appointment-body">
              <h3>{{ appointment.patientName }}</h3>
              <p class="reason">{{ appointment.reason }}</p>
            </div>
            <div class="appointment-footer" v-if="appointment.status === 'pending'">
              <button @click="confirmAppointment(appointment.id)" class="confirm-button">
                Confirm Appointment
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
import { useRouter } from 'vue-router'
import { getCurrentUser, getAppointmentsForDoctor, confirmAppointment as confirmApt, logout } from '@/store'
import type { Appointment } from '@/types'

const router = useRouter()
const currentUser = ref(getCurrentUser())
const appointments = ref<Appointment[]>([])

const pendingCount = computed(() => 
  appointments.value.filter(apt => apt.status === 'pending').length
)

const confirmedCount = computed(() => 
  appointments.value.filter(apt => apt.status === 'confirmed').length
)

const sortedAppointments = computed(() => {
  return [...appointments.value].sort((a, b) => {
    const dateA = new Date(a.date + ' ' + a.time)
    const dateB = new Date(b.date + ' ' + b.time)
    return dateA.getTime() - dateB.getTime()
  })
})

const loadAppointments = () => {
  if (currentUser.value) {
    appointments.value = getAppointmentsForDoctor(currentUser.value.id)
  }
}

const confirmAppointment = (appointmentId: number) => {
  if (confirmApt(appointmentId)) {
    loadAppointments()
  }
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { 
    weekday: 'short', 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric' 
  })
}

const handleLogout = () => {
  logout()
  router.push('/')
}

onMounted(() => {
  loadAppointments()
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

.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 15px;
}

.stat-icon {
  font-size: 40px;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #667eea;
}

.stat-label {
  color: #666;
  font-size: 14px;
}

.calendar-section {
  background: white;
  padding: 30px;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.calendar-section h2 {
  margin-bottom: 20px;
  color: #333;
}

.calendar {
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

.status-badges {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.checkin-badge {
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  background: #2196f3;
  color: white;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.appointment-body h3 {
  margin-bottom: 8px;
  color: #333;
}

.reason {
  color: #666;
  font-size: 14px;
}

.appointment-footer {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #ddd;
}

.confirm-button {
  background: #667eea;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  transition: background 0.3s;
}

.confirm-button:hover {
  background: #5568d3;
}
</style>
