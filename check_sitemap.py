#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер sitemap.xml для onbon.ru
Извлекает все slug моделей оборудования и сохраняет в файл
"""

import requests
import re
import logging
from urllib.parse import urlparse
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Конфигурация
CONFIG = {
    'base_domain': 'http://onbon.ru',
    'output_file': 'onbon_slugs.txt',
    'timeout': 30,
}

# Возможные адреса sitemap
SITEMAP_CANDIDATES = [
    'sitemap_index.xml',
    'sitemap.xml',
    'sitemap_products.xml',
]


def fetch_text(url: str) -> str | None:
    """Скачивает текст с URL с обработкой редиректов"""
    try:
        resp = requests.get(url, timeout=CONFIG['timeout'], allow_redirects=True)
        resp.raise_for_status()
        # Пробуем разные кодировки
        for enc in ['utf-8-sig', 'utf-8', 'cp1251']:
            try:
                return resp.content.decode(enc)
            except:
                continue
        return resp.text
    except Exception as e:
        logger.error(f'❌ {url}: {e}')
        return None


def parse_with_regex(content: str) -> list[str]:
    """Парсит sitemap через REGEX — работает даже с битым XML"""
    slugs = []
    
    # Паттерн для <loc>...</loc>
    loc_pattern = re.compile(r'<loc>\s*([^<]+)\s*</loc>', re.I)
    
    # Находим все блоки <url>...</url>
    url_blocks = re.findall(r'<url>(.*?)</url>', content, re.I | re.DOTALL)
    
    if url_blocks:
        # Парсим каждый блок <url>
        for block in url_blocks:
            loc_match = loc_pattern.search(block)
            if loc_match:
                loc = loc_match.group(1).strip()
                slug = extract_slug_from_url(loc)
                if slug:
                    slugs.append(slug)
    else:
        # Если нет <url>, ищем просто <loc>
        for loc in loc_pattern.findall(content):
            slug = extract_slug_from_url(loc)
            if slug:
                slugs.append(slug)
    
    return slugs


def extract_slug_from_url(url: str) -> str | None:
    """Извлекает slug модели из URL продукта"""
    if '/product/' not in url:
        return None
    
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    parts = path.split('/')
    
    # Ожидаем: .../product/CATEGORY/SLUG[.html]
    try:
        prod_idx = parts.index('product')
        if len(parts) > prod_idx + 2:
            slug = parts[prod_idx + 2].replace('.html', '').replace('.xml', '')
            return slug if slug else None
    except (ValueError, IndexError):
        pass
    
    # Фолбэк: последняя часть пути
    slug = parts[-1].replace('.html', '').replace('.xml', '')
    return slug if slug and len(slug) > 1 else None


def find_sitemap_urls(content: str) -> list[str]:
    """Находит ссылки на дочерние sitemap в индексе (через regex)"""
    urls = []
    # Паттерн для <loc> внутри sitemap-индекса
    pattern = re.compile(r'<sitemap>.*?<loc>\s*([^<]+)\s*</loc>.*?</sitemap>', re.I | re.DOTALL)
    
    for match in pattern.finditer(content):
        loc = match.group(1).strip()
        # Делаем абсолютный URL если нужно
        if loc.startswith('//'):
            loc = 'https:' + loc
        elif loc.startswith('/'):
            loc = CONFIG['base_domain'] + loc
        elif not loc.startswith('http'):
            loc = CONFIG['base_domain'] + '/' + loc
        urls.append(loc)
    
    return urls


def main():
    print('=' * 70)
    print('🔍 SITEMAP ПАРСЕР ДЛЯ ONBON.RU')
    print('=' * 70)
    
    all_slugs = []
    processed_sitemaps = set()
    sitemap_to_parse = []
    
    # Находим рабочий sitemap
    for candidate in SITEMAP_CANDIDATES:
        url = f"{CONFIG['base_domain']}/{candidate}"
        print(f'\n📍 Проверяем: {url}')
        
        content = fetch_text(url)
        if not content:
            print('⚠️ Не удалось загрузить')
            continue
        
        # Определяем тип по содержимому
        if '<sitemapindex' in content.lower() or '<sitemap:index' in content.lower():
            print('✅ Это индекс sitemap')
            children = find_sitemap_urls(content)
            print(f'🔗 Найдено дочерних: {len(children)}')
            sitemap_to_parse.extend(children)
            break
        elif '<urlset' in content.lower() or '<url' in content.lower():
            print('✅ Это обычный sitemap — парсим...')
            slugs = parse_with_regex(content)
            print(f'📦 Найдено slug: {len(slugs)}')
            all_slugs.extend(slugs)
            break
        else:
            print('⚠️ Не распознан формат')
    
    # Если есть дочерние sitemap — парсим их
    if sitemap_to_parse:
        print(f'\n🔄 Парсим {len(sitemap_to_parse)} дочерних sitemap...')
        for sm_url in sitemap_to_parse:
            if sm_url in processed_sitemaps:
                continue
            processed_sitemaps.add(sm_url)
            print(f'\n  📥 {sm_url}')
            content = fetch_text(sm_url)
            if content:
                slugs = parse_with_regex(content)
                print(f'     → {len(slugs)} slug')
                all_slugs.extend(slugs)
    
    # Удаляем дубликаты
    unique_slugs = list(dict.fromkeys(all_slugs))
    
    # === ВЫВОД РЕЗУЛЬТАТОВ ===
    print('\n' + '=' * 70)
    print('📊 РЕЗУЛЬТАТЫ')
    print('=' * 70)
    
    if unique_slugs:
        print(f'\n✅ Найдено уникальных моделей: {len(unique_slugs)}\n')
        
        # Группировка по префиксам
        prefixes = {}
        for slug in unique_slugs:
            prefix = slug.split('-')[0] if '-' in slug else slug[:3]
            prefixes[prefix] = prefixes.get(prefix, 0) + 1
        
        print('📁 По префиксам:')
        for prefix, cnt in sorted(prefixes.items(), key=lambda x: -x[1])[:15]:
            print(f'  • {prefix}: {cnt} шт.')
        
        # Сохранение в файл
        with open(CONFIG['output_file'], 'w', encoding='utf-8') as f:
            for slug in unique_slugs:
                f.write(f'{slug}\n')
        
        print(f'\n💾 Сохранено в: {CONFIG["output_file"]}')
        
        # Вывод первых 30 для проверки
        print(f'\n🏷️ Первые 30 моделей:')
        for i, slug in enumerate(unique_slugs[:30], 1):
            print(f'  {i:2d}. {slug}')
        if len(unique_slugs) > 30:
            print(f'  ... и ещё {len(unique_slugs) - 30}')
        
        # Готовый список для Python-конфига
        print(f'\n🐍 Для вставки в CONFIG["models"]:')
        print('models = [')
        for slug in unique_slugs[:15]:
            print(f"    '{slug}',")
        if len(unique_slugs) > 15:
            print(f"    # ... ещё {len(unique_slugs) - 15}")
        print(']')
        
    else:
        print('\n❌ Не удалось извлечь slug')
        print('\n💡 Попробуй:')
        print('  1. Открыть http://onbon.ru/robots.txt в браузере')
        print('  2. Найти строку "Sitemap: ..."')
        print('  3. Вставить этот URL в SITEMAP_CANDIDATES')
    
    print('\n' + '=' * 70)


if __name__ == '__main__':
    main()