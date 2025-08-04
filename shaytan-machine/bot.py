from server import bot
import telebot
from telebot import types
import json
import time
from datetime import datetime, timedelta
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
import logging
import sys

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

state_storage = StateMemoryStorage()

waiting_for_number = {}  # Словарь для хранения состояний пользователей

def load_config():
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            # Проверяем, не истекло ли время действия режима
            if config['mode_expires_at']:
                expires_at = datetime.fromisoformat(config['mode_expires_at'])
                if datetime.now() > expires_at:
                    config['special_mode'] = False
                    config['mode_expires_at'] = None
                    save_config(config)
            return config
    except:
        return {"special_mode": False, "special_students": {}, "mode_expires_at": None}

def save_config(config):
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

# Заменим функцию load_students на прямое определение списка
STUDENTS = [
    "1 Алисафа Алескеров",
    "2 Александр Банзаков",
    "3 Роман Бирфельд",
    "4 Георгий Благочевский",
    "5 Артем Булатов",
    "6 Кирилл Валуйский",
    "7 Дмитрий Грибков",
    "8 Даниил Данилин",
    "9 Дарий Даценков",
    "10 Иван Долгополов",
    "11 Вячеслав Домнин",
    "12 Ярослав Дроздов",
    "13 Полина Егорова",
    "14 Дарья Жердева",
    "15 Илья Изразцов",
    "16 Михаил Казаков",
    "17 Антон Ковязин",
    "18 Андрей Кравченко",
    "19 Михаил Кузнецов",
    "20 Михаил Люкевич",
    "21 Елизавета Петина",
    "22 Арман Стройнов",
    "23 Борис Ступин",
    "24 Степан Тихомиров",
    "25 Александр Шмелев"
]

# Заменим функцию load_students на новую
def load_students():
    return STUDENTS

# Добавьте класс состояний
class BotStates(StatesGroup):
    waiting_for_number = State()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    logger.info(f"Получена команда /start от {message.from_user.id}")
    try:
        # Сначала попробуем отправить простое сообщение
        test_message = bot.send_message(message.chat.id, "⌛ Загрузка...")
        logger.info(f"Тестовое сообщение отправлено: {test_message.message_id}")
        
        # Если тестовое сообщение отправилось, создаем клавиатуру
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        show_students_btn = types.KeyboardButton('Показать список учеников')
        special_mode_btn = types.KeyboardButton('🎲 Режим свои')
        salt_btn = types.KeyboardButton('🎯 Насолить')
        markup.add(show_students_btn, special_mode_btn, salt_btn)
        
        welcome_text = (
            "👋 Привет! Я бот для управления шайтан-машиной.\n\n"
            "Доступные команды:\n"
            "/students - показать список учеников\n"
            "/special - включить режим свои\n"
            "/status - проверить статус режима\n"
            "/salt - насолить ученика"
        )
        
        # Отправляем основное сообщение
        main_message = bot.send_message(
            message.chat.id, 
            welcome_text, 
            reply_markup=markup,
            parse_mode='HTML'
        )
        logger.info(f"Основное сообщение отправлено: {main_message.message_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /start: {e}", exc_info=True)
        # Пробуем отправить сообщение об ошибке
        try:
            bot.send_message(message.chat.id, "❌ Произошла ошибка при обработке команды")
        except Exception as send_error:
            logger.error(f"Не удалось отправить сообщение об ошибке: {send_error}")

