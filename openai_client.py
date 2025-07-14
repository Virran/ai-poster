import openai
import os
openai.api_key = os.getenv("OPENAI_API_KEY")

async def generate_post(theme: str, style: str) -> str:
    prompt = (f"Напиши пост для Telegram-канала по теме {theme} "
              f"в стиле {style}. Максимум 2500 знаков, 3–5 хештегов.")
    chat = await openai.ChatCompletion.acreate(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return chat.choices[0].message.content.strip()

async def generate_image(theme: str, style: str) -> str:
    prompt = f"{theme}, {style}, high-resolution photo, 16:9"
    resp = await openai.Image.acreate(prompt=prompt, n=1, size="1024x576")
    return resp.data[0].url