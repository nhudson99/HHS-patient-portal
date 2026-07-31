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

function stubVideoPreview() {
  Object.defineProperty(HTMLVideoElement.prototype, 'srcObject', {
    configurable: true,
    get() {
      return (this as HTMLVideoElement & { _srcObject?: MediaStream | null })._srcObject ?? null
    },
    set(value: MediaStream | null) {
      ;(this as HTMLVideoElement & { _srcObject?: MediaStream | null })._srcObject = value
    },
  })
  Object.defineProperty(HTMLVideoElement.prototype, 'videoWidth', {
    configurable: true,
    get() {
      return (this as HTMLVideoElement).srcObject ? 640 : 0
    },
  })
  Object.defineProperty(HTMLVideoElement.prototype, 'videoHeight', {
    configurable: true,
    get() {
      return (this as HTMLVideoElement).srcObject ? 480 : 0
    },
  })
  Object.defineProperty(HTMLVideoElement.prototype, 'readyState', {
    configurable: true,
    get() {
      return (this as HTMLVideoElement).srcObject ? 4 : 0
    },
  })
  HTMLVideoElement.prototype.play = vi.fn().mockResolvedValue(undefined)
}

function appointmentResponse() {
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

describe('KioskView camera-first check-in', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    stubVideoPreview()
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/api/appointments/kiosk/lookup')) {
          return appointmentResponse()
        }
        if (url.includes('/checkin-guest') || url.includes('/profile-photo/kiosk')) {
          return { ok: true, json: async () => ({}) }
        }
        return { ok: true, json: async () => ({}) }
      }),
    )
  })

  async function submitForm(wrapper: ReturnType<typeof mount>) {
    await wrapper.get('.kiosk-btn.primary.big').trigger('click')
    await wrapper.get('#fullName').setValue('John Smith')
    await wrapper.get('#dob').setValue('1990-05-15')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
  }

  it('goes straight to the camera preview after Check In, even before lookup finishes', async () => {
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
          return appointmentResponse()
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

    // Photo screen appears immediately — not gated on lookup
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Profile Photo')
    })
    expect(getUserMedia).toHaveBeenCalled()
    expect(wrapper.text()).not.toContain("You're Checked In!")

    resolveLookup(undefined)
    await flushPromises()
    expect(wrapper.text()).toContain('Profile Photo')
  })

  it('shows Enable Camera + Skip when getUserMedia fails, without auto check-in', async () => {
    const getUserMedia = vi.fn().mockRejectedValue({ name: 'NotAllowedError' })
    vi.stubGlobal('navigator', {
      mediaDevices: { getUserMedia },
    })
    Object.defineProperty(window, 'isSecureContext', { configurable: true, value: true })

    const wrapper = mount(KioskView)
    await submitForm(wrapper)

    expect(wrapper.text()).toContain('Profile Photo')
    expect(wrapper.text()).toContain('Enable Camera')
    expect(wrapper.text()).toContain('Skip Photo & Check In')
    expect(wrapper.text()).not.toContain("You're Checked In!")
  })

  it('still opens the camera preview when appointment lookup fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/api/appointments/kiosk/lookup')) {
          return { ok: false, json: async () => ({ error: 'not found' }) }
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
    await submitForm(wrapper)

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Capture & Check In')
    })
    expect(wrapper.text()).not.toContain("You're Checked In!")
  })

  it('captures then goes to the check-in confirmation screen', async () => {
    const getUserMedia = vi.fn().mockResolvedValue(mockStream())
    vi.stubGlobal('navigator', {
      mediaDevices: { getUserMedia },
    })
    Object.defineProperty(window, 'isSecureContext', { configurable: true, value: true })

    HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue({
      drawImage: vi.fn(),
    }) as unknown as typeof HTMLCanvasElement.prototype.getContext
    HTMLCanvasElement.prototype.toDataURL = vi.fn().mockReturnValue('data:image/jpeg;base64,/9j/4AAQ')
    HTMLCanvasElement.prototype.toBlob = vi.fn((cb: BlobCallback) => {
      cb(new Blob(['fake-jpeg'], { type: 'image/jpeg' }))
    }) as unknown as typeof HTMLCanvasElement.prototype.toBlob

    const wrapper = mount(KioskView)
    await submitForm(wrapper)

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Capture & Check In')
    })

    await wrapper.get('button.kiosk-btn.primary').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain("You're Checked In!")
    expect(wrapper.text()).toContain('John Smith')
  })
})
