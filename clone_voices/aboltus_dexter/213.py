import os
import re

def remove_hash_from_filenames(directory):
    """
    Удаляет хеш (цифры и буквы в конце) из имен .wav файлов в директории
    """
    # Проверяем, существует ли директория
    if not os.path.exists(directory):
        print(f"Директория {directory} не существует!")
        return
    
    # Получаем список всех .wav файлов
    wav_files = [f for f in os.listdir(directory) if f.endswith('.wav')]
    
    if not wav_files:
        print("В директории нет .wav файлов")
        return
    
    renamed_count = 0
    
    for filename in wav_files:
        # Шаблон: ищем подчеркивание, затем хеш (цифры/буквы), затем .wav
        # Пример: выключение_отменено_2c824d6e.wav -> выключение_отменено.wav
        pattern = r'_(?![^_]*_)([a-f0-9]+)\.wav$'
        
        # Удаляем хеш (все что после последнего подчеркивания и до .wav)
        new_name = re.sub(pattern, '.wav', filename)
        
        # Альтернативный простой способ (если хеш всегда после последнего '_')
        # new_name = '_'.join(filename.split('_')[:-1]) + '.wav'
        
        if new_name != filename:
            old_path = os.path.join(directory, filename)
            new_path = os.path.join(directory, new_name)
            
            # Проверяем, не существует ли уже файл с новым именем
            if os.path.exists(new_path):
                print(f"Пропущен {filename}: файл {new_name} уже существует")
                continue
            
            try:
                os.rename(old_path, new_path)
                print(f"Переименован: {filename} -> {new_name}")
                renamed_count += 1
            except Exception as e:
                print(f"Ошибка при переименовании {filename}: {e}")
    
    print(f"\nГотово! Переименовано файлов: {renamed_count}")

# Использование
directory = r"D:\Aboltus\clone_voices\aboltus_zelens"
remove_hash_from_filenames(directory)