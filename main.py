#!/usr/bin/env python
import constants as c
from constants import Buttons
import media_group
import datetime
import json
import time

from aiogram import Bot, Dispatcher, executor, types, utils
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

import mysql.connector


bot = Bot(c.token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class Channels(StatesGroup):
    choose = State()
    place_ad = State()
    media_text = State()
    period_confirm = State()


class Watch_promo(StatesGroup):
    promo = State()


class Make_promo(StatesGroup):
    media_text = State()
    views_confirm = State()


class Make_search_request(StatesGroup):
    keyword = State()
    view = State()


class My_ads(StatesGroup):
    view = State()


class My_promos(StatesGroup):
    view = State()


class Top_up_balance(StatesGroup):
    amount = State()
    pay = State()


class Admin_privileges(StatesGroup):
    user_id = State()
    privileges = State()
    choose_privilege = State()







def inline_keyboard(buttons_set, back_data=None):
    key = types.InlineKeyboardMarkup()
    if isinstance(buttons_set, c.Button):
        key.add(types.InlineKeyboardButton(buttons_set.title, callback_data=buttons_set.data))
    else:
        for title, data in buttons_set:
            key.add(types.InlineKeyboardButton(title, callback_data=data))
    if back_data:
        key.add(types.InlineKeyboardButton(Buttons.back.title, callback_data=back_data))
    return key


def buttons_cortege(button_set):
    return [(x.title, x.data) for x in button_set]


async def _back(callback_query, state, function, *args, state_set=None):
    if callback_query.data == Buttons.back.data:
        await state_set.set() if state_set else await state.finish()
        await function(*args)
        return True


def _media_group_builder(data, caption=True):
    media = types.MediaGroup()
    first = True
    for photo in data['media']['photo']:
        if first:
            first = False
            if caption:
                media.attach_photo(photo, data['media']['caption'])
            else:
                media.attach_photo(photo)
        else:
            media.attach_photo(photo)
    for video in data['media']['video']:
        if first:
            first = False
            if caption:
                media.attach_photo(video, data['media']['caption'])
            else:
                media.attach_photo(video)
        else:
            media.attach_video(video)
    return media


def register_user(user_id, referral=None):
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    if referral:
        insertQuery = "INSERT INTO users (user_id, referral) VALUES (%s, %s)"
        cursor.executemany(insertQuery, [(user_id, referral)])
    else:
        insertQuery = "INSERT INTO users (user_id) VALUES (%s)"
        cursor.execute(insertQuery, [user_id])
    conn.commit()
    conn.close()


async def main_menu(user_id, first_name, delete_message=None, referral=None):
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    selectQuery = "SELECT balance FROM users WHERE user_id=(%s)"
    selectAdminQuery = "SELECT ID FROM admins WHERE user_id=(%s) AND menu_admin=1"
    cursor.execute(selectQuery, [user_id])
    result = cursor.fetchone()
    admin = False
    if result:
        balance = result[0]
        cursor.execute(selectAdminQuery, [user_id])
        admin = cursor.fetchone()
        conn.close()
    else:
        conn.close()
        register_user(user_id, referral)
        balance = 0
    buttons = buttons_cortege(Buttons.main)
    if admin:
        buttons += (Buttons.main_admin.title, Buttons.main_admin.data),
    key = inline_keyboard(buttons)
    await bot.send_message(user_id, f"Здравствуйте, {first_name}.\nНа вашем балансе: {balance} грн.", reply_markup=key)
    if delete_message:
        try: await bot.delete_message(user_id, delete_message)
        except utils.exceptions.MessageCantBeDeleted: pass


async def admin_menu(callback_query, delete_message=None):
    await callback_query.message.answer("Меню администратора", reply_markup=inline_keyboard(buttons_cortege(Buttons.admin), Buttons.back.data))
    if delete_message:
        try: await bot.delete_message(callback_query.message.chat.id, delete_message)
        except utils.exceptions.MessageCantBeDeleted: pass


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    referral = None
    if "ref" in message.text:
        referral = str(message.text)[10:]
        if referral == message.chat.id:
            referral = None
    await main_menu(message.chat.id, message.chat.first_name, referral=referral)


async def choose_channel(callback_query):
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    selectQuery = "SELECT name, ID FROM channels"
    cursor.execute(selectQuery)
    result = cursor.fetchall()
    conn.close()
    buttons = [(name, ID) for name, ID in result]
    key = inline_keyboard(buttons, Buttons.back.data)
    await Channels.choose.set()
    await callback_query.answer()
    await callback_query.message.answer("Выберите интересующий вас канал:", reply_markup=key)
    try: await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    except utils.exceptions.MessageCantBeDeleted: pass


async def proms_choose_mode(callback_query):
    await callback_query.message.answer("Выберите действие:", reply_markup=inline_keyboard(buttons_cortege(Buttons.make_promo), Buttons.back.data))
    try: await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    except utils.exceptions.MessageCantBeDeleted: pass


async def send_promo(callback_query, promo, edit=True, single=False):
    text = promo[1]
    photo = promo[2]
    video = promo[3]
    key = types.InlineKeyboardMarkup()
    but_1 = types.InlineKeyboardButton(Buttons.arrows[0].title, callback_data=Buttons.arrows[0].data)
    but_2 = types.InlineKeyboardButton(Buttons.arrows[1].title, callback_data=Buttons.arrows[1].data)
    if not single:
        key.add(but_1, but_2)
    key.add(types.InlineKeyboardButton(Buttons.watch_promo.title, callback_data=Buttons.watch_promo.data))
    key.add(types.InlineKeyboardButton(Buttons.back.title, callback_data=Buttons.back.data))
    try:
        if photo:
            if edit:
                await bot.edit_message_media(types.InputMediaPhoto(photo, caption=text), callback_query.message.chat.id, callback_query.message.message_id, reply_markup=key)
            else:
                await bot.send_photo(callback_query.message.chat.id, photo, text, reply_markup=key)
                await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
        elif video:
            if edit:
                await bot.edit_message_media(types.InputMediaVideo(video, caption=text), callback_query.message.chat.id, callback_query.message.message_id, reply_markup=key)
            else:
                await bot.send_video(callback_query.message.chat.id, video, caption=text, reply_markup=key)
                await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
        else:
            if edit:
                await bot.edit_message_text(text, callback_query.message.chat.id, callback_query.message.message_id, reply_markup=key)
            else:
                await bot.send_message(callback_query.message.chat.id, text, reply_markup=key)
                await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    except utils.exceptions.MessageNotModified: pass
    except utils.exceptions.BadRequest: await callback_query.answer("Не нажимайте так часто!", show_alert=True)


async def watch_proms(callback_query, state, arrow=None):
    selectLastTimeQuery = "SELECT last_time FROM promo_time WHERE user_id=(%s)"
    selectPromsQuery = "SELECT ID, text, photo, video FROM promo"
    selectViewedQuery = "SELECT promo_id FROM promo_viewed WHERE user_id=(%s)"
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    cursor.execute(selectLastTimeQuery, [callback_query.message.chat.id])
    last_time = cursor.fetchone()
    if last_time:
        difference = time.time() - last_time[0]
        wait_time = 120  # время ожидание между сеансами просмотра рекламы
        if difference < wait_time:
            conn.close()
            minutes, seconds = int(wait_time / 60 - difference / 60), int(60 - difference % 60)
            await callback_query.answer(f"Следующую рекламу можно просмотреть через {minutes} мин. {seconds} сек.")
            return
    cursor.execute(selectPromsQuery)
    promos = cursor.fetchall()
    cursor.execute(selectViewedQuery, [callback_query.message.chat.id])
    viewed = cursor.fetchall()
    conn.close()

    if viewed and promos:
        viewed = {x[0] for x in viewed}
        promos = [x for x in promos if x[0] not in viewed]
    if not promos:
        await state.finish()
        await callback_query.answer("Похоже, больше не осталось рекламы для просмотра!", show_alert=True)
        return
    data = await state.get_data()
    last_promo_id = data.get('promo_id')
    new_promo_id = promos[0][0]
    if last_promo_id is not None:
        last_index = 0
        length = len(promos)
        for num, promo in enumerate(promos):
            if promo[0] == last_promo_id:
                last_index = num
                break
        if arrow == Buttons.arrows[0].data:
            if last_index == 0 or last_index > length - 1:
                new_index = -1
            else:
                new_index = last_index - 1
        else:
            if last_index >= length - 1:
                new_index = 0
            else:
                new_index = last_index + 1
        new_promo_id = promos[new_index][0]
        await send_promo(callback_query, promos[new_index])
    else:
        await Watch_promo.promo.set()
        await send_promo(callback_query, promos[0], edit=False, single=True if len(promos) == 1 else False)
    await state.update_data({'promo_id': new_promo_id, 'start_watch': time.time()})


async def make_promo(callback_query):
    await Make_promo.media_text.set()
    await callback_query.answer()
    await callback_query.message.answer("Отправьте/перешлите фото или видео с подписью")


async def search_choose_option(callback_query):
    await callback_query.message.answer("Выберите действие:", reply_markup=inline_keyboard(buttons_cortege(Buttons.search_request), Buttons.back.data))
    try: await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    except utils.exceptions.MessageCantBeDeleted: pass


async def search_my_requests(callback_query):
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    selectQuery = "SELECT keyword, created FROM search_requests WHERE user_id=(%s)"
    cursor.execute(selectQuery, [callback_query.message.chat.id])
    result = cursor.fetchall()
    conn.close()
    if not result:
        await callback_query.answer("У вас нет ни одного запроса!")
        return
    text = ''
    for req in result:
        text += f"Запрос по фразе: {req[0]}\n" \
                f"Создан: {datetime.datetime.strftime(req[1], '%d.%m.%Y')}\n" \
                f"Активен до: {datetime.datetime.strftime(req[1] + datetime.timedelta(30), '%d.%m.%Y')}\n\n"
    key = types.InlineKeyboardMarkup()
    key.add(types.InlineKeyboardButton(Buttons.back.title, callback_data=Buttons.back.data))
    await callback_query.message.answer(text, reply_markup=key)
    try: await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    except utils.exceptions.MessageCantBeDeleted: pass


async def search_make_requests(callback_query):
    await Make_search_request.keyword.set()
    await callback_query.message.answer("Пожалуйста, введите ключевую фразу")
    try: await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    except utils.exceptions.MessageCantBeDeleted: pass


async def my_ads(callback_query, state):
    data = await state.get_data()
    last_index = data.get('ad_index')
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    selectQuery = "SELECT channel, message_id, ID, created, period FROM ads WHERE user_id=(%s)"
    selectChannelQuery = "SELECT username, name FROM channels WHERE ID=(%s)"
    cursor.execute(selectQuery, [callback_query.message.chat.id])
    result = cursor.fetchall()
    conn.close()
    if not result:
        await callback_query.answer("У вас нет ни одного объявления!")
        return
    key = types.InlineKeyboardMarkup()
    but_1 = types.InlineKeyboardButton(Buttons.arrows[0].title, callback_data=Buttons.arrows[0].data)
    but_2 = types.InlineKeyboardButton(Buttons.arrows[1].title, callback_data=Buttons.arrows[1].data)
    key.add(but_1, but_2)
    key.add(types.InlineKeyboardButton(Buttons.delete_ad.title, callback_data=Buttons.delete_ad.data))
    key.add(types.InlineKeyboardButton(Buttons.back.title, callback_data=Buttons.back.data))

    new_index = 0
    if last_index is not None:
        length = len(result)
        if callback_query.data == Buttons.arrows[0].data:
            if last_index == 0 or last_index > length - 1:
                new_index = -1
            else:
                new_index = last_index - 1
        else:
            if last_index >= length - 1:
                new_index = 0
            else:
                new_index = last_index + 1
    else:
        await My_ads.view.set()

    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    try:
        cursor.execute(selectChannelQuery, [result[new_index][0]])
    except IndexError:
        conn.close()
        await callback_query.answer("Не нажимайте так часто!", show_alert=True)
        return
    channel = cursor.fetchone()
    conn.close()

    await state.update_data({'ad_index': new_index, 'ad_id': result[new_index][2]})
    await bot.forward_message(callback_query.message.chat.id, f'@{channel[0]}', result[new_index][1])
    await callback_query.message.answer(
        f"Объявление №{result[new_index][2]}\n"
        f"Канал: {channel[1]} (@{channel[0]})\n"
        f"Создано: {datetime.datetime.strftime(result[new_index][3], '%d.%m.%Y')}\n"
        f"Длительность: {result[new_index][4]} дней\n"
        f"Активно до: {datetime.datetime.strftime(result[new_index][3] + datetime.timedelta(result[new_index][4]), '%d.%m.%Y')}",
        reply_markup=key)

    try:
        last_message_id = callback_query.message.message_id
        await bot.delete_message(callback_query.message.chat.id, last_message_id)
        await bot.delete_message(callback_query.message.chat.id, last_message_id - 1)
    except utils.exceptions.MessageCantBeDeleted: pass
    except utils.exceptions.MessageToDeleteNotFound: await callback_query.answer("Не нажимайте так часто!", show_alert=True)


async def my_promos(callback_query, state, edit=False):
    data = await state.get_data()
    last_index = data.get('promo_index')
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    selectQuery = "SELECT * FROM promo WHERE user_id=(%s)"
    cursor.execute(selectQuery, [callback_query.message.chat.id])
    result = cursor.fetchall()
    conn.close()
    if not result:
        await callback_query.answer("У вас нет ни одной рекламы!")
        return
    key = types.InlineKeyboardMarkup()
    but_1 = types.InlineKeyboardButton(Buttons.arrows[0].title, callback_data=Buttons.arrows[0].data)
    but_2 = types.InlineKeyboardButton(Buttons.arrows[1].title, callback_data=Buttons.arrows[1].data)
    key.add(but_1, but_2)
    key.add(types.InlineKeyboardButton(Buttons.back.title, callback_data=Buttons.back.data))

    new_index = 0
    if last_index is not None:
        length = len(result)
        if callback_query.data == Buttons.arrows[0].data:
            if last_index == 0 or last_index > length - 1:
                new_index = -1
            else:
                new_index = last_index - 1
        else:
            if last_index >= length - 1:
                new_index = 0
            else:
                new_index = last_index + 1
    else:
        await My_promos.view.set()

    await state.update_data({'promo_index': new_index, 'promo_id': result[new_index][0]})
    text = f"Реклама №{result[new_index][0]}\n"\
           f"Создано: {datetime.datetime.strftime(result[new_index][5], '%d.%m.%Y')}\n"\
           f"Просмотров: {result[new_index][7]}/{result[new_index][6]}\n"\
           f"Одобрено модератором: {'да' if result[new_index][8] else 'нет'}\n"\
           f"Содержимое:\n\n{result[new_index][2]}"
    if edit:
        try:
            if result[new_index][3]:
                await bot.edit_message_media(types.InputMediaPhoto(result[new_index][3], caption=text), callback_query.message.chat.id, callback_query.message.message_id, reply_markup=key)
            elif result[new_index][4]:
                await bot.edit_message_media(types.InputMediaVideo(result[new_index][4], caption=text), callback_query.message.chat.id, callback_query.message.message_id, reply_markup=key)
            else:
                await bot.edit_message_text(text, callback_query.message.chat.id, callback_query.message.message_id, reply_markup=key)
        except utils.exceptions.MessageNotModified: pass
        except utils.exceptions.BadRequest: await callback_query.answer("Не нажимайте так часто!", show_alert=True)
    else:
        if result[new_index][3]:
            await bot.send_photo(callback_query.message.chat.id, result[new_index][3], caption=text, reply_markup=key)
        elif result[new_index][4]:
            await bot.send_video(callback_query.message.chat.id, result[new_index][4], caption=text, reply_markup=key)
        else:
            await bot.send_message(callback_query.message.chat.id, text, reply_markup=key)
        try: await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
        except utils.exceptions.MessageCantBeDeleted: pass


async def referrals(callback_query):
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    countQuery = "SELECT COUNT(ID) FROM users WHERE referral=(%s)"
    selectBonusQuery = "SELECT referral_balance FROM users WHERE user_id=(%s)"
    cursor.execute(countQuery, [callback_query.message.chat.id])
    num = cursor.fetchone()[0]
    bonus = 0
    if num:
        cursor.execute(selectBonusQuery, [callback_query.message.chat.id])
        bonus = cursor.fetchone()[0]
    conn.close()
    await callback_query.message.answer(f"*Ваша реферальная ссылка:*\n"
                                        f"`https://t.me/AdvancedAdsBot?start=ref{callback_query.message.chat.id}`\n"
                                        f"*Приглашено пользователей:* {num}\n*Заработано бонусов:* {bonus} грн.",
                                        parse_mode="Markdown", reply_markup=inline_keyboard(Buttons.back))
    try: await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    except utils.exceptions.MessageCantBeDeleted: pass


async def top_up_balance(callback_query):
    await Top_up_balance.amount.set()
    await callback_query.message.answer("Введите сумму на которую хотите пополнить баланс:")


async def admin_privileges(callback_query):
    await Admin_privileges.user_id.set()
    await callback_query.message.answer("Перешлите мне любое сообщение пользователя", reply_markup=inline_keyboard(Buttons.back))
    try: await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    except utils.exceptions.MessageCantBeDeleted: pass


async def admin_channels(callback_query):
    # ДОБАВИТЬ КАНАЛЫ АДМИНА


async def admin_settings(callback_query):...
async def admin_promo(callback_query):...
async def admin_ads(callback_query):...




@dp.callback_query_handler(lambda callback_query: True)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == Buttons.back.data or callback_query.data == Buttons.back_to_menu.data:
        await main_menu(callback_query.message.chat.id, callback_query.message.chat.first_name, delete_message=callback_query.message.message_id)

    elif callback_query.data == Buttons.main[0].data:
        await choose_channel(callback_query)
    elif callback_query.data == Buttons.main[1].data:
        await proms_choose_mode(callback_query)
    elif callback_query.data == Buttons.main[2].data:
        await search_choose_option(callback_query)
    elif callback_query.data == Buttons.main[3].data:
        await my_ads(callback_query, state)
    elif callback_query.data == Buttons.main[4].data:
        await my_promos(callback_query, state)
    elif callback_query.data == Buttons.main[5].data:
        await referrals(callback_query)
    elif callback_query.data == Buttons.main[6].data:
        await top_up_balance(callback_query)

    elif callback_query.data == Buttons.make_promo[0].data:
        await watch_proms(callback_query, state)
    elif callback_query.data == Buttons.make_promo[1].data:
        await make_promo(callback_query)
    elif callback_query.data == Buttons.search_request[0].data:
        await search_my_requests(callback_query)
    elif callback_query.data == Buttons.search_request[1].data:
        await search_make_requests(callback_query)

    elif callback_query.data == Buttons.main_admin.data:
        await admin_menu(callback_query, callback_query.message.message_id)
    elif callback_query.data == Buttons.admin[0].data:
        await admin_privileges(callback_query)
    elif callback_query.data == Buttons.admin[1].data:
        ...





async def channels_choose(callback_query, state):
    selectQuery = "SELECT name, username FROM channels WHERE ID=(%s)"
    countQuery = "SELECT COUNT(ID) FROM ads WHERE channel=(%s)"
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    cursor.execute(selectQuery, [callback_query.data])
    result = cursor.fetchone()
    cursor.execute(countQuery, [callback_query.data])
    count = cursor.fetchone()[0]
    conn.close()
    await state.update_data({'channel': {'name': result[0], 'username': result[1], 'ID': callback_query.data}})
    await Channels.next()
    key = types.InlineKeyboardMarkup()
    key.add(types.InlineKeyboardButton(Buttons.to_channel[0], url=f'https://t.me/{result[1]}'))
    key.add(types.InlineKeyboardButton(Buttons.to_channel[1], callback_data='place_ad'))
    key.add(types.InlineKeyboardButton(Buttons.back.title, callback_data=Buttons.back.data))
    await callback_query.answer()
    await callback_query.message.answer(f"Имя канала: {result[0]}\nЮзернейм канала: @{result[1]}\nОбъявлений в канале: {count}", reply_markup=key)
    try: await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    except utils.exceptions.MessageCantBeDeleted: pass


@dp.callback_query_handler(lambda callback_query: True, state=Channels.choose)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, main_menu, callback_query.message.chat.id, callback_query.message.chat.first_name, callback_query.message.message_id):
        return
    await channels_choose(callback_query, state)


