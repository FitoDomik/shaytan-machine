from flask import Flask, send_file, request, jsonify
from flask_cors import CORS
import json
import os
import telebot
import logging
import sys
from datetime import datetime, timedelta, timezone
import tempfile
import threading
import time
import requests

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Глобальный конфиг
GLOBAL_CONFIG = {
    "special_mode": False,
    "special_students": {},
    "mode_expires_at": None,
    "salted_student": None
}

def save_config(config):
    try:
        global GLOBAL_CONFIG
        logger.info(f"Сохраняем конфиг в память: {config}")
        GLOBAL_CONFIG.update(config)
        logger.info(f"Конфиг после обновления: {GLOBAL_CONFIG}")
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения конфига: {e}", exc_info=True)
        return False

def load_config():
    try:
        global GLOBAL_CONFIG
        logger.info(f"Загружаем конфиг из памяти: {GLOBAL_CONFIG}")
        
        # Проверяем, не истекло ли время действия режима
        if GLOBAL_CONFIG.get('mode_expires_at'):
            expires_at = datetime.fromisoformat(GLOBAL_CONFIG['mode_expires_at'])
            if datetime.now() > expires_at:
                GLOBAL_CONFIG['special_mode'] = False
                GLOBAL_CONFIG['mode_expires_at'] = None
                logger.info("Время режима истекло, сбрасываем")
                
        return GLOBAL_CONFIG.copy()  # Возвращаем копию конфига
    except Exception as e:
        logger.error(f"Ошибка загрузки конфига: {e}", exc_info=True)
        return {
            "special_mode": False,
            "special_students": {},
            "mode_expires_at": None,
            "salted_student": None
        }

# Создаем бота
TOKEN = '7512260695:AAGRESRxQglZSb0mTFQri6ZFOha8PakUstA'
bot = telebot.TeleBot(TOKEN, threaded=False)

app = Flask(__name__)
CORS(app)

# Добавим обработку порта для Render
port = int(os.environ.get('PORT', 10000))

# Импортируем обработчики после создания бота
from bot import *

# Настраиваем вебхук при первом запросе
@app.before_first_request
def set_webhook():
    WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'https://shaytan-web.onrender.com')
    url = f"{WEBHOOK_URL}/{TOKEN}"
    try:
        logger.info("Начинаем настройку вебхука...")
        bot.remove_webhook()
        bot.set_webhook(url=url)
        logger.info(f"Вебхук установлен на {url}")
        
        try:
            bot.send_message(1228708306, f"🚀 Бот перезапущен\nWebhook URL: {url}")
            logger.info("Тестовое сообщение отправлено")
        except Exception as e:
            logger.error(f"Ошибка отправки тестового сообщения: {e}")
            
    except Exception as e:
        logger.error(f"Ошибка установки вебхука: {e}")

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        try:
            logger.info("Получен webhook запрос от Telegram")
            json_string = request.get_data().decode('utf-8')
            logger.info(f"Содержимое запроса: {json_string}")
            
            update = telebot.types.Update.de_json(json_string)
            
            if update.message:
                logger.info(f"Получено сообщение: {update.message.text}")
            elif update.callback_query:
                logger.info(f"Получен callback_query: {update.callback_query.data}")
            
            bot.process_new_updates([update])
            logger.info("Обновление успешно обработано")
            return 'ok', 200
            
        except Exception as e:
            logger.error("Ошибка обработки вебхука", exc_info=True)
            return str(e), 500
    return 'error', 403

@app.route('/')
def serve_html():
    return send_file('main.html')

@app.route('/config.json')
def serve_config():
    config = load_config()
    logger.info(f"Отдаем конфиг: {config}")
    return jsonify(config)

