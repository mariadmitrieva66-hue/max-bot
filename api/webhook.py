import json
import os
import time
import difflib
import requests
import urllib3
from http.server import BaseHTTPRequestHandler

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MAX_TOKEN = os.getenv('MAX_TOKEN')
API_BASE = 'https://platform-api2.max.ru'

# =====================================================
# ⚙️ НАСТРОЙКИ — РЕДАКТИРУЙТЕ ЗДЕСЬ
# =====================================================
REGISTRATION_URL = "https://forms.mchs.gov.ru/registration_tourist_groups"
RSCHS_URL = "https://max.ru/id6501156338_gos"
START_IMAGE_URL = "https://raw.githubusercontent.com/mariadmitrieva66-hue/max-bot/main/emblem.png"
START_IMAGE_TOKEN = ""
# =====================================================

EDDS_BODY = ("**Александровск-Сахалинский МО:** [8 (42434) 4-44-02](tel:+7424344402)\n"
    "**Анивский МО:** [8 (42441) 4-15-17](tel:+74244141517)\n"
    "**Долинский МО:** [8 (42442) 2-80-00](tel:+74244228000)\n"
    "**Корсаковский МО:** [8 (42435) 4-05-67](tel:+74243540567)\n"
    "**Курильский МО:** [8 (42454) 4-24-47](tel:+74245442447)\n"
    "**Макаровский МО:** [8 (42443) 5-05-13](tel:+74244350513)\n"
    "**Невельский МО:** [8 (42436) 6-09-39](tel:+74243660939)\n"
    "**Ногликский МО:** [8 (42444) 9-71-59](tel:+74244497159)\n"
    "**Охинский МО:** [8 (42437) 5-01-41](tel:+74243750141)\n"
    "**Поронайский МО:** [8 (42431) 4-25-85](tel:+74243142585)\n"
    "**Северо-Курильский МО:** [8 (42453) 2-11-54](tel:+74245321154)\n"
    "**Смирныховский МО:** [8 (42452) 4-26-67](tel:+74245242667)\n"
    "**Томаринский МО:** [8 (42446) 2-62-07](tel:+74244626207)\n"
    "**Тымовский МО:** [8 (42447) 9-10-44](tel:+74244791044)\n"
    "**Углегорский МО:** [8 (42432) 4-48-24](tel:+74243244824)\n"
    "**Холмский МО:** [8 (42433) 2-04-06](tel:+74243320406)\n"
    "**Южно-Курильский МО:** [8 (42455) 2-26-87](tel:+74245522687)\n"
    "**Город Южно-Сахалинск:** [112](tel:112)")

FIRSTAID_NOTE = ("_⚠️ Информация носит справочный характер и не заменяет практическое обучение. "
                 "Пройдите курс первой помощи (Центр скорой медицинской помощи и медицины катастроф Сахалинской области). "
                 "При сомнениях звоните в скорую: `103` / `112` — диспетчер подскажет по телефону._")


# =====================================================
# 📊 СТАТИСТИКА
# =====================================================
def stats_track(chat_id, event_type, command=None):
    base = os.getenv('UPSTASH_REDIS_REST_URL')
    token = os.getenv('UPSTASH_REDIS_REST_TOKEN')
    if not base or not token:
        return
    headers = {'Authorization': f'Bearer {token}'}
    today = time.strftime('%Y-%m-%d')
    try:
        requests.post(f'{base}/incr/stats:total:{today}', headers=headers, timeout=5)
        requests.post(f'{base}/sadd/stats:users:{today}', headers=headers, json=[chat_id], timeout=5)
        if command:
            requests.post(f'{base}/incr/stats:cmd:{command}:{today}', headers=headers, timeout=5)
        requests.post(f'{base}/set/user:{chat_id}:last', headers=headers,
                      json=[time.strftime('%Y-%m-%d %H:%M:%S')], timeout=5)
    except Exception as e:
        print(f'⚠️ Stats error: {e}')


def stats_get_summary():
    base = os.getenv('UPSTASH_REDIS_REST_URL')
    token = os.getenv('UPSTASH_REDIS_REST_TOKEN')
    if not base or not token:
        return "База статистики не настроена"
    headers = {'Authorization': f'Bearer {token}'}
    today = time.strftime('%Y-%m-%d')
    try:
        total_r = requests.get(f'{base}/get/stats:total:{today}', headers=headers, timeout=5).json()
        total_today = int(total_r.get('result') or 0)
        users_r = requests.get(f'{base}/scard/stats:users:{today}', headers=headers, timeout=5).json()
        users_today = int(users_r.get('result') or 0)
        top_cmds = {}
        for cmd in ['fire', 'flood', 'earthquake', 'edds', 'routes', 'checklists',
                    'lost_forest', 'terrorism', 'school', 'frostbite', 'bite',
                    'firstaid', 'cpr', 'seizure']:
            cmd_r = requests.get(f'{base}/get/stats:cmd:{cmd}:{today}', headers=headers, timeout=5).json()
            count = int(cmd_r.get('result') or 0)
            if count > 0:
                top_cmds[cmd] = count
        top_sorted = sorted(top_cmds.items(), key=lambda x: x[1], reverse=True)[:5]
        top_text = '\n'.join([f"• `{cmd}` — {count}" for cmd, count in top_sorted]) or 'Пока нет данных'
        return (f"**📊 СТАТИСТИКА**\n\n"
                f"**За сегодня ({today}):**\n"
                f"• Всего сообщений: **{total_today}**\n"
                f"• Уникальных пользователей: **{users_today}**\n\n"
                f"**Топ-5 команд сегодня:**\n{top_text}")
    except Exception as e:
        return f"Ошибка при получении статистики: {e}"


# =====================================================
# ОТПРАВКА СООБЩЕНИЙ
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
    return {"type": "callback", "text": text, "payload": payload}

def btn_link(text, url):
    return {"type": "link", "text": text, "url": url}


# =====================================================
# МЕНЮ
# =====================================================
def main_menu():
    return [
        [btn("🔥 Что делать при ЧС", 'emergency_menu')],
        [btn("🩺 Первая помощь", 'firstaid')],
        [btn("🚨 ЕДДС", 'edds')],
        [btn_link("⚠️ Предупреждения (РСЧС)", RSCHS_URL)],
        [btn("🏔️ Погода на маршрутах", 'routes')],
        [btn("📋 Чек-листы", 'checklists')],
        [btn("🎒 Школьникам", 'school')],
        [btn_link("📝 Регистрация туристских групп", REGISTRATION_URL)],
        [btn("📞 Контакты", 'contacts')],
    ]

def emergency_menu():
    return [
        [btn("🔥 Пожар", 'fire')],
        [btn("🌊 Наводнение / Цунами", 'flood')],
        [btn("🏠 Землетрясение", 'earthquake')],
        [btn("🌲 Потерялся в лесу", 'lost_forest')],
        [btn("🚨 Терроризм", 'terrorism')],
        [btn("🥶 Обморожение", 'frostbite')],
        [btn("🐍 Укус клеща/змеи", 'bite')],
        [btn("🎒 Школьникам", 'school')],
        [btn("❌ Отмена (Главное меню)", 'main')],
    ]