async def channels_place_ad(callback_query):
    await Channels.next()
    await callback_query.answer()
    await callback_query.message.answer("Отправьте/перешлите фото, видео или альбом с подписью")


@dp.callback_query_handler(lambda callback_query: True, state=Channels.place_ad)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, choose_channel, callback_query):
        return
    if callback_query.data == "place_ad":
        await channels_place_ad(callback_query)


async def get_caption(message, caption):
    if caption:
        if len(caption) < 840:
            return caption
        else:
            await message.reply("Слишком длинный текст, повторите попытку")
    else:
        await message.reply("Медиа без подписи, добавьте подпись")


async def period_and_confirm(message, state, period=None, price=None, callback_query=None):
    data = await state.get_data()
    text = f"Имя канала: {data['channel']['name']}\nЮзернейм канала: @{data['channel']['username']}\n"
    if callback_query:
        await state.update_data({'period': period, 'price': price})
        text += f"Срок размещения: {period} дней\n" \
                f"Размещение с: {datetime.datetime.strftime(datetime.datetime.now(), '%d.%m.%Y')}\n" \
                f"Размещение по: {datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(period), '%d.%m.%Y')}\n" \
                f"Стоимость: {price} грн.\n"
    text += f"Содержимое объявления:\n\n{data['media']['caption']}"

    key = types.InlineKeyboardMarkup()
    if callback_query:
        key.add(types.InlineKeyboardButton(Buttons.make_ad[0].title, callback_data=Buttons.make_ad[0].data))
    but_1 = types.InlineKeyboardButton(Buttons.make_ad[1].title, callback_data=Buttons.make_ad[1].data)
    but_2 = types.InlineKeyboardButton(Buttons.make_ad[2].title, callback_data=Buttons.make_ad[2].data)
    but_3 = types.InlineKeyboardButton(Buttons.make_ad[3].title, callback_data=Buttons.make_ad[3].data)
    but_4 = types.InlineKeyboardButton(Buttons.make_ad[4].title, callback_data=Buttons.make_ad[4].data)
    key.add(but_1, but_2)
    key.add(but_3, but_4)
    key.add(types.InlineKeyboardButton(Buttons.back.title, callback_data=Buttons.back.data))

    if not callback_query:
        await Channels.next()
        if data.get('media_group'):
            if not callback_query and False:  # отключил отправку альбома ботом
                media = _media_group_builder(data, caption=False)
                await bot.send_media_group(message.chat.id, media)
            await bot.send_message(message.chat.id, text + "\n\nАльбом с медиа: загружен", reply_markup=key)
        elif data['media']['photo']:
            await bot.send_photo(message.chat.id, data['media']['photo'], text, reply_markup=key)
        elif data['media']['video']:
            await bot.send_video(message.chat.id, data['media']['video'], caption=text, reply_markup=key)
        else:
            await bot.send_message(message.chat.id, text + "\n\n❗ Медиа файлы отсутствуют ❗", reply_markup=key)
    else:
        try:
            if data['media']['photo'] or data['media']['video']:
                await bot.edit_message_caption(message.chat.id, message.message_id, caption=text, reply_markup=key)
            else:
                await bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=key)
        except utils.exceptions.MessageNotModified: pass
        except utils.exceptions.BadRequest: await callback_query.answer("Не нажимайте так часто!", show_alert=True)


