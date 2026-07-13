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

export interface PatientProperty {
  patient_id: string
  property_id: number
  name: string
  description?: string | null
  created_by_doctor_id?: string | null
  updated_by_doctor_id?: string | null
  created_by_name?: string | null
  updated_by_name?: string | null
  created_at?: string
  updated_at?: string
}

export interface PatientDocument {
  id: string
  patient_id: string
  doctor_id?: string | null
  document_type: string
  title: string
  description?: string | null
  file_path?: string
  file_name: string
  file_size: number
  document_date: string
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

export interface ConversationParticipant {
  user_id: string
  display_name: string
  role: 'doctor' | 'patient' | string | null
  specialty?: string | null
  last_read_at?: string | null
  joined_at?: string | null
}

export interface ConversationLastMessage {
  body: string
  created_at?: string | null
  sender_name?: string | null
}

export interface Conversation {
  id: string
  type: 'dm' | 'channel'
  title: string
  created_by_user_id?: string | null
  created_at?: string
  updated_at?: string
  participants: ConversationParticipant[]
  unread_count: number
  last_message?: ConversationLastMessage | null
}

export interface ChatMessage {
  id: string
  conversation_id: string
  sender_user_id: string
  sender_name: string
  sender_role?: string | null
  parent_message_id?: string | null
  body: string
  created_at: string
  edited_at?: string | null
  deleted_at?: string | null
  reply_count: number
}

export interface MessagingContact {
  user_id: string
  display_name: string
  role: 'doctor' | 'patient' | string
  specialty?: string | null
}
