#!/usr/bin/env python
import constants as c
from buttons import Buttons
from database_connection import DatabaseConnection
import pay
import media_group
import expired_ads_checker
import get_location_names
import datetime
import json
import time
from asyncio import sleep

from aiogram import Bot, Dispatcher, executor, types, utils
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage


bot = Bot(c.token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class User_private_data(StatesGroup):
    location = State()


class Channels(StatesGroup):
    choose = State()
    place_ad = State()
    media = State()
    text = State()
    period_confirm = State()


class Watch_promo(StatesGroup):
    promo = State()


class Make_promo(StatesGroup):
    media = State()
    text = State()
    views_confirm = State()


class Make_search_request(StatesGroup):
    keyword = State()
    view = State()


class My_ads(StatesGroup):
    view = State()
    edit = State()
    delete = State()


# class My_promos(StatesGroup):
#    view = State()


class Top_up_balance(StatesGroup):
    amount = State()


class Choose_language(StatesGroup):
    choose = State()


class Admin_privileges(StatesGroup):
    user_id = State()
    privileges = State()
    choose_privilege = State()


class Admin_channels(StatesGroup):
    select = State()
    new_prices = State()
    new_channel = State()


class Admin_settings(StatesGroup):
    select = State()
    edit = State()


class Admin_promo(StatesGroup):
    select = State()


class Admin_ads(StatesGroup):
    ad_id = State()
    back_or_delete = State()


@dp.message_handler(regexp=Buttons.regexp_restart)
async def restart(message: types.Message, state: FSMContext):
    await state.finish()
    await main_menu(message.chat.id, message.chat.first_name)


@dp.message_handler(regexp=Buttons.regexp_restart, state=Channels)
async def restart(message: types.Message, state: FSMContext):
    await state.finish()
    await main_menu(message.chat.id, message.chat.first_name)


@dp.message_handler(regexp=Buttons.regexp_restart, state=Watch_promo)
async def restart(message: types.Message, state: FSMContext):
    await state.finish()
    await main_menu(message.chat.id, message.chat.first_name)


@dp.message_handler(regexp=Buttons.regexp_restart, state=Make_promo)
async def restart(message: types.Message, state: FSMContext):
    await state.finish()
    await main_menu(message.chat.id, message.chat.first_name)


@dp.message_handler(regexp=Buttons.regexp_restart, state=Make_search_request)
async def restart(message: types.Message, state: FSMContext):
    await state.finish()
    await main_menu(message.chat.id, message.chat.first_name)


@dp.message_handler(regexp=Buttons.regexp_restart, state=My_ads)
async def restart(message: types.Message, state: FSMContext):
    await state.finish()
    await main_menu(message.chat.id, message.chat.first_name)


# @dp.message_handler(regexp=Buttons.regexp_restart, state=My_promos)
# async def restart(message: types.Message, state: FSMContext):
#    await state.finish()
#    await main_menu(message.chat.id, message.chat.first_name)


@dp.message_handler(regexp=Buttons.regexp_restart, state=Top_up_balance)
async def restart(message: types.Message, state: FSMContext):
    await state.finish()
    await main_menu(message.chat.id, message.chat.first_name)


def inline_keyboard(buttons_set, lang, back_data=False, arrows=False):
    key = types.InlineKeyboardMarkup()
    if arrows:
        but_1 = types.InlineKeyboardButton(Buttons.arrows[0].title, callback_data=Buttons.arrows[0].data)
        but_2 = types.InlineKeyboardButton(Buttons.arrows[1].title, callback_data=Buttons.arrows[1].data)
        key.add(but_1, but_2)
    if isinstance(buttons_set, str):
        key.add(types.InlineKeyboardButton(lang[buttons_set], callback_data=buttons_set))
    else:
        for data in buttons_set:
            key.add(types.InlineKeyboardButton(lang[data], callback_data=data))
    if back_data:
        key.add(types.InlineKeyboardButton(lang[Buttons.back], callback_data=Buttons.back))
    return key


async def _back(callback_query, state, function, *args, state_set=None):
    if callback_query.data == Buttons.back:
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


async def _delete_message(user_id, message_id):
    try:
        await bot.delete_message(user_id, message_id)
    except utils.exceptions.MessageCantBeDeleted:
        return
    except utils.exceptions.MessageToDeleteNotFound:
        return


def language(user_id, registration_important=False):
    def get_lang():
        with DatabaseConnection() as db:
            conn, cursor = db
            selectQuery = "SELECT lang FROM users WHERE user_id=(%s)"
            cursor.execute(selectQuery, [user_id])
            result = cursor.fetchone()
            if result:
                return result[0]
            if registration_important:
                return
            return 'ua'

    def strings():
        lang = get_lang()
        with open('strings.json', encoding='utf-8') as f:
            data = json.load(f)[lang]
        return data
    return strings()


def register_user(user_id, phone, location, referral=None):
    with DatabaseConnection() as db:
        conn, cursor = db
        insertQuery = "INSERT INTO users (user_id, phone, location, referral) VALUES (%s, %s, %s, %s)"
        cursor.executemany(insertQuery, [(user_id, phone, location, referral)])
        conn.commit()


async def request_contact(user_id, first_name):
    key = types.ReplyKeyboardMarkup(resize_keyboard=True)
    key.add(types.KeyboardButton(Buttons.reply_request_contact, request_contact=True))
    await bot.send_message(user_id, f"Доброго дня, {first_name}.\n"
                           "Щоб продовжити, будь-ласка, надайте ваш номер телефону за допомогою кнопки знизу", reply_markup=key)


@dp.message_handler(content_types=['contact'])
async def contact_func(message: types.Message, state: FSMContext):
    with DatabaseConnection() as db:
        conn, cursor = db
        existsQuery = "SELECT EXISTS (SELECT ID FROM users WHERE user_id=(%s))"
        cursor.execute(existsQuery, [message.chat.id])
        exists = cursor.fetchone()[0]
    if exists:
        return
    country_code = str(message.contact.phone_number)[:-9]
    if '380' not in country_code:
        await message.reply("Схоже, номер телефону не український. .")
        return
    await state.update_data({'phone': str(message.contact.phone_number)[-10:]})
    key = types.ReplyKeyboardMarkup(resize_keyboard=True)
    key.add(types.KeyboardButton(Buttons.reply_request_location, request_location=True))
    await User_private_data.location.set()
    await message.answer("Чудово, тепер надайте ваше місцезнаходження за допомогою кнопки знизу", reply_markup=key)


@dp.message_handler(content_types=['location'], state=User_private_data.location)
async def location_func(message: types.Message, state: FSMContext):
    location = get_location_names.get_location(message.location.latitude, message.location.longitude, lang='ru')
    if location is None:
        await message.reply("Помилка розпізнавання місцезнаходження")
        return
    elif location == 0:
        await message.reply("Схоже, ви знаходитесь не в Україні. Використання бота дозволено тільки користувачам з України.")
        return
    data = await state.get_data()
    await state.finish()
    register_user(message.chat.id, data['phone'], location, data.get('referral'))
    await main_menu(message.chat.id, message.chat.first_name)


async def main_menu(user_id, first_name, delete_message=None, referral=None, state=None):
    lang = language(user_id)
    register = False
    with DatabaseConnection() as db:
        conn, cursor = db
        selectQuery = "SELECT balance FROM users WHERE user_id=(%s)"
        selectAdminQuery = "SELECT ID FROM admins WHERE user_id=(%s) AND menu_admin=1"
        cursor.execute(selectQuery, [user_id])
        result = cursor.fetchone()
        if result:
            balance = result[0]
            cursor.execute(selectAdminQuery, [user_id])
            admin = cursor.fetchone()
        else:
            register = True
    if register:
        if referral:
            await state.update_data({'referral': referral})
        await request_contact(user_id, first_name)
        return
    buttons = list(Buttons.main)
    if admin:
        buttons.append(Buttons.main_admin)
    key = types.ReplyKeyboardMarkup(resize_keyboard=True)
    key.add(types.KeyboardButton(lang['buttons']['reply_restart']))
    await bot.send_message(user_id, lang['main_menu'], reply_markup=key)
    await bot.send_message(user_id, lang['main_menu_hello'].format(first_name=first_name, balance=balance), reply_markup=inline_keyboard(buttons, lang['buttons']))
    if delete_message:
        await _delete_message(user_id, delete_message)


async def admin_menu(callback_query, delete_message=None):
    lang = language(callback_query.message.chat.id)
    await callback_query.message.answer(lang['admin_menu'], reply_markup=inline_keyboard(Buttons.admin, lang['buttons'], back_data=True))
    if delete_message:
        await _delete_message(callback_query.message.chat.id, delete_message)


@dp.message_handler(commands=['start'])
async def start(message: types.Message, state: FSMContext):
    referral = None
    if "ref" in message.text:
        referral = str(message.text)[10:]
        if referral == message.chat.id:
            referral = None
    await main_menu(message.chat.id, message.chat.first_name, referral=referral, state=state)


async def check_search_requests(text, message_id, channel):
    selectQuery = f"SELECT user_id, keyword FROM search_requests"
    deleteQuery = "DELETE FROM search_requests WHERE created<(%s)"
    now = datetime.datetime.now()
    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.execute(deleteQuery, [now - datetime.timedelta(30)])
        conn.commit()
        cursor.execute(selectQuery)
        results = cursor.fetchall()
    for result in results:
        keyword = str(result[1]).replace('_', '\\_').replace('*', '\\*').replace('`', '\\`').replace('[', '\\[')
        if result[1] in text:
            try:
                lang = language(result[0])
                await bot.send_message(result[0], lang['new_ad_notification'].format(channel[1:], message_id, keyword), parse_mode="Markdown")
                await sleep(.1)
            except utils.exceptions.BotBlocked: pass
            except utils.exceptions.UserDeactivated: pass
            except utils.exceptions.ChatNotFound: pass


async def choose_channel(callback_query):
    lang = language(callback_query.message.chat.id)
    with DatabaseConnection() as db:
        conn, cursor = db
        selectQuery = "SELECT name, ID FROM channels"
        cursor.execute(selectQuery)
        result = cursor.fetchall()
    key = types.InlineKeyboardMarkup()
    for name, idd in result:
        key.add(types.InlineKeyboardButton(name, callback_data=idd))
    key.add(types.InlineKeyboardButton(lang['buttons'][Buttons.back], callback_data=Buttons.back))
    await Channels.choose.set()
    await callback_query.answer()
    await callback_query.message.answer(lang['choose_channel'], reply_markup=key)
    await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


def delete_invalid_ad_from_db(message_id, channel):
    with DatabaseConnection() as db:
        conn, cursor = db
        deleteQuery = "DELETE FROM ads WHERE message_id=(%s) AND channel=(%s)"
        cursor.execute(deleteQuery, [(message_id, channel)])
        conn.commit()


async def proms_choose_mode(callback_query):
    lang = language(callback_query.message.chat.id)
    await callback_query.message.answer(lang['choose_action'], reply_markup=inline_keyboard(Buttons.make_promo, lang['buttons'], back_data=True))
    await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


async def send_promo(callback_query, promo, edit=True, single=False, key=None, parse_mode=None):
    lang = language(callback_query.message.chat.id)
    text = promo[0]
    photo = promo[1]
    video = promo[2]
    if not key:
        if single:
            key = inline_keyboard(Buttons.watch_promo, lang['buttons'], back_data=True)
        else:
            key = inline_keyboard(Buttons.watch_promo, lang['buttons'], back_data=True, arrows=True)
    try:
        if photo:
            if edit:
                await bot.edit_message_media(types.InputMediaPhoto(photo, caption=text, parse_mode=parse_mode), callback_query.message.chat.id, callback_query.message.message_id, reply_markup=key)
            else:
                await bot.send_photo(callback_query.message.chat.id, photo, text, reply_markup=key, parse_mode=parse_mode)
                await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)
        elif video:
            if edit:
                await bot.edit_message_media(types.InputMediaVideo(video, caption=text, parse_mode=parse_mode), callback_query.message.chat.id, callback_query.message.message_id, reply_markup=key)
            else:
                await bot.send_video(callback_query.message.chat.id, video, caption=text, reply_markup=key, parse_mode=parse_mode)
                await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)
        else:
            if edit:
                await bot.edit_message_text(text, callback_query.message.chat.id, callback_query.message.message_id, reply_markup=key, parse_mode=parse_mode)
            else:
                await bot.send_message(callback_query.message.chat.id, text, reply_markup=key, parse_mode=parse_mode)
                await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    except utils.exceptions.MessageNotModified: await callback_query.answer()
    except utils.exceptions.BadRequest: await callback_query.answer("Не нажимайте так часто!", show_alert=True)


