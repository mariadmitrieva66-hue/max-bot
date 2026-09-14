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
        
        result = {}
        
        # Проверка 1: действителен ли токен
        try:
            r1 = requests.get(f'{base}/me', headers=headers, timeout=10, verify=False)
            result['PROVERKA_TOKENA_me'] = {'status': r1.status_code, 'body': r1.text}
        except Exception as e:
            result['PROVERKA_TOKENA_me'] = {'error': str(e)}
        
        # Проверка 2: зарегистрирован ли webhook
        try:
            r2 = requests.get(f'{base}/subscriptions', headers=headers, timeout=10, verify=False)
            result['PROVERKA_PODPISKI_subscriptions'] = {'status': r2.status_code, 'body': r2.text}
        except Exception as e:
            result['PROVERKA_PODPISKI_subscriptions'] = {'error': str(e)}
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False, indent=2).encode('utf-8'))
