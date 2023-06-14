import logging
import os
import sys
import traceback

import dotenv
from rembg import new_session
from telegram import Update
from telegram import error as tg_err
from telegram.constants import StickerFormat
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from error import NoEmojiSent
from sticker import create_new_sticker

dotenv.load_dotenv()


def load_env_or_exit(key: str) -> str:
    """
    Возвращает значение переменной окружения или завершает выполнение программы с ошибкой.
    :param key: str
    :return: str
    """
    try:
        env_value = os.environ[key]
    except KeyError:
        print(f"[!] Значение `{key}` должно быть указано в файле `.env`.")
        sys.exit(1)
    else:
        return env_value


BOT_TOKEN = load_env_or_exit("BOT_TOKEN")
BOT_NAME = load_env_or_exit("BOT_NAME")
REMBG_AI_MODEL = load_env_or_exit("REMBG_AI_MODEL")

HELP_TEXT = """Приветствую 👋

Это бот для создания стикеров.
Он вырезает фон и создает стикеры из фотографий, которые вы ему отправите.

Чтобы создать стикер из фотки, необходимо проделать несколько простых шагов:
1) Выберите нужную фотографию для отправки.
2) В подписи к фотографии поставьте как минимум один эмодзи, который будет ассоциироваться с этим стикером (можно несколько штук подряд).
3) Дождитесь ответа от бота об успешном добавлении стикера в стикерпак*.

* Для вас будет создан один стикерпак, в который будут добавляться созданные ботом стикеры.
Вы можете удалить этот стикерпак с помощью бота в любой момент командой /delete_sticker_pack.
"""

STICKER_SET_NAME_TMPL = f"for_{{0}}_by_{BOT_NAME}"
DEFAULT_STICKER_SET_TITLE = f"Stickers from @{BOT_NAME}"


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.FileHandler("sticker_bot.log", mode="a"))


async def help_message(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT)


async def add_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user

    if not context.bot_data.get("performance_mode", False):
        rembg_session = new_session(REMBG_AI_MODEL)
    else:
        rembg_session = context.bot_data['rembg_session']

    try:
        new_sticker = await create_new_sticker(update, rembg_session)
    except NoEmojiSent:
        await update.message.reply_text("❌ Отправьте эмодзи вместе с картинкой, чтобы прикрепить его к стикеру.")
    except Exception:
        logger.error(f"❌ Ошибка при создании стикера из отправленной фотографии.\n{traceback.format_exc()}")
        await update.message.reply_text("❌ Возникла ошибка при добавлении стикера в стикерпак, попробуйте позже.")
    else:
        sticker_set_name = STICKER_SET_NAME_TMPL.format(user.username)
        try:
            await update.get_bot().add_sticker_to_set(user.id, sticker_set_name, sticker=new_sticker)
        except tg_err.BadRequest as err:
            if "Stickerset_invalid" in str(err):
                await _create_new_sticker_set(update, sticker_set_name, new_sticker)
            else:
                logger.error(f"❌ Ошибка при добавлении стикера в стикерпак.\n{traceback.format_exc()}")
                await update.message.reply_text(
                    "❌ Возникла ошибка при добавлении стикера в стикерпак, попробуйте позже.")
        except Exception:
            logger.error(f"[!] Ошибка при добавлении стикера в стикерпак.\n{traceback.format_exc()}")
            await update.message.reply_text("❌ Возникла ошибка при добавлении стикера в стикерпак, попробуйте позже.")
        else:
            await update.message.reply_text("✅ Стикер успешно добавлен в стикерпак.\n"
                                            f"https://t.me/addstickers/{sticker_set_name}")


async def delete_sticker_set(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    try:
        success = await update.get_bot().delete_sticker_set(STICKER_SET_NAME_TMPL.format(update.message.from_user.username))
    except Exception:
        logger.error(f"❌ Ошибка при удалении стикерпака.\n{traceback.format_exc()}")
        success = False

    if success:
        await update.message.reply_text("✅ Стикерпак успешно удален.")
    else:
        await update.message.reply_text("❌ Что-то пошло не так, попробуйте позже.")


async def get_user_sticker_set_link(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    sticker_set_name = STICKER_SET_NAME_TMPL.format(update.message.from_user.username)
    await update.message.reply_text(f"https://t.me/addstickers/{sticker_set_name}")


async def _create_new_sticker_set(update: Update, sticker_set_name, first_sticker):
    user = update.message.from_user
    try:
        await update.get_bot().create_new_sticker_set(user.id, sticker_set_name, DEFAULT_STICKER_SET_TITLE,
                                                      stickers=(first_sticker,), sticker_format=StickerFormat.STATIC)
    except tg_err.BadRequest:
        logger.error(f"❌ Ошибка при создании нового стикерпака.\n{traceback.format_exc()}")
    else:
        await update.message.reply_text(f"✅ Ваш новый стикерпак создан, можете добавить его себе по ссылке:\n"
                                        f"https://t.me/addstickers/{sticker_set_name}")


async def _init_persistent_rembg_session(app: Application):
    app.bot_data['rembg_session'] = new_session(REMBG_AI_MODEL)
    app.bot_data['performance_mode'] = True


def start_bot():
    bot = Application.builder().token(BOT_TOKEN).build()

    print(sys.argv)
    if len(sys.argv) == 2 and sys.argv[1] == "--performance-mode":
        bot.post_init = _init_persistent_rembg_session

    bot.add_handler(CommandHandler("help", help_message))
    bot.add_handler(CommandHandler("start", help_message))
    bot.add_handler(CommandHandler("sticker_pack_link", get_user_sticker_set_link))
    bot.add_handler(CommandHandler("delete_sticker_pack", delete_sticker_set))
    bot.add_handler(MessageHandler(filters.PHOTO, add_sticker))

    bot.run_polling()


if __name__ == "__main__":
    start_bot()
