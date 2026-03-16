import { mount } from '@vue/test-utils'
import { vi, beforeEach } from 'vitest'
import DoctorDashboard from '@/views/DoctorDashboard.vue'

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async () => ({
    ok: true,
    json: async () => ({ events: [] })
  })))
})

describe('DoctorDashboard.vue', () => {
  it('renders calendar view controls', () => {
    const wrapper = mount(DoctorDashboard)
    expect(wrapper.text()).toContain('Day')
    expect(wrapper.text()).toContain('Week')
    expect(wrapper.text()).toContain('Month')
  })

  it('shows day, week, and month views', async () => {
    const wrapper = mount(DoctorDashboard)
    expect(wrapper.find('.week-view').exists()).toBe(true)

    wrapper.vm.viewMode = 'day'
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.day-view').exists()).toBe(true)

    wrapper.vm.viewMode = 'week'
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.week-view').exists()).toBe(true)

    wrapper.vm.viewMode = 'month'
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.month-view').exists()).toBe(true)
  })

  it('opens event modal when clicking a time slot', async () => {
    const wrapper = mount(DoctorDashboard)
    wrapper.vm.viewMode = 'day'
    await wrapper.vm.$nextTick()
    const hourSlot = wrapper.find('.hour-slot')
    await hourSlot.trigger('click')
    expect(wrapper.find('.modal-overlay').exists()).toBe(true)
  })
})
