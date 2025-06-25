import logging
import os
import json
import random
import string
from datetime import datetime
import asyncio
import requests
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S' 
    
)

CHANNEL_LINK = "https://t.me/zxcv_215"
REFERRAL_REWARDS = []  # Будет хранить данные о награде за реферала
 
# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CODE = os.getenv("ADMIN_CODE", "12")  # Код для входа в админку

# Инициализация бота с правильным parse_mode
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# Константы для API игры
TOKEN_API = "BUDyVrw9u2HlxhOhco2U"
SKINS_REQUESTED = "$QW20"
SENDER_NICK = "Б2ОТ"
PRICES_HASH = "fbd9aec4384456124c0765581a4ba099"
SENDER_VERSION = "2.38.0"

# Доступные чаты и языки
CHAT_REGIONS = ["RU", "US", "DE", "PL", "PREMIUM", "DEV"]
LANGUAGES = {
    "ru": "Русский",
    "en": "English"
}

# Базы данных (будут загружаться из файлов)
users_db = {}
promocodes_db = {}
free_skins_db = {}

# Состояния для FSM
class PromoStates(StatesGroup):
    waiting_for_skin_name = State()
    waiting_for_activations = State()
    waiting_for_multiple_choice = State()
    waiting_for_skin_id = State()
    waiting_for_activation_choice = State()
    waiting_for_promo_input = State()
    waiting_for_language = State()
    waiting_for_chat_region = State()
    waiting_for_verification_code = State()
    waiting_for_personal_code = State()  
    waiting_for_promo_to_send = State()  
    waiting_for_skin_delete = State()
    waiting_for_friend_code = State()
    waiting_for_friend_promo = State()
    waiting_for_ref_skin_name = State()
    waiting_for_ref_skin_id = State()
    waiting_for_ref_skin_delete = State()
    waiting_for_promo_delete = State()
    

# ========== Функции работы с данными ==========
def generate_personal_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def generate_promocode():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def generate_verification_code():
    return str(random.randint(100, 999))


def check_files():
    files = ['data.json']
    for file in files:
        if not os.path.exists(file):
            with open(file, 'w', encoding='utf-8') as f:
                json.dump({
                    'users': {},
                    'promocodes': {},
                    'skins': {},
                    'referral_rewards': []
                }, f)


def save_data():
    data_to_save = {
        'users': users_db,
        'promocodes': promocodes_db,
        'skins': free_skins_db,
        'referral_rewards': REFERRAL_REWARDS  # Добавлено сохранение наград
    }
    
    try:
        # Создаем временный файл
        temp_file = 'data_temp.json'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        
        # Если запись прошла успешно, переименовываем временный файл
        if os.path.exists(temp_file):
            # Создаем резервную копию
            if os.path.exists('data.json'):
                os.replace('data.json', 'data_backup.json')
            os.replace(temp_file, 'data.json')
            
    except Exception as e:
        logging.error(f"Error saving data: {str(e)}")
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except:
            pass
    # Обработчики для установки награды
@dp.message(PromoStates.waiting_for_ref_skin_id)
async def process_ref_skin_id(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    skin_id = message.text.strip()
    
    if not skin_id:
        await message.answer("Пожалуйста, введите ID скина." if lang == 'ru' else "Please enter skin ID.")
        return
    
    data = await state.get_data()
    
    reward = {
        "skin_name": data["skin_name"],
        "skin_id": skin_id,
        "added_at": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    REFERRAL_REWARDS.append(reward)
    save_data()
    await message.answer(
        f"✅ Награда за реферала успешно добавлена!\n\n"
        f"🔹 Название: {data['skin_name']}\n"
        f"🔹 ID: {skin_id}" if lang == 'ru' else
        f"✅ Referral reward successfully added!\n\n"
        f"🔹 Name: {data['skin_name']}\n"
        f"🔹 ID: {skin_id}",
        reply_markup=get_admin_keyboard(user_id))
    
    await state.clear()
    
def load_data():
    global users_db, promocodes_db, free_skins_db, REFERRAL_REWARDS
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            users_db = data.get('users', {})
            promocodes_db = data.get('promocodes', {})
            free_skins_db = data.get('skins', {})
            REFERRAL_REWARDS = data.get('referral_rewards', [])
        logging.info("Data loaded successfully")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error loading data: {str(e)}")
        users_db = {}
        promocodes_db = {}
        free_skins_db = {}
        REFERRAL_REWARDS = []

    try:
        with open('promocodes.json', 'r', encoding='utf-8') as f:
            promocodes_db = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        promocodes_db = {}

    try:
        with open('skins.json', 'r', encoding='utf-8') as f:
            free_skins_db = json.load(f)
            if not isinstance(free_skins_db, dict):
                free_skins_db = {}
    except (FileNotFoundError, json.JSONDecodeError):
        free_skins_db = {}
        

check_files()
load_data()

# ========== Функции для работы с API игры ==========
async def get_user_id_from_chat(verification_code: str, chat_region: str) -> str:
    """Получаем ID пользователя из чата игры по коду верификации"""
    url = f"https://api-project-7952672729.firebaseio.com/Chat/Messages/{chat_region}.json?orderBy=\"ts\"&limitToLast=20"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        messages = response.json()

        if messages is None:
            logging.error("No messages in chat")
            return None

        for message_id in messages:
            msg_data = messages[message_id]
            if verification_code in msg_data.get('msg', ''):
                return msg_data.get('playerID', None)

        logging.error("User with verification code not found in last 20 messages")
        return None

    except requests.exceptions.RequestException as e:
        logging.error(f"Chat API error: {e}")
        return None
    except json.JSONDecodeError:
        logging.error("Invalid chat API response format")
        return None

async def send_skin_to_game(player_id: str, skin_id: str, chat_region: str) -> bool:
    """Отправляем скин пользователю через API игры"""
    create_offer_url = "https://api.efezgames.com/v1/trades/createOffer"
    respond_offer_url = "https://api.efezgames.com/v1/trades/respondOffer"

    try:
        # Создаем предложение обмена
        create_offer_params = {
            "token": TOKEN_API,
            "playerID": player_id,
            "receiverID": player_id,
            "senderNick": SENDER_NICK,
            "senderFrame": "",
            "senderAvatar": "",
            "receiverNick": SENDER_NICK,
            "receiverFrame": "",
            "receiverAvatar": "",
            "skinsOffered": skin_id,
            "skinsRequested": SKINS_REQUESTED,
            "message": "отмени",
            "pricesHash": PRICES_HASH,
            "senderOneSignal": "",
            "receiverOneSignal": "",
            "senderVersion": SENDER_VERSION,
            "receiverVersion": SENDER_VERSION
        }
        
        response = requests.get(create_offer_url, params=create_offer_params)
        response.raise_for_status()
        offer_data = response.json()

        if not offer_data.get("offerID"):
            logging.error("Не удалось получить offerID от API")
            return False

        # Принимаем предложение обмена
        respond_data = {
            "token": TOKEN_API,
            "playerID": player_id,
            "offerID": offer_data["offerID"],
            "receiverMessage": "",
            "accepted": "true"
        }
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(respond_offer_url, data=json.dumps(respond_data), headers=headers)
        response.raise_for_status()
        respond_data = response.json()

        # Всегда считаем трейд успешным, даже если access: -1
        logging.info(f"Трейд создан (ответ API: {respond_data})")
        return True

    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка запроса: {e}")
        return False
    except json.JSONDecodeError:
        logging.error("Неверный JSON ответ")
        return False
    except Exception as e:
        logging.error(f"Общая ошибка: {e}")
        return False

# ========== Клавиатуры ==========
def get_main_keyboard(user_id: str) -> ReplyKeyboardMarkup:
    user_lang = users_db.get(str(user_id), {}).get('language', 'ru')
    
    buttons = {
        "ru": {
            "profile": "👤 Мой профиль",
            "admin": "🔐 Админ панель",
            "promo": "🎁 Активировать промокод",
            "free_skin": "🎁 Получить бесплатный скин",
            "send_promo": "📤 Отправить промокод другу"
        },
        "en": {
            "profile": "👤 My profile",
            "admin": "🔐 Admin panel",
            "promo": "🎁 Activate promo code",
            "free_skin": "🎁 Get free skin",
            "send_promo": "📤 Send promo to friend"
        }
    }
    
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=buttons[user_lang]["profile"])],
            [KeyboardButton(text=buttons[user_lang]["admin"])],
            [KeyboardButton(text=buttons[user_lang]["promo"])],
            [KeyboardButton(text=buttons[user_lang]["free_skin"])],
            [KeyboardButton(text=buttons[user_lang]["send_promo"])]
        ],
        resize_keyboard=True
    )