async def watch_proms(callback_query, state, arrow=None):
    lang = language(callback_query.message.chat.id)
    selectLastTimeQuery = "SELECT last_time FROM promo_time WHERE user_id=(%s)"
    selectPromosAllIdQuery = "SELECT ID FROM promo WHERE approved=1"
    selectPromoQuery = "SELECT text, photo, video FROM promo WHERE ID=(%s)"
    selectViewedQuery = "SELECT promo_id FROM promo_viewed WHERE user_id=(%s)"
    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.execute(selectLastTimeQuery, [callback_query.message.chat.id])
        last_time = cursor.fetchone()
        if last_time:
            difference = time.time() - last_time[0]
            wait_time = 120  # время ожидание между сеансами просмотра рекламы
            if difference < wait_time:
                conn.close()
                minutes, seconds = int(wait_time / 60 - difference / 60), int(60 - difference % 60)
                await callback_query.answer(lang['next_promo_watch'].format(minutes=minutes, seconds=seconds))
                return
        cursor.execute(selectPromosAllIdQuery)
        promos_ids = cursor.fetchall()
        cursor.execute(selectViewedQuery, [callback_query.message.chat.id])
        viewed = cursor.fetchall()

    if viewed and promos_ids:
        viewed = {x[0] for x in viewed}
        promos_ids = [x for x in promos_ids if x[0] not in viewed]
    if not promos_ids:
        await state.finish()
        await callback_query.answer(lang['no_promo_to_watch'], show_alert=True)
        return
    data = await state.get_data()
    last_promo_id = data.get('promo_id')
    new_promo_id = promos_ids[0][0]
    if last_promo_id is not None:
        last_index = 0
        length = len(promos_ids)
        for num, promo_id in enumerate(promos_ids):
            if promo_id[0] == last_promo_id:
                last_index = num
                break
        if arrow == Buttons.arrows[0].data:
            if last_index == 0 or last_index > length - 1:
                new_index = length - 1
            else:
                new_index = last_index - 1
        else:
            if last_index >= length - 1:
                new_index = 0
            else:
                new_index = last_index + 1
        new_promo_id = promos_ids[new_index][0]
        single = False
        edit = True
    else:
        await Watch_promo.promo.set()
        single = True if len(promos_ids) == 1 else False
        edit = False
    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.execute(selectPromoQuery, [new_promo_id])
        promo = cursor.fetchone()
    await send_promo(callback_query, promo, edit=edit, single=single)
    await state.update_data({'promo_id': new_promo_id, 'start_watch': time.time()})


async def make_promo(callback_query):
    lang = language(callback_query.message.chat.id)
    await Make_promo.media.set()
    await callback_query.answer()
    await callback_query.message.answer(lang['send_media'])


async def search_choose_option(callback_query):
    lang = language(callback_query.message.chat.id)
    await callback_query.message.answer(lang['choose_action'], reply_markup=inline_keyboard(Buttons.search_request, lang['buttons'], back_data=True))
    await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


async def search_my_requests(callback_query):
    lang = language(callback_query.message.chat.id)
    with DatabaseConnection() as db:
        conn, cursor = db
        selectQuery = "SELECT keyword, created FROM search_requests WHERE user_id=(%s)"
        cursor.execute(selectQuery, [callback_query.message.chat.id])
        result = cursor.fetchall()
    if not result:
        await callback_query.answer(lang['have_not_any_request'])
        return
    text = ''
    for req in result:
        text += lang['my_request'].format(req[0], datetime.datetime.strftime(req[1], '%d.%m.%Y'),
                                          datetime.datetime.strftime(req[1] + datetime.timedelta(30), '%d.%m.%Y'))
    await callback_query.message.answer(text, reply_markup=inline_keyboard(Buttons.back, lang['buttons']))
    await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


async def search_make_requests(callback_query):
    lang = language(callback_query.message.chat.id)
    await Make_search_request.keyword.set()
    await callback_query.message.answer(lang['input_keyword'])
    await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


async def my_ads(callback_query):
    lang = language(callback_query.message.chat.id)
    with DatabaseConnection() as db:
        conn, cursor = db
        selectQuery = "SELECT channel, message_id, ID, created, period FROM ads WHERE user_id=(%s)"
        selectChannelQuery = "SELECT username, name, chat_id FROM channels WHERE ID=(%s)"
        cursor.execute(selectQuery, [callback_query.message.chat.id])
        results = cursor.fetchall()
        if not results:
            conn.close()
            await callback_query.answer(lang['have_not_any_ad'])
            return
        channels = {x[0] for x in results}
        usernames = {}
        for ch in channels:
            cursor.execute(selectChannelQuery, [ch])
            usernames[ch] = cursor.fetchone()

    await callback_query.answer()
    for ad in results:
        format_channel_name = str(usernames[ad[0]][1]).replace('_', '\\_').replace('*', '\\*').replace('`', '\\`').replace('[', '\\[')
        format_channel_username = str(usernames[ad[0]][0]).replace('_', '\\_')
        text = lang['my_ad'].format(usernames[ad[0]][0], ad[1], ad[2], format_channel_name, format_channel_username,
                                    datetime.datetime.strftime(ad[3], '%d.%m.%Y'), ad[4],
                                    datetime.datetime.strftime(ad[3] + datetime.timedelta(ad[4]), '%d.%m.%Y'))
        key = types.InlineKeyboardMarkup()
        key.add(types.InlineKeyboardButton(lang['edit_ad'], callback_data=f'editAd_{usernames[ad[0]][2]}_{ad[1]}'))
        key.add(types.InlineKeyboardButton(lang['delete_ad'], callback_data=f'delAd_{usernames[ad[0]][2]}_{ad[1]}_{ad[2]}'))
        await bot.send_message(callback_query.message.chat.id, text, reply_markup=key, parse_mode="Markdown")
        await sleep(.05)


async def edit_ad(callback_query, state):
    lang = language(callback_query.message.chat.id)
    data = str(callback_query.data).split('_')
    await My_ads.edit.set()
    await state.update_data({'channel': data[1], 'message_id': data[2]})
    await callback_query.answer()
    await callback_query.message.answer(lang['edit_ad_input_text'])


