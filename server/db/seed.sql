-- Development-only seed users for quick local deployment.
-- Uses bcrypt-compatible hashes via pgcrypto's crypt(..., gen_salt('bf')).

WITH doctor_hash AS (
    SELECT crypt('Doctor123!', gen_salt('bf', 12)) AS password_hash
),
doctor_user AS (
    INSERT INTO users (
        username, email, password_hash, salt, role, is_active,
        failed_login_attempts, must_change_password, password_last_changed
    )
    SELECT
        'doctor1',
        'doctor1@test.com',
        dh.password_hash,
        substring(dh.password_hash FROM 1 FOR 29),
        'doctor',
        TRUE,
        0,
        FALSE,
        NOW()
    FROM doctor_hash dh
    WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'doctor1')
    RETURNING id
),
resolved_doctor AS (
    SELECT id FROM doctor_user
    UNION ALL
    SELECT id FROM users WHERE username = 'doctor1'
    LIMIT 1
)
INSERT INTO doctors (user_id, first_name, last_name, specialty, license_number)
SELECT id, 'Sarah', 'Johnson', 'Family Medicine', 'MD12345'
FROM resolved_doctor
WHERE NOT EXISTS (
    SELECT 1
    FROM doctors d
    JOIN users u ON u.id = d.user_id
    WHERE u.username = 'doctor1'
);

WITH patient_hash AS (
    SELECT crypt('Patient123!', gen_salt('bf', 12)) AS password_hash
),
patient_user AS (
    INSERT INTO users (
        username, email, password_hash, salt, role, is_active,
        failed_login_attempts, must_change_password, password_last_changed
    )
    SELECT
        'patient1',
        'patient1@test.com',
        ph.password_hash,
        substring(ph.password_hash FROM 1 FOR 29),
        'patient',
        TRUE,
        0,
        FALSE,
        NOW()
    FROM patient_hash ph
    WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'patient1')
    RETURNING id
),
resolved_patient AS (
    SELECT id FROM patient_user
    UNION ALL
    SELECT id FROM users WHERE username = 'patient1'
    LIMIT 1
)
INSERT INTO patients (user_id, first_name, last_name, date_of_birth, phone)
SELECT id, 'John', 'Smith', '1990-05-15', '555-0100'
FROM resolved_patient
WHERE NOT EXISTS (
    SELECT 1
    FROM patients p
    JOIN users u ON u.id = p.user_id
    WHERE u.username = 'patient1'
);

-- Additional providers and patients for dashboard testing.
INSERT INTO users (
    username, email, password_hash, salt, role, is_active,
    failed_login_attempts, must_change_password, password_last_changed
)
SELECT
    provider.username,
    provider.email,
    provider_hash.password_hash,
    substring(provider_hash.password_hash FROM 1 FOR 29),
    'doctor',
    TRUE,
    0,
    FALSE,
    NOW()
FROM (
    VALUES
        ('doctor2', 'doctor2@test.com', 'Doctor123!'),
        ('doctor3', 'doctor3@test.com', 'Doctor123!'),
        ('doctor4', 'doctor4@test.com', 'Doctor123!')
) AS provider(username, email, plain_password)
CROSS JOIN LATERAL (
    SELECT crypt(provider.plain_password, gen_salt('bf', 12)) AS password_hash
) AS provider_hash
WHERE NOT EXISTS (
    SELECT 1 FROM users u WHERE u.username = provider.username
);

INSERT INTO doctors (user_id, first_name, last_name, specialty, license_number)
SELECT u.id, provider.first_name, provider.last_name, provider.specialty, provider.license_number
FROM (
    VALUES
        ('doctor2', 'Michael', 'Lee', 'Cardiology', 'MD22346'),
        ('doctor3', 'Priya', 'Patel', 'Dermatology', 'MD32347'),
        ('doctor4', 'James', 'Wilson', 'Pediatrics', 'MD42348')
) AS provider(username, first_name, last_name, specialty, license_number)
JOIN users u ON u.username = provider.username
WHERE NOT EXISTS (
    SELECT 1
    FROM doctors d
    WHERE d.user_id = u.id
);

