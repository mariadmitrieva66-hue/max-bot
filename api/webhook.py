import json
import os
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
        [btn("🚨 ЕДДС", 'edds')],
        [btn_link("⚠️ Предупреждения (РСЧС)", RSCHS_URL)],
        [btn("🏔️ Погода на маршрутах", 'routes')],
        [btn("📋 Чек-листы", 'checklists')],
        [btn_link("📝 Регистрация туристских групп", REGISTRATION_URL)],
        [btn("📞 Контакты", 'contacts')],
    ]

def emergency_menu():
    return [
        [btn("🔥 Пожар", 'fire')],
        [btn("🌊 Наводнение / Цунами", 'flood')],
        [btn("🏠 Землетрясение", 'earthquake')],
        [btn("❌ Отмена (Главное меню)", 'main')],
    ]

def back_menu():
    return [[btn("🏠 Главное меню", 'main')]]


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
            'Спасалки (ледовые гвозди) на шее',
            'Верёвка 15-20 м с поплавком',
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
    """Обновляет сообщение на месте, если есть его ID; иначе шлёт новое"""
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

    if command in ('start', 'main', '/start', 'главное меню', 'привет', 'здравствуй', 'здравствуйте', 'добрый день', 'hello', 'hi'):
        send_message(chat_id,
            "Привет!😊 Я бот Агентства по делам ГО, ЧС и ПБ Сахалинской области.\n\n"
            "**💡 Как пользоваться:**\n"
            "• выберите раздел через кнопки меню ниже 👇\n"
            "• или просто введите ключевые слова: `пожар`, `спасатели`, "
            "`градусник`, `огнетушитель`, `наводнение`, `цунами`, `землетрясение`, "
            "`еддс`, `погода`, `чек-лист` — и мгновенно получите информацию.\n\n"
            "Для начала работы нажмите кнопку ниже или введите нужное слово 👇:",
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
            "• Обработайте место разлива раствором марганцовки, хлорной извести либо горячим мыльно-содовым раствором (30 г соды + 40 г тёртого мыла на 1 л воды)\n"
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
                [btn("🏠 Главное меню", 'main')],
            ])

    elif command in ['contacts', 'контакты', '/contacts']:
        send_message(chat_id,
            "**📞 Экстренные службы:**\n\n"
            "• `112` — единый номер вызова экстренных служб\n"
            "• `101` — пожарные\n"
            "• `102` — полиция\n"
            "• `103` — скорая помощь",
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
                handle_command(chat_id, matched if matched else text)

            elif update_type == 'message_callback':
                callback = data.get('callback', {})
                payload = callback.get('payload') or data.get('payload')
                if payload:
                    mid = callback.get('messageId') or (callback.get('message') or {}).get('messageId')
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
