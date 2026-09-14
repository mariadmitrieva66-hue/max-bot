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

# Форма МЧС России для регистрации туристских групп
REGISTRATION_URL = "https://forms.mchs.gov.ru/registration_tourist_groups"

# Официальный бот РСЧС Сахалинской области с предупреждениями
RSCHS_URL = "https://max.ru/id6501156338_gos"

# Прямая ссылка на герб для приветствия
START_IMAGE_URL = "https://raw.githubusercontent.com/mariadmitrieva66-hue/max-bot/main/emblem.png"

# Токен герба (заполните, если перейдёте на /api/upload); пока пусто — работает по ссылке
START_IMAGE_TOKEN = ""
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
        if with_image:
            if START_IMAGE_TOKEN:
                attachments.append({'type': 'image', 'payload': {'token': START_IMAGE_TOKEN}})
            elif image_url:
                attachments.append({'type': 'image', 'payload': {'url': image_url}})
        if buttons:
            attachments.append({'type': 'inline_keyboard', 'payload': {'buttons': buttons}})
        if attachments:
            payload['attachments'] = attachments
        return payload

    response = requests.post(url, headers=headers, json=build_payload(True), timeout=10, verify=False)
    print(f"📤 ОТВЕТ MAX API: {response.status_code} | {response.text}")

    if response.status_code == 400 and 'image' in response.text.lower():
        print("⚠️ Картинка не загрузилась, повторяю отправку БЕЗ картинки")
        response = requests.post(url, headers=headers, json=build_payload(False), timeout=10, verify=False)
        print(f"📤 ОТВЕТ MAX API (без картинки): {response.status_code} | {response.text}")
    return response


def btn(text, payload):
    """Кнопка внутри бота (callback)"""
    return {"type": "callback", "text": text, "payload": payload}

def btn_link(text, url):
    """Кнопка-ссылка (открывает сайт в новой вкладке)"""
    return {"type": "link", "text": text, "url": url}