@dp.message_handler(content_types=['text', 'photo', 'video'], state=Channels.media_text)
async def media_text(message: types.Message, state: FSMContext):
    text = photo = video = None
    if message.media_group_id:
        data = await media_group.media_group(message, state)
        if data is None: return
        await state.update_data({'media_group': True})
        text = await get_caption(message, data['media_group']['caption'])
        photo = data['media_group']['photo']
        video = data['media_group']['video']
    elif message.photo:
        text = await get_caption(message, message.caption)
        photo = message.photo[-1].file_id
    elif message.video:
        text = await get_caption(message, message.caption)
        video = message.video.file_id
    elif message.text:
        text = message.text
    if not text:
        return
    await state.update_data({'media': {'caption': text, 'photo': photo, 'video': video}})
    await period_and_confirm(message, state)


async def publish_to_channel(callback_query, state):
    data = await state.get_data()
    selectBalanceQuery = "SELECT balance FROM users WHERE user_id=(%s)"
    selectChannelQuery = "SELECT username FROM channels WHERE ID=(%s)"
    insertQuery = "INSERT INTO ads (user_id, channel, message_id, period) VALUES (%s, %s, %s, %s)"
    updateQuery = "UPDATE users SET balance=(%s) WHERE user_id=(%s)"
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    cursor.execute(selectBalanceQuery, [callback_query.message.chat.id])
    balance = cursor.fetchone()[0]
    cursor.execute(selectChannelQuery, [data['channel']['ID']])
    channel = cursor.fetchone()[0]
    conn.close()
    if balance < data['price']:
        await callback_query.answer(f"На вашем балансе недостаточно средств. Текущая сумма на балансе: {balance} грн.", show_alert=True)
        return

    channel = f'@{channel}'
    if data.get('media_group'):
        media = _media_group_builder(data, caption=True)
        m = await bot.send_media_group(channel, media)
    elif data['media']['photo']:
        m = await bot.send_photo(channel, data['media']['photo'], data['media']['caption'])
    elif data['media']['video']:
        m = await bot.send_video(channel, data['media']['video'], caption=data['media']['caption'])
    else:
        m = await bot.send_message(channel, data['media']['caption'])

    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    cursor.executemany(insertQuery, [(callback_query.message.chat.id, data['channel']['ID'], m.message_id, data['period'])])
    cursor.executemany(updateQuery, [(balance - data['price'], callback_query.message.chat.id)])
    conn.commit()
    conn.close()

    await state.finish()
    await callback_query.message.answer("Ваше объявление создано. Детальнее вы можете посмотреть в меню «Мои объявления»",
                                        reply_markup=inline_keyboard(Buttons.back_to_menu))
    try: await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    except utils.exceptions.MessageCantBeDeleted: pass


