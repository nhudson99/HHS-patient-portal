import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProviderDashboard from '@/views/ProviderDashboard.vue'

function getLocalDateString(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function mockFetch({
  events = [],
  doctors = []
}: {
  events?: Record<string, unknown>[]
  doctors?: Record<string, unknown>[]
} = {}) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.includes('/api/patients/doctors')) {
      return {
        ok: true,
        json: async () => ({ doctors })
      }
    }
    return {
      ok: true,
      json: async () => ({ events })
    }
  })
}

describe('ProviderDashboard.vue', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch())
  })

  it('renders scheduling assistant controls', async () => {
    const wrapper = mount(ProviderDashboard)
    await flushPromises()

    expect(wrapper.text()).toContain('Scheduling Assistant')
    expect(wrapper.text()).toContain('Clinic-wide day board')
    expect(wrapper.find('.date-input').exists()).toBe(true)
    expect(wrapper.find('.patient-search-input').exists()).toBe(true)
    expect(wrapper.find('.add-event-btn').exists()).toBe(true)
    expect(wrapper.find('.schedule-board').exists()).toBe(true)
    expect(wrapper.find('.time-axis--left').exists()).toBe(true)
  })

  it('shows events for selected day across providers with redacted other-provider details', async () => {
    const today = getLocalDateString(new Date())
    vi.stubGlobal(
      'fetch',
      mockFetch({
        doctors: [
          { id: 'doc-1', first_name: 'Alice', last_name: 'Smith' },
          { id: 'doc-2', first_name: 'Bob', last_name: 'Jones' }
        ],
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
            provider_name: 'Alice Smith',
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
            provider_name: 'Bob Jones',
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
            provider_name: 'Alice Smith',
            is_own_event: true,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z'
          }
        ]
      })
    )

    const wrapper = mount(ProviderDashboard)
    await flushPromises()

    const providerColumns = wrapper.findAll('.provider-column')
    expect(providerColumns.length).toBe(2)

    const headers = wrapper.findAll('.provider-column-header').map((node) => node.text())
    expect(headers).toEqual(['Alice Smith (1)', 'Bob Jones (1)'])

    const items = wrapper.findAll('.schedule-block')
    expect(items.length).toBe(2)
    expect(wrapper.text()).toContain('Morning Huddle')
    expect(wrapper.text()).toContain('Appointment (pending)')
    expect(wrapper.text()).not.toContain('Jane Doe')
    expect(wrapper.text()).not.toContain('Future Event')

    const otherProviderItem = wrapper.find('.schedule-block--other')
    expect(otherProviderItem.exists()).toBe(true)

    await otherProviderItem.trigger('click')
    expect(wrapper.find('.selection-panel').exists()).toBe(true)
    expect(wrapper.find('.selection-panel').text()).not.toContain('Confirm')
    expect(wrapper.find('.selection-panel').text()).not.toContain('Edit')
    expect(wrapper.find('.selection-panel').text()).not.toContain('Delete')

    const ownProviderItem = wrapper.findAll('.schedule-block').find((item) => !item.classes().includes('schedule-block--other'))
    expect(ownProviderItem).toBeTruthy()
    await ownProviderItem!.trigger('click')
    expect(wrapper.find('.selection-panel').text()).toContain('Edit')
    expect(wrapper.find('.selection-panel').text()).toContain('Delete')
  })

  it('requests all providers when loading events', async () => {
    const fetchMock = mockFetch()
    vi.stubGlobal('fetch', fetchMock)

    mount(ProviderDashboard)
    await flushPromises()

    expect(fetchMock).toHaveBeenCalled()
    const eventRequest = fetchMock.mock.calls
      .map((call) => String(call[0]))
      .find((url) => url.includes('/api/events'))
    expect(eventRequest).toContain('include_all_providers=true')
  })

  it('still shows provider columns when the day has no events', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch({
        doctors: [
          { id: 'doc-1', first_name: 'Alice', last_name: 'Smith' },
          { id: 'doc-2', first_name: 'Bob', last_name: 'Jones' }
        ],
        events: []
      })
    )

    const wrapper = mount(ProviderDashboard)
    await flushPromises()

    expect(wrapper.find('.schedule-board').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('No appointments or events scheduled for this day.')

    const headers = wrapper.findAll('.provider-column-header').map((node) => node.text())
    expect(headers).toEqual(['Alice Smith (0)', 'Bob Jones (0)'])
    expect(wrapper.findAll('.schedule-block').length).toBe(0)
  })
})
