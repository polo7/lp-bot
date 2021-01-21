"""Логика бота: хэндлеры и вспомогательные функции."""

from decimal import Decimal

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters


from bot_settings import (BOT_USAGE_HINT, HELP_HINT, NEW_USAGE_HINT, JOIN_USAGE_HINT, SPEND_USAGE_HINT, 
    WHO_USAGE_HINT, FINISH_USAGE_HINT, DELETE_USAGE_HINT, REPORT_USAGE_HINT)  
from bot_db import (add_new_purchase, add_new_member, show_purchases, add_new_spending, show_members, finish_purchase,
    delete_purchase, purchase_report)


def start(update, context):
    """Запуск бота.
    Команда: /start
    Handler: start_handler
    """
    context.bot.send_message(chat_id=update.effective_chat.id, text=f'{update.effective_user.name}\n{BOT_USAGE_HINT}')

def help_info(update, context):
    """Вывод списка команд бота.
    Команда: /help
    Handler: help_handler
    """
    context.bot.send_message(chat_id=update.effective_chat.id, text=f'{update.effective_user.name}\n{HELP_HINT}')

def new_list(update, context):
    """Создание новой закупки.
    Команда: /new <название закупки>
    Handler: new_handler
    """
    if len(context.args) == 1 and context.args[0].isalnum():
        purchase_name = context.args[0].upper()
        try:
            add_new_purchase(update.effective_chat.id, update.effective_user.id, update.effective_user.username, purchase_name)
            context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f'{update.effective_user.name} Закупка "{purchase_name}" создана.'
            )
        except ValueError:
            context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f'{update.effective_user.name} Закупка "{purchase_name}" уже существует в этой группе.'
            )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f'{update.effective_user.name}\n{NEW_USAGE_HINT}'
        )

def purchase_list(update, context, active):
    """Вывод списка имеющихся закупок.
    Аргумент active принимает значения:
        True - отбор текущих закупок
        False - отбор завершенных закупок
    """
    s = 'текущих' if active else 'завершенных'
    dboutput_text = show_purchases(update.effective_chat.id, active)
    if dboutput_text is not None:
        output_text = f'{update.effective_user.name}\nСписок {s} закупок\nНазвание - потрачено\n'
        output_text = output_text + dboutput_text
    else:
        output_text = f'{update.effective_user.name} {s} закупок в этой группе нет.'
    context.bot.send_message(chat_id=update.effective_chat.id, text=output_text)

def current_purchases(update, context):
    """Вывод текущих закупок.
    Команда: /show
    Handler: show_handler
    """
    purchase_list(update, context, True)

def old_purchases(update, context):
    """Вывод завершенных закупок.
    Команда: /showold
    Handler: show__old_handler
    """
    purchase_list(update, context, False)

def join_purchase(update, context):
    """Присоединение к действующей закупке.
    Команда: /join <название закупки>
    Handler: join_handler
    """
    if len(context.args) == 1:
        purchase_name = context.args[0].upper()
        try:
            # WARNING: В Телеграме username может быть пустым, если регались по номеру.
            # В таком случае получим None и ф-ция ничего не добавит. Это надо как-то учесть в будущем.
            # Использовать Имя Фамилию тоже не вариант:
            # - могут быть не заполнены
            # - могут совпадать с другими пользователями
            add_new_member(update.effective_chat.id, purchase_name, update.effective_user.username)
            context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f'{update.effective_user.name} Теперь вы участвуете в закупке {purchase_name}'
            )
        except ValueError:
            context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f'{update.effective_user.name} Закупки {purchase_name} нет, она закрыта или вы уже в ней.'
            )
    else:
        # Не указано название закупки или лишние аргументы
        context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f'{update.effective_user.name}\n{JOIN_USAGE_HINT}'
        )