async def delete_ad(callback_query, state):
    lang = language(callback_query.message.chat.id)
    data = str(callback_query.data).split('_')
    await My_ads.delete.set()
    await state.update_data({'channel': data[1], 'message_id': data[2], 'ad_id': data[3]})
    await callback_query.answer()
    await callback_query.message.answer(lang['sure_to_delete_ad'].format(data[3]),
                                        reply_markup=inline_keyboard(Buttons.confirm_delete, lang['buttons']))


async def my_promos(callback_query):
    lang = language(callback_query.message.chat.id)
    with DatabaseConnection() as db:
        conn, cursor = db
        selectQuery = "SELECT * FROM promo WHERE user_id=(%s)"
        cursor.execute(selectQuery, [callback_query.message.chat.id])
        results = cursor.fetchall()
    if not results:
        await callback_query.answer(lang['have_not_any_promo'])
        return
    key = None  # If will be wish to make edit/delete buttons in future :)

    await callback_query.answer()
    for promo in results:
        text = lang['my_promo'].format(promo[0], datetime.datetime.strftime(promo[5], '%d.%m.%Y'),
                                       promo[7], promo[6], '+' if promo[9] else '-', promo[2])
        if promo[3]:
            await bot.send_photo(callback_query.message.chat.id, promo[3], caption=text, reply_markup=key)
        elif promo[4]:
            await bot.send_video(callback_query.message.chat.id, promo[4], caption=text, reply_markup=key)
        else:
            await bot.send_message(callback_query.message.chat.id, text, reply_markup=key)
        await sleep(.05)


async def referrals(callback_query):
    lang = language(callback_query.message.chat.id)
    with DatabaseConnection() as db:
        conn, cursor = db
        countQuery = "SELECT COUNT(ID) FROM users WHERE referral=(%s)"
        selectBonusQuery = "SELECT referral_balance FROM users WHERE user_id=(%s)"
        cursor.execute(countQuery, [callback_query.message.chat.id])
        num = cursor.fetchone()[0]
        bonus = 0
        if num:
            cursor.execute(selectBonusQuery, [callback_query.message.chat.id])
            bonus = cursor.fetchone()[0]
    await callback_query.message.answer(lang['referral'].format(num=num, bonus=bonus),
                                        parse_mode="Markdown", reply_markup=inline_keyboard(Buttons.back, lang['buttons']))
    await callback_query.message.answer(f"https://t.me/AdvancedAdsBot?start=ref{callback_query.message.chat.id}")
    await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


async def top_up_balance(callback_query):
    lang = language(callback_query.message.chat.id)
    await Top_up_balance.amount.set()
    await callback_query.message.answer(lang['input_amount'])


async def change_language(callback_query):
    lang = language(callback_query.message.chat.id)
    key = types.InlineKeyboardMarkup()
    for title, data in Buttons.languages:
        key.add(types.InlineKeyboardButton(title, callback_data=data))
    key.add(types.InlineKeyboardButton(lang['buttons'][Buttons.back], callback_data=Buttons.back))
    await Choose_language.choose.set()
    await callback_query.message.answer(lang['choose_language'], reply_markup=key)
    await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


async def admin_privileges(callback_query):
    lang = language(callback_query.message.chat.id)
    await Admin_privileges.user_id.set()
    await callback_query.message.answer(lang['forward_user_message'], reply_markup=inline_keyboard(Buttons.back, lang['buttons']))
    await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


async def admin_channels(callback_query, state):
    lang = language(callback_query.message.chat.id)
    data = await state.get_data()
    selectQuery = "SELECT * FROM channels LIMIT 1 OFFSET %s"
    countQuery = "SELECT COUNT(ID) FROM channels"
    first = False
    last_id = data.get('index')
    if last_id is not None:
        count = data['count']
        if callback_query.data == Buttons.arrows[0].data:
            next_id = last_id - 1
            if next_id < 0:
                next_id = count - 1
        else:
            next_id = last_id + 1
            if next_id >= count:
                next_id = 0
    else:
        next_id = 0
        first = True
    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.execute(selectQuery, [next_id])
        channel = cursor.fetchone()
        if first:
            cursor.execute(countQuery)
            count = cursor.fetchone()[0]

    text = lang['admin_channel'].format(channel[0], channel[2], channel[1], count, channel[3], channel[4], channel[5], channel[6])
    key = inline_keyboard(Buttons.admin_channels, lang['buttons'], back_data=True, arrows=True)
    await state.update_data({'index': next_id, 'channel_id': channel[0], 'count': count})
    if last_id is None:
        await Admin_channels.select.set()
        await callback_query.message.answer(text, reply_markup=key)
        await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    else:
        try:
            await bot.edit_message_text(text, callback_query.message.chat.id, callback_query.message.message_id, reply_markup=key)
        except utils.exceptions.MessageNotModified: await callback_query.answer()
        except utils.exceptions.BadRequest: await callback_query.answer(lang['warning_frequently_click'], show_alert=True)


async def admin_settings(callback_query):
    lang = language(callback_query.message.chat.id)
    with open('prices.json', 'r') as f:
        data = json.load(f)
    key = types.InlineKeyboardMarkup(6)
    but_1 = types.InlineKeyboardButton(Buttons.admin_settings[0].title, callback_data=Buttons.admin_settings[0].data)
    but_2 = types.InlineKeyboardButton(Buttons.admin_settings[1].title, callback_data=Buttons.admin_settings[1].data)
    but_3 = types.InlineKeyboardButton(Buttons.admin_settings[2].title, callback_data=Buttons.admin_settings[2].data)
    but_4 = types.InlineKeyboardButton(Buttons.admin_settings[3].title, callback_data=Buttons.admin_settings[3].data)
    but_5 = types.InlineKeyboardButton(Buttons.admin_settings[4].title, callback_data=Buttons.admin_settings[4].data)
    but_6 = types.InlineKeyboardButton(Buttons.admin_settings[5].title, callback_data=Buttons.admin_settings[5].data)
    key.add(but_1, but_2, but_3, but_4, but_5, but_6)
    key.add(types.InlineKeyboardButton(lang['buttons'][Buttons.back], callback_data=Buttons.back))
    await Admin_settings.select.set()
    await callback_query.message.answer(lang['admin_settings'].format(**data), reply_markup=key)
    await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


async def admin_promo(callback_query, state):
    lang = language(callback_query.message.chat.id)
    data = await state.get_data()
    selectQuery = "SELECT * FROM promo WHERE ID=(%s)"
    countAllQuery = "SELECT COUNT(ID) FROM promo WHERE approved=0"
    selectPromosQuery = "SELECT ID FROM promo WHERE approved=0"
    last_id = data.get('promo_id')
    with DatabaseConnection() as db:
        conn, cursor = db
        if last_id:
            last_index = data['promo_index']
            array = data['promo_array']
            length = len(array)
            if callback_query.data == Buttons.arrows[0].data:
                next_index = last_index - 1
                if next_index < 0:
                    next_index = length - 1
            else:
                next_index = last_index + 1
                if length <= next_index:
                    next_index = 0
            next_id = array[next_index]
            count = None
        else:
            cursor.execute(selectPromosQuery)
            promos_ids = cursor.fetchall()
            if not promos_ids:
                conn.close()
                await callback_query.answer(lang['have_not_any_unapproved'])
                return
            array = [x[0] for x in promos_ids]
            length = len(array)
            next_index = 0
            next_id = array[0]
            cursor.execute(countAllQuery)
            count = cursor.fetchone()[0]
        cursor.execute(selectQuery, [next_id])
        promo = cursor.fetchone()

    format_text = str(promo[2]).replace('_', '\\_').replace('*', '\\*').replace('`', '\\`').replace('[', '\\[')
    text = lang['admin_promo'].format(next_index + 1, length, promo[0], promo[1],
                                      datetime.datetime.strftime(promo[5], '%d.%m.%Y'),
                                      promo[7], promo[6], promo[8], format_text)
    to_send = [text, promo[3], promo[4]]
    await state.update_data({'promo_index': next_index, 'promo_id': next_id, 'promo_user': promo[1], 'promo_price': promo[8]})
    if not last_id:
        await state.update_data({'promo_array': array, 'promo_count': count})
        await Admin_promo.select.set()
        if length == 1:
            key = inline_keyboard(Buttons.admin_promo, lang['buttons'], back_data=True)
            await send_promo(callback_query, to_send, edit=False, single=True, key=key, parse_mode="Markdown")
        else:
            key = inline_keyboard(Buttons.admin_promo, lang['buttons'], back_data=True, arrows=True)
            await send_promo(callback_query, to_send, edit=False, key=key, parse_mode="Markdown")
    else:
        key = inline_keyboard(Buttons.admin_promo, lang['buttons'], back_data=True, arrows=True)
        await send_promo(callback_query, to_send, key=key, parse_mode="Markdown")


async def admin_ads(callback_query):
    lang = language(callback_query.message.chat.id)
    await Admin_ads.ad_id.set()
    await callback_query.message.answer(lang['input_ad_id'], reply_markup=inline_keyboard(Buttons.back, lang['buttons']))
    await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