@dp.callback_query_handler(lambda callback_query: True, state=Channels.period_confirm)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, choose_channel, callback_query):
        return
    with open('prices.json', 'r') as f:
        price = json.load(f)['periods']
    if callback_query.data in price.keys():
        period = callback_query.data
        await period_and_confirm(callback_query.message, state, int(period), price[period], True)
    elif callback_query.data == Buttons.make_ad[0].data:
        await publish_to_channel(callback_query, state)


@dp.callback_query_handler(lambda callback_query: True, state=Watch_promo.promo)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, proms_choose_mode, callback_query):
        return
    if callback_query.data == Buttons.arrows[0].data or callback_query.data == Buttons.arrows[1].data:
        await watch_proms(callback_query, state, callback_query.data)
    elif callback_query.data == Buttons.watch_promo.data:
        data = await state.get_data()
        difference = time.time() - data['start_watch']
        wait_time = 20
        if difference > wait_time:  # количество секунд на просмотр рекламы
            existsQuery = "SELECT EXISTS (SELECT ID FROM promo_time WHERE user_id=(%s))"
            insertQuery = "INSERT INTO promo_time (user_id, last_time) VALUES (%s, %s)"
            updateQuery = "UPDATE promo_time SET last_time=(%s) WHERE user_id=(%s)"
            insertViewedQuery = "INSERT INTO promo_viewed (user_id, promo_id) VALUES (%s, %s)"
            selectBalanceQuery = "SELECT balance FROM users WHERE user_id=(%s)"
            updateBalanceQuery = "UPDATE users SET balance=(%s) WHERE user_id=(%s)"
            conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
            cursor = conn.cursor(buffered=True)
            cursor.execute(selectBalanceQuery, [callback_query.message.chat.id])
            balance = cursor.fetchone()[0]
            cursor.execute(existsQuery, [callback_query.message.chat.id])
            exists = cursor.fetchone()[0]
            if exists:
                cursor.executemany(updateQuery, [(int(time.time()), callback_query.message.chat.id)])
            else:
                cursor.executemany(insertQuery, [(callback_query.message.chat.id, int(time.time()))])
            cursor.executemany(insertViewedQuery, [(callback_query.message.chat.id, data['promo_id'])])
            cursor.executemany(updateBalanceQuery, [(balance + 1, callback_query.message.chat.id)])
            conn.commit()
            conn.close()
            await state.finish()
            await callback_query.answer("На ваш баланс зачислено 1 грн.", show_alert=True)
            await main_menu(callback_query.message.chat.id, callback_query.message.chat.first_name, callback_query.message.message_id)
        else:
            await callback_query.answer(f"Внимательно прочитайте всё содержимое, вы сможете подтвердить просмотр через {int(wait_time - difference)} сек.", show_alert=True)


