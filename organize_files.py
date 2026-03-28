#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создаёт папки для каждой модели и раскладывает файлы по ним
Из: products_by_model/ovp-m1.csv
В: products_by_model/ovp-m1/ovp-m1.csv
"""

import shutil
from pathlib import Path
import logging
import re

# ==================== КОНФИГУРАЦИЯ ====================
CONFIG = {
    'source_dir': 'products_by_model',
    'file_extension': '.csv',  # или '.json'
}

# ==================== ЛОГИРОВАНИЕ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ==================== ФУНКЦИИ ====================

def safe_folder_name(name: str) -> str:
    """Делает безопасное имя папки из названия файла"""
    # Убираем расширение
    name = name.replace('.csv', '').replace('.json', '')
    # Заменяем опасные символы
    name = re.sub(r'[^\w\-_.]', '_', name.strip().lower())
    name = re.sub(r'_+', '_', name)
    return name.strip('_')


def organize_files():
    """Основная функция"""
    source_dir = Path(CONFIG['source_dir'])
    
    if not source_dir.exists():
        logger.error(f'❌ Папка не найдена: {source_dir}')
        return
    
    # Находим все файлы с расширением
    files = list(source_dir.glob(f'*{CONFIG["file_extension"]}'))
    
    # Исключаем index.json если есть
    files = [f for f in files if f.name != 'index.json']
    
    if not files:
        logger.info('📭 Нет файлов для обработки')
        return
    
    logger.info(f'📁 Найдено файлов: {len(files)}')
    
    created_folders = 0
    moved_files = 0
    
    for filepath in files:
        # Получаем имя без расширения
        folder_name = safe_folder_name(filepath.name)
        
        # Создаём папку
        folder_path = source_dir / folder_name
        folder_path.mkdir(exist_ok=True)
        
        # Перемещаем файл в папку
        dest_path = folder_path / filepath.name
        
        try:
            shutil.move(str(filepath), str(dest_path))
            moved_files += 1
            created_folders += 1
            logger.debug(f'✅ {filepath.name} → {folder_name}/')
        except Exception as e:
            logger.error(f'❌ Ошибка с {filepath.name}: {e}')
    
    # Итог
    print('\n' + '=' * 50)
    print('✅ ГОТОВО')
    print('=' * 50)
    print(f'📁 Папка: {source_dir}/')
    print(f'📂 Создано папок: {created_folders}')
    print(f'📄 Перемещено файлов: {moved_files}')
    print('\n📋 Пример структуры:')
    
    # Показываем первые 5 папок
    folders = sorted([f for f in source_dir.iterdir() if f.is_dir()])[:5]
    for folder in folders:
        files_in_folder = list(folder.glob(f'*{CONFIG["file_extension"]}'))
        print(f'  📂 {folder.name}/')
        for f in files_in_folder[:3]:
            print(f'     └── {f.name}')
    
    if len(folders) > 5:
        print(f'  ... и ещё {len(folders) - 5} папок')
    
    print('=' * 50)


if __name__ == '__main__':
    organize_files()