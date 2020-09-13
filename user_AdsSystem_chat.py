#!/usr/bin/env python
import constants as c
from database_connection import DatabaseConnection
from buttons import Buttons
from media_group import media_group
from user_AdsSystem_main import _back, _media_group_builder, get_caption, inline_keyboard, language
import os
import zipfile

from aiogram import Bot, Dispatcher, executor, types, utils
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage


bot = Bot(c.token2)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class Chat(StatesGroup):
    action = State()
    send = State()
    rename = State()
    delete = State()


class New_chat(StatesGroup):
    chat = State()


@dp.message_handler(regexp=Buttons.regexp_restart)
async def restart(message: types.Message, state: FSMContext):
    await state.finish()
    await main_menu(message.chat.id)


@dp.message_handler(regexp=Buttons.regexp_restart, state=Chat)
async def restart(message: types.Message, state: FSMContext):
    await state.finish()
    await main_menu(message.chat.id)


@dp.message_handler(regexp=Buttons.regexp_restart, state=New_chat)
async def restart(message: types.Message, state: FSMContext):
    await state.finish()
    await main_menu(message.chat.id)


async def main_menu(user_id, lang=None):
    if not lang:
        lang = language(user_id)
    await bot.send_message(user_id, lang['main_menu'], reply_markup=inline_keyboard(Buttons.chat_main, lang))


async def _send_message(func, **kwargs):
    try:
        await func(**kwargs)
    except utils.exceptions.BotBlocked: return
    except utils.exceptions.UserDeactivated: return
    except utils.exceptions.ChatNotFound: return
    except utils.exceptions.BadRequest: return
    return True


async def _delete_message(user_id, message_id):
    try:
        await bot.delete_message(user_id, message_id)
    except utils.exceptions.MessageCantBeDeleted:
        return
    except utils.exceptions.MessageToDeleteNotFound:
        return


@dp.message_handler(commands=['start'])
async def message_handler(message: types.Message):
    lang = language(message.chat.id, registration_important=True)
    if not lang:
        await message.answer("Для початку зареєструйтеся в @AdvancedAdsBot")
        return
    key = types.ReplyKeyboardMarkup(resize_keyboard=True)
    key.add(types.KeyboardButton(lang['buttons']['reply_restart']))
    await message.answer("Hello!", reply_markup=key)
    await main_menu(message.chat.id, lang)


async def my_chats(callback_query):
    lang = language(callback_query.message.chat.id)
    selectQuery = "SELECT uid1, uid2, alias1, alias2 FROM chats WHERE uid1=(%s) OR uid2=(%s)"
    iam = callback_query.message.chat.id
    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.executemany(selectQuery, [(iam, iam)])
        results = cursor.fetchall()
    if not results:
        await callback_query.message.answer(lang['have_not_any_chat'])
        return
    key = types.InlineKeyboardMarkup()
    for res in results:
        if res[0] == iam and not res[1] or res[1] == iam and not res[0]:
            interlocutor = (0, lang['no_interlocutor'])
        else:
            interlocutor = (res[0], res[3] if res[3] else res[0]) if res[1] == iam else (res[1], res[2] if res[2] else res[1])
        key.add(types.InlineKeyboardButton(str(interlocutor[1]), callback_data=f'chat_{interlocutor[0]}'))
    await callback_query.answer()
    await callback_query.message.answer(lang['choose_chat'], reply_markup=key)
    await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


async def chat_actions(callback_query, state):
    lang = language(callback_query.message.chat.id)
    chat = int(callback_query.data[5:])
    key = types.InlineKeyboardMarkup()
    if chat: ## ПРОДОЛЖАЕМ МЕНЯТЬ СТРОКИ НА LANG
        key.add(types.InlineKeyboardButton("Отправить сообщение", callback_data='send'))
    but_2 = types.InlineKeyboardButton("Переименовать", callback_data='rename')
    but_3 = types.InlineKeyboardButton("Удалить", callback_data='delete')
    key.add(but_2, but_3)
    key.add(types.InlineKeyboardButton("Назад", callback_data=Buttons.back))
    title = callback_query.message.reply_markup.inline_keyboard[0][0].text
    await Chat.action.set()
    await state.update_data({'chat': chat, 'title': title})
    await callback_query.message.answer(f"Выбрано: {title}", reply_markup=key)
    await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


async def new_chat(callback_query):
    await New_chat.chat.set()
    await callback_query.answer("Введите код чата")
    await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