async def views_and_confirm(message, state, views=None, price=None, callback_query=False):
    data = await state.get_data()
    text = ''
    if callback_query:
        await state.update_data({'views': views, 'price': price})
        text += f"Просмотров: {views}\n" \
                f"Стоимость: {price} грн.\n"
    text += f"Содержимое рекламы:\n\n{data['media']['caption']}"

    key = types.InlineKeyboardMarkup()
    if callback_query:
        key.add(types.InlineKeyboardButton(Buttons.make_ad[0].title, callback_data=Buttons.make_ad[0].data))
    but_1 = types.InlineKeyboardButton(Buttons.views_count[0].title, callback_data=Buttons.views_count[0].data)
    but_2 = types.InlineKeyboardButton(Buttons.views_count[1].title, callback_data=Buttons.views_count[1].data)
    key.add(but_1, but_2)
    key.add(types.InlineKeyboardButton(Buttons.back.title, callback_data=Buttons.back.data))

    if not callback_query:
        await Make_promo.next()
        if data['media']['photo']:
            await bot.send_photo(message.chat.id, data['media']['photo'], text, reply_markup=key)
        elif data['media']['video']:
            await bot.send_video(message.chat.id, data['media']['video'], caption=text, reply_markup=key)
        else:
            await bot.send_message(message.chat.id, text + "\n\n❗ Медиа файлы отсутствуют ❗", reply_markup=key)
    else:
        await bot.edit_message_caption(message.chat.id, message.message_id, caption=text, reply_markup=key)


