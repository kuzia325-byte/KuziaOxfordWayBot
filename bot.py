import asyncio
import logging
import os
from io import BytesIO

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from google import genai
from google.genai import types as genai_types
from aiohttp import web
from gtts import gTTS

TELEGRAM_TOKEN = "8686547051:AAHgoLVxYHINS0M9rRFC53ZuLMJv5arDyxA"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Хранилище выбранных языков пользователей
user_languages = {}

LANGUAGES = {
    "lang_en": {"name": "Английский 🇬🇧", "code": "en", "prompt_lang": "English"},
    "lang_es": {"name": "Испанский 🇪🇸", "code": "es", "prompt_lang": "Spanish"},
    "lang_fr": {"name": "Французский 🇫🇷", "code": "fr", "prompt_lang": "French"},
    "lang_de": {"name": "Немецкий 🇩🇪", "code": "de", "prompt_lang": "German"},
    "lang_ja": {"name": "Японский 🇯🇵", "code": "ja", "prompt_lang": "Japanese"},
    "lang_it": {"name": "Итальянский 🇮🇹", "code": "it", "prompt_lang": "Italian"},
    "lang_ko": {"name": "Корейский 🇰🇷", "code": "ko", "prompt_lang": "Korean"},
    "lang_zh": {"name": "Китайский 🇨🇳", "code": "zh-CN", "prompt_lang": "Chinese"},
    "lang_ru": {"name": "Русский 🇷🇺", "code": "ru", "prompt_lang": "Russian"},
    "lang_vi": {"name": "Вьетнамский 🇻🇳", "code": "vi", "prompt_lang": "Vietnamese"},
}

def get_tutor_prompt(target_language: str) -> str:
    return f"""
You are a highly skilled, patient, and adaptive language tutor teaching {target_language}.
You teach students from complete beginners (A0/A1) to advanced fluent speakers.

Core goals:
- Adapt to the user's level.
- Explain grammar clearly and gently correct mistakes using Russian for explanations when needed.
- Encourage conversation in {target_language}.

Audio & Speech Specific Instructions:
- You will receive both text and voice/audio messages from students.
- When processing voice messages, listen carefully to their pronunciation and grammar.
- Keep your answers natural, supportive, and structured so they sound clear both in text and spoken aloud.
"""

def text_to_speech_bytes(text: str, lang_code: str) -> BytesIO:
    try:
        tts = gTTS(text=text, lang=lang_code, slow=False)
    except Exception:
        tts = gTTS(text=text, lang='en', slow=False)
    
    fp = BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

async def send_voice_response(chat_id: int, text: str, lang_code: str):
    """Фоновая задача для синтеза и отправки голосового ответа."""
    try:
        await bot.send_chat_action(chat_id=chat_id, action="record_voice")
        voice_fp = await asyncio.to_thread(text_to_speech_bytes, text, lang_code)
        voice_file = BufferedInputFile(voice_fp.read(), filename="voice.ogg")
        await bot.send_voice(chat_id=chat_id, voice=voice_file)
    except Exception as e:
        logging.error(f"Error generating/sending voice: {e}")

def get_languages_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Английский 🇬🇧", callback_data="lang_en"),
         InlineKeyboardButton(text="Испанский 🇪🇸", callback_data="lang_es")],
        [InlineKeyboardButton(text="Французский 🇫🇷", callback_data="lang_fr"),
         InlineKeyboardButton(text="Немецкий 🇩🇪", callback_data="lang_de")],
        [InlineKeyboardButton(text="Японский 🇯🇵", callback_data="lang_ja"),
         InlineKeyboardButton(text="Итальянский 🇮🇹", callback_data="lang_it")],
        [InlineKeyboardButton(text="Корейский 🇰🇷", callback_data="lang_ko"),
         InlineKeyboardButton(text="Китайский 🇨🇳", callback_data="lang_zh")],
        [InlineKeyboardButton(text="Русский 🇷🇺", callback_data="lang_ru"),
         InlineKeyboardButton(text="Вьетнамский 🇻🇳", callback_data="lang_vi")]
    ])

def get_action_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💡 Объясни проще", callback_data="act_simpler"),
         InlineKeyboardButton(text="🔄 Переведи на русский", callback_data="act_translate")],
        [InlineKeyboardButton(text="⚙️ Сменить язык", callback_data="act_settings")]
    ])

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! 👋 Я твой личный ИИ-репетитор по иностранным языкам.\n\n"
        "Я умею работать как с **текстом**, так и с **голосовыми сообщениями**! 🎙\n\n"
        "Выбери язык, который ты хочешь изучать:",
        reply_markup=get_languages_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(Command("settings"))
async def cmd_settings(message: types.Message):
    await message.answer(
        "Выбери язык, на который хочешь переключиться:",
        reply_markup=get_languages_keyboard()
    )

