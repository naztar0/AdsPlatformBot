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
    selectAdminQuery = "SELECT ID FROM admins WHERE user_id=(%s)"
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
        buttons += buttons_cortege(Buttons.main_admin)
    key = inline_keyboard(buttons)
    await bot.send_message(user_id, f"Здравствуйте, {first_name}.\nНа вашем балансе: {balance} грн.", reply_markup=key)
    if delete_message:
        try: await bot.delete_message(user_id, delete_message)
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
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    selectLastTimeQuery = "SELECT last_time FROM promo_time WHERE user_id=(%s)"
    selectPromsQuery = "SELECT ID, text, photo, video FROM promo"
    selectViewedQuery = "SELECT promo_id FROM promo_viewed WHERE user_id=(%s)"
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
        viewed = [x[0] for x in viewed]
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


async def search_make_request(callback_query): ...
async def my_obs_see(callback_query): ...
async def my_ads(callback_query): ...
async def referrals(callback_query): ...
async def top_up_balance(callback_query): ...



@dp.callback_query_handler(lambda callback_query: True)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == Buttons.main[0].data:
        await choose_channel(callback_query)
    elif callback_query.data == Buttons.main[1].data:
        await proms_choose_mode(callback_query)
    elif callback_query.data == Buttons.main[2].data:
        await search_make_request(callback_query)
    elif callback_query.data == Buttons.main[3].data:
        await my_obs_see(callback_query)
    elif callback_query.data == Buttons.main[4].data:
        await my_ads(callback_query)
    elif callback_query.data == Buttons.main[5].data:
        await referrals(callback_query)
    elif callback_query.data == Buttons.main[6].data:
        await top_up_balance(callback_query)

    elif callback_query.data == Buttons.back.data:
        await main_menu(callback_query.message.chat.id, callback_query.message.chat.first_name, delete_message=callback_query.message.message_id)
    elif callback_query.data == Buttons.back_to_menu.data:
        await main_menu(callback_query.message.chat.id, callback_query.message.chat.first_name, delete_message=callback_query.message.message_id)

    elif callback_query.data == Buttons.make_promo[0].data:
        await watch_proms(callback_query, state)
    elif callback_query.data == Buttons.make_promo[1].data:
        await make_promo(callback_query)



async def channels_choose(callback_query, state):
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    selectQuery = "SELECT name, username FROM channels WHERE ID=(%s)"
    countQuery = "SELECT COUNT(ID) FROM ads WHERE channel=(%s)"
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
        await bot.edit_message_caption(message.chat.id, message.message_id, caption=text, reply_markup=key)


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
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    selectBalanceQuery = "SELECT balance FROM users WHERE user_id=(%s)"
    selectChannelQuery = "SELECT username FROM channels WHERE ID=(%s)"
    insertQuery = "INSERT INTO ads (user_id, channel, message_id, text, photos, videos, period) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    updateQuery = "UPDATE users SET balance=(%s) WHERE user_id=(%s)"
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
    cursor.executemany(insertQuery, [(callback_query.message.chat.id, data['channel']['ID'], m.message_id,
                                      data['media']['caption'], str(data['media']['photo']),
                                      str(data['media']['video']), data['period'])])
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
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    selectBalanceQuery = "SELECT balance FROM users WHERE user_id=(%s)"
    insertQuery = "INSERT INTO promo (user_id, text, photo, video, required_views) VALUES (%s, %s, %s, %s, %s)"
    updateQuery = "UPDATE users SET balance=(%s) WHERE user_id=(%s)"
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





if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)