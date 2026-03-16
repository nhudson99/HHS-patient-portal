"""
Feature request routes
Allows doctors to submit product feedback directly to GitHub as issues.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from api.middleware.auth import authenticate

feature_requests_bp = Blueprint('feature_requests', __name__, url_prefix='/api/feature-requests')


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

        data = request.get_json() or {}
        description = (data.get('description') or '').strip()
        page = (data.get('page') or '').strip()
        route_name = (data.get('route_name') or '').strip()
        custom_title = (data.get('title') or '').strip()

        if len(description) < 10:
            return jsonify({'error': 'Description must be at least 10 characters'}), 400

        if not page:
            return jsonify({'error': 'Page context is required'}), 400

        github_token = os.getenv('GITHUB_TOKEN')
        github_repo = os.getenv('GITHUB_REPO', 'nhudson99/HHS-patient-portal')

        if not github_token:
            return jsonify({
                'error': 'GitHub integration not configured',
                'details': 'Set GITHUB_TOKEN in backend environment'
            }), 503

        short_summary = description.replace('\n', ' ').strip()
        if len(short_summary) > 90:
            short_summary = short_summary[:87] + '...'

        title = custom_title or f"FEATURE REQUEST: {short_summary}"

        body = f"""
## Feature Request

{description}

---
### Submitted From
| Field | Value |
|---|---|
| Doctor | `{user.get('username')}` (ID: `{user.get('id')}`) |
| Page | `{page}` |
| Route | `{route_name or 'unknown'}` |
| Submitted (UTC) | `{datetime.utcnow().isoformat()}Z` |
""".strip()

        labels_env = os.getenv('GITHUB_FEATURE_REQUEST_LABELS', '')
        labels = [label.strip() for label in labels_env.split(',') if label.strip()]

        payload = {
            'title': title,
            'body': body,
        }
        if labels:
            payload['labels'] = labels

        try:
            issue = _post_github_issue(github_repo, github_token, payload)
        except HTTPError as http_error:
            response_body = http_error.read().decode('utf-8') if http_error.fp else ''
            if http_error.code == 422 and labels:
                payload.pop('labels', None)
                issue = _post_github_issue(github_repo, github_token, payload)
            else:
                return jsonify({
                    'error': 'GitHub API request failed',
                    'status': http_error.code,
                    'details': response_body or str(http_error)
                }), 502
        except URLError as url_error:
            return jsonify({'error': 'Unable to reach GitHub API', 'details': str(url_error)}), 502

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
