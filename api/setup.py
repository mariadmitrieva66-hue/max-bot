import os
import json
import requests
import urllib3
from http.server import BaseHTTPRequestHandler

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        MAX_TOKEN = os.getenv('MAX_TOKEN')
        url = 'https://platform-api2.max.ru/me/commands'
        headers = {'Authorization': MAX_TOKEN, 'Content-Type': 'application/json'}
        payload = {
            'commands': [
                {'name': 'start', 'description': 'Главное меню'},
                {'name': 'fire', 'description': 'Что делать при пожаре'},
                {'name': 'flood', 'description': 'Наводнение / цунами'},
                {'name': 'earthquake', 'description': 'Землетрясение'},
                {'name': 'warnings', 'description': 'Актуальные предупреждения'},
                {'name': 'contacts', 'description': 'Экстренные контакты'}
            ]
        }
        r = requests.patch(url, headers=headers, json=payload, timeout=10, verify=False)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(
            {'status': r.status_code, 'response': r.text},
            ensure_ascii=False).encode('utf-8'))
