import vk_api, os, aiohttp
from io import BytesIO

class VKPoster:
    def __init__(self, token: str):
        self.vk = vk_api.VkApi(token=token).get_api()

    async def post(self, message: str, image_url: str | None):
        attach = None
        if image_url:
            async with aiohttp.ClientSession() as s:
                async with s.get(image_url) as r:
                    photo = BytesIO(await r.read())
            upload = vk_api.VkUpload(self.vk)
            resp = upload.photo_wall(photos=photo, group_id=self.vk.groups.getById()[0]['id'])
            attach = f"photo{resp[0]['owner_id']}_{resp[0]['id']}"
        self.vk.wall.post(owner_id=f"-{self.vk.groups.getById()[0]['id']}",
                          message=message, attachments=attach)