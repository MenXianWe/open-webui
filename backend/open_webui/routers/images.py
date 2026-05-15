import asyncio
import base64
import uuid
import io
import json
import logging
import mimetypes
import re
from typing import Optional

import aiohttp

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from open_webui.config import (
    CACHE_DIR,
    IMAGE_AUTO_SIZE_MODELS_REGEX_PATTERN,
    IMAGE_URL_RESPONSE_MODELS_REGEX_PATTERN,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.retrieval.web.utils import validate_url
from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL, AIOHTTP_CLIENT_ALLOW_REDIRECTS, ENABLE_FORWARD_USER_INFO_HEADERS
from open_webui.utils.session_pool import get_session

from open_webui.models.chats import Chats
from open_webui.routers.files import upload_file_handler, get_file_content_by_id
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.headers import include_user_info_headers
from open_webui.utils.qlcode import (
    QLCODE_API_BASE_URL,
    QLCODE_IMAGE_GENERATION_MODEL,
    QLCODE_IMAGE_MODEL_MISSING_DETAIL,
    QLCODE_IMAGE_GENERATION_SIZE,
    get_required_user_qlcode_api_key,
    qlcode_models_include,
    qlcode_api_headers,
    qlcode_error_detail,
)
from pydantic import BaseModel

log = logging.getLogger(__name__)

# An image can lie as easily as it can illuminate. Let what
# is generated here be honest about what it shows.
IMAGE_CACHE_DIR = CACHE_DIR / 'image' / 'generations'
IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter()


async def set_image_model(request: Request, model: str):
    log.info(f'Setting image model to {model}')
    request.app.state.config.IMAGE_GENERATION_MODEL = model
    if request.app.state.config.IMAGE_GENERATION_ENGINE in ['', 'automatic1111']:
        api_auth = get_automatic1111_api_auth(request)

        try:
            session = await get_session()
            async with session.get(
                url=f'{request.app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options',
                headers={'authorization': api_auth},
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                options = await r.json()
            if model != options['sd_model_checkpoint']:
                options['sd_model_checkpoint'] = model
                async with session.post(
                    url=f'{request.app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options',
                    json=options,
                    headers={'authorization': api_auth},
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as r:
                    r.raise_for_status()
        except Exception as e:
            log.debug(f'{e}')

    return request.app.state.config.IMAGE_GENERATION_MODEL


async def get_image_model(request):
    if request.app.state.config.IMAGE_GENERATION_ENGINE == 'openai':
        return (
            request.app.state.config.IMAGE_GENERATION_MODEL
            if request.app.state.config.IMAGE_GENERATION_MODEL
            else 'dall-e-2'
        )
    elif request.app.state.config.IMAGE_GENERATION_ENGINE == 'gemini':
        return (
            request.app.state.config.IMAGE_GENERATION_MODEL
            if request.app.state.config.IMAGE_GENERATION_MODEL
            else 'imagen-3.0-generate-002'
        )
    elif request.app.state.config.IMAGE_GENERATION_ENGINE == 'comfyui':
        return (
            request.app.state.config.IMAGE_GENERATION_MODEL if request.app.state.config.IMAGE_GENERATION_MODEL else ''
        )
    elif (
        request.app.state.config.IMAGE_GENERATION_ENGINE == 'automatic1111'
        or request.app.state.config.IMAGE_GENERATION_ENGINE == ''
    ):
        try:
            session = await get_session()
            async with session.get(
                url=f'{request.app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options',
                headers={'authorization': get_automatic1111_api_auth(request)},
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                options = await r.json()
            return options['sd_model_checkpoint']
        except Exception as e:
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))


class ImagesConfig(BaseModel):
    ENABLE_IMAGE_GENERATION: bool
    ENABLE_IMAGE_PROMPT_GENERATION: bool

    IMAGE_GENERATION_ENGINE: str
    IMAGE_GENERATION_MODEL: str
    IMAGE_SIZE: Optional[str]
    IMAGE_STEPS: Optional[int]

    IMAGES_OPENAI_API_BASE_URL: str
    IMAGES_OPENAI_API_KEY: str
    IMAGES_OPENAI_API_VERSION: str
    IMAGES_OPENAI_API_PARAMS: Optional[dict | str]

    AUTOMATIC1111_BASE_URL: str
    AUTOMATIC1111_API_AUTH: Optional[dict | str]
    AUTOMATIC1111_PARAMS: Optional[dict | str]

    COMFYUI_BASE_URL: str
    COMFYUI_API_KEY: str
    COMFYUI_WORKFLOW: str
    COMFYUI_WORKFLOW_NODES: list[dict]

    IMAGES_GEMINI_API_BASE_URL: str
    IMAGES_GEMINI_API_KEY: str
    IMAGES_GEMINI_ENDPOINT_METHOD: str

    ENABLE_IMAGE_EDIT: bool
    IMAGE_EDIT_ENGINE: str
    IMAGE_EDIT_MODEL: str
    IMAGE_EDIT_SIZE: Optional[str]

    IMAGES_EDIT_OPENAI_API_BASE_URL: str
    IMAGES_EDIT_OPENAI_API_KEY: str
    IMAGES_EDIT_OPENAI_API_VERSION: str
    IMAGES_EDIT_GEMINI_API_BASE_URL: str
    IMAGES_EDIT_GEMINI_API_KEY: str
    IMAGES_EDIT_COMFYUI_BASE_URL: str
    IMAGES_EDIT_COMFYUI_API_KEY: str
    IMAGES_EDIT_COMFYUI_WORKFLOW: str
    IMAGES_EDIT_COMFYUI_WORKFLOW_NODES: list[dict]


@router.get('/config', response_model=ImagesConfig)
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        'ENABLE_IMAGE_GENERATION': request.app.state.config.ENABLE_IMAGE_GENERATION,
        'ENABLE_IMAGE_PROMPT_GENERATION': request.app.state.config.ENABLE_IMAGE_PROMPT_GENERATION,
        'IMAGE_GENERATION_ENGINE': request.app.state.config.IMAGE_GENERATION_ENGINE,
        'IMAGE_GENERATION_MODEL': request.app.state.config.IMAGE_GENERATION_MODEL,
        'IMAGE_SIZE': request.app.state.config.IMAGE_SIZE,
        'IMAGE_STEPS': request.app.state.config.IMAGE_STEPS,
        'IMAGES_OPENAI_API_BASE_URL': request.app.state.config.IMAGES_OPENAI_API_BASE_URL,
        'IMAGES_OPENAI_API_KEY': request.app.state.config.IMAGES_OPENAI_API_KEY,
        'IMAGES_OPENAI_API_VERSION': request.app.state.config.IMAGES_OPENAI_API_VERSION,
        'IMAGES_OPENAI_API_PARAMS': request.app.state.config.IMAGES_OPENAI_API_PARAMS,
        'AUTOMATIC1111_BASE_URL': request.app.state.config.AUTOMATIC1111_BASE_URL,
        'AUTOMATIC1111_API_AUTH': request.app.state.config.AUTOMATIC1111_API_AUTH,
        'AUTOMATIC1111_PARAMS': request.app.state.config.AUTOMATIC1111_PARAMS,
        'COMFYUI_BASE_URL': request.app.state.config.COMFYUI_BASE_URL,
        'COMFYUI_API_KEY': request.app.state.config.COMFYUI_API_KEY,
        'COMFYUI_WORKFLOW': request.app.state.config.COMFYUI_WORKFLOW,
        'COMFYUI_WORKFLOW_NODES': request.app.state.config.COMFYUI_WORKFLOW_NODES,
        'IMAGES_GEMINI_API_BASE_URL': request.app.state.config.IMAGES_GEMINI_API_BASE_URL,
        'IMAGES_GEMINI_API_KEY': request.app.state.config.IMAGES_GEMINI_API_KEY,
        'IMAGES_GEMINI_ENDPOINT_METHOD': request.app.state.config.IMAGES_GEMINI_ENDPOINT_METHOD,
        'ENABLE_IMAGE_EDIT': request.app.state.config.ENABLE_IMAGE_EDIT,
        'IMAGE_EDIT_ENGINE': request.app.state.config.IMAGE_EDIT_ENGINE,
        'IMAGE_EDIT_MODEL': request.app.state.config.IMAGE_EDIT_MODEL,
        'IMAGE_EDIT_SIZE': request.app.state.config.IMAGE_EDIT_SIZE,
        'IMAGES_EDIT_OPENAI_API_BASE_URL': request.app.state.config.IMAGES_EDIT_OPENAI_API_BASE_URL,
        'IMAGES_EDIT_OPENAI_API_KEY': request.app.state.config.IMAGES_EDIT_OPENAI_API_KEY,
        'IMAGES_EDIT_OPENAI_API_VERSION': request.app.state.config.IMAGES_EDIT_OPENAI_API_VERSION,
        'IMAGES_EDIT_GEMINI_API_BASE_URL': request.app.state.config.IMAGES_EDIT_GEMINI_API_BASE_URL,
        'IMAGES_EDIT_GEMINI_API_KEY': request.app.state.config.IMAGES_EDIT_GEMINI_API_KEY,
        'IMAGES_EDIT_COMFYUI_BASE_URL': request.app.state.config.IMAGES_EDIT_COMFYUI_BASE_URL,
        'IMAGES_EDIT_COMFYUI_API_KEY': request.app.state.config.IMAGES_EDIT_COMFYUI_API_KEY,
        'IMAGES_EDIT_COMFYUI_WORKFLOW': request.app.state.config.IMAGES_EDIT_COMFYUI_WORKFLOW,
        'IMAGES_EDIT_COMFYUI_WORKFLOW_NODES': request.app.state.config.IMAGES_EDIT_COMFYUI_WORKFLOW_NODES,
    }


@router.post('/config/update')
async def update_config(request: Request, form_data: ImagesConfig, user=Depends(get_admin_user)):
    request.app.state.config.ENABLE_IMAGE_GENERATION = form_data.ENABLE_IMAGE_GENERATION

    # Create Image
    request.app.state.config.ENABLE_IMAGE_PROMPT_GENERATION = form_data.ENABLE_IMAGE_PROMPT_GENERATION

    request.app.state.config.IMAGE_GENERATION_ENGINE = form_data.IMAGE_GENERATION_ENGINE
    await set_image_model(request, form_data.IMAGE_GENERATION_MODEL)
    if form_data.IMAGE_SIZE == 'auto' and not re.match(
        IMAGE_AUTO_SIZE_MODELS_REGEX_PATTERN, form_data.IMAGE_GENERATION_MODEL
    ):
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.INCORRECT_FORMAT(
                f'  (auto is only allowed with models matching {IMAGE_AUTO_SIZE_MODELS_REGEX_PATTERN}).'
            ),
        )

    pattern = r'^\d+x\d+$'
    if form_data.IMAGE_SIZE == 'auto' or form_data.IMAGE_SIZE == '' or re.match(pattern, form_data.IMAGE_SIZE):
        request.app.state.config.IMAGE_SIZE = form_data.IMAGE_SIZE
    else:
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.INCORRECT_FORMAT('  (e.g., 512x512).'),
        )

    if form_data.IMAGE_STEPS >= 0:
        request.app.state.config.IMAGE_STEPS = form_data.IMAGE_STEPS
    else:
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.INCORRECT_FORMAT('  (e.g., 50).'),
        )

    request.app.state.config.IMAGES_OPENAI_API_BASE_URL = form_data.IMAGES_OPENAI_API_BASE_URL
    request.app.state.config.IMAGES_OPENAI_API_KEY = form_data.IMAGES_OPENAI_API_KEY
    request.app.state.config.IMAGES_OPENAI_API_VERSION = form_data.IMAGES_OPENAI_API_VERSION
    request.app.state.config.IMAGES_OPENAI_API_PARAMS = form_data.IMAGES_OPENAI_API_PARAMS

    request.app.state.config.AUTOMATIC1111_BASE_URL = form_data.AUTOMATIC1111_BASE_URL
    request.app.state.config.AUTOMATIC1111_API_AUTH = form_data.AUTOMATIC1111_API_AUTH
    request.app.state.config.AUTOMATIC1111_PARAMS = form_data.AUTOMATIC1111_PARAMS

    request.app.state.config.COMFYUI_BASE_URL = form_data.COMFYUI_BASE_URL.strip('/')
    request.app.state.config.COMFYUI_API_KEY = form_data.COMFYUI_API_KEY
    request.app.state.config.COMFYUI_WORKFLOW = form_data.COMFYUI_WORKFLOW
    request.app.state.config.COMFYUI_WORKFLOW_NODES = form_data.COMFYUI_WORKFLOW_NODES

    request.app.state.config.IMAGES_GEMINI_API_BASE_URL = form_data.IMAGES_GEMINI_API_BASE_URL
    request.app.state.config.IMAGES_GEMINI_API_KEY = form_data.IMAGES_GEMINI_API_KEY
    request.app.state.config.IMAGES_GEMINI_ENDPOINT_METHOD = form_data.IMAGES_GEMINI_ENDPOINT_METHOD

    # Edit Image
    request.app.state.config.ENABLE_IMAGE_EDIT = form_data.ENABLE_IMAGE_EDIT
    request.app.state.config.IMAGE_EDIT_ENGINE = form_data.IMAGE_EDIT_ENGINE
    request.app.state.config.IMAGE_EDIT_MODEL = form_data.IMAGE_EDIT_MODEL
    request.app.state.config.IMAGE_EDIT_SIZE = form_data.IMAGE_EDIT_SIZE

    request.app.state.config.IMAGES_EDIT_OPENAI_API_BASE_URL = form_data.IMAGES_EDIT_OPENAI_API_BASE_URL
    request.app.state.config.IMAGES_EDIT_OPENAI_API_KEY = form_data.IMAGES_EDIT_OPENAI_API_KEY
    request.app.state.config.IMAGES_EDIT_OPENAI_API_VERSION = form_data.IMAGES_EDIT_OPENAI_API_VERSION

    request.app.state.config.IMAGES_EDIT_GEMINI_API_BASE_URL = form_data.IMAGES_EDIT_GEMINI_API_BASE_URL
    request.app.state.config.IMAGES_EDIT_GEMINI_API_KEY = form_data.IMAGES_EDIT_GEMINI_API_KEY

    request.app.state.config.IMAGES_EDIT_COMFYUI_BASE_URL = form_data.IMAGES_EDIT_COMFYUI_BASE_URL.strip('/')
    request.app.state.config.IMAGES_EDIT_COMFYUI_API_KEY = form_data.IMAGES_EDIT_COMFYUI_API_KEY
    request.app.state.config.IMAGES_EDIT_COMFYUI_WORKFLOW = form_data.IMAGES_EDIT_COMFYUI_WORKFLOW
    request.app.state.config.IMAGES_EDIT_COMFYUI_WORKFLOW_NODES = form_data.IMAGES_EDIT_COMFYUI_WORKFLOW_NODES

    return {
        'ENABLE_IMAGE_GENERATION': request.app.state.config.ENABLE_IMAGE_GENERATION,
        'ENABLE_IMAGE_PROMPT_GENERATION': request.app.state.config.ENABLE_IMAGE_PROMPT_GENERATION,
        'IMAGE_GENERATION_ENGINE': request.app.state.config.IMAGE_GENERATION_ENGINE,
        'IMAGE_GENERATION_MODEL': request.app.state.config.IMAGE_GENERATION_MODEL,
        'IMAGE_SIZE': request.app.state.config.IMAGE_SIZE,
        'IMAGE_STEPS': request.app.state.config.IMAGE_STEPS,
        'IMAGES_OPENAI_API_BASE_URL': request.app.state.config.IMAGES_OPENAI_API_BASE_URL,
        'IMAGES_OPENAI_API_KEY': request.app.state.config.IMAGES_OPENAI_API_KEY,
        'IMAGES_OPENAI_API_VERSION': request.app.state.config.IMAGES_OPENAI_API_VERSION,
        'IMAGES_OPENAI_API_PARAMS': request.app.state.config.IMAGES_OPENAI_API_PARAMS,
        'AUTOMATIC1111_BASE_URL': request.app.state.config.AUTOMATIC1111_BASE_URL,
        'AUTOMATIC1111_API_AUTH': request.app.state.config.AUTOMATIC1111_API_AUTH,
        'AUTOMATIC1111_PARAMS': request.app.state.config.AUTOMATIC1111_PARAMS,
        'COMFYUI_BASE_URL': request.app.state.config.COMFYUI_BASE_URL,
        'COMFYUI_API_KEY': request.app.state.config.COMFYUI_API_KEY,
        'COMFYUI_WORKFLOW': request.app.state.config.COMFYUI_WORKFLOW,
        'COMFYUI_WORKFLOW_NODES': request.app.state.config.COMFYUI_WORKFLOW_NODES,
        'IMAGES_GEMINI_API_BASE_URL': request.app.state.config.IMAGES_GEMINI_API_BASE_URL,
        'IMAGES_GEMINI_API_KEY': request.app.state.config.IMAGES_GEMINI_API_KEY,
        'IMAGES_GEMINI_ENDPOINT_METHOD': request.app.state.config.IMAGES_GEMINI_ENDPOINT_METHOD,
        'ENABLE_IMAGE_EDIT': request.app.state.config.ENABLE_IMAGE_EDIT,
        'IMAGE_EDIT_ENGINE': request.app.state.config.IMAGE_EDIT_ENGINE,
        'IMAGE_EDIT_MODEL': request.app.state.config.IMAGE_EDIT_MODEL,
        'IMAGE_EDIT_SIZE': request.app.state.config.IMAGE_EDIT_SIZE,
        'IMAGES_EDIT_OPENAI_API_BASE_URL': request.app.state.config.IMAGES_EDIT_OPENAI_API_BASE_URL,
        'IMAGES_EDIT_OPENAI_API_KEY': request.app.state.config.IMAGES_EDIT_OPENAI_API_KEY,
        'IMAGES_EDIT_OPENAI_API_VERSION': request.app.state.config.IMAGES_EDIT_OPENAI_API_VERSION,
        'IMAGES_EDIT_GEMINI_API_BASE_URL': request.app.state.config.IMAGES_EDIT_GEMINI_API_BASE_URL,
        'IMAGES_EDIT_GEMINI_API_KEY': request.app.state.config.IMAGES_EDIT_GEMINI_API_KEY,
        'IMAGES_EDIT_COMFYUI_BASE_URL': request.app.state.config.IMAGES_EDIT_COMFYUI_BASE_URL,
        'IMAGES_EDIT_COMFYUI_API_KEY': request.app.state.config.IMAGES_EDIT_COMFYUI_API_KEY,
        'IMAGES_EDIT_COMFYUI_WORKFLOW': request.app.state.config.IMAGES_EDIT_COMFYUI_WORKFLOW,
        'IMAGES_EDIT_COMFYUI_WORKFLOW_NODES': request.app.state.config.IMAGES_EDIT_COMFYUI_WORKFLOW_NODES,
    }


