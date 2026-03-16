"""
Events routes for doctor calendar
Handles calendar events, appointments, and doctor scheduling
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, date, time
from api.db.connection import execute_query, DatabaseTransaction
from api.middleware.auth import authenticate

events_bp = Blueprint('events', __name__, url_prefix='/api/events')


def serialize_event(event):
    """Convert event dict with date/time objects to JSON-serializable dict"""
    if not event:
        return None
    result = dict(event)
    for key, value in result.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, date):
            result[key] = value.isoformat()
        elif isinstance(value, time):
            result[key] = value.strftime('%H:%M:%S')
    return result


@events_bp.route('', methods=['GET'])
@authenticate
def get_events():
    """
    GET /api/events?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    Get events for date range (requires doctor context)
    """
    try:
        user = request.user
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date required'}), 400
        
        # Get doctor ID from user
        doctor_query = "SELECT id FROM doctors WHERE user_id = %s"
        doctor = execute_query(doctor_query, (user['id'],), fetch_one=True)
        
        if not doctor:
            return jsonify({'error': 'User is not a doctor'}), 403
        
        doctor_id = doctor['id']
        
        # Get events for date range
        events_query = """
            SELECT id, doctor_id, patient_id, event_type, title, description, 
                   event_date, start_time, end_time, color, is_all_day,
                   created_at, updated_at
            FROM events
            WHERE doctor_id = %s 
            AND event_date BETWEEN %s AND %s
            ORDER BY event_date, start_time
        """
        
        events = execute_query(
            events_query, 
            (doctor_id, start_date, end_date), 
            fetch_all=True
        )
        
        serialized_events = [serialize_event(e) for e in (events or [])]
        
        # Also fetch appointments for this doctor in the date range
        appointments_query = """
            SELECT a.id, a.doctor_id, a.patient_id, a.appointment_date, 
                   a.status, a.reason, a.notes,
                   a.created_at, a.updated_at,
                   p.first_name || ' ' || p.last_name AS patient_name
            FROM appointments a
            LEFT JOIN patients p ON a.patient_id = p.id
            WHERE a.doctor_id = %s
            AND a.appointment_date BETWEEN %s AND %s
            ORDER BY a.appointment_date
        """
        
        appointments = execute_query(
            appointments_query,
            (doctor_id, start_date, end_date),
            fetch_all=True
        )
        
        # Map status to color
        status_colors = {
            'pending': '#f59e0b',
            'confirmed': '#3b82f6',
            'cancelled': '#ef4444',
            'completed': '#10b981',
        }
        
        # Convert appointments to event format for the calendar
        for apt in (appointments or []):
            appointment_date = apt.get('appointment_date')
            start_time = None
            if isinstance(appointment_date, datetime):
                start_time = appointment_date.strftime('%H:%M:%S')

            apt_event = {
                'id': f"apt-{apt['id']}",
                'doctor_id': apt['doctor_id'],
                'patient_id': apt['patient_id'],
                'event_type': 'appointment',
                'title': f"{apt.get('patient_name', 'Patient')} ({apt['status']})",
                'description': apt.get('reason', ''),
                'event_date': apt['appointment_date'].isoformat() if isinstance(apt['appointment_date'], (date, datetime)) else apt['appointment_date'],
                'start_time': start_time,
                'end_time': None,
                'color': status_colors.get(apt['status'], '#3b82f6'),
                'is_all_day': False,
                'created_at': apt['created_at'].isoformat() if isinstance(apt['created_at'], datetime) else apt.get('created_at'),
                'updated_at': apt['updated_at'].isoformat() if isinstance(apt['updated_at'], datetime) else apt.get('updated_at'),
            }
            serialized_events.append(apt_event)
        
        return jsonify({
            'events': serialized_events
        }), 200
        
    except Exception as e:
        print(f"Events retrieval error: {e}")
        return jsonify({'error': 'Failed to retrieve events'}), 500

@events_bp.route('', methods=['POST'])
@authenticate
def create_event():
    """
    POST /api/events
    Create a new event
    """
    try:
        user = request.user
        data = request.get_json()
        
        # Validate required fields
        required = ['title', 'event_date', 'event_type']
        if not all(field in data for field in required):
            return jsonify({'error': 'Missing required fields: title, event_date, event_type'}), 400
        
        # Get doctor ID
        doctor_query = "SELECT id FROM doctors WHERE user_id = %s"
        doctor = execute_query(doctor_query, (user['id'],), fetch_one=True)
        
        if not doctor:
            return jsonify({'error': 'User is not a doctor'}), 403
        
        doctor_id = doctor['id']
        title = data['title']
        event_date = data['event_date']
        event_type = data['event_type']
        description = data.get('description', '')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        patient_id = data.get('patient_id')
        color = data.get('color', '#3b82f6')
        is_all_day = data.get('is_all_day', False)
        
        # Validate event_type
        valid_types = ['appointment', 'reminder', 'note', 'blocked_time', 'meeting', 'other']
        if event_type not in valid_types:
            return jsonify({'error': f'Invalid event_type. Must be one of: {", ".join(valid_types)}'}), 400
        
        # Create event
        insert_query = """
            INSERT INTO events 
            (doctor_id, patient_id, event_type, title, description, event_date, 
             start_time, end_time, color, is_all_day)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, doctor_id, patient_id, event_type, title, description,
                      event_date, start_time, end_time, color, is_all_day,
                      created_at, updated_at
        """
        
        event = execute_query(
            insert_query,
            (doctor_id, patient_id, event_type, title, description, event_date,
             start_time, end_time, color, is_all_day),
            fetch_one=True
        )
        
        return jsonify({
            'message': 'Event created successfully',
            'event': serialize_event(event)
        }), 201
        
    except Exception as e:
        print(f"Event creation error: {e}")
        return jsonify({'error': 'Failed to create event'}), 500

@events_bp.route('/<event_id>', methods=['GET'])
@authenticate
def get_event(event_id):
    """
    GET /api/events/<event_id>
    Get a specific event
    """
    try:
        user = request.user
        
        # Get doctor ID
        doctor_query = "SELECT id FROM doctors WHERE user_id = %s"
        doctor = execute_query(doctor_query, (user['id'],), fetch_one=True)
        
        if not doctor:
            return jsonify({'error': 'User is not a doctor'}), 403
        
        # Get event (verify ownership)
        event_query = """
            SELECT id, doctor_id, patient_id, event_type, title, description,
                   event_date, start_time, end_time, color, is_all_day,
                   created_at, updated_at
            FROM events
            WHERE id = %s AND doctor_id = %s
        """
        
        event = execute_query(event_query, (event_id, doctor['id']), fetch_one=True)
        
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        return jsonify({'event': serialize_event(event)}), 200
        
    except Exception as e:
        print(f"Event retrieval error: {e}")
        return jsonify({'error': 'Failed to retrieve event'}), 500

@events_bp.route('/<event_id>', methods=['PUT'])
@authenticate
def update_event(event_id):
    """
    PUT /api/events/<event_id>
    Update an event
    """
    try:
        user = request.user
        data = request.get_json()
        
        # Get doctor ID
        doctor_query = "SELECT id FROM doctors WHERE user_id = %s"
        doctor = execute_query(doctor_query, (user['id'],), fetch_one=True)
        
        if not doctor:
            return jsonify({'error': 'User is not a doctor'}), 403
        
        # Verify event ownership
        verify_query = "SELECT id FROM events WHERE id = %s AND doctor_id = %s"
        if not execute_query(verify_query, (event_id, doctor['id']), fetch_one=True):
            return jsonify({'error': 'Event not found or unauthorized'}), 404
        
        # Build update query dynamically based on provided fields
        allowed_fields = ['title', 'description', 'event_date', 'start_time', 'end_time', 
                         'patient_id', 'event_type', 'color', 'is_all_day']
        
        update_parts = []
        params = []
        
        for field in allowed_fields:
            if field in data:
                update_parts.append(f"{field} = %s")
                params.append(data[field])
        
        if not update_parts:
            return jsonify({'error': 'No fields to update'}), 400
        
        # Add updated_at and event_id
        update_parts.append("updated_at = CURRENT_TIMESTAMP")
        params.append(event_id)
        
        update_query = f"""
            UPDATE events
            SET {', '.join(update_parts)}
            WHERE id = %s
            RETURNING id, doctor_id, patient_id, event_type, title, description,
                      event_date, start_time, end_time, color, is_all_day,
                      created_at, updated_at
        """
        
        event = execute_query(update_query, params, fetch_one=True)
        
        return jsonify({
            'message': 'Event updated successfully',
            'event': serialize_event(event)
        }), 200
        
    except Exception as e:
        print(f"Event update error: {e}")
        return jsonify({'error': 'Failed to update event'}), 500

@events_bp.route('/<event_id>', methods=['DELETE'])
@authenticate
def delete_event(event_id):
    """
    DELETE /api/events/<event_id>
    Delete an event
    """
    try:
        user = request.user
        
        # Get doctor ID
        doctor_query = "SELECT id FROM doctors WHERE user_id = %s"
        doctor = execute_query(doctor_query, (user['id'],), fetch_one=True)
        
        if not doctor:
            return jsonify({'error': 'User is not a doctor'}), 403
        
        # Delete event (verify ownership)
        delete_query = "DELETE FROM events WHERE id = %s AND doctor_id = %s RETURNING id"
        result = execute_query(delete_query, (event_id, doctor['id']), fetch_one=True)
        
        if not result:
            return jsonify({'error': 'Event not found or unauthorized'}), 404
        
        return jsonify({'message': 'Event deleted successfully'}), 200
        
    except Exception as e:
        print(f"Event deletion error: {e}")
        return jsonify({'error': 'Failed to delete event'}), 500
