"""Работа с MongoDB. Функции из хэндлеров собирают и чистят данные, а этот
модуль производит операции непосредственно в БД.
"""

from decimal import Decimal


from pymongo import MongoClient

from bot_settings import MONGODB_LINK, MONGODB_NAME


db = MongoClient(MONGODB_LINK)[MONGODB_NAME]

def add_new_purchase(purchase_group_id, purchase_owner_id, purchase_owner, purchase_name):
# Добавление новой закупки в БД
    if db.purchase_list.find_one({'group_id': purchase_group_id, 'name': purchase_name}) is None:
        db.purchase_list.insert_one(
            {
                'group_id': purchase_group_id,  # какой группе принадлежит закупка
                'owner_id': purchase_owner_id,  # id создателя закупки
                'owner': purchase_owner,        # ник создателя закупки
                'name': purchase_name,          # имя закупки
                'members': {},                  # участники и сумма их расходов
                'members_debts': {},            # взаимозадолженности
                'total': 0,                     # всего потрачено по этой закупке
                'active': True                  # Текущая или закрытая
            }
        )
    else:
        raise ValueError(f'Purchase "{purchase_name}" already exists in this group')

def add_new_member(purchase_group_id, purchase_name, new_member):
# Добавление нового участника закупки в БД
    dboutput = db.purchase_list.find_one(
        {
            'group_id': purchase_group_id, 
            'name': purchase_name, 
            'active': True
        }, 
        projection={'_id': False, 'members': True}
    )
    if (dboutput is not None) and (new_member not in dboutput['members']):
        dboutput['members'].update({new_member: 0})
        db.purchase_list.update_one(
            {
                'group_id': purchase_group_id, 
                'name': purchase_name
            }, 
            {
                '$set': {'members': dboutput['members']}
            }
        )
    else:
        raise ValueError(f'Purchase "{purchase_name}" finished, does not exist or you already here.')

def show_purchases(purchase_group_id, show_active):
# Вывод текущих закупок
    purchase_dboutput = db.purchase_list.find(
        {
            'group_id': purchase_group_id, 
            'active': show_active
        }, 
        projection={'_id': False, 'name': True, 'total': True}
    )
    if purchase_dboutput.count() != 0:
    # .count() is now deprecated => count_documents({}) instead?
        purchases = ''
        for t in purchase_dboutput:
            purchases = purchases + ' - '.join(map(str, t.values())) + '\n'
        return purchases
    else:
        return None

def add_new_spending(purchase_group_id, purchase_name, spender_name, amount):
    # Внесение новой траты
    dboutput = db.purchase_list.find_one(
        {
            'group_id': purchase_group_id, 
            'name': purchase_name, 
            'active': True
        },
        projection={'_id': False, 'members': True}
    )
    if (dboutput is not None) and (spender_name in dboutput['members']):
        dboutput['members'][spender_name] += amount
        db.purchase_list.update_one(
            {
                'group_id': purchase_group_id, 
                'name': purchase_name
            }, 
            {
                '$set': {'members': dboutput['members']}, 
                '$inc': {'total': amount}
            }
        )
    else:
        raise ValueError(f'Purchase "{purchase_name}" does not exist or not active or user "{spender_name}" did not join it')

def show_members(purchase_group_id, purchase_name):
    """Возвращает список участников в виде словаря"""
    dboutput = db.purchase_list.find_one(
        {
            'group_id': purchase_group_id, 
            'name': purchase_name
        },
        projection={'_id': False, 'members': True}
    )
    return dboutput['members'] if dboutput is not None else None

