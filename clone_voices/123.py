import requests
import os
import time

VOICEBOX_URL = "http://localhost:17493"
OUTPUT_DIR = "aboltus_dexter"
TARGET_PROFILE_ID = "b885ccfb-7012-4bcf-9a2e-85334cf6f4e0" # ID для Dexter

def download_filtered_history():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    print(f"🔍 Получаю историю генераций и фильтрую по профилю Dexter...")
    try:
        resp = requests.get(f"{VOICEBOX_URL}/history")
        data = resp.json()
        items = data.get("items", [])
        
        # Фильтруем список: оставляем только те записи, где profile_id совпадает
        dexter_items = [item for item in items if item.get("profile_id") == TARGET_PROFILE_ID]
        
        print(f"✅ Найдено записей всего: {len(items)}")
        print(f"✅ Записей для профиля Dexter: {len(dexter_items)}")
    except Exception as e:
        print(f"❌ Ошибка при получении истории: {e}")
        return

    for item in dexter_items:
        gen_id = item.get("id")
        text = item.get("text", "unknown").replace(" ", "_")[:20]
        filename = f"{text}_{gen_id[:8]}.wav"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        if os.path.exists(filepath):
            print(f"⏭️ Пропуск (уже есть): {filename}")
            continue
            
        print(f"⬇️ Скачиваю (Dexter): {filename}...", end=" ", flush=True)
        try:
            audio_resp = requests.get(f"{VOICEBOX_URL}/audio/{gen_id}")
            if audio_resp.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(audio_resp.content)
                print("✅ Готово")
            else:
                print(f"⚠️ Ошибка {audio_resp.status_code}")
        except Exception as e:
            print(f"❌ {e}")
        
        time.sleep(0.5)

if __name__ == "__main__":
    download_filtered_history()