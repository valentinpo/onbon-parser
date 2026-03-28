#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Разбивает onbon_catalog.csv на отдельные файлы по моделям
Удаляет точные дубликаты строк, сохраняет всю структуру CSV
Версия: 1.0
"""

import csv
import json
from pathlib import Path
from collections import defaultdict
import logging
import re

# ==================== КОНФИГУРАЦИЯ ====================
CONFIG = {
    'input_csv': 'onbon_catalog.csv',
    'output_dir': 'products_by_model',
    'format': 'csv',  # 'csv' или 'json'
    'encoding': 'utf-8-sig',  # для Excel
    'group_by': 'slug',  # поле для группировки
    # Поля для проверки дублей (все кроме служебных)
    'dedupe_fields': ['parameter', 'value', 'unit', 'notes', 'category'],
}

# Все поля CSV (порядок важен для сохранения структуры)
CSV_FIELDS = ['sku', 'slug', 'model', 'category', 'parameter', 'value', 'unit', 'notes', 'url', 'updated']

# ==================== ЛОГИРОВАНИЕ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ==================== ФУНКЦИИ ====================

def safe_filename(name: str) -> str:
    """Делает безопасное имя файла из названия модели"""
    name = re.sub(r'[^\w\-_.]', '_', name.strip().lower())
    name = re.sub(r'_+', '_', name)
    return name.strip('_')


def load_catalog(filepath: str) -> list[dict]:
    """Загружает CSV каталог"""
    if not Path(filepath).exists():
        logger.error(f'❌ Файл не найден: {filepath}')
        return []
    
    with open(filepath, 'r', encoding=CONFIG['encoding']) as f:
        reader = csv.DictReader(f)
        return list(reader)


def create_dedupe_key(row: dict) -> tuple:
    """Создаёт ключ для проверки дублей по указанным полям"""
    return tuple(
        row.get(field, '').strip().lower() 
        for field in CONFIG['dedupe_fields']
    )


def group_by_model(rows: list[dict], key_field: str) -> dict[str, list[dict]]:
    """Группирует строки по модели + удаляет точные дубликаты"""
    grouped = defaultdict(list)
    stats = {'total': len(rows), 'duplicates_removed': 0}
    
    for row in rows:
        key = row.get(key_field, 'unknown').strip()
        if not key:
            continue
        
        # Создаём ключ для проверки дублей
        dedupe_key = create_dedupe_key(row)
        
        # Проверяем, нет ли уже такой строки для этой модели
        is_duplicate = False
        for existing in grouped[key]:
            if create_dedupe_key(existing) == dedupe_key:
                stats['duplicates_removed'] += 1
                is_duplicate = True
                break
        
        if not is_duplicate:
            # Сохраняем полную строку со всеми полями
            grouped[key].append(dict(row))
    
    logger.info(f'📊 Дублей удалено: {stats["duplicates_removed"]} из {stats["total"]} строк')
    return dict(grouped)


def export_model_csv(model: str, specs: list[dict], output_dir: Path) -> Path:
    """Экспортирует характеристики модели в отдельный CSV"""
    filename = safe_filename(model) + '.csv'
    filepath = output_dir / filename
    
    with open(filepath, 'w', encoding=CONFIG['encoding'], newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(specs)
    
    return filepath


def export_model_json(model: str, specs: list[dict], output_dir: Path) -> Path:
    """Экспортирует характеристики модели в JSON"""
    filename = safe_filename(model) + '.json'
    filepath = output_dir / filename
    
    data = {
        'model': model,
        'slug': model,
        'spec_count': len(specs),
        'fields': CSV_FIELDS,
        'parameters': specs
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filepath


def export_index(grouped: dict[str, list[dict]], output_dir: Path) -> Path:
    """Создаёт индекс-файл со списком всех моделей"""
    index = {
        'total_models': len(grouped),
        'total_specs': sum(len(s) for s in grouped.values()),
        'generated': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'models': {}
    }
    
    for model, specs in sorted(grouped.items()):
        # Собираем уникальные категории для этой модели
        categories = list(set(s.get('category', '') for s in specs if s.get('category')))
        
        index['models'][model] = {
            'file': safe_filename(model) + '.' + CONFIG['format'],
            'spec_count': len(specs),
            'categories': categories,
            'url': specs[0].get('url', '') if specs else ''
        }
    
    filepath = output_dir / 'index.json'
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    
    return filepath


def export_summary(grouped: dict[str, list[dict]]):
    """Выводит сводку в консоль"""
    if not grouped:
        return
    
    print('\n' + '=' * 70)
    print('📊 СВОДКА ПО МОДЕЛЯМ')
    print('=' * 70)
    
    # Сортировка по кол-ву спецификаций
    sorted_models = sorted(grouped.items(), key=lambda x: -len(x[1]))
    
    print(f'\n📁 Всего моделей: {len(grouped)}')
    print(f'📋 Всего параметров: {sum(len(s) for s in grouped.values())}')
    print(f'📈 В среднем на модель: {sum(len(s) for s in grouped.values()) // len(grouped):.1f}')
    
    print(f'\n🏆 Топ-10 моделей по кол-ву характеристик:')
    for i, (model, specs) in enumerate(sorted_models[:10], 1):
        print(f'  {i:2d}. {model:35s} → {len(specs):3d} параметр(ов)')
    
    print('\n' + '=' * 70)


def main():
    logger.info('🚀 Разбивка каталога по моделям с дедупликацией')
    
    # Проверяем входной файл
    input_path = Path(CONFIG['input_csv'])
    if not input_path.exists():
        logger.error(f'❌ Файл не найден: {input_path}')
        logger.info('💡 Запустите сначала: py onbon_parser.py')
        return
    
    # Загружаем данные
    rows = load_catalog(CONFIG['input_csv'])
    if not rows:
        logger.error('❌ Нет данных для обработки')
        return
    
    logger.info(f'📥 Загружено {len(rows)} строк из {CONFIG["input_csv"]}')
    
    # Группируем по модели + удаляем дубли
    grouped = group_by_model(rows, CONFIG['group_by'])
    logger.info(f'📦 Найдено уникальных моделей: {len(grouped)}')
    
    # Создаём папку для вывода
    output_dir = Path(CONFIG['output_dir'])
    output_dir.mkdir(exist_ok=True)
    
    # Экспортируем каждую модель
    exported = 0
    for model, specs in grouped.items():
        if CONFIG['format'] == 'json':
            export_model_json(model, specs, output_dir)
        else:
            export_model_csv(model, specs, output_dir)
        exported += 1
    
    # Создаём индекс
    index_file = export_index(grouped, output_dir)
    
    # Выводим сводку
    export_summary(grouped)
    
    # Итог
    print(f'\n✅ ГОТОВО')
    print(f'📁 Папка: {output_dir}/')
    print(f'📄 Файлов создано: {exported}')
    print(f'🗂️ Индекс: {index_file.name}')
    print(f'\n💡 Пример использования:')
    print(f'   Открой: {output_dir}/{safe_filename("ovp-m1")}.{CONFIG["format"]}')
    print('=' * 70)


if __name__ == '__main__':
    main()