async def report_send(callback_query):
    lang = language(callback_query.message.chat.id)
    message_id = callback_query.message.message_id
    selectChannelQuery = "SELECT ID FROM channels WHERE username=(%s)"
    selectExistsUserQuery = "SELECT EXISTS (SELECT ID FROM reports WHERE channel=(%s) AND message_id=(%s) AND user_id=(%s))"
    selectQuery = "SELECT COUNT(ID) FROM reports WHERE channel=(%s) AND message_id=(%s)"
    insertQuery = "INSERT INTO reports (channel, message_id, user_id) VALUES (%s, %s, %s)"
    deleteQuery = "DELETE FROM ads WHERE channel=(%s) AND message_id=(%s)"
    selectAdmins = "SELECT user_id FROM admins WHERE menu_admin=1"
    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.execute(selectChannelQuery, [callback_query.message.chat.username])
        channel = cursor.fetchone()[0]
        cursor.executemany(selectExistsUserQuery, [(channel, message_id, callback_query.from_user.id)])
        exists = cursor.fetchone()[0]
        if exists:  # exists for RELEASE, False for DEBUG
            conn.close()
            await callback_query.answer("Вы уже подали жалобу!", show_alert=True)
            return
        cursor.executemany(selectQuery, [(channel, message_id)])
        rep_num = cursor.fetchone()[0]
        admins = None
        with open('prices.json', 'r') as f:
            ban = json.load(f)['ban']
        ban_admin = ban[0]  # количество для уведомления админа
        ban_auto = ban[1]  # количество для автоматического удаления
        if rep_num < ban_admin or ban_auto > rep_num > ban_admin:  # количество игнорирования
            cursor.executemany(insertQuery, [(channel, message_id, callback_query.from_user.id)])
        elif rep_num == ban_admin:
            cursor.executemany(insertQuery, [(channel, message_id, callback_query.from_user.id)])
            cursor.execute(selectAdmins)
            admins = cursor.fetchall()
        elif rep_num == ban_auto:
            cursor.executemany(deleteQuery, [(channel, message_id)])
            conn.commit()
            conn.close()
            await _delete_message(callback_query.message.chat.id, message_id)
            return
        conn.commit()
    await callback_query.answer("Жалоба на объявление отправлена", show_alert=True)
    if admins:
        key = types.InlineKeyboardMarkup()
        but_1 = types.InlineKeyboardButton('❌🗑 Delete', callback_data=f'delRep_{channel}_{callback_query.message.chat.id}_{message_id}')
        but_2 = types.InlineKeyboardButton('✅ Keep', callback_data='delRep')
        key.add(but_1, but_2)
        for admin in admins:
            lang2 = language(admin[0])
            await bot.forward_message(admin[0], callback_query.message.chat.id, message_id)
            await bot.send_message(admin[0], lang2['reports_got'], reply_markup=key)
            await sleep(.1)


async def admin_delete_message(callback_query):
    lang = language(callback_query.message.chat.id)
    data = str(callback_query.data).split('_')
    if len(data) == 1:
        await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)
        await callback_query.answer(lang['kept'])
        return
    channel, channel_id, message_id = data[1], int(data[2]), int(data[3])
    success = False
    try:
        await bot.delete_message(channel_id, message_id)
        success = True
    except utils.exceptions.MessageCantBeDeleted:
        await callback_query.answer(lang['warning_can_not_delete_ad'], show_alert=True)
    except utils.exceptions.MessageToDeleteNotFound:
        await callback_query.answer(lang['warning_ad_already_deleted'])
        await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    with DatabaseConnection() as db:
        conn, cursor = db
        deleteQuery = "DELETE FROM ads WHERE channel=(%s) AND message_id=(%s)"
        cursor.executemany(deleteQuery, [(channel, message_id)])
        conn.commit()
    if success:
        await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)
        await callback_query.answer(lang['deleted'])




@dp.callback_query_handler(lambda callback_query: True)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    callback_query_data = callback_query.data
    if callback_query_data == Buttons.back or callback_query_data == Buttons.back_to_menu:
        await main_menu(callback_query.message.chat.id, callback_query.message.chat.first_name, delete_message=callback_query.message.message_id)

    elif callback_query_data == Buttons.main[0]:
        await choose_channel(callback_query)
    elif callback_query_data == Buttons.main[1]:
        await proms_choose_mode(callback_query)
    elif callback_query_data == Buttons.main[2]:
        await search_choose_option(callback_query)
    elif callback_query_data == Buttons.main[3]:
        await my_ads(callback_query)
    elif callback_query_data == Buttons.main[4]:
        await my_promos(callback_query)
    elif callback_query_data == Buttons.main[5]:
        await referrals(callback_query)
    elif callback_query_data == Buttons.main[6]:
        await top_up_balance(callback_query)
    elif callback_query_data == Buttons.main[7]:
        await change_language(callback_query)

    elif callback_query_data == Buttons.make_promo[0]:
        await watch_proms(callback_query, state)
    elif callback_query_data == Buttons.make_promo[1]:
        await make_promo(callback_query)
    elif callback_query_data == Buttons.search_request[0]:
        await search_my_requests(callback_query)
    elif callback_query_data == Buttons.search_request[1]:
        await search_make_requests(callback_query)

    elif callback_query_data == Buttons.main_admin:
        await admin_menu(callback_query, callback_query.message.message_id)
    elif callback_query_data == Buttons.admin[0]:
        await admin_privileges(callback_query)
    elif callback_query_data == Buttons.admin[1]:
        await admin_channels(callback_query, state)
    elif callback_query_data == Buttons.admin[2]:
        await admin_settings(callback_query)
    elif callback_query_data == Buttons.admin[3]:
        await admin_promo(callback_query, state)
    elif callback_query_data == Buttons.admin[4]:
        await admin_ads(callback_query)

    elif callback_query_data == Buttons.report.data:
        await report_send(callback_query)
    elif callback_query_data[:6] == 'delRep':
        await admin_delete_message(callback_query)

    elif callback_query_data[:6] == 'editAd':
        await edit_ad(callback_query, state)
    elif callback_query_data[:5] == 'delAd':
        await delete_ad(callback_query, state)





async def channels_choose(callback_query, state):
    lang = language(callback_query.message.chat.id)
    selectQuery = "SELECT * FROM channels WHERE ID=(%s)"
    countQuery = "SELECT COUNT(ID) FROM ads WHERE channel=(%s)"
    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.execute(selectQuery, [callback_query.data])
        result = cursor.fetchone()
        cursor.execute(countQuery, [callback_query.data])
        count = cursor.fetchone()[0]
    await state.update_data({'channel': {'name': result[2], 'username': result[1], 'ID': callback_query.data,
                                         'price_1': result[3], 'price_7': result[4], 'price_14': result[5], 'price_30': result[6]}})
    await Channels.next()
    key = types.InlineKeyboardMarkup()
    key.add(types.InlineKeyboardButton(lang['buttons']['go_to_channel'], url=f'https://t.me/{result[1]}'))
    key.add(types.InlineKeyboardButton(lang['buttons']['place_ad'], callback_data='place_ad'))
    key.add(types.InlineKeyboardButton(lang['buttons'][Buttons.back], callback_data=Buttons.back))
    await callback_query.answer()
    await callback_query.message.answer(lang['channel_info'].format(result[2], result[1], count), reply_markup=key)
    await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


@dp.callback_query_handler(lambda callback_query: True, state=Channels.choose)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, main_menu, callback_query.message.chat.id, callback_query.message.chat.first_name, callback_query.message.message_id):
        return
    await channels_choose(callback_query, state)


async def channels_place_ad(callback_query):
    lang = language(callback_query.message.chat.id)
    await Channels.next()
    await callback_query.answer()
    await callback_query.message.answer(lang['send_media_album'])


@dp.callback_query_handler(lambda callback_query: True, state=Channels.place_ad)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, choose_channel, callback_query):
        return
    if callback_query.data == "place_ad":
        await channels_place_ad(callback_query)


async def get_caption(message, caption, lang):
    if caption:
        if len(caption) < 840:
            return caption
        else:
            await message.reply(lang['warning_text_too_long'])
    else:
        await message.reply(lang['warning_no_caption'])


async def period_and_confirm(message, state, period=None, callback_query=None):
    lang = language(message.chat.id)
    data = await state.get_data()
    text = lang['channel_info_short'].format(data['channel']['name'], data['channel']['username'])
    if callback_query:
        await state.update_data({'period': period, 'price': data['channel'][f'price_{period}']})
        text += lang['make_ad_info'].format(period, datetime.datetime.strftime(datetime.datetime.now(), '%d.%m.%Y'),
                                            datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(period), '%d.%m.%Y'),
                                            data['channel'][f'price_{period}'])
    text += lang['ad_content'].format(data['media']['caption'])

    key = types.InlineKeyboardMarkup()
    if callback_query:
        key.add(types.InlineKeyboardButton(lang['buttons'][Buttons.make_ad[0]], callback_data=Buttons.make_ad[0]))
    but_1 = types.InlineKeyboardButton(lang['buttons'][Buttons.make_ad[1]], callback_data=Buttons.make_ad[1])
    but_2 = types.InlineKeyboardButton(lang['buttons'][Buttons.make_ad[2]], callback_data=Buttons.make_ad[2])
    but_3 = types.InlineKeyboardButton(lang['buttons'][Buttons.make_ad[3]], callback_data=Buttons.make_ad[3])
    but_4 = types.InlineKeyboardButton(lang['buttons'][Buttons.make_ad[4]], callback_data=Buttons.make_ad[4])
    key.add(but_1, but_2)
    key.add(but_3, but_4)
    key.add(types.InlineKeyboardButton(lang['buttons'][Buttons.back], callback_data=Buttons.back))

    is_media_group = data.get('media_group')
    if not callback_query:
        await Channels.next()
        if is_media_group:
            if not callback_query and False:  # отключен предпросмотр медиа
                media = _media_group_builder(data, caption=False)
                await bot.send_media_group(message.chat.id, media)
            await bot.send_message(message.chat.id, text + lang['album_uploaded'], reply_markup=key)
        elif data['media']['photo']:
            await bot.send_photo(message.chat.id, data['media']['photo'], text, reply_markup=key)
        elif data['media']['video']:
            await bot.send_video(message.chat.id, data['media']['video'], caption=text, reply_markup=key)
        else:
            await bot.send_message(message.chat.id, text + lang['no_media'], reply_markup=key)
    else:
        try:
            if (data['media']['photo'] or data['media']['video']) and not is_media_group:
                await bot.edit_message_caption(message.chat.id, message.message_id, caption=text, reply_markup=key)
            else:
                await bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=key)
        except utils.exceptions.MessageNotModified: await callback_query.answer()
        except utils.exceptions.BadRequest: await callback_query.answer(lang['warning_frequently_click'], show_alert=True)


