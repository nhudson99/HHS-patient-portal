import type { User, Appointment, MedicalDocument } from '@/types'

// Hardcoded users for demo
export const users: User[] = [
  {
    id: 1,
    username: 'doctor1',
    password: 'doctor123',
    email: 'doctor1@hhs.local',
    role: 'doctor',
    name: 'Dr. Sarah Johnson'
  },
  {
    id: 2,
    username: 'patient1',
    password: 'patient123',
    email: 'patient1@hhs.local',
    role: 'patient',
    name: 'John Smith',
    birthday: '1990-05-15'
  }
]

// Hardcoded appointments for demo
export const appointments: Appointment[] = [
  {
    id: 1,
    patientId: 2,
    patientName: 'John Smith',
    doctorId: 1,
    doctorName: 'Dr. Sarah Johnson',
    date: new Date().toISOString().split('T')[0], // Today's date for demo/testing
    time: '10:00',
    reason: 'Annual checkup',
    status: 'confirmed'
  },
  {
    id: 2,
    patientId: 2,
    patientName: 'John Smith',
    doctorId: 1,
    doctorName: 'Dr. Sarah Johnson',
    date: '2026-02-20',
    time: '14:30',
    reason: 'Follow-up consultation',
    status: 'pending'
  },
  {
    id: 3,
    patientId: 2,
    patientName: 'John Smith',
    doctorId: 1,
    doctorName: 'Dr. Sarah Johnson',
    date: '2026-02-18',
    time: '09:00',
    reason: 'Blood pressure check',
    status: 'pending'
  }
]

// Hardcoded medical documents for demo
export const medicalDocuments: MedicalDocument[] = [
  {
    id: 1,
    patientId: 2,
    title: 'Blood Test Results',
    type: 'lab_result',
    date: '2026-01-15',
    content: 'All blood test results are within normal range. Cholesterol: 180 mg/dL, Blood Sugar: 95 mg/dL, Hemoglobin: 14.5 g/dL'
  },
  {
    id: 2,
    patientId: 2,
    title: 'Prescription - Blood Pressure Medication',
    type: 'prescription',
    date: '2026-01-20',
    content: 'Lisinopril 10mg - Take one tablet daily in the morning. Refills: 3'
  },
  {
    id: 3,
    patientId: 2,
    title: 'Chest X-Ray Report',
    type: 'imaging',
    date: '2025-12-10',
    content: 'Chest X-ray shows clear lung fields with no abnormalities detected. Heart size is normal.'
  }
]

// Current logged in user
export let currentUser: User | null = null

// Initialize from localStorage if available
const storedUser = localStorage.getItem('currentUser')
if (storedUser) {
  try {
    const userData = JSON.parse(storedUser)
    // Convert API user format to local User format
    currentUser = {
      id: parseInt(userData.id) || 0,
      username: userData.username,
      password: '', // Not stored in localStorage
      role: userData.role,
      name: userData.username, // Use username as name for now
      email: userData.email
    }
  } catch (e) {
    console.error('Failed to parse stored user:', e)
  }
}

export function setCurrentUser(user: User | null) {
  currentUser = user
}

export function getCurrentUser(): User | null {
  return currentUser
}

export function authenticateUser(username: string, password: string): User | null {
  const user = users.find(u => u.username === username && u.password === password)
  if (user) {
    setCurrentUser(user)
    return user
  }
  return null
}

export function logout() {
  setCurrentUser(null)
  localStorage.removeItem('sessionToken')
  localStorage.removeItem('currentUser')
}

export function getDoctorName(doctorId: number | string): string {
  const numId = typeof doctorId === 'string' ? parseInt(doctorId) : doctorId
  const doctor = users.find(u => u.id === numId && u.role === 'doctor')
  return doctor ? (doctor.name || doctor.username) : 'Unknown Doctor'
}

export function getAppointmentsForDoctor(doctorId: number | string): Appointment[] {
  const numId = typeof doctorId === 'string' ? parseInt(doctorId) : doctorId
  return appointments.filter(apt => apt.doctorId === numId)
}

export function getAppointmentsForPatient(patientId: number | string): Appointment[] {
  const numId = typeof patientId === 'string' ? parseInt(patientId) : patientId
  return appointments.filter(apt => apt.patientId === numId)
}

export function getDocumentsForPatient(patientId: number | string): MedicalDocument[] {
  const numId = typeof patientId === 'string' ? parseInt(patientId) : patientId
  return medicalDocuments.filter(doc => doc.patientId === numId)
}

export function confirmAppointment(appointmentId: number | string): boolean {
  const numId = typeof appointmentId === 'string' ? parseInt(appointmentId) : appointmentId
  const appointment = appointments.find(apt => apt.id === numId)
  if (appointment) {
    appointment.status = 'confirmed'
    return true
  }
  return false
}

export function createAppointmentRequest(
  patientId: number | string,
  patientName: string,
  doctorId: number | string,
  doctorName: string,
  date: string,
  time: string,
  reason: string
): Appointment {
  const numPatientId = typeof patientId === 'string' ? parseInt(patientId) : patientId
  const numDoctorId = typeof doctorId === 'string' ? parseInt(doctorId) : doctorId
  
  // Find max ID to avoid duplicates
  const maxId = appointments.length > 0 
    ? Math.max(...appointments.map(apt => apt.id))
    : 0
  
  const newAppointment: Appointment = {
    id: maxId + 1,
    patientId: numPatientId,
    patientName,
    doctorId: numDoctorId,
    doctorName,
    date,
    time,
    reason,
    status: 'pending'
  }
  appointments.push(newAppointment)
  return newAppointment
}

export function checkInForAppointment(appointmentId: number | string): boolean {
  const numId = typeof appointmentId === 'string' ? parseInt(appointmentId) : appointmentId
  const appointment = appointments.find(apt => apt.id === numId)
  if (appointment) {
    appointment.checkedIn = true
    appointment.checkInTime = new Date().toISOString()
    return true
  }
  return false
}

export function findAppointmentByPatientInfo(name: string, birthday: string): Appointment | null {
  // Find today's appointments for the patient
  const today = new Date().toISOString().split('T')[0]
  
  // Find user with matching name and birthday for validation
  const user = users.find(u => 
    (u.name || u.username).toLowerCase() === name.toLowerCase() &&
    u.birthday === birthday &&
    u.role === 'patient'
  )
  
  // If no user found with matching name and birthday, return null
  if (!user) {
    return null
  }
  
  // Find appointment for this user today
  const appointment = appointments.find(apt => 
    apt.patientId === user.id &&
    apt.date === today
  )
  
  return appointment || null
}
