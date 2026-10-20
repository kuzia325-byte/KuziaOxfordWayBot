import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from google import genai
from aiohttp import web

TELEGRAM_TOKEN = "8686547051:AAHgoLVxYHINS0M9rRFC53ZuLMJv5arDyxA"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

ai_client = genai.Client(api_key=GEMINI_API_KEY)

TUTOR_PROMPT = """
You are a highly skilled, patient, and adaptive English language tutor capable of teaching students from complete beginners (A0/A1) to advanced fluent speakers (C1/C2).
Your core goals: adapt to the user's level, converse naturally, explain grammar clearly, and gently correct mistakes in a bilingual (Russian/English) approach.
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
            model="gemini-3.8-flash",
            contents=message.text,
            config={"system_instruction": TUTOR_PROMPT}
        )
        await message.answer(response.text)
    except Exception as e:
        logging.error(f"Error calling Gemini: {e}")
        await message.answer("Произошла ошибка при обращении к ИИ. Попробуй еще раз чуть позже!")

async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # ПРИНУДИТЕЛЬНО сбрасываем любые зависшие соединения и вебхуки Telegram
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Webhook successfully cleared, starting polling...")

    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server started on port {port}")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
