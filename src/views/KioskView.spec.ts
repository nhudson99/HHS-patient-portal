import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import KioskView from '@/views/KioskView.vue'

function mockStream(): MediaStream {
  const track = {
    readyState: 'live',
    stop: vi.fn(),
    getSettings: () => ({ facingMode: 'user' }),
  }
  return {
    getVideoTracks: () => [track],
    getTracks: () => [track],
  } as unknown as MediaStream
}

describe('KioskView camera step', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/api/appointments/kiosk/lookup')) {
          return {
            ok: true,
            json: async () => ({
              appointment: {
                id: 'apt-1',
                patient_id: 'pat-1',
                appointment_date: '2026-08-01T10:00:00.000Z',
                doctor_name: 'Adams',
                reason: 'Follow-up',
              },
            }),
          }
        }
        return { ok: true, json: async () => ({}) }
      }),
    )
  })

  it('stays on the photo step with Enable Camera when getUserMedia fails', async () => {
    const getUserMedia = vi.fn().mockRejectedValue({ name: 'NotAllowedError' })
    vi.stubGlobal('navigator', {
      mediaDevices: { getUserMedia },
    })
    Object.defineProperty(window, 'isSecureContext', { configurable: true, value: true })

    const wrapper = mount(KioskView)
    await wrapper.get('.kiosk-btn.primary.big').trigger('click')
    await wrapper.get('#fullName').setValue('John Smith')
    await wrapper.get('#dob').setValue('1990-05-15')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('Update Profile Photo')
    expect(wrapper.text()).toContain('Enable Camera')
    expect(wrapper.text()).toMatch(/permission was denied|Unable to open the front camera|Front camera/i)
    expect(wrapper.text()).not.toContain("You're Checked In!")
  })

  it('starts getUserMedia during the Check In click before lookup resolves', async () => {
    let resolveLookup: (value: unknown) => void = () => undefined
    const lookupGate = new Promise((resolve) => {
      resolveLookup = resolve
    })

    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/api/appointments/kiosk/lookup')) {
          await lookupGate
          return {
            ok: true,
            json: async () => ({
              appointment: {
                id: 'apt-1',
                patient_id: 'pat-1',
                appointment_date: '2026-08-01T10:00:00.000Z',
                doctor_name: 'Adams',
                reason: 'Follow-up',
              },
            }),
          }
        }
        return { ok: true, json: async () => ({}) }
      }),
    )

    const getUserMedia = vi.fn().mockResolvedValue(mockStream())
    vi.stubGlobal('navigator', {
      mediaDevices: { getUserMedia },
    })
    Object.defineProperty(window, 'isSecureContext', { configurable: true, value: true })

    const wrapper = mount(KioskView)
    await wrapper.get('.kiosk-btn.primary.big').trigger('click')
    await wrapper.get('#fullName').setValue('John Smith')
    await wrapper.get('#dob').setValue('1990-05-15')
    await wrapper.get('form').trigger('submit')

    // Camera request must start before lookup finishes (user-gesture window).
    expect(getUserMedia).toHaveBeenCalled()

    resolveLookup(undefined)
    await flushPromises()
    expect(wrapper.text()).toContain('Update Profile Photo')
  })
})
