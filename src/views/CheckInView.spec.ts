import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CheckInView from '@/views/CheckInView.vue'

const { routerPush, setCurrentUser, login } = vi.hoisted(() => ({
  routerPush: vi.fn(),
  setCurrentUser: vi.fn(),
  login: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush }),
}))

vi.mock('@/store', () => ({
  getCurrentUser: () => null,
  setCurrentUser,
}))

vi.mock('@/api', () => ({
  authApi: {
    login: (...args: unknown[]) => login(...args),
  },
}))

describe('CheckInView.vue', () => {
  beforeEach(() => {
    routerPush.mockReset()
    setCurrentUser.mockReset()
    login.mockReset()
    localStorage.clear()
    vi.stubGlobal('fetch', vi.fn())
  })

  it('redirects to profile when credential login requires a password change', async () => {
    login.mockResolvedValue({
      data: {
        sessionToken: 'token-1',
        requirePasswordChange: true,
        user: {
          id: 'user-1',
          username: 'newpatient',
          email: 'newpatient@example.com',
          role: 'patient',
        },
      },
    })

    const wrapper = mount(CheckInView)
    await wrapper.get('button.kiosk-btn.primary').trigger('click')
    await wrapper.get('#username').setValue('newpatient')
    await wrapper.get('#password').setValue('TempPass123!')
    await wrapper.get('form.kiosk-form').trigger('submit')
    await flushPromises()

    expect(login).toHaveBeenCalledWith('newpatient', 'TempPass123!')
    expect(routerPush).toHaveBeenCalledWith({
      path: '/profile',
      query: { password: 'required' },
    })
    expect(globalThis.fetch).not.toHaveBeenCalled()
  })
})
