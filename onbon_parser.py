#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер каталога Onbon.ru — ФИНАЛЬНАЯ ВЕРСИЯ
Извлекает характеристики товаров и экспортирует в CSV
"""

import requests
import csv
import re
import argparse
import time
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
import logging
from collections import defaultdict
from typing import Optional, List, Dict

# ==================== КОНФИГУРАЦИЯ ====================
CONFIG = {
    'base_domain': 'http://onbon.ru',
    'slugs_file': 'onbon_slugs.txt',
    'output_csv': 'onbon_catalog.csv',
    'timeout': 30,
    'delay': 0.5,  # задержка между запросами (сек)
    'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
    }
}

# ==================== МАППИНГ КАТЕГОРИЙ ====================
# Префикс slug → категория в URL
URL_CATEGORIES = {
    # Видеопроцессоры
    'ovp-': 'videoprocessory',
    'sdi-modul': 'videoprocessory',
    
    # Sending cards
    'bx-vs': 'sending-cards',
    'bx-vse': 'sending-cards',
    'bx-vh': 'sending-cards',
    'bx-vhe': 'sending-cards',
    'x-u': 'sending-cards',
    'x-w': 'sending-cards',
    
    # Receiving cards
    'bx-v-receiving': 'receiving-cards',
    'bx-v75': 'receiving-cards',
    'bx-vmf': 'receiving-cards',
    'bx-6q': 'receiving-cards',
    'bx-5q': 'receiving-cards',
    'bx-5ql': 'receiving-cards',
    'bx-mfyq': 'receiving-cards',
    
    # Контроллеры BX-5x
    'bx-5m': 'controllers-bx5',
    'bx-5u': 'controllers-bx5',
    'bx-5e': 'controllers-bx5',
    'bx-5a': 'controllers-bx5',
    'bx-5k': 'controllers-bx5',
    
    # Контроллеры BX-6x
    'bx-6m': 'controllers-bx6',
    'bx-6u': 'controllers-bx6',
    'bx-6e': 'controllers-bx6',
    'bx-6w': 'controllers-bx6',
    
    # Контроллеры YQ/Y-серии
    'bx-yq': 'controllers-yq',
    'bx-y0': 'controllers-yq',
    'bx-y2': 'controllers-yq',
    'bx-y3': 'controllers-yq',
    
    # HUB и адаптеры
    'hub': 'hub-adapters',
    'usbrs232': 'hub-adapters',
    '50pin-row': 'hub-adapters',
    
    # Датчики и пульты
    'temperatur': 'sensors',
    'brightness': 'sensors',
    'infrared-remote': 'sensors',
    
    # Сетевые модули
    'bx-wifi': 'network-modules',
    'bx-rf': 'network-modules',
    'bx-3gprs': 'network-modules',
    'bx-3gw': 'network-modules',
    
    # Питание и кабели
    '5v2a-power': 'power-cables',
    'usb-extension': 'power-cables',
    
    # Прочее
    '676': 'controllers-bx5',
    'bx-dc': 'accessories',
}

# Названия категорий для вывода
CATEGORY_NAMES = {
    'videoprocessory': 'Видеопроцессоры',
    'sending-cards': 'Передающие карты/боксы',
    'receiving-cards': 'Приёмные карты',
    'controllers-bx5': 'Контроллеры BX-5x',
    'controllers-bx6': 'Контроллеры BX-6x',
    'controllers-yq': 'Контроллеры YQ-серии',
    'hub-adapters': 'HUB-платы и адаптеры',
    'sensors': 'Датчики и пульты',
    'network-modules': 'Сетевые модули',
    'power-cables': 'Питание и кабели',
    'accessories': 'Аксессуары',
    'other': 'Прочее',
}

# ==================== ЛОГИРОВАНИЕ ====================
def setup_logging(log_file: str = 'onbon_parser.log'):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8', mode='w'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ==================== ФУНКЦИИ ====================

def load_slugs(filepath: str) -> List[str]:
    """Загружает список slug из файла"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            slugs = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        logger.info(f'📦 Загружено {len(slugs)} моделей из {filepath}')
        return slugs
    except FileNotFoundError:
        logger.error(f'❌ Файл не найден: {filepath}')
        return []


def build_product_url(slug: str) -> str:
    """Строит правильный URL: http://onbon.ru/product/{category}/{slug}"""
    slug_lower = slug.lower()
    
    for prefix, category in URL_CATEGORIES.items():
        if slug_lower.startswith(prefix) or prefix in slug_lower:
            return f"{CONFIG['base_domain']}/product/{category}/{slug}"
    
    # Фолбэк для неизвестных категорий
    return f"{CONFIG['base_domain']}/product/other/{slug}"


