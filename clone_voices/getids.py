import requests

VOICEBOX_URL = "http://localhost:17493"

try:
    resp = requests.get(f"{VOICEBOX_URL}/profiles")
    if resp.ok:
        profiles = resp.json()
        print("🔍 Доступные профили:")
        for p in profiles:
            print(f"Имя: {p['name']} | ID: {p['id']}")
    else:
        print(f"❌ Ошибка получения профилей: {resp.status_code}")
except Exception as e:
    print(f"❌ Ошибка соединения: {e}")