import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { getCurrentUser, requiresPasswordChange, validateSession } from '@/store'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Login',
    component: () => import('@/views/LoginView.vue')
  },
  {
    path: '/checkin',
    name: 'CheckIn',
    component: () => import('@/views/CheckInView.vue')
  },
  {
    // Tablet kiosk mode — no auth, self-resetting check-in screen
    path: '/kiosk',
    name: 'Kiosk',
    component: () => import('@/views/KioskView.vue')
  },
  {
    path: '/provider',
    name: 'ProviderDashboard',
    component: () => import('@/views/ProviderDashboard.vue'),
    meta: { requiresAuth: true, role: 'doctor' }
  },
  {
    // Legacy path redirect
    path: '/doctor',
    redirect: '/provider'
  },
  {
    path: '/patients',
    name: 'Patients',
    component: () => import('@/views/PatientsView.vue'),
    meta: { requiresAuth: true, role: 'doctor' }
  },
  {
    path: '/patient',
    name: 'PatientDashboard',
    component: () => import('@/views/PatientDashboard.vue'),
    meta: { requiresAuth: true, role: 'patient' }
  },
  {
    path: '/messages',
    name: 'Messages',
    component: () => import('@/views/MessagesView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { requiresAuth: true }
  },
  {
    // Admin portal — access via Microsoft SSO (@hudsonitconsulting.com only).
    // Auth is handled entirely inside AdminView; no portal session required to reach this route.
    path: '/admin',
    name: 'Admin',
    component: () => import('@/views/AdminView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard with session validation
router.beforeEach(async (to, _from, next) => {
  // Validate session token for protected routes first so currentUser is fresh.
  if (to.meta.requiresAuth) {
    const isValid = await validateSession()
    if (!isValid) {
      next('/')
      return
    }
  }

  const user = getCurrentUser()

  if (to.meta.requiresAuth && !user) {
    next('/')
    return
  }

  if (to.meta.requiresAuth && to.meta.role && user?.role !== to.meta.role) {
    next('/')
    return
  }

  // Force password change before any other authenticated destination.
  if (
    user &&
    requiresPasswordChange(user) &&
    to.path !== '/profile' &&
    to.path !== '/admin' &&
    to.path !== '/'
  ) {
    next({ path: '/profile', query: { password: 'required' } })
    return
  }

  if (to.path === '/' && user) {
    if (requiresPasswordChange(user)) {
      next({ path: '/profile', query: { password: 'required' } })
      return
    }
    next(user.role === 'doctor' ? '/provider' : '/patient')
    return
  }

  if (to.path === '/admin') {
    // /admin handles its own auth via Microsoft SSO — always allow
    next()
    return
  }

  next()
})

export default router
