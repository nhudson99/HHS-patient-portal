import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DoctorDashboard from '@/views/DoctorDashboard.vue'

function getLocalDateString(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

describe('DoctorDashboard.vue', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        json: async () => ({ events: [] })
      }))
    )
  })

  it('renders day schedule controls', async () => {
    const wrapper = mount(DoctorDashboard)
    await flushPromises()

    expect(wrapper.text()).toContain('Provider Day Schedule')
    expect(wrapper.text()).toContain('All appointments and events for the selected day across providers')
    expect(wrapper.find('.date-input').exists()).toBe(true)
    expect(wrapper.find('.add-event-btn').exists()).toBe(true)
  })

  it('shows events for selected day across providers', async () => {
    const today = getLocalDateString(new Date())
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          events: [
            {
              id: 'evt-1',
              doctor_id: 'doc-1',
              event_type: 'meeting',
              title: 'Morning Huddle',
              event_date: today,
              start_time: '08:30:00',
              color: '#3b82f6',
              is_all_day: false,
              provider_name: 'Dr. Alice Smith',
              created_at: '2026-01-01T00:00:00Z',
              updated_at: '2026-01-01T00:00:00Z'
            },
            {
              id: 'apt-123',
              doctor_id: 'doc-2',
              event_type: 'appointment',
              title: 'Jane Doe (pending)',
              event_date: today,
              start_time: '09:00:00',
              color: '#f59e0b',
              is_all_day: false,
              provider_name: 'Dr. Bob Jones',
              patient_name: 'Jane Doe',
              appointment_status: 'pending',
              created_at: '2026-01-01T00:00:00Z',
              updated_at: '2026-01-01T00:00:00Z'
            },
            {
              id: 'evt-future',
              doctor_id: 'doc-1',
              event_type: 'meeting',
              title: 'Future Event',
              event_date: '2099-01-01',
              start_time: '10:00:00',
              color: '#3b82f6',
              is_all_day: false,
              provider_name: 'Dr. Alice Smith',
              created_at: '2026-01-01T00:00:00Z',
              updated_at: '2026-01-01T00:00:00Z'
            }
          ]
        })
      }))
    )

    const wrapper = mount(DoctorDashboard)
    await flushPromises()

    const providerColumns = wrapper.findAll('.provider-column')
    expect(providerColumns.length).toBe(2)
    const headers = wrapper.findAll('.provider-column-header').map((node) => node.text())
    expect(headers).toEqual(['Dr. Alice Smith', 'Dr. Bob Jones'])

    const items = wrapper.findAll('.schedule-item')
    expect(items.length).toBe(2)
    expect(wrapper.text()).toContain('Confirm')
    expect(wrapper.text()).not.toContain('Future Event')
  })

  it('shows empty state when day has no events', async () => {
    const wrapper = mount(DoctorDashboard)
    await flushPromises()

    expect(wrapper.text()).toContain('No appointments or events scheduled for this day.')
  })
})