def main_menu():
    return [
        [btn("🔥 Что делать при ЧС", "emergency_menu")],
        [btn_link("⚠️ Предупреждения (РСЧС)", RSCHS_URL)],
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

def back_menu():
    return [[btn("🏠 Главное меню", "main")]]


def handle_command(chat_id, command):
    command = str(command).strip().lower()

    if command in ['/start', 'start', 'main', 'главное меню']:
        send_message(chat_id,
            "**⚠️ БОТ В ТЕСТОВОМ РЕЖИМЕ**\n\n"
            "Здравствуйте! Это бот Агентства по делам ГО, ЧС и ПБ "
            "Сахалинской области.\n\n"
            "**💡 Как пользоваться:**\n"
            "• Выберите раздел через кнопки меню ниже\n"
            "• Или просто введите ключевые слова: `пожар`, `спасатели`, "
            "`градусник`, `огнетушитель`, `наводнение`, `цунами`, `землетрясение` "
            "— и мгновенно получите информацию, как действовать\n\n"
            "Для начала работы нажмите кнопку ниже или введите нужное слово:",
            main_menu(),
            image_url=START_IMAGE_URL)

    elif command in ['emergency_menu', 'что делать при чс', '/emergency_menu']:
        send_message(chat_id,
            "**⚠️ ТЕСТОВЫЙ РЕЖИМ**\nЕсли есть угроза жизни — звоните `112`!",
            emergency_menu())

    elif command in ['fire', 'пожар', '/fire']:
        send_message(chat_id,
            "**🔥 ПОЖАР: что делать**\n\n"
            "✅ **НЕМЕДЛЕННО:**\n"
            "• Позвоните `101` или `112`\n"
            "• Покиньте помещение, закрывая за собой двери;\n"
            "• Двигайтесь пригнувшись, дышите через влажную ткань;\n"
            "• На улице отойдите от здания на безопасное расстояние.\n\n"
            "❌ **НЕЛЬЗЯ:**\n"
            "• Пользоваться лифтом;\n"
            "• Возвращаться за вещами;\n"
            "• Открывать окна (приток кислорода усилит огонь);\n"
            "• Тушить электроприборы водой под напряжением.\n\n"
            "💡 **Если путь отрезан огнём:**\n"
            "• Закройтесь в комнате, заткните щели влажной тканью;\n"
            "• Подавайте сигналы из окна;\n"
            "• Ждите пожарных.",
            back_menu())

    elif command in ['flood', 'наводнение', 'цунами', '/flood']:
        send_message(chat_id,
            "**🌊 НАВОДНЕНИЕ / ЦУНАМИ: что делать**\n\n"
            "⚠️ При сигнале цунами **немедленно уходите от берега!**\n\n"
            "✅ **НЕМЕДЛЕННО:**\n"
            "• Поднимитесь на возвышенность или верхние этажи\n"
            "• Отключите газ, электричество, воду\n"
            "• Возьмите документы, лекарства, воду, фонарик\n"
            "• Отойдите от берега минимум на 2-3 км или поднимитесь на 30-40 м\n\n"
            "❌ **НЕЛЬЗЯ:**\n"
            "• Подходить к берегу, смотреть на цунами\n"
            "• Возвращаться к берегу после первой волны (волн может быть несколько)\n"
            "• Пользоваться автомобилем в зоне затопления\n"
            "• Пить воду из затопленных источников\n\n"
            "💡 **После цунами:**\n"
            "• Оставайтесь на возвышенности до отбоя тревоги\n"
            "• Слушайте официальные сообщения\n"
            "• Не заходите в повреждённые здания",
            back_menu())

    elif command in ['earthquake', 'землетрясение', '/earthquake']:
        send_message(chat_id,
            "**🏠 ЗЕМЛЕТРЯСЕНИЕ: что делать**\n\n"
            "✅ **ВО ВРЕМЯ ТОЛЧКОВ:**\n"
            "• Если вы в здании: встаньте в дверной проём или под прочный стол\n"
            "• Держитесь подальше от окон и тяжёлой мебели\n"
            "• НЕ пользуйтесь лифтом\n"
            "• Если вы на улице: отойдите от зданий, столбов, проводов\n\n"
            "✅ **ПОСЛЕ ТОЛЧКОВ:**\n"
            "• Проверьте, нет ли пострадавших\n"
            "• Перекройте газ, воду, электричество\n"
            "• Покиньте здание по лестнице\n"
            "• Не зажигайте спички (возможна утечка газа)\n\n"
            "❌ **НЕЛЬЗЯ:**\n"
            "• Паниковать и создавать давку\n"
            "• Возвращаться в здание без необходимости\n"
            "• Пользоваться телефоном без необходимости (линии перегружены)\n\n"
            "💡 **Будьте готовы к повторным толчкам (афтершокам)!**",
            back_menu())

    elif command in ['спасатели', '/спасатели']:
        send_message(chat_id,
            "**🚒 СПАСАТЕЛИ: когда и как вызывать**\n\n"
            "✅ **Звоните немедленно:**\n"
            "• `112` — единый номер вызова экстренных служб\n"
            "• `101` — пожарная охрана\n\n"
            "**Что сообщить диспетчеру:**\n"
            "• Точный адрес происшествия\n"
            "• Что произошло (пожар, ДТП, обрушение)\n"
            "• Есть ли пострадавшие\n"
            "• Ваши ФИО и номер телефона\n\n"
            "⚠️ Не кладите трубку первым — диспетчер может уточнить детали!",
            back_menu())

    elif command in ['градусник', 'ртуть', '/градусник']:
        send_message(chat_id,
            "**🌡️ РАЗБИЛСЯ ГРАДУСНИК (ртуть): что делать**\n\n"
            "⚠️ **ВАЖНО:** Ртуть и её пары ЯДОВИТЫ!\n\n"
            "• Выведите людей и животных из помещения\n"
            "• Наденьте резиновые перчатки\n"
            "• Для сбора используйте кисточку, мокрую газету, фольгу, хлебный мякиш, скотч\n"
            "• Соберите ртуть в банку с водой, плотно закройте\n"
            "• Обработайте место разлива раствором марганцовки, хлорной извести либо горячим мыльно‑содовым раствором (30 г соды + 40 г тёртого мыла на 1 л воды)\n"
            "• Когда ртуть собрана, помещение необходимо хорошо проветрить в течение 2-3 часов.",
            back_menu())

    elif command in ['огнетушитель', '/огнетушитель']:
        send_message(chat_id,
            "**🧯 ОГНЕТУШИТЕЛЬ: как пользоваться**\n\n"
            "✅ **ПОРЯДОК ДЕЙСТВИЙ:**\n"
            "1. Сорвите пломбу\n"
            "2. Выдерните чеку\n"
            "3. Направьте раструб на очаг возгорания\n"
            "4. Нажмите на рычаг\n\n"
            "⚠️ **ВАЖНО:**\n"
            "• Тушите с наветренной стороны\n"
            "• Начинайте с основания пламени\n"
            "• Не направляйте на людей\n"
            "• После использования — замените!",
            back_menu())

    elif command in ['warnings', 'предупреждения', '/warnings']:
        send_message(chat_id,
            "**⚠️ ПРЕДУПРЕЖДЕНИЯ**\n\n"
            "Официальные штормовые предупреждения и оперативная информация "
            "публикуются в боте РСЧС Сахалинской области.\n\n"
            "Нажмите кнопку ниже, чтобы перейти к первоисточнику:",
            [
                [btn_link("🌐 Открыть бот РСЧС Сахалинской области", RSCHS_URL)],
                [btn("🏠 Главное меню", "main")]
            ])

    elif command in ['contacts', 'контакты', '/contacts']:
        send_message(chat_id,
            "**📞 Экстренные службы:**\n\n"
            "• `112` — единый номер вызова экстренных служб\n"
            "• `101` — пожарные\n"
            "• `102` — полиция\n"
            "• `103` — скорая помощь",
            back_menu())

    elif command in ['registration', 'регистрация туристских групп', '/registration']:
        send_message(chat_id,
            "📝 Регистрация туристских групп осуществляется на портале МЧС России:",
            [[btn_link("Перейти к регистрации", REGISTRATION_URL)]])

    else:
        send_message(chat_id, "Я вас не понял. Используйте кнопки меню или ключевые слова:", main_menu())


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
                payload = data.get('payload')
                if payload == 'reg_tour':
                    send_message(chat_id,
                        "**📝 Регистрация туристских групп**\n\n"
                        "Для выхода на маршрут необходимо зарегистрировать "
                        "группу на портале МЧС России:",
                        [[btn_link("Перейти к регистрации", REGISTRATION_URL)]])
                else:
                    handle_command(chat_id, '/start')

            elif update_type == 'message_created':
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
