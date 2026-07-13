<template>
  <div class="messages-page">
    <aside class="sidebar-pane">
      <div class="sidebar-header">
        <h2>Messages</h2>
        <button class="compose-btn" type="button" @click="openCompose">+ New</button>
      </div>

      <div class="sidebar-filters">
        <button
          type="button"
          class="filter-chip"
          :class="{ active: listFilter === 'all' }"
          @click="listFilter = 'all'"
        >
          All
        </button>
        <button
          type="button"
          class="filter-chip"
          :class="{ active: listFilter === 'dm' }"
          @click="listFilter = 'dm'"
        >
          Direct
        </button>
        <button
          type="button"
          class="filter-chip"
          :class="{ active: listFilter === 'channel' }"
          @click="listFilter = 'channel'"
        >
          Channels
        </button>
      </div>

      <div v-if="conversationsLoading" class="pane-state">Loading conversations...</div>
      <div v-else-if="conversationsError" class="pane-state error">{{ conversationsError }}</div>
      <div v-else-if="filteredConversations.length === 0" class="pane-state">
        No conversations yet. Start one with New.
      </div>

      <button
        v-for="conversation in filteredConversations"
        :key="conversation.id"
        type="button"
        class="conversation-item"
        :class="{ active: conversation.id === selectedConversationId }"
        @click="selectConversation(conversation.id)"
      >
        <div class="conversation-top">
          <span class="conversation-title">
            <span v-if="conversation.type === 'channel'" class="hash">#</span>
            {{ conversation.title }}
          </span>
          <span v-if="conversation.unread_count > 0" class="unread-pill">
            {{ conversation.unread_count }}
          </span>
        </div>
        <div class="conversation-preview">
          {{ conversation.last_message?.body || 'No messages yet' }}
        </div>
        <div class="conversation-meta">
          {{ formatRelative(conversation.last_message?.created_at || conversation.updated_at) }}
        </div>
      </button>
    </aside>

    <section class="main-pane" :class="{ 'with-thread': !!activeThreadRoot }">
      <template v-if="selectedConversation">
        <header class="main-header">
          <div>
            <h2>
              <span v-if="selectedConversation.type === 'channel'" class="hash">#</span>
              {{ selectedConversation.title }}
            </h2>
            <p class="subtitle">
              {{ participantSummary }}
            </p>
          </div>
          <button
            v-if="canCreateChannel && selectedConversation.type === 'channel'"
            type="button"
            class="secondary-btn"
            @click="openAddPeople"
          >
            Add people
          </button>
        </header>

        <div ref="messageListRef" class="message-list">
          <div v-if="messagesLoading" class="pane-state">Loading messages...</div>
          <div v-else-if="messagesError" class="pane-state error">{{ messagesError }}</div>
          <div v-else-if="messages.length === 0" class="pane-state">
            This is the beginning of the conversation.
          </div>

          <article
            v-for="message in messages"
            :key="message.id"
            class="message-row"
            :class="{ mine: message.sender_user_id === currentUserId }"
          >
            <div class="avatar" aria-hidden="true">
              {{ initials(message.sender_name) }}
            </div>
            <div class="message-body">
              <div class="message-meta">
                <strong>{{ message.sender_name }}</strong>
                <span>{{ formatTime(message.created_at) }}</span>
              </div>
              <p class="message-text">{{ message.body }}</p>
              <div class="message-actions">
                <button type="button" class="link-btn" @click="openThread(message)">
                  {{ message.reply_count > 0 ? `${message.reply_count} replies` : 'Reply in thread' }}
                </button>
              </div>
            </div>
          </article>
        </div>

        <form class="composer" @submit.prevent="sendTopLevelMessage">
          <textarea
            v-model="draft"
            rows="2"
            :placeholder="composerPlaceholder"
            @keydown.enter.exact.prevent="sendTopLevelMessage"
          ></textarea>
          <button class="primary-btn" type="submit" :disabled="sending || !draft.trim()">
            {{ sending ? 'Sending...' : 'Send' }}
          </button>
        </form>
      </template>

      <div v-else class="empty-main">
        <h2>Secure messaging</h2>
        <p>Message your care team in real time — direct chats, channels, and threaded replies.</p>
        <button type="button" class="primary-btn" @click="openCompose">Start a conversation</button>
      </div>
    </section>

    <aside v-if="activeThreadRoot && selectedConversation" class="thread-pane">
      <header class="thread-header">
        <h3>Thread</h3>
        <button type="button" class="icon-btn" aria-label="Close thread" @click="closeThread">✕</button>
      </header>

      <div class="thread-root">
        <strong>{{ activeThreadRoot.sender_name }}</strong>
        <p>{{ activeThreadRoot.body }}</p>
      </div>

      <div class="thread-replies">
        <div v-if="threadLoading" class="pane-state">Loading thread...</div>
        <article v-for="reply in threadReplies" :key="reply.id" class="message-row compact">
          <div class="avatar small" aria-hidden="true">{{ initials(reply.sender_name) }}</div>
          <div class="message-body">
            <div class="message-meta">
              <strong>{{ reply.sender_name }}</strong>
              <span>{{ formatTime(reply.created_at) }}</span>
            </div>
            <p class="message-text">{{ reply.body }}</p>
          </div>
        </article>
      </div>

      <form class="composer compact" @submit.prevent="sendThreadReply">
        <textarea
          v-model="threadDraft"
          rows="2"
          placeholder="Reply in thread..."
          @keydown.enter.exact.prevent="sendThreadReply"
        ></textarea>
        <button class="primary-btn" type="submit" :disabled="threadSending || !threadDraft.trim()">
          {{ threadSending ? 'Sending...' : 'Reply' }}
        </button>
      </form>
    </aside>

    <div v-if="showComposeModal" class="modal-overlay" @click="closeCompose">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h2>{{ composeMode === 'channel' ? 'Create channel' : 'New message' }}</h2>
          <button type="button" class="icon-btn" @click="closeCompose">✕</button>
        </div>

        <div class="modal-content">
          <div v-if="canCreateChannel" class="compose-tabs">
            <button
              type="button"
              class="filter-chip"
              :class="{ active: composeMode === 'dm' }"
              @click="composeMode = 'dm'"
            >
              Direct message
            </button>
            <button
              type="button"
              class="filter-chip"
              :class="{ active: composeMode === 'channel' }"
              @click="composeMode = 'channel'"
            >
              Channel
            </button>
          </div>

          <div v-if="composeMode === 'channel'" class="form-group">
            <label for="channel-title">Channel name</label>
            <input id="channel-title" v-model="channelTitle" type="text" maxlength="80" placeholder="e.g. Care Team — Smith" />
          </div>

          <div class="form-group">
            <label>{{ composeMode === 'channel' ? 'Add people' : 'Message' }}</label>
            <div v-if="contactsLoading" class="pane-state">Loading contacts...</div>
            <div v-else class="contact-list">
              <label
                v-for="contact in contacts"
                :key="contact.user_id"
                class="contact-option"
              >
                <input
                  v-if="composeMode === 'channel'"
                  v-model="selectedContactIds"
                  type="checkbox"
                  :value="contact.user_id"
                />
                <input
                  v-else
                  v-model="selectedDmContactId"
                  type="radio"
                  name="dm-contact"
                  :value="contact.user_id"
                />
                <span>
                  <strong>{{ contact.display_name }}</strong>
                  <small>
                    {{ contact.role === 'doctor' ? (contact.specialty || 'Provider') : 'Patient' }}
                  </small>
                </span>
              </label>
            </div>
          </div>

          <div v-if="composeError" class="pane-state error">{{ composeError }}</div>

          <div class="modal-actions">
            <button type="button" class="primary-btn" :disabled="composeSubmitting" @click="submitCompose">
              {{ composeSubmitting ? 'Creating...' : (composeMode === 'channel' ? 'Create channel' : 'Open chat') }}
            </button>
            <button type="button" class="secondary-btn" :disabled="composeSubmitting" @click="closeCompose">
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showAddPeopleModal" class="modal-overlay" @click="closeAddPeople">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h2>Add people</h2>
          <button type="button" class="icon-btn" @click="closeAddPeople">✕</button>
        </div>
        <div class="modal-content">
          <div class="contact-list">
            <label
              v-for="contact in addableContacts"
              :key="contact.user_id"
              class="contact-option"
            >
              <input v-model="addPeopleIds" type="checkbox" :value="contact.user_id" />
              <span>
                <strong>{{ contact.display_name }}</strong>
                <small>{{ contact.role === 'doctor' ? (contact.specialty || 'Provider') : 'Patient' }}</small>
              </span>
            </label>
          </div>
          <div v-if="addPeopleError" class="pane-state error">{{ addPeopleError }}</div>
          <div class="modal-actions">
            <button type="button" class="primary-btn" :disabled="addPeopleSubmitting" @click="submitAddPeople">
              {{ addPeopleSubmitting ? 'Adding...' : 'Add' }}
            </button>
            <button type="button" class="secondary-btn" @click="closeAddPeople">Cancel</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { formatDistanceToNow, parseISO, format } from 'date-fns'