async def chat_answer(callback_query, state):
    await Chat.send.set()
    await state.update_data({'chat': str(callback_query.data)[6:]})
    await callback_query.answer()
    await callback_query.message.answer("Отправьте сообщение собеседнику")



@dp.callback_query_handler(lambda callback_query: True)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == Buttons.back:
        await main_menu(callback_query.message.chat.id)

    elif callback_query.data == Buttons.chat_main[0]:
        await my_chats(callback_query)
    elif callback_query.data == Buttons.chat_main[1]:
        await new_chat(callback_query)
    elif callback_query.data[:4] == 'chat':
        await chat_actions(callback_query, state)
    elif callback_query.data[:6] == 'answer':
        await chat_answer(callback_query, state)


@dp.callback_query_handler(lambda callback_query: True, state=Chat.action)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    if await _back(callback_query, state, main_menu, callback_query.message.chat.id):
        return

    lang = language(callback_query.message.chat.id)
    data = await state.get_data()
    if callback_query.data == 'send':
        await Chat.send.set()
        await callback_query.message.answer("Отправьте сообщение собеседнику")
        await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    elif callback_query.data == 'rename':
        await Chat.rename.set()
        await callback_query.message.answer("Введите новое название чата. Это название будет отображаться только у вас.")
        await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    elif callback_query.data == 'delete':
        await Chat.delete.set()
        await callback_query.message.answer(f"Вы уверены что хотите удалить чат «{data['title']}»?",
                                            reply_markup=inline_keyboard(Buttons.confirm_delete, lang['buttons']))
        await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)


@dp.message_handler(regexp='^\\d+$', state=New_chat.chat)
async def message_handler(message: types.Message, state: FSMContext):
    chat = int(message.text)
    if chat == message.chat.id:
        await state.finish()
        await message.reply("Нельзя создать чат с самим собой!")
        return
    existsQuery1 = "SELECT EXISTS (SELECT ID FROM users WHERE user_id=(%s))"
    existsQuery2 = "SELECT EXISTS (SELECT ID FROM chats WHERE uid1=(%s) AND uid2=(%s) OR uid1=(%s) AND uid2=(%s))"
    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.execute(existsQuery1, [chat])
        result1 = cursor.fetchone()[0]
        cursor.executemany(existsQuery2, [(message.chat.id, chat, chat, message.chat.id)])
        result2 = cursor.fetchone()[0]
    if not result1:
        await state.finish()
        await message.reply("Пользователя нет в базе данных бота")
        return
    elif result2:
        await state.finish()
        await message.reply("У вас уже есть чат с данным пользователем")
        return
    insertQuery = "INSERT INTO chats (uid1, uid2)"
    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.executemany(insertQuery, [(message.chat.id, chat)])
        conn.commit()
    await message.answer("Чат с данным пользователем успешно создан")


