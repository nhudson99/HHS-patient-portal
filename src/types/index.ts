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

export interface Patient {
  id: string
  user_id?: string | null
  first_name: string
  last_name: string
  date_of_birth: string
  phone: string
  address?: string | null
  emergency_contact_name?: string | null
  emergency_contact_phone?: string | null
  portal_email?: string | null
  created_at?: string
  updated_at?: string
}

export interface MedicalDocument {
  id: number
  patientId: number
  title: string
  type: 'lab_result' | 'prescription' | 'imaging' | 'other'
  date: string
  content: string
}