def back_menu():
    return [[btn("🏠 Главное меню", 'main')]]

def school_menu():
    return [
        [btn("😢 Меня обижают (буллинг)", 'bullying')],
        [btn("💬 Психологическая помощь", 'psyhelp')],
        [btn("⚠️ Незнакомцы", 'strangers')],
        [btn("🏠 Главное меню", 'main')],
    ]

def firstaid_menu():
    return [
        [btn("❤️ Сердечно-лёгочная реанимация", 'cpr')],
        [btn("🩸 Кровотечение и жгут", 'bleeding')],
        [btn("🦴 Переломы и вывихи", 'fracture')],
        [btn("🔥 Ожоги", 'burn')],
        [btn("😮 Человек подавился", 'choking')],
        [btn("🫀 Инсульт и инфаркт", 'stroke')],
        [btn("😴 Потеря сознания", 'unconscious')],
        [btn("⚡ Припадок эпилепсии", 'seizure')],
        [btn("🏠 Главное меню", 'main')],
    ]


# =====================================================
# НЕЧЁТКИЙ ПОИСК (опечатки и формы слов)
# =====================================================
COMMAND_WORDS = [
    'пожар', 'fire',
    'наводнение', 'цунами', 'flood', 'tsunami',
    'землетрясение', 'earthquake',
    'спасатели',
    'градусник', 'ртуть',
    'огнетушитель',
    'предупреждения', 'warnings',
    'контакты', 'contacts',
    'еддс', 'edds',
    'регистрация туристских групп', 'registration',
    'что делать при чс',
    'главное меню', 'main',
    'погода', 'маршруты',
    'привет', 'здравствуй', 'здравствуйте', 'добрый день', 'hello', 'hi',
    'чек-лист', 'чек-листы', 'списки', 'checklist',
    'потерялся', 'заблудился', 'заблудился в лесу',
    'терроризм', 'теракт', 'подозрительный предмет', 'бомба',
    'школьник', 'школьникам', 'школьница', 'школа',
    'буллинг', 'травля', 'обижают', 'задирают',
    'психолог', 'психологическая помощь', 'телефон доверия',
    'незнакомец', 'незнакомцы', 'чужой человек',
    'обморожение', 'замерз', 'холод', 'переохлаждение', 'отморозил',
    'укус', 'клещ', 'змея', 'укус клеща', 'укус змеи', 'укусила змея', 'укусил клещ',
    'первая помощь', 'перваяпомощь', 'спасение', 'реанимация', 'слр',
    'кровотечение', 'жгут', 'рана', 'кровь',
    'перелом', 'вывих', 'ушиб', 'сломал',
    'ожог', 'обжегся', 'ошпарился',
    'подавился', 'поперхнулся', 'heimlich',
    'инсульт', 'инфаркт', 'сердце', 'боль в груди',
    'без сознания', 'обморок', 'потерял сознание', 'упал в обморок',
    'эпилепсия', 'припадок', 'судороги', 'приступ', 'эпилептический приступ',
]


def _norm(s):
    return str(s).strip().lower().strip('.,!?;:()«»"\' ')


def fuzzy_command(text):
    low = _norm(text)
    if not low:
        return None
    if low in COMMAND_WORDS:
        return low
    for w in COMMAND_WORDS:
        if len(w) >= 4 and w in low:
            return w
    candidates = [low] + [c for c in low.split() if len(c) >= 4]
    best_word, best_ratio = None, 0.0
    for cand in candidates:
        for w in COMMAND_WORDS:
            if len(w) < 4:
                continue
            ratio = difflib.SequenceMatcher(None, cand, w).ratio()
            if ratio > best_ratio:
                best_ratio, best_word = ratio, w
    if best_ratio >= 0.75:
        print(f"🔮 Нечёткое совпадение: '{text}' -> '{best_word}' (уверенность {best_ratio:.2f})")
        return best_word
    return None


# =====================================================
# 🏔️ ТУРИСТИЧЕСКИЕ ТОЧКИ САХАЛИНСКОЙ ОБЛАСТИ
# =====================================================
ROUTE_CATS = {
    'mountains': '⛰️ Горы и хребты',
    'coast': '🌊 Побережье и бухты',
    'kurily': '🌋 Курильские острова',
    'nature': '🌲 Реки и источники',
}

ROUTES = {
    'chekhov': {'name': 'Пик Чехова', 'cat': 'mountains', 'lat': 47.0053, 'lon': 142.8403,
                'info': '1045 м, Сусунайский хребет, подъём от «Горного воздуха»'},
    'lyagushka': {'name': 'Скала Лягушка (Весточка)', 'cat': 'mountains', 'lat': 46.8689, 'lon': 142.8888,
                  'info': 'смотровые площадки с видом на Охотское море'},
    'zdanko': {'name': 'Хребет Жданко', 'cat': 'mountains', 'lat': 48.2496, 'lon': 142.5845,
               'info': 'лавовый хребет 13 км, Макаровский округ'},
    'velikan': {'name': 'Мыс Великан', 'cat': 'coast', 'lat': 46.6256, 'lon': 143.5145,
                'info': 'скальные арки и кекуры, Корсаковский округ'},
    'aniva': {'name': 'Маяк Анива', 'cat': 'coast', 'lat': 46.0193, 'lon': 143.4141,
              'info': 'заброшенный маяк на скале Сивучья, стык двух морей'},
    'busse': {'name': 'Озеро Буссе', 'cat': 'coast', 'lat': 46.5383, 'lon': 143.3331,
              'info': 'тёплая лагуна с устрицами и гребешком'},
    'tihaya': {'name': 'Бухта Тихая', 'cat': 'coast', 'lat': 48.0425, 'lon': 142.5428,
               'info': 'живописная бухта залива Терпения, восточное побережье'},
    'kudryavy': {'name': 'Вулкан Кудрявый (Итуруп)', 'cat': 'kurily', 'lat': 45.3839, 'lon': 148.8131,
                 'info': 'действующий вулкан, единственное в мире месторождение рения'},
    'baransky': {'name': 'Вулкан Баранского (Итуруп)', 'cat': 'kurily', 'lat': 45.1033, 'lon': 148.0156,
                 'info': 'действующий вулкан 1125 м, Кипящие озёра и фумаролы'},
    'mendeleev': {'name': 'Вулкан Менделеева (Кунашир)', 'cat': 'kurily', 'lat': 43.9764, 'lon': 145.7361,
                  'info': 'действующий вулкан 887 м, фумаролы и горячие источники'},
    'tyatya': {'name': 'Вулкан Тятя (Кунашир)', 'cat': 'kurily', 'lat': 44.3544, 'lon': 146.2512,
               'info': 'символ Кунашира, 1819 м, территория Курильского заповедника'},
    'belye': {'name': 'Белые скалы (Итуруп)', 'cat': 'kurily', 'lat': 45.0333, 'lon': 147.6167,
              'info': '28 км пемзовых белых скал вдоль Охотского моря'},
    'stolbchaty': {'name': 'Мыс Столбчатый (Кунашир)', 'cat': 'kurily', 'lat': 44.0256, 'lon': 145.6762,
                   'info': 'базальтовые колонны-«органы», визитная карточка Курил'},
    'krilion': {'name': 'Мыс Крыльон', 'cat': 'coast', 'lat': 46.0528, 'lon': 142.1250,
                'info': 'южная оконечность Сахалина, маяк, стык Охотского и Японского морей'},
    'kovrizhka': {'name': 'Гора Коврижка (Макаров)', 'cat': 'mountains', 'lat': 48.6330, 'lon': 142.7830,
                  'info': 'останец со смотровой площадкой над Макаровом и морем'},
    'bykov': {'name': 'Быковские пороги', 'cat': 'nature', 'lat': 47.3376, 'lon': 142.5155,
              'info': 'каскад порогов и мини-водопадов на реке Красноярке у пос. Быков'},
    'lesogorsk': {'name': 'Лесогорские термальные источники', 'cat': 'nature', 'lat': 49.3202, 'lon': 142.3898,
                  'info': 'горячие источники 35-39°C, Углегорский округ; после циклонов уточняйте проходимость'},
    'aikhor': {'name': 'Водопад Айхор', 'cat': 'nature', 'lat': 46.8883, 'lon': 142.8978,
               'info': 'живописный водопад у пос. Весточка, по пути к Охотскому морю'},
}

