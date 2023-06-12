from PIL.Image import Image


def center_crop(img: Image, new_width=None, new_height=None) -> Image:
    width, height = img.size

    if new_width is None:
        new_width = min(width, height)

    if new_height is None:
        new_height = min(width, height)

    left = (width - new_width) / 2
    top = (height - new_height) / 2
    right = (width + new_width) / 2
    bottom = (height + new_height) / 2

    return img.crop((left, top, right, bottom))
