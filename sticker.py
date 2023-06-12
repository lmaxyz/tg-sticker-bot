import dataclasses
from io import BytesIO

from rembg import remove
from telegram import Update, InputSticker
from PIL.Image import open as img_open

from error import NoEmojiSent
from img_utils import center_crop


@dataclasses.dataclass
class DefaultStickerSize:
    WIDTH = 512
    HEIGHT = 512


async def create_new_sticker(update: Update):
    try:
        emoji_list = update.message.caption.split()
    except AttributeError:
        raise NoEmojiSent()

    photo = update.message.photo[-1]
    image_file = await photo.get_file()
    image_data = bytes(await image_file.download_as_bytearray())
    image_without_bg = remove(img_open(BytesIO(image_data)))
    cropped_pil_image = center_crop(image_without_bg, DefaultStickerSize.WIDTH, DefaultStickerSize.HEIGHT)
    with BytesIO() as img_buffer:
        cropped_pil_image.save(img_buffer, format="png")
        return InputSticker(img_buffer.getvalue(), emoji_list)