VERDICT_THRESHOLDS = {
    'mountains': {'warn_gust': 12, 'danger_gust': 18, 'warn_precip': 50, 'danger_precip': 80},
    'coast':     {'warn_gust': 14, 'danger_gust': 22, 'warn_precip': 50, 'danger_precip': 80},
    'kurily':    {'warn_gust': 16, 'danger_gust': 25, 'warn_precip': 50, 'danger_precip': 80},
    'nature':    {'warn_gust': 12, 'danger_gust': 18, 'warn_precip': 50, 'danger_precip': 80},
}


def day_verdict(gusts, precip, t_min, cat):
    th = VERDICT_THRESHOLDS.get(cat, VERDICT_THRESHOLDS['mountains'])
    if gusts >= th['danger_gust'] or precip >= th['danger_precip'] or t_min <= -18:
        return '❌'
    if gusts >= th['warn_gust'] or precip >= th['warn_precip'] or t_min <= -10:
        return '⚠️'
    return '✅'


def verdict_text(gusts, precip, t_min, cat):
    v = day_verdict(gusts, precip, t_min, cat)
    if v == '❌':
        return v + ' **ОПАСНО:** сильный ветер / непогода. Выход на маршрут лучше перенести.'
    if v == '⚠️':
        return v + ' **С ОСТОРОЖНОСТЬЮ:** условия пограничные. Тёплая одежда, снаряжение, сообщите родным маршрут.'
    return v + ' **Условия благоприятные.** Не забудьте воду, заряженный телефон и регистрацию группы.'


def fetch_route_weather(route_key):
    route = ROUTES.get(route_key)
    if not route:
        return None
    params = {
        'latitude': route['lat'],
        'longitude': route['lon'],
        'current': 'temperature_2m,wind_speed_10m,wind_gusts_10m',
        'daily': 'temperature_2m_max,temperature_2m_min,'
                 'precipitation_probability_max,wind_gusts_10m_max',
        'forecast_days': 3,
        'wind_speed_unit': 'ms',
        'timezone': 'auto',
    }
    try:
        r = requests.get('https://api.open-meteo.com/v1/forecast', params=params, timeout=10)
        if r.status_code != 200:
            print(f'⚠️ Open-Meteo: статус {r.status_code}')
            return None
        data = r.json()
    except Exception as e:
        print(f'⚠️ Open-Meteo ошибка: {e}')
        return None

    cur = data.get('current', {}) or {}
    daily = data.get('daily', {}) or {}
    days = daily.get('time', [])
    labels = ['Сегодня', 'Завтра', 'Послезавтра']
    cat = route.get('cat', 'mountains')

    lines = []
    for i in range(min(3, len(days))):
        t_min = (daily.get('temperature_2m_min') or [None] * 3)[i]
        t_max = (daily.get('temperature_2m_max') or [None] * 3)[i]
        precip = (daily.get('precipitation_probability_max') or [None] * 3)[i] or 0
        gust = (daily.get('wind_gusts_10m_max') or [None] * 3)[i] or 0
        emoji = day_verdict(gust, precip, t_min or 0, cat)
        lines.append(f"{emoji} **{labels[i]}:** {t_min}…{t_max}°C, "
                     f"осадки {precip}%, порывы до {gust} м/с")

    today_gust = (daily.get('wind_gusts_10m_max') or [None])[0] or cur.get('wind_gusts_10m') or 0
    today_precip = (daily.get('precipitation_probability_max') or [None])[0] or 0
    today_tmin = (daily.get('temperature_2m_min') or [None])[0] or 0

    return (f"**🏔️ {route['name']}**\n_{route['info']}_\n\n"
            f"**Сейчас:** {cur.get('temperature_2m')}°C, "
            f"ветер {cur.get('wind_speed_10m')} м/с (порывы {cur.get('wind_gusts_10m')})\n\n"
            "**Прогноз на 3 дня:**\n" + "\n".join(lines) + "\n\n"
            f"**Вердикт на сегодня:** {verdict_text(today_gust, today_precip, today_tmin, cat)}\n"
            f"_данные Open-Meteo, высота точки ≈ {data.get('elevation')} м_")


def routes_cat_menu():
    menu = [[btn(label, f'routes_cat|{key}')] for key, label in ROUTE_CATS.items()]
    menu.append([btn("🏠 Главное меню", 'main')])
    return menu


def routes_list_menu(cat):
    menu = []
    for key, route in ROUTES.items():
        if route['cat'] == cat:
            menu.append([btn(f"📍 {route['name']}", f'route_{key}')])
    menu.append([btn("⬅️ К категориям", 'routes')])
    menu.append([btn("🏠 Главное меню", 'main')])
    return menu


