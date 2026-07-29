<template>
  <div class="patients-page">
    <div class="content" :class="{ split: selectedPatient }">
      <aside class="patients-list">
        <div class="list-header">
          <h2>All Patients</h2>
          <span class="count">{{ patients.length }}</span>
        </div>
  <button class="add-patient-btn" @click="showAddPatientModal = true">+ New Patient</button>

        <div v-if="loading" class="state">Loading patients...</div>
        <div v-else-if="error" class="state error">{{ error }}</div>
        <div v-else-if="patients.length === 0" class="state">No patients found.</div>

        <button
          v-for="patient in patients"
          :key="patient.id"
          class="patient-item"
          :class="{ active: patient.id === selectedPatient?.id }"
          @click="selectPatient(patient)"
        >
          <div class="patient-name">
            {{ patient.first_name }} {{ patient.last_name }}
          </div>
          <div class="patient-meta">
            DOB: {{ formatDate(patient.date_of_birth) }}
          </div>
        </button>
      </aside>

      <section class="patient-detail" v-if="selectedPatient">
        <div class="detail-header">
          <div class="detail-header-main">
            <div class="patient-avatar">
              <img
                v-if="selectedPatientPhotoUrl"
                :src="selectedPatientPhotoUrl"
                :alt="`${selectedPatient.first_name} ${selectedPatient.last_name}`"
              />
              <span v-else class="patient-avatar-fallback">
                {{ selectedPatientInitials }}
              </span>
            </div>
            <div>
              <h2>{{ selectedPatient.first_name }} {{ selectedPatient.last_name }}</h2>
              <div class="banner-meta">
                <span>DOB: {{ formatDate(selectedPatient.date_of_birth) }}</span>
                <span v-if="selectedPatient.phone">Phone: {{ selectedPatient.phone }}</span>
              </div>
            </div>
          </div>
          <span class="badge" :class="{ linked: !!selectedPatient.user_id }">
            {{ selectedPatient.user_id ? 'Portal Linked' : 'No Portal Account' }}
          </span>
        </div>

        <nav class="chart-tabs" aria-label="Patient chart sections">
          <button
            v-for="tab in chartTabs"
            :key="tab.id"
            type="button"
            class="chart-tab"
            :class="{ active: activeChartTab === tab.id }"
            @click="activeChartTab = tab.id"
          >
            {{ tab.label }}
          </button>
        </nav>

        <div v-if="activeChartTab === 'summary'" class="chart-panel">
          <div v-if="summaryLoading" class="state">Loading summary...</div>
          <div v-else-if="summaryError" class="state error">{{ summaryError }}</div>
          <div v-else class="summary-widgets">
            <div class="summary-widget">
              <h3>Allergies</h3>
              <p v-if="!chartSummary || chartSummary.allergy_count === 0" class="widget-empty">No active allergies.</p>
              <ul v-else>
                <li v-for="item in chartSummary.allergies" :key="item.id">
                  <strong>{{ item.allergen }}</strong>
                  <span v-if="item.reaction"> — {{ item.reaction }}</span>
                  <span class="severity"> ({{ item.severity }})</span>
                </li>
              </ul>
            </div>
            <div class="summary-widget">
              <h3>Medications</h3>
              <p v-if="!chartSummary || chartSummary.medication_count === 0" class="widget-empty">No current medications.</p>
              <ul v-else>
                <li v-for="item in chartSummary.medications" :key="item.id">
                  <strong>{{ item.name }}</strong>
                  <span v-if="item.dosage"> — {{ item.dosage }}</span>
                  <span v-if="item.frequency">, {{ item.frequency }}</span>
                </li>
              </ul>
            </div>
            <div class="summary-widget">
              <h3>Problems</h3>
              <p v-if="!chartSummary || chartSummary.problem_count === 0" class="widget-empty">No active problems.</p>
              <ul v-else>
                <li v-for="item in chartSummary.problems" :key="item.id">
                  <strong>{{ item.name }}</strong>
                </li>
              </ul>
            </div>
          </div>

          <div class="detail-grid demographics-grid">
            <div class="detail-card">
              <p class="detail-label">Date of Birth</p>
              <div>{{ formatDate(selectedPatient.date_of_birth) }}</div>
            </div>
            <div class="detail-card">
              <p class="detail-label">Phone</p>
              <div>{{ selectedPatient.phone }}</div>
            </div>
            <div class="detail-card">
              <p class="detail-label">Address</p>
              <div>{{ selectedPatient.address || '—' }}</div>
            </div>
            <div class="detail-card">
              <p class="detail-label">Emergency Contact</p>
              <div>
                {{ selectedPatient.emergency_contact_name || '—' }}
                <span v-if="selectedPatient.emergency_contact_phone">
                  ({{ selectedPatient.emergency_contact_phone }})
                </span>
              </div>
            </div>
            <div class="detail-card" v-if="selectedPatient.portal_email">
              <p class="detail-label">Portal Email</p>
              <div>{{ selectedPatient.portal_email }}</div>
            </div>
          </div>

          <div class="properties-section">
            <div class="properties-header">
              <h3>Notes</h3>
              <button class="add-btn" @click="openAddProperty">+ Add</button>
            </div>

            <div v-if="propertiesLoading" class="state">Loading properties...</div>
            <div v-else-if="propertiesError" class="state error">{{ propertiesError }}</div>
            <div v-else-if="patientProperties.length === 0" class="state">No properties yet.</div>

            <div class="accordion" v-else>
              <div
                v-for="prop in patientProperties"
                :key="prop.property_id"
                class="accordion-item"
              >
                <button class="accordion-header" @click="toggleProperty(prop.property_id)">
                  <span>{{ getPropertyDisplayName(prop) }}</span>
                  <span class="accordion-actions">
                    <span v-if="getSaveStatus(prop.property_id) !== 'idle'" class="note-save-status-inline" :class="getSaveStatus(prop.property_id)">
                      {{ saveStatusLabel(prop.property_id) }}
                    </span>
                    <span class="toggle-indicator">
                      {{ expandedProperties.has(prop.property_id) ? '−' : '+' }}
                    </span>
                    <button class="delete-btn" @click.stop="confirmDelete(prop)">Delete</button>
                  </span>
                </button>
                <div v-if="expandedProperties.has(prop.property_id)" class="accordion-body">
                  <div class="note-editor">
                    <label class="note-label" :for="`note-title-${prop.property_id}`">Title</label>
                    <input
                      :id="`note-title-${prop.property_id}`"
                      class="note-title-input"
                      :value="getPropertyDraft(prop).name"
                      @input="onPropertyFieldChange(prop, 'name', ($event.target as HTMLInputElement).value)"
                    />
                    <label class="note-label" :for="`note-body-${prop.property_id}`">Notes</label>
                    <textarea
                      :id="`note-body-${prop.property_id}`"
                      class="note-body-input"
                      rows="5"
                      :value="getPropertyDraft(prop).description"
                      @input="onPropertyFieldChange(prop, 'description', ($event.target as HTMLTextAreaElement).value)"
                    />
                    <p class="note-audit">
                      Created by Dr. {{ formatProviderName(prop.created_by_name) }}
                      · Last edited by Dr. {{ formatProviderName(prop.updated_by_name) }}
                      <span v-if="prop.updated_at"> · {{ formatDate(prop.updated_at) }}</span>
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="activeChartTab === 'allergies'" class="chart-panel">
          <div class="section-header">
            <h3>Allergies</h3>
            <button class="add-btn" @click="openAllergyModal()">+ Add</button>
          </div>
          <div v-if="allergiesLoading" class="state">Loading allergies...</div>
          <div v-else-if="allergiesError" class="state error">{{ allergiesError }}</div>
          <div v-else-if="allergies.length === 0" class="state">No allergies recorded.</div>
          <div v-else class="chart-table-wrap">
            <table class="chart-table">
              <thead>
                <tr>
                  <th>Allergen</th>
                  <th>Reaction</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in allergies" :key="item.id">
                  <td>{{ item.allergen }}</td>
                  <td>{{ item.reaction || '—' }}</td>
                  <td>{{ item.severity }}</td>
                  <td><span class="status-pill" :class="item.status">{{ item.status }}</span></td>
                  <td class="row-actions">
                    <button class="icon-btn" @click="openAllergyModal(item)" title="Edit">✏️</button>
                    <button class="icon-btn delete-btn-icon" @click="confirmDeleteAllergy(item)" title="Delete">🗑️</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-else-if="activeChartTab === 'medications'" class="chart-panel">
          <div class="section-header">
            <h3>Medications</h3>
            <button class="add-btn" @click="openMedicationModal()">+ Add</button>
          </div>
          <div v-if="medicationsLoading" class="state">Loading medications...</div>
          <div v-else-if="medicationsError" class="state error">{{ medicationsError }}</div>
          <div v-else-if="medications.length === 0" class="state">No medications recorded.</div>
          <div v-else class="chart-table-wrap">
            <table class="chart-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Dosage</th>
                  <th>Frequency</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in medications" :key="item.id">
                  <td>{{ item.name }}</td>
                  <td>{{ item.dosage || '—' }}</td>
                  <td>{{ item.frequency || '—' }}</td>
                  <td><span class="status-pill" :class="item.status">{{ item.status }}</span></td>
                  <td class="row-actions">
                    <button class="icon-btn" @click="openMedicationModal(item)" title="Edit">✏️</button>
                    <button class="icon-btn delete-btn-icon" @click="confirmDeleteMedication(item)" title="Delete">🗑️</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-else-if="activeChartTab === 'problems'" class="chart-panel">
          <div class="section-header">
            <h3>Problems</h3>
            <button class="add-btn" @click="openProblemModal()">+ Add</button>
          </div>
          <div v-if="problemsLoading" class="state">Loading problems...</div>
          <div v-else-if="problemsError" class="state error">{{ problemsError }}</div>
          <div v-else-if="problems.length === 0" class="state">No problems recorded.</div>
          <div v-else class="chart-table-wrap">
            <table class="chart-table">
              <thead>
                <tr>
                  <th>Problem</th>
                  <th>Onset</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in problems" :key="item.id">
                  <td>{{ item.name }}</td>
                  <td>{{ item.onset_date ? formatDate(item.onset_date) : '—' }}</td>
                  <td><span class="status-pill" :class="item.status">{{ item.status }}</span></td>
                  <td class="row-actions">
                    <button class="icon-btn" @click="openProblemModal(item)" title="Edit">✏️</button>
                    <button class="icon-btn delete-btn-icon" @click="confirmDeleteProblem(item)" title="Delete">🗑️</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-else-if="activeChartTab === 'documents'" class="chart-panel">
          <div class="documents-header">
            <h3>Documents</h3>
            <div class="documents-header-actions">
              <label class="visibility-checkbox">
                <input v-model="uploadPatientVisible" type="checkbox" />
                Visible to patient
              </label>
              <button class="add-btn" @click="triggerFileUpload">+ Upload</button>
              <input
                ref="fileInput"
                type="file"
                multiple
                style="display: none"
                @change="handleFileUpload"
              />
            </div>
          </div>

          <div v-if="documentsLoading" class="state">Loading documents...</div>
          <div v-else-if="documentsError" class="state error">{{ documentsError }}</div>
          <div v-else-if="documents.length === 0" class="state">No documents yet.</div>

          <div class="documents-list" v-else>
            <div
              v-for="doc in documents"
              :key="doc.id"
              class="document-item"
            >
              <div class="document-info">
                <a
                  :href="`/api/documents/download/${doc.id}`"
                  class="document-link"
                  @click.prevent="downloadDocument(doc)"
                >
                  <span class="doc-icon">📄</span>
                  {{ doc.title }}
                </a>
                <span class="document-size">{{ formatFileSize(doc.file_size) }}</span>
                <span class="visibility-badge" :class="{ visible: doc.patient_visible }">
                  {{ doc.patient_visible ? 'Patient visible' : 'Provider only' }}
                </span>
              </div>
              <div class="document-actions">
                <button
                  class="icon-btn"
                  :title="doc.patient_visible ? 'Hide from patient' : 'Share with patient'"
                  @click="toggleDocumentVisibility(doc)"
                >
                  {{ doc.patient_visible ? '🔒' : '🔓' }}
                </button>
                <button class="icon-btn rename-btn" @click="openRenameDialog(doc)" title="Rename">
                  ✏️
                </button>
                <button class="icon-btn delete-btn-icon" @click="confirmDeleteDocument(doc)" title="Delete">
                  🗑️
                </button>
              </div>
            </div>
          </div>

          <div v-if="uploadProgress" class="upload-progress">
            <span>Uploading...</span>
          </div>
        </div>
      </section>

    </div>

    <!-- Add Patient Modal -->
    <div v-if="showAddPatientModal" class="modal-overlay" @click="showAddPatientModal = false">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h2>Add New Patient</h2>
          <button class="close-btn" @click="showAddPatientModal = false">✕</button>
        </div>
        <div class="modal-content">
          <div v-if="addPatientError" class="error-banner">{{ addPatientError }}</div>
          <div v-if="addPatientSuccess" class="success-banner">
            Patient created. Temporary password: <strong>{{ newPatientPassword }}</strong>
            <br /><small>Share this with the patient — they will be prompted to change it on first login.</small>
          </div>
          <template v-if="!addPatientSuccess">
            <div class="form-row">
              <div class="form-group">
                <label>First Name *</label>
                <input v-model="addPatientForm.firstName" type="text" placeholder="First name" />
              </div>
              <div class="form-group">
                <label>Last Name *</label>
                <input v-model="addPatientForm.lastName" type="text" placeholder="Last name" />
              </div>
            </div>
            <div class="form-group">
              <label>Username *</label>
              <input v-model="addPatientForm.username" type="text" placeholder="Portal login username" />
            </div>
            <div class="form-group">
              <label>Email *</label>
              <input v-model="addPatientForm.email" type="email" placeholder="Patient email" />
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Date of Birth</label>
                <input v-model="addPatientForm.dateOfBirth" type="date" />
              </div>
              <div class="form-group">
                <label>Phone</label>
                <input v-model="addPatientForm.phone" type="tel" placeholder="Phone number" />
              </div>
            </div>
            <div class="form-group">
              <label>Address</label>
              <input v-model="addPatientForm.address" type="text" placeholder="Street address" />
            </div>
          </template>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="closeAddPatientModal">{{ addPatientSuccess ? 'Close' : 'Cancel' }}</button>
          <button v-if="!addPatientSuccess" class="btn-primary" :disabled="addPatientSaving" @click="submitAddPatient">
            {{ addPatientSaving ? 'Creating...' : 'Create Patient' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showAddDialog" class="modal-overlay" @click="closeAddDialog">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h2>New Property</h2>
          <button class="close-btn" @click="closeAddDialog">✕</button>
        </div>
        <div class="modal-content">
          <div class="form-group">
            <label for="property-name">Name *</label>
            <input id="property-name" v-model="propertyForm.name" type="text" placeholder="Property name" />
          </div>
          <div class="form-group">
            <label for="property-description">Description</label>
            <textarea
              id="property-description"
              v-model="propertyForm.description"
              rows="4"
              placeholder="Detailed notes"
            ></textarea>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="closeAddDialog">Cancel</button>
          <button class="btn-primary" @click="saveProperty">Save</button>
        </div>
      </div>
    </div>

    <div v-if="showDeleteConfirm" class="modal-overlay" @click="cancelDelete">
      <div class="modal small" @click.stop>
        <div class="modal-content">
          <p>Delete property "{{ pendingDelete?.name }}"?</p>
          <div class="modal-actions">
            <button class="btn-danger" @click="deleteProperty">Delete</button>
            <button class="btn-secondary" @click="cancelDelete">Cancel</button>
          </div>
        </div>
      </div>
    </div>

        <!-- Rename Document Modal -->
    <div v-if="showRenameDialog" class="modal-overlay" @click="closeRenameDialog">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h2>Rename Document</h2>
          <button class="close-btn" @click="closeRenameDialog">✕</button>
        </div>
        <div class="modal-content">
          <div class="form-group">
            <label for="rename-document-title">Title</label>
            <input id="rename-document-title" v-model="renameForm.title" type="text" placeholder="Document title" />
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="closeRenameDialog">Cancel</button>
          <button class="btn-primary" @click="renameDocument">Save</button>
        </div>
      </div>
    </div>

    <!-- Delete Document Confirmation -->
    <div v-if="showDeleteDocConfirm" class="modal-overlay" @click="cancelDeleteDocument">
      <div class="modal small" @click.stop>
        <div class="modal-content">
          <p>Delete document "{{ pendingDeleteDoc?.title }}"?</p>
          <div class="modal-actions">
            <button class="btn-danger" @click="deleteDocument">Delete</button>
            <button class="btn-secondary" @click="cancelDeleteDocument">Cancel</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Allergy Modal -->
    <div v-if="showAllergyModal" class="modal-overlay" @click="closeAllergyModal">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h2>{{ editingAllergyId ? 'Edit Allergy' : 'Add Allergy' }}</h2>
          <button class="close-btn" @click="closeAllergyModal">✕</button>
        </div>
        <div class="modal-content">
          <div v-if="allergyFormError" class="error-banner">{{ allergyFormError }}</div>
          <div class="form-group">
            <label>Allergen *</label>
            <input v-model="allergyForm.allergen" type="text" placeholder="e.g. Penicillin" />
          </div>
          <div class="form-group">
            <label>Reaction</label>
            <input v-model="allergyForm.reaction" type="text" placeholder="e.g. Rash" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Severity</label>
              <select v-model="allergyForm.severity">
                <option value="unknown">unknown</option>
                <option value="mild">mild</option>
                <option value="moderate">moderate</option>
                <option value="severe">severe</option>
              </select>
            </div>
            <div class="form-group">
              <label>Status</label>
              <select v-model="allergyForm.status">
                <option value="active">active</option>
                <option value="inactive">inactive</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>Notes</label>
            <textarea v-model="allergyForm.notes" rows="3"></textarea>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="closeAllergyModal">Cancel</button>
          <button class="btn-primary" :disabled="allergySaving" @click="saveAllergy">
            {{ allergySaving ? 'Saving...' : 'Save' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Medication Modal -->
    <div v-if="showMedicationModal" class="modal-overlay" @click="closeMedicationModal">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h2>{{ editingMedicationId ? 'Edit Medication' : 'Add Medication' }}</h2>
          <button class="close-btn" @click="closeMedicationModal">✕</button>
        </div>
        <div class="modal-content">
          <div v-if="medicationFormError" class="error-banner">{{ medicationFormError }}</div>
          <div class="form-group">
            <label>Name *</label>
            <input v-model="medicationForm.name" type="text" placeholder="e.g. Lisinopril" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Dosage</label>
              <input v-model="medicationForm.dosage" type="text" placeholder="10 mg" />
            </div>
            <div class="form-group">
              <label>Frequency</label>
              <input v-model="medicationForm.frequency" type="text" placeholder="Once daily" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Route</label>
              <input v-model="medicationForm.route" type="text" placeholder="Oral" />
            </div>
            <div class="form-group">
              <label>Status</label>
              <select v-model="medicationForm.status">
                <option value="active">active</option>
                <option value="discontinued">discontinued</option>
                <option value="completed">completed</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Start Date</label>
              <input v-model="medicationForm.start_date" type="date" />
            </div>
            <div class="form-group">
              <label>End Date</label>
              <input v-model="medicationForm.end_date" type="date" />
            </div>
          </div>
          <div class="form-group">
            <label>Notes</label>
            <textarea v-model="medicationForm.notes" rows="3"></textarea>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="closeMedicationModal">Cancel</button>
          <button class="btn-primary" :disabled="medicationSaving" @click="saveMedication">
            {{ medicationSaving ? 'Saving...' : 'Save' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Problem Modal -->
    <div v-if="showProblemModal" class="modal-overlay" @click="closeProblemModal">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h2>{{ editingProblemId ? 'Edit Problem' : 'Add Problem' }}</h2>
          <button class="close-btn" @click="closeProblemModal">✕</button>
        </div>
        <div class="modal-content">
          <div v-if="problemFormError" class="error-banner">{{ problemFormError }}</div>
          <div class="form-group">
            <label>Problem *</label>
            <input v-model="problemForm.name" type="text" placeholder="e.g. Hypertension" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Status</label>
              <select v-model="problemForm.status">
                <option value="active">active</option>
                <option value="resolved">resolved</option>
                <option value="inactive">inactive</option>
              </select>
            </div>
            <div class="form-group">
              <label>Onset Date</label>
              <input v-model="problemForm.onset_date" type="date" />
            </div>
          </div>
          <div class="form-group">
            <label>Resolved Date</label>
            <input v-model="problemForm.resolved_date" type="date" />
          </div>
          <div class="form-group">
            <label>Notes</label>
            <textarea v-model="problemForm.notes" rows="3"></textarea>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="closeProblemModal">Cancel</button>
          <button class="btn-primary" :disabled="problemSaving" @click="saveProblem">
            {{ problemSaving ? 'Saving...' : 'Save' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showDeleteAllergyConfirm" class="modal-overlay" @click="showDeleteAllergyConfirm = false">
      <div class="modal small" @click.stop>
        <div class="modal-content">
          <p>Delete allergy "{{ pendingDeleteAllergy?.allergen }}"?</p>
          <div class="modal-actions">
            <button class="btn-danger" @click="deleteAllergy">Delete</button>
            <button class="btn-secondary" @click="showDeleteAllergyConfirm = false">Cancel</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showDeleteMedicationConfirm" class="modal-overlay" @click="showDeleteMedicationConfirm = false">
      <div class="modal small" @click.stop>
        <div class="modal-content">
          <p>Delete medication "{{ pendingDeleteMedication?.name }}"?</p>
          <div class="modal-actions">
            <button class="btn-danger" @click="deleteMedication">Delete</button>
            <button class="btn-secondary" @click="showDeleteMedicationConfirm = false">Cancel</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showDeleteProblemConfirm" class="modal-overlay" @click="showDeleteProblemConfirm = false">
      <div class="modal small" @click.stop>
        <div class="modal-content">
          <p>Delete problem "{{ pendingDeleteProblem?.name }}"?</p>
          <div class="modal-actions">
            <button class="btn-danger" @click="deleteProblem">Delete</button>
            <button class="btn-secondary" @click="showDeleteProblemConfirm = false">Cancel</button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { Patient, PatientProperty, PatientDocument, Allergy, Medication, Problem, ChartSummary, AllergySeverity, AllergyStatus, MedicationStatus, ProblemStatus } from '@/types'
import { patientPropertiesApi, chartApi, documentsApi } from '@/api/index'
import { logout } from '@/store'

const AUTOSAVE_DELAY_MS = 800
type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

interface PropertyDraft {
  name: string
  description: string
  updated_at?: string
}

const patients = ref<Patient[]>([])
const router = useRouter()
const selectedPatientId = ref<string | null>(null)
const loading = ref(false)
const error = ref('')
const patientProperties = ref<PatientProperty[]>([])
const propertiesLoading = ref(false)
const propertiesError = ref('')
const expandedProperties = ref<Set<number>>(new Set())
const showAddDialog = ref(false)
const showDeleteConfirm = ref(false)
const pendingDelete = ref<PatientProperty | null>(null)
const propertyForm = ref({
  name: '',
  description: ''
})
const propertyDrafts = ref<Record<number, PropertyDraft>>({})
const saveStatuses = ref<Record<number, SaveStatus>>({})
const debounceTimers = new Map<number, ReturnType<typeof setTimeout>>()
const pendingSaveProps = new Map<number, PatientProperty>()

// Add patient state
const showAddPatientModal = ref(false)
const addPatientSaving = ref(false)
const addPatientError = ref('')
const addPatientSuccess = ref(false)
const newPatientPassword = ref('')
const addPatientForm = ref({
  firstName: '',
  lastName: '',
  username: '',
  email: '',
  dateOfBirth: '',
  phone: '',
  address: '',
})

function closeAddPatientModal() {
  showAddPatientModal.value = false
  addPatientSuccess.value = false
  addPatientError.value = ''
  newPatientPassword.value = ''
  addPatientForm.value = { firstName: '', lastName: '', username: '', email: '', dateOfBirth: '', phone: '', address: '' }
}

async function submitAddPatient() {
  addPatientError.value = ''
  const f = addPatientForm.value
  if (!f.firstName || !f.lastName || !f.username || !f.email) {
    addPatientError.value = 'First name, last name, username, and email are required.'
    return
  }
  addPatientSaving.value = true
  try {
    const response = await fetch('/api/patients', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`,
      },
      body: JSON.stringify(f),
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      addPatientError.value = data.error || 'Failed to create patient.'
      return
    }
    newPatientPassword.value = data.temporaryPassword || ''
    addPatientSuccess.value = true
    await loadPatients()
  } catch {
    addPatientError.value = 'Network error while creating patient.'
  } finally {
    addPatientSaving.value = false
  }
}
// Documents state
const documents = ref<PatientDocument[]>([])
const documentsLoading = ref(false)
const documentsError = ref('')
const uploadProgress = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const showRenameDialog = ref(false)
const showDeleteDocConfirm = ref(false)
const pendingDeleteDoc = ref<PatientDocument | null>(null)
const renameForm = ref({
  id: '',
  title: ''
})
const uploadPatientVisible = ref(false)

type ChartTabId = 'summary' | 'allergies' | 'medications' | 'problems' | 'documents'
const chartTabs: { id: ChartTabId; label: string }[] = [
  { id: 'summary', label: 'Summary' },
  { id: 'allergies', label: 'Allergies' },
  { id: 'medications', label: 'Medications' },
  { id: 'problems', label: 'Problems' },
  { id: 'documents', label: 'Documents' },
]
const activeChartTab = ref<ChartTabId>('summary')

const chartSummary = ref<ChartSummary | null>(null)
const summaryLoading = ref(false)
const summaryError = ref('')

const allergies = ref<Allergy[]>([])
const allergiesLoading = ref(false)
const allergiesError = ref('')
const showAllergyModal = ref(false)
const allergySaving = ref(false)
const allergyFormError = ref('')
const editingAllergyId = ref<string | null>(null)
const allergyForm = ref({
  allergen: '',
  reaction: '',
  severity: 'unknown' as AllergySeverity,
  status: 'active' as AllergyStatus,
  notes: '',
})
const showDeleteAllergyConfirm = ref(false)
const pendingDeleteAllergy = ref<Allergy | null>(null)

const medications = ref<Medication[]>([])
const medicationsLoading = ref(false)
const medicationsError = ref('')
const showMedicationModal = ref(false)
const medicationSaving = ref(false)
const medicationFormError = ref('')
const editingMedicationId = ref<string | null>(null)
const medicationForm = ref({
  name: '',
  dosage: '',
  frequency: '',
  route: '',
  status: 'active' as MedicationStatus,
  start_date: '',
  end_date: '',
  notes: '',
})
const showDeleteMedicationConfirm = ref(false)
const pendingDeleteMedication = ref<Medication | null>(null)

const problems = ref<Problem[]>([])
const problemsLoading = ref(false)
const problemsError = ref('')
const showProblemModal = ref(false)
const problemSaving = ref(false)
const problemFormError = ref('')
const editingProblemId = ref<string | null>(null)
const problemForm = ref({
  name: '',
  status: 'active' as ProblemStatus,
  onset_date: '',
  resolved_date: '',
  notes: '',
})
const showDeleteProblemConfirm = ref(false)
const pendingDeleteProblem = ref<Problem | null>(null)

const selectedPatient = computed(() =>
  patients.value.find(p => p.id === selectedPatientId.value) || null
)

const selectedPatientPhotoUrl = ref<string | null>(null)

const selectedPatientInitials = computed(() => {
  const p = selectedPatient.value
  if (!p) return '?'
  const first = (p.first_name || '').charAt(0)
  const last = (p.last_name || '').charAt(0)
  return `${first}${last}`.toUpperCase() || '?'
})

function clearSelectedPatientPhoto() {
  if (selectedPatientPhotoUrl.value) {
    URL.revokeObjectURL(selectedPatientPhotoUrl.value)
    selectedPatientPhotoUrl.value = null
  }
}

async function loadSelectedPatientPhoto() {
  clearSelectedPatientPhoto()
  const patient = selectedPatient.value
  if (!patient?.has_profile_photo) return

  const token = localStorage.getItem('sessionToken')
  if (!token) return

  try {
    const response = await fetch(`/api/patients/${patient.id}/profile-photo`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) return
    const blob = await response.blob()
    selectedPatientPhotoUrl.value = URL.createObjectURL(blob)
  } catch (error) {
    console.error('Failed to load patient profile photo:', error)
  }
}

function selectPatient(patient: Patient) {
  selectedPatientId.value = patient.id
}

function toggleProperty(propertyId: number) {
  const next = new Set(expandedProperties.value)
  if (next.has(propertyId)) {
    next.delete(propertyId)
  } else {
    next.add(propertyId)
  }
  expandedProperties.value = next
}

function openAddProperty() {
  propertyForm.value = { name: '', description: '' }
  showAddDialog.value = true
}

function closeAddDialog() {
  showAddDialog.value = false
}

function confirmDelete(prop: PatientProperty) {
  pendingDelete.value = prop
  showDeleteConfirm.value = true
}

function cancelDelete() {
  pendingDelete.value = null
  showDeleteConfirm.value = false
}

function formatProviderName(name?: string | null) {
  return name?.trim() || 'Unknown provider'
}

function getPropertyDraft(prop: PatientProperty): PropertyDraft {
  const existing = propertyDrafts.value[prop.property_id]
  if (existing) {
    return existing
  }
  const draft: PropertyDraft = {
    name: prop.name,
    description: prop.description || '',
    updated_at: prop.updated_at,
  }
  propertyDrafts.value = {
    ...propertyDrafts.value,
    [prop.property_id]: draft,
  }
  return draft
}

function getPropertyDisplayName(prop: PatientProperty) {
  return getPropertyDraft(prop).name || prop.name
}

function getSaveStatus(propertyId: number): SaveStatus {
  return saveStatuses.value[propertyId] || 'idle'
}

function saveStatusLabel(propertyId: number) {
  const status = getSaveStatus(propertyId)
  if (status === 'saving') return 'Saving…'
  if (status === 'saved') return 'Saved'
  if (status === 'error') return 'Save failed'
  return ''
}

function setSaveStatus(propertyId: number, status: SaveStatus) {
  saveStatuses.value = { ...saveStatuses.value, [propertyId]: status }
  if (status === 'saved') {
    setTimeout(() => {
      if (saveStatuses.value[propertyId] === 'saved') {
        const next = { ...saveStatuses.value }
        delete next[propertyId]
        saveStatuses.value = next
      }
    }, 2000)
  }
}

function clearPendingSaves() {
  for (const timer of debounceTimers.values()) {
    clearTimeout(timer)
  }
  debounceTimers.clear()
  pendingSaveProps.clear()
  propertyDrafts.value = {}
  saveStatuses.value = {}
}

function mergePropertyFromServer(property: PatientProperty) {
  const idx = patientProperties.value.findIndex(p => p.property_id === property.property_id)
  if (idx === -1) {
    patientProperties.value = [...patientProperties.value, property]
  } else {
    const next = [...patientProperties.value]
    next[idx] = property
    patientProperties.value = next
  }
  propertyDrafts.value = {
    ...propertyDrafts.value,
    [property.property_id]: {
      name: property.name,
      description: property.description || '',
      updated_at: property.updated_at,
    },
  }
}

function onPropertyFieldChange(prop: PatientProperty, field: 'name' | 'description', value: string) {
  const draft = getPropertyDraft(prop)
  propertyDrafts.value = {
    ...propertyDrafts.value,
    [prop.property_id]: {
      ...draft,
      [field]: value,
    },
  }
  schedulePropertySave(prop)
}

function schedulePropertySave(prop: PatientProperty) {
  pendingSaveProps.set(prop.property_id, prop)
  const existingTimer = debounceTimers.get(prop.property_id)
  if (existingTimer) {
    clearTimeout(existingTimer)
  }
  const timer = setTimeout(() => {
    debounceTimers.delete(prop.property_id)
    const latestProp = pendingSaveProps.get(prop.property_id) || prop
    pendingSaveProps.delete(prop.property_id)
    void persistPropertyDraft(latestProp)
  }, AUTOSAVE_DELAY_MS)
  debounceTimers.set(prop.property_id, timer)
}

async function persistPropertyDraft(prop: PatientProperty, keepalive = false) {
  if (!selectedPatientId.value) return

  const draft = getPropertyDraft(prop)
  if (!draft.name.trim()) {
    setSaveStatus(prop.property_id, 'error')
    return
  }

  setSaveStatus(prop.property_id, 'saving')

  const payload = {
    name: draft.name.trim(),
    description: draft.description,
    updated_at: draft.updated_at || prop.updated_at,
  }

  if (keepalive) {
    const token = localStorage.getItem('sessionToken')
    fetch(`/api/patient-properties/${selectedPatientId.value}/${prop.property_id}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
      keepalive: true,
    }).catch(() => {})
    return
  }

  const response = await patientPropertiesApi.update(
    selectedPatientId.value,
    prop.property_id,
    payload,
  )

  if (handleApiAuthFailure(response.error)) {
    return
  }

  if (response.error?.includes('HTTP 409')) {
    propertiesError.value = 'Note was updated by another provider. Reloading latest version.'
    await loadProperties()
    return
  }

  if (response.error || !response.data?.property) {
    setSaveStatus(prop.property_id, 'error')
    propertiesError.value = response.error || 'Failed to save note'
    schedulePropertySave(prop)
    return
  }

  mergePropertyFromServer(response.data.property)
  setSaveStatus(prop.property_id, 'saved')
  propertiesError.value = ''
}

function flushPendingSaves() {
  for (const [propertyId, timer] of debounceTimers.entries()) {
    clearTimeout(timer)
    debounceTimers.delete(propertyId)
    const prop = pendingSaveProps.get(propertyId)
      || patientProperties.value.find(p => p.property_id === propertyId)
    pendingSaveProps.delete(propertyId)
    if (prop) {
      persistPropertyDraft(prop, true)
    }
  }
}

function handleBeforeUnload() {
  flushPendingSaves()
}

function handleApiAuthFailure(error?: string): boolean {
  if (error?.includes('HTTP 401')) {
    logout()
    void router.replace('/')
    return true
  }
  return false
}

function formatDate(dateStr: string) {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
}

async function handleAuthFailure(response: Response): Promise<boolean> {
  if (response.status !== 401) {
    return false
  }

  logout()
  await router.replace('/')
  return true
}

async function loadPatients() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetch('/api/patients', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })

    if (await handleAuthFailure(response)) {
      return
    }

    if (!response.ok) {
      error.value = 'Failed to load patients'
      return
    }

    const data = await response.json()
    patients.value = data.patients || []
  } catch (err) {
    console.error('Failed to load patients:', err)
    error.value = 'Failed to load patients'
  } finally {
    loading.value = false
  }
}

async function loadProperties() {
  if (!selectedPatientId.value) {
    patientProperties.value = []
    return
  }

  clearPendingSaves()
  propertiesLoading.value = true
  propertiesError.value = ''
  try {
    const response = await patientPropertiesApi.list(selectedPatientId.value)

    if (handleApiAuthFailure(response.error)) {
      return
    }

    if (response.error) {
      propertiesError.value = 'Failed to load properties'
      return
    }

    patientProperties.value = response.data?.properties || []
    expandedProperties.value = new Set()
  } catch (err) {
    console.error('Failed to load properties:', err)
    propertiesError.value = 'Failed to load properties'
  } finally {
    propertiesLoading.value = false
  }
}

async function saveProperty() {
  if (!selectedPatientId.value || !propertyForm.value.name.trim()) return

  try {
    const response = await patientPropertiesApi.create(selectedPatientId.value, {
      name: propertyForm.value.name.trim(),
      description: propertyForm.value.description,
    })

    if (handleApiAuthFailure(response.error)) {
      return
    }

    if (response.error || !response.data?.property) {
      propertiesError.value = response.error || 'Failed to add property'
      return
    }

    const created = response.data.property
    patientProperties.value = [...patientProperties.value, created]
    propertyDrafts.value = {
      ...propertyDrafts.value,
      [created.property_id]: {
        name: created.name,
        description: created.description || '',
        updated_at: created.updated_at,
      },
    }
    expandedProperties.value = new Set(expandedProperties.value).add(created.property_id)
    showAddDialog.value = false
  } catch (err) {
    console.error('Failed to add property:', err)
    propertiesError.value = 'Failed to add property'
  }
}

async function deleteProperty() {
  if (!selectedPatientId.value || !pendingDelete.value) return

  const propertyId = pendingDelete.value.property_id
  const timer = debounceTimers.get(propertyId)
  if (timer) {
    clearTimeout(timer)
    debounceTimers.delete(propertyId)
    pendingSaveProps.delete(propertyId)
  }

  try {
    const response = await patientPropertiesApi.delete(selectedPatientId.value, propertyId)

    if (handleApiAuthFailure(response.error)) {
      return
    }

    if (response.error) {
      propertiesError.value = 'Failed to delete property'
      return
    }

    patientProperties.value = patientProperties.value.filter(
      prop => prop.property_id !== propertyId
    )
    const nextDrafts = { ...propertyDrafts.value }
    delete nextDrafts[propertyId]
    propertyDrafts.value = nextDrafts
    const nextStatuses = { ...saveStatuses.value }
    delete nextStatuses[propertyId]
    saveStatuses.value = nextStatuses
    cancelDelete()
  } catch (err) {
    console.error('Failed to delete property:', err)
    propertiesError.value = 'Failed to delete property'
  }
}

onMounted(() => {
  loadPatients()
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
  clearPendingSaves()
  clearSelectedPatientPhoto()
})

watch(selectedPatientId, () => {
  clearPendingSaves()
  activeChartTab.value = 'summary'
  loadSelectedPatientPhoto()
  loadProperties()
  loadDocuments()
  loadChartSummary()
  loadAllergies()
  loadMedications()
  loadProblems()
})

watch(activeChartTab, (tab) => {
  if (!selectedPatientId.value) return
  if (tab === 'summary') loadChartSummary()
  if (tab === 'allergies') loadAllergies()
  if (tab === 'medications') loadMedications()
  if (tab === 'problems') loadProblems()
  if (tab === 'documents') loadDocuments()
})

// Document functions
async function loadDocuments() {
  if (!selectedPatientId.value) {
    documents.value = []
    return
  }

  documentsLoading.value = true
  documentsError.value = ''
  try {
    const response = await fetch(`/api/documents/${selectedPatientId.value}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })

    if (await handleAuthFailure(response)) {
      return
    }

    if (!response.ok) {
      documentsError.value = 'Failed to load documents'
      return
    }

    const data = await response.json()
    documents.value = data.documents || []
  } catch (err) {
    console.error('Failed to load documents:', err)
    documentsError.value = 'Failed to load documents'
  } finally {
    documentsLoading.value = false
  }
}

function triggerFileUpload() {
  fileInput.value?.click()
}

async function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const files = target.files
  
  if (!files || files.length === 0 || !selectedPatientId.value) return
  
  uploadProgress.value = true
  documentsError.value = ''
  
  try {
    const formData = new FormData()
    for (const file of Array.from(files)) {
      formData.append('files', file)
    }
    formData.append('patient_visible', uploadPatientVisible.value ? 'true' : 'false')
    
    const response = await fetch(`/api/documents/${selectedPatientId.value}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      },
      body: formData
    })

    if (await handleAuthFailure(response)) {
      return
    }
    
    if (!response.ok) {
      const data = await response.json()
      documentsError.value = data.error || 'Failed to upload files'
      return
    }
    
    const data = await response.json()
    documents.value = [...data.documents, ...documents.value]
    
    if (data.errors && data.errors.length > 0) {
      documentsError.value = data.errors.join(', ')
    }
  } catch (err) {
    console.error('Failed to upload files:', err)
    documentsError.value = 'Failed to upload files'
  } finally {
    uploadProgress.value = false
    // Reset file input
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  }
}

async function downloadDocument(doc: PatientDocument) {
  try {
    const response = await fetch(`/api/documents/download/${doc.id}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })

    if (await handleAuthFailure(response)) {
      return
    }
    
    if (!response.ok) {
      documentsError.value = 'Failed to download document'
      return
    }
    
    const blob = await response.blob()
    const url = globalThis.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = doc.title || doc.file_name
    document.body.appendChild(a)
    a.click()
    globalThis.URL.revokeObjectURL(url)
    a.remove()
  } catch (err) {
    console.error('Failed to download document:', err)
    documentsError.value = 'Failed to download document'
  }
}

function openRenameDialog(doc: PatientDocument) {
  renameForm.value = { id: doc.id, title: doc.title }
  showRenameDialog.value = true
}

function closeRenameDialog() {
  showRenameDialog.value = false
}

async function renameDocument() {
  if (!renameForm.value.title.trim()) return
  
  try {
    const response = await fetch(`/api/documents/${renameForm.value.id}/rename`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      },
      body: JSON.stringify({ title: renameForm.value.title.trim() })
    })

    if (await handleAuthFailure(response)) {
      return
    }
    
    if (!response.ok) {
      documentsError.value = 'Failed to rename document'
      return
    }
    
    const data = await response.json()
    const idx = documents.value.findIndex(d => d.id === renameForm.value.id)
    if (idx !== -1) {
      documents.value[idx] = data.document
    }
    showRenameDialog.value = false
  } catch (err) {
    console.error('Failed to rename document:', err)
    documentsError.value = 'Failed to rename document'
  }
}

function confirmDeleteDocument(doc: PatientDocument) {
  pendingDeleteDoc.value = doc
  showDeleteDocConfirm.value = true
}

function cancelDeleteDocument() {
  pendingDeleteDoc.value = null
  showDeleteDocConfirm.value = false
}

async function deleteDocument() {
  if (!pendingDeleteDoc.value) return
  
  try {
    const response = await fetch(`/api/documents/${pendingDeleteDoc.value.id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('sessionToken')}`
      }
    })

    if (await handleAuthFailure(response)) {
      return
    }
    
    if (!response.ok) {
      documentsError.value = 'Failed to delete document'
      return
    }
    
    documents.value = documents.value.filter(d => d.id !== pendingDeleteDoc.value?.id)
    cancelDeleteDocument()
  } catch (err) {
    console.error('Failed to delete document:', err)
    documentsError.value = 'Failed to delete document'
  }
}

function formatFileSize(bytes: number): string {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  while (bytes >= 1024 && i < units.length - 1) {
    bytes /= 1024
    i++
  }
  return `${bytes.toFixed(1)} ${units[i]}`
}

async function loadChartSummary() {
  if (!selectedPatientId.value) {
    chartSummary.value = null
    return
  }
  summaryLoading.value = true
  summaryError.value = ''
  try {
    const result = await chartApi.getSummary(selectedPatientId.value)
    if (result.error) {
      summaryError.value = result.error
      return
    }
    chartSummary.value = result.data?.summary || null
  } catch (err) {
    console.error('Failed to load chart summary:', err)
    summaryError.value = 'Failed to load chart summary'
  } finally {
    summaryLoading.value = false
  }
}

async function loadAllergies() {
  if (!selectedPatientId.value) {
    allergies.value = []
    return
  }
  allergiesLoading.value = true
  allergiesError.value = ''
  try {
    const result = await chartApi.listAllergies(selectedPatientId.value)
    if (result.error) {
      allergiesError.value = result.error
      return
    }
    allergies.value = result.data?.allergies || []
  } catch (err) {
    console.error('Failed to load allergies:', err)
    allergiesError.value = 'Failed to load allergies'
  } finally {
    allergiesLoading.value = false
  }
}

function openAllergyModal(item?: Allergy) {
  allergyFormError.value = ''
  if (item) {
    editingAllergyId.value = item.id
    allergyForm.value = {
      allergen: item.allergen,
      reaction: item.reaction || '',
      severity: item.severity,
      status: item.status,
      notes: item.notes || '',
    }
  } else {
    editingAllergyId.value = null
    allergyForm.value = {
      allergen: '',
      reaction: '',
      severity: 'unknown',
      status: 'active',
      notes: '',
    }
  }
  showAllergyModal.value = true
}

function closeAllergyModal() {
  showAllergyModal.value = false
  allergyFormError.value = ''
}

async function saveAllergy() {
  if (!selectedPatientId.value) return
  if (!allergyForm.value.allergen.trim()) {
    allergyFormError.value = 'Allergen is required.'
    return
  }
  allergySaving.value = true
  allergyFormError.value = ''
  try {
    const payload = {
      allergen: allergyForm.value.allergen.trim(),
      reaction: allergyForm.value.reaction,
      severity: allergyForm.value.severity,
      status: allergyForm.value.status,
      notes: allergyForm.value.notes,
    }
    const result = editingAllergyId.value
      ? await chartApi.updateAllergy(selectedPatientId.value, editingAllergyId.value, payload)
      : await chartApi.createAllergy(selectedPatientId.value, payload)
    if (result.error) {
      allergyFormError.value = result.error
      return
    }
    closeAllergyModal()
    await Promise.all([loadAllergies(), loadChartSummary()])
  } finally {
    allergySaving.value = false
  }
}

function confirmDeleteAllergy(item: Allergy) {
  pendingDeleteAllergy.value = item
  showDeleteAllergyConfirm.value = true
}

async function deleteAllergy() {
  if (!selectedPatientId.value || !pendingDeleteAllergy.value) return
  const result = await chartApi.deleteAllergy(selectedPatientId.value, pendingDeleteAllergy.value.id)
  if (result.error) {
    allergiesError.value = result.error
  } else {
    showDeleteAllergyConfirm.value = false
    pendingDeleteAllergy.value = null
    await Promise.all([loadAllergies(), loadChartSummary()])
  }
}

async function loadMedications() {
  if (!selectedPatientId.value) {
    medications.value = []
    return
  }
  medicationsLoading.value = true
  medicationsError.value = ''
  try {
    const result = await chartApi.listMedications(selectedPatientId.value)
    if (result.error) {
      medicationsError.value = result.error
      return
    }
    medications.value = result.data?.medications || []
  } catch (err) {
    console.error('Failed to load medications:', err)
    medicationsError.value = 'Failed to load medications'
  } finally {
    medicationsLoading.value = false
  }
}

function openMedicationModal(item?: Medication) {
  medicationFormError.value = ''
  if (item) {
    editingMedicationId.value = item.id
    medicationForm.value = {
      name: item.name,
      dosage: item.dosage || '',
      frequency: item.frequency || '',
      route: item.route || '',
      status: item.status,
      start_date: item.start_date ? String(item.start_date).slice(0, 10) : '',
      end_date: item.end_date ? String(item.end_date).slice(0, 10) : '',
      notes: item.notes || '',
    }
  } else {
    editingMedicationId.value = null
    medicationForm.value = {
      name: '',
      dosage: '',
      frequency: '',
      route: '',
      status: 'active',
      start_date: '',
      end_date: '',
      notes: '',
    }
  }
  showMedicationModal.value = true
}

function closeMedicationModal() {
  showMedicationModal.value = false
  medicationFormError.value = ''
}

async function saveMedication() {
  if (!selectedPatientId.value) return
  if (!medicationForm.value.name.trim()) {
    medicationFormError.value = 'Name is required.'
    return
  }
  medicationSaving.value = true
  medicationFormError.value = ''
  try {
    const payload = {
      name: medicationForm.value.name.trim(),
      dosage: medicationForm.value.dosage,
      frequency: medicationForm.value.frequency,
      route: medicationForm.value.route,
      status: medicationForm.value.status,
      start_date: medicationForm.value.start_date || null,
      end_date: medicationForm.value.end_date || null,
      notes: medicationForm.value.notes,
    }
    const result = editingMedicationId.value
      ? await chartApi.updateMedication(selectedPatientId.value, editingMedicationId.value, payload)
      : await chartApi.createMedication(selectedPatientId.value, payload)
    if (result.error) {
      medicationFormError.value = result.error
      return
    }
    closeMedicationModal()
    await Promise.all([loadMedications(), loadChartSummary()])
  } finally {
    medicationSaving.value = false
  }
}

function confirmDeleteMedication(item: Medication) {
  pendingDeleteMedication.value = item
  showDeleteMedicationConfirm.value = true
}

async function deleteMedication() {
  if (!selectedPatientId.value || !pendingDeleteMedication.value) return
  const result = await chartApi.deleteMedication(selectedPatientId.value, pendingDeleteMedication.value.id)
  if (result.error) {
    medicationsError.value = result.error
  } else {
    showDeleteMedicationConfirm.value = false
    pendingDeleteMedication.value = null
    await Promise.all([loadMedications(), loadChartSummary()])
  }
}

async function loadProblems() {
  if (!selectedPatientId.value) {
    problems.value = []
    return
  }
  problemsLoading.value = true
  problemsError.value = ''
  try {
    const result = await chartApi.listProblems(selectedPatientId.value)
    if (result.error) {
      problemsError.value = result.error
      return
    }
    problems.value = result.data?.problems || []
  } catch (err) {
    console.error('Failed to load problems:', err)
    problemsError.value = 'Failed to load problems'
  } finally {
    problemsLoading.value = false
  }
}

function openProblemModal(item?: Problem) {
  problemFormError.value = ''
  if (item) {
    editingProblemId.value = item.id
    problemForm.value = {
      name: item.name,
      status: item.status,
      onset_date: item.onset_date ? String(item.onset_date).slice(0, 10) : '',
      resolved_date: item.resolved_date ? String(item.resolved_date).slice(0, 10) : '',
      notes: item.notes || '',
    }
  } else {
    editingProblemId.value = null
    problemForm.value = {
      name: '',
      status: 'active',
      onset_date: '',
      resolved_date: '',
      notes: '',
    }
  }
  showProblemModal.value = true
}

function closeProblemModal() {
  showProblemModal.value = false
  problemFormError.value = ''
}

async function saveProblem() {
  if (!selectedPatientId.value) return
  if (!problemForm.value.name.trim()) {
    problemFormError.value = 'Problem name is required.'
    return
  }
  problemSaving.value = true
  problemFormError.value = ''
  try {
    const payload = {
      name: problemForm.value.name.trim(),
      status: problemForm.value.status,
      onset_date: problemForm.value.onset_date || null,
      resolved_date: problemForm.value.resolved_date || null,
      notes: problemForm.value.notes,
    }
    const result = editingProblemId.value
      ? await chartApi.updateProblem(selectedPatientId.value, editingProblemId.value, payload)
      : await chartApi.createProblem(selectedPatientId.value, payload)
    if (result.error) {
      problemFormError.value = result.error
      return
    }
    closeProblemModal()
    await Promise.all([loadProblems(), loadChartSummary()])
  } finally {
    problemSaving.value = false
  }
}

function confirmDeleteProblem(item: Problem) {
  pendingDeleteProblem.value = item
  showDeleteProblemConfirm.value = true
}

async function deleteProblem() {
  if (!selectedPatientId.value || !pendingDeleteProblem.value) return
  const result = await chartApi.deleteProblem(selectedPatientId.value, pendingDeleteProblem.value.id)
  if (result.error) {
    problemsError.value = result.error
  } else {
    showDeleteProblemConfirm.value = false
    pendingDeleteProblem.value = null
    await Promise.all([loadProblems(), loadChartSummary()])
  }
}

async function toggleDocumentVisibility(doc: PatientDocument) {
  const result = await documentsApi.setVisibility(doc.id, !doc.patient_visible)
  if (result.error) {
    documentsError.value = result.error
    return
  }
  if (result.data?.document) {
    const idx = documents.value.findIndex(d => d.id === doc.id)
    if (idx !== -1) {
      const next = [...documents.value]
      next[idx] = result.data.document
      documents.value = next
    }
  }
}
</script>

<style scoped>
.patients-page {
  min-height: 100vh;
  background: #f5f7fb;
}

.content {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
  padding: 1.5rem 2rem 2rem;
}

.content.split {
  grid-template-columns: 320px 1fr;
}

.patients-list {
  background: white;
  border-radius: 10px;
  padding: 1rem;
  box-shadow: 0 2px 6px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.list-header h2 {
  margin: 0;
  font-size: 1.1rem;
}

.count {
  background: #eef2ff;
  color: #4338ca;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.85rem;
}

.patient-item {
  text-align: left;
  border: 1px solid #e5e7eb;
  background: #fafafa;
  border-radius: 8px;
  padding: 0.75rem 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
}

.patient-item:hover {
  border-color: #6366f1;
  background: #eef2ff;
}

.patient-item.active {
  border-color: #4f46e5;
  background: #e0e7ff;
}

.patient-name {
  font-weight: 600;
}

.patient-meta {
  color: #6b7280;
  font-size: 0.85rem;
}

.state {
  padding: 0.75rem;
  color: #6b7280;
  font-size: 0.9rem;
}

.state.error {
  color: #dc2626;
}

.patient-detail {
  background: white;
  border-radius: 10px;
  padding: 1.5rem;
  box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.detail-header-main {
  display: flex;
  align-items: center;
  gap: 1rem;
  min-width: 0;
}

.patient-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  overflow: hidden;
  background: #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.patient-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.patient-avatar-fallback {
  font-size: 1.1rem;
  font-weight: 700;
  color: #4b5563;
}

.detail-header h2 {
  margin: 0;
}

.badge {
  padding: 0.3rem 0.7rem;
  border-radius: 999px;
  font-size: 0.8rem;
  background: #f3f4f6;
  color: #6b7280;
}

.badge.linked {
  background: #dcfce7;
  color: #15803d;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}

.detail-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 0.9rem;
}

.detail-card label {
  display: block;
  color: #6b7280;
  font-size: 0.8rem;
  margin-bottom: 0.35rem;
}

.detail-note {
  margin-top: 1.5rem;
  color: #6b7280;
  font-size: 0.9rem;
}

.properties-section {
  margin-top: 2rem;
}

.properties-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.properties-header h3 {
  margin: 0;
}

.add-btn {
  border: 1px solid #c7d2fe;
  background: #eef2ff;
  color: #4338ca;
  border-radius: 6px;
  padding: 0.4rem 0.8rem;
  font-weight: 600;
  cursor: pointer;
}

.add-patient-btn {
  display: block;
  width: calc(100% - 2rem);
  margin: 0.75rem 1rem 0;
  padding: 0.55rem 1rem;
  background: #4f46e5;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.2s;
}

.add-patient-btn:hover {
  background: #4338ca;
}

.error-banner {
  background: #fef2f2;
  border: 1px solid #fca5a5;
  color: #b91c1c;
  border-radius: 6px;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.success-banner {
  background: #f0fdf4;
  border: 1px solid #86efac;
  color: #166534;
  border-radius: 6px;
  padding: 0.75rem 1rem;
  font-size: 0.9rem;
  line-height: 1.6;
}

.accordion {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.accordion-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.accordion-header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: #f9fafb;
  border: none;
  cursor: pointer;
  font-weight: 600;
}

.accordion-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.toggle-indicator {
  font-size: 1.2rem;
  font-weight: 700;
}

.delete-btn {
  border: none;
  background: #fee2e2;
  color: #991b1b;
  padding: 0.35rem 0.7rem;
  border-radius: 6px;
  font-size: 0.85rem;
  cursor: pointer;
}

.detail-label {
  font-weight: 600;
  color: #374151;
  margin: 0 0 0.25rem;
}

.accordion-body {
  padding: 0.9rem 1rem;
  background: white;
  color: #374151;
  line-height: 1.4;
}

.note-editor {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.note-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: #6b7280;
}

.note-title-input,
.note-body-input {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 0.6rem 0.75rem;
  font: inherit;
  color: #111827;
  background: #fff;
}

.note-body-input {
  resize: vertical;
  min-height: 120px;
}

.note-audit {
  margin: 0.25rem 0 0;
  font-size: 0.8rem;
  color: #6b7280;
}

.note-save-status-inline {
  font-size: 0.75rem;
  font-weight: 500;
}

.note-save-status-inline.saving {
  color: #4338ca;
}

.note-save-status-inline.saved {
  color: #15803d;
}

.note-save-status-inline.error {
  color: #dc2626;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.modal {
  background: white;
  border-radius: 10px;
  width: 420px;
  max-width: 90%;
  padding: 1rem;
  box-shadow: 0 8px 20px rgba(0,0,0,0.2);
}

.modal.small {
  width: 320px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.2rem;
}

.close-btn {
  border: none;
  background: transparent;
  font-size: 1.2rem;
  cursor: pointer;
}

.modal-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.form-group input,
.form-group textarea {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 0.5rem 0.6rem;
}

.btn-primary {
  background: #4338ca;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
}

.btn-danger {
  background: #dc2626;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
}

/* Documents Section */
.documents-section {
  margin-top: 2rem;
}

.documents-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.documents-header h3 {
  margin: 0;
}

.documents-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.document-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.document-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  min-width: 0;
}

.document-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #4338ca;
  text-decoration: none;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.document-link:hover {
  text-decoration: underline;
}

.doc-icon {
  flex-shrink: 0;
}

.document-size {
  color: #6b7280;
  font-size: 0.8rem;
  flex-shrink: 0;
}

.document-actions {
  display: flex;
  gap: 0.5rem;
}

.icon-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0.35rem 0.5rem;
  border-radius: 6px;
  font-size: 1rem;
  transition: background 0.15s;
}

.icon-btn:hover {
  background: #e5e7eb;
}

.rename-btn:hover {
  background: #dbeafe;
}

.delete-btn-icon:hover {
  background: #fee2e2;
}

.upload-progress {
  margin-top: 0.75rem;
  padding: 0.5rem;
  background: #eef2ff;
  border-radius: 6px;
  color: #4338ca;
  font-size: 0.9rem;
  text-align: center;
}

.banner-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 0.35rem;
  color: #6b7280;
  font-size: 0.85rem;
}

.chart-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-bottom: 1.25rem;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 0.5rem;
}

.chart-tab {
  border: none;
  background: transparent;
  color: #6b7280;
  padding: 0.45rem 0.85rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9rem;
}

.chart-tab:hover {
  background: #f3f4f6;
  color: #374151;
}

.chart-tab.active {
  background: #e0e7ff;
  color: #3730a3;
}

.chart-panel {
  min-height: 200px;
}

.summary-widgets {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.summary-widget {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 0.9rem 1rem;
}

.summary-widget h3 {
  margin: 0 0 0.5rem;
  font-size: 0.95rem;
  color: #1f2937;
}

.summary-widget ul {
  margin: 0;
  padding-left: 1.1rem;
  color: #374151;
  font-size: 0.9rem;
}

.widget-empty {
  margin: 0;
  color: #6b7280;
  font-size: 0.9rem;
}

.severity {
  color: #6b7280;
  text-transform: capitalize;
}

.demographics-grid {
  margin-top: 0.5rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-header h3 {
  margin: 0;
}

.chart-table-wrap {
  overflow-x: auto;
}

.chart-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.chart-table th,
.chart-table td {
  text-align: left;
  padding: 0.65rem 0.75rem;
  border-bottom: 1px solid #e5e7eb;
}

.chart-table th {
  color: #6b7280;
  font-weight: 600;
  background: #f9fafb;
}

.row-actions {
  white-space: nowrap;
  text-align: right;
}

.status-pill {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: capitalize;
  background: #f3f4f6;
  color: #4b5563;
}

.status-pill.active {
  background: #dcfce7;
  color: #15803d;
}

.status-pill.inactive,
.status-pill.discontinued,
.status-pill.resolved,
.status-pill.completed {
  background: #e5e7eb;
  color: #4b5563;
}

.documents-header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.visibility-checkbox {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  color: #374151;
}

.visibility-badge {
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  background: #f3f4f6;
  color: #6b7280;
  flex-shrink: 0;
}

.visibility-badge.visible {
  background: #dbeafe;
  color: #1d4ed8;
}

.form-group select {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 0.5rem 0.6rem;
  background: #fff;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

@media (max-width: 900px) {
  .content.split {
    grid-template-columns: 1fr;
  }

  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