INSERT INTO users (
    username, email, password_hash, salt, role, is_active,
    failed_login_attempts, must_change_password, password_last_changed
)
SELECT
    patient.username,
    patient.email,
    patient_hash.password_hash,
    substring(patient_hash.password_hash FROM 1 FOR 29),
    'patient',
    TRUE,
    0,
    FALSE,
    NOW()
FROM (
    VALUES
        ('patient2', 'patient2@test.com', 'Patient123!'),
        ('patient3', 'patient3@test.com', 'Patient123!'),
        ('patient4', 'patient4@test.com', 'Patient123!'),
        ('patient5', 'patient5@test.com', 'Patient123!'),
        ('patient6', 'patient6@test.com', 'Patient123!'),
        ('patient7', 'patient7@test.com', 'Patient123!'),
        ('patient8', 'patient8@test.com', 'Patient123!')
) AS patient(username, email, plain_password)
CROSS JOIN LATERAL (
    SELECT crypt(patient.plain_password, gen_salt('bf', 12)) AS password_hash
) AS patient_hash
WHERE NOT EXISTS (
    SELECT 1 FROM users u WHERE u.username = patient.username
);

INSERT INTO patients (user_id, first_name, last_name, date_of_birth, phone)
SELECT u.id, patient.first_name, patient.last_name, patient.date_of_birth, patient.phone
FROM (
    VALUES
        ('patient2', 'Emma', 'Davis', '1988-11-02'::date, '555-0101'),
        ('patient3', 'Noah', 'Brown', '1979-03-17'::date, '555-0102'),
        ('patient4', 'Olivia', 'Garcia', '1994-08-09'::date, '555-0103'),
        ('patient5', 'Liam', 'Martinez', '1982-12-22'::date, '555-0104'),
        ('patient6', 'Ava', 'Anderson', '2001-01-13'::date, '555-0105'),
        ('patient7', 'Sophia', 'Thomas', '1996-04-05'::date, '555-0106'),
        ('patient8', 'Mason', 'Taylor', '1985-09-29'::date, '555-0107')
) AS patient(username, first_name, last_name, date_of_birth, phone)
JOIN users u ON u.username = patient.username
WHERE NOT EXISTS (
    SELECT 1
    FROM patients p
    WHERE p.user_id = u.id
);

-- Multi-provider appointment set for dashboard calendar/list testing.
INSERT INTO appointments (patient_id, doctor_id, appointment_date, reason, notes, status)
SELECT p.id, d.id, a.appointment_date, a.reason, a.notes, a.status
FROM (
    VALUES
        ('patient1', 'doctor1', '2026-07-10 09:00:00+00'::timestamptz, 'Annual wellness exam', 'Review annual labs', 'confirmed'),
        ('patient2', 'doctor1', '2026-07-10 14:30:00+00'::timestamptz, 'Blood pressure follow-up', 'Check medication tolerance', 'pending'),
        ('patient3', 'doctor2', '2026-07-11 10:00:00+00'::timestamptz, 'Cardiology consult', 'New patient intake', 'confirmed'),
        ('patient4', 'doctor2', '2026-07-11 15:15:00+00'::timestamptz, 'Chest discomfort review', 'Evaluate stress test results', 'completed'),
        ('patient5', 'doctor3', '2026-07-12 11:45:00+00'::timestamptz, 'Skin rash evaluation', 'Recurring seasonal rash', 'confirmed'),
        ('patient6', 'doctor3', '2026-07-12 16:00:00+00'::timestamptz, 'Mole screening', 'Baseline dermatology screening', 'pending'),
        ('patient7', 'doctor4', '2026-07-13 08:30:00+00'::timestamptz, 'Pediatric checkup', 'School physical paperwork', 'confirmed'),
        ('patient8', 'doctor4', '2026-07-13 13:15:00+00'::timestamptz, 'Vaccination consultation', 'Discuss booster schedule', 'cancelled'),
        ('patient1', 'doctor2', '2026-07-15 09:45:00+00'::timestamptz, 'EKG follow-up', 'Discuss ECG findings', 'pending'),
        ('patient3', 'doctor1', '2026-07-16 10:30:00+00'::timestamptz, 'Medication review', 'Adjust antihypertensive dosing', 'confirmed'),
        ('patient4', 'doctor3', '2026-07-17 15:00:00+00'::timestamptz, 'Allergy patch test', 'Post-test consult', 'confirmed'),
        ('patient6', 'doctor4', '2026-07-18 12:30:00+00'::timestamptz, 'Family consult', 'Nutrition and sleep habits', 'pending')
) AS a(patient_username, doctor_username, appointment_date, reason, notes, status)
JOIN users pu ON pu.username = a.patient_username
JOIN users du ON du.username = a.doctor_username
JOIN patients p ON p.user_id = pu.id
JOIN doctors d ON d.user_id = du.id
WHERE NOT EXISTS (
    SELECT 1
    FROM appointments existing
    WHERE existing.patient_id = p.id
      AND existing.doctor_id = d.id
      AND existing.appointment_date = a.appointment_date
      AND existing.reason = a.reason
);

