```markdown
# 3D Pallet Packing Optimizer

Интерактивное веб-приложение для оптимизации 3D упаковки коробок на поддоны с использованием различных алгоритмов и учетом физических ограничений.

## Особенности

- 5 алгоритмов упаковки (Weight-Aware, Extreme Points, LAFF, Corner Points, SFC)
- Учет веса и стабильности упаковки
- Проверка физических ограничений и поддержки
- 3D визуализация результатов в реальном времени
- Расчет эффективности использования пространства
- Анализ распределения веса
- Интерактивный веб-интерфейс на Streamlit

## Установка

```
git clone https://github.com/yourusername/3D-Pallet-Packing-Optimizer.git
cd 3D-Pallet-Packing-Optimizer
pip install -r requirements.txt
```

## Требования

```
streamlit>=1.24.0
plotly>=5.13.0
numpy>=1.23.5
py3dbp>=1.1.0
enum34>=1.1.10
```

## Использование

```
streamlit run app.py
```

## Алгоритмы упаковки

**Weight-Aware метод**
- Учитывает вес коробок при размещении
- Проверяет площадь опоры для каждой коробки
- Предотвращает размещение тяжелых коробок на легких
- Оптимизация использования пространства

**Extreme Points**
- Динамическое определение точек размещения
- Оптимизация плотности упаковки
- Минимизация пустого пространства
- Случайный фактор для разнообразия решений
- Проверка поддержки снизу (требует 70% опоры)

**LAFF (Largest Area Fit First)**
- Послойная укладка коробок
- Приоритет коробкам с большей площадью основания
- Оптимизация использования пространства в слое
- Эффективен для однородных грузов
- Проверка стабильности и поддержки (80% площади)

**Corner Points**
- Размещение коробок в угловых точках
- Оптимизация по компактности упаковки
- Сортировка по объему и соотношению сторон
- Минимизация пустых пространств
- Проверка поддержки снизу (80% площади)

**SFC (Space Filling Curve)**
- Спиральное заполнение пространства
- Дискретизация пространства сеткой
- Учет веса при размещении
- Проверка стабильности и поддержки
- Оптимизация для разных размеров коробок

## Особенности реализации

**Общие характеристики**
- Проверка пересечений коробок
- Учет границ контейнера
- Расчет площади поддержки
- Оптимизация времени вычислений
- Визуализация результатов в 3D

**Физические ограничения**
- Контроль максимального веса
- Проверка устойчивости конструкции
- Учет распределения нагрузки
- Соблюдение требований к опорной площади
- Предотвращение нестабильных конфигураций

## Структура проекта

```
3D-Pallet-Packing-Optimizer/
├── src/
│   ├── __init__.py
│   ├── packers/
│   │   ├── __init__.py
│   │   ├── weight_aware.py    # Weight-Aware алгоритм
│   │   ├── extreme_points.py  # Extreme Points алгоритм
│   │   ├── laff.py           # LAFF алгоритм
│   │   ├── corner_points.py  # Corner Points алгоритм
│   │   └── sfc.py           # SFC алгоритм
│   └── utils/
│       ├── __init__.py
│       ├── visualization.py
│       └── constants.py
├── app.py
├── requirements.txt
├── LICENSE
└── README.md
```

## Лицензия

MIT License
```