@dp.message_handler(content_types=['text', 'photo', 'video'], state=Make_promo.media_text)
async def media_text(message: types.Message, state: FSMContext):
    text = photo = video = None
    if message.photo:
        text = await get_caption(message, message.caption)
        photo = message.photo[-1].file_id
    elif message.video:
        text = await get_caption(message, message.caption)
        video = message.video.file_id
    elif message.text:
        text = message.text
    if not text:
        return
    await state.update_data({'media': {'caption': text, 'photo': photo, 'video': video}})
    await views_and_confirm(message, state)


async def publish_ad(callback_query, state):
    data = await state.get_data()
    selectBalanceQuery = "SELECT balance FROM users WHERE user_id=(%s)"
    insertQuery = "INSERT INTO promo (user_id, text, photo, video, required_views) VALUES (%s, %s, %s, %s, %s)"
    updateQuery = "UPDATE users SET balance=(%s) WHERE user_id=(%s)"
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    cursor.execute(selectBalanceQuery, [callback_query.message.chat.id])
    balance = cursor.fetchone()[0]
    conn.close()
    if balance < data['price']:
        await callback_query.answer(f"На вашем балансе недостаточно средств. Текущая сумма на балансе: {balance} грн.", show_alert=True)
        return

    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    cursor.executemany(insertQuery, [(callback_query.message.chat.id, data['media']['caption'], data['media']['photo'],
                                      data['media']['video'], data['views'])])
    cursor.executemany(updateQuery, [(balance - data['price'], callback_query.message.chat.id)])
    conn.commit()
    conn.close()

    await state.finish()
    await callback_query.message.answer("Ваша реклама создана. Детальнее вы можете посмотреть в меню «Мои рекламы»",
                                        reply_markup=inline_keyboard(Buttons.back_to_menu))
    try: await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    except utils.exceptions.MessageCantBeDeleted: pass


@dp.callback_query_handler(lambda callback_query: True, state=Make_promo.views_confirm)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, proms_choose_mode, callback_query):
        return
    with open('prices.json', 'r') as f:
        price = json.load(f)['views']
    if callback_query.data in price.keys():
        views = callback_query.data
        await views_and_confirm(callback_query.message, state, int(views), price[views], True)
    elif callback_query.data == Buttons.make_ad[0].data:
        await publish_ad(callback_query, state)


@dp.message_handler(content_types=['text'], state=Make_search_request.keyword)
async def search(message: types.Message, state: FSMContext):
    keyword = message.text
    if len(keyword) > 40:
        await message.reply("Слишком длинная фраза, разрешено не более 40 символов")
        return
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    searchQuery = f"SELECT channel, message_id FROM ads WHERE text LIKE '%{keyword}%'"
    selectChannelQuery = "SELECT username FROM channels WHERE ID=(%s)"
    cursor.execute(searchQuery)
    result = cursor.fetchall()
    if result:
        cursor.execute(selectChannelQuery, [result[0][0]])
        channel = cursor.fetchone()[0]
        conn.close()
    else:
        conn.close()
        await state.finish()
        await message.reply(f"По запросу «{keyword}» ничего не найдено")
        await main_menu(message.chat.id, message.chat.first_name)
        return
    await state.update_data({'keyword': keyword, 'ad_index': 0})
    await Make_search_request.next()
    key = types.InlineKeyboardMarkup()
    but_1 = types.InlineKeyboardButton(Buttons.arrows[0].title, callback_data=Buttons.arrows[0].data)
    but_2 = types.InlineKeyboardButton(Buttons.arrows[1].title, callback_data=Buttons.arrows[1].data)
    key.add(but_1, but_2)
    key.add(types.InlineKeyboardButton(Buttons.on_notifications.title, callback_data=Buttons.on_notifications.data))
    key.add(types.InlineKeyboardButton(Buttons.back.title, callback_data=Buttons.back.data))

    await bot.forward_message(message.chat.id, f'@{channel}', result[0][1])
    await message.answer("Выберите действие", reply_markup=key)