@dp.message_handler(content_types=['photo', 'video'], state=Channels.media)
async def media_text(message: types.Message, state: FSMContext):
    lang = language(message.chat.id)
    photo = video = None
    if message.media_group_id:
        data = await media_group.media_group(message, state)
        if data is None: return
        await state.update_data({'media_group': True})
        photo = data['media_group']['photo']
        video = data['media_group']['video']
    elif message.photo:
        photo = message.photo[-1].file_id
    elif message.video:
        video = message.video.file_id
    await state.update_data({'media': {'photo': photo, 'video': video}})
    await Channels.next()
    await message.answer(lang['send_ad_text'])


@dp.message_handler(content_types=['text'], state=Channels.text)
async def media_text(message: types.Message, state: FSMContext):
    lang = language(message.chat.id)
    text = await get_caption(message, message.text, lang)
    if not text:
        return
    data = await state.get_data()
    await state.update_data({'media': {'photo': data['media']['photo'], 'video': data['media']['video'], 'caption': text}})
    await period_and_confirm(message, state)


async def publish_to_channel(callback_query, state):
    lang = language(callback_query.message.chat.id)
    data = await state.get_data()
    selectQuery = "SELECT users.balance, channels.username FROM users, channels WHERE users.user_id=(%s) AND channels.ID=(%s)"
    insertQuery = "INSERT INTO ads (user_id, channel, message_id, period, expire, text) VALUES (%s, %s, %s, %s, %s, %s)"
    updateQuery = "UPDATE users SET balance=(%s) WHERE user_id=(%s)"
    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.executemany(selectQuery, [(callback_query.message.chat.id, data['channel']['ID'])])
        result = cursor.fetchone()
    balance, channel = result
    if balance < data['price']:
        await callback_query.answer(lang['warning_not_enough_money'].format(balance=balance), show_alert=True)
        return

    key = types.InlineKeyboardMarkup()
    key.add(types.InlineKeyboardButton(Buttons.report.title, callback_data=Buttons.report.data))
    channel = f'@{channel}'
    if data.get('media_group'):
        media = _media_group_builder(data, caption=True)
        n = await bot.send_media_group(c.media_channel_at, media)
        m = await bot.send_message(channel, f"[👉 Нажмите для просмотра всех медиа 👈](https://t.me/{c.media_channel}/{n[0].message_id})",
                                   parse_mode="Markdown", reply_markup=key)
    else:
        if data['media']['photo']:
            m = await bot.send_photo(channel, data['media']['photo'], data['media']['caption'], reply_markup=key)
        elif data['media']['video']:
            m = await bot.send_video(channel, data['media']['video'], caption=data['media']['caption'], reply_markup=key)
        else:
            m = await bot.send_message(channel, data['media']['caption'], reply_markup=key)

    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.executemany(insertQuery, [(callback_query.message.chat.id, data['channel']['ID'], m.message_id, data['period'],
                                         datetime.datetime.now() + datetime.timedelta(data['period']), data['media']['caption'])])
        cursor.executemany(updateQuery, [(balance - data['price'], callback_query.message.chat.id)])
        conn.commit()

    await state.finish()
    await callback_query.message.answer(lang['ad_created'], reply_markup=inline_keyboard(Buttons.back_to_menu, lang['buttons']))
    await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    await check_search_requests(data['media']['caption'], m.message_id, channel)


@dp.callback_query_handler(lambda callback_query: True, state=Channels.period_confirm)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, choose_channel, callback_query):
        return
    if callback_query.data in {'1', '7', '14', '30'}:
        period = int(callback_query.data)
        await period_and_confirm(callback_query.message, state, period, callback_query)
    elif callback_query.data == Buttons.make_ad[0]:
        await publish_to_channel(callback_query, state)


@dp.callback_query_handler(lambda callback_query: True, state=Watch_promo.promo)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, proms_choose_mode, callback_query):
        return
    if callback_query.data == Buttons.arrows[0].data or callback_query.data == Buttons.arrows[1].data:
        await watch_proms(callback_query, state, callback_query.data)
    elif callback_query.data == Buttons.watch_promo:
        lang = language(callback_query.message.chat.id)
        data = await state.get_data()
        difference = time.time() - data['start_watch']
        wait_time = 20
        if difference > wait_time:  # количество секунд на просмотр рекламы
            with open('prices.json', 'r') as f:
                reward = json.load(f)['ad_view']
            existsQuery = "SELECT EXISTS (SELECT ID FROM promo_time WHERE user_id=(%s))"
            selectQuery = "SELECT users.balance, promo.views FROM users, promo WHERE users.user_id=(%s) AND promo.ID=(%s)"
            insertQuery = "INSERT INTO promo_time (user_id, last_time) VALUES (%s, %s)"
            insertViewedQuery = "INSERT INTO promo_viewed (user_id, promo_id) VALUES (%s, %s)"
            updateQuery = "UPDATE promo_time SET last_time=(%s) WHERE user_id=(%s)"
            updateViewsQuery = "UPDATE promo SET views=(%s) WHERE ID=(%s)"
            updateBalanceQuery = "UPDATE users SET balance=(%s) WHERE user_id=(%s)"
            with DatabaseConnection() as db:
                conn, cursor = db
                cursor.executemany(selectQuery, [(callback_query.message.chat.id, [data['promo_id']])])
                result = cursor.fetchone()
                balance, views = result
                cursor.execute(existsQuery, [callback_query.message.chat.id])
                exists = cursor.fetchone()[0]
                if exists:
                    cursor.executemany(updateQuery, [(int(time.time()), callback_query.message.chat.id)])
                else:
                    cursor.executemany(insertQuery, [(callback_query.message.chat.id, int(time.time()))])
                cursor.executemany(insertViewedQuery, [(callback_query.message.chat.id, data['promo_id'])])
                cursor.executemany(updateBalanceQuery, [(balance + reward, callback_query.message.chat.id)])
                cursor.executemany(updateViewsQuery, [(views + 1, data['promo_id'])])
                conn.commit()
            await state.finish()
            await callback_query.answer(lang['got_reward'].format(reward=reward), show_alert=True)
            await main_menu(callback_query.message.chat.id, callback_query.message.chat.first_name, callback_query.message.message_id)
        else:
            await callback_query.answer(lang['promo_watch_wait'].format(int(wait_time - difference)), show_alert=True)


async def views_and_confirm(message, state, lang, views=None, price=None, callback_query=False):
    data = await state.get_data()
    text = ''
    if callback_query:
        await state.update_data({'views': views, 'price': price})
        text += lang['views_price'].format(views=views, price=price)
    text += lang['promo_content'].format(data['media']['caption'])

    key = types.InlineKeyboardMarkup()
    if callback_query:
        key.add(types.InlineKeyboardButton(lang['buttons'][Buttons.make_ad[0]], callback_data=Buttons.make_ad[0]))
    but_1 = types.InlineKeyboardButton(lang['buttons'][Buttons.views_count[0]], callback_data=Buttons.views_count[0])
    but_2 = types.InlineKeyboardButton(lang['buttons'][Buttons.views_count[1]], callback_data=Buttons.views_count[1])
    key.add(but_1, but_2)
    key.add(types.InlineKeyboardButton(lang['buttons'][Buttons.back], callback_data=Buttons.back))

    if not callback_query:
        await Make_promo.next()
        if data['media']['photo']:
            await bot.send_photo(message.chat.id, data['media']['photo'], text, reply_markup=key)
        elif data['media']['video']:
            await bot.send_video(message.chat.id, data['media']['video'], caption=text, reply_markup=key)
        else:
            await bot.send_message(message.chat.id, text + lang['no_media'], reply_markup=key)
    else:
        await bot.edit_message_caption(message.chat.id, message.message_id, caption=text, reply_markup=key)


@dp.message_handler(content_types=['photo', 'video'], state=Make_promo.media)
async def media_text(message: types.Message, state: FSMContext):
    lang = language(message.chat.id)
    photo = video = None
    if message.photo:
        photo = message.photo[-1].file_id
    elif message.video:
        video = message.video.file_id
    await state.update_data({'media': {'photo': photo, 'video': video}})
    await Make_promo.next()
    await message.answer(lang['send_promo_text'])


