from aiogram import Router, F
from aiogram.types import Message
from bot.config import settings
from bot.utils.storage import storage
from bot.services.claude_proxy import ClaudeProxyClient
from bot.utils.media import transcribe_voice, extract_document_text

router = Router()

def text_to_content_blocks(text: str) -> list:
    return [{"type": "text", "text": text}]

async def send_reply_safely(message: Message, text: str):
    max_len = 4096
    if len(text) <= max_len:
        await message.answer(text)
    else:
        for i in range(0, len(text), max_len):
            await message.answer(text[i:i+max_len])

async def handle_streaming(message: Message, client: ClaudeProxyClient, messages: list) -> str:
    sent_msg = await message.answer("...")
    full_text = ""
    try:
        stream = client.send_message(
            messages=messages,
            model=settings.free_claude_default_model,
            stream=True
        )
        async for chunk in stream:
            if chunk.get("type") == "content_block_delta":
                delta = chunk.get("delta", {})
                if delta.get("type") == "text_delta":
                    text = delta.get("text", "")
                    full_text += text
                    try:
                        await sent_msg.edit_text(full_text[:4096])
                    except Exception:
                        pass
            elif chunk.get("type") == "message_stop":
                break
    except Exception as e:
        await sent_msg.edit_text(f"❌ Error: {str(e)}")
        raise
    return full_text

@router.message(F.text | F.photo | F.voice | F.document)
async def handle_chat_message(message: Message):
    user_id = message.from_user.id
    chat = message.chat
    bot_username = message.bot.username

    # Determine guest mode
    is_guest = False
    if settings.telegram_guest_mode_enabled and chat.type in ("group", "supergroup"):
        # Check direct mention @botusername
        if message.text and f"@{bot_username}" in message.text:
            is_guest = True
        # Check reply to a bot message
        if message.reply_to_message and message.reply_to_message.from_user:
            if message.reply_to_message.from_user.username == bot_username:
                is_guest = True

    # Build conversation messages list
    messages = []
    if not is_guest:
        history = storage.get_history(user_id)
        messages.extend(history)

    # Build current user message content
    content_blocks = None

    if message.text:
        content_blocks = text_to_content_blocks(message.text)

    elif message.photo:
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        data = await message.bot.download_file(file.file_path)
        import base64
        b64 = base64.b64encode(data).decode('utf-8')
        content_blocks = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": photo.mime_type or "image/jpeg",
                    "data": b64,
                },
            }
        ]
        if message.caption:
            content_blocks.append({"type": "text", "text": message.caption})

    elif message.voice:
        file = await message.bot.get_file(message.voice.file_id)
        data = await message.bot.download_file(file.file_path)
        transcribed = await transcribe_voice(data)
        if not transcribed:
            await message.answer("❌ Could not transcribe voice message.")
            return
        content_blocks = text_to_content_blocks(transcribed)

    elif message.document:
        doc = message.document
        file = await message.bot.get_file(doc.file_id)
        data = await message.bot.download_file(file.file_path)
        extracted = await extract_document_text(doc.mime_type, data)
        if not extracted:
            await message.answer(f"❌ Could not extract text from document: {doc.file_name}")
            return
        content_blocks = text_to_content_blocks(extracted)

    else:
        return  # Unsupported type

    if content_blocks is None:
        return

    # Append user message
    messages.append({"role": "user", "content": content_blocks})

    # Call Claude
    client = ClaudeProxyClient(
        settings.free_claude_base_url,
        settings.free_claude_auth_token,
        settings.free_claude_timeout_seconds,
    )
    try:
        if settings.free_claude_streaming_enabled:
            reply_text = await handle_streaming(message, client, messages)
        else:
            response = await client.send_message(
                messages=messages,
                model=settings.free_claude_default_model,
            )
            reply_text = ""
            for block in response.get("content", []):
                if block.get("type") == "text":
                    reply_text += block.get("text", "")
            if not reply_text:
                reply_text = "Claude returned no text response."
            await send_reply_safely(message, reply_text)

        # Save assistant response to history if not guest
        if not is_guest:
            storage.add_message(user_id, "user", content_blocks)
            storage.add_message(user_id, "assistant", [{"type": "text", "text": reply_text}])

    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")
    finally:
        await client.close()