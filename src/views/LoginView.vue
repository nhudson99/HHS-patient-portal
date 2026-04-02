<template>
  <div class="login-container">
    <button @click="goToCheckIn" class="checkin-link">Check In →</button>
    <div class="login-split">
      <div class="login-brand">
        <div class="brand-icon">🏥</div>
        <h1>Hudson Health System</h1>
        <p>Secure access to your patient portal — manage appointments, documents, and your care team in one place.</p>
      </div>
      <div class="login-card">
        <h2>Sign in</h2>
        <p class="card-subtitle">Use your portal credentials</p>
        <form @submit.prevent="handleLogin" class="login-form">
          <div class="form-group">
            <label for="username">Username</label>
            <input id="username" v-model="username" type="text" placeholder="Enter username" required autocomplete="username" />
          </div>
          <div class="form-group">
            <label for="password">Password</label>
            <input id="password" v-model="password" type="password" placeholder="Enter password" required autocomplete="current-password" />
          </div>
          <div v-if="error" class="error-message">{{ error }}</div>
          <button type="submit" class="login-button" :disabled="loading">
            {{ loading ? 'Signing in…' : 'Sign in' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/api'
import { setCurrentUser, clearAdminSession } from '@/store'

const router = useRouter()
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

const handleLogin = async () => {
  error.value = ''
  loading.value = true
  
  try {
    const response = await authApi.login(username.value, password.value)
    
    console.log('Login response:', response)
    
    if (response.error) {
      error.value = response.error
      return
    }
    
    if (response.data) {
      // Enforce single session: clear any active admin SSO session
      clearAdminSession()

      // Store session token and user data
      localStorage.setItem('sessionToken', response.data.sessionToken)
      localStorage.setItem('currentUser', JSON.stringify(response.data.user))
      
      // Update store with current user
      setCurrentUser({
        id: response.data.user.id,
        username: response.data.user.username,
        email: response.data.user.email,
        role: response.data.user.role as 'doctor' | 'patient'
      })
      
      console.log('Login successful, user role:', response.data.user.role)
      
      if (response.data.requirePasswordChange) {
        router.push({ path: '/profile', query: { password: 'required' } })
        return
      }
      
      // Redirect based on user role
      if (response.data.user.role === 'doctor') {
        console.log('Redirecting to doctor dashboard')
        router.push('/doctor')
      } else {
        console.log('Redirecting to patient dashboard')
        router.push('/patient')
      }
    }
  } catch (err) {
    error.value = 'An unexpected error occurred. Please try again.'
    console.error('Login error:', err)
  } finally {
    loading.value = false
  }
}

const goToCheckIn = () => {
  router.push('/checkin')
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  background: #f8faff;
  display: flex;
  align-items: stretch;
  position: relative;
}

.login-split {
  display: flex;
  width: 100%;
  min-height: 100vh;
}

.login-brand {
  flex: 1;
  background: linear-gradient(145deg, #1e3a5f 0%, #2563eb 100%);
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 4rem 3rem;
  color: #fff;
}

.brand-icon {
  font-size: 56px;
  margin-bottom: 1.5rem;
}

.login-brand h1 {
  font-size: 2rem;
  font-weight: 700;
  margin: 0 0 1rem;
  line-height: 1.2;
}

.login-brand p {
  font-size: 1.05rem;
  opacity: 0.85;
  line-height: 1.7;
  max-width: 380px;
}

.login-card {
  width: 420px;
  flex-shrink: 0;
  background: #fff;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 3rem 2.5rem;
  box-shadow: -8px 0 40px rgba(0,0,0,0.08);
}

.login-card h2 {
  font-size: 1.75rem;
  font-weight: 700;
  color: #111827;
  margin: 0 0 0.35rem;
}

.card-subtitle {
  color: #6b7280;
  margin: 0 0 2rem;
  font-size: 0.95rem;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

label {
  font-size: 0.88rem;
  font-weight: 600;
  color: #374151;
}

input {
  padding: 0.75rem 1rem;
  border: 1.5px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.95rem;
  color: #111827;
  transition: border-color 0.2s, box-shadow 0.2s;
  background: #fafafa;
}

input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.12);
  background: #fff;
}

.login-button {
  padding: 0.85rem;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, transform 0.15s;
  margin-top: 0.5rem;
}

.login-button:hover:not(:disabled) {
  background: #1d4ed8;
  transform: translateY(-1px);
}

.login-button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.error-message {
  padding: 0.75rem 1rem;
  background: #fef2f2;
  border: 1px solid #fca5a5;
  color: #b91c1c;
  border-radius: 8px;
  font-size: 0.9rem;
}

.checkin-link {
  position: fixed;
  top: 1.25rem;
  right: 1.5rem;
  background: #fff;
  color: #2563eb;
  border: 1.5px solid #2563eb;
  padding: 0.5rem 1.25rem;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  z-index: 10;
  transition: background 0.2s, color 0.2s;
}

.checkin-link:hover {
  background: #2563eb;
  color: #fff;
}

@media (max-width: 768px) {
  .login-split {
    flex-direction: column;
  }
  .login-brand {
    padding: 3rem 2rem 2rem;
    flex: none;
  }
  .login-card {
    width: auto;
    flex: 1;
    padding: 2rem;
    box-shadow: none;
  }
}
</style>
