import aiohttp
from fastapi import HTTPException, status

QLCODE_API_BASE_URL = 'https://api.qlcodeapi.com/v1'
QLCODE_IMAGE_GENERATION_MODEL = 'gpt-image-2'
QLCODE_IMAGE_GENERATION_SIZE = '1024x1024'


def settings_to_dict(settings) -> dict:
    if settings is None:
        return {}
    if hasattr(settings, 'model_dump'):
        return settings.model_dump()
    if isinstance(settings, dict):
        return dict(settings)
    return {}


def user_settings_to_dict(user) -> dict:
    return settings_to_dict(getattr(user, 'settings', None))


def get_user_qlcode_api_key(user) -> str:
    settings = user_settings_to_dict(user)
    ui_settings = settings.get('ui') if isinstance(settings, dict) else None
    direct_connections = (ui_settings or {}).get('directConnections') or {}
    urls = direct_connections.get('OPENAI_API_BASE_URLS') or []
    keys = direct_connections.get('OPENAI_API_KEYS') or []

    fixed_idx = next(
        (idx for idx, url in enumerate(urls) if isinstance(url, str) and url.rstrip('/') == QLCODE_API_BASE_URL),
        None,
    )
    key = keys[fixed_idx] if fixed_idx is not None and fixed_idx < len(keys) else (keys[0] if keys else '')
    return str(key or '').strip()


def validate_qlcode_api_key(api_key: str, detail: str = 'QLCodeAPI key is required.') -> str:
    api_key = (api_key or '').strip()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )
    return api_key


def get_required_user_qlcode_api_key(user) -> str:
    return validate_qlcode_api_key(
        get_user_qlcode_api_key(user),
        detail='QLCodeAPI key is required. Please configure it in Settings > Connections.',
    )


def qlcode_api_headers(api_key: str, content_type: str | None = 'application/json') -> dict:
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}',
    }
    if content_type:
        headers['Content-Type'] = content_type
    return headers


async def qlcode_error_detail(response: aiohttp.ClientResponse):
    try:
        data = await response.json()
        if isinstance(data, dict):
            error = data.get('error')
            if isinstance(error, dict) and error.get('message'):
                return error['message']
            return data.get('detail') or data
        return data
    except Exception:
        return await response.text()


def normalize_user_direct_connections(settings):
    settings_data = settings_to_dict(settings)
    ui_settings = settings_data.get('ui')
    if not isinstance(ui_settings, dict) or 'directConnections' not in ui_settings:
        return settings_data

    ui_settings = dict(ui_settings)
    direct_connections = ui_settings.get('directConnections') or {}
    urls = direct_connections.get('OPENAI_API_BASE_URLS') or []
    keys = direct_connections.get('OPENAI_API_KEYS') or []

    fixed_idx = next(
        (idx for idx, url in enumerate(urls) if isinstance(url, str) and url.rstrip('/') == QLCODE_API_BASE_URL),
        None,
    )
    key = keys[fixed_idx] if fixed_idx is not None and fixed_idx < len(keys) else (keys[0] if keys else '')

    ui_settings['directConnections'] = {
        'OPENAI_API_BASE_URLS': [QLCODE_API_BASE_URL],
        'OPENAI_API_KEYS': [key],
        'OPENAI_API_CONFIGS': {
            '0': {
                'enable': True,
                'auth_type': 'bearer',
                'connection_type': 'external',
            }
        },
    }
    settings_data['ui'] = ui_settings
    return settings_data
