from collections import namedtuple
Button = namedtuple('Button', 'title data')


class Buttons:
    main = \
        'channels', \
        'proms', \
        'search', \
        'my_ads', \
        'my_promos', \
        'referrals', \
        'top_up_balance'
    main_admin = Button('Меню администратора', 'admin_menu')
    back_to_menu = Button('Вернуться в главное меню', 'main_menu')
    back = Button('Назад', 'back')
    to_channel = Button('Перейти в канал', 'go_to_channel'), Button('Разместить объявление', 'place_ad')
    make_ad = Button('ОПЛАТИТЬ И РАЗМЕСТИТЬ', 'confirm_place'),  Button('1 день', '1'), Button('7 дней', '7'),  Button('14 дней', '14'), Button('30 дней', '30')
    make_promo = Button('Просмотреть рекламу', 'watch_promo'),  Button('Создать рекламу', 'create_promo')
    arrows = Button('⬅', 'prev'), Button('➡', 'next')
    watch_promo = Button('Просмотреть', 'view_confirm')
    views_count = Button('1000 просмотров', '_1000'), Button('5000 просмотров', '_5000')
    search_request = Button('Мои запросы', 'my_search_requests'), Button('Создать запрос', 'make_search_request')
    on_notifications = Button('Включить оповещения для фразы', 'on_notify')
    pay_confirm = Button('Подтвердить оплату', 'confirm_pay')
    delete_ad = Button('Удалить объявление', 'delete_ad')
    confirm_delete = Button('Да, удалить', 'delete_ad_confirm'), Button('Нет, отменить', 'delete_back')
    admin = \
        Button('Привилегии', 'admin_privileges'), \
        Button('Каналы', 'admin_channels'), \
        Button('Настройки', 'admin_settings'), \
        Button('Реклама', 'admin_promo'), \
        Button('Объявления', 'admin_ads')
    add_remove_priv = Button('Добавить привилегию', 'add_priv'), Button('Убрать привилегию', 'remove_priv')
    add_remove_all_priv = Button('Добавить все', 'priv_all_add'), Button('Убрать все', 'priv_all_remove'),
    privileges = \
        Button('Доступ к меню «Администратор»', 'priv_admin'), \
        Button('Доступ к меню «Привилегии»', 'priv_priv'), \
        Button('Добавление привилегий', 'priv_add_priv'), \
        Button('Удаление привилегий', 'priv_remove_priv')
    admin_channels = Button('Добавить канал', 'add_channel'), Button('Удалить канал', 'delete_channel')
    admin_settings = \
        Button('1', 'set_1'), Button('2', 'set_2'),\
        Button('3', 'set_3'), Button('4', 'set_4'),\
        Button('5', 'set_5'), Button('6', 'set_6')
    admin_promo = Button('Одобрить', 'approve'), Button('Отклонить', 'reject')
    report = Button('Жалоба', 'report')
    reply_restart = '🏠 Главное меню'
    reply_request_contact = 'Поделиться контактом'
    reply_request_location = 'Поделиться местоположением'