@dp.message_handler(content_types=['text'], state=Make_promo.text)
async def media_text(message: types.Message, state: FSMContext):
    lang = language(message.chat.id)
    text = await get_caption(message, message.text, lang)
    if not text:
        return
    data = await state.get_data()
    await state.update_data({'media': {'photo': data['media']['photo'], 'video': data['media']['video'], 'caption': text}})
    await views_and_confirm(message, state, lang)


async def publish_ad(callback_query, state):
    lang = language(callback_query.message.chat.id)
    data = await state.get_data()
    selectBalanceQuery = "SELECT balance FROM users WHERE user_id=(%s)"
    insertQuery = "INSERT INTO promo (user_id, text, photo, video, required_views, paid) VALUES (%s, %s, %s, %s, %s, %s)"
    updateQuery = "UPDATE users SET balance=(%s) WHERE user_id=(%s)"
    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.execute(selectBalanceQuery, [callback_query.message.chat.id])
        balance = cursor.fetchone()[0]
        if balance < data['price']:
            conn.close()
            await callback_query.answer(lang['warning_not_enough_money'].format(balance=balance), show_alert=True)
            return
        cursor.executemany(insertQuery, [(callback_query.message.chat.id, data['media']['caption'], data['media']['photo'],
                                          data['media']['video'], data['views'], data['price'])])
        cursor.executemany(updateQuery, [(balance - data['price'], callback_query.message.chat.id)])
        conn.commit()

    await state.finish()
    await callback_query.message.answer(lang['promo_created'], reply_markup=inline_keyboard(Buttons.back_to_menu, lang['buttons']))
    await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


@dp.callback_query_handler(lambda callback_query: True, state=Make_promo.views_confirm)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, proms_choose_mode, callback_query):
        return
    with open('prices.json', 'r') as f:
        price = json.load(f)['views']
    if callback_query.data in price.keys():
        lang = language(callback_query.message.chat.id)
        views = callback_query.data
        await views_and_confirm(callback_query.message, state, lang, int(views[1:]), price[views], True)
    elif callback_query.data == Buttons.make_ad[0]:
        await publish_ad(callback_query, state)


@dp.message_handler(content_types=['text'], state=Make_search_request.keyword)
async def search(message: types.Message, state: FSMContext):
    lang = language(message.chat.id)
    keyword = message.text
    if len(keyword) > 30:
        await message.reply(lang['warning_keyword_too_long'])
        return
    await Make_search_request.next()

    searchQuery = f"SELECT channel, message_id FROM ads WHERE text LIKE '%{keyword}%' LIMIT 1 OFFSET 0"
    selectChannelQuery = "SELECT username FROM channels WHERE ID=(%s)"
    rows_count_query = f"SELECT COUNT(ID) FROM ads WHERE text LIKE '%{keyword}%'"
    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.execute(searchQuery)
        result = cursor.fetchone()
        if result:
            cursor.execute(selectChannelQuery, [result[0]])
            channel = cursor.fetchone()[0]
            cursor.execute(rows_count_query)
            count = cursor.fetchone()[0]
    if result:
        await state.update_data({'keyword': keyword, 'ad_index': 0, 'count': count})
        arrows = True
        if count == 1:
            arrows = False
        await message.answer(lang['ad_link'].format(channel, result[1]), parse_mode="Markdown",
                             reply_markup=inline_keyboard(Buttons.on_notifications, lang['buttons'], back_data=True, arrows=arrows))
    else:
        await message.reply(lang['search_no_results'].format(keyword=keyword), reply_markup=inline_keyboard(Buttons.on_notifications, lang['buttons'], back_data=True))


@dp.callback_query_handler(lambda callback_query: True, state=Make_search_request.view)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, search_choose_option, callback_query):
        return
    lang = language(callback_query.message.chat.id)
    data = await state.get_data()
    if callback_query.data == Buttons.arrows[0].data or callback_query.data == Buttons.arrows[1].data:
        edit = data.get('edit')
        last_index = data['ad_index']
        keyword = data['keyword']
        count = data['count']
        if callback_query.data == Buttons.arrows[0].data:
            if last_index == 0 or last_index > count - 1:
                new_index = count - 1
            else:
                new_index = last_index - 1
        else:
            if last_index >= count - 1:
                new_index = 0
            else:
                new_index = last_index + 1
        with DatabaseConnection() as db:
            conn, cursor = db
            searchQuery = f"SELECT channel, message_id FROM ads WHERE text LIKE '%{keyword}%' LIMIT 1 OFFSET %s"
            selectChannelQuery = "SELECT username FROM channels WHERE ID=(%s)"
            cursor.execute(searchQuery, [new_index])
            result = cursor.fetchone()
            if not result:
                conn.close()
                await callback_query.answer(lang['warning_ad_not_found'], show_alert=True)
                return
            cursor.execute(selectChannelQuery, [result[0]])
            channel = cursor.fetchone()[0]

        await state.update_data({'ad_index': new_index, 'edit': True})
        text = lang['ad_link'].format(channel, result[1])
        if edit:
            try:
                await bot.edit_message_text(text, callback_query.message.chat.id, callback_query.message.message_id,
                                            reply_markup=inline_keyboard(Buttons.on_notifications, lang['buttons'], back_data=True, arrows=True), parse_mode="Markdown")
            except utils.exceptions.MessageNotModified: await callback_query.answer()
            except utils.exceptions.BadRequest: await callback_query.answer(lang['warning_frequently_click'], show_alert=True)
        else:
            await bot.send_message(callback_query.message.chat.id, text,
                                   reply_markup=inline_keyboard(Buttons.on_notifications, lang['buttons'], back_data=True, arrows=True), parse_mode="Markdown")
            await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)

    elif callback_query.data == Buttons.on_notifications:
        with open('prices.json', 'r') as f:
            price = json.load(f)['notify']
        await callback_query.message.answer(lang['turn_on_notifications'].format(data['keyword'], price),
                                            reply_markup=inline_keyboard(Buttons.pay_confirm, lang['buttons'], back_data=True))
        try:
            last_message_id = callback_query.message.message_id
            await bot.delete_message(callback_query.message.chat.id, last_message_id)
            await bot.delete_message(callback_query.message.chat.id, last_message_id - 1)
        except utils.exceptions.MessageCantBeDeleted: pass
        except utils.exceptions.MessageToDeleteNotFound: await callback_query.answer(lang['warning_frequently_click'], show_alert=True)
    elif callback_query.data == Buttons.pay_confirm:
        with open('prices.json', 'r') as f:
            price = json.load(f)['notify']
        selectBalanceQuery = "SELECT balance FROM users WHERE user_id=(%s)"
        updateBalanceQuery = "UPDATE users SET balance=(%s) WHERE user_id=(%s)"
        insertQuery = "INSERT INTO search_requests (user_id, keyword) VALUES (%s, %s)"
        with DatabaseConnection() as db:
            conn, cursor = db
            cursor.execute(selectBalanceQuery, [callback_query.message.chat.id])
            balance = cursor.fetchone()[0]
            if balance < price:
                conn.close()
                await callback_query.answer(lang['warning_not_enough_money'].format(balance=balance), show_alert=True)
                return
            cursor.executemany(insertQuery, [(callback_query.message.chat.id, data['keyword'])])
            cursor.executemany(updateBalanceQuery, [(balance - price, callback_query.message.chat.id)])
            conn.commit()
        await state.finish()
        await callback_query.message.answer(lang['notifications_activated'].format(data['keyword']),
                                            reply_markup=inline_keyboard(Buttons.back_to_menu, lang['buttons']))
        await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


@dp.message_handler(content_types=['text'], state=My_ads.edit)
async def message_handler(message: types.Message, state: FSMContext):
    lang = language(message.chat.id)
    text = await get_caption(message, message.text, lang)
    if not isinstance(text, str):
        return
    data = await state.get_data()
    await state.finish()
    try: await bot.edit_message_caption(data['channel'], data['message_id'], caption=text)
    except utils.exceptions.BadRequest:
        try: await bot.edit_message_text(text, data['channel'], data['message_id'])
        except utils.exceptions.BadRequest: pass
    await message.answer(lang['edited'])
    await main_menu(message.chat.id, message.chat.first_name)


@dp.callback_query_handler(lambda callback_query: True, state=My_ads.delete)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    lang = language(callback_query.message.chat.id)
    if callback_query.data == Buttons.confirm_delete[0]:
        data = await state.get_data()
        await state.finish()
        with DatabaseConnection() as db:
            conn, cursor = db
            deleteQuery = "DELETE FROM ads WHERE ID=(%s)"
            selectAdminsQuery = "SELECT user_id FROM admins WHERE menu_admin=1"
            cursor.execute(selectAdminsQuery)
            admins = cursor.fetchall()
            cursor.execute(deleteQuery, [data['ad_id']])
            conn.commit()
        try:
            await bot.delete_message(data['channel'], data['message_id'])
            await callback_query.answer(lang['deleted'], show_alert=True)
        except utils.exceptions.MessageToDeleteNotFound: pass
        except utils.exceptions.MessageCantBeDeleted:
            for admin in admins:
                lang = language(admin[0])
                await bot.forward_message(admin[0], data['channel'], data['message_id'])
                await bot.send_message(admin[0], lang['delete_ad_manually'])
                await sleep(.1)
            await callback_query.answer(lang['will_be_deleted_soon'], show_alert=True)
        await main_menu(callback_query.message.chat.id, callback_query.message.chat.first_name)
    elif callback_query.data == Buttons.confirm_delete[1]:
        await state.finish()
        await callback_query.answer(lang['canceled'])
        await main_menu(callback_query.message.chat.id, callback_query.message.chat.first_name)


