import os, asyncio
from celery import Celery
from datetime import datetime, timedelta
from db import async_session
from models import User, Post, PostStatus
from openai_client import generate_post, generate_image
from vk import VKPoster

cel = Celery("tasks", broker=os.getenv("REDIS_URL"))

@cel.on_after_configure.connect
def setup_periodic(sender, **kwargs):
    sender.add_periodic_task(60*30, post_job.s(), name="post every 30 min")

@cel.task
def post_job():
    asyncio.run(_post())

async def _post():
    async with async_session() as s:
        posts = await s.execute(
            select(Post).where(Post.status==PostStatus.PLANNED,
                               Post.scheduled_at <= datetime.utcnow()))
        for p in posts.scalars():
            try:
                vk = VKPoster(p.user.vk_token)
                await vk.post(p.text, p.image_url)
                p.status = PostStatus.POSTED
                p.posted_at = datetime.utcnow()
            except Exception as e:
                p.status = PostStatus.ERROR
            await s.commit()

@cel.task
def generate_future_posts():
    asyncio.run(_gen())

async def _gen():
    async with async_session() as s:
        users = await s.execute(select(User).where(User.is_active==True,
                                                   User.expires_at > datetime.utcnow()))
        for u in users.scalars():
            needed = int(u.posts_per_day * 30)
            have = await s.execute(select(Post).where(Post.user_id==u.id,
                                                      Post.status==PostStatus.PLANNED))
            if len(have.all()) < needed:
                dt = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0)
                for i in range(needed - len(have.all())):
                    text = await generate_post(u.theme, u.style)
                    img = await generate_image(u.theme, u.style)
                    p = Post(user_id=u.id, text=text, image_url=img,
                             scheduled_at=dt+timedelta(hours=12*(i%2)))
                    s.add(p)
                await s.commit()