@bot.message_handler(commands=['special'])
@bot.message_handler(func=lambda message: message.text == '🎲 Режим свои')
def special_mode_menu(message):
    logger.info(f"Получена команда special от {message.from_user.id}")
    try:
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("15 минут", callback_data="special_15"),
            types.InlineKeyboardButton("30 минут", callback_data="special_30"),
            types.InlineKeyboardButton("45 минут", callback_data="special_45")
        )
        markup.row(types.InlineKeyboardButton("Выключить", callback_data="special_off"))
        
        bot.reply_to(message, "Выберите время действия режима:", reply_markup=markup)
        logger.info("Меню режима свои отправлено успешно")
    except Exception as e:
        logger.error(f"Ошибка при отправке меню режима свои: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('special_'))
def handle_special_mode(call):
    logger.info(f"Обработка callback_query: {call.data}")
    try:
        config = load_config()
        
        if call.data == "special_off":
            logger.info("Выключение режима свои")
            config['special_mode'] = False
            config['mode_expires_at'] = None
            save_config(config)
            bot.answer_callback_query(call.id, "Режим свои выключен ❌")
            bot.edit_message_text("Режим свои выключен ❌", 
                                call.message.chat.id, 
                                call.message.message_id)
            return

        minutes = int(call.data.split('_')[1])
        logger.info(f"Включение режима свои на {minutes} минут")
        
        expires_at = datetime.now() + timedelta(minutes=minutes)
        
        # Сбрасываем режим "насолить" при включении режима "свои"
        config['special_mode'] = True
        config['mode_expires_at'] = expires_at.isoformat()
        config['salted_student'] = None  # Сбрасываем насоленного ученика
        save_config(config)
        
        bot.answer_callback_query(call.id, f"Режим свои включен на {minutes} минут ✅")
        bot.edit_message_text(f"Режим свои включен на {minutes} минут ✅\n" +
                            f"Действует до: {expires_at.strftime('%H:%M:%S')}", 
                            call.message.chat.id, 
                            call.message.message_id)
        logger.info("Режим свои успешно включен")
        
    except Exception as e:
        logger.error(f"Ошибка в обработке callback_query: {e}", exc_info=True)
        try:
            bot.answer_callback_query(call.id, "Произошла ошибка ❌")
        except:
            pass

@bot.message_handler(commands=['status'])
def check_status(message):
    config = load_config()
    if config['special_mode']:
        expires_at = datetime.fromisoformat(config['mode_expires_at'])
        remaining = expires_at - datetime.now()
        minutes = remaining.seconds // 60
        seconds = remaining.seconds % 60
        bot.reply_to(message, 
                    f"✅ Режим свои включен\n" +
                    f"Осталось: {minutes}:{seconds:02d}\n" +
                    f"Действует до: {expires_at.strftime('%H:%M:%S')}")
    else:
        bot.reply_to(message, "❌ Режим свои выключен")

@bot.message_handler(commands=['students'])
@bot.message_handler(func=lambda message: message.text == 'Показать список учеников')
def show_students(message):
    students = load_students()
    students_text = "📝 Список учеников:\n\n" + "\n".join(students)
    bot.reply_to(message, students_text)

@bot.message_handler(commands=['salt'])
@bot.message_handler(func=lambda message: message.text == '🎯 Насолить')
def salt_student_command(message):
    logger.info(f"Получена команда salt от {message.from_user.id}")
    try:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        show_students_btn = types.KeyboardButton('Показать список учеников')
        special_mode_btn = types.KeyboardButton('🎲 Режим свои')
        salt_btn = types.KeyboardButton('🎯 Насолить')
        markup.add(show_students_btn, special_mode_btn, salt_btn)
        
        # Устанавливаем состояние ожидания номера
        waiting_for_number[message.chat.id] = True
        
        bot.reply_to(message, 
                     "Введите номер ученика, которого хотите насолить 😈\n" +
                     "Этот ученик будет выбран следующим с вероятностью 100%",
                     reply_markup=markup)
        logger.info(f"Запрошен номер ученика от {message.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка при запросе номера ученика: {e}")

@bot.message_handler(func=lambda message: message.chat.id in waiting_for_number)
def handle_student_number(message):
    try:
        print(f"Получен номер: {message.text}")  # Отладка
        number = message.text.strip()
        
        # Проверяем, что введён существующий номер
        students = load_students()
        print(f"Загружен список учеников: {len(students)} учеников")  # Отладка
        
        valid_numbers = [s.split()[0] for s in students]
        print(f"Доступные номера: {valid_numbers}")  # Отладка
        
        if number not in valid_numbers:
            print(f"Номер {number} не найден в списке")  # Отладка
            bot.reply_to(message, f"❌ Ученик с номером {number} не найден")
            return
        
        print(f"Номер {number} найден, обновляем конфиг")  # Отладка
        config = load_config()
        
        # Отключаем режим "свои" при включении режима "насолить"
        config['special_mode'] = False
        config['mode_expires_at'] = None
        config['salted_student'] = number
        
        save_config(config)
        
        # Находим имя ученика
        student_name = next(s for s in students if s.split()[0] == number)
        print(f"Найден ученик: {student_name}")  # Отладка
        
        # Отправляем ответ
        response = f"😈 Пока-пока, {' '.join(student_name.split()[1:])}"
        print(f"Отправляем ответ: {response}")  # Отладка
        bot.reply_to(message, response)
        
        # Удаляем состояние ожидания
        del waiting_for_number[message.chat.id]
        print("Состояние сброшено")  # Отладка
        
    except Exception as e:
        print(f"Ошибка при обработке номера: {e}")  # Отладка
        bot.reply_to(message, "❌ Ошибка! Введите только номер ученика")
        if message.chat.id in waiting_for_number:
            del waiting_for_number[message.chat.id]

# Запускаем бота
if __name__ == '__main__':
    print("Бот запущен...")
    # Убираем bot.infinity_polling(), так как бот будет запускаться из server.py
