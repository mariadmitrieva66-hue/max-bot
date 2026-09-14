import os
import json
import requests
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        MAX_TOKEN = os.getenv('MAX_TOKEN')
        WEBHOOK_URL = os.getenv('WEBHOOK_URL')
        
        if not WEBHOOK_URL:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Missing WEBHOOK_URL env variable')
            return

        url = 'https://platform-api2.max.ru/subscriptions'
        headers = {
            'Authorization': MAX_TOKEN,
            'Content-Type': 'application/json'
        }
        payload = {
            'url': WEBHOOK_URL,
            'update_types': ['message_created', 'bot_started', 'message_callback']
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        result = {
            'status_code': response.status_code,
            'response': response.text
        }
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
