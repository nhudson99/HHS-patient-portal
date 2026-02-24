<template>
  <div id="app">
    <header v-if="showHeader" class="top-header">
      <div class="header-content">
        <h1>🏥 {{ pageTitle }}</h1>
        <div class="user-actions">
          <RouterLink
            v-for="button in navButtons"
            :key="button.to"
            :to="button.to"
            class="header-btn"
          >
            {{ button.label }}
          </RouterLink>
          <span class="user-name">{{ userName }}</span>
          <button @click="handleLogout" class="logout-btn">Logout</button>
        </div>
      </div>
    </header>
    <RouterView />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import { RouterView, RouterLink, useRoute, useRouter } from 'vue-router'
import { logout } from '@/store'

type NavButton = {
  label: string
  to: string
}

const route = useRoute()
const router = useRouter()
const currentUser = ref<{ name?: string; username?: string; role?: string } | null>(null)

const loadUser = () => {
  const userStr = localStorage.getItem('currentUser')
  if (!userStr) {
    currentUser.value = null
    return
  }

  try {
    currentUser.value = JSON.parse(userStr)
  } catch {
    currentUser.value = null
  }
}

const showHeader = computed(() => {
  return !!currentUser.value && route.path !== '/'
})

const userName = computed(() => {
  if (!currentUser.value) return ''
  return currentUser.value.name || currentUser.value.username || ''
})

const pageTitle = computed(() => {
  if (route.path.startsWith('/patients')) return 'Patients'
  if (route.path.startsWith('/doctor')) return 'Doctor Dashboard'
  if (route.path.startsWith('/patient')) return 'Patient Dashboard'
  return 'Hudson Health System'
})

const navButtons = computed<NavButton[]>(() => {
  if (!currentUser.value) return []
  if (currentUser.value.role === 'doctor') {
    return [
      { label: 'Home', to: '/doctor' },
      { label: 'Patients', to: '/patients' }
    ]
  }
  if (currentUser.value.role === 'patient') {
    return [{ label: 'Home', to: '/patient' }]
  }
  return []
})

const handleLogout = () => {
  logout()
  localStorage.removeItem('sessionToken')
  localStorage.removeItem('currentUser')
  currentUser.value = null
  router.push('/')
}

onMounted(() => {
  loadUser()
})

watch(
  () => route.fullPath,
  () => {
    loadUser()
  }
)
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background-color: #f5f5f5;
  color: #333;
}

#app {
  min-height: 100vh;
}

.top-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-content h1 {
  margin: 0;
  font-size: 1.4rem;
}

.user-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.user-name {
  font-weight: 600;
}

.header-btn {
  padding: 0.5rem 1rem;
  background: rgba(255,255,255,0.2);
  color: white;
  border: 1px solid white;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
  text-decoration: none;
}

.header-btn:hover {
  background: rgba(255,255,255,0.3);
}

.logout-btn {
  padding: 0.5rem 1rem;
  background: rgba(255,255,255,0.2);
  color: white;
  border: 1px solid white;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
}

.logout-btn:hover {
  background: rgba(255,255,255,0.3);
}

button {
  cursor: pointer;
  font-family: inherit;
}

input, select, textarea {
  font-family: inherit;
}
</style>
