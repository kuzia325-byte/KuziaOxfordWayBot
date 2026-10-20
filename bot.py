import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from openai import AsyncOpenAI

TELEGRAM_TOKEN = "8686547051:AAE8d6U2APr61gWrH46QUlE8Nlk2mBcz1Jg"
OPENAI_API_KEY = "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"

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
ai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

TUTOR_PROMPT = """
You are a friendly, patient English tutor.
1. Chat with the user in English at their level.
2. If they make mistakes, gently correct them first in Russian/English.
3. Keep the conversation going with a short follow-up question.
"""

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Hello! 👋 Я твой личный ИИ-репетитор английского языка.\n\n"
        "Напиши мне что-нибудь на английском, и мы начнем общение!"
    )

@dp.message(F.text)
async def chat_with_tutor(message: types.Message):
    response = await ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": TUTOR_PROMPT},
            {"role": "user", "content": message.text}
        ]
    )
    await message.answer(response.choices[0].message.content)

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
