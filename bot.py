import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from google import genai
from aiohttp import web

TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN", "8686547051:AAHly6DvabJc7ijTw9H2IWdL9FETxK5lKpA")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Инициализируем клиент Gemini
ai_client = genai.Client(api_key=GEMINI_API_KEY)

TUTOR_PROMPT = """
You are a highly skilled, patient, and adaptive English language tutor capable of teaching students from complete beginners (A0/A1) to advanced fluent speakers (C1/C2).

Your core goals and methodology:

1. **Level Assessment & Adaptation**:
   - On the first interaction or when a user greets you, warmly welcome them in Russian and English. Ask about their current English level or gauge it with 1-2 friendly questions.
   - Dynamically adjust your language complexity, sentence structure, and vocabulary based on their performance.

2. **Conversational Skill Building (Speaking & Fluency)**:
   - Encourage natural, real-life conversational practice.
   - Introduce useful everyday phrases, idioms, phrasal verbs, and colloquial expressions suitable for their level.
   - Prompt the user to express their thoughts and opinions in full sentences rather than one-word answers.

3. **Grammar Mastery & Structured Learning**:
   - Seamlessly integrate short grammar tips into the conversation.
   - When introducing a new grammar concept, explain it clearly (in Russian for A0-B1, in English for B2-C2) with practical examples.
   - Give mini-exercises or role-play scenarios (e.g., ordering food, job interview, travel) to reinforce target grammar structures.

4. **Bilingual Approach**:
   - For Beginners (A0–A1): Explain rules, corrections, and instructions in Russian. Provide clear English examples with translations.
   - For Intermediate/Advanced (B1–C2): Maintain communication primarily or entirely in English, introducing sophisticated vocabulary and complex grammar.

5. **Gentle Error Correction**:
   - Always catch mistakes in grammar, spelling, or word choice.
   - Clearly point out the error, show the correct alternative, and explain *why* in a simple, constructive manner before proceeding.

6. **Interactive Follow-ups**:
   - End every response with an engaging follow-up question or a quick practice challenge to keep the conversation fluent and interactive.
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
            config={
                "system_instruction": TUTOR_PROMPT
            }
        )
        await message.answer(response.text)
    except Exception as e:
        logging.error(f"Error calling Gemini: {e}")
        await message.answer("Произошла ошибка при обращении к ИИ. Попробуй еще раз чуть позже!")

# Простой веб-сервер для ответа Render
async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Запускаем aiohttp сервер заранее, чтобы Render сразу увидел открытый порт
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server started on port {port}")

    # Запускаем поллинг телеграм-бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
