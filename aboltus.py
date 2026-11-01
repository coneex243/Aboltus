import os
import sys
import math
import time
import json
import threading
import subprocess
import webbrowser
import asyncio
import multiprocessing
import urllib.request
import urllib.parse
import re
import platform
import random
import gc
import psutil
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Union
import ctypes
import socket

# For startup and recycle bin
import winshell
from win32com.client import Dispatch

# For YouTube download and search
try:
    from pytube import YouTube, Search
    HAS_PYTUBE = True
except ImportError:
    HAS_PYTUBE = False
    print("[ВНИМАНИЕ] 'pytube' не установлен. Скачивание видео отключено.")

# For translation
try:
    from deep_translator import GoogleTranslator
    HAS_TRANSLATOR = True
except ImportError:
    HAS_TRANSLATOR = False
    print("[ВНИМАНИЕ] 'deep-translator' не установлен. Перевод отключён.")

# For weather
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("[ВНИМАНИЕ] 'requests' не установлен. Погода отключена.")

# For speed test
try:
    import speedtest
    HAS_SPEEDTEST = True
except ImportError:
    HAS_SPEEDTEST = False
    print("[ВНИМАНИЕ] 'speedtest-cli' не установлен. Тест скорости отключён.")

# For getting active window
try:
    import pygetwindow as gw
    HAS_PYGETWINDOW = True
except ImportError:
    HAS_PYGETWINDOW = False
    print("[ВНИМАНИЕ] 'pygetwindow' не установлен.")

# For parsing YouTube page
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    print("[ВНИМАНИЕ] 'beautifulsoup4' не установлен. Поиск видео по названию на странице ограничен.")

# For controlling audio
try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    from ctypes import cast, POINTER
    HAS_PYCAW = True
except ImportError:
    HAS_PYCAW = False
    print("[ВНИМАНИЕ] 'pycaw' не установлен. Управление громкостью ограничено.")

# For direct audio control via Windows API (fallback)
try:
    from ctypes import windll
    HAS_WINAPI_AUDIO = True
except:
    HAS_WINAPI_AUDIO = False

# Telegram bot
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False
    print("[ВНИМАНИЕ] 'python-telegram-bot' не установлен. Telegram-бот отключён.")

# For sound playback
try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False
    print("[ВНИМАНИЕ] 'pygame' не установлен. Воспроизведение звуков отключено.")

# Принудительная сборка мусора при старте
gc.enable()
gc.set_threshold(700, 10, 5)

# Базовая директория проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Telegram bot credentials (загружаются из config.yaml или переменных среды)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
PASSWORD = os.getenv("TELEGRAM_PASSWORD", "")
try:
    AUTHORIZED_USER_ID = int(os.getenv("AUTHORIZED_USER_ID", "0"))
except (ValueError, TypeError):
    AUTHORIZED_USER_ID = 0

# === ГОЛОСОВЫЕ ПРОФИЛИ ДЛЯ ОТВЕТОВ ===
VOICE_PROFILES = {
    "default": {
        "name": "Стандартный",
        "path": None,
        "use_tts": True,
        "responses": {}
    },
    "dexter": {
        "name": "Декстер",
        "path": os.path.join(BASE_DIR, "clone_voices", "aboltus_dexter"),
        "use_tts": False,
        "responses": {}
    },
    "zelensky": {
        "name": "Зеленский",
        "path": os.path.join(BASE_DIR, "clone_voices", "aboltus_zelens"),
        "use_tts": False,
        "responses": {}
    },
    "mell": {
        "name": "Мэлл",
        "path": os.path.join(BASE_DIR, "clone_voices", "aboltus_mell"),
        "use_tts": False,
        "responses": {}
    }
}

# === ФУНКЦИЯ ДЛЯ ПОИСКА ЗВУКОВЫХ ФАЙЛОВ ===
def find_audio_file(profile_path: str, search_phrase: str) -> Optional[str]:
    """Ищет звуковой файл по фразе, игнорируя хэш-суммы в конце имени"""
    if not profile_path or not os.path.exists(profile_path):
        return None
    
    # Очищаем фразу для поиска
    clean_phrase = search_phrase.lower().strip()
    clean_phrase = re.sub(r'[^\w\s]', '', clean_phrase)
    clean_phrase = clean_phrase.replace(' ', '_')
    
    # Получаем список всех аудиофайлов в директории
    audio_extensions = ('.wav', '.mp3', '.ogg')
    audio_files = [f for f in os.listdir(profile_path) if f.lower().endswith(audio_extensions)]
    
    # Функция для нормализации имени файла (удаляем хэш и расширение)
    def normalize_filename(filename):
        name = os.path.splitext(filename)[0]
        name = re.sub(r'_[a-f0-9]{8}$', '', name)
        name = re.sub(r'_$', '', name)
        return name.lower()
    
    # Сначала ищем точное совпадение нормализованных имён
    for audio_file in audio_files:
        normalized = normalize_filename(audio_file)
        if normalized == clean_phrase:
            return os.path.join(profile_path, audio_file)
    
    # Затем ищем частичное совпадение (файл содержит фразу)
    for audio_file in audio_files:
        normalized = normalize_filename(audio_file)
        if clean_phrase in normalized or normalized in clean_phrase:
            return os.path.join(profile_path, audio_file)
    
    # Ищем по ключевым словам (берём первые 1-2 слова из фразы)
    words = clean_phrase.split('_')
    for i in range(min(2, len(words)), 0, -1):
        key_phrase = '_'.join(words[:i])
        for audio_file in audio_files:
            normalized = normalize_filename(audio_file)
            if key_phrase == normalized or key_phrase in normalized:
                return os.path.join(profile_path, audio_file)
    
    # Пробуем найти "команда выполнена"
    for audio_file in audio_files:
        normalized = normalize_filename(audio_file)
        if "команда_выполнена" in normalized or normalized == "команда_выполнена":
            return os.path.join(profile_path, audio_file)
    
    return None

# === ФУНКЦИЯ ДЛЯ ВОСПРОИЗВЕДЕНИЯ ЗВУКОВЫХ ФАЙЛОВ ===
def play_sound_file(file_path: str):
    """Воспроизводит звуковой файл через pygame"""
    if not HAS_PYGAME or not file_path or not os.path.exists(file_path):
        return False
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        if pygame.mixer.get_busy():
            pygame.mixer.stop()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        return True
    except Exception as e:
        print(f"[SOUND] Ошибка воспроизведения {file_path}: {e}")
        return False

# === ОГРАНИЧЕНИЕ ПАМЯТИ ===
def check_memory_usage():
    try:
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        if memory_mb > 800:
            print(f"[MEMORY] Высокое использование памяти: {memory_mb:.0f}MB, очистка...")
            gc.collect()
            return True
        return False
    except:
        return False

def memory_monitor():
    while True:
        check_memory_usage()
        time.sleep(30)

threading.Thread(target=memory_monitor, daemon=True).start()

# Попытка импортировать CustomTkinter
try:
    import customtkinter as ctk
except ImportError:
    print("[ВНИМАНИЕ] Библиотека 'customtkinter' не найдена. Установите её: py -m pip install customtkinter")
    sys.exit(1)

# Проверка pywebview
try:
    import webview
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False
    print("[ВНИМАНИЕ] 'pywebview' не найден. Установите её: py -m pip install pywebview")

# Библиотеки для трея
try:
    from PIL import Image, ImageDraw
    import pystray
except ImportError:
    pystray = None
    print("[ИНФО] 'pystray' или 'Pillow' не найдены. Трей отключен.")

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Синтез речи (для стандартных голосов)
try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False
    print("[ВНИМАНИЕ] 'edge-tts' не установлен. TTS озвучка отключена.")

# Звуковое окружение
try:
    import sounddevice as sd
    import numpy as np
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

try:
    from vosk import Model, KaldiRecognizer
    HAS_VOSK = True
except ImportError:
    HAS_VOSK = False

# Список WebSocket клиентов для рендерера
WS_CLIENTS = set()

# Глобальная ссылка на приложение для Telegram бота
app_instance = None

# === УПРАВЛЕНИЕ ГРОМКОСТЬЮ ===
def set_volume(percent):
    percent = max(0, min(100, percent))
    try:
        if HAS_PYCAW:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(percent / 100.0, None)
            return True, f"громкость установлена на {percent}%"
    except Exception as e:
        print(f"[VOLUME] Ошибка pycaw: {e}")
        try:
            devices = AudioUtilities.GetSpeakers()
            volume = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(volume, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(percent / 100.0, None)
            return True, f"громкость установлена на {percent}%"
        except:
            pass
    try:
        for _ in range(50):
            windll.user32.keybd_event(0xAF, 0, 0, 0)
            windll.user32.keybd_event(0xAF, 0, 2, 0)
            time.sleep(0.005)
        return False, f"громкость установлена на {percent}% (приблизительно)"
    except:
        return False, "управление громкостью недоступно"

def get_current_volume():
    try:
        if HAS_PYCAW:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            return int(volume.GetMasterVolumeLevelScalar() * 100)
    except:
        pass
    return 50

def volume_up(step=10):
    current = get_current_volume()
    new_vol = min(100, current + step)
    success, msg = set_volume(new_vol)
    return msg

def volume_down(step=10):
    current = get_current_volume()
    new_vol = max(0, current - step)
    success, msg = set_volume(new_vol)
    return msg

def volume_set(percent):
    success, msg = set_volume(percent)
    return msg

def volume_max():
    return volume_set(100)

def volume_min():
    return volume_set(5)

def volume_mute():
    try:
        if HAS_PYCAW:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMute(1, None)
            return "звук выключен"
    except:
        pass
    try:
        windll.user32.keybd_event(0xAD, 0, 0, 0)
        windll.user32.keybd_event(0xAD, 0, 2, 0)
        return "звук выключен"
    except:
        return "управление громкостью недоступно"

def volume_unmute():
    try:
        if HAS_PYCAW:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMute(0, None)
            return "звук включен"
    except:
        pass
    try:
        windll.user32.keybd_event(0xAD, 0, 0, 0)
        windll.user32.keybd_event(0xAD, 0, 2, 0)
        return "звук включен"
    except:
        return "управление громкостью недоступно"

def parse_number_words(text):
    number_words = {
        "ноль": 0, "один": 1, "одна": 1, "одно": 1, "два": 2, "две": 2, "три": 3, "четыре": 4,
        "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10,
        "одиннадцать": 11, "двенадцать": 12, "тринадцать": 13, "четырнадцать": 14,
        "пятнадцать": 15, "шестнадцать": 16, "семнадцать": 17, "восемнадцать": 18,
        "девятнадцать": 19, "двадцать": 20, "тридцать": 30, "сорок": 40, "пятьдесят": 50,
        "шестьдесят": 60, "семьдесят": 70, "восемьдесят": 80, "девяносто": 90,
        "сто": 100, "двести": 200, "триста": 300, "четыреста": 400, "пятьсот": 500
    }
    for word, num in number_words.items():
        if word in text.lower():
            return num
    return None

def extract_number_from_text(text):
    digit_match = re.search(r'(\d+)', text)
    if digit_match:
        return int(digit_match.group(1))
    word_match = re.search(r'(ноль|один|два|три|четыре|пять|шесть|семь|восемь|девять|десять|одиннадцать|двенадцать|тринадцать|четырнадцать|пятнадцать|шестнадцать|семнадцать|восемнадцать|девятнадцать|двадцать|тридцать|сорок|пятьдесят|шестьдесят|семьдесят|восемьдесят|девяносто|сто|двести|триста|четыреста|пятьсот)', text.lower())
    if word_match:
        return parse_number_words(word_match.group(1))
    return None

# === АВТОЗАПУСК ===
def add_to_startup():
    try:
        exe_path = sys.executable if getattr(sys, 'frozen', False) else __file__
        startup_folder = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
        shortcut_path = os.path.join(startup_folder, "AboltusAssistant.lnk")
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = exe_path
        shortcut.WorkingDirectory = os.path.dirname(exe_path)
        shortcut.save()
        return True
    except Exception as e:
        print(f"[AUTOSTART] Ошибка: {e}")
        return False

def remove_from_startup():
    try:
        startup_folder = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
        shortcut_path = os.path.join(startup_folder, "AboltusAssistant.lnk")
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)
        return True
    except Exception as e:
        print(f"[AUTOSTART] Ошибка удаления: {e}")
        return False

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ WINAPI ===
def set_clipboard_text(text):
    if not ctypes.windll.user32.OpenClipboard(None):
        return False
    try:
        ctypes.windll.user32.EmptyClipboard()
        text_bytes = text.encode('utf-16-le')
        h_global_mem = ctypes.windll.kernel32.GlobalAlloc(0x0042, len(text_bytes) + 2)
        p_global_mem = ctypes.windll.kernel32.GlobalLock(h_global_mem)
        ctypes.memmove(p_global_mem, text_bytes, len(text_bytes))
        ctypes.windll.kernel32.GlobalUnlock(h_global_mem)
        ctypes.windll.user32.SetClipboardData(13, h_global_mem)
        return True
    except Exception:
        return False
    finally:
        ctypes.windll.user32.CloseClipboard()
        gc.collect()

