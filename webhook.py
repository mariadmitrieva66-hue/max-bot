import json
import os
import requests
from http.server import BaseHTTPRequestHandler

MAX_TOKEN = os.getenv('MAX_TOKEN')
API_BASE = 'https://platform-api2.max.ru'

# --- ФУНКЦИЯ ОТПРАВКИ СООБЩЕНИЙ ---
def send_message(chat_id: int, text: str, buttons: list = None):
    url = f'{API_BASE}/messages'
    headers = {
        'Authorization': MAX_TOKEN,  # Без слова Bearer!
        'Content-Type': 'application/json'
    }
    payload = {
        'recipient': {'chat_id': chat_id},
        'text': text
    }
    if buttons:
        payload['attachments'] = [{
            'type': 'inline_keyboard',
            'payload': {'buttons': buttons}
        }]
    
    requests.post(url, headers=headers, json=payload, timeout=10)

# --- КОНСТРУКТОР КНОПОК ---
def btn(text: str, payload: str):
    """Создает callback-кнопку"""
    return {"type": "callback", "text": text, "payload": payload}

# --- МЕНЮ (КНОПКИ) ---
def main_menu():
    return [
        [btn("🔥 Что делать при ЧС", "emergency_menu")],
        [btn("⚠️ Предупреждения", "warnings")],
        [btn("📞 Контакты", "contacts")],
        [btn(" Регистрация туристских групп", "registration")]
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

# --- ЛОГИКА ОТВЕТОВ (РОУТЕР) ---
def handle_command(chat_id: int, command: str):
    command = command.strip().lower()
    
    # Главное меню
    if command in ['/start', 'main', 'главное меню']:
        send_message(chat_id, 
            "⚠️ БОТ В ТЕСТОВОМ РЕЖИМЕ\n\nЗдравствуйте! Это тестовая версия бота Агентства по делам ГО, ЧС и ПБ Сахалинской области. Выберите раздел:", 
            main_menu())

    # Меню ЧС
    elif command in ['emergency_menu', 'что делать при чс']:
        send_message(chat_id, 
            "️ ТЕСТОВЫЙ РЕЖИМ\nЕсли есть угроза жизни — звоните 112!", 
            emergency_menu())

    # Пожар
    elif command in ['fire', 'пожар']:
        send_message(chat_id, 
            "🔥 ПОЖАР: что делать\n\n✅ НЕМЕДЛЕННО:\nПозвоните 101 или 112.\nСообщите адрес и что горит.", 
            back_menu())

    # Наводнение / Цунами
    elif command in ['flood', 'наводнение', 'цунами']:
        send_message(chat_id, 
            "🌊 НАВОДНЕНИЕ / ЦУНАМИ: что делать\n\n⚠️ При сигнале цунами немедленно уходите от берега! Поднимитесь на возвышенность.", 
            back_menu())

    # Землетрясение
    elif command in ['earthquake', 'землетрясение']:
        send_message(chat_id, 
            "🏠 ЗЕМЛЕТРЯСЕНИЕ: что делать\n\n✅ ВО ВРЕМЯ ТОЛЧКОВ:\nЕсли вы в здании: встаньте в дверной проём или под прочный стол. Держитесь подальше от окон.", 
            back_menu())

    # Предупреждения
    elif command in ['warnings', 'предупреждения']:
        send_message(chat_id, 
            "⚠️ ВНИМАНИЕ!\n\nПо данным Сахалинского УГМС, сегодня в регионе ожидается усиление ветра до 20 м/с. Соблюдайте осторожность!", 
            back_menu())

    # Контакты
    elif command in ['contacts', 'контакты']:
        send_message(chat_id, 
            "📞 Экстренные службы:\n\n112 - Единый номер вызова экстренных служб\n101 - Пожарные\n102 - Полиция\n103 - Скорая помощь", 
            back_menu())

    # Регистрация (заглушка)
    elif command in ['registration', 'регистрация туристских групп']:
        send_message(chat_id, 
            " Функция регистрации туристских групп находится в разработке. Пожалуйста, позвоните в Агентство.", 
            back_menu())
            
    # Неизвестная команда
    else:
        send_message(chat_id, "Я вас не понял. Пожалуйста, используйте кнопки меню:", main_menu())

# --- ОБРАБОТЧИК WEBHOOK (VERCEL) ---
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode('utf-8'))
            update_type = data.get('update_type')
            chat_id = data.get('chat_id')

            # 1. Пользователь нажал /start или зашел по диплинку
            if update_type == 'bot_started':
                handle_command(chat_id, '/start')

            # 2. Пользователь отправил текстовое сообщение
            elif update_type == 'message_created':
                text = data.get('message', {}).get('body', {}).get('text', '')
                handle_command(chat_id, text)

            # 3. Пользователь нажал на inline-кнопку (callback)
            elif update_type == 'message_callback':
                # MAX API может прислать payload в разных полях, проверяем все варианты
                payload = (data.get('callback', {}).get('payload') or 
                           data.get('payload') or 
                           data.get('message', {}).get('callback_payload'))
                if payload:
                    handle_command(chat_id, payload)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))

        except Exception as e:
            print(f"Error processing webhook: {e}")
            self.send_response(500)
            self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'MAX Bot is running!')
