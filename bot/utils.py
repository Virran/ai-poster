import asyncio
from datetime import datetime, timedelta
from openai_client import generate_post, generate_image
from db import async_session
from models import Post, User

async def generate_all_posts(user_id: int, theme: str, style: str, posts_per_day: float):
    total = int(posts_per_day * 30)
    dt = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0)
    async with async_session() as s:
        for i in range(total):
            text = await generate_post(theme, style)
            img = await generate_image(theme, style)
            p = Post(
                user_id=user_id,
                text=text,
                image_url=img,
                scheduled_at=dt + timedelta(hours=12 * (i % 2)),
            )
            s.add(p)
        await s.commit()