def justify(user_expenses):
    """Принимает словарь {ИМЯ:СУММА}, проводит взаиморасчеты и возвращает словарь в виде 
    {ИМЯ НЕДОПЛАТИВШЕГО: {ИМЯ ПЕРЕПЛАТИВШЕГО: СУММА}}. Другими словами {КТО: {КОМУ: СКОЛЬКО}}.
    """
    # Кто кому и сколько должен
    user_debts = {}
    # Список недоплативших с суммой недоплаты
    user_underpay = {}
    # Список переплативших с суммой переплаты
    user_overpay = {}
    # Всего потрачено = total в БД
    if user_expenses:
        total_exp = sum(user_expenses.values())
        # Ср. арифм. расход на 1 участника
        exp_per_user = total_exp / len(user_expenses)

        for user in user_expenses:
            # Делим на переплативших и недоплативших
            if user_expenses[user] > exp_per_user:
                # Словарь переплативших
                user_overpay.update({user : user_expenses[user] - exp_per_user})
            elif user_expenses[user] < exp_per_user:
                # Словарь недоплативших
                user_underpay.update({user : exp_per_user - user_expenses[user]})
            # Заплативших сколько надо мы не трогаем
        for underpaid in user_underpay:
            for overpaid in user_overpay:
                delta = user_underpay[underpaid] - user_overpay[overpaid]
                # Переплатили меньше, чем недоплата текущего.
                if delta > 0:
                    if underpaid in user_debts:
                        user_debts[underpaid].update({overpaid : delta})
                    else:
                        user_debts.update({underpaid : {overpaid : delta}})
                    user_underpay[underpaid] -= delta
                    # Обнуляем переплату текущего переплатившего, т. к. ему все погасили
                    # Удалить нельзя, т. к. цикл сломается.
                    user_overpay[overpaid] = 0
                    # И переходим к следующему переплатившему, т. к. еще есть недоплата
                # Переплатили больше или столько же, сколько недоплата текущего.
                else:
                    # Заносим должника, кому он отдал и сколько.
                    if underpaid in user_debts:
                        user_debts[underpaid].update({overpaid : user_underpay[underpaid]})
                    else:
                        user_debts.update({underpaid : {overpaid : user_underpay[underpaid]}})
                    # У текущего переплатившего снижаем переплату
                    user_overpay[overpaid] -= user_underpay[underpaid]
                    # Обнуляем недоплату у текущего недоплатившего, т. к. он все отдал.
                    # Удалить нельзя, т. к. цикл сломается.
                    user_underpay[underpaid] = 0
                    # И выходим из FOR, т. к. ему больше отдать нечего.
                    break
    return user_debts

def finish_purchase(purchase_group_id, purchase_name, purchase_owner):
    dboutput = db.purchase_list.find_one(
        {
            'group_id': purchase_group_id,
            'owner': purchase_owner,
            'name': purchase_name,
            'active': True
        },
        projection={'_id': False, 'members': True}
    )
    if dboutput is not None:
        debts = justify(dboutput['members'])
        db.purchase_list.update_one(
            {
                'group_id': purchase_group_id, 
                'name': purchase_name
            }, 
            {
                '$set': {'members_debts': debts, 'active': False}
            }
        )
    else:
        raise ValueError(f'Purchase "{purchase_name}" does not exist or not active or must be closed by {purchase_owner} only.')

def delete_purchase(purchase_group_id, purchase_name, purchase_owner):
    """Удаление документа из БД по названию и владельцу закрытой закупки."""
    dboutput = db.purchase_list.delete_one(
        {
            'group_id': purchase_group_id,
            'owner': purchase_owner,
            'name': purchase_name,
            'active': False
        }
    )
    if dboutput is None:
        raise ValueError(f'Purchase "{purchase_name}" does not exist or still active or must be deleted by {purchase_owner} only.')

def purchase_report(purchase_group_id, purchase_name):
    dboutput = db.purchase_list.find_one(
        {
            'group_id': purchase_group_id,
            'name': purchase_name,
            'active': False
        },
        projection={'_id': False, 'members': True, 'members_debts': True, 'total': True}
    )
    if dboutput is not None:
        total_amount = dboutput['total']
        total_members = len(dboutput['members'])
        if total_members != 0:
            exp_per_member = round(Decimal(total_amount / total_members), 2)
            debts = dboutput['members_debts']

            txt_report = f'\t\tВзаиморасчеты по закупке {purchase_name}\n'
            txt_report += 'Список участников и их покупки:\n'
            for user, amount in dboutput['members'].items():
                txt_report += f'\t{user}: {amount}\n'
            txt_report += 10 * '-' + '\n'
            txt_report += f'Всего потрачено: {total_amount}\n'
            txt_report += f'Всего участников: {total_members}\n'
            txt_report += f'Доля каждого: {exp_per_member}\n'
            txt_report += 10 * '-' + '\n'
            txt_report += 'Взаиморасчеты по закупке:\n'
            for debtor, creditor in debts.items():
                txt_report += f'\t{debtor} должен:\n'
                for user, amount in creditor.items():
                    txt_report += f'\t\t{user}: {amount}\n'
            txt_report += 10 * '-' + '\n'
            txt_report += 'ВСЕМ СПАСИБО ЗА УЧАСТИЕ'
        else:
            txt_report = f'В ЗАКУПКЕ {purchase_name} НЕ БЫЛО АКТИВНОСТИ.'
        return txt_report
    else:
        raise ValueError(f'Purchase "{purchase_name}" does not exist or still active.')
    