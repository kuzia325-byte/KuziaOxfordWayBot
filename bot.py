import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from google import genai
from aiohttp import web

TELEGRAM_TOKEN = "8686547051:AAHgoLVxYHINS0M9rRFC53ZuLMJv5arDyxA"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Получаем внешний URL от Render или используем заглушку
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
ai_client = genai.Client(api_key=GEMINI_API_KEY)

TUTOR_PROMPT = """
You are a highly skilled, patient, and adaptive English language tutor capable of teaching students from complete beginners (A0/A1) to advanced fluent speakers (C1/C2).

Core goals: adapt to the user's level, encourage conversation, explain grammar clearly, and gently correct mistakes in a bilingual (Russian/English) approach.
"""

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Hello! 👋 Привет! Я твой личный репетитор по английскому языку.\n\n"
        "Я помогу тебе выучить английский с самого нуля или прокачать разговорную речь и грамматику до совершенства!\n\n"
        "Скажи, какой у тебя сейчас уровень английского, или мы начинаем с самого нуля?"
    )

@dp.message(F.text)
async def chat_with_tutor(message: types.Message):
    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=message.text,
            config={"system_instruction": TUTOR_PROMPT}
        )
        await message.answer(response.text)
    except Exception as e:
        logging.error(f"Error calling Gemini: {e}")
        await message.answer("Произошла ошибка при обращении к ИИ. Попробуй еще раз чуть позже!")

async def on_startup(bot: Bot):
    if RENDER_EXTERNAL_URL:
        await bot.set_webhook(WEBHOOK_URL)
        logging.info(f"Webhook set to {WEBHOOK_URL}")
    else:
        logging.warning("RENDER_EXTERNAL_URL is not set. Webhook might not work correctly.")

# Обработчик для пингов (чтобы сервер не засыпал)
async def index(request):
    return web.Response(text="OxfordWayBot is running!")

def main():
    logging.basicConfig(level=logging.INFO)
    app = web.Application()
    
    # Регистрируем корневой URL для пингов крона
    app.router.add_get("/", index)

    # Регистрируем обработчик вебхуков для aiogram
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