@dp.callback_query_handler(lambda callback_query: True, state=Top_up_balance.amount)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, main_menu, callback_query.message.chat.id, callback_query.message.chat.first_name, callback_query.message.message_id):
        return


@dp.message_handler(regexp='^\\d+$', state=Top_up_balance.amount)
async def search(message: types.Message, state: FSMContext):
    lang = language(message.chat.id)
    amount = int(message.text)
    if amount < 1 or amount > 1000000:
        await message.reply(lang['warning_bad_amount'])
        return
    await state.finish()
    pay_link = pay.way_for_pay_request_purchase(message.chat.id, amount)
    if isinstance(pay_link, tuple):
        print("Error: %s" % pay_link[1])
        await message.answer(lang['warning_payment_error'])
        await message.answer("Error: %s" % pay_link[1])
        return
    key = types.InlineKeyboardMarkup()
    key.add(types.InlineKeyboardButton(lang['pay'], url=pay_link))
    key.add(types.InlineKeyboardButton(lang['buttons'][Buttons.back], callback_data=Buttons.back))
    await message.answer(lang['top_up_balance'].format(amount=amount), reply_markup=key)


@dp.callback_query_handler(lambda callback_query: True, state=Choose_language.choose)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, main_menu, callback_query.message.chat.id, callback_query.message.chat.first_name, callback_query.message.message_id):
        return
    await state.finish()
    updateQuery = "UPDATE users SET lang=(%s) WHERE user_id=(%s)"
    lang = 'ru'
    if callback_query.data == Buttons.languages[0].data:
        lang = 'ru'
    elif callback_query.data == Buttons.languages[1].data:
        lang = 'ua'
    elif callback_query.data == Buttons.languages[2].data:
        lang = 'en'
    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.executemany(updateQuery, [(lang, callback_query.message.chat.id)])
        conn.commit()
    with open('strings.json', encoding='utf-8') as f:
        lang_json = json.load(f)
    await callback_query.message.answer(lang_json[lang]['selected_language'])
    await main_menu(callback_query.message.chat.id, callback_query.message.chat.first_name)
    await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


@dp.callback_query_handler(lambda callback_query: True, state=Admin_privileges.user_id)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, admin_menu, callback_query, callback_query.message.message_id):
        return


@dp.message_handler(content_types=types.ContentTypes.ANY, state=Admin_privileges.user_id)
async def search(message: types.Message, state: FSMContext):
    lang = language(message.chat.id)
    forward = message.forward_from
    if not forward:
        await message.answer(lang['warning_not_forwarded'])
        return
    with DatabaseConnection() as db:
        conn, cursor = db
        selectQuery = "SELECT ID FROM users WHERE user_id=(%s)"
        selectAdminQuery = "SELECT menu_admin, menu_priv, priv_add, priv_remove FROM admins WHERE user_id=(%s)"
        cursor.execute(selectQuery, [forward.id])
        db_id = cursor.fetchone()
        if not db_id:
            conn.close()
            await state.finish()
            await message.answer(lang['warning_no_user_in_db'], reply_markup=inline_keyboard(Buttons.back, lang['buttons']))
            return
        cursor.execute(selectAdminQuery, [forward.id])
        result = cursor.fetchone()
    if not result:
        privileges = lang['admin_privileges_list'][0]
    else:
        privileges = ''
        if result[0]:
            privileges += lang['admin_privileges_list'][1]
        if result[1]:
            privileges += lang['admin_privileges_list'][2]
        if result[2]:
            privileges += lang['admin_privileges_list'][3]
        if result[3]:
            privileges += lang['admin_privileges_list'][4]
        if not privileges:
            privileges = lang['admin_privileges_list'][0]
    await Admin_privileges.next()
    await state.update_data({'priv_id': forward.id, 'priv_name': forward.first_name})
    await message.answer(lang['admin_privileges'].format(db_id[0], forward.first_name, forward.username, privileges),
                         reply_markup=inline_keyboard(Buttons.add_remove_priv, lang['buttons'], back_data=True))


@dp.callback_query_handler(lambda callback_query: True, state=Admin_privileges.privileges)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, admin_menu, callback_query, callback_query.message.message_id):
        return
    lang = language(callback_query.message.chat.id)
    await Admin_privileges.next()
    data = await state.get_data()
    if callback_query.data == Buttons.add_remove_priv[0]:
        await state.update_data({'priv': 'add'})
        buttons = inline_keyboard((Buttons.add_remove_all_priv[0], ) + Buttons.privileges, lang['buttons'])
        verb = lang['priv_add']
    else:
        await state.update_data({'priv': 'remove'})
        buttons = inline_keyboard((Buttons.add_remove_all_priv[1], ) + Buttons.privileges, lang['buttons'])
        verb = lang['priv_remove']
    await callback_query.message.answer(lang['admin_privileges_choose'].format(verb, data['priv_name']), reply_markup=buttons)
    await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


@dp.callback_query_handler(lambda callback_query: True, state=Admin_privileges.choose_privilege)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, admin_menu, callback_query, callback_query.message.message_id):
        return
    data = await state.get_data()
    existsQuery = "SELECT EXISTS (SELECT ID FROM admins WHERE user_id=(%s))"
    insertQuery = "INSERT INTO admins (user_id) VALUES (%s)"
    updateQuery = None
    if data['priv'] == 'add':
        if callback_query.data == Buttons.add_remove_all_priv[0]:
            updateQuery = "UPDATE admins SET menu_admin=1, menu_priv=1, priv_add=1, priv_remove=1 WHERE user_id=(%s)"
        elif callback_query.data == Buttons.privileges[0]:
            updateQuery = "UPDATE admins SET menu_admin=1 WHERE user_id=(%s)"
        elif callback_query.data == Buttons.privileges[1]:
            updateQuery = "UPDATE admins SET menu_priv=1 WHERE user_id=(%s)"
        elif callback_query.data == Buttons.privileges[2]:
            updateQuery = "UPDATE admins SET priv_add=1 WHERE user_id=(%s)"
        elif callback_query.data == Buttons.privileges[3]:
            updateQuery = "UPDATE admins SET priv_remove=1 WHERE user_id=(%s)"
    elif data['priv'] == 'remove':
        if callback_query.data == Buttons.add_remove_all_priv[1]:
            updateQuery = "UPDATE admins SET menu_admin=0, menu_priv=0, priv_add=0, priv_remove=0 WHERE user_id=(%s)"
        elif callback_query.data == Buttons.privileges[0]:
            updateQuery = "UPDATE admins SET menu_admin=0 WHERE user_id=(%s)"
        elif callback_query.data == Buttons.privileges[1]:
            updateQuery = "UPDATE admins SET menu_priv=0 WHERE user_id=(%s)"
        elif callback_query.data == Buttons.privileges[2]:
            updateQuery = "UPDATE admins SET priv_add=0 WHERE user_id=(%s)"
        elif callback_query.data == Buttons.privileges[3]:
            updateQuery = "UPDATE admins SET priv_remove=0 WHERE user_id=(%s)"
    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.execute(existsQuery, [data['priv_id']])
        exists = cursor.fetchone()[0]
        if not exists:
            cursor.execute(insertQuery, [data['priv_id']])
        cursor.execute(updateQuery, [data['priv_id']])
        conn.commit()
    await state.finish()
    await callback_query.answer("Привилегии успешно изменены", show_alert=True) ##
    await admin_menu(callback_query, callback_query.message.message_id)


@dp.callback_query_handler(lambda callback_query: True, state=Admin_channels.select)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, admin_menu, callback_query, callback_query.message.message_id):
        return
    if callback_query.data == Buttons.arrows[0].data or callback_query.data == Buttons.arrows[1].data:
        await admin_channels(callback_query, state)
        return
    lang = language(callback_query.message.chat.id)
    if callback_query.data == Buttons.admin_channels[0]:
        await Admin_channels.next()
        await callback_query.message.answer(lang['input_ad_cost'], reply_markup=inline_keyboard(Buttons.back, lang['buttons']))
        await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    elif callback_query.data == Buttons.admin_channels[1]:
        data = await state.get_data()
        selectQuery = "SELECT name FROM channels WHERE ID=(%s)"
        with DatabaseConnection() as db:
            conn, cursor = db
            cursor.execute(selectQuery, [data['channel_id']])
            channel = cursor.fetchone()[0]
        await callback_query.message.answer(lang['sure_to_delete_channel'].format(channel=channel),
                                            reply_markup=inline_keyboard(Buttons.confirm_delete, lang['buttons']))
        await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    elif callback_query.data == Buttons.confirm_delete[0]:
        data = await state.get_data()
        deleteQuery = "DELETE FROM channels WHERE ID=(%s)"
        deleteAllAdsQuery = "DELETE FROM ads WHERE channel=(%s)"
        with DatabaseConnection() as db:
            conn, cursor = db
            cursor.execute(deleteQuery, [data['channel_id']])
            cursor.execute(deleteAllAdsQuery, [data['channel_id']])
            conn.commit()
        await callback_query.answer(lang['deleted'], show_alert=True)
        await admin_menu(callback_query, callback_query.message.message_id)
    elif callback_query.data == Buttons.confirm_delete[1]:
        await callback_query.answer(lang['canceled'])
        await admin_menu(callback_query, callback_query.message.message_id)


