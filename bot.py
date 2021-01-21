""" Тело бота """

import logging


from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from bot_settings import TOKEN, PROXY
from bot_handlers import (start_handler, help_handler, new_handler, show_handler, show_old_handler, join_handler, 
    spend_handler, who_handler, finish_handler, delete_handler, report_handler)


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO, filename='bot.log')
    
    # Use with PROXY to start from your PC with LearnPython proxy
    updater = Updater(token=TOKEN, request_kwargs=PROXY, use_context=True)

    # Use without PROXY for PythonAnywhere
    # updater = Updater(token=TOKEN, use_context=True)

    logging.info('Бот запущен')

    dp = updater.dispatcher

    dp.add_handler(start_handler)
    dp.add_handler(help_handler)
    dp.add_handler(new_handler)
    dp.add_handler(show_handler)
    dp.add_handler(show_old_handler)
    dp.add_handler(join_handler)
    dp.add_handler(spend_handler)
    dp.add_handler(who_handler)
    dp.add_handler(finish_handler)
    dp.add_handler(delete_handler)
    dp.add_handler(report_handler)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()