def get_admin_keyboard(user_id: str) -> ReplyKeyboardMarkup:
    user_lang = users_db.get(str(user_id), {}).get('language', 'ru')
    
    buttons = {
        "ru": {
            "create": "🆕 Создать промокод",
            "list": "📋 Список промокодов",
            "delete_promo": "🗑️ Удалить промокод",
            "add_skin": "🎁 Добавить бесплатный скин",
            "list_skins": "📋 Список бесплатных скинов",
            "delete_skin": "🗑️ Удалить бесплатный скин",
            "send_promo": "📤 Отправить промокод",
            "ref_reward": "🎁 Награда за реферала",
            "back": "🔙 Назад"
        },
        "en": {
            "create": "🆕 Create promo code",
            "list": "📋 Promo codes list",
            "delete_promo": "🗑️ Delete promo code",
            "add_skin": "🎁 Add free skin",
            "list_skins": "📋 Free skins list",
            "delete_skin": "🗑️ Delete free skin",
            "send_promo": "📤 Send promo code",
            "ref_reward": "🎁 Referral reward",
            "back": "🔙 Back"
        }
    }
    
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=buttons[user_lang]["create"]),
             KeyboardButton(text=buttons[user_lang]["list"]),
             KeyboardButton(text=buttons[user_lang]["delete_promo"])],
            [KeyboardButton(text=buttons[user_lang]["add_skin"]),
             KeyboardButton(text=buttons[user_lang]["list_skins"]),
             KeyboardButton(text=buttons[user_lang]["delete_skin"])],
            [KeyboardButton(text=buttons[user_lang]["send_promo"]),
             KeyboardButton(text=buttons[user_lang]["ref_reward"])],
            [KeyboardButton(text=buttons[user_lang]["back"])]
        ],
        resize_keyboard=True
    )

def get_cancel_keyboard(user_id: str) -> ReplyKeyboardMarkup:
    user_lang = users_db.get(str(user_id), {}).get('language', 'ru')
    text = "🚫 Отмена" if user_lang == "ru" else "🚫 Cancel"
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text)]],
        resize_keyboard=True
    )
    
 #---обработчик для кнопки отмены
@dp.message(F.text.contains("🚫"))
async def cancel_handler(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    current_state = await state.get_state()
    if current_state is None:
        return
    
    await state.clear()
    
    # Проверяем, откуда пришла отмена (из админки или основного меню)
    if users_db.get(user_id, {}).get('is_admin', False):
        reply_markup = get_admin_keyboard(user_id)
    else:
        reply_markup = get_main_keyboard(user_id)
    
    if lang == 'ru':
        await message.answer("Действие отменено.", reply_markup=reply_markup)
    else:
        await message.answer("Action cancelled.", reply_markup=reply_markup)

def get_after_activation_keyboard(user_id: str) -> ReplyKeyboardMarkup:
    user_lang = users_db.get(str(user_id), {}).get('language', 'ru')
    
    buttons = {
        "ru": {
            "now": "Вывести в игру сейчас",
            "later": "Оставить в профиле"
        },
        "en": {
            "now": "Send to game now",
            "later": "Keep in profile"
        }
    }
    
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=buttons[user_lang]["now"])],
            [KeyboardButton(text=buttons[user_lang]["later"])]
        ],
        resize_keyboard=True
    )

def get_language_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Русский", callback_data="lang_ru"),
            InlineKeyboardButton(text="English", callback_data="lang_en")
        ]
    ])
    return keyboard

def get_chat_region_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=region, callback_data=f"chat_{region}")] for region in CHAT_REGIONS
    ])
    return keyboard
#---Список бесплатных скинов---
@dp.message(F.text == "📋 Список бесплатных скинов")
@dp.message(F.text == "📋 Free skins list")
async def list_free_skins(message: types.Message):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    if not users_db.get(user_id, {}).get('is_admin', False):
        if lang == 'ru':
            await message.answer("❌ У вас нет прав администратора.")
        else:
            await message.answer("❌ You don't have admin privileges.")
        return
    
    if not free_skins_db:
        if lang == 'ru':
            await message.answer("❌ Нет доступных бесплатных скинов.")
        else:
            await message.answer("❌ No free skins available.")
        return
    
    if lang == 'ru':
        text = ("📋 Список бесплатных скинов:\n\n"
               "Чтобы удалить скин, введите его номер (например: 1 или 1 2 для удаления нескольких)\n\n")
    else:
        text = ("📋 Free skins list:\n\n"
               "To delete skin, enter its number (e.g.: 1 or 1 2 to delete multiple)\n\n")  
    
    for i, (skin_id, skin_data) in enumerate(free_skins_db.items(), 1):
        text += f"{i}. {skin_data['skin_name']} (ID: {skin_id})\n"
        text += f"▪️ Добавлен: {skin_data.get('added_at', 'неизвестно')}\n\n" if lang == 'ru' else f"▪️ Added: {skin_data.get('added_at', 'unknown')}\n\n"
    
    await message.answer(text)

# ----- Добавьте новый обработчик для кнопки награды за реферала ------
@dp.message(F.text == "🎁 Награда за реферала")
@dp.message(F.text == "🎁 Referral reward")
async def referral_reward_menu(message: types.Message):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    if not users_db.get(user_id, {}).get('is_admin', False):
        if lang == 'ru':
            await message.answer("❌ У вас нет прав администратора.")
        else:
            await message.answer("❌ You don't have admin privileges.")
        return
    
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить награду" if lang == 'ru' else "Add reward")],
            [KeyboardButton(text="Список наград" if lang == 'ru' else "List rewards")],
            [KeyboardButton(text="Удалить награду" if lang == 'ru' else "Delete reward")],
            [KeyboardButton(text="🔙 Назад" if lang == 'ru' else "🔙 Back")]
        ],
        resize_keyboard=True
    )
    
    if lang == 'ru':
        await message.answer("🎁 Управление наградами за рефералов:", reply_markup=markup)
    else:
        await message.answer("🎁 Referral rewards management:", reply_markup=markup)
    