import { messagesApi } from '@/api'
import type { ChatMessage, Conversation, MessagingContact } from '@/types'
import { getCurrentUser } from '@/store'

const POLL_MS = 4000

const currentUser = getCurrentUser()
const currentUserId = String(currentUser?.id || '')
const canCreateChannel = currentUser?.role === 'doctor'

const conversations = ref<Conversation[]>([])
const conversationsLoading = ref(false)
const conversationsError = ref('')
const listFilter = ref<'all' | 'dm' | 'channel'>('all')
const selectedConversationId = ref<string | null>(null)

const messages = ref<ChatMessage[]>([])
const messagesLoading = ref(false)
const messagesError = ref('')
const draft = ref('')
const sending = ref(false)
const messageListRef = ref<HTMLElement | null>(null)

const activeThreadRoot = ref<ChatMessage | null>(null)
const threadReplies = ref<ChatMessage[]>([])
const threadLoading = ref(false)
const threadDraft = ref('')
const threadSending = ref(false)

const showComposeModal = ref(false)
const composeMode = ref<'dm' | 'channel'>('dm')
const contacts = ref<MessagingContact[]>([])
const contactsLoading = ref(false)
const selectedDmContactId = ref('')
const selectedContactIds = ref<string[]>([])
const channelTitle = ref('')
const composeError = ref('')
const composeSubmitting = ref(false)

