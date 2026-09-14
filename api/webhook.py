import json
import os
import requests
import urllib3
from http.server import BaseHTTPRequestHandler

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MAX_TOKEN = os.getenv('MAX_TOKEN')
API_BASE = 'https://platform-api2.max.ru'

# =====================================================
# ⚙️ НАСТРОЙКИ — РЕДАКТИРУЙТЕ ЗДЕСЬ
# =====================================================

# Официальная форма регистрации туристских групп МЧС
REGISTRATION_URL = "https://forms.mchs.gov.ru/registration_tourist_groups"

# Прямая ссылка на герб (вставьте ВАШУ ссылку из шага 1!)
START_IMAGE_URL = "https://raw.githubusercontent.com/mariadmitrieva66-hue/max-bot/main/emblem.png"

# Актуальный текст предупреждений (меняйте при новых штормовых)
WARNINGS_TEXT = ("**⚠️ ВНИМАНИЕ!**\n\n"
                 "По данным Сахалинского УГМС: сегодня в регионе ожидается "
                 "усиление ветра до 20 м/с.\n"
                 "Соблюдайте осторожность!")
# =====================================================


def send_message(chat_id, text, buttons=None, image_url=None):
    if not chat_id:
        print("⚠️ chat_id пустой, пропускаю отправку")
        return
    url = f'{API_BASE}/messages?chat_id={chat_id}'
    headers = {'Authorization': MAX_TOKEN, 'Content-Type': 'application/json'}

    def build_payload(with_image):
        payload = {'text': text, 'format': 'markdown'}
        attachments = []
        if with_image and image_url:
            attachments.append({'type': 'image', 'payload': {'url': image_url}})
        if buttons:
            attachments.append({'type': 'inline_keyboard', 'payload': {'buttons': buttons}})
        if attachments:
            payload['attachments'] = attachments
        return payload

    response = requests.post(url, headers=headers, json=build_payload(True), timeout=10, verify=False)
    print(f"📤 ОТВЕТ MAX API: {response.status_code} | {response.text}")

    # Если MAX не смог скачать картинку — отправляем то же сообщение без неё
    if response.status_code == 400 and 'image' in response.text.lower():
        print("⚠️ Картинка не загрузилась, повторяю отправку БЕЗ картинки")
        response = requests.post(url, headers=headers, json=build_payload(False), timeout=10, verify=False)
        print(f"📤 ОТВЕТ MAX API (без картинки): {response.status_code} | {response.text}")
    return response

# --- КОНСТРУКТОРЫ КНОПОК ---
def btn(text, payload):
    """Кнопка внутри бота (callback)"""
    return {"type": "callback", "text": text, "payload": payload}

def btn_link(text, url):
    """Кнопка-ссылка (открывает сайт в новой вкладке)"""
    return {"type": "link", "text": text, "url": url}

def btn_contact(text):
    """Кнопка запроса контакта пользователя"""
    return {"type": "request_contact", "text": text}


# --- МЕНЮ ---
def main_menu():
    return [
        [btn("🔥 Что делать при ЧС", "emergency_menu")],
        [btn("⚠️ Предупреждения", "warnings")],
        [btn("📞 Контакты", "contacts")],
        [btn_link("📝 Регистрация туристских групп", REGISTRATION_URL)]
    ]

def emergency_menu():
    return [
        [btn("🔥 Пожар", "fire")],
        [btn("🌊 Наводнение / Цунами", "flood")],
        [btn("🏠 Землетрясение", "earthquake")],
        [btn("❌ Отмена (Главное меню)", "main")]
    ]

def contacts_menu():
    return [
        [btn_contact("📱 Поделиться контактом")],
        [btn("🏠 Главное меню", "main")]
    ]

def back_menu():
    return [[btn("🏠 Главное меню", "main")]]


