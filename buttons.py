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
    admin = \
        'admin_privileges', \
        'admin_channels', \
        'admin_settings', \
        'admin_promo', \
        'admin_ads'
    add_remove_priv = 'add_priv', 'remove_priv'
    add_remove_all_priv = 'priv_all_add', 'priv_all_remove',
    privileges = \
        'priv_admin', \
        'priv_priv', \
        'priv_add_priv', \
        'priv_remove_priv'
    admin_channels = 'add_channel', 'delete_channel'
    admin_promo = 'approve', 'reject'
    admin_settings = \
        Button('1', 'set_1'), Button('2', 'set_2'),\
        Button('3', 'set_3'), Button('4', 'set_4'),\
        Button('5', 'set_5'), Button('6', 'set_6')
    languages = \
        Button('Українська', 'lang_ua'), \
        Button('Русский', 'lang_ru'), \
        Button('English', 'lang_en')
    report = Button('Жалоба', 'report')
    arrows = Button('⬅', 'prev'), Button('➡', 'next')
    regexp_restart = '^(🏠 Главное меню|🏠 Головне меню|🏠 Main menu)$'
    reply_request_contact = 'Поделиться контактом'
    reply_request_location = 'Поделиться местоположением'

    chat_main = 'my_chats', 'new_chat'