const showAddPeopleModal = ref(false)
const addPeopleIds = ref<string[]>([])
const addPeopleError = ref('')
const addPeopleSubmitting = ref(false)

let pollTimer: ReturnType<typeof globalThis.setInterval> | null = null

const selectedConversation = computed(() =>
  conversations.value.find((c) => c.id === selectedConversationId.value) || null,
)

const filteredConversations = computed(() => {
  if (listFilter.value === 'all') return conversations.value
  return conversations.value.filter((c) => c.type === listFilter.value)
})

const participantSummary = computed(() => {
  const conversation = selectedConversation.value
  if (!conversation) return ''
  const names = conversation.participants.map((p) => p.display_name)
  if (conversation.type === 'channel') {
    return `${names.length} members · ${names.slice(0, 3).join(', ')}${names.length > 3 ? '…' : ''}`
  }
  return names.filter((name) => !nameIncludesCurrentUser(name)).join(', ') || names.join(', ')
})

const composerPlaceholder = computed(() => {
  if (!selectedConversation.value) return 'Write a message...'
  if (selectedConversation.value.type === 'channel') {
    return `Message #${selectedConversation.value.title}`
  }
  return `Message ${selectedConversation.value.title}`
})

const addableContacts = computed(() => {
  const existing = new Set(
    (selectedConversation.value?.participants || []).map((p) => p.user_id),
  )
  return contacts.value.filter((c) => !existing.has(c.user_id))
})

function nameIncludesCurrentUser(name: string): boolean {
  const username = currentUser?.username || ''
  const fullName = currentUser?.name || ''
  return (!!fullName && name.includes(fullName)) || (!!username && name.toLowerCase().includes(username.toLowerCase()))
}

function initials(name: string): string {
  const parts = (name || '?').trim().split(/\s+/).slice(0, 2)
  return parts.map((p) => p[0]?.toUpperCase() || '').join('') || '?'
}

