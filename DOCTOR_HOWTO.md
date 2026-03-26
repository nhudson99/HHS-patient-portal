# Doctor How-To Guide — HHS Patient Portal

This guide walks through every feature available to doctors in the HHS Patient Portal, step by step.

---

## Table of Contents

1. [Logging In](#1-logging-in)
2. [Navigation Overview](#2-navigation-overview)
3. [Home — Calendar Dashboard](#3-home--calendar-dashboard)
   - [Switching Calendar Views](#switching-calendar-views)
   - [Navigating Dates](#navigating-dates)
   - [Creating a New Event](#creating-a-new-event)
   - [Editing an Existing Event](#editing-an-existing-event)
   - [Deleting an Event](#deleting-an-event)
   - [Confirming a Pending Appointment](#confirming-a-pending-appointment)
4. [Patients](#4-patients)
   - [Browsing the Patient List](#browsing-the-patient-list)
   - [Viewing a Patient Profile](#viewing-a-patient-profile)
   - [Managing Patient Notes](#managing-patient-notes)
   - [Managing Patient Documents](#managing-patient-documents)
5. [Profile](#5-profile)
   - [Viewing Account Information](#viewing-account-information)
   - [Changing Your Password](#changing-your-password)
6. [Feature Request](#6-feature-request)

---

## 1. Logging In

1. Open the portal URL in your browser. You will land on the **Login** page.
2. Enter your **username** and **password**, then click **Login**.
3. If you have been assigned a temporary password by an administrator, you will be prompted to set a new password before continuing.
4. After a successful login you are automatically redirected to the **Doctor Dashboard** (`/doctor`).

> **Session timeout:** Your session expires after a period of inactivity. You will be sent back to the login page and will need to sign in again.

---

## 2. Navigation Overview

Once logged in, a header bar appears at the top of every page with the following controls:

| Element | Description |
|---|---|
| **Home** | Returns to the Calendar Dashboard (`/doctor`). |
| **Patients** | Opens the patient list and profile viewer (`/patients`). |
| **Profile** | Opens your account and password settings (`/profile`). |
| **FEATURE REQUEST** | Opens the feature request dialog (doctors only). |
| *Your name* | Displays the username of the currently signed-in doctor. |
| **Logout** | Ends your session and returns to the login page. |

---

## 3. Home — Calendar Dashboard

The dashboard (`/doctor`) is a full-featured calendar that shows your scheduled events and incoming patient appointment requests.

### Switching Calendar Views

Three view modes are available via the buttons in the top-left corner:

| Button | What it shows |
|---|---|
| **Day** | A 24-hour grid for the selected day, with each event displayed in its time slot. |
| **Week** | A 7-day column layout (Sunday–Saturday) for the current week. |
| **Month** | A traditional monthly grid. Events appear as colored dots on each day cell. |

Click any button to switch instantly.

### Navigating Dates

Use the three navigation buttons next to the view switcher:

| Button | Action |
|---|---|
| **← Previous** | Move back one day / week / month (depending on the active view). |
| **Today** | Jump immediately to the current date. |
| **Next →** | Move forward one day / week / month. |

The current date range is shown to the right of these buttons as a label that updates automatically.

In **Week** or **Month** view you can also click a specific day cell to jump directly into **Day** view for that date.

### Creating a New Event

**Option A — Click a time slot (Day view only):**

1. Switch to **Day** view.
2. Click on the hour row where you want the event to start.
3. The **New Event** dialog opens with the start time pre-filled.

**Option B — Right-click context menu:**

1. Right-click anywhere on the calendar background (any view).
2. Select **Add Event** from the context menu.
3. The **New Event** dialog opens.

**Filling in the event form:**

| Field | Required | Description |
|---|---|---|
| **Title** | ✅ | Short name for the event (e.g., "Follow-up with J. Smith"). |
| **Date** | ✅ | The calendar date for the event. |
| **Type** | ✅ | Choose from: `Appointment`, `Reminder`, `Note`, `Blocked Time`, `Meeting`, `Other`. |
| **Start Time** | Optional | Time the event begins (24-hour picker). |
| **End Time** | Optional | Time the event ends. |
| **All Day Event** | Optional | Check this box to mark the event as all-day (hides time fields). |
| **Description** | Optional | Free-text notes or details. |
| **Color** | Optional | Pick a color swatch to visually distinguish the event on the calendar. |

Click **Save Event** to add it to the calendar, or **Cancel** to discard.

### Editing an Existing Event

1. Click on any event on the calendar (in Day or Week view).
2. The event form dialog opens pre-populated with the event's current data.
3. Make your changes and click **Save Event**.

Alternatively, right-click the event and select **Edit** from the context menu.

### Deleting an Event

1. Right-click the event on the calendar.
2. Select **Delete** from the context menu.
3. A confirmation dialog appears — click **Delete** to confirm, or **Cancel** to abort.

> **Note:** Only calendar events you created can be deleted this way. Patient appointment requests (shown with a "pending" status badge) are managed separately via the confirm workflow below.

### Confirming a Pending Appointment

When a patient submits an appointment request it appears on your calendar as an event labeled with the patient's name and the status `(pending)`.

1. Locate the pending appointment event on your calendar.
2. Click the **✓ Confirm** button that appears inside the event card.
3. The appointment status changes to `confirmed` and the event refreshes automatically.

---

## 4. Patients

The Patients page (`/patients`) gives you a searchable roster of all patients and a detailed profile panel.

### Browsing the Patient List

The left-hand sidebar lists every patient in the system, sorted alphabetically. Each entry shows:
- Full name
- Date of birth

The total patient count is shown next to the **All Patients** heading.

Click any patient name to open their profile in the right-hand panel.

### Viewing a Patient Profile

The detail panel on the right displays the following information for the selected patient:

| Field | Description |
|---|---|
| **Date of Birth** | Patient's date of birth. |
| **Phone** | Contact phone number. |
| **Address** | Mailing/home address (if on record). |
| **Emergency Contact** | Name and phone number of the emergency contact (if on record). |
| **Portal Email** | The patient's portal login email, shown only when the patient has a linked portal account. A **Portal Linked** / **No Portal Account** badge also indicates this status. |

### Managing Patient Notes

The **Notes** section displays custom key/value properties attached to the patient record. These can be used for clinical notes, flags, or any free-form information.

**Adding a note:**

1. Select a patient and scroll to the **Notes** section.
2. Click the **+ Add** button.
3. In the dialog that opens, enter:
   - **Name** *(required)* — a short label for the note (e.g., "Allergy Alert").
   - **Description** *(optional)* — free-text detail.
4. Click **Save**.

**Viewing a note:**

- Notes are displayed in an accordion. Click a note's header row to expand or collapse it and reveal the description.

**Deleting a note:**

1. Locate the note in the accordion.
2. Click the **Delete** button on the right side of the note header.
3. Confirm the deletion in the dialog that appears.

### Managing Patient Documents

The **Documents** section shows all files that have been uploaded for the patient.

**Uploading documents:**

1. Select a patient and scroll to the **Documents** section.
2. Click **+ Upload**.
3. A file chooser opens — select one or more files from your computer.
4. The files are uploaded immediately and appear in the list once complete.

**Downloading a document:**

- Click the document title link. The file will be downloaded through your browser.

**Renaming a document:**

1. Click the ✏️ (pencil) icon next to the document.
2. Enter the new title in the dialog.
3. Click **Save**.

**Deleting a document:**

1. Click the 🗑️ (trash) icon next to the document.
2. Confirm the deletion in the dialog that appears.

---

## 5. Profile

The Profile page (`/profile`) lets you review your account details and update your password.

### Viewing Account Information

The **Account** card on the left shows:

| Field | Description |
|---|---|
| **Username** | Your portal login username. |
| **Email** | The email address registered to your account. |
| **Role** | Your portal role (displayed as `Doctor`). |

### Changing Your Password

1. Navigate to **Profile** from the header.
2. In the **Change Password** card, fill in:
   - **Current Password** — your existing password.
   - **New Password** — must be at least 8 characters and include uppercase letters, lowercase letters, a number, and a special character.
   - **Confirm New Password** — re-enter the new password to confirm.
3. Click **Update Password**.
4. A success message confirms the change. If there are any errors (e.g., passwords don't match, policy not met), an error message is shown instead.

> **Temporary password:** If an administrator reset your password, you will be prompted to change it on your first login. You must complete this step before accessing the rest of the portal.

---

## 6. Feature Request

The **FEATURE REQUEST** button in the header is available exclusively to doctors. Use it to send product feedback directly to the development team.

**Submitting a feature request:**

1. Click the **FEATURE REQUEST** button in the top navigation bar. A dialog opens.
2. In the **Description** field, describe:
   - The problem you are experiencing or the workflow you need.
   - The desired behavior.
   - Who it would help and how.
   > The description must be at least 10 characters.
3. The **Page** field is auto-populated with the current page you are on — this helps the dev team reproduce the context.
4. Click **Submit Request**.
5. A GitHub issue is created automatically. A confirmation message with a link to the issue (e.g., *#42: view on GitHub →*) appears in the dialog so you can track its progress.

> **Note:** A GitHub token must be configured by the portal administrator for this feature to work. If it is not configured, the submission will fail with an explanatory error.
