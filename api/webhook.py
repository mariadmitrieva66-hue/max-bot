import json
import os
import requests
import urllib3
from http.server import BaseHTTPRequestHandler

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MAX_TOKEN = os.getenv('MAX_TOKEN')
API_BASE = 'https://platform-api2.max.ru'

def send_message(chat_id: int, text: str, buttons: list = None):
    if not chat_id:
        print("⚠️ chat_id пустой, пропускаю отправку")
        return
        
    # ГЛАВНОЕ ИЗМЕНЕНИЕ: chat_id передается прямо в URL!
    url = f'{API_BASE}/messages?chat_id={chat_id}'
    
    headers = {
        'Authorization': MAX_TOKEN,
        'Content-Type': 'application/json'
    }
    
    # В теле запроса (payload) больше нет объекта 'recipient'!
    # Там остается только сам текст и кнопки.
    payload = {
        'text': text
    }
    
    if buttons:
        payload['attachments'] = [{
            'type': 'inline_keyboard',
            'payload': {'buttons': buttons}
        }]
    
    response = requests.post(url, headers=headers, json=payload, timeout=10, verify=False)
    print(f"📤 ОТВЕТ MAX API: {response.status_code} | {response.text}")
    return response

def btn(text: str, payload: str):
    return {"type": "callback", "text": text, "payload": payload}

def main_menu():
    return [
        [btn("🔥 Что делать при ЧС", "emergency_menu")],
        [btn("⚠️ Предупреждения", "warnings")],
        [btn("📞 Контакты", "contacts")],
        [btn("📝 Регистрация туристских групп", "registration")]
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

def handle_command(chat_id: int, command: str):
    command = str(command).strip().lower()
    
    if command in ['/start', 'main', 'главное меню', 'start']:
        send_message(chat_id, "⚠️ БОТ В ТЕСТОВОМ РЕЖИМЕ\n\nЗдравствуйте! Это тестовая версия бота Агентства по делам ГО, ЧС и ПБ Сахалинской области. Выберите раздел:", main_menu())
    elif command in ['emergency_menu', 'что делать при чс']:
        send_message(chat_id, "⚠️ ТЕСТОВЫЙ РЕЖИМ\nЕсли есть угроза жизни — звоните 112!", emergency_menu())
    elif command in ['fire', 'пожар']:
        send_message(chat_id, "🔥 ПОЖАР: что делать\n\n✅ НЕМЕДЛЕННО:\nПозвоните 101 или 112.\nСообщите адрес и что горит.", back_menu())
    elif command in ['flood', 'наводнение', 'цунами']:
        send_message(chat_id, "🌊 НАВОДНЕНИЕ / ЦУНАМИ: что делать\n\n⚠️ При сигнале цунами немедленно уходите от берега! Поднимитесь на возвышенность.", back_menu())
    elif command in ['earthquake', 'землетрясение']:
        send_message(chat_id, "🏠 ЗЕМЛЕТРЯСЕНИЕ: что делать\n\n✅ ВО ВРЕМЯ ТОЛЧКОВ:\nЕсли вы в здании: встаньте в дверной проём или под прочный стол.", back_menu())
    elif command in ['warnings', 'предупреждения']:
        send_message(chat_id, "⚠️ ВНИМАНИЕ!\n\nПо данным Сахалинского УГМС, сегодня в регионе ожидается усиление ветра до 20 м/с.", back_menu())
    elif command in ['contacts', 'контакты']:
        send_message(chat_id, "📞 Экстренные службы:\n\n112 - Единый номер вызова\n101 - Пожарные\n102 - Полиция\n103 - Скорая помощь", back_menu())
    elif command in ['registration', 'регистрация туристских групп']:
        send_message(chat_id, "📝 Функция регистрации в разработке. Позвоните в Агентство.", back_menu())
    else:
        send_message(chat_id, "Я вас не понял. Используйте кнопки меню:", main_menu())

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode('utf-8'))
            update_type = data.get('update_type')
            message = data.get('message', {})
            
            # === ПЕЧАТАЕМ ВСЕ КЛЮЧЕВЫЕ ПОЛЯ ===
            print("=== СТРУКТУРА UPDATE ===")
            print("update_type:", update_type)
            print("Ключи верхнего уровня:", list(data.keys()))
            print("Ключи внутри message:", list(message.keys()))
            
            # Печатаем recipient целиком
            recipient = message.get('recipient', {})
            print("🎯 ОБЪЕКТ recipient:", json.dumps(recipient, ensure_ascii=False))
            
            # Печатаем sender (отправитель)
            sender = message.get('sender', {})
            print("👤 ОБЪЕКТ sender:", json.dumps(sender, ensure_ascii=False))
            print("=========================")
            
            # === ПРАВИЛЬНОЕ ИЗВЛЕЧЕНИЕ chat_id ===
            chat_id = recipient.get('chat_id')
            
            print(f"✅ ИСПОЛЬЗУЕМЫЙ chat_id (из recipient): {chat_id}")

            if update_type == 'bot_started':
                user = data.get('user', {})
                chat_id = chat_id or user.get('user_id')
                handle_command(chat_id, '/start')
                
            elif update_type == 'message_created':
                body = message.get('body', {})
                text = body.get('text', '') if isinstance(body, dict) else str(body)
                print(f"💬 Текст: '{text}'")
                handle_command(chat_id, text)
                
            elif update_type == 'message_callback':
                callback = data.get('callback', {})
                payload = callback.get('payload') or data.get('payload')
                chat_id = callback.get('chat_id') or chat_id
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
