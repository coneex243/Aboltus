import requests
import time
import os
import re

VOICEBOX_URL = "http://localhost:17493"
PROFILE_ID = "adb5a098-e0f8-4a36-8d6e-3df89cca3cf7"
OUTPUT_DIR = "aboltus_voices"

RESPONSES = [
    "Хорошо", "Слушаю", "Скажи мое имя для активации", "Зеленский готов. Скажи мое имя для активации.",
    "Привет!", "Доброго дня!", "Мы з украины!", "Нормально, работаем.", "Добра.!", 
    "Я Зеленский - помощник.", "Твой голосовой помощник!", "Пожалуйста!", "Обращайся!", "Рад помочь!",
    "Пока Слава России!", "До встречи под киевом!", "Возвращайся на фронт!", "Хм, интересно. Попробуй другую команду например штурм.",
    "Попробуй сказать 'помощь' для списка команд и зброи.", "открываю браузер", "открываю YouTube", "открываю Google",
    "открываю GitHub", "открываю Reddit", "открываю веб-версию Telegram", "Телеграм запущен", 
    "не удалось запустить Telegram", "закрыл активное окно", "свернул активное окно", "свернул все окна",
    "переключил полноэкранный режим", "вышел из полноэкранного режима", "вернулся на предыдущую страницу", 
    "перешёл на следующую страницу", "пролистал страницу вниз", "пролистал страницу вверх",
    "открыл браузер в режиме инкогнито", "не удалось открыть инкогнито", "экран заблокирован", 
    "выключение отменено", "компьютер выключится через 60 секунд", "компьютер перезагрузится через 60 секунд",
    "перезагрузка отменена", "открываю проводник", "открываю папку Загрузки", "открываю папку Документы",
    "открываю рабочий стол", "открываю папку Изображения", "открываю папку Музыка",
    "открываю папку Видео", "открываю настройки", "открываю панель управления",
    "открываю диспетчер задач", "открываю командную строку", "открываю PowerShell",
    "открываю блокнот", "открываю калькулятор", "открываю Paint", "открываю камеру",
    "открываю окно Выполнить", "открываю очистку диска", "кликнул мышкой", "нажал правую кнопку мыши",
    "скриншот сохранён", "не удалось сделать скриншот", "корзина очищена", "не удалось очистить корзину",
    "Код скопирован в буфер", "Что написать?", "звук выключен", "звук включен", 
    "управление громкостью недоступно", "голосовые ответы отключены", "голосовые ответы включены",
    "программа свёрнута в трей", "окно восстановлено", "открываю 3D аватар", "закрываю 3D аватар",
    "Напоминания удалены", "Скажи: напомни мне текст через минуты или часы"
]

def sanitize_filename(text):
    return re.sub(r'[^\w\s-]', '', text.lower()).replace(' ', '_')[:40] + ".wav"

def generate_phrase(text):
    filename = sanitize_filename(text)
    filepath = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(filepath): return True

    print(f"⏳ Генерирую: '{text}'...", end=" ", flush=True)
    
    # Payload с учетом обязательных параметров модели
    payload = {
        "text": text,
        "profile_id": PROFILE_ID,
        "language": "ru",
        "engine": "qwen",
        "model": "qwen-1.7b"  # Добавили поле model, чтобы исправить ошибку 400
    }
    
    try:
        # Отправка запроса
        gen_resp = requests.post(f"{VOICEBOX_URL}/generate", json=payload)
        
        if gen_resp.status_code != 200:
            print(f"\n❌ Ошибка 400: Сервер требует другие параметры. Ответ: {gen_resp.text}")
            return False
            
        generation_id = gen_resp.json().get("id")
        
        # Ожидание
        while True:
            time.sleep(2)
            status_resp = requests.get(f"{VOICEBOX_URL}/generate/{generation_id}/status")
            status = status_resp.json().get("status", "")
            
            if status in ["complete", "success", "done"]: break
            if status in ["failed", "error"]: return False
            print(".", end="", flush=True)

        # Скачивание
        audio_resp = requests.get(f"{VOICEBOX_URL}/audio/{generation_id}")
        with open(filepath, "wb") as f: f.write(audio_resp.content)
        print(" ✅ Готово")
        return True
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    
    print(f"🚀 Старт генерации ({len(RESPONSES)} фраз)...")
    for phrase in RESPONSES:
        if generate_phrase(phrase):
            time.sleep(1) # Обязательная пауза
        else:
            time.sleep(3) # Дольше ждем при ошибке
    print("\n🎉 Все файлы созданы в папке 'aboltus_voices'!")