"""
In-app messaging routes (Slack-like DMs, channels, and threads).
HIPAA: participant-scoped access with audit logging on PHI message reads/writes.
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timezone
import re

from api.middleware.auth import authenticate
from api.db.connection import execute_query, DatabaseTransaction
from api.utils.audit_log import log_data_access

messages_bp = Blueprint('messages', __name__, url_prefix='/api/conversations')

MAX_MESSAGE_LENGTH = 4000
MAX_CHANNEL_TITLE_LENGTH = 80
DEFAULT_MESSAGE_LIMIT = 50
MAX_MESSAGE_LIMIT = 100
INSUFFICIENT_PERMISSIONS_ERROR = 'Insufficient permissions'
CONVERSATION_NOT_FOUND_ERROR = 'Conversation not found'
MESSAGE_NOT_FOUND_ERROR = 'Message not found'


def _iso(value):
    if value is None:
        return None
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value)


def _sanitize_message_body(body: str) -> str:
    """Keep readable punctuation while stripping HTML-ish tags and control chars."""
    if body is None:
        return ''
    cleaned = re.sub(r'<[^>]*>', '', str(body))
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', cleaned)
    return cleaned.strip()


def _sanitize_title(title: str) -> str:
    if title is None:
        return ''
    cleaned = re.sub(r'<[^>]*>', '', str(title))
    cleaned = re.sub(r'[\x00-\x1f]', '', cleaned)
    return cleaned.strip()


def _display_name_for_user(user_id):
    doctor = execute_query(
        """
        SELECT first_name, last_name, specialty
        FROM doctors
        WHERE user_id = %s
        """,
        (user_id,),
        fetch_one=True,
    )
    if doctor:
        return {
            'display_name': f"Dr. {doctor['first_name']} {doctor['last_name']}",
            'role': 'doctor',
            'specialty': doctor['specialty'],
        }

    patient = execute_query(
        """
        SELECT first_name, last_name
        FROM patients
        WHERE user_id = %s
        """,
        (user_id,),
        fetch_one=True,
    )
    if patient:
        return {
            'display_name': f"{patient['first_name']} {patient['last_name']}",
            'role': 'patient',
            'specialty': None,
        }

    user = execute_query(
        "SELECT username, role FROM users WHERE id = %s",
        (user_id,),
        fetch_one=True,
    )
    if user:
        return {
            'display_name': user['username'],
            'role': user['role'],
            'specialty': None,
        }
    return {'display_name': 'Unknown', 'role': None, 'specialty': None}


def _is_participant(conversation_id, user_id):
    row = execute_query(
        """
        SELECT 1
        FROM conversation_participants
        WHERE conversation_id = %s AND user_id = %s
        """,
        (conversation_id, user_id),
        fetch_one=True,
    )
    return row is not None


def _get_conversation(conversation_id):
    return execute_query(
        """
        SELECT id, type, title, created_by_user_id, created_at, updated_at
        FROM conversations
        WHERE id = %s
        """,
        (conversation_id,),
        fetch_one=True,
    )


def _serialize_participant(row):
    info = _display_name_for_user(row['user_id'])
    return {
        'user_id': str(row['user_id']),
        'display_name': info['display_name'],
        'role': info['role'],
        'specialty': info.get('specialty'),
        'last_read_at': _iso(row.get('last_read_at')),
        'joined_at': _iso(row.get('joined_at')),
    }


def _conversation_display_title(conversation, current_user_id, participants):
    if conversation['type'] == 'channel':
        return conversation.get('title') or 'Channel'
    others = [p for p in participants if p['user_id'] != str(current_user_id)]
    if others:
        return others[0]['display_name']
    return 'Direct message'


def _serialize_message(row):
    sender = _display_name_for_user(row['sender_user_id'])
    body = row['body']
    if row.get('deleted_at'):
        body = '[Message deleted]'
    return {
        'id': str(row['id']),
        'conversation_id': str(row['conversation_id']),
        'sender_user_id': str(row['sender_user_id']),
        'sender_name': sender['display_name'],
        'sender_role': sender['role'],
        'parent_message_id': str(row['parent_message_id']) if row.get('parent_message_id') else None,
        'body': body,
        'created_at': _iso(row['created_at']),
        'edited_at': _iso(row.get('edited_at')),
        'deleted_at': _iso(row.get('deleted_at')),
        'reply_count': int(row.get('reply_count') or 0),
    }


def _find_existing_dm(user_a, user_b):
    return execute_query(
        """
        SELECT c.id
        FROM conversations c
        WHERE c.type = 'dm'
          AND EXISTS (
              SELECT 1 FROM conversation_participants cp
              WHERE cp.conversation_id = c.id AND cp.user_id = %s
          )
          AND EXISTS (
              SELECT 1 FROM conversation_participants cp
              WHERE cp.conversation_id = c.id AND cp.user_id = %s
          )
          AND (
              SELECT COUNT(*) FROM conversation_participants cp
              WHERE cp.conversation_id = c.id
          ) = 2
        LIMIT 1
        """,
        (user_a, user_b),
        fetch_one=True,
    )


def _can_message_user(actor, target_user_id):
    """Patients and doctors may only message the opposite portal role."""
    if str(actor['id']) == str(target_user_id):
        return False

    target = execute_query(
        """
        SELECT id, role, is_active
        FROM users
        WHERE id = %s
        """,
        (target_user_id,),
        fetch_one=True,
    )
    if not target or not target.get('is_active'):
        return False

    actor_role = actor.get('role')
    target_role = target.get('role')

    if actor_role == 'doctor' and target_role in ('patient', 'doctor'):
        return True
    if actor_role == 'patient' and target_role == 'doctor':
        return True
    return False


def _patient_user_ids(user_ids):
    """Return the subset of user_ids that belong to active patient accounts."""
    ids = [str(uid) for uid in user_ids if uid]
    if not ids:
        return set()
    placeholders = ','.join(['%s'] * len(ids))
    rows = execute_query(
        f"""
        SELECT id
        FROM users
        WHERE role = 'patient'
          AND id IN ({placeholders})
        """,
        tuple(ids),
        fetch_all=True,
    ) or []
    return {str(row['id']) for row in rows}


def _channel_patient_ids(conversation_id):
    """Return patient user IDs already participating in a channel."""
    rows = execute_query(
        """
        SELECT u.id
        FROM conversation_participants cp
        JOIN users u ON u.id = cp.user_id
        WHERE cp.conversation_id = %s
          AND u.role = 'patient'
        """,
        (conversation_id,),
        fetch_all=True,
    ) or []
    return {str(row['id']) for row in rows}


def _list_participants(conversation_id):
    rows = execute_query(
        """
        SELECT conversation_id, user_id, last_read_at, joined_at
        FROM conversation_participants
        WHERE conversation_id = %s
        ORDER BY joined_at ASC
        """,
        (conversation_id,),
        fetch_all=True,
    ) or []
    return [_serialize_participant(row) for row in rows]


def _unread_count_for_user(user_id, conversation_id=None):
    params = [user_id]
    conversation_filter = ''
    if conversation_id:
        conversation_filter = 'AND cp.conversation_id = %s'
        params.append(conversation_id)

    row = execute_query(
        f"""
        SELECT COUNT(*) AS count
        FROM messages m
        JOIN conversation_participants cp
          ON cp.conversation_id = m.conversation_id
         AND cp.user_id = %s
        WHERE m.deleted_at IS NULL
          AND m.sender_user_id <> cp.user_id
          AND (cp.last_read_at IS NULL OR m.created_at > cp.last_read_at)
          {conversation_filter}
        """,
        tuple(params),
        fetch_one=True,
    )
    return int(row['count']) if row else 0


@messages_bp.route('/contacts', methods=['GET'])
@authenticate
def list_contacts():
    """List users the current user can start a conversation with."""
    try:
        user = request.user
        role = user.get('role')
        if role not in ('doctor', 'patient'):
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403

        if role == 'doctor':
            rows = execute_query(
                """
                SELECT u.id AS user_id, u.role,
                       COALESCE(d.first_name, p.first_name) AS first_name,
                       COALESCE(d.last_name, p.last_name) AS last_name,
                       d.specialty
                FROM users u
                LEFT JOIN doctors d ON d.user_id = u.id
                LEFT JOIN patients p ON p.user_id = u.id
                WHERE u.is_active = TRUE
                  AND u.id <> %s
                  AND u.role IN ('doctor', 'patient')
                  AND (d.user_id IS NOT NULL OR p.user_id IS NOT NULL)
                ORDER BY u.role DESC, last_name ASC, first_name ASC
                """,
                (user['id'],),
                fetch_all=True,
            ) or []
        else:
            rows = execute_query(
                """
                SELECT u.id AS user_id, u.role,
                       d.first_name, d.last_name, d.specialty
                FROM users u
                JOIN doctors d ON d.user_id = u.id
                WHERE u.is_active = TRUE
                  AND u.role = 'doctor'
                ORDER BY d.last_name ASC, d.first_name ASC
                """,
                fetch_all=True,
            ) or []

        contacts = []
        for row in rows:
            if row['role'] == 'doctor':
                display_name = f"Dr. {row['first_name']} {row['last_name']}"
            else:
                display_name = f"{row['first_name']} {row['last_name']}"
            contacts.append({
                'user_id': str(row['user_id']),
                'display_name': display_name,
                'role': row['role'],
                'specialty': row.get('specialty'),
            })

        return jsonify({'contacts': contacts}), 200
    except Exception:
        current_app.logger.exception('Failed to list messaging contacts')
        return jsonify({'error': 'Failed to list contacts'}), 500


@messages_bp.route('/unread-count', methods=['GET'])
@authenticate
def unread_count():
    try:
        user = request.user
        if user.get('role') not in ('doctor', 'patient'):
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403
        return jsonify({'unread_count': _unread_count_for_user(user['id'])}), 200
    except Exception:
        current_app.logger.exception('Failed to get unread message count')
        return jsonify({'error': 'Failed to get unread count'}), 500


@messages_bp.route('', methods=['GET'])
@authenticate
def list_conversations():
    """List conversations for the current user with preview + unread counts."""
    try:
        user = request.user
        if user.get('role') not in ('doctor', 'patient'):
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403

        rows = execute_query(
            """
            SELECT c.id, c.type, c.title, c.created_by_user_id, c.created_at, c.updated_at,
                   cp.last_read_at,
                   (
                       SELECT m.body
                       FROM messages m
                       WHERE m.conversation_id = c.id AND m.deleted_at IS NULL
                       ORDER BY m.created_at DESC
                       LIMIT 1
                   ) AS last_message_body,
                   (
                       SELECT m.id
                       FROM messages m
                       WHERE m.conversation_id = c.id AND m.deleted_at IS NULL
                       ORDER BY m.created_at DESC
                       LIMIT 1
                   ) AS last_message_id,
                   (
                       SELECT m.parent_message_id
                       FROM messages m
                       WHERE m.conversation_id = c.id AND m.deleted_at IS NULL
                       ORDER BY m.created_at DESC
                       LIMIT 1
                   ) AS last_message_parent_id,
                   (
                       SELECT m.created_at
                       FROM messages m
                       WHERE m.conversation_id = c.id AND m.deleted_at IS NULL
                       ORDER BY m.created_at DESC
                       LIMIT 1
                   ) AS last_message_at,
                   (
                       SELECT m.sender_user_id
                       FROM messages m
                       WHERE m.conversation_id = c.id AND m.deleted_at IS NULL
                       ORDER BY m.created_at DESC
                       LIMIT 1
                   ) AS last_message_sender_id
            FROM conversations c
            JOIN conversation_participants cp
              ON cp.conversation_id = c.id AND cp.user_id = %s
            ORDER BY COALESCE(
                (
                    SELECT m.created_at
                    FROM messages m
                    WHERE m.conversation_id = c.id AND m.deleted_at IS NULL
                    ORDER BY m.created_at DESC
                    LIMIT 1
                ),
                c.updated_at
            ) DESC
            """,
            (user['id'],),
            fetch_all=True,
        ) or []

        conversations = []
        for row in rows:
            participants = _list_participants(row['id'])
            unread = _unread_count_for_user(user['id'], row['id'])
            last_sender_name = None
            if row.get('last_message_sender_id'):
                last_sender_name = _display_name_for_user(row['last_message_sender_id'])['display_name']

            conversations.append({
                'id': str(row['id']),
                'type': row['type'],
                'title': _conversation_display_title(row, user['id'], participants),
                'created_by_user_id': str(row['created_by_user_id']) if row.get('created_by_user_id') else None,
                'created_at': _iso(row['created_at']),
                'updated_at': _iso(row['updated_at']),
                'participants': participants,
                'unread_count': unread,
                'last_message': {
                    'id': str(row['last_message_id']) if row.get('last_message_id') else None,
                    'body': row.get('last_message_body'),
                    'created_at': _iso(row.get('last_message_at')),
                    'sender_name': last_sender_name,
                    'parent_message_id': (
                        str(row['last_message_parent_id'])
                        if row.get('last_message_parent_id')
                        else None
                    ),
                } if row.get('last_message_body') else None,
            })

        log_data_access(user['id'], 'conversations', 'list', 'VIEW', request)
        return jsonify({'conversations': conversations}), 200
    except Exception:
        current_app.logger.exception('Failed to list conversations')
        return jsonify({'error': 'Failed to list conversations'}), 500


@messages_bp.route('', methods=['POST'])
@authenticate
def create_conversation():
    """
    Create a DM or channel.

    DM body: { "type": "dm", "participant_user_id": "<uuid>" }
    Channel body: { "type": "channel", "title": "...", "participant_user_ids": ["..."] }
    """
    try:
        user = request.user
        if user.get('role') not in ('doctor', 'patient'):
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403

        data = request.get_json(silent=True) or {}
        conv_type = (data.get('type') or '').strip().lower()

        if conv_type == 'dm':
            participant_user_id = data.get('participant_user_id')
            if not participant_user_id:
                return jsonify({'error': 'participant_user_id is required for DMs'}), 400
            if not _can_message_user(user, participant_user_id):
                return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403

            existing = _find_existing_dm(user['id'], participant_user_id)
            if existing:
                conversation = _get_conversation(existing['id'])
                participants = _list_participants(existing['id'])
                return jsonify({
                    'conversation': {
                        'id': str(conversation['id']),
                        'type': conversation['type'],
                        'title': _conversation_display_title(conversation, user['id'], participants),
                        'created_by_user_id': str(conversation['created_by_user_id']) if conversation.get('created_by_user_id') else None,
                        'created_at': _iso(conversation['created_at']),
                        'updated_at': _iso(conversation['updated_at']),
                        'participants': participants,
                        'unread_count': _unread_count_for_user(user['id'], conversation['id']),
                        'last_message': None,
                    },
                    'created': False,
                }), 200

            with DatabaseTransaction() as cursor:
                cursor.execute(
                    """
                    INSERT INTO conversations (type, title, created_by_user_id)
                    VALUES ('dm', NULL, %s)
                    RETURNING id, type, title, created_by_user_id, created_at, updated_at
                    """,
                    (user['id'],),
                )
                conversation = cursor.fetchone()
                for participant_id in {str(user['id']), str(participant_user_id)}:
                    cursor.execute(
                        """
                        INSERT INTO conversation_participants (conversation_id, user_id, last_read_at)
                        VALUES (%s, %s, NOW())
                        """,
                        (conversation['id'], participant_id),
                    )

            participants = _list_participants(conversation['id'])
            log_data_access(user['id'], 'conversations', str(conversation['id']), 'CREATE', request)
            return jsonify({
                'conversation': {
                    'id': str(conversation['id']),
                    'type': conversation['type'],
                    'title': _conversation_display_title(conversation, user['id'], participants),
                    'created_by_user_id': str(conversation['created_by_user_id']),
                    'created_at': _iso(conversation['created_at']),
                    'updated_at': _iso(conversation['updated_at']),
                    'participants': participants,
                    'unread_count': 0,
                    'last_message': None,
                },
                'created': True,
            }), 201

        if conv_type == 'channel':
            if user.get('role') != 'doctor':
                return jsonify({'error': 'Only providers can create channels'}), 403

            title = _sanitize_title(data.get('title') or '')
            if not title:
                return jsonify({'error': 'Channel title is required'}), 400
            if len(title) > MAX_CHANNEL_TITLE_LENGTH:
                return jsonify({'error': f'Channel title must be {MAX_CHANNEL_TITLE_LENGTH} characters or fewer'}), 400

            participant_ids = data.get('participant_user_ids') or []
            if not isinstance(participant_ids, list):
                return jsonify({'error': 'participant_user_ids must be a list'}), 400

            resolved_ids = {str(user['id'])}
            for raw_id in participant_ids:
                if not _can_message_user(user, raw_id) and str(raw_id) != str(user['id']):
                    return jsonify({'error': f'Cannot add participant {raw_id}'}), 403
                resolved_ids.add(str(raw_id))

            # HIPAA: at most one patient per channel so patients cannot see each other.
            if len(_patient_user_ids(resolved_ids)) > 1:
                return jsonify({
                    'error': 'Channels may include at most one patient',
                }), 400

            with DatabaseTransaction() as cursor:
                cursor.execute(
                    """
                    INSERT INTO conversations (type, title, created_by_user_id)
                    VALUES ('channel', %s, %s)
                    RETURNING id, type, title, created_by_user_id, created_at, updated_at
                    """,
                    (title, user['id']),
                )
                conversation = cursor.fetchone()
                for participant_id in resolved_ids:
                    cursor.execute(
                        """
                        INSERT INTO conversation_participants (conversation_id, user_id, last_read_at)
                        VALUES (%s, %s, NOW())
                        """,
                        (conversation['id'], participant_id),
                    )

            participants = _list_participants(conversation['id'])
            log_data_access(user['id'], 'conversations', str(conversation['id']), 'CREATE', request)
            return jsonify({
                'conversation': {
                    'id': str(conversation['id']),
                    'type': conversation['type'],
                    'title': conversation['title'],
                    'created_by_user_id': str(conversation['created_by_user_id']),
                    'created_at': _iso(conversation['created_at']),
                    'updated_at': _iso(conversation['updated_at']),
                    'participants': participants,
                    'unread_count': 0,
                    'last_message': None,
                },
                'created': True,
            }), 201

        return jsonify({'error': 'type must be "dm" or "channel"'}), 400
    except Exception:
        current_app.logger.exception('Failed to create conversation')
        return jsonify({'error': 'Failed to create conversation'}), 500


@messages_bp.route('/<conversation_id>', methods=['GET'])
@authenticate
def get_conversation(conversation_id):
    try:
        user = request.user
        if user.get('role') not in ('doctor', 'patient'):
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403
        if not _is_participant(conversation_id, user['id']):
            return jsonify({'error': CONVERSATION_NOT_FOUND_ERROR}), 404

        conversation = _get_conversation(conversation_id)
        if not conversation:
            return jsonify({'error': CONVERSATION_NOT_FOUND_ERROR}), 404

        participants = _list_participants(conversation_id)
        log_data_access(user['id'], 'conversations', conversation_id, 'VIEW', request)
        return jsonify({
            'conversation': {
                'id': str(conversation['id']),
                'type': conversation['type'],
                'title': _conversation_display_title(conversation, user['id'], participants),
                'created_by_user_id': str(conversation['created_by_user_id']) if conversation.get('created_by_user_id') else None,
                'created_at': _iso(conversation['created_at']),
                'updated_at': _iso(conversation['updated_at']),
                'participants': participants,
                'unread_count': _unread_count_for_user(user['id'], conversation_id),
            }
        }), 200
    except Exception:
        current_app.logger.exception('Failed to get conversation')
        return jsonify({'error': 'Failed to get conversation'}), 500


@messages_bp.route('/<conversation_id>/messages', methods=['GET'])
@authenticate
def list_messages(conversation_id):
    try:
        user = request.user
        if user.get('role') not in ('doctor', 'patient'):
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403
        if not _is_participant(conversation_id, user['id']):
            return jsonify({'error': CONVERSATION_NOT_FOUND_ERROR}), 404

        try:
            limit = min(int(request.args.get('limit', DEFAULT_MESSAGE_LIMIT)), MAX_MESSAGE_LIMIT)
        except (TypeError, ValueError):
            limit = DEFAULT_MESSAGE_LIMIT

        before = request.args.get('before')
        since_raw = request.args.get('since')
        parent_message_id = request.args.get('parent_message_id')
        top_level_only = request.args.get('top_level_only', 'true').lower() != 'false'

        since = None
        if since_raw:
            # Unencoded '+' in ISO offsets becomes a space in query strings.
            normalized = str(since_raw).strip()
            if normalized.endswith(('Z', 'z')):
                normalized = f'{normalized[:-1]}+00:00'
            normalized = re.sub(
                r'(\d{2}:\d{2}:\d{2}(?:\.\d+)?) (\d{2}:\d{2})$',
                r'\1+\2',
                normalized,
            )
            try:
                since = datetime.fromisoformat(normalized)
            except (TypeError, ValueError, AttributeError):
                return jsonify({'error': 'Invalid since timestamp'}), 400

        params = [conversation_id]
        filters = ['m.conversation_id = %s']

        if parent_message_id:
            filters.append('m.parent_message_id = %s')
            params.append(parent_message_id)
            top_level_only = False
        elif top_level_only:
            filters.append('m.parent_message_id IS NULL')

        if before:
            filters.append('m.created_at < %s')
            params.append(before)

        if since is not None:
            filters.append('m.created_at > %s')
            params.append(since)

        params.append(limit)
        # Incremental polls (`since`) return ascending rows ready to append;
        # page loads use DESC + reverse for the latest window.
        order_dir = 'ASC' if since is not None else 'DESC'
        rows = execute_query(
            f"""
            SELECT m.id, m.conversation_id, m.sender_user_id, m.parent_message_id,
                   m.body, m.created_at, m.edited_at, m.deleted_at,
                   (
                       SELECT COUNT(*)
                       FROM messages replies
                       WHERE replies.parent_message_id = m.id
                         AND replies.deleted_at IS NULL
                   ) AS reply_count
            FROM messages m
            WHERE {' AND '.join(filters)}
            ORDER BY m.created_at {order_dir}
            LIMIT %s
            """,
            tuple(params),
            fetch_all=True,
        ) or []

        if since is not None:
            messages = [_serialize_message(row) for row in rows]
        else:
            # Return chronological order for the UI
            messages = [_serialize_message(row) for row in reversed(rows)]
        log_data_access(user['id'], 'messages', conversation_id, 'VIEW', request)
        return jsonify({
            'messages': messages,
            'has_more': len(rows) == limit,
        }), 200
    except Exception:
        current_app.logger.exception('Failed to list messages')
        return jsonify({'error': 'Failed to list messages'}), 500


@messages_bp.route('/<conversation_id>/messages', methods=['POST'])
@authenticate
def send_message(conversation_id):
    try:
        user = request.user
        if user.get('role') not in ('doctor', 'patient'):
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403
        if not _is_participant(conversation_id, user['id']):
            return jsonify({'error': CONVERSATION_NOT_FOUND_ERROR}), 404

        data = request.get_json(silent=True) or {}
        body = _sanitize_message_body(data.get('body') or '')
        if not body:
            return jsonify({'error': 'Message body is required'}), 400
        if len(body) > MAX_MESSAGE_LENGTH:
            return jsonify({'error': f'Message must be {MAX_MESSAGE_LENGTH} characters or fewer'}), 400

        parent_message_id = data.get('parent_message_id')
        if parent_message_id:
            parent = execute_query(
                """
                SELECT id, conversation_id, deleted_at
                FROM messages
                WHERE id = %s
                """,
                (parent_message_id,),
                fetch_one=True,
            )
            if not parent or str(parent['conversation_id']) != str(conversation_id):
                return jsonify({'error': MESSAGE_NOT_FOUND_ERROR}), 404
            if parent.get('deleted_at'):
                return jsonify({'error': 'Cannot reply to a deleted message'}), 400

        with DatabaseTransaction() as cursor:
            cursor.execute(
                """
                INSERT INTO messages (conversation_id, sender_user_id, parent_message_id, body)
                VALUES (%s, %s, %s, %s)
                RETURNING id, conversation_id, sender_user_id, parent_message_id,
                          body, created_at, edited_at, deleted_at
                """,
                (conversation_id, user['id'], parent_message_id, body),
            )
            message = cursor.fetchone()
            cursor.execute(
                """
                UPDATE conversations
                SET updated_at = NOW()
                WHERE id = %s
                """,
                (conversation_id,),
            )
            cursor.execute(
                """
                UPDATE conversation_participants
                SET last_read_at = NOW()
                WHERE conversation_id = %s AND user_id = %s
                """,
                (conversation_id, user['id']),
            )

        serialized = _serialize_message({**message, 'reply_count': 0})
        log_data_access(user['id'], 'messages', str(message['id']), 'CREATE', request)
        return jsonify({'message': serialized}), 201
    except Exception:
        current_app.logger.exception('Failed to send message')
        return jsonify({'error': 'Failed to send message'}), 500


@messages_bp.route('/<conversation_id>/read', methods=['PATCH'])
@authenticate
def mark_conversation_read(conversation_id):
    try:
        user = request.user
        if user.get('role') not in ('doctor', 'patient'):
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403
        if not _is_participant(conversation_id, user['id']):
            return jsonify({'error': CONVERSATION_NOT_FOUND_ERROR}), 404

        execute_query(
            """
            UPDATE conversation_participants
            SET last_read_at = NOW()
            WHERE conversation_id = %s AND user_id = %s
            """,
            (conversation_id, user['id']),
        )
        return jsonify({
            'message': 'Conversation marked as read',
            'unread_count': 0,
            'read_at': datetime.now(timezone.utc).isoformat(),
        }), 200
    except Exception:
        current_app.logger.exception('Failed to mark conversation read')
        return jsonify({'error': 'Failed to mark conversation as read'}), 500


@messages_bp.route('/<conversation_id>/participants', methods=['POST'])
@authenticate
def add_participants(conversation_id):
    """Add participants to a channel (providers only)."""
    try:
        user = request.user
        if user.get('role') != 'doctor':
            return jsonify({'error': 'Only providers can add channel participants'}), 403
        if not _is_participant(conversation_id, user['id']):
            return jsonify({'error': CONVERSATION_NOT_FOUND_ERROR}), 404

        conversation = _get_conversation(conversation_id)
        if not conversation:
            return jsonify({'error': CONVERSATION_NOT_FOUND_ERROR}), 404
        if conversation['type'] != 'channel':
            return jsonify({'error': 'Participants can only be added to channels'}), 400

        data = request.get_json(silent=True) or {}
        participant_ids = data.get('participant_user_ids') or []
        if not isinstance(participant_ids, list) or not participant_ids:
            return jsonify({'error': 'participant_user_ids is required'}), 400

        # HIPAA: reject adding a second patient to a channel that already has one.
        existing_patients = _channel_patient_ids(conversation_id)
        new_patients = _patient_user_ids(participant_ids)
        if len(existing_patients | new_patients) > 1:
            return jsonify({
                'error': 'Channels may include at most one patient',
            }), 400

        added = []
        with DatabaseTransaction() as cursor:
            for raw_id in participant_ids:
                if not _can_message_user(user, raw_id):
                    return jsonify({'error': f'Cannot add participant {raw_id}'}), 403
                cursor.execute(
                    """
                    INSERT INTO conversation_participants (conversation_id, user_id, last_read_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (conversation_id, user_id) DO NOTHING
                    RETURNING user_id
                    """,
                    (conversation_id, raw_id),
                )
                row = cursor.fetchone()
                if row:
                    added.append(str(row['user_id']))
            cursor.execute(
                "UPDATE conversations SET updated_at = NOW() WHERE id = %s",
                (conversation_id,),
            )

        log_data_access(user['id'], 'conversations', conversation_id, 'UPDATE', request)
        return jsonify({
            'message': 'Participants added',
            'added_user_ids': added,
            'participants': _list_participants(conversation_id),
        }), 200
    except Exception:
        current_app.logger.exception('Failed to add participants')
        return jsonify({'error': 'Failed to add participants'}), 500
