import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProviderDashboard from '@/views/ProviderDashboard.vue'

function getLocalDateString(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

describe('ProviderDashboard.vue', () => {
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
    const wrapper = mount(ProviderDashboard)
    await flushPromises()

    expect(wrapper.text()).toContain('Provider Day Schedule')
    expect(wrapper.text()).toContain('View provider availability across the clinic')
    expect(wrapper.find('.date-input').exists()).toBe(true)
    expect(wrapper.find('.add-event-btn').exists()).toBe(true)
  })

  it('shows events for selected day across providers with redacted other-provider details', async () => {
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
              is_own_event: true,
              created_at: '2026-01-01T00:00:00Z',
              updated_at: '2026-01-01T00:00:00Z'
            },
            {
              id: 'apt-123',
              doctor_id: 'doc-2',
              event_type: 'appointment',
              title: 'Appointment (pending)',
              event_date: today,
              start_time: '09:00:00',
              color: '#f59e0b',
              is_all_day: false,
              provider_name: 'Dr. Bob Jones',
              patient_name: null,
              appointment_status: 'pending',
              is_own_event: false,
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
              is_own_event: true,
              created_at: '2026-01-01T00:00:00Z',
              updated_at: '2026-01-01T00:00:00Z'
            }
          ]
        })
      }))
    )

    const wrapper = mount(ProviderDashboard)
    await flushPromises()

    const providerColumns = wrapper.findAll('.provider-column')
    expect(providerColumns.length).toBe(2)
    const headers = wrapper.findAll('.provider-column-header').map((node) => node.text())
    expect(headers).toEqual(['Dr. Alice Smith', 'Dr. Bob Jones'])

    const items = wrapper.findAll('.schedule-item')
    expect(items.length).toBe(2)
    expect(wrapper.text()).toContain('Morning Huddle')
    expect(wrapper.text()).toContain('Appointment (pending)')
    expect(wrapper.text()).not.toContain('Jane Doe')
    expect(wrapper.text()).not.toContain('Future Event')

    const otherProviderItem = wrapper.find('.schedule-item--other')
    expect(otherProviderItem.exists()).toBe(true)
    expect(otherProviderItem.text()).not.toContain('Confirm')
    expect(otherProviderItem.text()).not.toContain('Edit')
    expect(otherProviderItem.text()).not.toContain('Delete')

    const ownProviderItem = wrapper.findAll('.schedule-item').find((item) => !item.classes().includes('schedule-item--other'))
    expect(ownProviderItem?.text()).toContain('Edit')
    expect(ownProviderItem?.text()).toContain('Delete')
  })

  it('requests all providers when loading events', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({ events: [] })
    }))
    vi.stubGlobal('fetch', fetchMock)

    mount(ProviderDashboard)
    await flushPromises()

    expect(fetchMock).toHaveBeenCalled()
    const requestUrl = String(fetchMock.mock.calls[0][0])
    expect(requestUrl).toContain('include_all_providers=true')
  })

  it('shows empty state when day has no events', async () => {
    const wrapper = mount(ProviderDashboard)
    await flushPromises()

    expect(wrapper.text()).toContain('No appointments or events scheduled for this day.')
  })
})
