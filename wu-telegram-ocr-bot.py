import argparse
import configparser
import os

from telegram import ParseMode
from telegram.utils import helpers


try:
    from PIL import Image
except ImportError:
    import Image
import pytesseract
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters


BOT_VERSION = 0.8
BOT_TEMP = ".tmp_wuocrbot"
bot_config = configparser.ConfigParser()


def on_start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Welcome to *{}* `{}`'.format(
        helpers.escape_markdown(bot_config.get("telegram", "name")),
        BOT_VERSION),
        parse_mode=ParseMode.MARKDOWN)


def on_photo(update, context):
    """Get photo and run tesseract on it"""
    if len(update.message.photo) > 0:
        # Get file_id of the biggest version of photo in message
        file_id = update.message.photo[-1]
    elif update.message.document is not None:
        if hasattr(update.message.document, 'mime_type'):
            supported_mimes = [
                'image/png',
                'image/jpg',
                'image/jpeg',
                'image/pgm',
                'image/x-portable-graymap',
                'image/ppm',
                'image/x-portable-pixmap',
                'image/tiff',
                'image/gif',
                'image/webp'
            ]
            if update.message.document.mime_type in supported_mimes:
                file_id = update.message.document.file_id
            else:
                update.message.reply_text('❌ File type is not supported!',
                                          reply_to_message_id=update.message.message_id)
                return
        else:
            update.message.reply_text('❌ Can you identify file type!',
                                      reply_to_message_id=update.message.message_id)
            return
    else:
        update.message.reply_text('❌ I can not understand you!',
                                  reply_to_message_id=update.message.message_id)
        return
    filepath = os.path.join(BOT_TEMP, '{}_{}'.format(update.message.chat_id, update.message.message_id))
    # Make sure .tmp is exit
    os.makedirs(BOT_TEMP, exist_ok=True)
    # Download Image
    newFile = update.message.bot.get_file(file_id).download(filepath)
    # Send a waiting message
    msg = update.message.reply_text('_Processing..._',
                                    reply_to_message_id=update.message.message_id,
                                    parse_mode=ParseMode.MARKDOWN)
    # Process the image file
    try:
        pytesseract.pytesseract.tesseract_cmd = bot_config.get("tesseract", "path")
        extracted_txt = pytesseract.image_to_string(filepath)
        # Send back extracted text
        msg.edit_text(extracted_txt)
    except RuntimeError as timeout_error:
        # Tesseract processing is terminated
        # Send back error
        msg.edit_text('❌ process timed out!')
    # Remove image file
    try:
        os.remove(filepath)
    except OSError:
        pass


def main():
    """Start the bot."""

    # Parse Arguments
    my_parser = argparse.ArgumentParser(description='WU OCR Telegram Bot')
    my_parser.add_argument('-c', '--config',
                           default='config.ini',
                           type=str,
                           help='Config file')
    args = my_parser.parse_args()

    # Read config file
    bot_config.read(args.config)

    updater = Updater(bot_config.get("telegram", "api"), use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", on_start))

    dp.add_handler(MessageHandler(Filters.photo | Filters.document, on_photo))

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