@dp.callback_query_handler(lambda callback_query: True, state=Admin_channels.new_prices)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, admin_menu, callback_query, callback_query.message.message_id):
        return


@dp.message_handler(content_types=['text'], state=Admin_channels.new_prices)
async def new_prices(message: types.Message, state: FSMContext):
    lang = language(message.chat.id)
    text = str(message.text).split(' ')
    if len(text) != 4:
        await message.answer(lang['warning_bad_values_1'])
        return
    for x in text:
        if not x.isdigit():
            await message.answer(lang['warning_bad_values_2'])
            return
    text = [int(x) for x in text]
    await state.update_data({'prices': text})
    await Admin_channels.next()
    await message.answer(lang['admin_connect_channel'], reply_markup=inline_keyboard(Buttons.back, lang['buttons']))


@dp.callback_query_handler(lambda callback_query: True, state=Admin_channels.new_channel)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, admin_menu, callback_query, callback_query.message.message_id):
        return


@dp.message_handler(content_types=types.ContentTypes.ANY, state=Admin_channels.new_channel)
async def new_channel(message: types.Message, state: FSMContext):
    lang = language(message.chat.id)
    forward = message.forward_from_chat
    if not forward:
        await message.reply(lang['warning_not_forwarded_or_not_from_channel'])
        return
    try:
        m = await bot.get_chat_member(f'@{forward.username}', 1097976142)
    except utils.exceptions.ChatNotFound:
        await message.reply(lang['warning_not_forwarded_from_public_channel'])
        return
    if m.status == "left":
        await message.answer(lang['warning_bot_not_in_channel'])
        return
    data = await state.get_data()
    name, username, ch_id, prices = forward.title, forward.username, forward.id, data['prices']
    existsQuery = "SELECT EXISTS (SELECT ID FROM channels WHERE chat_id=(%s))"
    updateQuery = "UPDATE channels SET username=(%s), name=(%s), 1_day=(%s), 7_days=(%s), 14_days=(%s), 30_days=(%s) WHERE chat_id=(%s)"
    insertQuery = "INSERT INTO channels (username, name, chat_id, 1_day, 7_days, 14_days, 30_days) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.execute(existsQuery, [ch_id])
        exists = cursor.fetchone()[0]
        if exists:
            cursor.executemany(updateQuery, [(username, name, prices[0], prices[1], prices[2], prices[3], ch_id)])
        else:
            cursor.executemany(insertQuery, [(username, name, ch_id, prices[0], prices[1], prices[2], prices[3])])
        conn.commit()
    await state.finish()
    if exists:
        await message.answer(lang['channel_updated'], reply_markup=inline_keyboard(Buttons.back, lang['buttons']))
    else:
        await message.answer(lang['channel_added'], reply_markup=inline_keyboard(Buttons.back, lang['buttons']))
    await _delete_message(message.chat.id, message.message_id)


@dp.callback_query_handler(lambda callback_query: True, state=Admin_settings.select)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, admin_menu, callback_query, callback_query.message.message_id):
        return
    lang = language(callback_query.message.chat.id)
    await state.update_data({'set': callback_query.data})
    await Admin_settings.next()
    await callback_query.message.answer(lang['input_value'], reply_markup=inline_keyboard(Buttons.back, lang['buttons']))
    await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


@dp.callback_query_handler(lambda callback_query: True, state=Admin_settings.edit)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, admin_menu, callback_query, callback_query.message.message_id):
        return


@dp.message_handler(regexp='^\\d+$', state=Admin_settings.edit)
async def new_prices(message: types.Message, state: FSMContext):
    lang = language(message.chat.id)
    text = int(message.text)
    data = await state.get_data()
    setting = data['set']
    with open('prices.json', 'r') as f:
        prices = json.load(f)
    if setting == Buttons.admin_settings[0].data:
        prices['views']['_1000'] = text
    elif setting == Buttons.admin_settings[1].data:
        prices['views']['_5000'] = text
    elif setting == Buttons.admin_settings[2].data:
        prices['notify'] = text
    elif setting == Buttons.admin_settings[3].data:
        prices['ad_view'] = text
    elif setting == Buttons.admin_settings[4].data:
        prices['ban'][0] = text
    elif setting == Buttons.admin_settings[5].data:
        prices['ban'][1] = text
    with open('prices.json', 'wt') as f:
        json.dump(prices, f, ensure_ascii=False, indent=2)
    await state.finish()
    await message.answer(lang['edited'], reply_markup=inline_keyboard(Buttons.back_to_menu, lang['buttons']))


@dp.callback_query_handler(lambda callback_query: True, state=Admin_promo.select)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, admin_menu, callback_query, callback_query.message.message_id):
        return
    if callback_query.data == Buttons.arrows[0].data or callback_query.data == Buttons.arrows[1].data:
        await admin_promo(callback_query, state)
        return
    lang = language(callback_query.message.chat.id)
    if callback_query.data == Buttons.admin_promo[0]:
        data = await state.get_data()
        with DatabaseConnection() as db:
            conn, cursor = db
            updateQuery = "UPDATE promo SET approved=1 WHERE ID=(%s)"
            cursor.execute(updateQuery, [data['promo_id']])
            conn.commit()
        await state.update_data({'promo_id': None})
        await callback_query.answer(lang['approved'], show_alert=True)
    elif callback_query.data == Buttons.admin_promo[1]:
        data = await state.get_data()
        deleteQuery = "DELETE FROM promo WHERE ID=(%s)"
        selectBalanceQuery = "SELECT balance FROM users WHERE user_id=(%s)"
        updateBalanceQuery = "UPDATE users SET balance=(%s) WHERE user_id=(%s)"
        with DatabaseConnection() as db:
            conn, cursor = db
            cursor.execute(selectBalanceQuery, [data['promo_user']])
            balance = cursor.fetchone()[0]
            cursor.executemany(updateBalanceQuery, [(balance + data['promo_price'], data['promo_user'])])
            cursor.execute(deleteQuery, [data['promo_id']])
            conn.commit()
        await state.update_data({'promo_id': None})
        await callback_query.answer(lang['rejected'], show_alert=True)


@dp.callback_query_handler(lambda callback_query: True, state=Admin_ads.ad_id)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, admin_menu, callback_query, callback_query.message.message_id):
        return


@dp.message_handler(regexp='^\\d+$', state=Admin_ads.ad_id)
async def search(message: types.Message, state: FSMContext):
    lang = language(message.chat.id)
    ad_id = int(message.text)
    with DatabaseConnection() as db:
        conn, cursor = db
        selectQuery = "SELECT user_id, channel, message_id, created, period FROM ads WHERE ID=(%s)"
        selectChannelQuery = "SELECT username, name FROM channels WHERE ID=(%s)"
        cursor.execute(selectQuery, [ad_id])
        result = cursor.fetchone()
        if not result:
            conn.close()
            await message.answer(lang['warning_ad_not_found'], reply_markup=inline_keyboard(Buttons.back, lang['buttons']))
            return
        cursor.execute(selectChannelQuery, [result[1]])
        channel = cursor.fetchone()

    try:
        await bot.forward_message(message.chat.id, f'@{channel[0]}', result[2])
    except utils.exceptions.MessageToForwardNotFound:
        await message.answer(lang['warning_no_ad_in_db'])
        delete_invalid_ad_from_db(result[2], result[1])
        return
    await Admin_ads.next()
    await state.update_data({'ad_id': ad_id})
    await message.answer(lang['admin_ad'].format(ad_id, channel[1], channel[0],
                                                 datetime.datetime.strftime(result[3], '%d.%m.%Y'), result[4],
                                                 datetime.datetime.strftime(result[3] + datetime.timedelta(result[4]), '%d.%m.%Y')),
                         reply_markup=inline_keyboard(Buttons.delete_ad, lang['buttons'], back_data=True))


@dp.callback_query_handler(lambda callback_query: True, state=Admin_ads.back_or_delete)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, admin_menu, callback_query, callback_query.message.message_id):
        await _delete_message(callback_query.message.chat.id, callback_query.message.message_id - 1)
        return
    lang = language(callback_query.message.chat.id)
    if callback_query.data == Buttons.delete_ad:
        data = await state.get_data()
        await callback_query.message.answer(lang['sure_to_delete_ad_admin'].format(data['ad_id']),
                                            reply_markup=inline_keyboard(Buttons.confirm_delete, lang['buttons']))
        last_message_id = callback_query.message.message_id
        await _delete_message(callback_query.message.chat.id, last_message_id)
        await _delete_message(callback_query.message.chat.id, last_message_id - 1)
    elif callback_query.data == Buttons.confirm_delete[0]:
        data = await state.get_data()
        with DatabaseConnection() as db:
            conn, cursor = db
            deleteQuery = "DELETE FROM ads WHERE ID=(%s)"
            cursor.execute(deleteQuery, [data['ad_id']])
            conn.commit()
        await callback_query.answer(lang['deleted'], show_alert=True)
        await admin_menu(callback_query, callback_query.message.message_id)
    elif callback_query.data == Buttons.confirm_delete[1]:
        await callback_query.answer(lang['canceled'])
        await admin_menu(callback_query, callback_query.message.message_id)






if __name__ == "__main__":
    #dp.loop.create_task(expired_ads_checker.loop_check())
    executor.start_polling(dp, skip_updates=True)