def detect_category_name(slug: str) -> str:
    """Возвращает читаемое название категории"""
    url = build_product_url(slug)
    parts = url.split('/')
    if len(parts) >= 5:
        cat_id = parts[4]
        return CATEGORY_NAMES.get(cat_id, cat_id.replace('-', ' ').title())
    return 'Прочее'


def fetch_page(url: str) -> Optional[str]:
    """Скачивает HTML страницы с обработкой кодировок"""
    try:
        response = requests.get(url, headers=CONFIG['headers'], timeout=CONFIG['timeout'], allow_redirects=True)
        
        if response.status_code != 200:
            logger.debug(f'⚠️ {response.status_code} для {url}')
            return None
        
        # Пробуем разные кодировки
        for enc in ['utf-8-sig', 'utf-8', 'cp1251']:
            try:
                return response.content.decode(enc)
            except:
                continue
        return response.text
        
    except requests.RequestException as e:
        logger.debug(f'⚠️ Ошибка загрузки {url}: {e}')
        return None


def parse_value_unit(raw: str) -> Dict[str, str]:
    """Разбирает значение на части: value, unit, notes"""
    result = {'value': raw.strip(), 'unit': '', 'notes': ''}
    
    # Выделяем примечания в скобках
    notes_match = re.search(r'\(([^)]+)\)\s*$', raw)
    if notes_match:
        result['notes'] = notes_match.group(1).strip()
        result['value'] = raw[:notes_match.start()].strip()
    
    # Паттерны для единиц измерения
    unit_patterns = [
        (r'([\d.,]+)\s*(Вт|W)', 'W'),
        (r'([\d.,]+)\s*(кг|kg)', 'kg'),
        (r'([\d.,]+)\s*(мм|mm)', 'mm'),
        (r'([\d.,]+)\s*(°C|℃)', '°C'),
        (r'([\d.,]+)\s*(%)', '%'),
        (r'([\d.,]+)\s*(V|В)', 'V'),
        (r'([\d.,]+)\s*(Hz)', 'Hz'),
        (r'([\d.,]+)\s*(пикс?|px)', 'px'),
    ]
    
    for pattern, unit in unit_patterns:
        if re.search(pattern, result['value'], re.I):
            result['unit'] = unit
            break
    
    return result


def parse_product_page(html: str, slug: str) -> List[Dict[str, str]]:
    """Извлекает характеристики из HTML страницы"""
    specs = []
    seen = set()  # Для дедупликации
    soup = BeautifulSoup(html, 'html.parser')
    
    # Ищем таблицы характеристик
    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:
                continue
            
            param = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True)
            
            # Пропускаем заголовки и пустые значения
            if not param or not value:
                continue
            if param.lower() in ['параметр', 'наименование', 'характеристика', 'параметры']:
                continue
            
            parsed = parse_value_unit(value)
            
            # Создаём сигнатуру для дедупликации
            signature = (
                param.lower().strip(),
                parsed['value'].lower().strip(),
                parsed['unit'].lower().strip(),
                parsed['notes'].lower().strip()
            )
            
            if signature in seen:
                continue  # Пропускаем дубль
            seen.add(signature)
            
            specs.append({
                'parameter': param,
                'value': parsed['value'],
                'unit': parsed['unit'],
                'notes': parsed['notes'],
            })
    
    # Фолбэк: ищем в списках <dl>/<dt>/<dd>
    if not specs:
        for dl in soup.find_all('dl'):
            for dt, dd in zip(dl.find_all('dt'), dl.find_all('dd')):
                param = dt.get_text(strip=True)
                value = dd.get_text(strip=True)
                
                if not param or not value:
                    continue
                
                parsed = parse_value_unit(value)
                signature = (param.lower().strip(), parsed['value'].lower().strip())
                
                if signature in seen:
                    continue
                seen.add(signature)
                
                specs.append({
                    'parameter': param,
                    'value': parsed['value'],
                    'unit': parsed['unit'],
                    'notes': parsed['notes'],
                })
    
    return specs


def parse_product(slug: str) -> Optional[Dict]:
    """Парсит один продукт и возвращает структурированные данные"""
    url = build_product_url(slug)
    html = fetch_page(url)
    
    # Фолбэк: пробуем URL без категории
    if not html:
        fallback_url = f"{CONFIG['base_domain']}/product/{slug}"
        html = fetch_page(fallback_url)
        if html:
            logger.debug(f'🔄 Фолбэк URL сработал для {slug}')
    
    if not html:
        logger.warning(f'⚠️ Не загружен: {slug}')
        return None
    
    specs = parse_product_page(html, slug)
    
    if not specs:
        logger.debug(f'⚠️ Нет характеристик: {slug}')
        return None
    
    return {
        'slug': slug,
        'url': url,
        'category': detect_category_name(slug),
        'updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'specs': specs,
        'spec_count': len(specs)
    }


