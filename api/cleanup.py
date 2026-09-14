import os
import json
import requests
import urllib3
from http.server import BaseHTTPRequestHandler

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        MAX_TOKEN = os.getenv('MAX_TOKEN')
        base = 'https://platform-api2.max.ru'
        headers = {'Authorization': MAX_TOKEN}
        
        result = {'actions': []}
        
        # 1. Получаем все подписки
        r = requests.get(f'{base}/subscriptions', headers=headers, timeout=10, verify=False)
        subs_data = r.json() if r.status_code == 200 else {}
        subscriptions = subs_data.get('subscriptions', [])
        
        result['initial_count'] = len(subscriptions)
        
        # 2. Удаляем все подписки через DELETE (MAX поддерживает такой метод)
        for sub in subscriptions:
            url_to_delete = sub.get('url', '')
            
            # Пробуем удалить через DELETE с URL в query-параметре
            try:
                del_resp = requests.delete(
                    f'{base}/subscriptions',
                    headers=headers,
                    params={'url': url_to_delete},
                    timeout=10,
                    verify=False
                )
                result['actions'].append({
                    'deleted': url_to_delete,
                    'status': del_resp.status_code,
                    'response': del_resp.text
                })
            except Exception as e:
                result['actions'].append({
                    'failed': url_to_delete,
                    'error': str(e)
                })
        
        # 3. Регистрируем заново только наш webhook
        WEBHOOK_URL = os.getenv('WEBHOOK_URL')
        if WEBHOOK_URL:
            payload = {
                'url': WEBHOOK_URL,
                'update_types': ['message_created', 'bot_started', 'message_callback']
            }
            reg_resp = requests.post(
                f'{base}/subscriptions',
                headers={**headers, 'Content-Type': 'application/json'},
                json=payload,
                timeout=10,
                verify=False
            )
            result['new_subscription'] = {
                'url': WEBHOOK_URL,
                'status': reg_resp.status_code,
                'response': reg_resp.text
            }
        
        # 4. Проверяем финальный список
        r_final = requests.get(f'{base}/subscriptions', headers=headers, timeout=10, verify=False)
        result['final_subscriptions'] = r_final.json() if r_final.status_code == 200 else {}
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False, indent=2).encode('utf-8'))
