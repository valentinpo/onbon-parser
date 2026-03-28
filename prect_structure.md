nbon_parser_project/
│
├── 📄 check_sitemap.py          # 🔍 Сбор списка моделей из sitemap.xml
├──  onbon_parser.py           # 🎯 Главный парсер характеристик
├── 📄 split_by_model.py         # ✂️ Разбивка CSV на файлы по моделям
├── 📄 organize_files.py         # 📂 Создание папок для каждой модели
├──  requirements.txt          #  Зависимости Python
├── 📄 project_structure.md      # 📋 Этот файл — документация
│
├── 📄 onbon_slugs.txt           # 📝 Список моделей (131 шт.) ← ТВОЙ ФАЙЛ
│
├── 📊 onbon_catalog.csv         # 📈 Общий каталог (после запуска парсера)
├── 📝 onbon_parser.log          # 📜 Лог работы парсера (после запуска)
│
└── 📂 products_by_model/        # 🗂️ Папка с файлами по моделям
    ├── 📄 index.json            # Индекс всех моделей
    ├── 📂 ovp-m1/
    │   └── 📄 ovp-m1.csv
    ├── 📂 ovp-m2/
    │   └── 📄 ovp-m2.csv
    ├── 📂 bx-vs-sending-card/
    │   └── 📄 bx-vs-sending-card.csv
    └── ... (ещё ~128 папок)