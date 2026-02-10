import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { getCurrentUser } from '@/store'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Login',
    component: () => import('@/views/LoginView.vue')
  },
  {
    path: '/doctor',
    name: 'DoctorDashboard',
    component: () => import('@/views/DoctorDashboard.vue'),
    meta: { requiresAuth: true, role: 'doctor' }
  },
  {
    path: '/patient',
    name: 'PatientDashboard',
    component: () => import('@/views/PatientDashboard.vue'),
    meta: { requiresAuth: true, role: 'patient' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard
router.beforeEach((to, _from, next) => {
  const user = getCurrentUser()
  
  if (to.meta.requiresAuth && !user) {
    next('/')
  } else if (to.meta.requiresAuth && to.meta.role && user?.role !== to.meta.role) {
    next('/')
  } else if (to.path === '/' && user) {
    // Redirect logged in users to their dashboard
    next(user.role === 'doctor' ? '/doctor' : '/patient')
  } else {
    next()
  }
})

export default router
