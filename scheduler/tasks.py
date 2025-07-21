from celery import Celery
from celery.schedules import crontab
from db import async_session
from models import Post, PostStatus
from vk import VKPoster

cel = Celery("tasks", broker="redis://redis:6379/0")

@cel.on_after_configure.connect
def setup_periodic(sender, **kwargs):
    sender.add_periodic_task(crontab(minute="*/30"), post_job.s())

@cel.task
def post_job():
    import asyncio
    asyncio.run(_post())

async def _post():
    async with async_session() as s:
        posts = await s.execute(
            select(Post).where(Post.status == PostStatus.PLANNED, Post.scheduled_at <= datetime.utcnow())
        )
        for p in posts.scalars():
            try:
                vk = VKPoster(p.user.vk_token)
                await vk.post(p.text, p.image_url)
                p.status = PostStatus.POSTED
                p.posted_at = datetime.utcnow()
            except Exception as e:
                p.status = PostStatus.ERROR
            await s.commit()