def get_automatic1111_api_auth(request: Request):
    if request.app.state.config.AUTOMATIC1111_API_AUTH is None:
        return ''
    else:
        auth1111_byte_string = request.app.state.config.AUTOMATIC1111_API_AUTH.encode('utf-8')
        auth1111_base64_encoded_bytes = base64.b64encode(auth1111_byte_string)
        auth1111_base64_encoded_string = auth1111_base64_encoded_bytes.decode('utf-8')
        return f'Basic {auth1111_base64_encoded_string}'


@router.get('/config/url/verify')
async def verify_url(request: Request, user=Depends(get_admin_user)):
    if request.app.state.config.IMAGE_GENERATION_ENGINE == 'automatic1111':
        try:
            session = await get_session()
            async with session.get(
                url=f'{request.app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options',
                headers={'authorization': get_automatic1111_api_auth(request)},
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                r.raise_for_status()
                return True
        except Exception:
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.INVALID_URL)
    elif request.app.state.config.IMAGE_GENERATION_ENGINE == 'comfyui':
        headers = None
        if request.app.state.config.COMFYUI_API_KEY:
            headers = {'Authorization': f'Bearer {request.app.state.config.COMFYUI_API_KEY}'}
        try:
            session = await get_session()
            async with session.get(
                url=f'{request.app.state.config.COMFYUI_BASE_URL}/object_info',
                headers=headers,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                r.raise_for_status()
                return True
        except Exception:
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.INVALID_URL)
    else:
        return True