def export_csv(products: List[Dict], filepath: str):
    """Экспортирует все продукты в плоский CSV"""
    if not products:
        logger.warning('⚠️ Нет данных для экспорта')
        return
    
    fieldnames = ['sku', 'slug', 'model', 'category', 'parameter', 'value', 'unit', 'notes', 'url', 'updated']
    
    rows = []
    for prod in products:
        for spec in prod['specs']:
            rows.append({
                'sku': f"{prod['category'][:3].upper()}-{prod['slug'].upper().replace('-', '_')[:10]}-{hash(spec['parameter']) % 1000:03d}",
                'slug': prod['slug'],
                'model': prod['slug'].upper().replace('-', ' '),
                'category': prod['category'],
                'parameter': spec['parameter'],
                'value': spec['value'],
                'unit': spec['unit'],
                'notes': spec['notes'],
                'url': prod['url'],
                'updated': prod['updated']
            })
    
    # Сортировка для удобства
    rows.sort(key=lambda x: (x['category'], x['slug'], x['parameter']))
    
    with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    logger.info(f'💾 Экспортировано {len(rows)} строк в {filepath}')


def export_summary(products: List[Dict]):
    """Выводит сводку по категориям"""
    if not products:
        return
    
    print('\n' + '=' * 70)
    print('📊 СВОДКА ПО КАТЕГОРИЯМ')
    print('=' * 70)
    
    by_cat = defaultdict(int)
    for p in products:
        by_cat[p['category']] += 1
    
    total_products = 0
    total_specs = sum(p['spec_count'] for p in products)
    
    for cat, cnt in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f'📁 {cat}: {cnt} продуктов')
        total_products += cnt
    
    print('\n' + '-' * 70)
    print(f'🎯 ВСЕГО: {total_products} продуктов, {total_specs} параметров')
    print('=' * 70)


def run_parser(slug_list: Optional[List[str]] = None, category_filter: Optional[str] = None):
    """Основная функция запуска парсера"""
    logger.info('🚀 Запуск парсера Onbon')
    
    if slug_list is None:
        slug_list = load_slugs(CONFIG['slugs_file'])
        if not slug_list:
            logger.error('❌ Нет моделей для парсинга')
            return
    
    # Фильтр по категории (по названию)
    if category_filter:
        slug_list = [s for s in slug_list if category_filter.lower() in detect_category_name(s).lower()]
        logger.info(f'🎯 Фильтр "{category_filter}": {len(slug_list)} моделей')
    
    products = []
    success = 0
    failed = 0
    
    for i, slug in enumerate(slug_list, 1):
        logger.info(f'[{i}/{len(slug_list)}] Обработка: {slug}')
        
        result = parse_product(slug)
        if result:
            products.append(result)
            success += 1
        else:
            failed += 1
        
        # Задержка чтобы не блокировали
        if i < len(slug_list):
            time.sleep(CONFIG['delay'])
    
    # Экспорт
    if products:
        export_csv(products, CONFIG['output_csv'])
        export_summary(products)
    
    # Итог
    print(f'\n✅ Готово: {success} успешно, {failed} с ошибками')
    logger.info(f'🏁 Завершено: {success}/{len(slug_list)}')


def main():
    parser = argparse.ArgumentParser(description='Парсер каталога Onbon.ru')
    parser.add_argument('--category', '-c', type=str, default=None,
                       help='Фильтр по категории (например: "Видеопроцессоры")')
    parser.add_argument('--test', '-t', type=str, default=None,
                       help='Протестировать парсинг одного slug')
    parser.add_argument('--list', action='store_true',
                       help='Показать список доступных категорий')
    parser.add_argument('--slugs', '-s', type=str, default=None,
                       help='Файл со списком slug (по умолчанию: onbon_slugs.txt)')
    
    args = parser.parse_args()
    
    # Обновляем конфиг из аргументов
    if args.slugs:
        CONFIG['slugs_file'] = args.slugs
    
    # Показать категории
    if args.list:
        print('📁 Доступные категории:')
        for cat_id, cat_name in sorted(CATEGORY_NAMES.items(), key=lambda x: x[1]):
            print(f'  • {cat_name}')
        return
    
    # Тест одного продукта
    if args.test:
        print(f'🧪 Тест парсинга: {args.test}')
        result = parse_product(args.test)
        if result:
            print(f'✅ Найдено {result["spec_count"]} параметров')
            print(f'📁 Категория: {result["category"]}')
            print(f'🔗 URL: {result["url"]}')
            print('\n📋 Первые 10 характеристик:')
            for spec in result['specs'][:10]:
                unit = f" {spec['unit']}" if spec['unit'] else ""
                print(f"  • {spec['parameter']}: {spec['value']}{unit}")
        else:
            print('❌ Не удалось спарсить')
        return
    
    # Запуск парсинга
    run_parser(category_filter=args.category)


if __name__ == '__main__':
    main()