def get_clipboard_text():
    try:
        ctypes.windll.user32.OpenClipboard(0)
        if ctypes.windll.user32.IsClipboardFormatAvailable(13):
            h_data = ctypes.windll.user32.GetClipboardData(13)
            p_data = ctypes.windll.kernel32.GlobalLock(h_data)
            text = ctypes.wstring_at(p_data)
            ctypes.windll.kernel32.GlobalUnlock(h_data)
            ctypes.windll.user32.CloseClipboard()
            return text
        ctypes.windll.user32.CloseClipboard()
    except:
        pass
    return None

def simulate_ctrl_v():
    time.sleep(0.5)
    ctypes.windll.user32.keybd_event(0x11, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x56, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x56, 0, 2, 0)
    ctypes.windll.user32.keybd_event(0x11, 0, 2, 0)

def simulate_ctrl_c():
    ctypes.windll.user32.keybd_event(0x11, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x43, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x43, 0, 2, 0)
    ctypes.windll.user32.keybd_event(0x11, 0, 2, 0)

def scroll_down():
    ctypes.windll.user32.keybd_event(0x22, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x22, 0, 2, 0)

def scroll_up():
    ctypes.windll.user32.keybd_event(0x21, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x21, 0, 2, 0)

def go_back():
    ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x25, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x25, 0, 2, 0)
    ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)

def go_forward():
    ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x27, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x27, 0, 2, 0)
    ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)

def mouse_click():
    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)

def mouse_right_click():
    ctypes.windll.user32.mouse_event(0x0008, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(0x0010, 0, 0, 0, 0)

def close_browser():
    ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x73, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x73, 0, 2, 0)
    ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)

def minimize_window():
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    ctypes.windll.user32.ShowWindow(hwnd, 6)

def minimize_all_windows():
    ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x44, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x44, 0, 2, 0)
    ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)

def open_incognito():
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for path in chrome_paths:
        if os.path.exists(path):
            subprocess.Popen([path, "--incognito", "https://google.com"])
            return True
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    for path in edge_paths:
        if os.path.exists(path):
            subprocess.Popen([path, "--inprivate", "https://google.com"])
            return True
    webbrowser.open("https://google.com")
    return False

def lock_pc():
    ctypes.windll.user32.LockWorkStation()

def get_system_info():
    try:
        mem = psutil.virtual_memory()
        return f"Компьютер: {platform.node()}, ОС: {platform.system()} {platform.release()}, RAM: {mem.total // (1024**3)}GB"
    except:
        return f"Компьютер: {platform.node()}, ОС: {platform.system()} {platform.release()}"

def open_folder(path):
    try:
        os.startfile(path)
        return True
    except:
        return False

def empty_recycle_bin():
    try:
        winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
        return True
    except:
        os.system('rd /s /q C:\\$Recycle.bin')
        return True

def fullscreen_active_window():
    ctypes.windll.user32.keybd_event(0x7A, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x7A, 0, 2, 0)

def exit_fullscreen():
    ctypes.windll.user32.keybd_event(0x1B, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x1B, 0, 2, 0)

def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        return response.json()['ip']
    except:
        try:
            response = requests.get('https://httpbin.org/ip', timeout=5)
            return response.json()['origin']
        except:
            return "Не удалось определить IP"

def get_location_by_ip():
    try:
        response = requests.get('https://ipapi.co/json/', timeout=5)
        data = response.json()
        return data.get('city', 'Москва'), data.get('country_name', 'Россия')
    except:
        return "Москва", "Россия"

def get_weather():
    try:
        city, country = get_location_by_ip()
        url = f"https://wttr.in/{city}?format=%C+%t+%w&lang=ru"
        response = requests.get(url, timeout=5)
        weather = response.text.strip()
        return f"В {city}: {weather}"
    except:
        return "Не удалось получить погоду"

def get_battery_status():
    try:
        battery = psutil.sensors_battery()
        if battery:
            percent = battery.percent
            plugged = battery.power_plugged
            status = "в сети" if plugged else "от батареи"
            return f"Заряд батареи: {percent}%, питание {status}"
        return "Информация о батарее недоступна"
    except:
        return "Не удалось получить статус батареи"

def get_random_joke():
    try:
        response = requests.get('https://official-joke-api.appspot.com/random_joke', timeout=5)
        data = response.json()
        return f"{data['setup']} {data['punchline']}"
    except:
        jokes = [
            "Почему программисты не путают Хэллоуин и Рождество? Потому что 31 октября это 25 декабря!",
            "Встречаются два админа. Один говорит: 'У меня проблема'. Второй: 'У меня решение'.",
            "Сколько программистов нужно, чтобы заменить лампочку? Нисколько, это аппаратная проблема!"
        ]
        return random.choice(jokes)

def get_current_youtube_url():
    try:
        if HAS_PYGETWINDOW:
            active_window = gw.getActiveWindow()
            if active_window and ('chrome' in active_window.title.lower() or 'edge' in active_window.title.lower() or 'youtube' in active_window.title.lower()):
                ctypes.windll.user32.keybd_event(0x11, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0x4C, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0x4C, 0, 2, 0)
                ctypes.windll.user32.keybd_event(0x11, 0, 2, 0)
                time.sleep(0.3)
                simulate_ctrl_c()
                time.sleep(0.3)
                url = get_clipboard_text()
                if url and ('youtube.com/watch' in url or 'youtu.be' in url):
                    return url
        return None
    except:
        return None

def get_youtube_videos_from_page():
    try:
        if HAS_PYGETWINDOW:
            active_window = gw.getActiveWindow()
            if active_window and ('youtube.com' in active_window.title.lower() or 'youtube -' in active_window.title.lower()):
                ctypes.windll.user32.keybd_event(0x11, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0x4C, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0x4C, 0, 2, 0)
                ctypes.windll.user32.keybd_event(0x11, 0, 2, 0)
                time.sleep(0.3)
                simulate_ctrl_c()
                time.sleep(0.3)
                page_url = get_clipboard_text()
                if page_url and 'youtube.com' in page_url and HAS_BS4:
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    response = requests.get(page_url, headers=headers, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    videos = []
                    video_elements = soup.find_all('a', href=re.compile(r'/watch\?v='))
                    seen_ids = set()
                    for elem in video_elements:
                        href = elem.get('href', '')
                        video_id_match = re.search(r'/watch\?v=([^&]+)', href)
                        if video_id_match:
                            video_id = video_id_match.group(1)
                            if video_id not in seen_ids:
                                seen_ids.add(video_id)
                                title_elem = elem.find('yt-formatted-string', {'class': 'style-scope ytd-video-renderer'})
                                if not title_elem:
                                    title_elem = elem.find('span', {'class': 'title'})
                                if not title_elem:
                                    title_elem = elem
                                title = title_elem.get_text(strip=True) if title_elem else elem.get('title', '')
                                if title and video_id:
                                    videos.append({'title': title, 'id': video_id})
                    return videos
        return []
    except Exception as e:
        print(f"[YOUTUBE PARSE] Ошибка: {e}")
        return []

def search_video_on_current_page(query):
    videos = get_youtube_videos_from_page()
    if not videos:
        return None
    query_words = query.lower().split()
    best_match = None
    best_score = 0
    for video in videos:
        title_lower = video['title'].lower()
        score = 0
        for word in query_words:
            if word in title_lower:
                score += 1
        if score > best_score:
            best_score = score
            best_match = video
    return best_match if best_score > 0 else None

def open_youtube_video_on_current_page(query):
    video = search_video_on_current_page(query)
    if video:
        video_url = f"https://youtube.com/watch?v={video['id']}"
        webbrowser.open(video_url)
        return f"Открываю видео: {video['title'][:50]}"
    return None

def download_current_youtube_video():
    url = get_current_youtube_url()
    if url:
        return download_youtube_video(url)
    return "Не удалось найти открытое видео YouTube. Откройте видео в браузере и повторите команду."

def download_youtube_video(url):
    if not HAS_PYTUBE:
        return "Библиотека pytube не установлена"
    try:
        yt = YouTube(url)
        stream = yt.streams.get_highest_resolution()
        download_path = os.path.expanduser("~/Downloads")
        filename = f"{yt.title}.mp4"
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        stream.download(output_path=download_path, filename=filename)
        return f"Видео '{yt.title[:50]}' скачано в {download_path}"
    except Exception as e:
        return f"Ошибка скачивания: {e}"

def search_and_open_youtube_video(query):
    if not HAS_PYTUBE:
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
        return f"Открываю поиск по запросу: {query}"
    try:
        s = Search(query)
        if s.results and len(s.results) > 0:
            video_url = f"https://youtube.com/watch?v={s.results[0].video_id}"
            webbrowser.open(video_url)
            return f"Открываю видео: {s.results[0].title[:50]}"
        else:
            webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
            return f"Видео не найдено, открываю поиск по запросу: {query}"
    except:
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
        return f"Открываю поиск по запросу: {query}"

# === ПЕРЕВОД С ВСПЛЫВАЮЩИМ ОКНОМ ===
class TranslatePopup(ctk.CTkToplevel):
    def __init__(self, parent, original_text, translated_text):
        super().__init__(parent)
        self.title("Перевод")
        self.geometry("500x400")
        self.resizable(True, True)
        self.attributes("-topmost", True)
        self.configure(fg_color="#0a0e17")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        main_frame = ctk.CTkFrame(self, fg_color="#101622", corner_radius=16)
        main_frame.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(main_frame, text="Оригинальный текст:", font=("Arial", 14, "bold"), text_color="#00f2fe").grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        original_box = ctk.CTkTextbox(main_frame, height=120, wrap="word", font=("Arial", 12))
        original_box.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="nsew")
        original_box.insert("1.0", original_text)
        original_box.configure(state="disabled")
        ctk.CTkLabel(main_frame, text="Перевод:", font=("Arial", 14, "bold"), text_color="#7928ca").grid(row=2, column=0, padx=15, pady=(5, 5), sticky="w")
        translated_box = ctk.CTkTextbox(main_frame, height=120, wrap="word", font=("Arial", 12))
        translated_box.grid(row=3, column=0, padx=15, pady=(0, 15), sticky="nsew")
        translated_box.insert("1.0", translated_text)
        translated_box.configure(state="disabled")
        btn_close = ctk.CTkButton(main_frame, text="Закрыть", fg_color="#ef4444", command=self.destroy, width=150)
        btn_close.grid(row=4, column=0, padx=15, pady=(0, 15))

def translate_text_with_popup():
    if not HAS_TRANSLATOR:
        return "Библиотека deep-translator не установлена"
    time.sleep(0.2)
    simulate_ctrl_c()
    time.sleep(0.3)
    text = get_clipboard_text()
    if not text or len(text.strip()) == 0:
        return "Не удалось получить текст для перевода. Выделите текст мышкой."
    try:
        has_cyrillic = any(ord(c) > 0x0400 and ord(c) < 0x0500 for c in text[:100])
        if has_cyrillic:
            translator = GoogleTranslator(source='ru', target='en')
            lang_name = 'английский'
            translated = translator.translate(text)
        else:
            translator = GoogleTranslator(source='auto', target='ru')
            lang_name = 'русский'
            translated = translator.translate(text)
        if app_instance:
            app_instance.after(0, lambda: TranslatePopup(app_instance, text, translated))
        set_clipboard_text(translated)
        return f"Переведено на {lang_name}. Результат в буфере обмена и в окне."
    except Exception as e:
        return f"Ошибка перевода: {e}"

def translate_text():
    return translate_text_with_popup()

def test_internet_speed():
    if not HAS_SPEEDTEST:
        return "Библиотека speedtest-cli не установлена. Установите: pip install speedtest-cli"
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download = st.download() / 1_000_000
        upload = st.upload() / 1_000_000
        ping = st.results.ping
        return f"Скорость: {download:.1f} Мбит/с на загрузку, {upload:.1f} Мбит/с на отдачу, пинг: {ping:.0f} мс"
    except Exception as e:
        return f"Ошибка теста скорости: {e}"

# === ПАРСИНГ ВРЕМЕНИ ДЛЯ НАПОМИНАНИЙ ===
def parse_reminder_time(text):
    patterns = [
        (r'через\s+(\d+)\s+секунд(?:у|ы)?', 'seconds'),
        (r'через\s+(\d+)\s+минут(?:у|ы)?', 'minutes'),
        (r'через\s+(\d+)\s+минуту', 'minutes'),
        (r'через\s+(\d+)\s+час(?:а|ов)?', 'hours'),
        (r'через\s+(\d+)\s+часа', 'hours'),
        (r'через\s+(\d+)\s+часов', 'hours'),
        (r'через\s+(\d+)\s+день(?:я|ей)?', 'days'),
        (r'через\s+(\d+)\s+дня', 'days'),
    ]
    for pattern, unit in patterns:
        match = re.search(pattern, text.lower())
        if match:
            value = int(match.group(1))
            if unit == 'seconds':
                return value
            elif unit == 'minutes':
                return value * 60
            elif unit == 'hours':
                return value * 3600
            elif unit == 'days':
                return value * 86400
    simple_patterns = [
        (r'(\d+)\s+секунд(?:у|ы)?', 'seconds'),
        (r'(\d+)\s+минут(?:у|ы)?', 'minutes'),
        (r'(\d+)\s+минуту', 'minutes'),
        (r'(\d+)\s+час(?:а|ов)?', 'hours'),
        (r'(\d+)\s+часа', 'hours'),
        (r'(\d+)\s+день(?:я|ей)?', 'days'),
    ]
    for pattern, unit in simple_patterns:
        match = re.search(pattern, text.lower())
        if match:
            value = int(match.group(1))
            if unit == 'seconds':
                return value
            elif unit == 'minutes':
                return value * 60
            elif unit == 'hours':
                return value * 3600
            elif unit == 'days':
                return value * 86400
    return None