# =====================================================
# 📋 ЧЕК-ЛИСТЫ
# =====================================================
CHECKLISTS = {
    'forest': {
        'title': '🌲 Поход в лес',
        'items': [
            'Сообщил родным, куда и когда вернусь',
            'Заряженный телефон + пауэрбанк',
            'Спички/зажигалка в влагозащите',
            'Запас воды и перекус',
            'Нож, компас или офлайн-карты',
            'Яркая одежда, головной убор, репеллент',
            'Аптечка',
            'Свисток для сигнала',
            'Посмотрел прогноз погоды на день',
        ],
    },
    'fish_winter': {
        'title': '🧊 Зимняя рыбалка',
        'items': [
            'Уточнил сводку по льду (безопасно от 10 см)',
            'Сообщил родным место и время возврата',
            'Спасательное одеяло',
            'Верёвка 15-20 м',
            'Телефон заряжен, во внутреннем кармане',
            'Тёплая одежда, запасные перчатки',
            'Термос с горячим питьём',
            'Без алкоголя!',
            'Телефон ЕДДС округа — в разделе «ЕДДС»',
        ],
    },
    'fish_summer': {
        'title': '🎣 Летняя рыбалка',
        'items': [
            'Сообщил родным маршрут и время возврата',
            'Жилет на воде и с лодки',
            'Телефон в водозащитном чехле',
            'Вода, головной убор, солнцезащита',
            'Защита от клещей и гнуса',
            'Аптечка',
            'Проверил прогноз погоды и ветра',
            'Для лодки: запас топлива и вёсла',
            'Знаю точки съезда к берегу и телефон ЕДДС',
        ],
    },
    'car': {
        'title': '🚗 Поездка на машине',
        'items': [
            'Полный бак + запас топлива',
            'Запаска, домкрат, насос',
            'Зарядка для телефона в машине',
            'Вода, перекус, тёплый плед',
            'Аптечка, знак аварийной остановки, жилет',
            'Трос, провода для прикуривания',
            'Офлайн-карты в телефоне',
            'Сообщил родным маршрут и время прибытия',
            'Зимой: лопата, скребок, песок',
        ],
    },
    'gobag': {
        'title': '🎒 Тревожный чемоданчик',
        'items': [
            'Документы в водонепроницаемом пакете',
            'Вода 2-3 л на человека',
            'Продукты на 3 дня без холодильника',
            'Аптечка и личные лекарства',
            'Фонарик + запасные батарейки',
            'Пауэрбанк, радиоприёмник',
            'Тёплые вещи, дождевик',
            'Наличные (карты могут не работать)',
            'Запасные ключи, свисток, маска',
        ],
    },
    'storm': {
        'title': '🌪️ Дом перед циклоном',
        'items': [
            'Закрепил окна, убрал вещи с балкона и двора',
            'Запас воды и еды на 2-3 дня',
            'Зарядил телефоны и пауэрбанки',
            'Фонарики (свечи — с осторожностью)',
            'Перекрыл газ, набрал техводу в ванну',
            'Собрал тревожный чемоданчик (см. чек-лист)',
            'Машину — подальше от деревьев и щитов',
            'Телефоны ЕДДС и 112 — под рукой',
        ],
    },
}


def checklists_menu():
    menu = [[btn(cl['title'], f'check_show|{key}')] for key, cl in CHECKLISTS.items()]
    menu.append([btn("🏠 Главное меню", 'main')])
    return menu


def render_checklist(key, mask):
    cl = CHECKLISTS.get(key)
    if not cl:
        return None, None
    lines = []
    buttons = []
    done = 0
    for i, item in enumerate(cl['items']):
        checked = i < len(mask) and mask[i] == '1'
        if checked:
            done += 1
        sym = '✅' if checked else '⬜'
        lines.append(f"{sym} {item}")
        buttons.append([btn(f"{sym} {item}", f'check_toggle|{key}|{i}|{mask}')])
    total = len(cl['items'])
    text = (f"**📋 {cl['title']}**\nНажимайте на пункты, которые выполнили:\n\n"
            + "\n".join(lines)
            + f"\n\n**Готовность: {done} из {total}**")
    if done == total:
        text += "\n\n🏅 **Отлично! Вы полностью готовы.** Хорошей дороги и берегите себя!"
    buttons.append([btn("🔄 Начать заново", f'check_reset|{key}'),
                    btn("⬅️ Чек-листы", 'checklists')])
    return text, buttons


def send_or_edit(chat_id, message_id, text, buttons=None):
    if message_id:
        payload = {'text': text, 'format': 'markdown'}
        if buttons:
            payload['attachments'] = [{'type': 'inline_keyboard', 'payload': {'buttons': buttons}}]
        try:
            r = requests.put(f'{API_BASE}/messages/{message_id}',
                             headers={'Authorization': MAX_TOKEN, 'Content-Type': 'application/json'},
                             json=payload, timeout=10, verify=False)
            print(f'✏️ Редактирование сообщения: {r.status_code}')
            if r.status_code == 200:
                return r
        except Exception as e:
            print(f'⚠️ Редактирование не удалось: {e}')
    return send_message(chat_id, text, buttons)