@router.get('/models')
async def get_models(request: Request, user=Depends(get_verified_user)):
    return [{'id': QLCODE_IMAGE_GENERATION_MODEL, 'name': 'GPT-IMAGE 2'}]


async def ensure_user_has_image_model(session, api_key: str):
    async with session.get(
        url=f'{QLCODE_API_BASE_URL}/models',
        headers=qlcode_api_headers(api_key),
        ssl=AIOHTTP_CLIENT_SESSION_SSL,
    ) as r:
        if r.status >= 400:
            raise HTTPException(status_code=r.status, detail=await qlcode_error_detail(r))
        models_payload = await r.json()

    if not qlcode_models_include(models_payload, QLCODE_IMAGE_GENERATION_MODEL):
        raise HTTPException(status_code=403, detail=QLCODE_IMAGE_MODEL_MISSING_DETAIL)


class CreateImageForm(BaseModel):
    model: Optional[str] = None
    prompt: str
    size: Optional[str] = None
    n: int = 1
    steps: Optional[int] = None
    negative_prompt: Optional[str] = None


GenerateImageForm = CreateImageForm  # Alias for backward compatibility


async def get_image_data(data: str, headers=None):
    try:
        if data.startswith('http://') or data.startswith('https://'):
            # Defense-in-depth: gate before fetch (mirrors load_url_image).
            validate_url(data)
            session = await get_session()
            async with session.get(
                data,
                headers=headers,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                r.raise_for_status()
                content_type = r.headers.get('content-type', '')
                if content_type.split('/')[0] == 'image':
                    return await r.read(), content_type
                else:
                    log.error('Url does not point to an image.')
                    return None, None
        else:
            if ',' in data:
                header, encoded = data.split(',', 1)
                mime_type = header.split(';')[0].lstrip('data:')
                img_data = base64.b64decode(encoded)
            else:
                mime_type = 'image/png'
                img_data = base64.b64decode(data)
            return img_data, mime_type
    except Exception as e:
        log.exception(f'Error loading image data: {e}')
        return None, None


async def upload_image(request, image_data, content_type, metadata, user, db=None):
    image_format = mimetypes.guess_extension(content_type)
    file = UploadFile(
        file=io.BytesIO(image_data),
        filename=f'generated-image{image_format}',  # will be converted to a unique ID on upload_file
        headers={
            'content-type': content_type,
        },
    )
    file_item = await upload_file_handler(
        request,
        file=file,
        metadata=metadata,
        process=False,
        user=user,
    )

    if file_item and file_item.id:
        # If chat_id and message_id are provided in metadata, link the file to the chat message
        chat_id = metadata.get('chat_id')
        message_id = metadata.get('message_id')

        if chat_id and message_id:
            await Chats.insert_chat_files(
                chat_id=chat_id,
                message_id=message_id,
                file_ids=[file_item.id],
                user_id=user.id,
                db=db,
            )

    url = request.app.url_path_for('get_file_content_by_id', id=file_item.id)
    return file_item, url


@router.post('/generations')
async def generate_images(request: Request, form_data: CreateImageForm, user=Depends(get_verified_user)):
    return await image_generations(request, form_data, user=user)


async def image_generations(
    request: Request,
    form_data: CreateImageForm,
    metadata: Optional[dict] = None,
    user=None,
):
    metadata = metadata or {}
    qlcode_api_key = get_required_user_qlcode_api_key(user)
    model = QLCODE_IMAGE_GENERATION_MODEL
    size = form_data.size or QLCODE_IMAGE_GENERATION_SIZE

    if size != 'auto' and not re.match(r'^\d+x\d+$', size):
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.INCORRECT_FORMAT('  (e.g., 1024x1024).'),
        )

    try:
        # User-facing image generation uses the user's fixed QLCodeAPI connection.
        headers = qlcode_api_headers(qlcode_api_key)

        if ENABLE_FORWARD_USER_INFO_HEADERS:
            headers = include_user_info_headers(headers, user)

        data = {
            'model': model,
            'prompt': form_data.prompt,
            'n': form_data.n,
            'size': size,
            **(
                {}
                if re.match(
                    IMAGE_URL_RESPONSE_MODELS_REGEX_PATTERN,
                    model,
                )
                else {'response_format': 'b64_json'}
            ),
        }

        session = await get_session()
        await ensure_user_has_image_model(session, qlcode_api_key)
        async with session.post(
            url=f'{QLCODE_API_BASE_URL}/images/generations',
            json=data,
            headers=headers,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as r:
            if r.status >= 400:
                raise HTTPException(status_code=r.status, detail=await qlcode_error_detail(r))
            res = await r.json()

        images = []

        for image in res['data']:
            if image_url := image.get('url', None):
                image_data, content_type = await get_image_data(
                    image_url,
                    {k: v for k, v in headers.items() if k != 'Content-Type'},
                )
            else:
                image_data, content_type = await get_image_data(image['b64_json'])

            _, url = await upload_image(request, image_data, content_type, {**data, **metadata}, user)
            images.append({'url': url})
        return images

    except HTTPException:
        raise
    except Exception as e:
        error = e
        if isinstance(e, aiohttp.ClientResponseError):
            error = e.message
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(error))