function formatRelative(value?: string | null): string {
  if (!value) return ''
  try {
    return formatDistanceToNow(parseISO(value), { addSuffix: true })
  } catch {
    return ''
  }
}

function formatTime(value?: string | null): string {
  if (!value) return ''
  try {
    return format(parseISO(value), 'MMM d, h:mm a')
  } catch {
    return value
  }
}

async function scrollMessagesToBottom() {
  await nextTick()
  const el = messageListRef.value
  if (el) {
    el.scrollTop = el.scrollHeight
  }
}

async function loadConversations(options: { quiet?: boolean } = {}) {
  if (!options.quiet) {
    conversationsLoading.value = true
  }
  conversationsError.value = ''
  const response = await messagesApi.listConversations()
  conversationsLoading.value = false

  if (response.error || !response.data) {
    conversationsError.value = response.error || 'Failed to load conversations'
    return
  }

  conversations.value = response.data.conversations
  if (!selectedConversationId.value && conversations.value.length > 0) {
    selectedConversationId.value = conversations.value[0].id
  }
}

function mergeById(existing: ChatMessage[], incoming: ChatMessage[]): ChatMessage[] {
  if (incoming.length === 0) return existing
  const byId = new Map(existing.map((message) => [message.id, message]))
  for (const message of incoming) {
    byId.set(message.id, message)
  }
  return Array.from(byId.values()).sort((a, b) => a.created_at.localeCompare(b.created_at))
}

function newestCreatedAt(items: ChatMessage[]): string | undefined {
  if (items.length === 0) return undefined
  return items.reduce((latest, message) =>
    message.created_at > latest ? message.created_at : latest,
  items[0].created_at)
}

async function loadMessages(options: { quiet?: boolean } = {}) {
  const conversationId = selectedConversationId.value
  if (!conversationId) {
    messages.value = []
    return
  }

  if (!options.quiet) {
    messagesLoading.value = true
  }
  messagesError.value = ''

  const since = options.quiet ? newestCreatedAt(messages.value) : undefined
  const response = await messagesApi.listMessages(conversationId, since ? { since } : {})
  messagesLoading.value = false

  if (selectedConversationId.value !== conversationId) {
    return
  }

  if (response.error || !response.data) {
    messagesError.value = response.error || 'Failed to load messages'
    return
  }

  const previousCount = messages.value.length
  if (since) {
    messages.value = mergeById(messages.value, response.data.messages)
  } else {
    messages.value = response.data.messages
  }
  await messagesApi.markRead(conversationId)

  if (selectedConversationId.value !== conversationId) {
    return
  }

  const conversation = conversations.value.find((c) => c.id === conversationId)
  if (conversation) {
    conversation.unread_count = 0
  }

  if (!options.quiet || messages.value.length !== previousCount) {
    await scrollMessagesToBottom()
  }
}

async function selectConversation(conversationId: string) {
  selectedConversationId.value = conversationId
  closeThread()
  await loadMessages()
}

async function sendTopLevelMessage() {
  const conversationId = selectedConversationId.value
  const body = draft.value.trim()
  if (!conversationId || !body || sending.value) return

  sending.value = true
  const response = await messagesApi.sendMessage(conversationId, { body })
  sending.value = false

  if (response.error || !response.data) {
    messagesError.value = response.error || 'Failed to send message'
    return
  }

  draft.value = ''
  messages.value = [...messages.value, response.data.message]
  await loadConversations({ quiet: true })
  await scrollMessagesToBottom()
}

async function openThread(message: ChatMessage) {
  activeThreadRoot.value = message
  threadDraft.value = ''
  await loadThreadReplies()
}

function closeThread() {
  activeThreadRoot.value = null
  threadReplies.value = []
  threadDraft.value = ''
}

