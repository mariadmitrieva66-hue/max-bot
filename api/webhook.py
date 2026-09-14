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
        print("⚠️ ОШИБКА: chat_id не найден, не могу отправить сообщение!")
        return
        
    url = f'{API_BASE}/messages'
    headers = {
        'Authorization': MAX_TOKEN,
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
    
    response = requests.post(url, headers=headers, json=payload, timeout=10, verify=False)
    print(f"📤 ОТВЕТ ОТ MAX (send_message): {response.status_code} {response.text}")

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
        send_message(chat_id, "️ ТЕСТОВЫЙ РЕЖИМ\nЕсли есть угроза жизни — звоните 112!", emergency_menu())
    elif command in ['fire', 'пожар']:
        send_message(chat_id, "🔥 ПОЖАР: что делать\n\n✅ НЕМЕДЛЕННО:\nПозвоните 101 или 112.\nСообщите адрес и что горит.", back_menu())
    elif command in ['flood', 'наводнение', 'цунами']:
        send_message(chat_id, "🌊 НАВОДНЕНИЕ / ЦУНАМИ: что делать\n\n⚠️ При сигнале цунами немедленно уходите от берега! Поднимитесь на возвышенность.", back_menu())
    elif command in ['earthquake', 'землетрясение']:
        send_message(chat_id, "🏠 ЗЕМЛЕТРЯСЕНИЕ: что делать\n\n✅ ВО ВРЕМЯ ТОЛЧКОВ:\nЕсли вы в здании: встаньте в дверной проём или под прочный стол. Держитесь подальше от окон.", back_menu())
    elif command in ['warnings', 'предупреждения']:
        send_message(chat_id, "⚠️ ВНИМАНИЕ!\n\nПо данным Сахалинского УГМС, сегодня в регионе ожидается усиление ветра до 20 м/с. Соблюдайте осторожность!", back_menu())
    elif command in ['contacts', 'контакты']:
        send_message(chat_id, "📞 Экстренные службы:\n\n112 - Единый номер вызова экстренных служб\n101 - Пожарные\n102 - Полиция\n103 - Скорая помощь", back_menu())
    elif command in ['registration', 'регистрация туристских групп']:
        send_message(chat_id, "📝 Функция регистрации туристских групп находится в разработке. Пожалуйста, позвоните в Агентство.", back_menu())
    else:
        send_message(chat_id, "Я вас не понял. Пожалуйста, используйте кнопки меню:", main_menu())

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode('utf-8'))
            
            # === ПОЛНЫЙ ДАМП ДАННЫХ БЕЗ СОКРАЩЕНИЙ ===
            print("=== ПОЛНЫЙ ДАМП ДАННЫХ ОТ MAX (БЕЗ СОКРАЩЕНИЙ) ===")
            print(json.dumps(data, ensure_ascii=False, indent=2))
            print("==================================================")
            
            update_type = data.get('update_type')
            
            # Умный поиск chat_id во всех возможных местах
            chat_id = data.get('chat_id')
            if not chat_id and 'message' in data:
                msg = data['message']
                chat_id = msg.get('chat_id') or msg.get('id')
                if 'chat' in msg and isinstance(msg['chat'], dict):
                    chat_id = msg['chat'].get('id')
                if 'recipient' in msg and isinstance(msg['recipient'], dict):
                    chat_id = msg['recipient'].get('chat_id')
            
            print(f"🔍 НАЙДЕННЫЙ chat_id: {chat_id}")

            if update_type == 'bot_started':
                handle_command(chat_id, '/start')
            elif update_type == 'message_created':
                msg = data.get('message', {})
                body = msg.get('body', {})
                
                if isinstance(body, dict):
                    text = body.get('text', '')
                else:
                    text = str(body)
                
                # Если текст пустой, возможно он лежит в другом месте
                if not text and 'text' in msg:
                    text = msg['text']
                    
                print(f"💬 ИТОГОВЫЙ ТЕКСТ ДЛЯ ОБРАБОТКИ: '{text}'")
                handle_command(chat_id, text)
                
            elif update_type == 'message_callback':
                payload = (data.get('callback', {}).get('payload') or 
                           data.get('payload') or 
                           data.get('message', {}).get('callback_payload'))
                if payload:
                    handle_command(chat_id, payload)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))

        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'MAX Bot is running!')