@dp.callback_query_handler(lambda callback_query: True, state=Make_search_request.view)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, search_choose_option, callback_query):
        return
    data = await state.get_data()
    if callback_query.data == Buttons.arrows[0].data or callback_query.data == Buttons.arrows[1].data:
        last_index = data['ad_index']
        keyword = data['keyword']
        conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
        cursor = conn.cursor(buffered=True)
        searchQuery = f"SELECT channel, message_id FROM ads WHERE text LIKE '%{keyword}%'"
        selectChannelQuery = "SELECT username FROM channels WHERE ID=(%s)"
        cursor.execute(searchQuery)
        result = cursor.fetchall()
        conn.close()
        key = types.InlineKeyboardMarkup()
        but_1 = types.InlineKeyboardButton(Buttons.arrows[0].title, callback_data=Buttons.arrows[0].data)
        but_2 = types.InlineKeyboardButton(Buttons.arrows[1].title, callback_data=Buttons.arrows[1].data)
        key.add(but_1, but_2)
        key.add(types.InlineKeyboardButton(Buttons.on_notifications.title, callback_data=Buttons.on_notifications.data))
        key.add(types.InlineKeyboardButton(Buttons.back.title, callback_data=Buttons.back.data))

        length = len(result)
        if callback_query.data == Buttons.arrows[0].data:
            if last_index == 0 or last_index > length - 1:
                new_index = -1
            else:
                new_index = last_index - 1
        else:
            if last_index >= length - 1:
                new_index = 0
            else:
                new_index = last_index + 1

        conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
        cursor = conn.cursor(buffered=True)
        cursor.execute(selectChannelQuery, [result[new_index][0]])
        channel = cursor.fetchone()[0]
        conn.close()

        await state.update_data({'ad_index': new_index})
        await bot.forward_message(callback_query.message.chat.id, f'@{channel}', result[new_index][1])
        await callback_query.message.answer("Выберите действие", reply_markup=key)

        try:
            last_message_id = callback_query.message.message_id
            await bot.delete_message(callback_query.message.chat.id, last_message_id)
            await bot.delete_message(callback_query.message.chat.id, last_message_id - 1)
        except utils.exceptions.MessageCantBeDeleted: pass
        except utils.exceptions.MessageToDeleteNotFound: await callback_query.answer("Не нажимайте так часто!", show_alert=True)

    elif callback_query.data == Buttons.on_notifications.data:
        with open('prices.json', 'r') as f:
            price = json.load(f)['notify']
        await callback_query.message.answer(f"Оповещения о новых объявлениях по фразе «{data['keyword']}» будут включены на 30 дней.\nСтоимость: {price} грн.",
                                            reply_markup=inline_keyboard(Buttons.pay_confirm, Buttons.back.data))
        try:
            last_message_id = callback_query.message.message_id
            await bot.delete_message(callback_query.message.chat.id, last_message_id)
            await bot.delete_message(callback_query.message.chat.id, last_message_id - 1)
        except utils.exceptions.MessageCantBeDeleted: pass
        except utils.exceptions.MessageToDeleteNotFound: await callback_query.answer("Не нажимайте так часто!", show_alert=True)
    elif callback_query.data == Buttons.pay_confirm.data:
        with open('prices.json', 'r') as f:
            price = json.load(f)['notify']
        selectBalanceQuery = "SELECT balance FROM users WHERE user_id=(%s)"
        updateBalanceQuery = "UPDATE users SET balance=(%s) WHERE user_id=(%s)"
        insertQuery = "INSERT INTO search_requests (user_id, keyword) VALUES (%s, %s)"
        conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
        cursor = conn.cursor(buffered=True)
        cursor.execute(selectBalanceQuery, [callback_query.message.chat.id])
        balance = cursor.fetchone()[0]
        conn.close()
        if balance < price:
            await callback_query.answer(f"На вашем балансе недостаточно средств. Текущая сумма на балансе: {balance} грн.", show_alert=True)
            return
        conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
        cursor = conn.cursor(buffered=True)
        cursor.executemany(insertQuery, [(callback_query.message.chat.id, data['keyword'])])
        cursor.executemany(updateBalanceQuery, [(balance - price, callback_query.message.chat.id)])
        conn.commit()
        conn.close()
        await state.finish()
        await callback_query.message.answer(f"Оповещения по фразе «{data['keyword']}» подключены на 30 дней. Детальнее вы можете посмотреть в меню «Поиск - Мои запросы»",
                                            reply_markup=inline_keyboard(Buttons.back_to_menu))
        try: await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
        except utils.exceptions.MessageCantBeDeleted: pass


@dp.callback_query_handler(lambda callback_query: True, state=My_ads.view)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, main_menu, callback_query.message.chat.id, callback_query.message.chat.first_name, callback_query.message.message_id):
        try: await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id - 1)
        except utils.exceptions.MessageCantBeDeleted: pass
        except utils.exceptions.MessageToDeleteNotFound: pass
        return
    if callback_query.data == Buttons.arrows[0].data or callback_query.data == Buttons.arrows[1].data:
        await my_ads(callback_query, state)
    elif callback_query.data == Buttons.delete_ad.data:
        data = await state.get_data()
        await callback_query.message.answer(f"Вы уверены что хотите удалить объявление №{data['ad_id']} ?\nДеньги за объявление не будут возвращены.",
                                            reply_markup=inline_keyboard(buttons_cortege(Buttons.confirm_delete_ad)))
        try:
            last_message_id = callback_query.message.message_id
            await bot.delete_message(callback_query.message.chat.id, last_message_id)
            await bot.delete_message(callback_query.message.chat.id, last_message_id - 1)
        except utils.exceptions.MessageCantBeDeleted: pass
        except utils.exceptions.MessageToDeleteNotFound: pass
    elif callback_query.data == Buttons.confirm_delete_ad[0].data:
        data = await state.get_data()
        conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
        cursor = conn.cursor(buffered=True)
        deleteQuery = "DELETE FROM ads WHERE ID=(%s)"
        cursor.execute(deleteQuery, [data['ad_id']])
        conn.commit()
        conn.close()
        await callback_query.answer("Удалено!", show_alert=True)
        await my_ads(callback_query, state)
    elif callback_query.data == Buttons.confirm_delete_ad[1].data:
        await callback_query.answer("Отменено")
        await my_ads(callback_query, state)


@dp.callback_query_handler(lambda callback_query: True, state=My_promos.view)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, main_menu, callback_query.message.chat.id, callback_query.message.chat.first_name, callback_query.message.message_id):
        return
    if callback_query.data == Buttons.arrows[0].data or callback_query.data == Buttons.arrows[1].data:
        await my_promos(callback_query, state, edit=True)