async function loadThreadReplies(options: { quiet?: boolean } = {}) {
  const conversationId = selectedConversationId.value
  const root = activeThreadRoot.value
  if (!conversationId || !root) return

  if (!options.quiet) {
    threadLoading.value = true
  }
  const since = options.quiet ? newestCreatedAt(threadReplies.value) : undefined
  const response = await messagesApi.listMessages(conversationId, {
    parent_message_id: root.id,
    ...(since ? { since } : {}),
  })
  threadLoading.value = false

  if (response.error || !response.data) {
    return
  }

  const previousCount = threadReplies.value.length
  if (since) {
    threadReplies.value = mergeById(threadReplies.value, response.data.messages)
  } else {
    threadReplies.value = response.data.messages
  }

  const added = threadReplies.value.length - previousCount
  if (added > 0) {
    const parent = messages.value.find((m) => m.id === root.id)
    if (parent) {
      parent.reply_count = Math.max(parent.reply_count, threadReplies.value.length)
    }
  }
}

async function sendThreadReply() {
  const conversationId = selectedConversationId.value
  const root = activeThreadRoot.value
  const body = threadDraft.value.trim()
  if (!conversationId || !root || !body || threadSending.value) return

  threadSending.value = true
  const response = await messagesApi.sendMessage(conversationId, {
    body,
    parent_message_id: root.id,
  })
  threadSending.value = false

  if (response.error || !response.data) {
    return
  }

  threadDraft.value = ''
  threadReplies.value = [...threadReplies.value, response.data.message]
  const parent = messages.value.find((m) => m.id === root.id)
  if (parent) {
    parent.reply_count += 1
  }
  await loadConversations({ quiet: true })
}

async function openCompose() {
  showComposeModal.value = true
  composeMode.value = 'dm'
  composeError.value = ''
  selectedDmContactId.value = ''
  selectedContactIds.value = []
  channelTitle.value = ''
  await loadContacts()
}

function closeCompose() {
  showComposeModal.value = false
}

async function loadContacts() {
  contactsLoading.value = true
  const response = await messagesApi.listContacts()
  contactsLoading.value = false
  if (response.error || !response.data) {
    composeError.value = response.error || 'Failed to load contacts'
    contacts.value = []
    return
  }
  contacts.value = response.data.contacts
}

async function submitCompose() {
  composeError.value = ''
  composeSubmitting.value = true

  let response
  if (composeMode.value === 'channel') {
    if (!channelTitle.value.trim()) {
      composeError.value = 'Channel name is required'
      composeSubmitting.value = false
      return
    }
    response = await messagesApi.createConversation({
      type: 'channel',
      title: channelTitle.value.trim(),
      participant_user_ids: selectedContactIds.value,
    })
  } else {
    if (!selectedDmContactId.value) {
      composeError.value = 'Select someone to message'
      composeSubmitting.value = false
      return
    }
    response = await messagesApi.createConversation({
      type: 'dm',
      participant_user_id: selectedDmContactId.value,
    })
  }

  composeSubmitting.value = false
  if (response.error || !response.data) {
    composeError.value = response.error || 'Failed to create conversation'
    return
  }

  closeCompose()
  await loadConversations()
  selectedConversationId.value = response.data.conversation.id
  await loadMessages()
}

async function openAddPeople() {
  addPeopleError.value = ''
  addPeopleIds.value = []
  showAddPeopleModal.value = true
  if (contacts.value.length === 0) {
    await loadContacts()
  }
}

function closeAddPeople() {
  showAddPeopleModal.value = false
}

async function submitAddPeople() {
  if (!selectedConversationId.value || addPeopleIds.value.length === 0) {
    addPeopleError.value = 'Select at least one person'
    return
  }
  addPeopleSubmitting.value = true
  const response = await messagesApi.addParticipants(
    selectedConversationId.value,
    addPeopleIds.value,
  )
  addPeopleSubmitting.value = false
  if (response.error) {
    addPeopleError.value = response.error
    return
  }
  closeAddPeople()
  await loadConversations({ quiet: true })
}

async function pollUpdates() {
  if (typeof document !== 'undefined' && document.hidden) {
    return
  }
  await loadConversations({ quiet: true })
  if (selectedConversationId.value) {
    await loadMessages({ quiet: true })
  }
  if (activeThreadRoot.value) {
    await loadThreadReplies({ quiet: true })
  }
}

function onVisibilityChange() {
  if (typeof document !== 'undefined' && !document.hidden) {
    void pollUpdates()
  }
}

