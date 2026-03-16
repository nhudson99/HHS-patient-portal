"""
Admin SSO route — Microsoft Entra ID (Azure AD) token verification
-----------------------------------------------------------------
POST /api/admin/verify-token
  Body: { "idToken": "<Microsoft ID token JWT>" }

Steps:
  1. Fetch Microsoft's JWKS for the tenant configured in AZURE_TENANT_ID
  2. Validate the JWT signature, expiry, audience, and issuer
  3. Enforce the @hudsonitconsulting.com domain requirement
  4. Return { email, name } on success

Required env vars:
  AZURE_TENANT_ID  – Azure Active Directory tenant ID
  AZURE_CLIENT_ID  – App (client) ID registered in Azure Portal
"""

from flask import Blueprint, request, jsonify
from urllib.request import urlopen
from urllib.error import URLError
import json
import os
import logging

import jwt
from jwt import PyJWKClient, PyJWKClientError

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

ALLOWED_DOMAIN = 'hudsonitconsulting.com'
_TENANT_ID = os.getenv('AZURE_TENANT_ID', '')
_CLIENT_ID = os.getenv('AZURE_CLIENT_ID', '')


def _get_valid_issuers(tenant_id: str) -> set[str]:
    """Return trusted Microsoft issuer formats for a tenant."""
    return {
        f'https://login.microsoftonline.com/{tenant_id}/v2.0',
        f'https://login.microsoftonline.com/{tenant_id}/v2.0/',
        f'https://login.microsoftonline.com/{tenant_id}/',
        f'https://sts.windows.net/{tenant_id}/',
    }


def _get_jwks_uri() -> str:
    """Fetch the JWKS URI from Microsoft's OpenID Connect discovery document."""
    if not _TENANT_ID:
        raise ValueError('AZURE_TENANT_ID is not configured')

    discovery_url = (
        f'https://login.microsoftonline.com/{_TENANT_ID}/v2.0'
        '/.well-known/openid-configuration'
    )
    try:
        with urlopen(discovery_url, timeout=5) as resp:
            config = json.loads(resp.read())
        return config['jwks_uri']
    except (URLError, KeyError) as exc:
        raise RuntimeError(f'Failed to fetch OIDC discovery document: {exc}') from exc


@admin_bp.route('/verify-token', methods=['POST'])
def verify_token():
    """
    POST /api/admin/verify-token
    Validate a Microsoft-issued ID token and enforce domain restriction.
    """
    data = request.get_json(silent=True)
    if not data or 'idToken' not in data:
        return jsonify({'error': 'idToken is required'}), 400

    id_token: str = data['idToken']

    # ── Env-var guard ─────────────────────────────────────────────────────────
    if not _TENANT_ID or not _CLIENT_ID:
        logger.error('AZURE_TENANT_ID or AZURE_CLIENT_ID is not configured')
        return jsonify({'error': 'Admin SSO is not configured on this server'}), 503

    try:
        # ── Fetch JWKS and decode/verify the token ────────────────────────────
        jwks_uri = _get_jwks_uri()
        jwks_client = PyJWKClient(jwks_uri)
        signing_key = jwks_client.get_signing_key_from_jwt(id_token)

        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=['RS256'],
            audience=_CLIENT_ID,
            options={
                'verify_exp': True,
                'verify_iss': False,
            }
        )

        issuer = str(claims.get('iss', ''))
        valid_issuers = _get_valid_issuers(_TENANT_ID)
        if issuer not in valid_issuers:
            raise jwt.InvalidIssuerError(f'Unexpected issuer: {issuer}')

        token_tenant_id = str(claims.get('tid', ''))
        if token_tenant_id and token_tenant_id != _TENANT_ID:
            raise jwt.InvalidIssuerError(
                f'Tenant mismatch: expected {_TENANT_ID}, got {token_tenant_id}'
            )

    except PyJWKClientError as exc:
        logger.warning('JWKS lookup failed: %s', exc)
        return jsonify({'error': 'Token validation failed (JWKS)'}), 401
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token has expired'}), 401
    except jwt.InvalidIssuerError:
        return jsonify({'error': 'Token issuer is not trusted'}), 401
    except jwt.InvalidAudienceError:
        return jsonify({'error': 'Token audience mismatch'}), 401
    except jwt.PyJWTError as exc:
        logger.warning('JWT decode error: %s', exc)
        return jsonify({'error': 'Invalid token'}), 401
    except (RuntimeError, ValueError) as exc:
        logger.error('Admin SSO config error: %s', exc)
        return jsonify({'error': str(exc)}), 503

    # ── Domain enforcement ────────────────────────────────────────────────────
    # 'preferred_username' / 'email' / 'upn' all hold the UPN in Microsoft tokens
    email: str = (
        claims.get('preferred_username') or
        claims.get('email') or
        claims.get('upn') or
        ''
    ).lower()

    if not email.endswith(f'@{ALLOWED_DOMAIN}'):
        logger.warning(
            'Admin SSO domain rejected: %s (allowed: %s)', email, ALLOWED_DOMAIN
        )
        return jsonify({
            'error': f'Access denied. Only @{ALLOWED_DOMAIN} accounts are permitted.'
        }), 403

    name: str = claims.get('name') or email

    logger.info('Admin SSO success: %s', email)

    return jsonify({
        'email': email,
        'name': name,
        'tid': claims.get('tid', '')
    }), 200
