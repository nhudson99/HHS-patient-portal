<template>
  <div class="login-container">
    <button @click="goToCheckIn" class="checkin-link">Check In</button>
    <div class="login-card">
      <div class="logo">
        <h1>🏥</h1>
      </div>
      <h2>Hudson Health System</h2>
      <p class="subtitle">Patient Portal</p>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="username">Username</label>
          <input
            id="username"
            v-model="username"
            type="text"
            placeholder="Enter username"
            required
          />
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="Enter password"
            required
          />
        </div>

        <button type="submit" class="login-button" :disabled="loading">
          {{ loading ? 'Logging in...' : 'Login' }}
        </button>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/api'
import { setCurrentUser } from '@/store'

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
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  background: white;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  max-width: 450px;
  width: 100%;
}

.logo {
  text-align: center;
  font-size: 48px;
  margin-bottom: 10px;
}

h2 {
  text-align: center;
  color: #333;
  margin-bottom: 5px;
  font-size: 28px;
}

.subtitle {
  text-align: center;
  color: #666;
  margin-bottom: 30px;
  font-size: 16px;
}

.login-form {
  margin-bottom: 30px;
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  margin-bottom: 5px;
  color: #555;
  font-weight: 500;
}

input {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.3s;
}

input:focus {
  outline: none;
  border-color: #667eea;
}

.login-button {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  transition: transform 0.2s;
}

.login-button:hover {
  transform: translateY(-2px);
}

.error-message {
  margin-top: 15px;
  padding: 10px;
  background: #fee;
  color: #c33;
  border-radius: 6px;
  text-align: center;
  font-size: 14px;
}

.checkin-link {
  position: absolute;
  top: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 2px solid white;
  padding: 10px 24px;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  transition: all 0.3s;
  backdrop-filter: blur(10px);
}

.checkin-link:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
}
</style>