@dp.message_handler(content_types=['text', 'photo', 'video', 'location'], state=Chat.send)
async def message_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    chat = data['chat']
    with DatabaseConnection() as db:
        conn, cursor = db
        selectQuery = "SELECT uid1, uid2, alias1, alias2, ID FROM chats WHERE uid1=(%s) AND uid2=(%s) OR uid1=(%s) AND uid2=(%s)"
        cursor.executemany(selectQuery, [(message.chat.id, chat, chat, message.chat.id)])
        res = cursor.fetchone()
    interlocutor_chat_title = (res[3] if res[3] else res[0]) if res[0] == chat else (res[2] if res[2] else res[1])
    lang = language(message.chat.id)
    caption, has_media, has_media_group = '', False, False
    key = types.InlineKeyboardMarkup()
    key.add(types.InlineKeyboardButton("Ответить", callback_data=f"answer{message.chat.id}"))
    if message.media_group_id:
        data = await media_group(message, state)
        if data is None: return
        await state.update_data({'media_group': True})
        caption = data['media_group']['caption']
        if not caption:
            caption = False
        else:
            caption = await get_caption(message, caption, lang)
            if not caption:
                return
        media = _media_group_builder(data, caption=f'{interlocutor_chat_title}:\n{caption}')
        send = await _send_message(bot.send_media_group, chat_id=chat, media=media)
        if send:
            await message.answer("Отправлено")
        else:
            await message.reply("Сообщение не доставлено, возможно пользователь заблокировал бота")
        if data['media_group']['photo']:
            has_media = True
            has_media_group = True
    elif message.photo:
        photo = message.photo[-1].file_id
        caption = message.caption
        if caption:
            caption = await get_caption(message, caption, lang)
            if not caption:
                return
        send = await _send_message(bot.send_photo, chat_id=chat, photo=photo,
                                   caption=f'{interlocutor_chat_title}:\n{caption}', reply_markup=key)
        if send:
            await message.answer("Отправлено")
        else:
            await message.reply("Сообщение не доставлено, возможно пользователь заблокировал бота")
        has_media = True
    elif message.video:
        video = message.video.file_id
        caption = message.caption
        if caption:
            caption = await get_caption(message, caption, lang)
            if not caption:
                return
        send = await _send_message(bot.send_video, chat_id=chat, video=video,
                                   caption=f'{interlocutor_chat_title}:\n{caption}', reply_markup=key)
        if send:
            await message.reply("Отправлено")
        else:
            await message.reply("Сообщение не доставлено, возможно пользователь заблокировал бота")
    elif message.text:
        caption = message.text
        if caption:
            caption = await get_caption(message, caption, lang)
            if not caption:
                return
        send = await _send_message(bot.send_message, chat_id=chat,
                                   text=f'{interlocutor_chat_title}:\n{caption}', reply_markup=key)
        if send:
            await message.answer("Отправлено")
        else:
            await message.reply("Сообщение не доставлено, возможно пользователь заблокировал бота")
    elif message.location:
        await _send_message(bot.send_message, chat_id=chat, text=f'{interlocutor_chat_title}:')
        send = await _send_message(bot.send_location, chat_id=chat, latitude=message.location.latitude,
                                   longitude=message.location.longitude, reply_markup=key)
        if send:
            await message.answer("Отправлено")
        else:
            await message.reply("Сообщение не доставлено, возможно пользователь заблокировал бота")

    # Logging
    with open(f'export/text/{res[4]}.txt', 'at', encoding='utf-8') as f:
        f.write(f'{message.chat.first_name}:\n{caption}\n\n')
    if has_media:
        first_name = str(message.chat.first_name).replace('\\', '-').replace('/', '-').replace(':', '-') \
            .replace('*', '-').replace('?', '-').replace('"', '-').replace('<', '-').replace('>', '-').replace('|', '-')
        if not os.path.exists(f'export/media/{res[4]}'):
            os.mkdir(f'export/media/{res[4]}')
        if has_media_group:
            data = await state.get_data()
            for photo_id in data['media_group']['photo']:
                file_info = await bot.get_file(photo_id)
                await file_info.download(f'export/media/{res[4]}/{first_name} - {photo_id}.jpg')
        else:
            fileID = message.photo[-1].file_id
            file_info = await bot.get_file(fileID)
            await file_info.download(f'export/media/{res[4]}/{first_name} - {fileID}.jpg')


@dp.message_handler(content_types=['text'], state=Chat.rename)
async def message_handler(message: types.Message, state: FSMContext):
    lang = language(message.chat.id)
    title = message.text
    if len(title) > 20:
        await message.reply("Слишком длинное название чата, повторите попытку")
        return
    data = await state.get_data()
    chat = data['chat']
    selectQuery = "SELECT uid1, uid2, ID FROM chats WHERE uid1=(%s) AND uid2=(%s) OR uid1=(%s) AND uid2=(%s)"
    updateQuery = "UPDATE chats SET {}=(%s) WHERE ID=(%s)"
    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.executemany(selectQuery, [(message.chat.id, chat, chat, message.chat.id)])
        res = cursor.fetchone()
        my_alias = 'alias1' if res[0] == message.chat.id else 'alias2'
        cursor.executemany(updateQuery.format(my_alias), [(title, res[2])])
        conn.commit()
    await state.finish()
    await message.answer(lang['edited'])


@dp.callback_query_handler(lambda callback_query: True, state=Chat.delete)
async def callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    lang = language(callback_query.message.chat.id)
    if callback_query.data == Buttons.confirm_delete[0]:
        data = await state.get_data()
        chat = data['chat']
        await state.finish()
        deleteQuery = "DELETE FROM chats WHERE uid1=(%s) AND uid2=(%s) OR uid1=(%s) AND uid2=(%s)"
        with DatabaseConnection() as db:
            conn, cursor = db
            cursor.executemany(deleteQuery, [(callback_query.message.chat.id, chat, chat, callback_query.message.chat.id)])
            conn.commit()
        await callback_query.message.answer(lang['deleted'])
        await _delete_message(callback_query.message.chat.id, callback_query.message.message_id)
        await main_menu(callback_query.message.chat.id, lang)
    elif callback_query.data == Buttons.confirm_delete[1]:
        await state.finish()
        await callback_query.answer(lang['canceled'])




if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