class EditImageForm(BaseModel):
    image: str | list[str]  # base64-encoded image(s) or URL(s)
    prompt: str
    model: Optional[str] = None
    size: Optional[str] = None
    n: Optional[int] = None
    negative_prompt: Optional[str] = None
    background: Optional[str] = None


@router.post('/edit')
async def image_edits(
    request: Request,
    form_data: EditImageForm,
    metadata: Optional[dict] = None,
    user=Depends(get_verified_user),
):
    size = form_data.size
    metadata = metadata or {}

    if size and size != 'auto' and not re.match(r'^\d+x\d+$', size):
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.INCORRECT_FORMAT('  (e.g., 1024x1024).'),
        )

    qlcode_api_key = get_required_user_qlcode_api_key(user)
    model = QLCODE_IMAGE_GENERATION_MODEL

    try:

        async def load_url_image(data):
            if data.startswith('data:'):
                return data

            if data.startswith('http://') or data.startswith('https://'):
                # Validate URL to prevent SSRF attacks against local/private networks.
                # allow_redirects=False prevents redirect-based SSRF: validate_url() is
                # called only on the originally-submitted URL; following 3xx redirects
                # without re-validation would let an attacker reach private IPs via a
                # public host that redirects internally (e.g. cloud-metadata exfil).
                validate_url(data)
                session = await get_session()
                async with session.get(
                    data, ssl=AIOHTTP_CLIENT_SESSION_SSL, allow_redirects=AIOHTTP_CLIENT_ALLOW_REDIRECTS
                ) as r:
                    r.raise_for_status()

                    image_data = base64.b64encode(await r.read()).decode('utf-8')
                    return f'data:{r.headers["content-type"]};base64,{image_data}'

            else:
                file_id = None
                if data.startswith('/api/v1/files'):
                    file_id = data.split('/api/v1/files/')[1].split('/content')[0]
                else:
                    file_id = data

                file_response = await get_file_content_by_id(file_id, user)
                if isinstance(file_response, FileResponse):
                    file_path = file_response.path

                    with open(file_path, 'rb') as f:
                        file_bytes = f.read()
                        image_data = base64.b64encode(file_bytes).decode('utf-8')
                        mime_type, _ = mimetypes.guess_type(file_path)

                    return f'data:{mime_type};base64,{image_data}'
            return data

        # Load image(s) from URL(s) if necessary
        if isinstance(form_data.image, str):
            form_data.image = await load_url_image(form_data.image)
        elif isinstance(form_data.image, list):
            # Load all images in parallel for better performance
            form_data.image = list(await asyncio.gather(*[load_url_image(img) for img in form_data.image]))
    except Exception as e:
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))

    def get_image_file_item(base64_string, param_name='image'):
        data = base64_string
        header, encoded = data.split(',', 1)
        mime_type = header.split(';')[0].lstrip('data:')
        image_data = base64.b64decode(encoded)
        return (
            param_name,
            (
                f'{uuid.uuid4()}.png',
                io.BytesIO(image_data),
                mime_type if mime_type else 'image/png',
            ),
        )

    try:
        # User-facing image editing uses the user's fixed QLCodeAPI connection.
        headers = qlcode_api_headers(qlcode_api_key, content_type=None)

        if ENABLE_FORWARD_USER_INFO_HEADERS:
            headers = include_user_info_headers(headers, user)

        data = {
            'model': model,
            'prompt': form_data.prompt,
            **({'n': form_data.n} if form_data.n else {}),
            **({'size': size} if size else {}),
            **({'background': form_data.background} if form_data.background else {}),
            **(
                {}
                if re.match(
                    IMAGE_URL_RESPONSE_MODELS_REGEX_PATTERN,
                    model,
                )
                else {'response_format': 'b64_json'}
            ),
        }

        files = []
        if isinstance(form_data.image, str):
            files = [get_image_file_item(form_data.image)]
        elif isinstance(form_data.image, list):
            for img in form_data.image:
                files.append(get_image_file_item(img, 'image[]'))

        form = aiohttp.FormData()
        for key, value in data.items():
            if isinstance(value, dict):
                form.add_field(key, json.dumps(value))
            else:
                form.add_field(key, str(value))
        for param_name, (filename, file_obj, content_type_val) in files:
            form.add_field(
                param_name,
                file_obj,
                filename=filename,
                content_type=content_type_val,
            )

        session = await get_session()
        await ensure_user_has_image_model(session, qlcode_api_key)
        async with session.post(
            url=f'{QLCODE_API_BASE_URL}/images/edits',
            headers=headers,
            data=form,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as r:
            if r.status >= 400:
                raise HTTPException(status_code=r.status, detail=await qlcode_error_detail(r))
            res = await r.json()

        images = []
        for image in res['data']:
            if image_url := image.get('url', None):
                image_data, content_type = await get_image_data(
                    image_url,
                    headers,
                )
            else:
                image_data, content_type = await get_image_data(image['b64_json'])

            _, url = await upload_image(
                request,
                image_data,
                content_type,
                {**data, **metadata},
                user,
            )
            images.append({'url': url})
        return images

    except HTTPException:
        raise
    except Exception as e:
        error = e
        if isinstance(e, aiohttp.ClientResponseError):
            error = e.message

        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(error))
