import os
import time
import requests
import urllib3
from http.server import BaseHTTPRequestHandler

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        base = os.getenv('UPSTASH_REDIS_REST_URL')
        token = os.getenv('UPSTASH_REDIS_REST_TOKEN')
        
        if not base or not token:
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write('<h1>База статистики не настроена</h1>'.encode('utf-8'))
            return
        
        headers = {'Authorization': f'Bearer {token}'}
        today = time.strftime('%Y-%m-%d')
        
        try:
            total_r = requests.get(f'{base}/get/stats:total:{today}', headers=headers, timeout=5).json()
            total = int(total_r.get('result', 0))
            users_r = requests.get(f'{base}/scard/stats:users:{today}', headers=headers, timeout=5).json()
            users = int(users_r.get('result', 0))
        except Exception as e:
            total, users = 0, 0
        
        html = f"""<!DOCTYPE html>
        <html><head><meta charset="UTF-8"><title>Статистика бота</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
            .stat {{ background: #f5f5f5; padding: 20px; margin: 10px 0; border-radius: 8px; }}
            .number {{ font-size: 32px; font-weight: bold; color: #2196F3; }}
        </style></head><body>
        <h1>📊 Статистика бота</h1>
        <p>Дата: <strong>{today}</strong></p>
        <div class="stat"><div>Всего сообщений сегодня</div><div class="number">{total}</div></div>
        <div class="stat"><div>Уникальных пользователей сегодня</div><div class="number">{users}</div></div>
        <p><em>Обновлено: {time.strftime('%H:%M:%S')}</em></p>
        </body></html>"""
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
