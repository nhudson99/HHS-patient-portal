export interface User {
  id: number | string
  username: string
  password?: string
  email?: string
  role: 'doctor' | 'patient'
  name?: string
  birthday?: string
}

export interface Appointment {
  id: number
  patientId: number
  patientName: string
  doctorId: number
  doctorName: string
  date: string
  time: string
  reason: string
  status: 'pending' | 'confirmed' | 'cancelled'
  checkedIn?: boolean
  checkInTime?: string
}

export interface MedicalDocument {
  id: number
  patientId: number
  title: string
  type: 'lab_result' | 'prescription' | 'imaging' | 'other'
  date: string
  content: string
}