watch(selectedConversationId, async (id) => {
  if (id) {
    await loadMessages()
  }
})

onMounted(async () => {
  await loadConversations()
  if (selectedConversationId.value) {
    await loadMessages()
  }
  pollTimer = globalThis.setInterval(() => {
    void pollUpdates()
  }, POLL_MS)
  if (typeof document !== 'undefined') {
    document.addEventListener('visibilitychange', onVisibilityChange)
  }
})

onBeforeUnmount(() => {
  if (pollTimer) {
    globalThis.clearInterval(pollTimer)
  }
  if (typeof document !== 'undefined') {
    document.removeEventListener('visibilitychange', onVisibilityChange)
  }
})
</script>

<style scoped>
.messages-page {
  --msg-bg: #f3f6fb;
  --msg-panel: #ffffff;
  --msg-ink: #0f172a;
  --msg-muted: #64748b;
  --msg-accent: #1d4ed8;
  --msg-accent-soft: #dbeafe;
  --msg-border: #d9e2ec;
  --msg-mine: #eff6ff;
  display: grid;
  grid-template-columns: minmax(240px, 300px) minmax(0, 1fr);
  gap: 0;
  height: calc(100vh - 64px);
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.08), transparent 40%),
    linear-gradient(180deg, #e8eef8 0%, var(--msg-bg) 45%, #eef2f7 100%);
  color: var(--msg-ink);
}

.messages-page:has(.thread-pane) {
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr) minmax(260px, 340px);
}

.sidebar-pane,
.main-pane,
.thread-pane {
  background: var(--msg-panel);
  border-right: 1px solid var(--msg-border);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.thread-pane {
  border-right: none;
  border-left: 1px solid var(--msg-border);
}

.sidebar-header,
.main-header,
.thread-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 1rem 1.1rem;
  border-bottom: 1px solid var(--msg-border);
}

.sidebar-header h2,
.main-header h2,
.thread-header h3 {
  margin: 0;
  font-size: 1.15rem;
}

.subtitle {
  margin: 0.25rem 0 0;
  color: var(--msg-muted);
  font-size: 0.85rem;
}

.sidebar-filters,
.compose-tabs {
  display: flex;
  gap: 0.4rem;
  padding: 0.75rem 1rem;
  flex-wrap: wrap;
}

.filter-chip,
.compose-btn,
.primary-btn,
.secondary-btn,
.link-btn,
.icon-btn {
  border: none;
  cursor: pointer;
  font: inherit;
}

.filter-chip {
  background: #eef2ff;
  color: #334155;
  border-radius: 999px;
  padding: 0.35rem 0.75rem;
  font-size: 0.8rem;
}

.filter-chip.active {
  background: var(--msg-accent);
  color: white;
}

.compose-btn,
.primary-btn {
  background: var(--msg-accent);
  color: white;
  border-radius: 0.55rem;
  padding: 0.55rem 0.9rem;
  font-weight: 600;
}

.secondary-btn {
  background: #e2e8f0;
  color: #0f172a;
  border-radius: 0.55rem;
  padding: 0.55rem 0.9rem;
}

.compose-btn:hover,
.primary-btn:hover {
  background: #1e40af;
}

.primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.conversation-item {
  display: block;
  width: 100%;
  text-align: left;
  background: transparent;
  border: none;
  border-bottom: 1px solid #edf2f7;
  padding: 0.85rem 1rem;
  cursor: pointer;
}

.conversation-item:hover,
.conversation-item.active {
  background: var(--msg-accent-soft);
}

.conversation-top {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  align-items: center;
}

.conversation-title {
  font-weight: 650;
  font-size: 0.95rem;
}

.hash {
  color: var(--msg-muted);
  margin-right: 0.15rem;
}

.unread-pill {
  background: #dc2626;
  color: white;
  border-radius: 999px;
  min-width: 1.4rem;
  text-align: center;
  font-size: 0.72rem;
  padding: 0.1rem 0.4rem;
}