@dp.callback_query(F.data == "act_settings")
async def callback_settings(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "Выбери язык, на который хочешь переключиться:",
        reply_markup=get_languages_keyboard()
    )

@dp.callback_query(F.data == "act_simpler")
async def callback_simpler(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    lang_info = user_languages.get(user_id, {"prompt_lang": "English", "code": "en", "name": "Английский"})
    
    prompt = get_tutor_prompt(lang_info["prompt_lang"])
    try:
        await bot.send_chat_action(chat_id=callback.message.chat.id, action="typing")
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Explain the previous rule or concept much simpler, using more Russian explanations and easy examples.",
            config={"system_instruction": prompt}
        )
        await callback.message.answer(response.text, reply_markup=get_action_keyboard())
    except Exception as e:
        logging.error(f"Error: {e}")
        await callback.message.answer("Не удалось получить ответ. Попробуй еще раз.")

@dp.callback_query(F.data == "act_translate")
async def callback_translate(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    lang_info = user_languages.get(user_id, {"prompt_lang": "English", "code": "en", "name": "Английский"})
    
    prompt = get_tutor_prompt(lang_info["prompt_lang"])
    try:
        await bot.send_chat_action(chat_id=callback.message.chat.id, action="typing")
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Translate your last message or explanation into Russian completely so I can understand it clearly.",
            config={"system_instruction": prompt}
        )
        await callback.message.answer(response.text, reply_markup=get_action_keyboard())
    except Exception as e:
        logging.error(f"Error: {e}")
        await callback.message.answer("Не удалось получить перевод.")

@dp.callback_query(F.data.startswith("lang_"))
async def process_language_choice(callback: types.CallbackQuery):
    await callback.answer()

    try:
        lang_key = callback.data
        lang_info = LANGUAGES.get(lang_key, LANGUAGES["lang_en"])

        user_languages[callback.from_user.id] = lang_info

        await callback.message.answer(
            f"Отлично! Начинаем изучать **{lang_info['name']}**! 🎉\n\n"
            f"Напиши или отправь мне **голосовое сообщение**:\n"
            f"Какой у тебя текущий уровень (с нуля или уже есть база)?",
            reply_markup=get_action_keyboard(),
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Error in callback query: {e}")

@dp.message(F.text)
async def chat_with_tutor_text(message: types.Message):
    user_id = message.from_user.id
    lang_info = user_languages.get(user_id, {"prompt_lang": "English", "code": "en", "name": "Английский"})
    
    prompt = get_tutor_prompt(lang_info["prompt_lang"])

    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=message.text,
            config={"system_instruction": prompt}
        )
        await message.answer(response.text, reply_markup=get_action_keyboard())
    except Exception as e:
        logging.error(f"Error calling Gemini: {e}")
        await message.answer("Произошла ошибка при обращении к ИИ. Попробуй еще раз чуть позже!")

@dp.message(F.voice)
async def chat_with_tutor_voice(message: types.Message):
    user_id = message.from_user.id
    lang_info = user_languages.get(user_id, {"prompt_lang": "English", "code": "en", "name": "Английский"})
    
    target_language = lang_info["prompt_lang"]
    lang_code = lang_info["code"]
    prompt = get_tutor_prompt(target_language)

    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

        file_id = message.voice.file_id
        file_info = await bot.get_file(file_id)
        file_bytes = await bot.download_file(file_info.file_path)
        audio_data = file_bytes.read()

        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                genai_types.Part.from_bytes(
                    data=audio_data,
                    mime_type="audio/ogg"
                ),
                f"Сначала напиши ровно то, что услышал от пользователя в аудио, в формате: '🎤 Вы сказали: ...'. Затем ответь пользователю как репетитор по языку ({target_language})."
            ],
            config={"system_instruction": prompt}
        )

        reply_text = response.text

        await message.answer(reply_text, reply_markup=get_action_keyboard())

        asyncio.create_task(send_voice_response(message.chat.id, reply_text, lang_code))

    except Exception as e:
        logging.error(f"Error handling voice message: {e}")
        await message.answer("Не удалось распознать голосовое сообщение. Попробуй еще раз!")

async def on_startup(bot: Bot):
    if RENDER_EXTERNAL_URL:
        await bot.set_webhook(WEBHOOK_URL)
        logging.info(f"Webhook set to {WEBHOOK_URL}")
    else:
        logging.warning("RENDER_EXTERNAL_URL is not set. Webhook might not work correctly.")

async def index(request):
    return web.Response(text="Multilingual Tutor Bot is running!")

def main():
    logging.basicConfig(level=logging.INFO)
    app = web.Application()
    
    app.router.add_get("/", index)

    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    dp.startup.register(on_startup)

    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
