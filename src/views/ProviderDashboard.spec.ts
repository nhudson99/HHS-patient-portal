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

  it('skips events entirely outside the clinic time window', async () => {
    const today = getLocalDateString(new Date())
    vi.stubGlobal(
      'fetch',
      mockFetch({
        doctors: [{ id: 'doc-1', first_name: 'Alice', last_name: 'Smith' }],
        events: [
          {
            id: 'early',
            doctor_id: 'doc-1',
            event_type: 'appointment',
            title: 'Too Early',
            event_date: today,
            start_time: '06:00:00',
            end_time: '06:30:00',
            color: '#3b82f6',
            is_all_day: false,
            provider_name: 'Alice Smith',
            is_own_event: true,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z'
          },
          {
            id: 'late',
            doctor_id: 'doc-1',
            event_type: 'appointment',
            title: 'Too Late',
            event_date: today,
            start_time: '20:30:00',
            end_time: '21:00:00',
            color: '#3b82f6',
            is_all_day: false,
            provider_name: 'Alice Smith',
            is_own_event: true,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z'
          },
          {
            id: 'in-window',
            doctor_id: 'doc-1',
            event_type: 'appointment',
            title: 'In Window',
            event_date: today,
            start_time: '10:00:00',
            end_time: '10:30:00',
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

    expect(wrapper.findAll('.schedule-block').length).toBe(1)
    expect(wrapper.text()).toContain('In Window')
    expect(wrapper.text()).not.toContain('Too Early')
    expect(wrapper.text()).not.toContain('Too Late')
    expect(wrapper.find('.provider-column-header').text()).toContain('(1)')
  })

  it('spans all-day events across the full timed grid', async () => {
    const today = getLocalDateString(new Date())
    vi.stubGlobal(
      'fetch',
      mockFetch({
        doctors: [{ id: 'doc-1', first_name: 'Alice', last_name: 'Smith' }],
        events: [
          {
            id: 'all-day',
            doctor_id: 'doc-1',
            event_type: 'meeting',
            title: 'Clinic Closed',
            event_date: today,
            color: '#f59e0b',
            is_all_day: true,
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

    const block = wrapper.find('.schedule-block--all-day')
    expect(block.exists()).toBe(true)
    expect(block.text()).toContain('Clinic Closed')
    expect(block.text()).toContain('All day')
    // 7 AM–8 PM = 13 hours = 52 slots * 18px = 936px
    expect(block.attributes('style')).toContain('height: 936px')
  })

  it('lays overlapping events into side-by-side lanes', async () => {
    const today = getLocalDateString(new Date())
    vi.stubGlobal(
      'fetch',
      mockFetch({
        doctors: [{ id: 'doc-1', first_name: 'Alice', last_name: 'Smith' }],
        events: [
          {
            id: 'a',
            doctor_id: 'doc-1',
            event_type: 'appointment',
            title: 'Patient A',
            patient_name: 'Patient A',
            event_date: today,
            start_time: '10:00:00',
            end_time: '10:30:00',
            color: '#3b82f6',
            is_all_day: false,
            provider_name: 'Alice Smith',
            is_own_event: true,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z'
          },
          {
            id: 'b',
            doctor_id: 'doc-1',
            event_type: 'appointment',
            title: 'Patient B',
            patient_name: 'Patient B',
            event_date: today,
            start_time: '10:00:00',
            end_time: '10:30:00',
            color: '#10b981',
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

    const blocks = wrapper.findAll('.schedule-block')
    expect(blocks.length).toBe(2)
    const styles = blocks.map((block) => block.attributes('style') || '')
    expect(styles.some((style) => style.includes('left: calc(0% + 2px)'))).toBe(true)
    expect(styles.some((style) => style.includes('left: calc(50% + 2px)'))).toBe(true)
    expect(styles.every((style) => style.includes('width: calc(50% - 4px)'))).toBe(true)
  })

  it('keeps other-provider availability visible while searching patients', async () => {
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
            id: 'own-match',
            doctor_id: 'doc-1',
            event_type: 'appointment',
            title: 'Garcia Visit',
            patient_name: 'Garcia, Jayla',
            event_date: today,
            start_time: '10:00:00',
            end_time: '10:30:00',
            color: '#3b82f6',
            is_all_day: false,
            provider_name: 'Alice Smith',
            is_own_event: true,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z'
          },
          {
            id: 'own-other',
            doctor_id: 'doc-1',
            event_type: 'appointment',
            title: 'Smith Visit',
            patient_name: 'Smith, John',
            event_date: today,
            start_time: '11:00:00',
            end_time: '11:30:00',
            color: '#3b82f6',
            is_all_day: false,
            provider_name: 'Alice Smith',
            is_own_event: true,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z'
          },
          {
            id: 'other-block',
            doctor_id: 'doc-2',
            event_type: 'blocked_time',
            title: 'Blocked Time',
            event_date: today,
            start_time: '09:00:00',
            end_time: '09:30:00',
            color: '#ef4444',
            is_all_day: false,
            provider_name: 'Bob Jones',
            is_own_event: false,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z'
          }
        ]
      })
    )

    const wrapper = mount(ProviderDashboard)
    await flushPromises()

    await wrapper.find('.patient-search-input').setValue('Garcia')
    await flushPromises()

    expect(wrapper.text()).toContain('GARCIA, JAYLA')
    expect(wrapper.text()).not.toContain('SMITH, JOHN')
    expect(wrapper.text()).toContain('Blocked Time')
    expect(wrapper.find('.provider-column-header').text()).toContain('Alice Smith (1)')
    const headers = wrapper.findAll('.provider-column-header').map((node) => node.text())
    expect(headers).toContain('Bob Jones (1)')
  })
})