-- Calendar events across multiple providers and event types.
INSERT INTO events (
    doctor_id, patient_id, event_type, title, description, event_date,
    start_time, end_time, color, is_all_day
)
SELECT d.id, p.id, e.event_type, e.title, e.description, e.event_date,
       e.start_time, e.end_time, e.color, e.is_all_day
FROM (
    VALUES
        ('doctor1', 'patient1', 'appointment', 'Annual wellness prep', 'Pre-visit chart review', '2026-07-10'::date, '08:30:00'::time, '09:00:00'::time, '#3b82f6', FALSE),
        ('doctor1', NULL, 'meeting', 'Care team huddle', 'Daily provider alignment', '2026-07-10'::date, '12:00:00'::time, '12:30:00'::time, '#8b5cf6', FALSE),
        ('doctor2', 'patient3', 'appointment', 'Cardiology imaging review', 'Echo and EKG comparison', '2026-07-11'::date, '09:15:00'::time, '10:00:00'::time, '#ef4444', FALSE),
        ('doctor2', NULL, 'blocked_time', 'Procedure block', 'Reserved block for urgent cases', '2026-07-11'::date, '13:00:00'::time, '15:00:00'::time, '#f59e0b', FALSE),
        ('doctor3', 'patient5', 'reminder', 'Derm follow-up reminder', 'Bring previous biopsy report', '2026-07-12'::date, '11:15:00'::time, '11:45:00'::time, '#10b981', FALSE),
        ('doctor3', NULL, 'note', 'Lab review window', 'Pending pathology inbox review', '2026-07-12'::date, '14:00:00'::time, '15:00:00'::time, '#6366f1', FALSE),
        ('doctor4', 'patient7', 'appointment', 'Pediatrics intake prep', 'Immunization records check', '2026-07-13'::date, '08:00:00'::time, '08:30:00'::time, '#3b82f6', FALSE),
        ('doctor4', NULL, 'meeting', 'Parent outreach block', 'Calls for care plan follow-up', '2026-07-13'::date, '16:00:00'::time, '17:00:00'::time, '#14b8a6', FALSE),
        ('doctor1', NULL, 'other', 'Admin catch-up', 'Chart completion and inbox cleanup', '2026-07-14'::date, NULL, NULL, '#64748b', TRUE)
) AS e(doctor_username, patient_username, event_type, title, description, event_date, start_time, end_time, color, is_all_day)
JOIN users du ON du.username = e.doctor_username
JOIN doctors d ON d.user_id = du.id
LEFT JOIN users pu ON pu.username = e.patient_username
LEFT JOIN patients p ON p.user_id = pu.id
WHERE NOT EXISTS (
    SELECT 1
    FROM events existing
    WHERE existing.doctor_id = d.id
      AND existing.event_type = e.event_type
      AND existing.title = e.title
      AND existing.event_date = e.event_date
);

