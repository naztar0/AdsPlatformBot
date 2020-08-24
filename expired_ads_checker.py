import mysql.connector
import datetime
from asyncio import sleep
from aiogram import Bot, utils
import constants as c

bot = Bot(c.token)
selectAdsQuery = "SELECT channel, message_id, period FROM ads WHERE expire<(%s)"
selectChannelQuery = "SELECT username FROM channels WHERE ID=(%s)"
deleteQuery = "DELETE FROM ads WHERE expire<(%s)"
selectAdminsQuery = "SELECT user_id FROM admins WHERE menu_admin=1"


async def loop_check():
    while True:
        conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
        cursor = conn.cursor(buffered=True)
        now = datetime.datetime.now()
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
        conn.close()

        for ad in ads:
            channel, message_id,  period = ad[0], ad[1], ad[2]
            if period == 1:
                try:
                    await bot.delete_message(f'@{usernames[channel]}', message_id)
                except utils.exceptions.MessageCantBeDeleted: pass
                except utils.exceptions.BadRequest: pass
            else:
                for admin in admins:
                    try:
                        await bot.send_message(admin[0], f"Удалите [объявление](https://t.me/{usernames[channel]}/{message_id}), срок истёк", parse_mode="Markdown")
                    except utils.exceptions.BotBlocked: pass
                    except utils.exceptions.UserDeactivated: pass
                    except utils.exceptions.ChatNotFound: pass
        await sleep(28800)  # 8 hours