# --- ЛОГИКА ОТВЕТОВ ---
def handle_command(chat_id, command):
    command = str(command).strip().lower()

    if command in ['/start', 'main', 'главное меню', 'start']:
        send_message(chat_id,
            "**⚠️ БОТ В ТЕСТОВОМ РЕЖИМЕ**\n\n"
            "Здравствуйте! Это бот Агентства по делам ГО, ЧС и ПБ "
            "Сахалинской области.\nВыберите раздел:",
            main_menu(),
            image_url=START_IMAGE_URL)

    elif command in ['emergency_menu', 'что делать при чс']:
        send_message(chat_id,
            "**⚠️ ТЕСТОВЫЙ РЕЖИМ**\nЕсли есть угроза жизни — звоните `112`!",
            emergency_menu())

    elif command in ['fire', 'пожар']:
        send_message(chat_id,
            "**🔥 ПОЖАР: что делать**\n\n"
            "✅ **НЕМЕДЛЕННО:**\n"
            "• Позвоните `101` или `112`\n"
            "• Сообщите адрес и что горит\n"
            "• Выведите людей из помещения",
            back_menu())

    elif command in ['flood', 'наводнение', 'цунами']:
        send_message(chat_id,
            "**🌊 НАВОДНЕНИЕ / ЦУНАМИ: что делать**\n\n"
            "⚠️ При сигнале цунами **немедленно уходите от берега!**\n"
            "• Поднимитесь на возвышенность\n"
            "• Не возвращайтесь до отбоя тревоги",
            back_menu())

    elif command in ['earthquake', 'землетрясение']:
        send_message(chat_id,
            "**🏠 ЗЕМЛЕТРЯСЕНИЕ: что делать**\n\n"
            "✅ **ВО ВРЕМЯ ТОЛЧКОВ:**\n"
            "• В здании: встаньте в дверной проём или под прочный стол\n"
            "• Держитесь подальше от окон и шкафов",
            back_menu())

    elif command in ['warnings', 'предупреждения']:
        send_message(chat_id, WARNINGS_TEXT, back_menu())

    elif command in ['contacts', 'контакты']:
        send_message(chat_id,
            "**📞 Экстренные службы:**\n\n"
            "• `112` — единый номер вызова экстренных служб\n"
            "• `101` — пожарные\n"
            "• `102` — полиция\n"
            "• `103` — скорая помощь\n\n"
            "Нажмите кнопку ниже, чтобы оставить свой контакт для обратной связи:",
            contacts_menu())

    elif command in ['registration', 'регистрация туристских групп']:
        send_message(chat_id,
            "📝 Регистрация туристских групп осуществляется на сайте Агентства:",
            [[btn_link("Перейти к регистрации", REGISTRATION_URL)]])

    else:
        send_message(chat_id, "Я вас не понял. Используйте кнопки меню:", main_menu())


# --- ОБРАБОТЧИК WEBHOOK ---
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode('utf-8'))
            update_type = data.get('update_type')
            message = data.get('message', {})
            recipient = message.get('recipient', {})
            chat_id = recipient.get('chat_id') or data.get('chat_id')

            print(f"📨 Получено: {update_type} | chat_id={chat_id}")

            if update_type == 'bot_started':
                handle_command(chat_id, '/start')

            elif update_type == 'message_created':
                attachments = message.get('attachments', [])

                # Пользователь поделился контактом
                if any(a.get('type') == 'contact' for a in attachments):
                    send_message(chat_id,
                        "**✅ Спасибо!** Ваш контакт получен.\n"
                        "Специалист Агентства свяжется с вами.",
                        back_menu())
                else:
                    body = message.get('body', {})
                    text = body.get('text', '') if isinstance(body, dict) else str(body)
                    handle_command(chat_id, text)

            elif update_type == 'message_callback':
                callback = data.get('callback', {})
                payload = callback.get('payload') or data.get('payload')
                if payload:
                    handle_command(chat_id, payload)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))

        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'MAX Bot is running!')
