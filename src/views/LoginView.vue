<template>
  <div class="login-container">
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

        <button type="submit" class="login-button">Login</button>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>
      </form>

      <div class="demo-credentials">
        <h3>Demo Credentials</h3>
        <div class="credentials-section">
          <strong>Doctor:</strong>
          <p>Username: doctor1</p>
          <p>Password: doctor123</p>
        </div>
        <div class="credentials-section">
          <strong>Patient:</strong>
          <p>Username: patient1</p>
          <p>Password: patient123</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authenticateUser } from '@/store'

const router = useRouter()
const username = ref('')
const password = ref('')
const error = ref('')

const handleLogin = () => {
  error.value = ''
  
  const user = authenticateUser(username.value, password.value)
  
  if (user) {
    // Redirect based on user role
    if (user.role === 'doctor') {
      router.push('/doctor')
    } else {
      router.push('/patient')
    }
  } else {
    error.value = 'Invalid username or password'
  }
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

.demo-credentials {
  border-top: 1px solid #eee;
  padding-top: 20px;
}

.demo-credentials h3 {
  font-size: 16px;
  color: #555;
  margin-bottom: 15px;
  text-align: center;
}

.credentials-section {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 10px;
  font-size: 13px;
}

.credentials-section strong {
  color: #667eea;
  display: block;
  margin-bottom: 5px;
}

.credentials-section p {
  margin: 2px 0;
  color: #666;
}
</style>