def spend(update, context):
    """Внесение суммы потраченного
    Команда: /spend <название закупки> <сумма>
    Handler: spend_handler
    """
    if len(context.args) == 2:
        purchase_name = context.args[0].upper()
        try:
            # amount = round(Decimal(context.args[1]), 2)
            # Decimal работал через раз с ошибкой:
            # bson.errors.InvalidDocument: cannot encode object: Decimal('200.00'), of type: <class 'decimal.Decimal'>
            # Заменил на float
            # ValueError
            amount = round(float(context.args[1]), 2)
            # ValueError
            add_new_spending(update.effective_chat.id, purchase_name, update.effective_user.username, amount)
            
            context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f'{update.effective_user.name}\n{amount} - трата добавлена в закупку {purchase_name}.'
            )
        except ValueError:
            context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f'{update.effective_user.name}\n{SPEND_USAGE_HINT}'
            )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f'{update.effective_user.name}\n{SPEND_USAGE_HINT}'
        )

def who(update, context):
    """Вывод участников закупки.
    Команда: /who <название закупки>
    Handler: who_handler
    """
    if len(context.args) == 1:
        purchase_name = context.args[0].upper()
        members = show_members(update.effective_chat.id, purchase_name)
        if members is None:
            # БД по отбору ничего не нашла, возможно ошибка в названии
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f'{update.effective_user.name}\n{WHO_USAGE_HINT}'
            )
        elif not members:
            # В закупке нет участников и получили пустой словарь
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f'{update.effective_user.name}\nВ закупке {purchase_name} нет участников.'
            )
        else:
            # Нашли по отбору закупку и в ней есть участники => получили словарь ИМЯ-СУММА
            members_output = f'Участники {purchase_name}\nИмя - Потрачено\n'
            for name, spent in members.items():
                members_output = members_output + name + ' - ' + str(spent) + '\n'
            context.bot.send_message(chat_id=update.effective_chat.id, text=members_output)
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f'{update.effective_user.name}\n{WHO_USAGE_HINT}'
        )

def finish(update, context):
    """Закрывает закупку и проводит взаиморасчеты"""
    if len(context.args) == 1:    
        purchase_name = context.args[0].upper()
        try:
            finish_purchase(update.effective_chat.id, purchase_name, update.effective_user.username)
        except ValueError:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f'{update.effective_user.name}\n{FINISH_USAGE_HINT}'
            )
        context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f'{update.effective_user.name}\nЗакупка {purchase_name} завершена.'
            )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{update.effective_user.name}\n{FINISH_USAGE_HINT}'
        )

def delete(update, context):
    """Удаляет закрытую закупку с учетом ее названия и владельца."""
    if len(context.args) == 1:    
        purchase_name = context.args[0].upper()
        try:
            delete_purchase(update.effective_chat.id, purchase_name, update.effective_user.username)
        except ValueError:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f'{update.effective_user.name}\n{DELETE_USAGE_HINT}'
            )
        context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f'{update.effective_user.name}\nЗакупка {purchase_name} удалена.'
            )    
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{update.effective_user.name}\n{DELETE_USAGE_HINT}'
        )

def get_report(update, context):
    if len(context.args) == 1:
        purchase_name = context.args[0].upper()
        file_name = f'Report-{purchase_name}.txt'
        file_text = purchase_report(update.effective_chat.id,purchase_name)
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(file_text)
        context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=open(file_name, 'rb')
        )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{update.effective_user.name}\n{REPORT_USAGE_HINT}'
        )

start_handler = CommandHandler('start', start)
help_handler = CommandHandler('help', help_info)
new_handler = CommandHandler('new', new_list)
show_handler = CommandHandler('show', current_purchases)
show_old_handler = CommandHandler('showold', old_purchases)
join_handler = CommandHandler('join', join_purchase)
spend_handler = CommandHandler('spend', spend)
who_handler = CommandHandler('who', who)
finish_handler = CommandHandler('finish', finish)
delete_handler = CommandHandler('delete', delete)
report_handler = CommandHandler('report', get_report)