def voice_confirm_shutdown():
    confirm_dialog = ctk.CTk()
    confirm_dialog.title("Подтверждение")
    confirm_dialog.geometry("350x180")
    confirm_dialog.resizable(False, False)
    confirm_dialog.attributes("-topmost", True)
    result = [False]
    ctk.CTkLabel(confirm_dialog, text="Вы уверены, что хотите\nвыключить компьютер?", font=("Arial", 14)).pack(pady=20)
    btn_frame = ctk.CTkFrame(confirm_dialog)
    btn_frame.pack(pady=10)
    def on_yes():
        result[0] = True
        confirm_dialog.destroy()
    def on_no():
        result[0] = False
        confirm_dialog.destroy()
    ctk.CTkButton(btn_frame, text="✅ Да", fg_color="green", width=100, command=on_yes).pack(side="left", padx=10)
    ctk.CTkButton(btn_frame, text="❌ Нет", fg_color="red", width=100, command=on_no).pack(side="left", padx=10)
    confirm_dialog.mainloop()
    return result[0]

def voice_confirm_restart():
    confirm_dialog = ctk.CTk()
    confirm_dialog.title("Подтверждение")
    confirm_dialog.geometry("350x180")
    confirm_dialog.resizable(False, False)
    confirm_dialog.attributes("-topmost", True)
    result = [False]
    ctk.CTkLabel(confirm_dialog, text="Вы уверены, что хотите\nперезагрузить компьютер?", font=("Arial", 14)).pack(pady=20)
    btn_frame = ctk.CTkFrame(confirm_dialog)
    btn_frame.pack(pady=10)
    def on_yes():
        result[0] = True
        confirm_dialog.destroy()
    def on_no():
        result[0] = False
        confirm_dialog.destroy()
    ctk.CTkButton(btn_frame, text="✅ Да", fg_color="green", width=100, command=on_yes).pack(side="left", padx=10)
    ctk.CTkButton(btn_frame, text="❌ Нет", fg_color="red", width=100, command=on_no).pack(side="left", padx=10)
    confirm_dialog.mainloop()
    return result[0]

# === ЛОКАЛЬНЫЙ ИИ ЧЕРЕЗ OLLAMA ===
class OllamaAI:
    def __init__(self):
        self.conversation_history = []
        self.models = ["llama3:latest", "qwen2.5:0.5b"]
        self.current_model = "qwen2.5:0.5b"
        self.available = self.check_ollama()
        self.max_history = 10
        self.last_request_time = 0
        self.request_delay = 1
        
    def check_ollama(self):
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode('utf-8'))
                if 'models' in data and len(data['models']) > 0:
                    for m in data['models']:
                        if 'qwen' in m['name'] or '0.5b' in m['name']:
                            self.current_model = m['name']
                            break
                    print(f"[OLLAMA] Доступны модели, используем: {self.current_model}")
                    return True
            return False
        except Exception as e:
            print(f"[OLLAMA] Ollama не запущен: {e}")
            return False
    
    def ask(self, prompt: str, ironic_mode: bool = False) -> str:
        if not self.available:
            return self.local_fallback(prompt, ironic_mode)
        if time.time() - self.last_request_time < self.request_delay:
            time.sleep(self.request_delay - (time.time() - self.last_request_time))
        self.last_request_time = time.time()
        if ironic_mode:
            system_prompt = "Ты Аболтус. Отвечай кратко (1-2 предложения) с юмором на русском."
        else:
            system_prompt = "Ты Аболтус. Отвечай кратко (1-2 предложения) дружелюбно на русском."
        context = ""
        for msg in self.conversation_history[-4:]:
            context += f"{msg}\n"
        full_prompt = f"{system_prompt}\n\n{context}Вопрос: {prompt}\n\nОтвет:"
        try:
            url = "http://localhost:11434/api/generate"
            data = {
                "model": self.current_model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 100,
                    "num_ctx": 1024
                }
            }
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'))
            req.add_header('Content-Type', 'application/json')
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                answer = result.get('response', '').strip()
                if answer:
                    answer = re.sub(r'^(Аболтус:|Ответ:|Ассистент:)\s*', '', answer)
                    answer = answer.strip()
                    if len(answer) > 300:
                        answer = answer[:300] + "..."
                    self.conversation_history.append(f"User: {prompt}")
                    self.conversation_history.append(f"Assistant: {answer}")
                    if len(self.conversation_history) > self.max_history:
                        self.conversation_history = self.conversation_history[-self.max_history:]
                    gc.collect()
                    return answer
                return "Не удалось получить ответ"
        except Exception as e:
            print(f"[OLLAMA ERROR] {e}")
            return self.local_fallback(prompt, ironic_mode)
    
    def local_fallback(self, prompt: str, ironic_mode: bool) -> str:
        prompt_lower = prompt.lower()
        basic_responses = {
            "привет": ["Привет!", "Здравствуй!", "Приветствую!"],
            "как дела": ["Нормально, работаю.", "Всё отлично!", "Хорошо!"],
            "кто ты": ["Я Аболтус - помощник.", "Твой голосовой помощник!"],
            "спасибо": ["Пожалуйста!", "Обращайся!", "Рад помочь!"],
            "пока": ["Пока!", "До встречи!", "Возвращайся!"]
        }
        for key, resp in basic_responses.items():
            if key in prompt_lower:
                return random.choice(resp) if isinstance(resp, list) else resp
        if ironic_mode:
            return "Хм, интересно. Попробуй другую команду."
        return "Попробуй сказать 'помощь' для списка команд."

# === ВСТРОЕННЫЕ КОМАНДЫ ===
class BuiltinCommands:
    @staticmethod
    def open_browser():
        webbrowser.open("https://google.com")
        return "открываю браузер"
    @staticmethod
    def open_youtube():
        webbrowser.open("https://youtube.com")
        return "открываю YouTube"
    @staticmethod
    def open_google():
        webbrowser.open("https://google.com")
        return "открываю Google"
    @staticmethod
    def say_time():
        now = datetime.now()
        return f"сейчас {now.hour} часов {now.minute} минут"
    @staticmethod
    def say_date():
        now = datetime.now()
        months = ["января", "февраля", "марта", "апреля", "мая", "июня", 
                  "июля", "августа", "сентября", "октября", "ноября", "декабря"]
        return f"сегодня {now.day} {months[now.month-1]} {now.year} года"
    @staticmethod
    def lock_computer():
        lock_pc()
        return "экран заблокирован"
    @staticmethod
    def system_info():
        return get_system_info()
    @staticmethod
    def cancel_shutdown():
        os.system("shutdown /a")
        return "выключение отменено"
    @staticmethod
    def volume_max():
        return volume_max()
    @staticmethod
    def volume_mid():
        return volume_set(50)
    @staticmethod
    def volume_min():
        return volume_min()
    @staticmethod
    def mute():
        return volume_mute()
    @staticmethod
    def unmute():
        return volume_unmute()
    @staticmethod
    def open_explorer():
        os.startfile("explorer.exe")
        return "открываю проводник"
    @staticmethod
    def open_downloads():
        open_folder(os.path.expanduser("~/Downloads"))
        return "открываю папку Загрузки"
    @staticmethod
    def open_documents():
        open_folder(os.path.expanduser("~/Documents"))
        return "открываю папку Документы"
    @staticmethod
    def open_desktop():
        open_folder(os.path.expanduser("~/Desktop"))
        return "открываю рабочий стол"
    @staticmethod
    def open_pictures():
        open_folder(os.path.expanduser("~/Pictures"))
        return "открываю папку Изображения"
    @staticmethod
    def open_music():
        open_folder(os.path.expanduser("~/Music"))
        return "открываю папку Музыка"
    @staticmethod
    def open_videos():
        open_folder(os.path.expanduser("~/Videos"))
        return "открываю папку Видео"
    @staticmethod
    def open_settings():
        os.system("start ms-settings:")
        return "открываю настройки"
    @staticmethod
    def open_control_panel():
        os.system("control")
        return "открываю панель управления"
    @staticmethod
    def open_task_manager():
        os.system("taskmgr")
        return "открываю диспетчер задач"
    @staticmethod
    def open_cmd():
        os.system("start cmd")
        return "открываю командную строку"
    @staticmethod
    def open_powershell():
        os.system("start powershell")
        return "открываю PowerShell"
    @staticmethod
    def open_notepad():
        os.system("notepad")
        return "открываю блокнот"
    @staticmethod
    def open_calculator():
        os.system("calc")
        return "открываю калькулятор"
    @staticmethod
    def open_paint():
        os.system("mspaint")
        return "открываю Paint"
    @staticmethod
    def take_screenshot():
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            screenshot.save(filename)
            os.startfile(filename)
            return "скриншот сохранён"
        except Exception as e:
            return f"не удалось сделать скриншот: {e}"
    @staticmethod
    def open_camera():
        os.system("start microsoft.windows.camera:")
        return "открываю камеру"
    @staticmethod
    def open_run():
        ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0x52, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0x52, 0, 2, 0)
        ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)
        return "открываю окно Выполнить"
    @staticmethod
    def tell_joke():
        return get_random_joke()
    @staticmethod
    def clear_system():
        os.system("cleanmgr")
        return "открываю очистку диска"
    @staticmethod
    def click_mouse():
        mouse_click()
        return "кликнул мышкой"
    @staticmethod
    def right_click():
        mouse_right_click()
        return "нажал правую кнопку мыши"
    @staticmethod
    def close_browser_window():
        close_browser()
        return "закрыл активное окно"
    @staticmethod
    def minimize_active_window():
        minimize_window()
        return "свернул активное окно"
    @staticmethod
    def minimize_all():
        minimize_all_windows()
        return "свернул все окна"
    @staticmethod
    def go_back():
        go_back()
        return "вернулся на предыдущую страницу"
    @staticmethod
    def go_forward():
        go_forward()
        return "перешёл на следующую страницу"
    @staticmethod
    def incognito_mode():
        if open_incognito():
            return "открыл браузер в режиме инкогнито"
        return "не удалось открыть инкогнито"
    @staticmethod
    def open_telegram():
        try:
            path = os.path.expandvars(r"%APPDATA%\Telegram Desktop\Telegram.exe")
            if os.path.exists(path):
                subprocess.Popen(path)
                return "Телеграм запущен"
            else:
                webbrowser.open("https://web.telegram.org")
                return "открываю веб-версию Telegram"
        except:
            return "не удалось запустить Telegram"
    @staticmethod
    def open_github():
        webbrowser.open("https://github.com")
        return "открываю GitHub"
    @staticmethod
    def open_reddit():
        webbrowser.open("https://reddit.com")
        return "открываю Reddit"
    @staticmethod
    def shutdown_pc():
        if voice_confirm_shutdown():
            os.system("shutdown /s /t 60")
            return "компьютер выключится через 60 секунд"
        return "выключение отменено"
    @staticmethod
    def restart_pc():
        if voice_confirm_restart():
            os.system("shutdown /r /t 60")
            return "компьютер перезагрузится через 60 секунд"
        return "перезагрузка отменена"
    @staticmethod
    def volume_up():
        return volume_up(10)
    @staticmethod
    def volume_down():
        return volume_down(10)
    @staticmethod
    def empty_bin():
        if empty_recycle_bin():
            return "корзина очищена"
        return "не удалось очистить корзину"
    @staticmethod
    def fullscreen():
        fullscreen_active_window()
        return "переключил полноэкранный режим"
    @staticmethod
    def exit_fullscreen():
        exit_fullscreen()
        return "вышел из полноэкранного режима"
    @staticmethod
    def get_ip():
        ip = get_public_ip()
        return f"ваш IP адрес: {ip}"
    @staticmethod
    def get_weather():
        return get_weather()
    @staticmethod
    def get_battery():
        return get_battery_status()
    @staticmethod
    def get_speed():
        return test_internet_speed()
    @staticmethod
    def translate():
        return translate_text()
    @staticmethod
    def download_video():
        return download_current_youtube_video()
    @staticmethod
    def scroll_page_down():
        scroll_down()
        return "пролистал страницу вниз"
    @staticmethod
    def scroll_page_up():
        scroll_up()
        return "пролистал страницу вверх"
    @staticmethod
    def search_youtube(query):
        return search_and_open_youtube_video(query)
    @staticmethod
    def search_youtube_on_page(query):
        result = open_youtube_video_on_current_page(query)
        if result:
            return result
        return search_and_open_youtube_video(query)
    @staticmethod
    def greet(user_name):
        greetings = [
            f"Привет, {user_name}!",
            f"Здарова, {user_name}!",
            f"И тебе привет, {user_name}!",
            f"Салют, {user_name}!"
        ]
        return random.choice(greetings)

