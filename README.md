# 🕷️ Onbon.ru Parser

Парсер каталога светодиодного оборудования с сайта **onbon.ru**.
Извлекает характеристики товаров и экспортирует в CSV для интеграции с системами учёта (1С, МойСклад).

> **Сайт:** https://onbon.ru
> **Компания:** Onbon — тот же вендор, что и в [onbonbx-parser](https://github.com/valentinpo/onbonbx-parser), но у **onbon.ru другая структура каталога**.
> Связанный репозиторий: [Onbon-LED-Controllers-Data-Repository](https://github.com/valentinpo/Onbon-LED-Controllers-Data-Repository).

---

## ✨ Возможности

- 🕷 **Сбор каталога** — извлечение характеристик светодиодного оборудования
- 🗂 **Разбивка по моделям** — формирование CSV-файла для каждой модели отдельно
- 📊 **Экспорт в CSV** — для интеграции с системами учёта (1С, МойСклад)
- 🔁 **Автоматическое обновление** — повторный запуск парсит заново весь каталог

---

## 📁 Структура проекта

```
onbon-parser/
├── onbon_parser.py          # Основной парсер каталога
├── check_sitemap.py         # Проверка наличия карты сайта sitemap.xml
├── split_by_model.py        # Разбивка общего CSV на CSV по каждой модели
├── organize_files.py        # Организация файлов по папкам моделей
├── onbon_slugs.txt          # Список моделей (131 шт.) для сопоставления
├── requirements.txt         # Зависимости Python
├── prect_structure.md       # Описание структуры проекта
├── start.md                 # Инструкция по запуску
└── README.md                # Документация
```

---

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Запуск парсинга каталога

```bash
python onbon_parser.py
# Результат: onbon_catalog.csv (полный каталог)
# Ожидаемый результат: 128+ моделей...
```

### 3. Разбивка по моделям

```bash
python split_by_model.py
# Результат: products_by_model/ — папка с CSV-файлом для каждой модели
```

### 4. Организация файлов по папкам

```bash
python organize_files.py
# Результат: products_by_model/ организован в папки ovp-m1, ovp-m2 и т.д.
```

---

## 📄 Что где лежит после парсинга

- **Полный каталог:** `onbon_catalog.csv` — удобно открывать в Excel
- **По моделям:** `products_by_model/` — папка с CSV для каждой модели отдельно
- **Логи:** `onbon_parser.log` — история работы парсера

---

## 🛠 Частые проблемы

| Проблема | Решение |
|---|---|
| `No module named 'requests'` | Установи зависимости: `pip install -r requirements.txt` |
| `File not found` | Убедись, что запускаешь скрипт из папки проекта |
| `404 Not Found` | Некоторые страницы недоступны — повторный запуск пропустит их |
| Кривизна в CSV | Сохрани/открой с кодировкой UTF-8 |

---

## 🔄 Обновление данных

Чтобы обновить каталог — просто запусти шаги 2–4 заново:

```bash
python onbon_parser.py
python split_by_model.py
python organize_files.py
```

---

## 📫 Связанные репозитории

- [onbonbx-parser](https://github.com/valentinpo/onbonbx-parser) — парсер сайта **ru.onbonbx.com**
- [Onbon-LED-Controllers-Data-Repository](https://github.com/valentinpo/Onbon-LED-Controllers-Data-Repository) — структурированная база данных LED-контроллеров Onbon