@dp.message_handler(regexp='^\\d+$', state=Top_up_balance.amount)
async def search(message: types.Message, state: FSMContext):
    amount = int(message.text)
    if amount < 1 or amount > 1000000:
        await message.reply("Недействительная сумма!")
        return
    await state.update_data({'amount': amount})
    await Top_up_balance.next()
    key = types.InlineKeyboardMarkup()
    key.add(types.InlineKeyboardButton("Оплатить", url="https://privat24.ua"))
    key.add(types.InlineKeyboardButton(Buttons.back.title, callback_data=Buttons.back.data))
    await message.answer(f"Ваш баланс будет пополнен на {amount} грн. Чтобы оплатить используйте кнопку ниже."
                         "_После оплаты бот автоматически обработает платёж._", parse_mode="Markdown", reply_markup=key)


@dp.callback_query_handler(lambda callback_query: True, state=Top_up_balance.pay)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    # ТУТ НАДО КАК-ТО ОБРАБОТАТЬ ПЛАТЁЖ
    pass


@dp.callback_query_handler(lambda callback_query: True, state=Admin_privileges.user_id)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, admin_menu, callback_query, callback_query.message.message_id):
        return


@dp.message_handler(content_types=types.ContentTypes.ANY, state=Admin_privileges.user_id)
async def search(message: types.Message, state: FSMContext):
    forward = message.forward_from
    if not forward:
        await message.answer("Это не пересланное сообщение!")
        return
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    selectQuery = "SELECT ID FROM users WHERE user_id=(%s)"
    selectAdminQuery = "SELECT menu_admin, menu_priv, priv_add, priv_remove FROM admins WHERE user_id=(%s)"
    cursor.execute(selectQuery, [forward.id])
    db_id = cursor.fetchone()
    if not db_id:
        conn.close()
        await state.finish()
        await message.answer("Пользователь отсутствует в базе", reply_markup=inline_keyboard(Buttons.back))
        return
    cursor.execute(selectAdminQuery, [forward.id])
    result = cursor.fetchone()
    conn.close()
    if not result:
        privileges = " - Отсутствуют"
    else:
        privileges = ''
        if result[0]:
            privileges += " - Доступ к меню «Администратор»\n"
        if result[1]:
            privileges += " - Доступ к меню «Привилегии»\n"
        if result[2]:
            privileges += " - Добавление привилегий\n"
        if result[3]:
            privileges += " - Удаление привилегий\n"
        if not privileges:
            privileges = " - Отсутствуют"
    await Admin_privileges.next()
    await state.update_data({'priv_id': forward.id, 'priv_name': forward.first_name})
    await message.answer(f"ID: {db_id[0]}\nИмя: {forward.first_name}\nЮзернейм: @{forward.username}\nПривилегии:\n{privileges}",
                         reply_markup=inline_keyboard(buttons_cortege(Buttons.add_remove_priv), Buttons.back.data))


@dp.callback_query_handler(lambda callback_query: True, state=Admin_privileges.privileges)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, admin_menu, callback_query, callback_query.message.message_id):
        return
    await Admin_privileges.next()
    data = await state.get_data()
    buttons = buttons_cortege(Buttons.privileges)
    if callback_query.data == Buttons.add_remove_priv[0].data:
        await state.update_data({'priv': 'add'})
        buttons = inline_keyboard([(Buttons.add_remove_all_priv[0].title, Buttons.add_remove_all_priv[0].data)] + buttons)
        verb = 'добавить'
    else:
        await state.update_data({'priv': 'remove'})
        buttons = inline_keyboard([(Buttons.add_remove_all_priv[1].title, Buttons.add_remove_all_priv[1].data)] + buttons)
        verb = 'убрать'
    await callback_query.message.answer(f"Выберите привилегию которую хотите {verb} пользователю {data['priv_name']}", reply_markup=buttons)
    try: await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    except utils.exceptions.MessageCantBeDeleted: pass


@dp.callback_query_handler(lambda callback_query: True, state=Admin_privileges.choose_privilege)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, admin_menu, callback_query, callback_query.message.message_id):
        return
    data = await state.get_data()
    updateQuery = None
    if data['priv'] == 'add':
        if callback_query.data == Buttons.add_remove_all_priv[0].data:
            updateQuery = "UPDATE admins SET menu_admin=1, menu_priv=1, priv_add=1, priv_remove=1 WHERE user_id=(%s)"
        elif callback_query.data == Buttons.privileges[0].data:
            updateQuery = "UPDATE admins SET menu_admin=1 WHERE user_id=(%s)"
        elif callback_query.data == Buttons.privileges[1].data:
            updateQuery = "UPDATE admins SET menu_priv=1 WHERE user_id=(%s)"
        elif callback_query.data == Buttons.privileges[2].data:
            updateQuery = "UPDATE admins SET priv_add=1 WHERE user_id=(%s)"
        elif callback_query.data == Buttons.privileges[3].data:
            updateQuery = "UPDATE admins SET priv_remove=1 WHERE user_id=(%s)"
    elif data['priv'] == 'remove':
        if callback_query.data == Buttons.add_remove_all_priv[1].data:
            updateQuery = "UPDATE admins SET menu_admin=0, menu_priv=0, priv_add=0, priv_remove=0 WHERE user_id=(%s)"
        elif callback_query.data == Buttons.privileges[0].data:
            updateQuery = "UPDATE admins SET menu_admin=0 WHERE user_id=(%s)"
        elif callback_query.data == Buttons.privileges[1].data:
            updateQuery = "UPDATE admins SET menu_priv=0 WHERE user_id=(%s)"
        elif callback_query.data == Buttons.privileges[2].data:
            updateQuery = "UPDATE admins SET priv_add=0 WHERE user_id=(%s)"
        elif callback_query.data == Buttons.privileges[3].data:
            updateQuery = "UPDATE admins SET priv_remove=0 WHERE user_id=(%s)"
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    cursor.execute(updateQuery, [data['priv_id']])
    conn.commit()
    conn.close()
    await state.finish()
    await callback_query.answer("Привилегии успешно изменены", show_alert=True)
    await admin_menu(callback_query, callback_query.message.message_id)





if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