def fetch_news():
    try:
        import xml.etree.ElementTree as ET
        url = "https://lenta.ru/rss/news"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as res:
            content = res.read().decode('utf-8', errors='ignore')
            root = ET.fromstring(content)
            items = root.findall('.//item')
            news_list = []
            for i, item in enumerate(items[:3]):
                title = item.find('title').text
                if title:
                    title = title.replace('&quot;', '"').replace('&amp;', '&')
                    news_list.append(title)
            if news_list:
                webbrowser.open("https://lenta.ru")
                return news_list
            return ["Не удалось получить новости"]
    except Exception as e:
        print(f"[NEWS ERROR] {e}")
        return ["Новости временно недоступны"]

def fetch_currency_rate(currency_code):
    mapping = {"доллар": "USD", "евро": "EUR", "юань": "CNY"}
    code = mapping.get(currency_code.lower(), "USD")
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        req = urllib.request.Request(url, headers={'User-Agent': 'AboltusAssistant/1.8'})
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode('utf-8'))
            rates = data.get("rates", {})
            if "RUB" in rates and code in rates:
                value_in_rub = rates["RUB"] / rates[code]
                return f"Курс {code} - {value_in_rub:.2f} рублей"
            return f"Валюта {code} не найдена"
    except Exception:
        return "Курс временно недоступен"

def fetch_wikipedia(query):
    try:
        search_url = f"https://ru.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json"
        req = urllib.request.Request(search_url, headers={'User-Agent': 'AboltusAssistant/1.8'})
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode('utf-8'))
            search_results = data.get("query", {}).get("search", [])
            if not search_results:
                return "Ничего не найдено"
            title = search_results[0]["title"]
        content_url = f"https://ru.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&titles={urllib.parse.quote(title)}&format=json"
        req2 = urllib.request.Request(content_url, headers={'User-Agent': 'AboltusAssistant/1.8'})
        with urllib.request.urlopen(req2, timeout=5) as res2:
            data2 = json.loads(res2.read().decode('utf-8'))
            pages = data2.get("query", {}).get("pages", {})
            for _, page_data in pages.items():
                extract = page_data.get("extract", "")
                if extract:
                    sentences = extract.split('. ')
                    return f"{'. '.join(sentences[:2])}"
            return f"Найдена статья про {title}"
    except Exception as e:
        return f"Ошибка: {e}"

def run_overlay_process(html_path):
    try:
        import webview
        window = webview.create_window(
            title='Aboltus 3D Visual',
            url=html_path,
            transparent=True,
            frameless=True,
            width=450,
            height=800,
            on_top=True
        )
        webview.start(gui='edgechromium', debug=False)
    except Exception as e:
        print(f"[ОШИБКА] Сбой оверлея: {e}")

class MacroDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Редактор макросов")
        self.geometry("750x650")
        self.minsize(650, 550)
        self.selected_trigger = None
        self.actions = []
        self.setup_ui()
        self.load_existing_macros()
        
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header_frame, text="📌 Редактор макросов", font=("Arial", 20, "bold"), text_color=self.parent.color_cyan).pack()
        main_paned = ctk.CTkFrame(self, fg_color="transparent")
        main_paned.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        main_paned.grid_columnconfigure(0, weight=1)
        main_paned.grid_columnconfigure(1, weight=2)
        main_paned.grid_rowconfigure(0, weight=1)
        left_panel = ctk.CTkFrame(main_paned, fg_color=self.parent.color_panel, corner_radius=12)
        left_panel.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        left_panel.grid_columnconfigure(0, weight=1)
        left_panel.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(left_panel, text="📋 Существующие макросы", font=("Arial", 14, "bold")).grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")
        self.macros_listbox = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
        self.macros_listbox.grid(row=1, column=0, padx=10, pady=(0, 15), sticky="nsew")
        self.macros_listbox.grid_columnconfigure(0, weight=1)
        right_panel = ctk.CTkFrame(main_paned, fg_color=self.parent.color_panel, corner_radius=12)
        right_panel.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(right_panel, text="✏️ Редактор макроса", font=("Arial", 14, "bold")).grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")
        ctk.CTkLabel(right_panel, text="Фраза-триггер:", font=("Arial", 12)).grid(row=1, column=0, padx=15, pady=(5, 2), sticky="w")
        self.trigger_entry = ctk.CTkEntry(right_panel, placeholder_text="Введите команду...", height=40)
        self.trigger_entry.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="ew")
        ctk.CTkLabel(right_panel, text="Действия:", font=("Arial", 12, "bold")).grid(row=3, column=0, padx=15, pady=(5, 5), sticky="w")
        self.actions_frame = ctk.CTkScrollableFrame(right_panel, height=200, fg_color="#0a0e17")
        self.actions_frame.grid(row=4, column=0, padx=15, pady=(0, 15), sticky="nsew")
        self.actions_frame.grid_columnconfigure(0, weight=1)
        self.refresh_actions_list()
        ctk.CTkLabel(right_panel, text="➕ Добавить действие:", font=("Arial", 12, "bold")).grid(row=5, column=0, padx=15, pady=(10, 5), sticky="w")
        action_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        action_frame.grid(row=6, column=0, padx=15, pady=(0, 15), sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(1, weight=3)
        self.action_type = ctk.CTkOptionMenu(action_frame, values=["open_url", "open_app", "run_command", "type_text"], width=130)
        self.action_type.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="ew")
        self.action_value = ctk.CTkEntry(action_frame, placeholder_text="URL/путь/команда/текст", height=40)
        self.action_value.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.btn_add = ctk.CTkButton(action_frame, text="➕", width=50, fg_color=self.parent.color_success, command=self.add_action)
        self.btn_add.grid(row=0, column=2, pady=5)
        btn_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        btn_frame.grid(row=7, column=0, padx=15, pady=(0, 20), sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        btn_frame.grid_columnconfigure(2, weight=1)
        self.btn_save = ctk.CTkButton(btn_frame, text="💾 Сохранить", fg_color=self.parent.color_success, command=self.save_macro, height=40)
        self.btn_save.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="ew")
        self.btn_delete = ctk.CTkButton(btn_frame, text="🗑 Удалить", fg_color=self.parent.color_alert, command=self.delete_selected_macro, height=40)
        self.btn_delete.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        self.btn_new = ctk.CTkButton(btn_frame, text="✨ Новый", fg_color=self.parent.color_cyan, text_color="#0a0e17", command=self.new_macro, height=40)
        self.btn_new.grid(row=0, column=2, padx=(10, 0), pady=5, sticky="ew")
    
    def load_existing_macros(self):
        for widget in self.macros_listbox.winfo_children():
            widget.destroy()
        if not self.parent.custom_macros:
            ctk.CTkLabel(self.macros_listbox, text="Нет сохранённых макросов", text_color="gray").pack(pady=20)
            return
        for trigger, macro_data in self.parent.custom_macros.items():
            actions = macro_data.get("actions", [])
            action_count = len(actions)
            btn = ctk.CTkButton(
                self.macros_listbox, 
                text=f"📌 {trigger} ({action_count} действий)",
                anchor="w",
                fg_color="transparent",
                hover_color=self.parent.color_panel,
                command=lambda t=trigger: self.load_macro_for_edit(t),
                height=35
            )
            btn.pack(fill="x", padx=5, pady=3)
    
    def load_macro_for_edit(self, trigger):
        self.selected_trigger = trigger
        macro_data = self.parent.custom_macros.get(trigger, {})
        actions = macro_data.get("actions", [])
        self.trigger_entry.delete(0, "end")
        self.trigger_entry.insert(0, trigger)
        self.actions = actions.copy()
        self.refresh_actions_list()
    
    def new_macro(self):
        self.selected_trigger = None
        self.trigger_entry.delete(0, "end")
        self.actions = []
        self.refresh_actions_list()
    
    def refresh_actions_list(self):
        for widget in self.actions_frame.winfo_children():
            widget.destroy()
        if not self.actions:
            ctk.CTkLabel(self.actions_frame, text="Нет действий. Нажмите 'Добавить'", text_color="gray").pack(pady=20)
            return
        for i, action in enumerate(self.actions):
            action_frame = ctk.CTkFrame(self.actions_frame, fg_color=self.parent.color_panel, corner_radius=8)
            action_frame.pack(fill="x", padx=5, pady=5)
            action_frame.grid_columnconfigure(0, weight=1)
            type_icon = {"open_url": "🌐", "open_app": "📱", "run_command": "⚡", "type_text": "📝"}.get(action["type"], "📌")
            ctk.CTkLabel(action_frame, text=f"{type_icon} {action['type']}: {action['value'][:50]}", anchor="w").grid(row=0, column=0, padx=10, pady=8, sticky="ew")
            btn_delete = ctk.CTkButton(action_frame, text="✖", width=40, fg_color="red", hover_color="#aa2222", command=lambda idx=i: self.delete_action(idx))
            btn_delete.grid(row=0, column=1, padx=5, pady=5)
    
    def delete_action(self, idx):
        self.actions.pop(idx)
        self.refresh_actions_list()
    
    def add_action(self):
        atype = self.action_type.get()
        avalue = self.action_value.get().strip()
        if not avalue:
            self.parent.log_message("SYSTEM", "Введите значение действия", is_error=True)
            return
        self.actions.append({"type": atype, "value": avalue})
        self.action_value.delete(0, "end")
        self.refresh_actions_list()
    
    def delete_selected_macro(self):
        trigger = self.trigger_entry.get().strip().lower()
        if not trigger:
            self.parent.log_message("SYSTEM", "Выберите макрос для удаления", is_error=True)
            return
        if trigger in self.parent.custom_macros:
            del self.parent.custom_macros[trigger]
            self.parent.save_custom_macros()
            self.parent.log_message("SYSTEM", f"Макрос '{trigger}' удалён")
            self.load_existing_macros()
            self.new_macro()
    
    def save_macro(self):
        trigger = self.trigger_entry.get().strip().lower()
        if not trigger:
            self.parent.log_message("SYSTEM", "Введите фразу-триггер", is_error=True)
            return
        if not self.actions:
            self.parent.log_message("SYSTEM", "Добавьте хотя бы одно действие", is_error=True)
            return
        self.parent.custom_macros[trigger] = {"actions": self.actions}
        self.parent.save_custom_macros()
        self.parent.log_message("SYSTEM", f"Макрос '{trigger}' сохранён с {len(self.actions)} действиями")
        self.load_existing_macros()
        self.new_macro()

class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Настройки")
        self.geometry("500x550")
        self.resizable(False, False)
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="Настройки ассистента", font=("Arial", 18, "bold")).grid(row=0, column=0, padx=20, pady=(20, 15))
        ctk.CTkLabel(self, text="Активационная фраза (wake word):", font=("Arial", 12)).grid(row=1, column=0, padx=20, pady=(5, 2), sticky="w")
        self.wake_word_entry = ctk.CTkEntry(self, placeholder_text="джарвис, алекса, окей гугл...", width=350)
        self.wake_word_entry.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="ew")
        ctk.CTkLabel(self, text="Голос ассистента:", font=("Arial", 12)).grid(row=3, column=0, padx=20, pady=(5, 2), sticky="w")
        self.voice_profile = ctk.CTkOptionMenu(self, values=list(VOICE_PROFILES.keys()), width=350)
        self.voice_profile.grid(row=4, column=0, padx=20, pady=(0, 15), sticky="ew")
        ctk.CTkLabel(self, text="Как ко мне обращаться:", font=("Arial", 12)).grid(row=5, column=0, padx=20, pady=(5, 2), sticky="w")
        self.user_name_entry = ctk.CTkEntry(self, placeholder_text="сэр, босс, командир...", width=350)
        self.user_name_entry.grid(row=6, column=0, padx=20, pady=(0, 15), sticky="ew")
        self.ironic_switch = ctk.CTkSwitch(self, text="Ироничный режим (Аболтус будет отвечать с юмором)")
        self.ironic_switch.grid(row=7, column=0, padx=20, pady=(5, 15), sticky="w")
        self.startup_switch = ctk.CTkSwitch(self, text="Автозапуск при старте Windows", command=self.toggle_startup)
        self.startup_switch.grid(row=8, column=0, padx=20, pady=(5, 20), sticky="w")
        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=9, column=0, padx=20, pady=(10, 20), sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        self.btn_save = ctk.CTkButton(btn_frame, text="💾 Сохранить", fg_color=self.parent.color_success, command=self.save_settings)
        self.btn_save.grid(row=0, column=0, padx=(0, 10), pady=10, sticky="ew")
        self.btn_cancel = ctk.CTkButton(btn_frame, text="❌ Отмена", fg_color="gray", command=self.destroy)
        self.btn_cancel.grid(row=0, column=1, padx=(10, 0), pady=10, sticky="ew")
    
    def load_settings(self):
        self.wake_word_entry.insert(0, self.parent.config_data["assistant"].get("wake_word", "джарвис"))
        self.user_name_entry.insert(0, self.parent.config_data["assistant"].get("user_name", "сэр"))
        self.ironic_switch.select() if self.parent.config_data["assistant"].get("ironic_mode", True) else self.ironic_switch.deselect()
        self.voice_profile.set(self.parent.config_data["assistant"].get("voice_profile", "default"))
        startup_folder = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
        shortcut_path = os.path.join(startup_folder, "AboltusAssistant.lnk")
        self.startup_switch.select() if os.path.exists(shortcut_path) else self.startup_switch.deselect()
    
    def toggle_startup(self):
        if self.startup_switch.get():
            add_to_startup()
        else:
            remove_from_startup()
    
    def save_settings(self):
        new_wake_word = self.wake_word_entry.get().strip().lower()
        if new_wake_word:
            self.parent.config_data["assistant"]["wake_word"] = new_wake_word
        self.parent.config_data["assistant"]["user_name"] = self.user_name_entry.get().strip() or "сэр"
        self.parent.config_data["assistant"]["ironic_mode"] = self.ironic_switch.get()
        self.parent.config_data["assistant"]["voice_profile"] = self.voice_profile.get()
        self.parent.save_config()
        self.parent.log_message("SYSTEM", f"Настройки сохранены. Wake word: '{self.parent.config_data['assistant']['wake_word']}', Голос: {self.voice_profile.get()}")
        self.parent.update_wake_word(self.parent.config_data['assistant']['wake_word'])
        self.parent.update_voice_profile(self.parent.config_data['assistant']['voice_profile'])
        self.destroy()

class AboltusAssistantApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Аболтус: ИИ-Помощник")
        self.geometry("1100x720")
        self.minsize(1000, 650)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.color_bg = "#0a0e17"
        self.color_panel = "#101622"
        self.color_cyan = "#00f2fe"
        self.color_purple = "#7928ca"
        self.color_text = "#94a3b8"
        self.color_success = "#10b981"
        self.color_alert = "#ef4444"
        self.init_logs = []
        self.chat_history = []
        self.reminders = []
        self.custom_macros = {}
        self.avatar_visible = False
        self.overlay_process = None
        self.is_minimized = False
        self.speech_enabled = True
        self.current_wake_word = "джарвис"
        self.current_voice_profile = "default"
        self.max_log_lines = 200
        self.ai = OllamaAI()
        self.load_config()
        self.current_wake_word = self.config_data["assistant"].get("wake_word", "джарвис")
        self.current_voice_profile = self.config_data["assistant"].get("voice_profile", "default")
        self.load_custom_macros()
        self.assistant_state = "sleep"
        self.session_active = False
        self.orb_angle = 0
        self.is_listening = False
        self.last_interaction_time = 0
        self.dialogue_timeout = 30
        self.configure(fg_color=self.color_bg)
        self.available_mics = self.get_microphone_list()
        self.create_widgets()
        self.animate_orb()
        if HAS_PYGAME:
            pygame.mixer.init()
        threading.Thread(target=self.start_websocket_server, daemon=True).start()
        if not HAS_WEBVIEW:
            self.log_message("SYSTEM", "pywebview не установлен", is_error=True)
        self.start_background_listening()
        self.protocol('WM_DELETE_WINDOW', self.minimize_to_tray)
        self.after(2000, self.say_hello)
        self.after(60000, self.periodic_memory_cleanup)
        self.check_reminders()
        if HAS_TELEGRAM:
            threading.Thread(target=self.start_telegram_bot, daemon=True).start()

    def get_voice_profile(self):
        return VOICE_PROFILES.get(self.current_voice_profile, VOICE_PROFILES["default"])

    def speak(self, text):
        """Озвучивание текста (через TTS или звуковые файлы)"""
        if not self.speech_enabled:
            return
        profile = self.get_voice_profile()
        if profile.get("use_tts", True):
            self._speak_tts(text)
        else:
            self._speak_with_audio_files(text, profile.get("path"))
    
    def _speak_with_audio_files(self, text: str, profile_path: str):
        """Воспроизводит звуковые файлы для клонированных голосов"""
        if not profile_path:
            self._speak_tts(text)
            return
        
        # Ищем звуковой файл по фразе
        audio_file = find_audio_file(profile_path, text)
        
        # Если не нашли, пробуем "команда выполнена"
        if not audio_file:
            audio_file = find_audio_file(profile_path, "команда выполнена")
        
        if audio_file and os.path.exists(audio_file):
            threading.Thread(target=play_sound_file, args=(audio_file,), daemon=True).start()
            self.log_message("SOUND", f"Воспроизведён файл: {os.path.basename(audio_file)}")
        else:
            self.log_message("SYSTEM", f"Звуковой файл не найден для: {text[:50]}, использую TTS")
            self._speak_tts(text)
    
    def _speak_tts(self, text: str):
        """Озвучивание через TTS (для стандартных голосов)"""
        def tts_task():
            if not HAS_EDGE_TTS:
                self.set_assistant_state("speaking")
                time.sleep(min(len(text) * 0.03, 5))
                self.after(0, lambda: self.set_assistant_state("listen" if self.session_active else "sleep"))
                return
            try:
                temp_dir = os.path.dirname(os.path.abspath(__file__))
                output_file = os.path.join(temp_dir, "tts_temp.mp3")
                voice = "ru-RU-SvetlanaNeural"
                async def gen():
                    communicate = edge_tts.Communicate(text, voice)
                    await communicate.save(output_file)
                asyncio.run(gen())
                if os.path.exists(output_file):
                    if not HAS_PYGAME:
                        import pygame
                    pygame.mixer.init()
                    pygame.mixer.music.load(output_file)
                    pygame.mixer.music.set_volume(0.8)
                    self.after(0, lambda: self.set_assistant_state("speaking"))
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.02)
                    pygame.mixer.music.unload()
                    try:
                        os.remove(output_file)
                    except:
                        pass
            except Exception as e:
                self.log_message("TTS", f"Ошибка: {e}", is_error=True)
                time.sleep(min(len(text) * 0.03, 5))
            self.after(0, lambda: self.set_assistant_state("listen" if self.session_active else "sleep"))
            gc.collect()
        threading.Thread(target=tts_task, daemon=True).start()

    def update_wake_word(self, new_wake_word):
        self.current_wake_word = new_wake_word
        if not self.session_active:
            self.session_label.configure(text=f"⚠️ Скажите '{self.current_wake_word}'", text_color=self.color_alert)
        self.log_message("SYSTEM", f"Wake word обновлён: '{self.current_wake_word}'")
    
    def update_voice_profile(self, profile_name):
        self.current_voice_profile = profile_name
        self.log_message("SYSTEM", f"Голосовой профиль изменён: {VOICE_PROFILES.get(profile_name, {}).get('name', profile_name)}")

    def periodic_memory_cleanup(self):
        gc.collect()
        check_memory_usage()
        if hasattr(self, 'log_box') and self.log_box:
            try:
                if int(self.log_box.index('end-1c').split('.')[0]) > self.max_log_lines:
                    self.log_box.delete('1.0', f'{self.max_log_lines - 50}.0')
            except:
                pass
        self.after(60000, self.periodic_memory_cleanup)

    def check_reminders(self):
        now = datetime.now()
        expired = []
        for i, reminder in enumerate(self.reminders):
            if reminder.get("time") <= now:
                self.speak(f"Напоминаю: {reminder['text']}")
                expired.append(i)
        for i in reversed(expired):
            self.reminders.pop(i)
        self.after(1000, self.check_reminders)

    def load_custom_macros(self):
        macros_file = os.path.join(BASE_DIR, "macros.json")
        if os.path.exists(macros_file):
            try:
                with open(macros_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        for trigger, actions in data.items():
                            if isinstance(actions, dict) and "actions" in actions:
                                self.custom_macros[trigger] = actions
                            elif isinstance(actions, dict) and "type" in actions:
                                self.custom_macros[trigger] = {"actions": [{"type": actions["type"], "value": actions["value"]}]}
                            else:
                                self.custom_macros[trigger] = {"actions": [{"type": "open_url", "value": str(actions)}]}
                self.log_message("SYSTEM", f"Загружено {len(self.custom_macros)} макросов")
            except Exception as e:
                self.log_message("SYSTEM", f"Ошибка загрузки: {e}", is_error=True)

    def save_custom_macros(self):
        try:
            with open(os.path.join(BASE_DIR, "macros.json"), "w", encoding="utf-8") as f:
                json.dump(self.custom_macros, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.log_message("SYSTEM", f"Ошибка сохранения: {e}", is_error=True)
            return False

    def open_macro_editor(self):
        MacroDialog(self)
    
    def open_settings(self):
        SettingsDialog(self)
    
    def execute_custom_macro(self, trigger: str) -> Optional[str]:
        if trigger in self.custom_macros:
            macro = self.custom_macros[trigger]
            actions = macro.get("actions", [])
            if not actions:
                return None
            results = []
            for action in actions:
                atype = action["type"]
                avalue = action["value"]
                if atype == "open_url":
                    webbrowser.open(avalue)
                    results.append("открываю ссылку")
                elif atype == "open_app":
                    try:
                        os.startfile(avalue)
                    except:
                        subprocess.Popen(avalue)
                    results.append("запускаю приложение")
                elif atype == "run_command":
                    os.system(avalue)
                    results.append("выполняю команду")
                elif atype == "type_text":
                    set_clipboard_text(avalue)
                    threading.Thread(target=simulate_ctrl_v, daemon=True).start()
                    results.append("вставляю текст")
            if results:
                return ", ".join(results)
            return "действия выполнены"
        return None

    def show_help(self):
        help_text = """📋 СПИСОК КОМАНД:

🌐 ИНТЕРНЕТ: открой браузер, открой ютуб, открой телеграм
🕒 ВРЕМЯ: который час, какое сегодня число
💻 СИСТЕМА: информация о системе, заблокируй экран, батарея, мой айпи
🔊 ЗВУК: максимальная/средняя/минимальная громкость, сделай громче/тише, громкость на X процентов
📁 ФАЙЛЫ: открой проводник, загрузки, документы, очисти корзину
🛠️ ПРОГРАММЫ: открой настройки, диспетчер задач, калькулятор
🎮 РАЗВЛЕЧЕНИЯ: расскажи шутку, сделай скриншот, кликни мышкой
🪟 ОКНА: сверни окно, сверни все окна, на весь экран, сверни видео, вернись/назад/бэк
🌤️ ПОГОДА: какая погода, погода сегодня
📥 СКАЧИВАНИЕ: скачай видео с ютуб (скачает текущее видео)
🎬 ЮТУБ: открой [название] видео, листай ниже/вверх/вниз
🎭 АВАТАР: покажи аватара / убери аватара
🔤 ПЕРЕВОД: переведи текст (выдели текст мышкой)
📡 ИНТЕРНЕТ: скорость интернета
⏰ НАПОМИНАНИЯ: напомни мне ... через X секунд/минут/часов
🪟 ТРЕЙ: трей / разверни / сверни
🔇 ГОЛОС: не отвечай / отвечай"""
        self.log_message("HELP", help_text)
        self.speak("Открыл список команд в консоли")

    def say_hello(self):
        hello_text = "Аболтус готов. Скажи мое имя для активации."
        self.log_message("AI", hello_text)
        self.speak(hello_text)

    def deep_merge(self, default, loaded):
        if not isinstance(loaded, dict):
            return default
        result = default.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def load_config(self):
        config_path = os.path.join(BASE_DIR, "config.yaml")
        default_config = {
            "assistant": {"wake_word": "джарвис", "ironic_mode": True, "user_name": "сэр", "voice_profile": "default"},
            "telegram": {"token": "", "password": "", "authorized_user_id": 0},
            "stt": {"sensitivity": 35, "mic_index": None},
            "tts": {"volume": 80}
        }
        self.config_data = default_config
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    loaded_data = yaml.safe_load(f) if HAS_YAML else json.load(f)
                    if isinstance(loaded_data, dict):
                        self.config_data = self.deep_merge(default_config, loaded_data)
                self.log_message("SYSTEM", "Конфигурация загружена")
            except Exception as e:
                self.log_message("SYSTEM", f"Ошибка чтения: {e}", is_error=True)
        else:
            self.save_config()

        # Синхронизация настроек Telegram из config.yaml
        global TELEGRAM_TOKEN, PASSWORD, AUTHORIZED_USER_ID
        tg_conf = self.config_data.get("telegram", {})
        if not TELEGRAM_TOKEN and tg_conf.get("token"):
            TELEGRAM_TOKEN = str(tg_conf.get("token", "")).strip()
        if not PASSWORD and tg_conf.get("password"):
            PASSWORD = str(tg_conf.get("password", "")).strip()
        if not AUTHORIZED_USER_ID and tg_conf.get("authorized_user_id"):
            try:
                AUTHORIZED_USER_ID = int(tg_conf.get("authorized_user_id", 0))
            except (ValueError, TypeError):
                AUTHORIZED_USER_ID = 0

    def save_config(self):
        try:
            config_path = os.path.join(BASE_DIR, "config.yaml")
            with open(config_path, "w", encoding="utf-8") as f:
                if HAS_YAML:
                    yaml.dump(self.config_data, f, default_flow_style=False, allow_unicode=True)
                else:
                    json.dump(self.config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log_message("SYSTEM", f"Ошибка сохранения: {e}", is_error=True)

    def get_microphone_list(self):
        mics = {"[Симуляция] Микрофон": None}
        if HAS_SOUNDDEVICE:
            try:
                devices = sd.query_devices()
                mics.clear()
                for i, dev in enumerate(devices):
                    if dev.get('max_input_channels', 0) > 0:
                        name = dev.get('name', f"Микрофон {i}")
                        mics[f"{i}: {name[:35]}"] = i
                if not mics:
                    mics = {"Нет микрофонов": None}
            except Exception as e:
                mics = {f"Ошибка: {e}": None}
        return mics

    def start_websocket_server(self):
        try:
            import websockets
            async def handler(websocket):
                WS_CLIENTS.add(websocket)
                try:
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                        except:
                            pass
                except websockets.exceptions.ConnectionClosed:
                    pass
                finally:
                    if websocket in WS_CLIENTS:
                        WS_CLIENTS.remove(websocket)
            async def start():
                async with websockets.serve(handler, "localhost", 8765):
                    await asyncio.Future()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(start())
        except Exception as e:
            print(f"[WS ERROR] {e}")

    def broadcast_to_avatar(self, data_dict):
        if not WS_CLIENTS:
            return
        payload = json.dumps(data_dict)
        async def send_all():
            for ws in list(WS_CLIENTS):
                try:
                    await ws.send(payload)
                except:
                    pass
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(send_all())
        except:
            pass

    def launch_transparent_avatar(self):
        if self.avatar_visible:
            return
        html_path = os.path.join(BASE_DIR, "www", "index.html")
        if not os.path.exists(html_path):
            self.log_message("SYSTEM", "www/index.html не найден", is_error=True)
            return
        self.log_message("SYSTEM", "Запуск оверлея...")
        self.overlay_process = multiprocessing.Process(target=run_overlay_process, args=(html_path,), daemon=True)
        self.overlay_process.start()
        self.avatar_visible = True

    def close_transparent_avatar(self):
        if self.overlay_process:
            self.overlay_process.terminate()
            self.overlay_process = None
        self.avatar_visible = False
        self.log_message("SYSTEM", "Оверлей закрыт")

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar = ctk.CTkFrame(self, fg_color=self.color_panel, corner_radius=16)
        self.sidebar.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="nsew")
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.logo_label = ctk.CTkLabel(self.sidebar, text="АБОЛТУС", font=("Courier New", 28, "bold"), text_color=self.color_cyan)
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 5))
        self.sublogo_label = ctk.CTkLabel(self.sidebar, text="AI ASSISTANT", font=("Arial", 11, "bold"), text_color=self.color_purple)
        self.sublogo_label.grid(row=1, column=0, padx=20, pady=(0, 25))
        self.scroll_settings = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.scroll_settings.grid(row=2, column=0, padx=15, pady=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(2, weight=1)
        self.scroll_settings.grid_columnconfigure(0, weight=1)
        self.btn_settings = ctk.CTkButton(self.scroll_settings, text="⚙️ НАСТРОЙКИ", fg_color=self.color_purple, command=self.open_settings)
        self.btn_settings.grid(row=0, column=0, padx=10, pady=(10, 15), sticky="ew")
        self.lbl_mic = ctk.CTkLabel(self.scroll_settings, text="Микрофон:", font=("Arial", 13, "bold"))
        self.lbl_mic.grid(row=1, column=0, padx=10, pady=(12, 2), sticky="w")
        mic_names = list(self.available_mics.keys())
        self.opt_mic = ctk.CTkOptionMenu(self.scroll_settings, values=mic_names, command=self.change_mic)
        self.opt_mic.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        if mic_names:
            self.opt_mic.set(mic_names[0])
        self.lbl_sens = ctk.CTkLabel(self.scroll_settings, text="Чувствительность:", font=("Arial", 13, "bold"))
        self.lbl_sens.grid(row=3, column=0, padx=10, pady=(15, 2), sticky="w")
        self.slider_sens = ctk.CTkSlider(self.scroll_settings, from_=10, to=100)
        self.slider_sens.grid(row=4, column=0, padx=10, pady=(0, 15), sticky="ew")
        self.slider_sens.set(35)
        self.lbl_macros = ctk.CTkLabel(self.scroll_settings, text="Макросы (комбо):", font=("Arial", 13, "bold"))
        self.lbl_macros.grid(row=5, column=0, padx=10, pady=(15, 5), sticky="w")
        self.btn_macro_editor = ctk.CTkButton(self.scroll_settings, text="📝 Редактор макросов", fg_color=self.color_purple, command=self.open_macro_editor)
        self.btn_macro_editor.grid(row=6, column=0, padx=10, pady=(0, 15), sticky="ew")
        self.btn_tray = ctk.CTkButton(self.scroll_settings, text="🪟 СВЕРНУТЬ В ТРЕЙ", fg_color=self.color_purple, command=self.minimize_to_tray)
        self.btn_tray.grid(row=7, column=0, padx=10, pady=(0, 15), sticky="ew")
        self.btn_help = ctk.CTkButton(self.scroll_settings, text="❓ ПОМОЩЬ", fg_color=self.color_cyan, text_color="#0a0e17", command=self.show_help)
        self.btn_help.grid(row=8, column=0, padx=10, pady=(0, 15), sticky="ew")
        self.btn_save_config = ctk.CTkButton(self.sidebar, text="СОХРАНИТЬ", fg_color=self.color_purple, command=self.apply_manual_config)
        self.btn_save_config.grid(row=3, column=0, padx=20, pady=(10, 25), sticky="ew")
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="nsew")
        self.main_area.grid_columnconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(1, weight=1)
        self.status_panel = ctk.CTkFrame(self.main_area, fg_color=self.color_panel, corner_radius=16)
        self.status_panel.grid(row=0, column=0, padx=0, pady=(0, 10), sticky="nsew")
        self.status_panel.grid_columnconfigure(0, weight=1)
        self.orb_canvas = ctk.CTkCanvas(self.status_panel, width=220, height=220, bg=self.color_panel, highlightthickness=0)
        self.orb_canvas.grid(row=0, column=0, pady=(10, 0))
        self.state_label = ctk.CTkLabel(self.status_panel, text="РЕЖИМ ОЖИДАНИЯ", font=("Courier New", 16, "bold"), text_color=self.color_text)
        self.state_label.grid(row=1, column=0, pady=(5, 5))
        self.session_label = ctk.CTkLabel(self.status_panel, text=f"⚠️ Скажите '{self.current_wake_word}'", font=("Arial", 12, "bold"), text_color=self.color_alert)
        self.session_label.grid(row=2, column=0, pady=(0, 5))
        self.volume_bar = ctk.CTkProgressBar(self.status_panel, width=250, height=8, progress_color=self.color_cyan)
        self.volume_bar.grid(row=3, column=0, pady=(5, 5))
        self.volume_bar.set(get_current_volume() / 100)
        self.live_text_label = ctk.CTkLabel(self.status_panel, text="[Ожидание...]", font=("Arial", 13, "italic"))
        self.live_text_label.grid(row=4, column=0, pady=(5, 15))
        self.console_panel = ctk.CTkFrame(self.main_area, fg_color=self.color_panel, corner_radius=16)
        self.console_panel.grid(row=1, column=0, padx=0, pady=(10, 0), sticky="nsew")
        self.console_panel.grid_columnconfigure(0, weight=1)
        self.console_panel.grid_rowconfigure(0, weight=1)
        self.log_box = ctk.CTkTextbox(self.console_panel, fg_color="#06090f", text_color="#cbd5e1", font=("Consolas", 11))
        self.log_box.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        self.input_frame = ctk.CTkFrame(self.console_panel, fg_color="transparent")
        self.input_frame.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        self.entry_cmd = ctk.CTkEntry(self.input_frame, placeholder_text="Введите команду...")
        self.entry_cmd.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.entry_cmd.bind("<Return>", lambda event: self.send_text_command())
        self.btn_send = ctk.CTkButton(self.input_frame, text="ЗАПУСК", width=100, fg_color=self.color_cyan, command=self.send_text_command)
        self.btn_send.grid(row=0, column=1)
        self.log_message("SYSTEM", "Интерфейс загружен")

    def change_mic(self, selection):
        idx = self.available_mics.get(selection)
        self.config_data["stt"]["mic_index"] = idx
        self.save_config()
        self.is_listening = False
        time.sleep(0.5)
        self.start_background_listening()

    def update_live_text(self, text, is_final=False):
        if is_final:
            self.live_text_label.configure(text=f"Распознано: «{text[:50]}»", text_color=self.color_success)
        else:
            self.live_text_label.configure(text=f"Слышу: {text[:50]}", text_color=self.color_cyan)

    def apply_manual_config(self):
        self.save_config()
        self.log_message("SYSTEM", "Настройки сохранены")
        self.volume_bar.set(get_current_volume() / 100)

    def log_message(self, sender, text, is_error=False):
        timestamp = time.strftime("%H:%M:%S")
        prefix = f"[{timestamp}] [{sender}]"
        if is_error:
            msg = f"{prefix} ❌ {text}\n"
        elif sender == "SYSTEM":
            msg = f"{prefix} ⚙️ {text}\n"
        elif sender == "AI":
            msg = f"{prefix} 🧠 {text}\n"
        else:
            msg = f"{prefix} {text}\n"
        if hasattr(self, "log_box") and self.log_box:
            try:
                self.after(0, lambda: self._safe_log_insert(msg))
            except:
                pass
        else:
            self.init_logs.append(msg)

    def _safe_log_insert(self, msg):
        try:
            self.log_box.insert("end", msg)
            self.log_box.see("end")
        except:
            pass

    def set_assistant_state(self, state):
        self.assistant_state = state
        self.broadcast_to_avatar({"action": "state_change", "state": state})
        states = {
            "sleep": ("РЕЖИМ ОЖИДАНИЯ", self.color_text),
            "listen": ("АКТИВЕН", self.color_cyan),
            "thinking": ("ДУМАЮ", self.color_purple),
            "speaking": ("ОТВЕЧАЮ", self.color_success)
        }
        if state in states:
            text, color = states[state]
            self.state_label.configure(text=text, text_color=color)

    def set_session_active(self, active: bool):
        self.session_active = active
        if active:
            self.set_assistant_state("listen")
            self.last_interaction_time = time.time()
            self.session_label.configure(text="✅ АКТИВНА", text_color=self.color_success)
        else:
            self.set_assistant_state("sleep")
            self.session_label.configure(text=f"⚠️ Скажите '{self.current_wake_word}'", text_color=self.color_alert)

    def animate_orb(self):
        canvas = self.orb_canvas
        canvas.delete("all")
        cx, cy = 110, 110
        self.orb_angle += 0.05
        if self.assistant_state == "sleep":
            pulse_mod = math.sin(self.orb_angle * 0.5) * 6
            base_radius = 65
        elif self.assistant_state == "listen":
            pulse_mod = math.sin(self.orb_angle * 2.0) * 15
            base_radius = 70
        elif self.assistant_state == "thinking":
            pulse_mod = math.sin(self.orb_angle * 1.2) * 4
            base_radius = 65
        elif self.assistant_state == "speaking":
            pulse_mod = abs(math.sin(self.orb_angle * 3.0)) * 20
            base_radius = 60
        else:
            pulse_mod = 0
            base_radius = 65
        r1 = base_radius + pulse_mod
        r2 = base_radius - pulse_mod * 0.5
        canvas.create_oval(cx - r1, cy - r1, cx + r1, cy + r1, outline=self.color_cyan, width=2)
        canvas.create_oval(cx - r2, cy - r2, cx + r2, cy + r2, fill="#111824", outline=self.color_cyan, width=1)
        self.after(20, self.animate_orb)

    def start_background_listening(self):
        self.is_listening = True
        threading.Thread(target=self.voice_listening_loop, daemon=True).start()

    def voice_listening_loop(self):
        if not HAS_SOUNDDEVICE:
            return
        recognizer = None
        if HAS_VOSK:
            try:
                model = Model(lang="ru")
                recognizer = KaldiRecognizer(model, 16000)
                self.log_message("STT", "Модель загружена")
            except Exception as e:
                self.log_message("STT", f"Ошибка: {e}", is_error=True)
        import queue
        audio_q = queue.Queue()
        def callback(indata, frames, time, status):
            audio_q.put(indata.copy())
        mic_index = self.config_data.get("stt", {}).get("mic_index", None)
        wake_word = self.current_wake_word.lower()
        try:
            stream = sd.InputStream(samplerate=16000, channels=1, dtype='int16', device=mic_index, callback=callback)
            with stream:
                self.log_message("SYSTEM", "Микрофон активен")
                while self.is_listening:
                    try:
                        data = audio_q.get(timeout=0.2)
                    except queue.Empty:
                        continue
                    if self.session_active and (time.time() - self.last_interaction_time > self.dialogue_timeout):
                        self.after(0, lambda: self.set_session_active(False))
                    if recognizer and recognizer.AcceptWaveform(data.tobytes()):
                        res = json.loads(recognizer.Result())
                        text = res.get("text", "").strip()
                        if text:
                            self.after(0, self.update_live_text, text, True)
                            lower_text = text.lower()
                            if any(word in lower_text for word in ["спи", "отбой", "выключись"]):
                                self.after(0, lambda: self.set_session_active(False))
                                self.after(0, self.speak, "Хорошо")
                                continue
                            if wake_word in lower_text:
                                if not self.session_active:
                                    self.after(0, lambda: self.set_session_active(True))
                                    self.after(0, self.speak, "Слушаю")
                                continue
                            if self.session_active:
                                self.last_interaction_time = time.time()
                                threading.Thread(target=self.process_command, args=(text,), daemon=True).start()
        except Exception as e:
            self.log_message("SYSTEM", f"Ошибка: {e}", is_error=True)

    def send_text_command(self):
        if not self.session_active:
            self.speak(f"Скажи '{self.current_wake_word}' для активации")
            return
        cmd_text = self.entry_cmd.get().strip()
        if not cmd_text:
            return
        self.entry_cmd.delete(0, "end")
        self.last_interaction_time = time.time()
        threading.Thread(target=self.process_command, args=(cmd_text,), daemon=True).start()

    def process_command(self, raw_command: str):
        command = raw_command.lower().strip()
        if not command:
            return
        self.set_assistant_state("thinking")
        response_text = ""
        action_executed = False
        is_code_command = False
        if command in ["помощь", "что ты умеешь", "команды"]:
            self.show_help()
            self.set_assistant_state("listen")
            return
        if command == "не отвечай":
            self.speech_enabled = False
            response_text = "голосовые ответы отключены"
            action_executed = True
        elif command == "отвечай":
            self.speech_enabled = True
            response_text = "голосовые ответы включены"
            action_executed = True
        elif any(word in command for word in ["трей", "т рей", "сверни программу", "в трей"]):
            self.minimize_to_tray()
            response_text = "программа свёрнута в трей"
            action_executed = True
        elif any(word in command for word in ["разверни", "открой программу", "покажи окно"]):
            self.restore_from_tray()
            response_text = "окно восстановлено"
            action_executed = True
        elif command in ["привет", "здарова", "дароу", "здароу"]:
            greeting = BuiltinCommands.greet(self.config_data["assistant"].get("user_name", "сэр"))
            response_text = greeting
            action_executed = True
        elif any(word in command for word in ["покажи аватара", "открой аватар", "покажи персонажа", "открой модель", "аватар"]):
            self.launch_transparent_avatar()
            response_text = "открываю 3D аватар"
            action_executed = True
        elif any(word in command for word in ["убери аватара", "закрой аватара", "убери персонажа", "закрой персонажа", "закрой модель", "убери модель"]):
            self.close_transparent_avatar()
            response_text = "закрываю 3D аватар"
            action_executed = True
        elif any(word in command for word in ["листай ниже", "гортай ниже", "вниз", "ниже", "свайп вниз"]):
            scroll_down()
            response_text = "пролистал страницу вниз"
            action_executed = True
        elif any(word in command for word in ["листай выше", "гортай выше", "вверх", "выше", "свайп вверх"]):
            scroll_up()
            response_text = "пролистал страницу вверх"
            action_executed = True
        elif any(word in command for word in ["вернись", "назад", "бэк", "бек", "обратно"]):
            go_back()
            response_text = "вернулся на предыдущую страницу"
            action_executed = True
        elif any(word in command for word in ["вперед", "вперёд", "дальше"]):
            go_forward()
            response_text = "перешёл на следующую страницу"
            action_executed = True
        elif command.startswith("открой ") and (" видео" in command or "ютуб" in command):
            query = raw_command.replace("открой", "").replace("видео", "").replace("ютуб", "").strip()
            if query:
                result = search_and_open_youtube_video(query)
                response_text = result
                action_executed = True
        elif command.startswith("напомни мне"):
            reminder_match = re.search(r'напомни мне (.+?)(?: через|$)', raw_command)
            if reminder_match:
                reminder_text = reminder_match.group(1).strip()
                delay = parse_reminder_time(raw_command)
                if delay is None:
                    delay = 600
                    time_str = "10 минут"
                else:
                    if delay < 60:
                        time_str = f"{delay} секунд"
                    elif delay < 3600:
                        time_str = f"{delay // 60} минут"
                    else:
                        time_str = f"{delay // 3600} часов"
                reminder_time = datetime.now() + timedelta(seconds=delay)
                self.reminders.append({"text": reminder_text, "time": reminder_time})
                response_text = f"Напомню '{reminder_text}' через {time_str}"
            else:
                response_text = "Скажи: напомни мне текст через X минут/секунд/часов"
            action_executed = True
        elif "хватит напоминать" in command or "удали напоминания" in command:
            self.reminders.clear()
            response_text = "Напоминания удалены"
            action_executed = True
        if not action_executed:
            macro_result = self.execute_custom_macro(command)
            if macro_result:
                response_text = macro_result
                action_executed = True
        if not action_executed and command.startswith("напиши код"):
            code_prompt = raw_command[10:].strip()
            if code_prompt:
                result = self.ai.ask(f"Код для: {code_prompt}", False)
                if set_clipboard_text(result):
                    response_text = "Код скопирован в буфер"
                    is_code_command = True
            else:
                response_text = "Что написать?"
            action_executed = True
        elif not action_executed and ("скачай видео с ютуб" in command or "скачай это видео" in command or "сохрани видео" in command):
            result = download_current_youtube_video()
            response_text = result
            action_executed = True
        elif not action_executed and ("кто такой" in command or "кто такая" in command):
            query = raw_command.split("такой")[-1].strip() or raw_command.split("такая")[-1].strip()
            result = fetch_wikipedia(query) if query else "Кого?"
            response_text = result
            action_executed = True
        elif not action_executed and "что такое" in command:
            query = raw_command.replace("что такое", "").strip()
            result = fetch_wikipedia(query) if query else "Что?"
            response_text = result
            action_executed = True
        elif not action_executed and "новости" in command:
            news_list = fetch_news()
            if isinstance(news_list, list) and news_list:
                result = news_list[0] if news_list else "Новостей нет"
            else:
                result = "Новости недоступны"
            response_text = result
            action_executed = True
        elif not action_executed and "курс" in command:
            currency = "доллар"
            if "евро" in command:
                currency = "евро"
            elif "юань" in command:
                currency = "юань"
            result = fetch_currency_rate(currency)
            response_text = result
            action_executed = True
        elif not action_executed and re.search(r'громкость на (\d+)', command):
            match = re.search(r'громкость на (\d+)', command)
            percent = int(match.group(1))
            percent = max(0, min(100, percent))
            result = volume_set(percent)
            self.volume_bar.set(percent / 100)
            response_text = result
            action_executed = True
        elif not action_executed and ("громкость на максимум" in command or "максимальная громкость" in command or "сделай громко" in command):
            result = volume_max()
            self.volume_bar.set(1.0)
            response_text = result
            action_executed = True
        elif not action_executed and ("громкость на минимум" in command or "минимальная громкость" in command or "сделай тихо" in command):
            result = volume_min()
            self.volume_bar.set(0.05)
            response_text = result
            action_executed = True
        elif not action_executed:
            num = extract_number_from_text(command)
            if num is not None and ("громкость" in command or "звук" in command):
                percent = max(0, min(100, num))
                result = volume_set(percent)
                self.volume_bar.set(percent / 100)
                response_text = result
                action_executed = True
        if not action_executed:
            commands_dict = {
                "open_browser": ["открой браузер", "запусти браузер", "включи браузер"],
                "open_youtube": ["открой ютуб", "включи ютуб", "ютуб", "youtube"],
                "open_google": ["открой гугл", "гугл", "google", "хром"],
                "say_time": ["который час", "скажи время", "время"],
                "say_date": ["какое сегодня число", "какая сегодня дата", "дата"],
                "lock_computer": ["заблокируй экран", "заблокируй компьютер", "блокировка"],
                "system_info": ["информация о системе", "характеристики компьютера"],
                "cancel_shutdown": ["отмени выключение", "не выключай"],
                "volume_mid": ["средняя громкость", "половина громкости"],
                "mute": ["выключи звук", "без звука", "mute", "мут"],
                "unmute": ["включи звук", "верни звук"],
                "tell_joke": ["расскажи шутку", "пошути", "анекдот", "шутка"],
                "open_explorer": ["открой проводник", "проводник"],
                "open_downloads": ["открой загрузки", "загрузки"],
                "open_documents": ["открой документы", "документы"],
                "open_desktop": ["открой рабочий стол", "рабочий стол"],
                "open_pictures": ["открой изображения", "картинки"],
                "open_music": ["открой папку музыка", "музыка"],
                "open_videos": ["открой видео", "видео"],
                "open_settings": ["открой настройки", "настройки"],
                "open_control_panel": ["панель управления"],
                "open_task_manager": ["диспетчер задач"],
                "open_cmd": ["командная строка", "cmd", "консоль"],
                "open_notepad": ["блокнот", "notepad"],
                "open_calculator": ["калькулятор", "calc"],
                "take_screenshot": ["скриншот", "сделай скриншот", "скрин"],
                "click_mouse": ["кликни мышкой", "кликни", "левый клик"],
                "right_click": ["правую кнопку", "правый клик"],
                "close_browser_window": ["закрой браузер", "закрыть браузер"],
                "minimize_active_window": ["сверни браузер", "сверни окно"],
                "minimize_all": ["сверни все окна", "свернуть всё"],
                "incognito_mode": ["инкогнито", "режим инкогнито"],
                "open_telegram": ["открой телеграм", "телеграм"],
                "shutdown_pc": ["выключи компьютер", "выключи пк"],
                "restart_pc": ["перезагрузи компьютер", "перезагрузка"],
                "volume_up": ["сделай громче", "прибавь громкость", "громче"],
                "volume_down": ["сделай тише", "убавь громкость", "тише"],
                "empty_bin": ["очисти корзину", "почисти корзину"],
                "fullscreen": ["на весь экран", "полный экран"],
                "exit_fullscreen": ["сверни видео", "выйти из полноэкранного режима"],
                "get_ip": ["мой айпи", "айпи адрес", "мой ip"],
                "get_weather": ["какая погода", "погода сегодня", "погода"],
                "get_battery": ["батарея", "заряд батареи", "уровень заряда"],
                "get_speed": ["скорость интернета", "тест скорости"],
                "translate": ["переведи текст", "перевод"]
            }
            for cmd_name, phrases in commands_dict.items():
                for phrase in phrases:
                    if phrase in command:
                        try:
                            result = getattr(BuiltinCommands, cmd_name)()
                            response_text = result
                            action_executed = True
                            break
                        except Exception as e:
                            response_text = f"Ошибка: {e}"
                            action_executed = True
                        break
                if action_executed:
                    break
        if not action_executed:
            ai_response = self.ai.ask(raw_command, self.config_data["assistant"]["ironic_mode"])
            response_text = ai_response
        self.log_message("AI", response_text[:200])
        if self.speech_enabled:
            self.speak(response_text[:200])
        else:
            self.log_message("SYSTEM", "[РЕЧЬ ОТКЛЮЧЕНА]")
        if is_code_command:
            threading.Thread(target=simulate_ctrl_v, daemon=True).start()
        self.set_assistant_state("listen")
        gc.collect()

    def minimize_to_tray(self):
        if not pystray:
            self.withdraw()
            self.is_minimized = True
            return
        self.withdraw()
        self.is_minimized = True
        if not hasattr(self, 'tray_icon') or self.tray_icon is None:
            icon_image = Image.new("RGBA", (64, 64), (10, 22, 34, 255))
            draw = ImageDraw.Draw(icon_image)
            draw.ellipse((8, 8, 56, 56), outline=(0, 242, 254), width=4)
            draw.ellipse((20, 20, 44, 44), fill=(121, 40, 202))
            menu = pystray.Menu(
                pystray.MenuItem("Развернуть", self.restore_from_tray),
                pystray.MenuItem("Выход", self.exit_app)
            )
            self.tray_icon = pystray.Icon("AboltusAI", icon_image, "Аболтус", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def restore_from_tray(self):
        self.is_minimized = False
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.after(0, self.deiconify)
        self.after(100, lambda: self.lift())
        self.after(100, lambda: self.focus_force())

    def exit_app(self):
        self.is_listening = False
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.stop()
        if hasattr(self, 'overlay_process') and self.overlay_process:
            self.overlay_process.terminate()
        gc.collect()
        self.destroy()
        sys.exit(0)

    # === TELEGRAM БОТ ===
    def start_telegram_bot(self):
        if not HAS_TELEGRAM:
            return
        global app_instance, TELEGRAM_TOKEN, PASSWORD, AUTHORIZED_USER_ID
        app_instance = self

        tg_conf = self.config_data.get("telegram", {})
        token = TELEGRAM_TOKEN or str(tg_conf.get("token", "")).strip()
        if not token or token == "YOUR_TELEGRAM_BOT_TOKEN_HERE" or not token.strip():
            print("[TELEGRAM] Токен бота не указан в config.yaml. Бот отключен.")
            self.log_message("TELEGRAM", "Токен не указан в config.yaml. Бот отключен.")
            return

        pwd = PASSWORD or str(tg_conf.get("password", "")).strip()
        auth_id = AUTHORIZED_USER_ID or tg_conf.get("authorized_user_id", 0)
        try:
            auth_id = int(auth_id)
        except (ValueError, TypeError):
            auth_id = 0

        async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            if user_id == auth_id:
                context.user_data['authorized'] = True
                await update.message.reply_text("✅ Доступ разрешён. Вы можете управлять ассистентом.")
                await show_menu(update, context)
            else:
                context.user_data['awaiting_password'] = True
                await update.message.reply_text("🔐 Введите пароль для доступа к ассистенту:")
        async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if context.user_data.get('awaiting_password'):
                if update.message.text.strip() == pwd:
                    context.user_data['authorized'] = True
                    context.user_data['awaiting_password'] = False
                    await update.message.reply_text("✅ Пароль верный! Добро пожаловать.")
                    await show_menu(update, context)
                else:
                    await update.message.reply_text("❌ Неверный пароль. Доступ запрещён.")
                    context.user_data['awaiting_password'] = False
        async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not context.user_data.get('authorized'):
                await update.message.reply_text("❌ Доступ запрещён. Введите пароль.")
                return
            keyboard = [
                [InlineKeyboardButton("💻 Система", callback_data="system")],
                [InlineKeyboardButton("🎬 YouTube", callback_data="youtube")],
                [InlineKeyboardButton("🔊 Звук", callback_data="sound")],
                [InlineKeyboardButton("🌤️ Погода", callback_data="weather")],
                [InlineKeyboardButton("📁 Файлы", callback_data="files")],
                [InlineKeyboardButton("🎮 Развлечения", callback_data="fun")],
                [InlineKeyboardButton("📝 Помощь", callback_data="help")],
                [InlineKeyboardButton("🗣️ Голосовая команда", callback_data="voice")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("📱 Выберите действие:", reply_markup=reply_markup)
        async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            await query.answer()
            if not context.user_data.get('authorized'):
                await query.edit_message_text("❌ Доступ запрещён. Используйте /start для входа.")
                return
            command = query.data
            if command == "system":
                info = get_system_info()
                battery = get_battery_status()
                await query.edit_message_text(f"🖥️ СИСТЕМА:\n\n{info}\n\n{battery}")
            elif command == "youtube":
                keyboard = [
                    [InlineKeyboardButton("🔍 Поиск видео", callback_data="youtube_search")],
                    [InlineKeyboardButton("📥 Скачать текущее видео", callback_data="youtube_download")]
                ]
                await query.edit_message_text("🎬 YouTube команды:", reply_markup=InlineKeyboardMarkup(keyboard))
            elif command == "youtube_search":
                context.user_data['awaiting_youtube_search'] = True
                await query.edit_message_text("Введите название видео для поиска на YouTube:")
            elif command == "youtube_download":
                result = download_current_youtube_video()
                await query.edit_message_text(f"📥 {result}")
            elif command == "sound":
                keyboard = [
                    [InlineKeyboardButton("🔊 Максимум", callback_data="vol_max")],
                    [InlineKeyboardButton("🔉 Средняя", callback_data="vol_mid")],
                    [InlineKeyboardButton("🔇 Минимум", callback_data="vol_min")],
                    [InlineKeyboardButton("⬆️ Громче", callback_data="vol_up")],
                    [InlineKeyboardButton("⬇️ Тише", callback_data="vol_down")],
                    [InlineKeyboardButton("🔇 Выкл звук", callback_data="vol_mute")],
                    [InlineKeyboardButton("🔊 Вкл звук", callback_data="vol_unmute")]
                ]
                await query.edit_message_text("🔊 Управление звуком:", reply_markup=InlineKeyboardMarkup(keyboard))
            elif command == "vol_max":
                result = volume_max()
                await query.edit_message_text(f"🔊 {result}")
            elif command == "vol_mid":
                result = volume_set(50)
                await query.edit_message_text(f"🔉 {result}")
            elif command == "vol_min":
                result = volume_min()
                await query.edit_message_text(f"🔇 {result}")
            elif command == "vol_up":
                result = volume_up(10)
                await query.edit_message_text(f"⬆️ {result}")
            elif command == "vol_down":
                result = volume_down(10)
                await query.edit_message_text(f"⬇️ {result}")
            elif command == "vol_mute":
                result = volume_mute()
                await query.edit_message_text(f"🔇 {result}")
            elif command == "vol_unmute":
                result = volume_unmute()
                await query.edit_message_text(f"🔊 {result}")
            elif command == "weather":
                weather = get_weather()
                await query.edit_message_text(f"🌤️ {weather}")
            elif command == "files":
                keyboard = [
                    [InlineKeyboardButton("📁 Загрузки", callback_data="open_downloads")],
                    [InlineKeyboardButton("📄 Документы", callback_data="open_documents")],
                    [InlineKeyboardButton("🖼️ Изображения", callback_data="open_pictures")],
                    [InlineKeyboardButton("🎵 Музыка", callback_data="open_music")],
                    [InlineKeyboardButton("🗑️ Очистить корзину", callback_data="empty_bin")]
                ]
                await query.edit_message_text("📁 Файловые команды:", reply_markup=InlineKeyboardMarkup(keyboard))
            elif command == "open_downloads":
                open_folder(os.path.expanduser("~/Downloads"))
                await query.edit_message_text("📁 Открываю папку Загрузки")
            elif command == "open_documents":
                open_folder(os.path.expanduser("~/Documents"))
                await query.edit_message_text("📁 Открываю папку Документы")
            elif command == "open_pictures":
                open_folder(os.path.expanduser("~/Pictures"))
                await query.edit_message_text("📁 Открываю папку Изображения")
            elif command == "open_music":
                open_folder(os.path.expanduser("~/Music"))
                await query.edit_message_text("📁 Открываю папку Музыка")
            elif command == "empty_bin":
                result = empty_recycle_bin()
                await query.edit_message_text("🗑️ Корзина очищена" if result else "❌ Не удалось очистить корзину")
            elif command == "fun":
                joke = get_random_joke()
                await query.edit_message_text(f"🎭 {joke}")
            elif command == "help":
                await query.edit_message_text("""📋 ДОСТУПНЫЕ КОМАНДЫ:

💻 СИСТЕМА: информация, батарея, IP
🔊 ЗВУК: громкость, выкл/вкл звук
🎬 ЮТУБ: скачать видео, поиск
🌤️ ПОГОДА: текущая погода
📁 ФАЙЛЫ: открыть папки, очистить корзину
🎮 РАЗВЛЕЧЕНИЯ: шутка
🗣️ ГОЛОС: отправьте голосовое сообщение

Также можно отправлять текстовые команды!""")
            elif command == "voice":
                await query.edit_message_text("🎤 Отправьте голосовое сообщение, и я его распознаю и выполню команду.")
        async def youtube_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if context.user_data.get('awaiting_youtube_search'):
                query_text = update.message.text
                context.user_data['awaiting_youtube_search'] = False
                result = search_and_open_youtube_video(query_text)
                await update.message.reply_text(f"🎬 {result}")
        async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not context.user_data.get('authorized'):
                await update.message.reply_text("❌ Доступ запрещён.")
                return
            voice_file = await update.message.voice.get_file()
            ogg_path = f"voice_{update.effective_user.id}_{int(time.time())}.ogg"
            wav_path = ogg_path.replace('.ogg', '.wav')
            await voice_file.download_to_drive(ogg_path)
            try:
                try:
                    from pydub import AudioSegment
                    audio = AudioSegment.from_ogg(ogg_path)
                    audio.export(wav_path, format="wav")
                except ImportError:
                    subprocess.run(['ffmpeg', '-i', ogg_path, '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', wav_path], capture_output=True, check=False)
                import speech_recognition as sr
                r = sr.Recognizer()
                with sr.AudioFile(wav_path) as source:
                    audio = r.record(source)
                text = r.recognize_google(audio, language="ru-RU")
                await update.message.reply_text(f"🎤 Распознано: {text}")
                if app_instance:
                    response = app_instance.process_command_sync(text)
                    await update.message.reply_text(f"🤖 {response}")
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка распознавания: {e}")
            finally:
                try:
                    os.remove(ogg_path)
                except:
                    pass
                try:
                    os.remove(wav_path)
                except:
                    pass
        async def text_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not context.user_data.get('authorized'):
                await update.message.reply_text("❌ Доступ запрещён. Используйте /start для входа.")
                return
            text = update.message.text
            if text == "/menu":
                await show_menu(update, context)
                return
            if app_instance:
                response = app_instance.process_command_sync(text)
                await update.message.reply_text(f"🤖 {response}")
        async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            if user_id == auth_id:
                context.user_data['authorized'] = True
                await update.message.reply_text("✅ Добро пожаловать, хозяин! Я Аболтус. Отправьте /menu для управления.")
            else:
                context.user_data['awaiting_password'] = True
                await update.message.reply_text("🔐 Введите пароль для доступа к ассистенту:")
        try:
            app = Application.builder().token(token).build()
            app.add_handler(CommandHandler("start", start_command))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_command_handler))
            app.add_handler(MessageHandler(filters.VOICE, voice_handler))
            app.add_handler(CallbackQueryHandler(button_handler))
            print("[TELEGRAM] Бот успешно запущен")
            self.log_message("TELEGRAM", "Бот подключен и работает")
            app.run_polling(allowed_updates=["message", "callback_query"])
        except Exception as e:
            print(f"[TELEGRAM] Ошибка запуска бота: {e}")
            self.log_message("TELEGRAM", f"Ошибка запуска бота: {e}", is_error=True)
    
    def process_command_sync(self, command: str) -> str:
        cmd_lower = command.lower()
        if "время" in cmd_lower or "который час" in cmd_lower:
            return BuiltinCommands.say_time()
        if "дата" in cmd_lower or "число" in cmd_lower:
            return BuiltinCommands.say_date()
        if "информация" in cmd_lower or "система" in cmd_lower:
            return get_system_info()
        if "айпи" in cmd_lower or "ip" in cmd_lower:
            return get_public_ip()
        if "батарея" in cmd_lower or "заряд" in cmd_lower:
            return get_battery_status()
        if "погода" in cmd_lower:
            return get_weather()
        if "шутка" in cmd_lower or "анекдот" in cmd_lower:
            return get_random_joke()
        if "максимальная громкость" in cmd_lower or "максимум" in cmd_lower:
            return volume_max()
        if "минимальная громкость" in cmd_lower or "минимум" in cmd_lower:
            return volume_min()
        if "средняя громкость" in cmd_lower:
            return volume_set(50)
        if "громче" in cmd_lower:
            return volume_up(10)
        if "тише" in cmd_lower:
            return volume_down(10)
        if "выключи звук" in cmd_lower:
            return volume_mute()
        if "включи звук" in cmd_lower:
            return volume_unmute()
        num = extract_number_from_text(command)
        if num is not None and ("громкость" in cmd_lower or "звук" in cmd_lower):
            return volume_set(max(0, min(100, num)))
        if "скачай видео" in cmd_lower:
            return download_current_youtube_video()
        if "открой видео" in cmd_lower or "поищи видео" in cmd_lower:
            query = command.replace("открой", "").replace("поищи", "").replace("видео", "").strip()
            if query:
                return search_and_open_youtube_video(query)
        if "открой загрузки" in cmd_lower:
            open_folder(os.path.expanduser("~/Downloads"))
            return "открываю загрузки"
        if "открой документы" in cmd_lower:
            open_folder(os.path.expanduser("~/Documents"))
            return "открываю документы"
        if "очисти корзину" in cmd_lower:
            return "корзина очищена" if empty_recycle_bin() else "не удалось очистить корзину"
        if any(g in cmd_lower for g in ["привет", "здарова"]):
            return BuiltinCommands.greet(self.config_data["assistant"].get("user_name", "сэр"))
        if "переведи" in cmd_lower:
            return translate_text_with_popup()
        if "открой браузер" in cmd_lower:
            webbrowser.open("https://google.com")
            return "открываю браузер"
        if "открой ютуб" in cmd_lower:
            webbrowser.open("https://youtube.com")
            return "открываю YouTube"
        return self.ai.ask(command, self.config_data["assistant"]["ironic_mode"])

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = AboltusAssistantApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        app.exit_app()