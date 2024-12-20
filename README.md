# 3D Pallet Packing Optimizer

Интерактивное веб-приложение для оптимизации 3D упаковки коробок на поддоны с использованием различных алгоритмов.

## Особенности

- 5 алгоритмов упаковки (Weight-Aware, Extreme Points, LAFF, Corner Points, SFC)
- Проверка физических ограничений и поддержки
- 3D визуализация результатов в реальном времени
- Расчет эффективности использования пространства
- Анализ распределения веса
- Интерактивный веб-интерфейс на Streamlit
- Загрузка пользовательских коробок и выгрузка результатов

## Входные форматы данных
- CSV файл должен содержать следующие колонки: name, length, width, height, weight, quantity
- Excel файл должен иметь аналогичную структуру с теми же колонками
- Все размеры указываются в сантиметрах, вес в килограммах

## Форматы сохранения результатов
- JSON: полная информация о упаковке, включая координаты размещения каждой коробки, статистику и параметры поддона
- CSV: упрощенный формат с основными параметрами упакованных коробок (имя, размеры, вес, координаты)
- Excel: расширенный формат с тремя листами:
  - "Упакованные": информация о размещенных коробках
  - "Неупакованные": список коробок, которые не удалось разместить
  - "Статистика": общие показатели упаковки


## Установка

```bash
git clone https://github.com/artyerokhin/3D-Pallet-Packing-Optimizer.git
cd 3D-Pallet-Packing-Optimizer
pip install -r requirements.txt
```

## Запуск приложения

```bash
streamlit run app.py
```

## Требования

- Python 3.8+
- streamlit>=1.24.0
- plotly>=5.13.0
- numpy>=1.23.5
- py3dbp>=1.1.0
- enum34>=1.1.10

## Алгоритмы упаковки

### Weight-Aware
- Учитывает вес коробок при размещении
- Проверяет площадь опоры (80%)
- Предотвращает размещение тяжелых коробок на легких
- Оптимизация использования пространства

### Extreme Points
- Динамическое определение точек размещения
- Оптимизация плотности упаковки
- Минимизация пустого пространства
- Случайный фактор для разнообразия решений
- Проверка поддержки снизу (70% опоры)

### LAFF (Largest Area Fit First)
- Послойная укладка коробок
- Приоритет коробкам с большей площадью основания
- Оптимизация использования пространства в слое
- Эффективен для однородных грузов
- Проверка поддержки (80% площади)

### Corner Points
- Размещение коробок в угловых точках
- Оптимизация по компактности упаковки
- Сортировка по объему и соотношению сторон
- Минимизация пустых пространств
- Проверка поддержки снизу (80% площади)

### SFC (Space Filling Curve)
- Спиральное заполнение пространства
- Дискретизация пространства сеткой
- Учет веса при размещении
- Проверка поддержки снизу
- Оптимизация для разных размеров коробок

## Структура проекта

```
3D-Pallet-Packing-Optimizer/
├── src/
│   ├── packers/
│   │   ├── __init__.py
│   │   ├── weight_aware.py    # Weight-Aware алгоритм
│   │   ├── extreme_points.py  # Extreme Points алгоритм
│   │   ├── laff.py           # LAFF алгоритм
│   │   ├── corner_points.py  # Corner Points алгоритм
│   │   └── sfc.py           # SFC алгоритм
│   └── utils/
│       ├── __init__.py
│       ├── visualization.py   # Функции визуализации
│       └── constants.py       # Константы и перечисления
├── tests/
│   └── test_base.py          # Базовые тесты
│   └── test_file_operations.py       # Тесты работы с файлами
├── examples/
│   └── boxes_example.csv         # Пример файла
├── results/                # Создается автоматом
│   ├── packing_result_*.json
│   ├── packing_result_*.csv
│   └── packing_result_*.xlsx
├── app.py                     # Основное приложение
├── requirements.txt          # Зависимости проекта
├── .gitignore
└── README.md
```

## Лицензия

MIT License

## Запуск тестов

```bash
pytest tests/test_base.py -v
```

## Пример работы программы

<img src="images/demo.png" alt="3D Bin Packing Demo" width="800"/>