# =====================================================
# ЛОГИКА ОТВЕТОВ
# =====================================================
def handle_command(chat_id, command, message_id=None):
    command = str(command).strip().lower()

    ADMIN_CHAT_IDS = ['111486830']
    if command in ['/stats', 'статистика', 'stats'] and str(chat_id) in ADMIN_CHAT_IDS:
        send_message(chat_id, stats_get_summary(), back_menu())
        return

    if command in ('start', 'main', '/start', 'главное меню', 'привет', 'здравствуй', 'здравствуйте', 'добрый день', 'hello', 'hi'):
        send_message(chat_id,
            "Привет!😊 Я бот Агентства по делам ГО, ЧС и ПБ Сахалинской области.\n\n"
            "**Для начала работы нажмите кнопку ниже или введите ключевое слово** 👇\n\n"
            "✅ Популярные запросы: пожар, спасатели, градусник, огнетушитель, наводнение, цунами, землетрясение, ЕДДС, погода, первая помощь.",
            main_menu())

    elif command in ['emergency_menu', 'что делать при чс', '/emergency_menu']:
        send_message(chat_id,
            "**⚠️ Если есть угроза жизни — звоните `112`!**\nВыберите тип ЧС:",
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
            "✅ **Звоните:**\n"
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
            "1. Выведите людей и животных из помещения\n"
            "2. Наденьте резиновые перчатки\n"
            "3. Для сбора используйте кисточку, мокрую газету, фольгу, хлебный мякиш, скотч\n"
            "4. Соберите ртуть в банку с водой, плотно закройте\n"
            "5 Обработайте место разлива раствором марганцовки, хлорной извести либо горячим мыльно-содовым раствором (30 г соды + 40 г тёртого мыла на 1 л воды)\n"
            "6. Когда ртуть собрана, помещение необходимо хорошо проветрить в течение 2-3 часов.",
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
                [btn("🏠 Главное меню", 'main')],
            ])

    elif command in ['contacts', 'контакты', '/contacts']:
        send_message(chat_id,
            "**📞 Экстренные службы:**\n\n"
            "• `112` — единый номер вызова экстренных служб\n"
            "• `101` — пожарные\n"
            "• `102` — полиция\n"
            "• `103` — скорая помощь\n"
            "• `104` — аварийная газовая служба\n"        
            "• `8 (4242) 240-304` — поисково-спасательный отряд\n"
            "• `8 (984) 184-10-10` — ПСО "СОВА"",
            back_menu())

    elif command in ['edds', 'еддс', '/edds']:
        send_message(chat_id,
            "**🚨 ЕДДС — Единые дежурные диспетчерские службы Сахалинской области**\n\n"
            "📞 **Нажмите на номер, чтобы позвонить:**\n\n" + EDDS_BODY,
            back_menu())

    elif command in ['registration', 'регистрация туристских групп', '/registration']:
        send_message(chat_id,
            "📝 Регистрация туристских групп осуществляется на портале МЧС России:",
            [[btn_link("Перейти к регистрации", REGISTRATION_URL)]])

    elif command in ['routes', 'погода', 'маршруты', '/routes']:
        send_message(chat_id,
            "**🏔️ ПОГОДА НА ТУРИСТИЧЕСКИХ ТОЧКАХ**\n\n"
            "Выберите категорию — бот покажет прогноз на 3 дня "
            "и вердикт о безопасности по каждому дню:",
            routes_cat_menu())

    elif command.startswith('routes_cat|'):
        cat = command.split('|')[1]
        send_message(chat_id,
            f"**{ROUTE_CATS.get(cat, 'Точки')}**\nВыберите точку:",
            routes_list_menu(cat))

    elif command.startswith('route_'):
        key = command[len('route_'):]
        text = fetch_route_weather(key)
        if text:
            cat = ROUTES.get(key, {}).get('cat', 'mountains')
            send_message(chat_id, text, routes_list_menu(cat))
        else:
            send_message(chat_id,
                "⚠️ Не удалось получить погоду сейчас. "
                "Попробуйте через пару минут.",
                routes_cat_menu())

    elif command in ['checklists', 'чек-лист', 'чек-листы', 'списки', '/checklist']:
        send_message(chat_id,
            "**📋 ЧЕК-ЛИСТЫ**\n\n"
            "Выберите ситуацию — бот покажет список. "
            "Нажимайте на пункты, чтобы отмечать выполненное:",
            checklists_menu())

    elif command.startswith('check_show|'):
        key = command.split('|')[1]
        cl = CHECKLISTS.get(key)
        if cl:
            text, buttons = render_checklist(key, '0' * len(cl['items']))
            send_message(chat_id, text, buttons)

    elif command.startswith('check_toggle|'):
        try:
            parts = command.split('|')
            key, idx, mask = parts[1], int(parts[2]), list(parts[3])
            if 0 <= idx < len(mask):
                mask[idx] = '0' if mask[idx] == '1' else '1'
            text, buttons = render_checklist(key, ''.join(mask))
            send_or_edit(chat_id, message_id, text, buttons)
        except Exception as e:
            print(f'❌ Чек-лист ошибка: {e}')

    elif command.startswith('check_reset|'):
        key = command.split('|')[1]
        cl = CHECKLISTS.get(key)
        if cl:
            text, buttons = render_checklist(key, '0' * len(cl['items']))
            send_or_edit(chat_id, message_id, text, buttons)

    elif command in ['lost_forest', 'потерялся', 'заблудился', 'заблудился в лесу']:
        send_message(chat_id,
            "**🌲 ПОТЕРЯЛСЯ В ЛЕСУ: что делать**\n\n"
            "✅ **НЕМЕДЛЕННО:**\n"
            "• **Остановись и не паникуй.** Бежать наугад — худшая стратегия, так только уходишь дальше.\n"
            "• **Позвони `112`.** Работает даже без сим-карты, без денег на счету и вне зоны своего оператора.\n"
            "• **Сообщи:** где примерно находишься, когда вышел, что видишь вокруг.\n"
            "• **Оставайся на месте**, если не знаешь точного направления. Так тебя быстрее найдут.\n\n"
            "🧭 **Как выйти самостоятельно:**\n"
            "• Иди к **линейному ориентиру**: река, дорога, просека, ЛЭП, железная дорога.\n"
            "• Двигайся **вниз по склону** — там чаще бывают ручьи и дороги.\n"
            "• **Не ходи ночью** — остановись, разведи костёр, устрой убежище.\n\n"
            "📣 **Подавай сигналы:**\n"
            "• **Свисток** (3 коротких свистка — международный сигнал бедствия).\n"
            "• Крик: 3 раза громко, потом пауза, слушай ответ.\n"
            "• **Костёр с дымом** — днём добавь сырых веток для густого дыма.\n"
            "• Если слышишь **вертолёт** — выйди на открытую поляну, размахивай ярким предметом.\n"
            "• **Береги заряд телефона**: пиши СМС вместо звонков, выключи экран, убери в тепло.\n"
            "• **Не пей воду из сомнительных водоёмов** без кипячения.\n\n"
            "⚠️ **Главное правило:** перед выходом в лес всегда говори родным, куда идёшь и когда вернёшься. Тогда поиск начнётся сразу.",
            back_menu())

    elif command in ['terrorism', 'терроризм', 'теракт', 'подозрительный предмет', 'бомба']:
        send_message(chat_id,
            "**🚨 ТЕРРОРИСТИЧЕСКАЯ УГРОЗА**\n\n"
            "**🎒 Нашёл подозрительный предмет (сумка, коробка, пакет с проводами):**\n"
            "• **НЕ трогай, НЕ вскрывай, НЕ передвигай!**\n"
            "• Отойди на безопасное расстояние — **минимум 100 метров**.\n"
            "• Позвони `112`, сообщи: где нашёл, как выглядит, когда обнаружил.\n"
            "• Предупреди окружающих, но **не создавай панику**.\n"
            "• Дождись спецслужбы, по возможности не подпускай других людей.\n"
            "• **Не пользуйся телефоном рядом с предметом** — отойди подальше.\n\n"
            "**🏢 Захват заложников / стрельба:**\n"
            "• **Не сопротивляйся**, выполняй требования, не провоцируй.\n"
            "• **Не смотри в глаза**, не делай резких движений.\n"
            "• Дыши спокойно, **экономь силы**.\n"
            "• Если есть возможность **спрятаться** — сделай это бесшумно.\n"
            "• **При штурме:** ложись на пол лицом вниз, закрой голову руками, **не беги к выходу**.\n"
            "• Главная цель — **выжить и дождаться освобождения**.\n"
            "• Запомни: сколько преступников, вооружены ли, куда смотрят.\n"
            "• После освобождения — **не спеши вставать**, следуй указаниям спецслужб.",
            back_menu())

    elif command in ['frostbite', 'обморожение', 'замерз', 'холод', 'переохлаждение', 'отморозил']:
        send_message(chat_id,
            "**🥶 ОБМОРОЖЕНИЕ / ПЕРЕОХЛАЖДЕНИЕ: что делать**\n"
            "_Признаки обморожения: кожа побелела, потеряла чувствительность, появились белые пятна._\n"
            "✅ **НЕМЕДЛЕННО:**\n"
            "• **Уйдите в тепло** как можно скорее.\n"
            "• **Снимите мокрую и тесную одежду**, переоденьтесь в сухое.\n"
            "• **Пейте тёплое** (не горячее!): чай, воду, бульон. **Не алкоголь!**\n"
            "• **Согревайте постепенно**: тёплые руки другого человека, тёплая (не горячая) вода.\n"
            "• **Согревайте от центра к краям**: сначала туловище, потом руки и ноги.\n\n"
            "❌ **НЕЛЬЗЯ:**\n"
            "• **Растирать снегом** — это повреждает кожу и сосуды.\n"
            "• **Греть у открытого огня** или батареи — можно получить ожог, кожа не чувствует.\n"
            "• **Пить алкоголь** — даёт ложное ощущение тепла, но усиливает потерю тепла.\n"
            "• **Прокалывать пузыри** на обмороженной коже.\n\n"
            "⚠️ **Обязательно к врачу, если:**\n"
            "• Кожа побелела и не восстанавливает цвет.\n"
            "• Появились пузыри.\n"
            "• Сильная боль или полная потеря чувствительности.\n"
            "• Обморозились лицо, уши, пальцы.\n"
            "• Признаки переохлаждения: сильная дрожь, спутанность сознания, сонливость.\n"
            "🚑 **При сильном обморожении или переохлаждении вызывайте скорую: `103` или `112`**.",
            back_menu())

    elif command in ['bite', 'укус', 'клещ', 'змея', 'укус клеща', 'укус змеи', 'укусила змея', 'укусил клещ']:
        send_message(chat_id,
            "**🐍 УКУС КЛЕЩА / ЗМЕИ: что делать**\n\n"
            "**🦟 УКУС КЛЕЩА:**\n"
            "• **Не паникуйте.** Клещи на Сахалине могут переносить энцефалит и боррелиоз.\n"
            "• **Удалите клеща как можно скорее**: пинцетом или ниткой, **выкручивая** против часовой стрелки.\n"
            "• **НЕ давите** клеща пальцами и **НЕ мажьте маслом** — это повышает риск заражения.\n"
            "• **Сохраните клеща** в баночке для анализа (положите в холодильник).\n"
            "• **Обратитесь к врачу** в течение 72 часов — решат вопрос о прививке/иммуноглобулине.\n"
            "• **Следите за самочувствием** 2-3 недели: температура, пятно вокруг укуса, слабость → к врачу.\n\n"
            "**🐍 УКУС ЗМЕИ:**\n"
            "• **НЕ паникуйте и двигайтесь как можно меньше** — это замедлит распространение яда.\n"
            "• **НЕ накладывайте жгут** выше укуса — это ухудшит состояние.\n"
            "• **НЕ отсасывайте яд ртом** и **НЕ прижигайте** рану.\n"
            "• **Обеспечьте покой**: уложите пострадавшего, обездвижьте укушенную руку/ногу.\n"
            "• **Давайте много пить** (воду, не алкоголь).\n"
            "• **Запомните**, как выглядела змея, или сфотографируйте её (издалека).\n"
            "• **Снимите украшения** с укушенной конечности (кольца, браслеты) — она отечёт.\n"
            "🚑 **Срочно к врачу или вызовите скорую: `103` или `112`**. Противоядие вводят только в больнице.\n"
            "⚠️ **Профилактика:** в лесу — закрытая обувь, плотные брюки, осмотр каждые 15-20 минут, репеллент.",
            back_menu())

    elif command in ['firstaid', 'первая помощь', 'перваяпомощь', 'спасение']:
        send_message(chat_id,
            "**🩺 ПЕРВАЯ ПОМОЩЬ**\n"
            "_Раздел подготовлен по современным протоколам первой помощи "
            "(Европейский реанимационный совет ERC, Американская кардиологическая ассоциация AHA, "
            "материалы Российского Красного Креста)._\n\n"
            "⚠️ **Помните главное:**\n"
            "• При угрозе жизни **сначала позвоните в скорую: `103` или `112`** — "
            "диспетчер будет вести вас по телефону, пока едет бригада.\n"
            "• Текстовая инструкция **не заменяет практических занятий** на манекене с инструктором.\n"
            "• Если вас учили иначе — **следуйте своей подготовке**.\n\n"
            "Выберите тему:",
            firstaid_menu())

    elif command in ['cpr', 'реанимация', 'слр', 'сердечно-лёгочная реанимация']:
        send_message(chat_id,
            "**❤️ СЕРДЕЧНО-ЛЁГОЧНАЯ РЕАНИМАЦИЯ (СЛР)**\n"
            "_Применяется, если человек не отвечает и не дышит нормально._\n"
            "✅ **1.** Громко окликните, слегка потрясите за плечо — есть реакция?\n"
            "✅ **2.** Проверьте дыхание: смотрите на грудь **до 10 секунд**. "
            "**Если сомневаетесь, дышит ли человек — считайте, что не дышит.**\n"
            "✅ **3.** **Позвоните `103` / `112`** (или попросите рядом стоящих), включите громкую связь — "
            "диспетчер будет подсказывать шаги.\n"
            "✅ **4.** Уложите на спину на твёрдую поверхность.\n"
            "✅ **5.** Надавливания: основание ладони на центр груди, руки прямые, давите весом корпуса "
            "на глубину около 5-6 см в темпе 100-120 в минуту.\n"
            "✅ **6.** Если обучены вдохам: чередуйте **30 надавливаний : 2 вдоха**. "
            "Если не обучены или сомневаетесь — **непрерывные надавливания без пауз**: это тоже эффективно.\n"
            "⚠️ Продолжайте до прибытия скорой или явных признаков жизни.\n"
            "👶 Детям — одной рукой, младенцам — двумя пальцами; "
            "если нет подготовки, выполняйте указания диспетчера по телефону.\n\n" + FIRSTAID_NOTE,
            firstaid_menu())

    elif command in ['bleeding', 'кровотечение', 'жгут', 'рана', 'кровь']:
        send_message(chat_id,
            "**🩸 КРОВОТЕЧЕНИЕ: первая помощь**\n"
            "✅ **Первое действие при любом сильном кровотечении:** прижмите рану чистой тканью или салфеткой "
            "и удерживайте давление; при сильном кровотечении параллельно звоните `103` / `112`.\n"
            "**🔴 Артериальное (алая кровь бьёт струёй/пульсирует):**\n"
            "• Если прямое прижимание не помогает — жгут **выше раны**, поверх одежды или ткани.\n"
            "• **Обязательно запишите время наложения** (на коже, повязке, бумаге) и сообщите его медикам.\n"
            "• **Не ослабляйте и не снимайте жгут самостоятельно** — это делают только медики.\n"
            "• По общепринятым ориентирам время жгута ограничено (около 1 часа, в холод — меньше), "
            "но окончательное решение принимают врачи; ваша задача — записать время и как можно быстрее передать человека бригаде.\n"
            "**🔵 Венозное (тёмная кровь течёт ровно):**\n"
            "• Давящая повязка: салфетка на рану, плотно забинтовать; если промокает — **не снимать**, добавлять слои сверху.\n"
            "• По возможности приподнимите конечность.\n"
            "⚠️ **Не извлекайте** предмет, торчащий из раны, — зафиксируйте его повязкой вокруг.\n"
            "🚑 Жгут, раны головы/шеи/живота, непроходящее кровотечение — скорая немедленно.\n\n" + FIRSTAID_NOTE,
            firstaid_menu())

    elif command in ['fracture', 'перелом', 'вывих', 'ушиб', 'сломал']:
        send_message(chat_id,
            "**🦴 ПЕРЕЛОМЫ И ВЫВИХИ**\n"
            "⚠️ **Подозрение на травму позвоночника** (падение с высоты, ДТП, ныряние): "
            "**не перемещайте человека**, поддерживайте голову неподвижно, звоните `103` / `112` и ждите бригаду.\n"
            "✅ **Перелом конечности:**\n"
            "• Обездвижьте **в том положении, как есть**: шина из подручных средств (доска, журнал, зонт), "
            "захватывая суставы выше и ниже повреждения.\n"
            "• **Не пытайтесь** выпрямить конечность или вправить вывих самостоятельно.\n"
            "• Холод на место травмы через ткань, 15-20 минут.\n"
            "✅ **Открытый перелом (кость видна в ране):**\n"
            "• **Не трогайте кость**, наложите стерильную повязку вокруг раны, остановите кровотечение "
            "(см. «Кровотечение»), обездвижьте.\n"
            "🚑 Подозрение на перелом позвоночника, таза, черепа; открытый перелом; сильная боль или деформация — скорая.\n\n" + FIRSTAID_NOTE,
            firstaid_menu())

    elif command in ['burn', 'ожог', 'обжегся', 'ошпарился']:
        send_message(chat_id,
            "**🔥 ОЖОГИ**\n"
            "✅ **Главное действие:** охлаждайте место ожога **прохладной проточной водой 10-20 минут** "
            "(не ледяной!). Это ограничивает повреждение тканей.\n"
            "• Снимите украшения и тесную одежду **вокруг** ожога до начала отёка.\n"
            "• Накройте чистой неворсистой тканью или стерильной салфеткой, не приклеивайте и не смазывайте.\n"
            "• Давайте пить воду.\n"
            "❌ **Не делайте:** масло, жир, сметана, кремы; лёд; прокалывание пузырей; отдирание прилипшей одежды.\n"
            "✅ **Химический ожог:** промывайте проточной водой 20 минут и более, удалите одежду с веществом.\n"
            "🚑 Скорая, если: ожог больше ладони пострадавшего; лицо, шея, кисти, стопы, пах; "
            "белая или обугленная кожа; ребёнок или пожилой человек; признаки шока (бледность, спутанность).\n\n" + FIRSTAID_NOTE,
            firstaid_menu())

    elif command in ['choking', 'подавился', 'поперхнулся', 'heimlich']:
        send_message(chat_id,
            "**😮 ЧЕЛОВЕК ПОДАВИЛСЯ**\n"
            "✅ Если человек **может кашлять и говорить** — поощряйте кашель, оставайтесь рядом, не бейте по спине.\n"
            "✅ Если кашель неэффективен, говорить и дышать не может:\n"
            "• Наклоните вперёд и сделайте **5 ударов** основанием ладони между лопаток.\n"
            "• Не помогло — **5 толчков в живот (приём Геймлиха):** сзади, кулак выше пупка и ниже рёбер, "
            "второй рукой обхватить кулак, резкие толчки внутрь и вверх.\n"
            "• Чередуйте 5 ударов / 5 толчков, пока предмет не выйдет или не приедет скорая.\n"
            "✅ Если сознание потеряно: уложите, звоните `103` / `112`, начните СЛР (см. «Реанимация»).\n"
            "👶 Младенцам до года: лицом вниз на предплечье, голова ниже тела, 5 ударов между лопаток; "
            "затем 5 надавливаний двумя пальцами по центру груди. **По возможности выполняйте под руководством диспетчера по телефону.**\n\n" + FIRSTAID_NOTE,
            firstaid_menu())

    elif command in ['stroke', 'инсульт', 'инфаркт', 'сердце', 'боль в груди']:
        send_message(chat_id,
            "**🫀 ИНСУЛЬТ И ИНФАРКТ: как распознать**\n"
            "**🧠 Инсульт — тест УДАР (международный FAST):**\n"
            "• **У**лыбка — попросите улыбнуться: лицо перекошено, уголок рта опущен.\n"
            "• **Д**вижение — попросите поднять обе руки: одна слабая или не поднимается.\n"
            "• **А**ртикуляция — попросите сказать простую фразу: речь невнятная.\n"
            "• **Р**ешение — при ХОТЯ БЫ ОДНОМ признаке **немедленно звоните `103`** и запомните время появления симптомов.\n"
            "**❤️ Инфаркт — признаки:** давящая или жгучая боль за грудиной дольше 15 минут, "
            "отдающая в руку, челюсть, под лопатку; холодный пот, страх, нехватка воздуха.\n"
            "✅ **Действия:** усадите полусидя, обеспечьте воздух, не давайте ходить и нагружаться; "
            "**выполняйте указания диспетчера скорой по телефону**, в том числе по лекарствам.\n"
            "❌ При подозрении на инсульт **не давайте** еду, воду и таблетки.\n"
            "🚑 Оба состояния требуют скорой **немедленно** — счёт идёт на минуты.\n\n" + FIRSTAID_NOTE,
            firstaid_menu())

    elif command in ['unconscious', 'без сознания', 'обморок', 'потерял сознание', 'упал в обморок']:
        send_message(chat_id,
            "**😴 ПОТЕРЯ СОЗНАНИЯ**\n"
            "✅ Проверьте реакцию (окликните, потрясите за плечо) и дыхание (до 10 секунд).\n"
            "**🟢 Дышит, но без сознания:** переверните **на бок** (устойчивое боковое положение), "
            "ртом вниз; укройте; следите за дыханием до прибытия скорой.\n"
            "**🔴 Не дышит:** звоните `103` / `112` и начинайте СЛР (см. «Реанимация»).\n"
            "❌ Не давайте воду и таблетки, не используйте нашатырный спирт, не бейте по щекам.\n"
            "✅ Обычный обморок (духота, испуг, голод): уложите, приподнимите ноги, обеспечьте воздух; "
            "если не приходит в себя за 1-2 минуты или обморок после травмы головы — скорая.\n"
            "🚑 Скорая всегда, если: нет дыхания; травма головы или шеи; судороги; беременность, диабет, пожилой возраст.\n\n" + FIRSTAID_NOTE,
            firstaid_menu())

    elif command in ['seizure', 'эпилепсия', 'припадок', 'судороги', 'приступ', 'эпилептический приступ']:
        send_message(chat_id,
            "**⚡ ПРИПАДОК ЭПИЛЕПСИИ: как действовать**\n"
            "_Во время приступа человек не управляет собой. Ваша задача — не дать ему получить травму._\n"
            "✅ **ВО ВРЕМЯ ПРИСТУПА:**\n"
            "• **Сохраняйте спокойствие и оставайтесь рядом.** Засеките время начала приступа.\n"
            "• **Уберите опасные предметы** вокруг (мебель, острые вещи, стекло).\n"
            "• **Подложите под голову что-то мягкое и плоское** (свёрнутую одежду, сумку).\n"
            "• Ослабьте тесную одежду у шеи, снимите очки.\n"
            "• **НЕ удерживайте человека и не прижимайте конечности** — это не останавливает приступ "
            "и может привести к переломам.\n"
            "• **НЕ кладите ничего в рот** (ни ложку, ни пальцы): человек не может проглотить язык, "
            "а вот сломать зубы и челюсть при попытке — легко.\n"
            "• **НЕ давайте** воду, таблетки, нашатырный спирт во время приступа.\n"
            "✅ **ПОСЛЕ ОКОНЧАНИЯ ПРИСТУПА:**\n"
            "• Переверните человека **на бок** (устойчивое боковое положение), ртом вниз.\n"
            "• Проверьте дыхание; оставайтесь рядом до полного возвращения сознания.\n"
            "• Говорите спокойно, объясните, что произошло; **не давайте еду и питьё**, пока сознание не вернулось полностью.\n"
            "• Дайте отдохнуть: после приступа обычны слабость, сонливость и спутанность — это проходит.\n"
            "🚑 **Немедленно вызывайте скорую `103` / `112`, если:**\n"
            "• Приступ длится **более 5 минут**.\n"
            "• Приступы повторяются один за другим без возвращения сознания.\n"
            "• Это **первый в жизни** приступ у человека.\n"
            "• Приступ произошёл **в воде** или человек получил травму.\n"
            "• Человек беременен, болен диабетом или дыхание не восстановилось после приступа.\n\n" + FIRSTAID_NOTE,
            firstaid_menu())

    elif command in ['school', 'школьник', 'школьникам', 'школьница', 'школа']:
        send_message(chat_id,
            "**🎒 РАЗДЕЛ ДЛЯ ШКОЛЬНИКОВ**\n"
            "_Привет! Если тебе нужна помощь или совет — ты по адресу. Выбери ситуацию:_",
            school_menu())

    elif command in ['bullying', 'буллинг', 'травля', 'обижают', 'задирают']:
        send_message(chat_id,
            "**😢 МЕНЯ ОБИЖАЮТ (БУЛЛИНГ): что делать**\n"
            "_Помни: ты НИ В ЧЁМ не виноват. Травля — это проблема обидчика, а не твоя._\n"
            "✅ **Что делать:**\n"
            "• **Расскажи взрослому**, которому доверяешь: родителю, учителю, школьному психологу, тренеру.\n"
            "• **Сохраняй доказательства**: скриншоты сообщений, фото, записи.\n"
            "• **Не отвечай агрессией и не мсти** — это может усилить травлю.\n"
            "• **Заблокируй обидчика** в соцсетях и мессенджерах.\n"
            "• Держись рядом с друзьями — вместе безопаснее.\n"
            "• Если травля происходит в интернете — пожалуйся администрации сайта.\n"
            "• Если есть угроза здоровью или вымогают деньги/вещи — **сразу звони `112`**.\n"
            "📞 **Детский телефон доверия: `8-800-2000-122`** (бесплатно, анонимно, круглосуточно)\n"
            "_Ты не один. Взрослые могут и должны помочь._",
            school_menu())

    elif command in ['psyhelp', 'психолог', 'психологическая помощь', 'телефон доверия']:
        send_message(chat_id,
            "**💬 ПСИХОЛОГИЧЕСКАЯ ПОМОЩЬ: куда обратиться**\n"
            "_Просить помощь — это не слабость, а смелость. Ты не обязан справляться со всем один._\n"
            "✅ **Куда можно обратиться:**\n"
            "• **Телефон доверия для детей и подростков: `8-800-2000-122`**\n"
            "  Бесплатно, анонимно, круглосуточно. Можно звонить с любого телефона.\n"
            "• **Школьный психолог** — есть в каждой школе, обращаются бесплатно.\n"
            "• **Родители или другой взрослый**, которому доверяешь: бабушка, тётя, тренер.\n"
            "• **Онлайн-чат телефона доверия** — если неудобно говорить голосом.\n"
            "• В экстренной ситуации (себе или близким) — звони `112`.\n"
            "🤝 **Когда стоит обратиться:**\n"
            "• Если долго грустно, тревожно или страшно.\n"
            "• Если поссорился с друзьями или родителями.\n"
            "• Если кто-то обижает или давит на тебя.\n"
            "• Если тяжело справиться с учёбой.\n"
            "• Если появились мысли о том, что жизнь не имеет смысла — **обязательно позвони `8-800-2000-122`**, там помогут.",
            school_menu())

    elif command in ['strangers', 'незнакомец', 'незнакомцы', 'чужой человек']:
        send_message(chat_id,
            "**⚠️ НЕЗНАКОМЦЫ: как вести себя**\n"
            "_Правила простые, но они могут спасти жизнь._\n"
            "✅ **Никогда не делай:**\n"
            "• Не разговаривай с незнакомцами, не бери подарки, сладости, игрушки.\n"
            "• **Не садись в машину к незнакомому человеку**, даже если он просит помочь.\n"
            "• Не иди с чужим человеком, даже если он говорит: «Твоя мама попросила меня тебя забрать».\n"
            "• Не открывай дверь незнакомцам.\n"
            "• Не заходи с незнакомыми в лифт, подъезд, безлюдные места.\n"
            "✅ **Если что-то случилось:**\n"
            "• Если кто-то пытается схватить или увести — **кричи громко:** «Я его не знаю! Помогите!».\n"
            "• **Вырывайся, падай на землю, цепляйся за предметы** — так труднее утащить.\n"
            "• Если кто-то идёт за тобой — **иди в людное место**: магазин, школу, банк, аптеку.\n"
            "• Позвони родителям или в `112`.\n"
            "✅ **Советы:**\n"
            "• Выучи наизусть **номер телефона родителей**.\n"
            "• Придумайте с родителями **семейный пароль** — если кто-то говорит «меня прислала мама», он должен его назвать.\n"
            "• Если потерялся в городе — обратись к **полицейскому или продавцу в магазине**.\n"
            "• Взрослый **не должен просить помощи у ребёнка** — это должно насторожить.",
            school_menu())

    else:
        send_message(chat_id, "Я вас не понял. Используйте кнопки меню или ключевые слова:", main_menu())


# =====================================================
# ОБРАБОТЧИК WEBHOOK
# =====================================================
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
                    handle_command(chat_id, 'start')

            elif update_type == 'message_created':
                body = message.get('body', {})
                text = body.get('text', '') if isinstance(body, dict) else str(body)
                matched = fuzzy_command(text)
                cmd = matched if matched else text
                stats_track(chat_id, 'message', cmd)
                handle_command(chat_id, cmd)

            elif update_type == 'message_callback':
                callback = data.get('callback', {})
                payload = callback.get('payload') or data.get('payload')
                if payload:
                    mid = callback.get('messageId') or (callback.get('message') or {}).get('messageId')
                    stats_track(chat_id, 'button', payload)
                    handle_command(chat_id, payload, message_id=mid)

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