-- Sample messaging: DM between doctor1 and patient1, plus a care-team channel.
WITH doctor1_user AS (
    SELECT id FROM users WHERE username = 'doctor1' LIMIT 1
),
patient1_user AS (
    SELECT id FROM users WHERE username = 'patient1' LIMIT 1
),
doctor2_user AS (
    SELECT id FROM users WHERE username = 'doctor2' LIMIT 1
),
existing_dm AS (
    SELECT c.id
    FROM conversations c
    WHERE c.type = 'dm'
      AND EXISTS (
          SELECT 1 FROM conversation_participants cp
          JOIN doctor1_user d1 ON cp.user_id = d1.id
          WHERE cp.conversation_id = c.id
      )
      AND EXISTS (
          SELECT 1 FROM conversation_participants cp
          JOIN patient1_user p1 ON cp.user_id = p1.id
          WHERE cp.conversation_id = c.id
      )
    LIMIT 1
),
new_dm AS (
    INSERT INTO conversations (type, title, created_by_user_id)
    SELECT 'dm', NULL, d1.id
    FROM doctor1_user d1
    WHERE NOT EXISTS (SELECT 1 FROM existing_dm)
    RETURNING id, created_by_user_id
),
resolved_dm AS (
    SELECT id FROM existing_dm
    UNION ALL
    SELECT id FROM new_dm
),
dm_participants AS (
    INSERT INTO conversation_participants (conversation_id, user_id, last_read_at)
    SELECT rd.id, u.id, NOW()
    FROM resolved_dm rd
    CROSS JOIN (
        SELECT id FROM doctor1_user
        UNION
        SELECT id FROM patient1_user
    ) u
    WHERE NOT EXISTS (
        SELECT 1
        FROM conversation_participants cp
        WHERE cp.conversation_id = rd.id AND cp.user_id = u.id
    )
    RETURNING conversation_id
),
dm_message AS (
    INSERT INTO messages (conversation_id, sender_user_id, body)
    SELECT rd.id, d1.id, 'Hi John — welcome to secure messaging. Reply here anytime with questions about your care.'
    FROM resolved_dm rd
    CROSS JOIN doctor1_user d1
    WHERE NOT EXISTS (
        SELECT 1 FROM messages m WHERE m.conversation_id = rd.id
    )
    RETURNING id
)
SELECT 1 FROM dm_message
UNION ALL
SELECT 1 FROM dm_participants
LIMIT 1;

WITH doctor1_user AS (
    SELECT id FROM users WHERE username = 'doctor1' LIMIT 1
),
doctor2_user AS (
    SELECT id FROM users WHERE username = 'doctor2' LIMIT 1
),
patient1_user AS (
    SELECT id FROM users WHERE username = 'patient1' LIMIT 1
),
existing_channel AS (
    SELECT id FROM conversations
    WHERE type = 'channel' AND title = 'Care Team — Smith'
    LIMIT 1
),
new_channel AS (
    INSERT INTO conversations (type, title, created_by_user_id)
    SELECT 'channel', 'Care Team — Smith', d1.id
    FROM doctor1_user d1
    WHERE NOT EXISTS (SELECT 1 FROM existing_channel)
    RETURNING id
),
resolved_channel AS (
    SELECT id FROM existing_channel
    UNION ALL
    SELECT id FROM new_channel
)
INSERT INTO conversation_participants (conversation_id, user_id, last_read_at)
SELECT rc.id, u.id, NOW()
FROM resolved_channel rc
CROSS JOIN (
    SELECT id FROM doctor1_user
    UNION
    SELECT id FROM doctor2_user
    UNION
    SELECT id FROM patient1_user
) u
WHERE NOT EXISTS (
    SELECT 1
    FROM conversation_participants cp
    WHERE cp.conversation_id = rc.id AND cp.user_id = u.id
);

INSERT INTO messages (conversation_id, sender_user_id, body)
SELECT c.id, d1.id, 'Care team channel for coordinating John Smith''s follow-up plan.'
FROM conversations c
CROSS JOIN (SELECT id FROM users WHERE username = 'doctor1' LIMIT 1) d1
WHERE c.type = 'channel'
  AND c.title = 'Care Team — Smith'
  AND NOT EXISTS (
      SELECT 1 FROM messages m WHERE m.conversation_id = c.id
  );

