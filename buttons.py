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
        'top_up_balance', \
        'change_language'
    main_admin = 'admin_menu'
    back_to_menu = 'main_menu'
    back = 'back'
    to_channel = 'go_to_channel', 'place_ad'
    make_ad = 'confirm_place', '1', '7', '14', '30'
    make_promo = 'watch_promo',  'create_promo'
    watch_promo = 'view_confirm'
    views_count = '_1000', '_5000'
    search_request = 'my_search_requests', 'make_search_request'
    on_notifications = 'on_notify'
    pay_confirm = 'confirm_pay'
    delete_ad = 'delete_ad'
    confirm_delete = 'delete_ad_confirm', 'delete_back'
    choose_language = 'choose_language'
    languages = \
        Button('Русский', 'lang_ru'), \
        Button('Українська', 'lang_ua'), \
        Button('English', 'lang_en')
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
    arrows = Button('⬅', 'prev'), Button('➡', 'next')
    back_but = Button('Назад', 'back')
    back_to_menu_but = Button('Вернуться в главное меню', 'main_menu')
    delete_ad_but = Button('Удалить объявление', 'delete_ad')
    confirm_delete_but = Button('Да, удалить', 'delete_ad_confirm'), Button('Нет, отменить', 'delete_back')
    regexp_restart = '^(🏠 Главное меню|🏠 Головне меню|🏠 Main menu)$'
    reply_request_contact = 'Поделиться контактом'
    reply_request_location = 'Поделиться местоположением'
