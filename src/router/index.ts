import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { getCurrentUser, validateSession } from '@/store'

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
    path: '/doctor',
    name: 'DoctorDashboard',
    component: () => import('@/views/DoctorDashboard.vue'),
    meta: { requiresAuth: true, role: 'doctor' }
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
  const user = getCurrentUser()
  
  // Validate session token for protected routes
  if (to.meta.requiresAuth) {
    const isValid = await validateSession()
    if (!isValid) {
      next('/')
      return
    }
  }
  
  if (to.meta.requiresAuth && !user) {
    next('/')
  } else if (to.meta.requiresAuth && to.meta.role && user?.role !== to.meta.role) {
    next('/')
  } else if (to.path === '/' && user) {
    // Redirect logged in users to their dashboard
    next(user.role === 'doctor' ? '/doctor' : '/patient')
  } else if (to.path === '/admin') {
    // /admin handles its own auth via Microsoft SSO — always allow
    next()
  } else {
    next()
  }
})

export default router