.conversation-preview {
  color: var(--msg-muted);
  font-size: 0.82rem;
  margin-top: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conversation-meta {
  color: #94a3b8;
  font-size: 0.72rem;
  margin-top: 0.2rem;
}

.message-list,
.thread-replies,
.sidebar-pane {
  overflow-y: auto;
}

.message-list {
  flex: 1;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.message-row {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  padding: 0.55rem 0.65rem;
  border-radius: 0.75rem;
}

.message-row.mine {
  background: var(--msg-mine);
}

.message-row.compact {
  padding: 0.4rem 0;
}

.avatar {
  width: 2.2rem;
  height: 2.2rem;
  border-radius: 0.65rem;
  background: #1e3a5f;
  color: white;
  display: grid;
  place-items: center;
  font-size: 0.75rem;
  font-weight: 700;
  flex-shrink: 0;
}

.avatar.small {
  width: 1.8rem;
  height: 1.8rem;
  font-size: 0.68rem;
}

.message-meta {
  display: flex;
  gap: 0.55rem;
  align-items: baseline;
  margin-bottom: 0.2rem;
}

.message-meta span {
  color: var(--msg-muted);
  font-size: 0.75rem;
}

.message-text {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.45;
}

.message-actions {
  margin-top: 0.35rem;
}

.link-btn {
  background: transparent;
  color: var(--msg-accent);
  padding: 0;
  font-size: 0.8rem;
}

.composer {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.75rem;
  padding: 0.9rem 1rem 1.1rem;
  border-top: 1px solid var(--msg-border);
  background: #f8fafc;
}

.composer.compact {
  grid-template-columns: 1fr;
}

.composer textarea,
.form-group input {
  width: 100%;
  border: 1px solid var(--msg-border);
  border-radius: 0.65rem;
  padding: 0.7rem 0.8rem;
  font: inherit;
  resize: vertical;
  background: white;
}

.empty-main,
.pane-state {
  padding: 2rem 1.25rem;
  color: var(--msg-muted);
  text-align: center;
}

.empty-main h2 {
  margin: 0 0 0.5rem;
  color: var(--msg-ink);
}

.pane-state.error,
.feature-request-error {
  color: #b91c1c;
}

.thread-root {
  padding: 1rem;
  border-bottom: 1px solid var(--msg-border);
  background: #f8fafc;
}

.thread-root p {
  margin: 0.4rem 0 0;
}

.thread-replies {
  flex: 1;
  padding: 0.75rem 1rem;
}

.icon-btn {
  background: transparent;
  color: var(--msg-muted);
  font-size: 1rem;
  padding: 0.2rem 0.4rem;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: grid;
  place-items: center;
  z-index: 40;
  padding: 1rem;
}

.modal {
  width: min(520px, 100%);
  background: white;
  border-radius: 0.9rem;
  overflow: hidden;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.25);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.1rem;
  border-bottom: 1px solid var(--msg-border);
}

.modal-header h2 {
  margin: 0;
  font-size: 1.1rem;
}

.modal-content {
  padding: 1rem 1.1rem 1.2rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.4rem;
  font-weight: 600;
}

.contact-list {
  max-height: 240px;
  overflow-y: auto;
  border: 1px solid var(--msg-border);
  border-radius: 0.65rem;
}

.contact-option {
  display: flex;
  gap: 0.65rem;
  align-items: flex-start;
  padding: 0.7rem 0.8rem;
  border-bottom: 1px solid #edf2f7;
  cursor: pointer;
}

.contact-option:last-child {
  border-bottom: none;
}

.contact-option span {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.contact-option small {
  color: var(--msg-muted);
}

.modal-actions {
  display: flex;
  gap: 0.6rem;
  justify-content: flex-end;
  margin-top: 1rem;
}

@media (max-width: 960px) {
  .messages-page,
  .messages-page:has(.thread-pane) {
    grid-template-columns: 1fr;
    height: auto;
    min-height: calc(100vh - 64px);
  }

  .sidebar-pane {
    max-height: 280px;
    border-right: none;
    border-bottom: 1px solid var(--msg-border);
  }

  .main-pane {
    min-height: 420px;
  }

  .thread-pane {
    border-left: none;
    border-top: 1px solid var(--msg-border);
    min-height: 320px;
  }
}
</style>