@app.route('/update_config', methods=['POST'])
def update_config():
    try:
        config = request.json
        if save_config(config):
            return jsonify({"success": True, "config": load_config()})
        else:
            return jsonify({"success": False, "error": "Failed to save config"}), 500
    except Exception as e:
        logger.error(f"Ошибка обновления конфига: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/test')
def test():
    try:
        bot.send_message(1228708306, "🔄 Тест соединения")
        return "OK", 200
    except Exception as e:
        logger.error(f"Ошибка теста: {e}", exc_info=True)
        return str(e), 500

@app.route('/test_special')
def test_special():
    try:
        config = load_config()
        expires_at = datetime.now() + timedelta(minutes=5)
        
        config['special_mode'] = True
        config['mode_expires_at'] = expires_at.isoformat()
        
        if save_config(config):
            logger.info(f"Режим свои включен до {expires_at}")
            return jsonify({
                "status": "success",
                "message": "Режим свои включен на 5 минут",
                "expires_at": expires_at.isoformat(),
                "config": load_config()
            })
        else:
            return jsonify({"status": "error", "message": "Failed to save config"}), 500
            
    except Exception as e:
        logger.error(f"Ошибка теста режима свои: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.before_first_request
def check_permissions():
    try:
        logger.info(f"Временная директория: {tempfile.gettempdir()}")
        logger.info(f"Текущая директория: {os.getcwd()}")
        logger.info(f"Содержимое текущей директории: {os.listdir()}")
        
        # Проверяем права на запись во временную директорию
        test_file = os.path.join(tempfile.gettempdir(), 'test_write.tmp')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        logger.info("Права на запись во временную директорию есть")
        
    except Exception as e:
        logger.error(f"Проблема с правами доступа: {e}", exc_info=True)

# Обновим функцию для работы с временем
def get_moscow_time():
    # Москва UTC+3
    moscow_tz = timezone(timedelta(hours=3))
    now = datetime.now(timezone.utc)  # Получаем время в UTC
    return now.astimezone(moscow_tz)  # Конвертируем в московское время

# Обновим обработчик callback_query
@bot.callback_query_handler(func=lambda call: call.data.startswith('special_'))
def handle_special_mode(call):
    logger.info(f"Обработка callback_query: {call.data}")
    try:
        config = load_config()
        
        if call.data == "special_off":
            logger.info("Выключение режима свои")
            config['special_mode'] = False
            config['mode_expires_at'] = None
            if save_config(config):
                bot.answer_callback_query(call.id, "Режим свои выключен ❌")
                bot.edit_message_text("Режим свои выключен ❌", 
                                    call.message.chat.id, 
                                    call.message.message_id)
            else:
                raise Exception("Не удалось сохранить конфиг")
            return

        minutes = int(call.data.split('_')[1])
        logger.info(f"Включение режима свои на {minutes} минут")
        
        # Используем UTC время для сохранения
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=minutes)
        
        config['special_mode'] = True
        config['mode_expires_at'] = expires_at.isoformat()
        
        if save_config(config):
            # Для отображения используем московское время
            moscow_expires = expires_at.astimezone(timezone(timedelta(hours=3)))
            bot.answer_callback_query(call.id, f"Режим свои включен на {minutes} минут ✅")
            bot.edit_message_text(
                f"Режим свои включен на {minutes} минут ✅\n" +
                f"Действует до: {moscow_expires.strftime('%H:%M:%S (МСК)')}", 
                call.message.chat.id, 
                call.message.message_id
            )
            logger.info("Режим свои успешно включен")
        else:
            raise Exception("Не удалось сохранить конфиг")
            
    except Exception as e:
        logger.error(f"Ошибка в обработке callback_query: {e}", exc_info=True)
        try:
            bot.answer_callback_query(call.id, "Произошла ошибка ❌")
        except:
            pass

# Обновим функцию проверки статуса
@bot.message_handler(commands=['status'])
def check_status(message):
    config = load_config()
    if config['special_mode']:
        expires_at = datetime.fromisoformat(config['mode_expires_at'])
        now = get_moscow_time()
        remaining = expires_at - now
        minutes = remaining.seconds // 60
        seconds = remaining.seconds % 60
        bot.reply_to(message, 
                    f"✅ Режим свои включен\n" +
                    f"Осталось: {minutes}:{seconds:02d}\n" +
                    f"Действует до: {expires_at.strftime('%H:%M:%S (МСК)')}")
    else:
        bot.reply_to(message, "❌ Режим свои выключен")

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

def keepalive():
    while True:
        try:
            # Пингуем наш сервер каждые 10 минут
            response = requests.get('https://shaytan-web.onrender.com/health')
            print(f"Keepalive ping: {response.status_code}")
        except Exception as e:
            print(f"Keepalive error: {e}")
        time.sleep(600)  # 10 минут

# Запускаем keepalive в отдельном потоке
keepalive_thread = threading.Thread(target=keepalive, daemon=True)
keepalive_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