-- Sample chart data for patient1 (provider chart demo).
INSERT INTO allergies (
    patient_id, allergen, reaction, severity, status, notes, created_by_doctor_id
)
SELECT p.id, a.allergen, a.reaction, a.severity, a.status, a.notes, d.id
FROM (
    VALUES
        ('Penicillin', 'Rash and hives', 'moderate', 'active', 'Avoid all beta-lactam antibiotics'),
        ('Peanuts', 'Anaphylaxis', 'severe', 'active', 'Carries epinephrine auto-injector')
) AS a(allergen, reaction, severity, status, notes)
JOIN users pu ON pu.username = 'patient1'
JOIN patients p ON p.user_id = pu.id
JOIN users du ON du.username = 'doctor1'
JOIN doctors d ON d.user_id = du.id
WHERE NOT EXISTS (
    SELECT 1
    FROM allergies existing
    WHERE existing.patient_id = p.id
      AND existing.allergen = a.allergen
);

INSERT INTO medications (
    patient_id, name, dosage, frequency, route, status, start_date, notes, prescribed_by_doctor_id
)
SELECT p.id, m.name, m.dosage, m.frequency, m.route, m.status, m.start_date, m.notes, d.id
FROM (
    VALUES
        ('Lisinopril', '10 mg', 'Once daily', 'Oral', 'active', '2025-01-15'::date, 'Blood pressure control'),
        ('Metformin', '500 mg', 'Twice daily', 'Oral', 'active', '2024-06-01'::date, 'Type 2 diabetes')
) AS m(name, dosage, frequency, route, status, start_date, notes)
JOIN users pu ON pu.username = 'patient1'
JOIN patients p ON p.user_id = pu.id
JOIN users du ON du.username = 'doctor1'
JOIN doctors d ON d.user_id = du.id
WHERE NOT EXISTS (
    SELECT 1
    FROM medications existing
    WHERE existing.patient_id = p.id
      AND existing.name = m.name
);

INSERT INTO problems (
    patient_id, name, status, onset_date, notes, created_by_doctor_id
)
SELECT p.id, pr.name, pr.status, pr.onset_date, pr.notes, d.id
FROM (
    VALUES
        ('Hypertension', 'active', '2024-11-01'::date, 'Well controlled on lisinopril'),
        ('Type 2 Diabetes Mellitus', 'active', '2024-05-20'::date, 'A1C trending down')
) AS pr(name, status, onset_date, notes)
JOIN users pu ON pu.username = 'patient1'
JOIN patients p ON p.user_id = pu.id
JOIN users du ON du.username = 'doctor1'
JOIN doctors d ON d.user_id = du.id
WHERE NOT EXISTS (
    SELECT 1
    FROM problems existing
    WHERE existing.patient_id = p.id
      AND existing.name = pr.name
);

-- Sample documents: one patient-visible, one provider-only.
INSERT INTO medical_documents (
    patient_id, doctor_id, document_type, title, description,
    file_path, file_name, file_size, document_date, patient_visible
)
SELECT p.id, d.id, doc.document_type, doc.title, doc.description,
       doc.file_path, doc.file_name, doc.file_size, doc.document_date, doc.patient_visible
FROM (
    VALUES
        (
            'lab_result',
            'Annual Labs Summary',
            'Shared lab summary for patient portal',
            'seed/annual-labs-summary.txt',
            'annual-labs-summary.txt',
            128,
            '2026-06-01'::date,
            TRUE
        ),
        (
            'document',
            'Internal Chart Review Notes',
            'Provider-only clinical notes',
            'seed/internal-chart-review.txt',
            'internal-chart-review.txt',
            256,
            '2026-06-15'::date,
            FALSE
        )
) AS doc(document_type, title, description, file_path, file_name, file_size, document_date, patient_visible)
JOIN users pu ON pu.username = 'patient1'
JOIN patients p ON p.user_id = pu.id
JOIN users du ON du.username = 'doctor1'
JOIN doctors d ON d.user_id = du.id
WHERE NOT EXISTS (
    SELECT 1
    FROM medical_documents existing
    WHERE existing.patient_id = p.id
      AND existing.title = doc.title
);