# Обработчик для добавления награды за реферала
@dp.message(F.text == "1")
async def add_referral_reward_start(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    if lang == 'ru':
        await message.answer("Введите название скина для награды:", reply_markup=get_cancel_keyboard(user_id))
    else:
        await message.answer("Enter skin name for reward:", reply_markup=get_cancel_keyboard(user_id))
    
    await state.set_state(PromoStates.waiting_for_ref_skin_name)

@dp.message(PromoStates.waiting_for_ref_skin_name)
async def process_ref_skin_name(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    skin_name = message.text.strip()
    
    if not skin_name:
        if lang == 'ru':
            await message.answer("Пожалуйста, введите название скина.")
        else:
            await message.answer("Please enter skin name.")
        return
    
    await state.update_data(skin_name=skin_name)
    
    if lang == 'ru':
        await message.answer("Введите ID скина (из API игры):", reply_markup=get_cancel_keyboard(user_id))
    else:
        await message.answer("Enter skin ID (from game API):", reply_markup=get_cancel_keyboard(user_id))
    
    await state.set_state(PromoStates.waiting_for_ref_skin_id)

@dp.message(PromoStates.waiting_for_ref_skin_id)
async def process_ref_skin_id(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    skin_id = message.text.strip()
    
    if not skin_id:
        if lang == 'ru':
            await message.answer("Пожалуйста, введите ID скина.")
        else:
            await message.answer("Please enter skin ID.")
        return
    
    data = await state.get_data()
    
    # Добавляем награду в список
    if 'referral_rewards' not in users_db[user_id]:
        users_db[user_id]['referral_rewards'] = []
    
    reward = {
        "skin_name": data["skin_name"],
        "skin_id": skin_id,
        "added_at": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    
    REFERRAL_REWARDS.append(reward)
    save_data()
    
    if lang == 'ru':
        await message.answer(
            f"✅ Награда за реферала успешно добавлена!\n\n"
            f"🔹 Название: {data['skin_name']}\n"
            f"🔹 ID: {skin_id}",
            reply_markup=get_admin_keyboard(user_id))
    else:
        await message.answer(
            f"✅ Referral reward successfully added!\n\n"
            f"🔹 Name: {data['skin_name']}\n"
            f"🔹 ID: {skin_id}",
            reply_markup=get_admin_keyboard(user_id))
    
    await state.clear()

# ========== ОСНОВНЫЕ КОМАНДЫ ==========
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')

    # Инициализируем referrer_id как None
    referrer_id = None
    
    # Проверяем реферальную ссылку
    if "ref_" in message.text:
        referrer_id = message.text.split("ref_")[-1]
    
    # Обрабатываем реферала, если он есть
    if referrer_id and referrer_id in users_db and referrer_id != user_id:
      if user_id not in users_db[referrer_id].get("referrals", []):
        users_db[referrer_id].setdefault("referrals", []).append(user_id)
          
        if REFERRAL_REWARDS:  # Проверяем список наград
            reward = random.choice(REFERRAL_REWARDS)
            promo_code = generate_promocode()
                
            promocodes_db[promo_code] = {
                "skin_name": reward["skin_name"],
                "skin_id": reward["skin_id"],
                "max_activations": 1,
                "allow_multiple": False,
                "created_by": "system",
                "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "used_by": []
            }
            users_db[referrer_id].setdefault('inactive_promocodes', []).append({
                'code': promo_code,
                'skin_name': reward["skin_name"],
                'skin_id': reward["skin_id"],
                'activated_at': datetime.now().strftime("%d.%m.%Y %H:%M"),
                'from_referral': True
            })
            save_data()
            
            try:
                    ref_lang = users_db[referrer_id].get('language', 'ru')
                    if ref_lang == 'ru':
                        text = (f"🎉 Вы получили промокод за приглашение друга!\n"
                              f"🔹 Промокод: <code>{promo_code}</code>\n"
                              f"🔹 Награда: {reward['skin_name']}\n\n"
                              f"Активируйте его в разделе '👤 Мой профиль'")
                    else:
                        text = (f"🎉 You got a promo code for inviting a friend!\n"
                              f"🔹 Promo code: <code>{promo_code}</code>\n"
                              f"🔹 Reward: {reward['skin_name']}\n\n"
                              f"Activate it in '👤 My profile' section")
                    
                    await bot.send_message(
                        chat_id=referrer_id,
                        text=text,
                        parse_mode="HTML"
                    )
            except Exception as e:
                    logging.error(f"Не удалось отправить уведомление пригласившему: {e}")

    # Упрощенная проверка подписки
    text = (
        f"📢 Для использования бота подпишитесь на канал: {CHANNEL_LINK}\n"
        "После подписки нажмите /start снова."
        if lang == 'ru'
        else f"📢 To use the bot, subscribe to: {CHANNEL_LINK}\n"
             "Press /start after subscribing."
    )
    await message.answer(text, reply_markup=ReplyKeyboardRemove())
    
    # Регистрация нового пользователя
    if user_id not in users_db:
        users_db[user_id] = {
            "reg_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "personal_code": generate_personal_code(),
            "promocodes": [],
            "inactive_promocodes": [],
            "referrals": [],
            "is_admin": False,
            "language": "ru",
            "chat_region": "RU",
            "language_set": False
        }
        save_data()
        logging.info(f"Новый пользователь зарегистрирован: {user_id}")

    # Проверяем, установлен ли язык
    if not users_db[user_id].get('language_set', False):
        await message.answer("Please choose your language / Пожалуйста, выберите язык:", 
                           reply_markup=get_language_keyboard())
        return

    # Главное меню
    lang = users_db[user_id]['language']
    welcome_text = ("Добро пожаловать в бота! Выберите действие:" if lang == 'ru' 
                   else "Welcome to the bot! Choose an action:")
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard(user_id))
    

@dp.callback_query(lambda c: c.data.startswith('lang_'))
async def process_language(callback: types.CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    lang = callback.data.split('_')[1]
    
    if user_id not in users_db:
        users_db[user_id] = {
            "reg_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "personal_code": generate_personal_code(),
            "promocodes": [],
            "inactive_promocodes": [],
            "referrals": [],
            "is_admin": False,
            "language": lang,
            "chat_region": "RU",
            "language_set": True
        }
    else:
        users_db[user_id]['language'] = lang
        users_db[user_id]['language_set'] = True
    
    save_data()
    
    # После выбора языка предлагаем выбрать чат
    text = "Выберите ваш чат в игре:" if lang == 'ru' else "Choose your game chat:"
    await callback.message.edit_text(text, reply_markup=get_chat_region_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith('chat_'))
async def process_chat_region(callback: types.CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    chat_region = callback.data.split('_')[1]
    
    users_db[user_id]['chat_region'] = chat_region
    save_data()
    
    lang = users_db[user_id].get('language', 'ru')
    text = "Отлично! Теперь вы можете пользоваться ботом." if lang == 'ru' else "Great! Now you can use the bot."
    await callback.message.answer(text, reply_markup=get_main_keyboard(user_id))
    await callback.answer()

@dp.message(F.text == "👤 Мой профиль")
@dp.message(F.text == "👤 My profile")
async def profile(message: types.Message):
    user_id = str(message.from_user.id)
    user = users_db.get(user_id, {})
    lang = user.get('language', 'ru')

    active_promos = user.get("promocodes", [])
    inactive_promos = user.get("inactive_promocodes", [])
    referrals = user.get("referrals", [])
    
    # Формируем текст для неактивированных промокодов
    inactive_text = ""
    if inactive_promos:
        if lang == 'ru':
            inactive_text = "\n\n🔒 Неактивированные промокоды:\n"
        else:
            inactive_text = "\n\n🔒 Inactive promo codes:\n"
            
        for promo in inactive_promos:
            source = "(за приглашение)" if promo.get('from_referral') and lang == 'ru' else "(for referral)" if promo.get('from_referral') else ""
            if lang == 'ru':
                inactive_text += f"🔹 {promo['code']} - {promo['skin_name']} {source}\n"
            else:
                inactive_text += f"🔹 {promo['code']} - {promo['skin_name']} {source}\n"

    # Формируем полный текст профиля
    if lang == 'ru':
        profile_text = (
            f"👤 Ваш профиль:\n"
            f"📅 Дата регистрации: {user.get('reg_date', 'неизвестно')}\n"
            f"🔑 Персональный код: {user.get('personal_code', 'не установлен')}\n\n"
            f"👥 Рефералов: {len(referrals)}\n"
            f"🔗 Реферальная ссылка:\n"
            f"t.me/{(await bot.get_me()).username}?start=ref_{user_id}\n\n"
            f"🎁 Активированные промокоды:\n"
            f"{', '.join(active_promos) if active_promos else 'Нет'}"
            f"{inactive_text}"
        )
    else:
        profile_text = (
            f"👤 Your profile:\n"
            f"📅 Registration date: {user.get('reg_date', 'unknown')}\n"
            f"🔑 Personal code: {user.get('personal_code', 'not set')}\n\n"
            f"👥 Referrals: {len(referrals)}\n"
            f"🔗 Referral link:\n"
            f"t.me/{(await bot.get_me()).username}?start=ref_{user_id}\n\n"
            f"🎁 Activated promo codes:\n"
            f"{', '.join(active_promos) if active_promos else 'None'}"
            f"{inactive_text}"
        )
    
    if lang == 'ru':
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Сменить язык/чат", callback_data="change_lang_chat")],
        ])
    else:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Change language/chat", callback_data="change_lang_chat")],
        ])

    await message.answer(profile_text, reply_markup=markup)
        
@dp.callback_query(lambda c: c.data == "change_lang_chat")
async def change_lang_chat(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    
    if lang == 'ru':
        text = "Выберите действие:"
        buttons = [
            [InlineKeyboardButton(text="🇷🇺 Сменить язык", callback_data="change_lang")],
            [InlineKeyboardButton(text="💬 Сменить чат игры", callback_data="change_chat")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile")]
        ]
    else:
        text = "Choose action:"
        buttons = [
            [InlineKeyboardButton(text="🇬🇧 Change language", callback_data="change_lang")],
            [InlineKeyboardButton(text="💬 Change game chat", callback_data="change_chat")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_profile")]
        ]
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "change_lang")
async def change_language(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Выберите язык / Choose language:",
        reply_markup=get_language_keyboard()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "change_chat")
async def change_chat(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    text = "Выберите ваш чат в игре:" if lang == 'ru' else "Choose your game chat:"
    await callback.message.edit_text(text, reply_markup=get_chat_region_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_profile")
async def back_to_profile(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user = users_db.get(user_id, {})
    lang = user.get('language', 'ru')
    
    # Повторяем код из функции profile для формирования текста
    active_promos = user.get("promocodes", [])
    inactive_promos = user.get("inactive_promocodes", [])
    referrals = user.get("referrals", [])
    
    inactive_text = ""
    if inactive_promos:
        if lang == 'ru':
            inactive_text = "\n\n🔒 Неактивированные промокоды:\n"
        else:
            inactive_text = "\n\n🔒 Inactive promo codes:\n"
            
        for promo in inactive_promos:
            source = "(за приглашение)" if promo.get('from_referral') and lang == 'ru' else "(for referral)" if promo.get('from_referral') else ""
            if lang == 'ru':
                inactive_text += f"🔹 {promo['code']} - {promo['skin_name']} {source}\n"
            else:
                inactive_text += f"🔹 {promo['code']} - {promo['skin_name']} {source}\n"

    if lang == 'ru':
        profile_text = (
            f"👤 Ваш профиль:\n"
            f"📅 Дата регистрации: {user.get('reg_date', 'неизвестно')}\n"
            f"🔑 Персональный код: {user.get('personal_code', 'не установлен')}\n\n"
            f"👥 Рефералов: {len(referrals)}\n"
            f"🔗 Реферальная ссылка:\n"
            f"t.me/{(await bot.get_me()).username}?start=ref_{user_id}\n\n"
            f"🎁 Активированные промокоды:\n"
            f"{', '.join(active_promos) if active_promos else 'Нет'}"
            f"{inactive_text}"
        )
    else:
        profile_text = (
            f"👤 Your profile:\n"
            f"📅 Registration date: {user.get('reg_date', 'unknown')}\n"
            f"🔑 Personal code: {user.get('personal_code', 'not set')}\n\n"
            f"👥 Referrals: {len(referrals)}\n"
            f"🔗 Referral link:\n"
            f"t.me/{(await bot.get_me()).username}?start=ref_{user_id}\n\n"
            f"🎁 Activated promo codes:\n"
            f"{', '.join(active_promos) if active_promos else 'None'}"
            f"{inactive_text}"
        )
    
    if lang == 'ru':
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Сменить язык/чат", callback_data="change_lang_chat")],
        ])
    else:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Change language/chat", callback_data="change_lang_chat")],
        ])
    
    await callback.message.edit_text(profile_text, reply_markup=markup)
    await callback.answer()
    
#---  
@dp.message(F.text == "🗑️ Удалить промокод")
@dp.message(F.text == "🗑️ Delete promo code")
async def delete_promo_start(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    if not users_db.get(user_id, {}).get('is_admin', False):
        if lang == 'ru':
            await message.answer("❌ У вас нет прав администратора.")
        else:
            await message.answer("❌ You don't have admin privileges.")
        return
    
    if not promocodes_db:
        if lang == 'ru':
            await message.answer("❌ Нет созданных промокодов для удаления.")
        else:
            await message.answer("❌ No promo codes to delete.")
        return
    
    if lang == 'ru':
        text = "📋 Список промокодов для удаления:\n\n"
    else:
        text = "📋 List of promo codes to delete:\n\n"
    
    for i, (code, data) in enumerate(promocodes_db.items(), 1):
        text += f"{i}. {code} - {data['skin_name']}\n"
    
    if lang == 'ru':
        text += "\nВведите номер промокода для удаления:"
    else:
        text += "\nEnter promo code number to delete:"
    
    await message.answer(text, reply_markup=get_cancel_keyboard(user_id))
    await state.set_state(PromoStates.waiting_for_promo_delete)

@dp.message(PromoStates.waiting_for_promo_delete)
async def process_promo_delete(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    try:
        # Обрабатываем ввод чисел через пробел
        promo_nums = list(map(int, message.text.strip().split()))
        
        deleted = []
        for num in sorted(promo_nums, reverse=True):  # Удаляем с конца, чтобы индексы не сдвигались
            if 1 <= num <= len(promocodes_db):
                promo_code = list(promocodes_db.keys())[num-1]
                deleted.append((num, promo_code, promocodes_db[promo_code]['skin_name']))
                del promocodes_db[promo_code]
        
        if not deleted:
            raise ValueError
        
        save_data()  # Явно сохраняем изменения
        
        if lang == 'ru':
            text = "✅ Удалены промокоды:\n"
        else:
            text = "✅ Deleted promo codes:\n"
            
        for num, code, name in deleted:
            text += f"{num}. {code} - {name}\n"
            
        await message.answer(text, reply_markup=get_admin_keyboard(user_id))
    
    except (ValueError, IndexError):
        if lang == 'ru':
            await message.answer("❌ Пожалуйста, введите корректные номера промокодов (например: 1 или 1 2 3).")
        else:
            await message.answer("❌ Please enter valid promo code numbers (e.g.: 1 or 1 2 3).")
        return
    
    await state.clear()

@dp.message(PromoStates.waiting_for_skin_delete)
async def process_skin_delete(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    try:
        # Обрабатываем ввод чисел через пробел
        skin_nums = list(map(int, message.text.strip().split()))
        
        deleted = []
        for num in sorted(skin_nums, reverse=True):  # Удаляем с конца, чтобы индексы не сдвигались
            if 1 <= num <= len(free_skins_db):
                skin_id = list(free_skins_db.keys())[num-1]
                skin_data = free_skins_db[skin_id]
                deleted.append((num, skin_id, skin_data['skin_name']))
                del free_skins_db[skin_id]
        
        if not deleted:
            raise ValueError
        
        save_data()  # Явно сохраняем изменения
        
        if lang == 'ru':
            text = "✅ Удалены скины:\n"
        else:
            text = "✅ Deleted skins:\n"
            
        for num, skin_id, name in deleted:
            text += f"{num}. {name} (ID: {skin_id})\n"
            
        await message.answer(text, reply_markup=get_admin_keyboard(user_id))
    
    except (ValueError, IndexError):
        if lang == 'ru':
            await message.answer("❌ Пожалуйста, введите корректные номера скинов (например: 1 или 1 2 3).")
        else:
            await message.answer("❌ Please enter valid skin numbers (e.g.: 1 or 1 2 3).")
        return
    
    await state.clear()

@dp.message(F.text == "🗑️ Удалить бесплатный скин")
@dp.message(F.text == "🗑️ Delete free skin")
async def delete_skin_start(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    if not users_db.get(user_id, {}).get('is_admin', False):
        if lang == 'ru':
            await message.answer("❌ У вас нет прав администратора.")
        else:
            await message.answer("❌ You don't have admin privileges.")
        return
    
    if not free_skins_db:
        if lang == 'ru':
            await message.answer("❌ Нет бесплатных скинов для удаления.")
        else:
            await message.answer("❌ No free skins to delete.")
        return
    
    if lang == 'ru':
        text = "📋 Список бесплатных скинов для удаления:\n\n"
    else:
        text = "📋 List of free skins to delete:\n\n"
    
    for i, (skin_id, skin_data) in enumerate(free_skins_db.items(), 1):
        text += f"{i}. {skin_data['skin_name']} (ID: {skin_id})\n"
    
    if lang == 'ru':
        text += "\nВведите номер скина для удаления:"
    else:
        text += "\nEnter skin number to delete:"
    
    await message.answer(text, reply_markup=get_cancel_keyboard(user_id))
    await state.set_state(PromoStates.waiting_for_skin_delete)

@dp.message(PromoStates.waiting_for_skin_delete)
async def process_skin_delete(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    try:
        # Обрабатываем ввод чисел через пробел
        skin_nums = list(map(int, message.text.strip().split()))
        
        deleted = []
        for num in sorted(skin_nums, reverse=True):  # Удаляем с конца, чтобы индексы не сдвигались
            if 1 <= num <= len(free_skins_db):
                skin_id = list(free_skins_db.keys())[num-1]
                skin_data = free_skins_db[skin_id]
                deleted.append((num, skin_id, skin_data['skin_name']))
                del free_skins_db[skin_id]
        
        if not deleted:
            raise ValueError
        
        save_data()  # Явно сохраняем изменения
        
        if lang == 'ru':
            text = "✅ Удалены скины:\n"
        else:
            text = "✅ Deleted skins:\n"
            
        for num, skin_id, name in deleted:
            text += f"{num}. {name} (ID: {skin_id})\n"
            
        await message.answer(text, reply_markup=get_admin_keyboard(user_id))
    
    except (ValueError, IndexError):
        if lang == 'ru':
            await message.answer("❌ Пожалуйста, введите корректные номера скинов (например: 1 или 1 2 3).")
        else:
            await message.answer("❌ Please enter valid skin numbers (e.g.: 1 or 1 2 3).")
        return
    
    await state.clear()
     
# ========== АДМИН ПАНЕЛЬ ==========
@dp.message(F.text == "🔐 Админ панель")
@dp.message(F.text == "🔐 Admin panel")
async def admin_panel_request(message: types.Message):
    logging.info(f"Admin panel request from user {message.from_user.id}")
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    # Проверяем, есть ли активная админ-сессия
    if users_db.get(user_id, {}).get('is_admin', False):
        admin_time = users_db[user_id].get('admin_time')
        if admin_time:
            admin_time = datetime.strptime(admin_time, "%d.%m.%Y %H:%M")
            hours_passed = (datetime.now() - admin_time).total_seconds() / 3600
            if hours_passed < 48:
                if lang == 'ru':
                    await message.answer("🔐 Админ-панель", reply_markup=get_admin_keyboard(user_id))
                else:
                    await message.answer("🔐 Admin panel", reply_markup=get_admin_keyboard(user_id))
                return
    
    if lang == 'ru':
        await message.answer("Введите админ-код:")
    else:
        await message.answer("Enter admin code:")

@dp.message(F.text == ADMIN_CODE)
async def admin_panel_access(message: types.Message, state: FSMContext):
    logging.info(f"Admin access granted to user {message.from_user.id}")
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    if user_id not in users_db:
        users_db[user_id] = {
            "is_admin": True,
            "admin_time": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "reg_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "promocodes": [],
            "inactive_promocodes": [],
            "referrals": [],
            "language": lang
        }
    else:
        users_db[user_id]["is_admin"] = True
        users_db[user_id]["admin_time"] = datetime.now().strftime("%d.%m.%Y %H:%M")
    save_data()
    await state.clear()
    
    if lang == 'ru':
        await message.answer("🔐 Админ-панель", reply_markup=get_admin_keyboard(user_id))
    else:
        await message.answer("🔐 Admin panel", reply_markup=get_admin_keyboard(user_id))

def get_admin_keyboard(user_id: str) -> ReplyKeyboardMarkup:
    user_lang = users_db.get(str(user_id), {}).get('language', 'ru')
    
    buttons = {
        "ru": {
            "create": "🆕 Создать промокод",
            "list": "📋 Список промокодов",
            "add_skin": "🎁 Добавить бесплатный скин",
            "list_skins": "📋 Список бесплатных скинов",
            "send_promo": "📤 Отправить промокод",
            "ref_reward": "🎁 Награда за реферала",
            "back": "🔙 Назад"
        },
        "en": {
            "create": "🆕 Create promo code",
            "list": "📋 Promo codes list",
            "add_skin": "🎁 Add free skin",
            "list_skins": "📋 Free skins list",
            "send_promo": "📤 Send promo code",
            "ref_reward": "🎁 Referral reward",
            "back": "🔙 Back"
        }
    }
    
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=buttons[user_lang]["create"]),
             KeyboardButton(text=buttons[user_lang]["list"])],
            [KeyboardButton(text=buttons[user_lang]["add_skin"]),
             KeyboardButton(text=buttons[user_lang]["list_skins"])],
            [KeyboardButton(text=buttons[user_lang]["send_promo"]),
             KeyboardButton(text=buttons[user_lang]["ref_reward"])],
            [KeyboardButton(text=buttons[user_lang]["back"])]
        ],
        resize_keyboard=True
    )
#---новый обработчик для кнопки "Список наград"---    
@dp.message(F.text == "2")
async def list_referral_rewards(message: types.Message):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    if not REFERRAL_REWARDS:
        if lang == 'ru':
            await message.answer("❌ Нет добавленных наград за рефералов.")
        else:
            await message.answer("❌ No referral rewards added.")
        return
    
    if lang == 'ru':
        text = "🎁 Список наград за рефералов:\n\n"
    else:
        text = "🎁 Referral rewards list:\n\n"
    
    for i, reward in enumerate(REFERRAL_REWARDS, 1):
        text += f"{i}. {reward['skin_name']} (ID: {reward['skin_id']})\n"
        text += f"Добавлен: {reward.get('added_at', 'неизвестно')}\n\n"
    
    await message.answer(text, reply_markup=get_admin_keyboard(user_id))
    
 #---обработчик для кнопки "3" (удаление награды)---   
async def list_referral_rewards_for_deletion(message: types.Message, state: FSMContext):
    """Функция для отображения списка наград за рефералов и перехода в режим удаления"""
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')  # Получаем язык пользователя
    
    # Проверяем есть ли награды
    if not REFERRAL_REWARDS:
        if lang == 'ru':
            await message.answer("❌ Нет добавленных наград за рефералов.")
        else:
            await message.answer("❌ No referral rewards added.")
        return

    # Формируем текст сообщения
    if lang == 'ru':
        text = "🎁 Список наград за рефералов:\n\n"
    else:
        text = "🎁 Referral rewards list:\n\n"
    
    # Добавляем каждую награду в список
    for i, reward in enumerate(REFERRAL_REWARDS, 1):  # Нумерация с 1
        text += f"{i}. {reward['skin_name']} (ID: {reward['skin_id']})\n"
    
    # Добавляем инструкцию
    text += "\nВведите номер награды для удаления:" if lang == 'ru' else "\nEnter reward number to delete:"
    
    # Отправляем сообщение
    await message.answer(text, reply_markup=get_cancel_keyboard(user_id))
    await state.set_state(PromoStates.waiting_for_ref_skin_delete)

# ========== ОТПРАВКА ПРОМОКОДА ДРУГУ (ДЛЯ ОБЫЧНЫХ ПОЛЬЗОВАТЕЛЕЙ) ==========
@dp.message(F.text == "📤 Отправить промокод другу")
@dp.message(F.text == "📤 Send promo to friend")
async def send_promo_to_friend_start(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    # Проверяем есть ли неактивированные промокоды
    inactive_promos = users_db.get(user_id, {}).get('inactive_promocodes', [])
    if not inactive_promos:
        if lang == 'ru':
            await message.answer("❌ У вас нет неактивированных промокодов для отправки.")
        else:
            await message.answer("❌ You don't have inactive promo codes to send.")
        return
    
    if lang == 'ru':
        await message.answer("Введите персональный код друга:", reply_markup=get_cancel_keyboard(user_id))
    else:
        await message.answer("Enter friend's personal code:", reply_markup=get_cancel_keyboard(user_id))
    
    await state.set_state(PromoStates.waiting_for_friend_code)

@dp.message(PromoStates.waiting_for_friend_code)
async def process_friend_code(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    friend_code = message.text.strip().upper()
    
    # Ищем пользователя с таким персональным кодом
    target_user_id = None
    for uid, user_data in users_db.items():
        if user_data.get('personal_code', '').upper() == friend_code:
            target_user_id = uid
            break
    
    if not target_user_id:
        if lang == 'ru':
            await message.answer("❌ Пользователь с таким персональным кодом не найден.")
        else:
            await message.answer("❌ User with this personal code not found.")
        await state.clear()
        return
    
    if target_user_id == user_id:
        if lang == 'ru':
            await message.answer("❌ Нельзя отправить промокод самому себе.")
        else:
            await message.answer("❌ You can't send promo code to yourself.")
        await state.clear()
        return
    
    await state.update_data(target_user_id=target_user_id)
    
    # Формируем список доступных промокодов
    inactive_promos = users_db[user_id].get('inactive_promocodes', [])
    
    if lang == 'ru':
        text = "📋 Ваши неактивированные промокоды:\n\n"
    else:
        text = "📋 Your inactive promo codes:\n\n"
    
    for i, promo in enumerate(inactive_promos, 1):
        text += f"{i}. {promo['code']} - {promo['skin_name']}\n"
    
    if lang == 'ru':
        text += "\nВведите номер промокода для отправки:"
    else:
        text += "\nEnter promo code number to send:"
    
    await message.answer(text)
    await state.set_state(PromoStates.waiting_for_friend_promo)

@dp.message(PromoStates.waiting_for_friend_promo)
async def process_friend_promo(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    
    try:
        promo_num = int(message.text.strip())
        inactive_promos = users_db[user_id].get('inactive_promocodes', [])
        
        if not 1 <= promo_num <= len(inactive_promos):
            raise ValueError
        
        promo_data = inactive_promos[promo_num-1]
        
        # Удаляем промокод у отправителя
        users_db[user_id]['inactive_promocodes'] = [
            p for p in inactive_promos 
            if p['code'] != promo_data['code']
        ]
        
        # Добавляем промокод получателю
        if 'inactive_promocodes' not in users_db[target_user_id]:
            users_db[target_user_id]['inactive_promocodes'] = []
        
        users_db[target_user_id]['inactive_promocodes'].append({
            'code': promo_data['code'],
            'skin_name': promo_data['skin_name'],
            'skin_id': promo_data['skin_id'],
            'sent_by': user_id,
            'sent_at': datetime.now().strftime("%d.%m.%Y %H:%M")
        })
        
        save_data()
        
        # Отправляем уведомление получателю
        try:
            target_lang = users_db[target_user_id].get('language', 'ru')
            sender_name = message.from_user.full_name
            
            if target_lang == 'ru':
                text = (
                    f"🎁 Пользователь {sender_name} отправил вам промокод!\n\n"
                    f"🔹 Промокод: <code>{promo_data['code']}</code>\n"
                    f"🔹 Скин: {promo_data['skin_name']}\n\n"
                    f"Вы можете активировать его в разделе '👤 Мой профиль'"
                )
            else:
                text = (
                    f"🎁 User {sender_name} sent you a promo code!\n\n"
                    f"🔹 Promo code: <code>{promo_data['code']}</code>\n"
                    f"🔹 Skin: {promo_data['skin_name']}\n\n"
                    f"You can activate it in '👤 My profile' section"
                )
            
            await bot.send_message(chat_id=target_user_id, text=text, parse_mode="HTML")
            
            if lang == 'ru':
                await message.answer(
                    f"✅ Промокод успешно отправлен!",
                    reply_markup=get_main_keyboard(user_id)
                )
            else:
                await message.answer(
                    f"✅ Promo code successfully sent!",
                    reply_markup=get_main_keyboard(user_id)
                )
        
        except Exception as e:
            logging.error(f"Error sending notification: {e}")
            if lang == 'ru':
                await message.answer(
                    "✅ Промокод отправлен, но не удалось уведомить получателя.",
                    reply_markup=get_main_keyboard(user_id)
                )
            else:
                await message.answer(
                    "✅ Promo code sent, but failed to notify recipient.",
                    reply_markup=get_main_keyboard(user_id)
                )
    
    except (ValueError, IndexError):
        if lang == 'ru':
            await message.answer("❌ Пожалуйста, введите корректный номер промокода.")
        else:
            await message.answer("❌ Please enter valid promo code number.")
        return
    
    await state.clear()
    
#Добавим обработчики для новой функциональности  
@dp.message(F.text == "📤 Отправить промокод")
@dp.message(F.text == "📤 Send promo code")
async def send_promo_start(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    if not users_db.get(user_id, {}).get('is_admin', False):
        if lang == 'ru':
            await message.answer("❌ У вас нет прав администратора.")
        else:
            await message.answer("❌ You don't have admin privileges.")
        return
    
    if lang == 'ru':
        await message.answer("Введите персональный код пользователя:", reply_markup=get_cancel_keyboard(user_id))
    else:
        await message.answer("Enter user's personal code:", reply_markup=get_cancel_keyboard(user_id))
    
    await state.set_state(PromoStates.waiting_for_personal_code)

@dp.message(PromoStates.waiting_for_personal_code)
async def process_personal_code(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    personal_code = message.text.strip().upper()
    
    # Ищем пользователя с таким персональным кодом
    target_user_id = None
    for uid, user_data in users_db.items():
        if user_data.get('personal_code', '').upper() == personal_code:
            target_user_id = uid
            break
    
    if not target_user_id:
        if lang == 'ru':
            await message.answer("❌ Пользователь с таким персональным кодом не найден.")
        else:
            await message.answer("❌ User with this personal code not found.")
        await state.clear()
        return
    
    await state.update_data(target_user_id=target_user_id)
    
    if lang == 'ru':
        await message.answer("Введите промокод для отправки:", reply_markup=get_cancel_keyboard(user_id))
    else:
        await message.answer("Enter promo code to send:", reply_markup=get_cancel_keyboard(user_id))
    
    await state.set_state(PromoStates.waiting_for_promo_to_send)

@dp.message(PromoStates.waiting_for_promo_to_send)
async def process_promo_to_send(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    promo_code = message.text.strip().upper()
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    
    if not target_user_id:
        if lang == 'ru':
            await message.answer("❌ Ошибка: пользователь не найден.")
        else:
            await message.answer("❌ Error: user not found.")
        await state.clear()
        return
    
    # Проверяем существование промокода
    if promo_code not in promocodes_db:
        if lang == 'ru':
            await message.answer("❌ Промокод не найден.")
        else:
            await message.answer("❌ Promo code not found.")
        await state.clear()
        return
    
    # Получаем данные промокода
    promo_data = promocodes_db[promo_code]
    
    # Добавляем промокод в неактивированные пользователя
    if 'inactive_promocodes' not in users_db[target_user_id]:
        users_db[target_user_id]['inactive_promocodes'] = []
    
    users_db[target_user_id]['inactive_promocodes'].append({
        'code': promo_code,
        'skin_name': promo_data['skin_name'],
        'skin_id': promo_data['skin_id'],
        'sent_by': user_id,
        'sent_at': datetime.now().strftime("%d.%m.%Y %H:%M")
    })
    save_data()
    
    # Отправляем уведомление пользователю
    try:
        target_lang = users_db[target_user_id].get('language', 'ru')
        if target_lang == 'ru':
            text = (
                f"🎁 Администратор отправил вам промокод!\n\n"
                f"🔹 Промокод: <code>{promo_code}</code>\n"
                f"🔹 Скин: {promo_data['skin_name']}\n\n"
                f"Вы можете активировать его в разделе '👤 Мой профиль'"
            )
        else:
            text = (
                f"🎁 Administrator sent you a promo code!\n\n"
                f"🔹 Promo code: <code>{promo_code}</code>\n"
                f"🔹 Skin: {promo_data['skin_name']}\n\n"
                f"You can activate it in '👤 My profile' section"
            )
        
        await bot.send_message(chat_id=target_user_id, text=text, parse_mode="HTML")
        
        if lang == 'ru':
            await message.answer(f"✅ Промокод успешно отправлен пользователю!", reply_markup=get_admin_keyboard(user_id))
        else:
            await message.answer(f"✅ Promo code successfully sent to user!", reply_markup=get_admin_keyboard(user_id))
    
    except Exception as e:
        logging.error(f"Error sending notification to user: {e}")
        if lang == 'ru':
            await message.answer("✅ Промокод добавлен пользователю, но не удалось отправить уведомление.", reply_markup=get_admin_keyboard(user_id))
        else:
            await message.answer("✅ Promo code added to user, but failed to send notification.", reply_markup=get_admin_keyboard(user_id))
    
    await state.clear()
# ========== ОБРАБОТКА ПРОМОКОДОВ ==========
@dp.message(F.text == "🎁 Активировать промокод")
@dp.message(F.text == "🎁 Activate promo code")
async def activate_promo_command(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    if lang == 'ru':
        await message.answer("Введите промокод для активации:", reply_markup=get_cancel_keyboard(user_id))
    else:
        await message.answer("Enter promo code to activate:", reply_markup=get_cancel_keyboard(user_id))
        
    await state.set_state(PromoStates.waiting_for_promo_input)

@dp.message(PromoStates.waiting_for_promo_input)
async def process_promo_input(message: types.Message, state: FSMContext):
    try:
        user_id = str(message.from_user.id)
        lang = users_db.get(user_id, {}).get('language', 'ru')
        promo_code = message.text.strip().upper()
        
        if not promo_code:
            if lang == 'ru':
                await message.answer("Пожалуйста, укажите промокод.")
            else:
                await message.answer("Please enter promo code.")
            return

        if promo_code not in promocodes_db:
            if lang == 'ru':
                await message.answer("❌ Промокод не найден.")
            else:
                await message.answer("❌ Promo code not found.")
            await state.clear()
            return

        promo_data = promocodes_db[promo_code]
        used_by = promo_data.get("used_by", []) or []
        max_activations = promo_data.get("max_activations", 0)
        allow_multiple = promo_data.get("allow_multiple", False)

        # Проверяем, есть ли неактивированный промокод у пользователя
        has_inactive = any(p['code'] == promo_code for p in users_db.get(user_id, {}).get('inactive_promocodes', []))
        
        # Если промокод уже использован и не многоразовый, и нет неактивированной версии
        if user_id in used_by and not allow_multiple and not has_inactive:
            if lang == 'ru':
                await message.answer("❌ Вы уже активировали этот промокод.")
            else:
                await message.answer("❌ You have already activated this promo code.")
            await state.clear()
            return

        if len(used_by) >= max_activations and not has_inactive:
            if lang == 'ru':
                await message.answer("❌ Превышено максимальное количество активаций для этого промокода.")
            else:
                await message.answer("❌ Maximum activations exceeded for this promo code.")
            await state.clear()
            return

        # Если это активация из неактивированных, не добавляем в used_by повторно
        if not has_inactive:
            used_by.append(user_id)
            promo_data["used_by"] = used_by
            save_data()  # Сохраняем изменения в промокоде
        
        # Сохраняем информацию о промокоде для выбора действия
        await state.update_data(
            activated_promo=promo_code,
            promo_data={
                "code": promo_code,
                "skin_name": promo_data["skin_name"],
                "skin_id": promo_data["skin_id"],
                "from_inactive": has_inactive  # Флаг, что активируем из неактивных
            }
        )
        await state.set_state(PromoStates.waiting_for_activation_choice)

        if lang == 'ru':
            await message.answer(
                f"✅ Промокод <code>{promo_code}</code> успешно активирован!\n\n"
                f"🎁 Вы получили скин: {promo_data['skin_name']}\n\n"
                f"Хотите вывести его сейчас в игру или оставить в профиле?",
                reply_markup=get_after_activation_keyboard(user_id),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"✅ Promo code <code>{promo_code}</code> successfully activated!\n\n"
                f"🎁 You received skin: {promo_data['skin_name']}\n\n"
                f"Do you want to send it to game now or keep in profile?",
                reply_markup=get_after_activation_keyboard(user_id),
                parse_mode="HTML"
            )

    except Exception as e:
        logging.error(f"Error in process_promo_input: {str(e)}", exc_info=True)
        if lang == 'ru':
            await message.answer("❌ Произошла ошибка при активации промокода. Пожалуйста, попробуйте снова.")
        else:
            await message.answer("❌ An error occurred while activating the promo code. Please try again.")
        await state.clear()

@dp.message(PromoStates.waiting_for_activation_choice)
async def handle_activation_choice(message: types.Message, state: FSMContext):
    try:
        user_id = str(message.from_user.id)
        lang = users_db.get(user_id, {}).get('language', 'ru')
        data = await state.get_data()
        promo_code = data.get("activated_promo")
        promo_data = data.get("promo_data")
        from_inactive = data.get("from_inactive", False)
        
        if not promo_code or not promo_data:
            if lang == 'ru':
                await message.answer("❌ Не удалось обработать ваш выбор. Пожалуйста, попробуйте активировать промокод снова.")
            else:
                await message.answer("❌ Failed to process your choice. Please try activating the promo code again.")
            await state.clear()
            return
            
        user_text = message.text
        send_now_ru = "Вывести в игру сейчас"
        send_now_en = "Send to game now"
        keep_ru = "Оставить в профиле"
        keep_en = "Keep in profile"
        
        if user_text in [send_now_ru, send_now_en]:
            # Добавляем промокод в активные
            if promo_code not in users_db[user_id]["promocodes"]:
                users_db[user_id]["promocodes"].append(promo_code)
            
            # Удаляем из неактивированных, если был там
            users_db[user_id]['inactive_promocodes'] = [
                p for p in users_db[user_id].get('inactive_promocodes', []) 
                if p['code'] != promo_code
            ]
            
            save_data()
            
            # Генерируем код верификации
            verification_code = generate_verification_code()
            chat_region = users_db[user_id].get('chat_region', 'RU')
            
            await state.update_data({
                "verification_code": verification_code,
                "skin_id": promo_data['skin_id'],
                "chat_region": chat_region
            })
            await state.set_state(PromoStates.waiting_for_verification_code)
            
            if lang == 'ru':
                await message.answer(
                    f"Чтобы получить скин {promo_data['skin_name']} в игре, "
                    f"напишите в чат {chat_region} следующий код: <b>{verification_code}</b>\n\n"
                    "После этого нажмите кнопку подтверждения.",
                    parse_mode="HTML",
                    reply_markup=ReplyKeyboardMarkup(
                        keyboard=[[KeyboardButton(text="✅ Я отправил код")]],
                        resize_keyboard=True
                    )
                )
            else:
                await message.answer(
                    f"To receive skin {promo_data['skin_name']} in game, "
                    f"write in {chat_region} chat the following code: <b>{verification_code}</b>\n\n"
                    "After that press confirmation button.",
                    parse_mode="HTML",
                    reply_markup=ReplyKeyboardMarkup(
                        keyboard=[[KeyboardButton(text="✅ I sent the code")]],
                        resize_keyboard=True
                    )
                )
            
        elif user_text in [keep_ru, keep_en]:
            # Если это не из неактивных, добавляем в неактивированные
            if not from_inactive:
                if 'inactive_promocodes' not in users_db[user_id]:
                    users_db[user_id]['inactive_promocodes'] = []
                    
                # Проверяем, нет ли уже этого промокода в неактивированных
                existing = [p for p in users_db[user_id]['inactive_promocodes'] if p['code'] == promo_code]
                if not existing:
                    users_db[user_id]['inactive_promocodes'].append({
                        'code': promo_code,
                        'skin_name': promo_data['skin_name'],
                        'skin_id': promo_data['skin_id'],
                        'activated_at': datetime.now().strftime("%d.%m.%Y %H:%M")
                    })
                    save_data()
            
            if lang == 'ru':
                await message.answer(
                    f"📁 Промокод сохранен в вашем профиле.\n"
                    f"Вы можете активировать его в любое время через раздел '👤 Мой профиль'.",
                    reply_markup=get_main_keyboard(user_id)
                )
            else:
                await message.answer(
                    f"📁 Promo code saved in your profile.\n"
                    f"You can activate it anytime in '👤 My profile' section.",
                    reply_markup=get_main_keyboard(user_id))
            await state.clear()
        else:
            if lang == 'ru':
                await message.answer("Пожалуйста, выберите один из предложенных вариантов.")
            else:
                await message.answer("Please choose one of the suggested options.")
            return
            
    except Exception as e:
        logging.error(f"Error in handle_activation_choice: {str(e)}", exc_info=True)
        if lang == 'ru':
            await message.answer("❌ Произошла ошибка при обработке вашего выбора. Пожалуйста, попробуйте снова.")
        else:
            await message.answer("❌ An error occurred while processing your choice. Please try again.")
        await state.clear()

@dp.message(PromoStates.waiting_for_verification_code)
async def process_verification_code(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    data = await state.get_data()
    
    verification_code = data.get("verification_code")
    skin_id = data.get("skin_id")
    chat_region = data.get("chat_region")
    skin_name = data.get("skin_name", "Неизвестно")
    
    if lang == 'ru':
        confirm_text = "✅ Я отправил код"
    else:
        confirm_text = "✅ I sent the code"
    
    if message.text != confirm_text:
        if lang == 'ru':
            await message.answer("Пожалуйста, отправьте код в чат игры и нажмите кнопку подтверждения.")
        else:
            await message.answer("Please send the code to game chat and press confirmation button.")
        return
    
    # Получаем playerID из чата игры
    player_id = await get_user_id_from_chat(verification_code, chat_region)
    
    if not player_id:
        if lang == 'ru':
            await message.answer("❌ Не удалось найти ваш код в чате. Убедитесь, что вы отправили его правильно.")
        else:
            await message.answer("❌ Failed to find your code in chat. Make sure you sent it correctly.")
        await state.clear()
        return
    
    # Отправляем скин в игру и проверяем результат
    success = await send_skin_to_game(player_id, skin_id, chat_region)
    
    if success:
        if lang == 'ru':
           await message.answer(
        "🎉 Трейд был отправлен вам на аккаунт!\n"
        "Если трейда нет, значит в игре временно заблокированы трейды.",
        reply_markup=get_main_keyboard(user_id))
        else:
          await message.answer(
        "🎉 The trade has been sent to your account!\n"
        "If there is no trade, it means that trades are temporarily blocked in the game.",
        reply_markup=get_main_keyboard(user_id))
    
#----Добавить бесплатный скин----
@dp.message(F.text == "🎁 Добавить бесплатный скин")
@dp.message(F.text == "🎁 Add free skin")
async def add_free_skin_start(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    if not users_db.get(user_id, {}).get('is_admin', False):
        if lang == 'ru':
            await message.answer("❌ У вас нет прав администратора.")
        else:
            await message.answer("❌ You don't have admin privileges.")
        return
    
    if lang == 'ru':
        await message.answer("Введите название скина:", reply_markup=get_cancel_keyboard(user_id))
    else:
        await message.answer("Enter skin name:", reply_markup=get_cancel_keyboard(user_id))
    
    await state.set_state(PromoStates.waiting_for_skin_name)

@dp.message(PromoStates.waiting_for_skin_name)
async def process_skin_name_for_free(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    skin_name = message.text.strip()
    
    if not skin_name:
        if lang == 'ru':
            await message.answer("Пожалуйста, введите название скина.")
        else:
            await message.answer("Please enter skin name.")
        return
    
    await state.update_data(skin_name=skin_name)
    
    if lang == 'ru':
        await message.answer("Введите ID скина (из API игры):", reply_markup=get_cancel_keyboard(user_id))
    else:
        await message.answer("Enter skin ID (from game API):", reply_markup=get_cancel_keyboard(user_id))
    
    await state.set_state(PromoStates.waiting_for_skin_id)

@dp.message(PromoStates.waiting_for_skin_name)
async def process_skin_name_for_promo(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    skin_name = message.text.strip()
    
    if not skin_name:
        if lang == 'ru':
            await message.answer("Пожалуйста, введите название скина.")
        else:
            await message.answer("Please enter skin name.")
        return
    
    await state.update_data(skin_name=skin_name)
    
    if lang == 'ru':
        await message.answer("Введите ID скина (из API игры):", reply_markup=get_cancel_keyboard(user_id))
    else:
        await message.answer("Enter skin ID (from game API):", reply_markup=get_cancel_keyboard(user_id))
    
    await state.set_state(PromoStates.waiting_for_skin_id)

@dp.message(PromoStates.waiting_for_skin_id)
async def process_skin_id_for_promo(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    skin_id = message.text.strip()
    
    if not skin_id:
        if lang == 'ru':
            await message.answer("Пожалуйста, введите ID скина.")
        else:
            await message.answer("Please enter skin ID.")
        return
    
    await state.update_data(skin_id=skin_id)
    
    if lang == 'ru':
        await message.answer("Введите максимальное количество активаций (0 - без ограничений):", reply_markup=get_cancel_keyboard(user_id))
    else:
        await message.answer("Enter max activations count (0 - unlimited):", reply_markup=get_cancel_keyboard(user_id))
    
    await state.set_state(PromoStates.waiting_for_activations)

# ========== БЕСПЛАТНЫЕ СКИНЫ ==========
@dp.message(F.text == "🎁 Получить бесплатный скин")
@dp.message(F.text == "🎁 Get free skin")
async def get_free_skin(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    # Проверяем, есть ли скины для бесплатной раздачи
    if not free_skins_db:
        if lang == 'ru':
            await message.answer("❌ В данный момент нет скинов для бесплатной раздачи.")
        else:
            await message.answer("❌ There are no skins available for free distribution at the moment.")
        return
    
    # Проверяем, когда пользователь последний раз получал бесплатный скин
    last_claimed = users_db[user_id].get('last_free_skin')
    if last_claimed:
        last_claimed_date = datetime.strptime(last_claimed, "%d.%m.%Y %H:%M")
        days_passed = (datetime.now() - last_claimed_date).days
        if days_passed < 4:
            days_left = 4 - days_passed
            if lang == 'ru':
                await message.answer(f"❌ Вы уже получали бесплатный скин. Следующий будет доступен через {days_left} дней.")
            else:
                await message.answer(f"❌ You have already received a free skin. Next one will be available in {days_left} days.")
            return
    
    # Выбираем случайный скин из доступных
    skin_id, skin_data = random.choice(list(free_skins_db.items()))
    
    # Обновляем время последнего получения скина
    users_db[user_id]['last_free_skin'] = datetime.now().strftime("%d.%m.%Y %H:%M")
    save_data()
    
    # Генерируем код верификации
    verification_code = generate_verification_code()
    chat_region = users_db[user_id].get('chat_region', 'RU')
    
    await state.update_data(
        verification_code=verification_code,
        skin_id=skin_id,
        skin_name=skin_data.get('skin_name', 'Неизвестный скин'),
        chat_region=chat_region
    )
    await state.set_state(PromoStates.waiting_for_verification_code)
    
    if lang == 'ru':
        await message.answer(
            f"🎉 Вы получили бесплатный скин: {skin_data['skin_name']}\n\n"
            f"Чтобы получить его в игре, напишите в чат {chat_region} следующий код: <b>{verification_code}</b>\n\n"
            "После этого нажмите кнопку подтверждения.",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="✅ Я отправил код")]],
                resize_keyboard=True
            )
        )
    else:
        await message.answer(
            f"🎉 You received a free skin: {skin_data['skin_name']}\n\n"
            f"To receive it in game, write in {chat_region} chat the following code: <b>{verification_code}</b>\n\n"
            "After that press confirmation button.",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="✅ I sent the code")]],
                resize_keyboard=True
            )
        )

# ========== АДМИН ФУНКЦИИ ==========
@dp.message(F.text == "🆕 Создать промокод")
@dp.message(F.text == "🆕 Create promo code")
async def create_promo_start(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    if not users_db.get(user_id, {}).get('is_admin', False):
        if lang == 'ru':
            await message.answer("❌ У вас нет прав администратора.")
        else:
            await message.answer("❌ You don't have admin privileges.")
        return
    
    if lang == 'ru':
        await message.answer("Введите название скина для промокода:", reply_markup=get_cancel_keyboard(user_id))
    else:
        await message.answer("Enter skin name for promo code:", reply_markup=get_cancel_keyboard(user_id))
    
    await state.set_state(PromoStates.waiting_for_skin_name)

@dp.message(PromoStates.waiting_for_skin_name)
async def process_skin_name(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    skin_name = message.text.strip()
    
    if not skin_name:
        if lang == 'ru':
            await message.answer("Пожалуйста, введите название скина.")
        else:
            await message.answer("Please enter skin name.")
        return
    
    await state.update_data(skin_name=skin_name)
    
    if lang == 'ru':
        await message.answer("Введите ID скина (из API игры):", reply_markup=get_cancel_keyboard(user_id))
    else:
        await message.answer("Enter skin ID (from game API):", reply_markup=get_cancel_keyboard(user_id))
    
    await state.set_state(PromoStates.waiting_for_skin_id)

@dp.message(PromoStates.waiting_for_skin_id)
async def process_skin_id(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    skin_id = message.text.strip()
    
    if not skin_id:
        if lang == 'ru':
            await message.answer("Пожалуйста, введите ID скина.")
        else:
            await message.answer("Please enter skin ID.")
        return
    
    await state.update_data(skin_id=skin_id)
    
    if lang == 'ru':
        await message.answer("Введите максимальное количество активаций (0 - без ограничений):", reply_markup=get_cancel_keyboard(user_id))
    else:
        await message.answer("Enter max activations count (0 - unlimited):", reply_markup=get_cancel_keyboard(user_id))
    
    await state.set_state(PromoStates.waiting_for_activations)

@dp.message(PromoStates.waiting_for_activations)
async def process_activations(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    try:
        max_activations = int(message.text.strip())
        if max_activations < 0:
            raise ValueError
    except ValueError:
        if lang == 'ru':
            await message.answer("Пожалуйста, введите корректное число (0 или больше).")
        else:
            await message.answer("Please enter a valid number (0 or more).")
        return
    
    await state.update_data(max_activations=max_activations)
    
    if lang == 'ru':
        await message.answer("Разрешить многократную активацию одним пользователем? (да/нет):", reply_markup=get_cancel_keyboard(user_id))
    else:
        await message.answer("Allow multiple activations by one user? (yes/no):", reply_markup=get_cancel_keyboard(user_id))
    
    await state.set_state(PromoStates.waiting_for_multiple_choice)

@dp.message(PromoStates.waiting_for_multiple_choice)
async def process_multiple_choice(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    choice = message.text.strip().lower()
    
    if lang == 'ru':
        yes_choices = ['да', 'д', 'yes', 'y']
        no_choices = ['нет', 'н', 'no', 'n']
    else:
        yes_choices = ['yes', 'y']
        no_choices = ['no', 'n']
    
    if choice not in yes_choices + no_choices:
        if lang == 'ru':
            await message.answer("Пожалуйста, ответьте 'да' или 'нет'.")
        else:
            await message.answer("Please answer 'yes' or 'no'.")
        return
    
    allow_multiple = choice in yes_choices
    data = await state.get_data()
    
    # Генерируем промокод
    promo_code = generate_promocode()
    while promo_code in promocodes_db:
        promo_code = generate_promocode()
    
    # Сохраняем промокод
    promocodes_db[promo_code] = {
        "skin_name": data["skin_name"],
        "skin_id": data["skin_id"],
        "max_activations": data["max_activations"],
        "allow_multiple": allow_multiple,
        "created_by": user_id,
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "used_by": []
    }
    save_data()
    
    if lang == 'ru':
        await message.answer(
            f"✅ Промокод успешно создан!\n\n"
            f"🔹 Код: <code>{promo_code}</code>\n"
            f"🔹 Скин: {data['skin_name']}\n"
            f"🔹 ID скина: {data['skin_id']}\n"
            f"🔹 Макс. активаций: {data['max_activations'] if data['max_activations'] > 0 else '∞'}\n"
            f"🔹 Многократная активация: {'Да' if allow_multiple else 'Нет'}",
            parse_mode="HTML",
            reply_markup=get_admin_keyboard(user_id)
        )
    else:
        await message.answer(
            f"✅ Promo code successfully created!\n\n"
            f"🔹 Code: <code>{promo_code}</code>\n"
            f"🔹 Skin: {data['skin_name']}\n"
            f"🔹 Skin ID: {data['skin_id']}\n"
            f"🔹 Max activations: {data['max_activations'] if data['max_activations'] > 0 else '∞'}\n"
            f"🔹 Multiple activations: {'Yes' if allow_multiple else 'No'}",
            parse_mode="HTML",
            reply_markup=get_admin_keyboard(user_id)
        )
    
    await state.clear()

@dp.message(F.text == "📋 Список промокодов")
@dp.message(F.text == "📋 Promo codes list")
async def list_promocodes(message: types.Message):
    user_id = str(message.from_user.id)
    lang = users_db.get(user_id, {}).get('language', 'ru')
    
    if not users_db.get(user_id, {}).get('is_admin', False):
        if lang == 'ru':
            await message.answer("❌ У вас нет прав администратора.")
        else:
            await message.answer("❌ You don't have admin privileges.")
        return
    
    if not promocodes_db:
        if lang == 'ru':
            await message.answer("❌ Нет созданных промокодов.")
        else:
            await message.answer("❌ No promo codes created.")
        return
    
    if lang == 'ru':
        text = ("📋 Список промокодов:\n\n"
               "Чтобы удалить промокод, введите его номер (например: 1 или 1 2 для удаления нескольких)\n\n")
    else:
        text = ("📋 Promo codes list:\n\n"
               "To delete promo code, enter its number (e.g.: 1 or 1 2 to delete multiple)\n\n")
    
    for i, (code, data) in enumerate(promocodes_db.items(), 1):
        used_count = len(data.get("used_by", []))
        max_activations = data.get("max_activations", 0)
        
        if lang == 'ru':
            text += (
                f"{i}. <code>{code}</code> - {data['skin_name']}\n"
                f"▪️ Активаций: {used_count}/{max_activations if max_activations > 0 else '∞'}\n"
                f"▪️ Многократные: {'Да' if data.get('allow_multiple', False) else 'Нет'}\n"
                f"▪️ Создан: {data.get('created_at', 'неизвестно')}\n\n"
            )
        else:
            text += (
                f"{i}. <code>{code}</code> - {data['skin_name']}\n"
                f"▪️ Activations: {used_count}/{max_activations if max_activations > 0 else '∞'}\n"
                f"▪️ Multiple: {'Yes' if data.get('allow_multiple', False) else 'No'}\n"
                f"▪️ Created: {data.get('created_at', 'unknown')}\n\n"
            )
    
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "🔙 Назад")
@dp.message(F.text == "🔙 Back")
async def back_to_main(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    await state.clear()
    await message.answer(
        "Главное меню:" if users_db[user_id]['language'] == 'ru' else "Main menu:",
        reply_markup=get_main_keyboard(user_id))
    
# ========== ЗАПУСК БОТА ==========
async def main():
    logging.info("Starting bot...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Bot crashed: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())