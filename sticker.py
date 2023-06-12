import os
from io import BytesIO

from rembg import remove, new_session
from telegram import Update, InputSticker
from PIL.Image import open as img_open

from error import NoEmojiSent
from img_utils import center_crop


class DefaultStickerSize:
    WIDTH = 512
    HEIGHT = 512


async def create_new_sticker(update: Update, rembg_session):
    try:
        emoji_list = update.message.caption.split()
    except AttributeError:
        raise NoEmojiSent()

    photo = update.message.photo[-1]
    image_file = await photo.get_file()
    image_data = bytes(await image_file.download_as_bytearray())

    with BytesIO(image_data) as bytes_io_image:
        image_without_bg = remove(img_open(bytes_io_image), session=rembg_session)

    cropped_pil_image = center_crop(image_without_bg, DefaultStickerSize.WIDTH, DefaultStickerSize.HEIGHT)

    with BytesIO() as img_buffer:
        cropped_pil_image.save(img_buffer, format="png")
        img_bytes = img_buffer.getvalue()

    return InputSticker(img_bytes, emoji_list)
