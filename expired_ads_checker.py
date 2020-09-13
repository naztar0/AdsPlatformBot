import datetime
import json
from asyncio import sleep
from aiogram import Bot, utils
import constants as c
from database_connection import DatabaseConnection

bot = Bot(c.token)
selectAdsQuery = "SELECT channel, message_id, period FROM ads WHERE expire<(%s)"
selectChannelQuery = "SELECT username FROM channels WHERE ID=(%s)"
deleteQuery = "DELETE FROM ads WHERE expire<(%s)"
selectAdminsQuery = "SELECT user_id FROM admins WHERE menu_admin=1"
selectAdminLangQuery = "SELECT lang FROM users WHERE user_id=(%s)"


async def loop_check():
    while True:
        now = datetime.datetime.now()
        with DatabaseConnection() as db:
            conn, cursor = db
            cursor.execute(selectAdsQuery, [now])
            ads = cursor.fetchall()
            channels = {x[0] for x in ads}
            usernames = {}
            for ch in channels:
                cursor.execute(selectChannelQuery, [ch])
                usernames[ch] = cursor.fetchone()[0]
            cursor.execute(selectAdminsQuery)
            admins = cursor.fetchall()
            cursor.execute(deleteQuery, [now])
            conn.commit()

        for ad in ads:
            channel, message_id,  period = ad[0], ad[1], ad[2]
            if period == 1:
                try:
                    await bot.delete_message(f'@{usernames[channel]}', message_id)
                except utils.exceptions.MessageCantBeDeleted: pass
                except utils.exceptions.BadRequest: pass
            else:
                for admin in admins:
                    with DatabaseConnection() as db:
                        conn, cursor = db
                        cursor.execute(selectAdminLangQuery, [admin[0]])
                        la = cursor.fetchone()[0]
                    with open('strings.json', 'r') as f:
                        lang = json.load(f)[la]
                    try:
                        await bot.send_message(admin[0], lang['expired_ad_delete_request'].format(usernames[channel], message_id), parse_mode="Markdown")
                        await sleep(.05)
                    except utils.exceptions.BotBlocked: pass
                    except utils.exceptions.UserDeactivated: pass
                    except utils.exceptions.ChatNotFound: pass
        await sleep(28800)  # 8 hours
