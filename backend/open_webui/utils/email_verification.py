import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import smtplib
import ssl
import time
from email.message import EmailMessage
from email.utils import formataddr
from typing import Optional

from open_webui.env import REDIS_KEY_PREFIX
from open_webui.utils.redis import get_redis_client

log = logging.getLogger(__name__)

_redis = get_redis_client()
_memory_codes: dict[str, dict] = {}


def is_smtp_configured(config) -> bool:
    try:
        port = int(config.SMTP_PORT or 0)
    except (TypeError, ValueError):
        port = 0

    return bool(str(config.SMTP_HOST or '').strip() and port and str(config.SMTP_FROM_EMAIL or '').strip())


def generate_verification_code() -> str:
    return f'{secrets.randbelow(900000) + 100000}'


def _code_key(email: str, purpose: str) -> str:
    return f'{REDIS_KEY_PREFIX}:email_verification:{purpose}:{email.lower().strip()}'


def _code_digest(email: str, purpose: str, code: str, secret: str) -> str:
    message = f'{purpose}:{email.lower().strip()}:{code.strip()}'.encode('utf-8')
    return hmac.new(secret.encode('utf-8'), message, hashlib.sha256).hexdigest()


def store_verification_code(email: str, purpose: str, code: str, secret: str, ttl_seconds: int) -> None:
    key = _code_key(email, purpose)
    payload = {
        'digest': _code_digest(email, purpose, code, secret),
        'expires_at': int(time.time()) + ttl_seconds,
    }

    if _redis is not None:
        try:
            _redis.setex(key, ttl_seconds, json.dumps(payload))
            return
        except Exception as e:
            log.warning(f'Failed to store email verification code in Redis: {e}')

    _memory_codes[key] = payload


def verify_verification_code(
    email: str,
    purpose: str,
    code: str,
    secret: str,
    *,
    consume: bool = True,
) -> bool:
    key = _code_key(email, purpose)
    payload: Optional[dict] = None

    if _redis is not None:
        try:
            raw = _redis.get(key)
            if raw:
                payload = json.loads(raw)
        except Exception as e:
            log.warning(f'Failed to read email verification code from Redis: {e}')

    if payload is None:
        payload = _memory_codes.get(key)

    if not payload:
        return False

    if int(payload.get('expires_at') or 0) < int(time.time()):
        _delete_verification_code(key)
        return False

    expected = payload.get('digest') or ''
    actual = _code_digest(email, purpose, code, secret)
    valid = hmac.compare_digest(expected, actual)

    if valid and consume:
        _delete_verification_code(key)

    return valid


def _delete_verification_code(key: str) -> None:
    if _redis is not None:
        try:
            _redis.delete(key)
        except Exception as e:
            log.warning(f'Failed to delete email verification code from Redis: {e}')

    _memory_codes.pop(key, None)


def render_verification_email(code: str, ttl_seconds: int) -> tuple[str, str, str]:
    minutes = max(1, ttl_seconds // 60)
    subject = 'QLCodeChat 注册验证码'
    text = f'您的 QLCodeChat 注册验证码是：{code}\n\n验证码 {minutes} 分钟内有效。如非本人操作，请忽略本邮件。'
    html = f"""
    <div style="font-family:Arial,'Microsoft YaHei',sans-serif;color:#111827;line-height:1.7">
      <h2 style="margin:0 0 16px;color:#061155">QLCodeChat 注册验证码</h2>
      <p>您的验证码是：</p>
      <div style="display:inline-block;padding:12px 18px;border-radius:10px;background:#eff6ff;color:#075cf8;font-size:28px;font-weight:800;letter-spacing:6px">
        {code}
      </div>
      <p>验证码 {minutes} 分钟内有效。如非本人操作，请忽略本邮件。</p>
    </div>
    """
    return subject, text, html


async def send_smtp_email_async(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    from_email: str,
    from_name: str,
    use_tls: bool,
    to_email: str,
    subject: str,
    text: str,
    html: Optional[str] = None,
) -> None:
    await asyncio.to_thread(
        send_smtp_email,
        host=host,
        port=port,
        username=username,
        password=password,
        from_email=from_email,
        from_name=from_name,
        use_tls=use_tls,
        to_email=to_email,
        subject=subject,
        text=text,
        html=html,
    )


def send_smtp_email(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    from_email: str,
    from_name: str,
    use_tls: bool,
    to_email: str,
    subject: str,
    text: str,
    html: Optional[str] = None,
) -> None:
    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = formataddr((from_name or from_email, from_email))
    message['To'] = to_email
    message.set_content(text)
    if html:
        message.add_alternative(html, subtype='html')

    context = ssl.create_default_context()
    if use_tls:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as server:
            _smtp_login_if_needed(server, username, password)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=15) as server:
            _smtp_login_if_needed(server, username, password)
            server.send_message(message)


def _smtp_login_if_needed(server, username: str, password: str) -> None:
    username = (username or '').strip()
    password = password or ''
    if username or password:
        if not username or not password:
            raise ValueError('SMTP username and password must both be provided when SMTP authentication is used.')
        server.login(username, password)
