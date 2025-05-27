from enum import Enum

# Стандартные размеры коробок
STANDARD_BOXES = {
    "Маленькая": {
        "dimensions": (20, 15, 10),
        "weight": 2,
        "color": "red"
    },
    "Средняя": {
        "dimensions": (30, 20, 15),
        "weight": 5,
        "color": "yellow"
    },
    "Книжная": {
        "dimensions": (40, 30, 20),
        "weight": 10,
        "color": "green"
    },
    "Большая": {
        "dimensions": (60, 40, 30),
        "weight": 15,
        "color": "purple"
    },
    "Очень большая": {
        "dimensions": (80, 60, 40),
        "weight": 20,
        "color": "orange"
    }
}

# Параметры паллеты по умолчанию
DEFAULT_PALLET = {
    "width": 120,
    "height": 100,
    "depth": 180,
    "max_weight": 1000
}

# Параметры алгоритмов
ALGORITHM_PARAMS = {
    "support_threshold": 0.6,
    "weight_tolerance": 0.7,
    "grid_step": 5,
    "max_iterations": 1000
}

class PackingMethod(Enum):
    WEIGHT_AWARE = "Weight-Aware (стабильная укладка с учетом веса)"
    EXTREME_POINTS = "Extreme Points (максимизация использования пространства)"
    LAFF = "Largest Area Fit First (быстрая послойная укладка)"
    CORNER_POINTS = "Corner Points (оптимизация по угловым точкам)"
    SFC = "Space Filling Curve (спиральная укладка с учетом веса)"

method_descriptions = {
    PackingMethod.WEIGHT_AWARE.value: """
**Weight-Aware метод**
- Учитывает вес коробок при размещении
- Обеспечивает стабильность укладки
- Не допускает размещение тяжелых коробок на легких
- Проверяет площадь опоры для каждой коробки
""",
    PackingMethod.EXTREME_POINTS.value: """
**Extreme Points метод**
- Максимизирует использование пространства
- Учитывает все возможные ориентации коробок
- Использует динамические точки размещения
- Оптимизирует плотность упаковки
""",
    PackingMethod.LAFF.value: """
**Largest Area Fit First метод**
- Быстрый и предсказуемый алгоритм
- Послойная укладка коробок
- Приоритет коробкам с большей площадью основания
- Эффективен для однородных грузов
""",
    PackingMethod.CORNER_POINTS.value: """
**Corner Points метод**
- Оптимизация размещения по угловым точкам
- Учитывает компактность упаковки
- Минимизирует пустые пространства
- Эффективен для разнородных грузов
""",
    PackingMethod.SFC.value: """
**Space Filling Curve метод**
- Спиральное заполнение пространства от центра
- Учет веса и устойчивости
- Оптимизация использования пространства
- Эффективен для разных размеров коробок
"""
}