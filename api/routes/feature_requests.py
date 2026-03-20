"""
Feature request routes
Allows doctors to submit product feedback directly to GitHub as issues.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from api.middleware.auth import authenticate

feature_requests_bp = Blueprint('feature_requests', __name__, url_prefix='/api/feature-requests')
MIN_DESCRIPTION_LENGTH = 10
MAX_TITLE_SUMMARY_LENGTH = 90
DEFAULT_GITHUB_REPO = 'nhudson99/HHS-patient-portal'


def _post_github_issue(owner_repo: str, token: str, payload: dict):
    """Create GitHub issue via REST API."""
    url = f"https://api.github.com/repos/{owner_repo}/issues"
    req = Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        method='POST',
        headers={
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'Content-Type': 'application/json',
            'User-Agent': 'hhs-patient-portal-feature-request'
        }
    )

    with urlopen(req, timeout=15) as response:
        data = response.read().decode('utf-8')
        return json.loads(data)


def _extract_feature_request_fields(payload: dict) -> tuple[str, str, str, str]:
    description = (payload.get('description') or '').strip()
    page = (payload.get('page') or '').strip()
    route_name = (payload.get('route_name') or '').strip()
    custom_title = (payload.get('title') or '').strip()
    return description, page, route_name, custom_title


def _build_issue_title(description: str, custom_title: str) -> str:
    if custom_title:
        return custom_title

    short_summary = description.replace('\n', ' ').strip()
    if len(short_summary) > MAX_TITLE_SUMMARY_LENGTH:
        short_summary = f"{short_summary[:MAX_TITLE_SUMMARY_LENGTH - 3]}..."
    return f"FEATURE REQUEST: {short_summary}"


def _build_issue_body(description: str, user: dict, page: str, route_name: str) -> str:
    return f"""
## Feature Request

{description}

---
### Submitted From
| Field | Value |
|---|---|
| Doctor | `{user.get('username')}` (ID: `{user.get('id')}`) |
| Page | `{page}` |
| Route | `{route_name or 'unknown'}` |
| Submitted (UTC) | `{datetime.now(timezone.utc).isoformat()}` |
""".strip()


def _build_issue_payload(title: str, body: str) -> dict:
    payload: dict[str, object] = {
        'title': title,
        'body': body,
    }
    labels_env = os.getenv('GITHUB_FEATURE_REQUEST_LABELS', '')
    labels = [label.strip() for label in labels_env.split(',') if label.strip()]
    if labels:
        payload['labels'] = labels
    return payload


def _create_issue_with_label_fallback(github_repo: str, github_token: str, payload: dict) -> dict:
    try:
        return _post_github_issue(github_repo, github_token, payload)
    except HTTPError as http_error:
        response_body = http_error.read().decode('utf-8') if http_error.fp else ''
        has_labels = bool(payload.get('labels'))
        if http_error.code == 422 and has_labels:
            payload_without_labels = dict(payload)
            payload_without_labels.pop('labels', None)
            return _post_github_issue(github_repo, github_token, payload_without_labels)
        raise RuntimeError(json.dumps({
            'status': http_error.code,
            'details': response_body or str(http_error)
        })) from http_error


@feature_requests_bp.route('', methods=['POST'])
@authenticate
def create_feature_request():
    """
    POST /api/feature-requests
    Create a GitHub issue from doctor-side feedback.

    Required JSON body:
      - description: str
      - page: str
    Optional:
      - title: str
      - route_name: str
    """
    try:
        user = request.user
        if user.get('role') != 'doctor':
            return jsonify({'error': 'Only doctors can submit feature requests'}), 403

        data = request.get_json(silent=True) or {}
        description, page, route_name, custom_title = _extract_feature_request_fields(data)

        if len(description) < MIN_DESCRIPTION_LENGTH:
            return jsonify({'error': f'Description must be at least {MIN_DESCRIPTION_LENGTH} characters'}), 400

        if not page:
            return jsonify({'error': 'Page context is required'}), 400

        github_token = os.getenv('GITHUB_TOKEN')
        github_repo = os.getenv('GITHUB_REPO', DEFAULT_GITHUB_REPO)

        if not github_token:
            return jsonify({
                'error': 'GitHub integration not configured',
                'details': 'Set GITHUB_TOKEN in backend environment'
            }), 503

        title = _build_issue_title(description, custom_title)
        body = _build_issue_body(description, user, page, route_name)
        payload = _build_issue_payload(title, body)

        try:
            issue = _create_issue_with_label_fallback(github_repo, github_token, payload)
        except URLError as url_error:
            return jsonify({'error': 'Unable to reach GitHub API', 'details': str(url_error)}), 502
        except RuntimeError as runtime_error:
            details = json.loads(str(runtime_error))
            return jsonify({
                'error': 'GitHub API request failed',
                'status': details.get('status'),
                'details': details.get('details')
            }), 502

        return jsonify({
            'message': 'Feature request submitted successfully',
            'issue': {
                'id': issue.get('id'),
                'number': issue.get('number'),
                'url': issue.get('html_url'),
                'title': issue.get('title')
            }
        }), 201

    except Exception as e:
        return jsonify({'error': 'Failed to submit feature request', 'details': str(e)}), 500
