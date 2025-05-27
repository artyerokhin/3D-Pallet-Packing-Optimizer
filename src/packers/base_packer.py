# src/packers/base_packer.py
from py3dbp import Packer
import time
from abc import ABC, abstractmethod

class BasePacker(Packer, ABC):
    def __init__(self):
        super().__init__()
        self.unpacked_items = []
        self.packing_issues = []
        self.calculation_time = 0
        self.allow_rotation = True  # Новый параметр для включения/отключения поворота
        
    @abstractmethod
    def pack(self):
        """Основной метод упаковки - должен быть реализован в наследниках"""
        pass
    
    def _get_item_orientations(self, item):
        """Получить все возможные ориентации предмета"""
        if not self.allow_rotation:
            return [(item.width, item.height, item.depth)]
        
        orientations = [
            (item.width, item.height, item.depth),  # исходная
            (item.height, item.width, item.depth),  # поворот на 90°
            (item.depth, item.height, item.width),  # поворот по другой оси
            (item.height, item.depth, item.width),  # комбинированный поворот
            (item.width, item.depth, item.height),  # еще один поворот
            (item.depth, item.width, item.height)   # финальный поворот
        ]
        # Убираем дубликаты (например, для кубических предметов)
        return list(set(orientations))
    
    def _can_place_item_with_rotation(self, item, x, y, z):
        """Проверка размещения с учетом всех возможных поворотов"""
        for width, height, depth in self._get_item_orientations(item):
            if self._can_place_item_orientation(width, height, depth, x, y, z):
                return (width, height, depth)  # Возвращаем первую подходящую ориентацию
        return None
    
    def _can_place_item_orientation(self, width, height, depth, x, y, z):
        """Проверка размещения для конкретной ориентации"""
        # Проверка границ контейнера
        if (x + width > self.bins[0].width or
            y + height > self.bins[0].height or
            z + depth > self.bins[0].depth):
            return False
        
        # Проверка пересечений
        for other in self.bins[0].items:
            if self._check_intersection_orientation(
                x, y, z, width, height, depth,
                other.position[0], other.position[1], other.position[2],
                other.width, other.height, other.depth
            ):
                return False
        
        # Проверка поддержки снизу
        if z > 0:
            return self._check_support_orientation(width, height, depth, x, y, z)
        
        return True
    
    def _check_intersection_orientation(self, x1, y1, z1, w1, h1, d1, x2, y2, z2, w2, h2, d2):
        """Проверка пересечения для конкретных размеров"""
        return not (
            x1 + w1 <= x2 or x2 + w2 <= x1 or
            y1 + h1 <= y2 or y2 + h2 <= y1 or
            z1 + d1 <= z2 or z2 + d2 <= z1
        )
    
    def _check_support_orientation(self, width, height, depth, x, y, z, support_threshold=0.5):
        """Проверка поддержки для конкретной ориентации"""
        total_support_area = 0
        required_support_area = width * height * support_threshold
        
        for other in self.bins[0].items:
            if abs(other.position[2] + other.depth - z) < 0.1:
                support_area = self._calculate_overlap_area_orientation(
                    other.position[0], other.position[1], other.width, other.height,
                    x, y, width, height
                )
                if support_area > 0:
                    total_support_area += support_area
        
        return total_support_area >= required_support_area
    
    def _calculate_overlap_area_orientation(self, x1, y1, w1, h1, x2, y2, w2, h2):
        """Расчет площади перекрытия для конкретных размеров"""
        x_left = max(x1, x2)
        y_bottom = max(y1, y2)
        x_right = min(x1 + w1, x2 + w2)
        y_top = min(y1 + h1, y2 + h2)
        
        if x_left < x_right and y_bottom < y_top:
            return (x_right - x_left) * (y_top - y_bottom)
        return 0
    
    def _check_weight_limit(self, item_weight):
        """Проверка весового ограничения паллеты"""
        current_weight = sum(item.weight for item in self.bins[0].items)
        max_weight = getattr(self.bins[0], 'max_weight', 1000)
        return current_weight + item_weight <= max_weight
    
    def _check_stability(self, item_width, item_height, item_weight, x, y, z):
        """Проверка устойчивости упаковки"""
        # Расчет центра тяжести
        total_weight = item_weight
        weighted_x = (x + item_width / 2) * item_weight
        weighted_y = (y + item_height / 2) * item_weight
        
        for other in self.bins[0].items:
            center_x = other.position[0] + other.width / 2
            center_y = other.position[1] + other.height / 2
            weighted_x += center_x * other.weight
            weighted_y += center_y * other.weight
            total_weight += other.weight
        
        # Проверяем центр тяжести
        cog_x = weighted_x / total_weight
        cog_y = weighted_y / total_weight
        
        # Центр тяжести должен быть в пределах основания паллеты с небольшим запасом
        margin = min(self.bins[0].width, self.bins[0].height) * 0.1  # 10% запас
        return (margin <= cog_x <= self.bins[0].width - margin and 
                margin <= cog_y <= self.bins[0].height - margin)
    
    # Оставляем старые методы для обратной совместимости
    def _can_place_item(self, item, x, y, z):
        """Обратная совместимость - проверка с поворотом"""
        orientation = self._can_place_item_with_rotation(item, x, y, z)
        return orientation is not None
    
    def _check_intersection(self, item, other, x, y, z):
        """Проверка пересечения двух предметов"""
        return not (
            x + item.width <= other.position[0] or
            other.position[0] + other.width <= x or
            y + item.height <= other.position[1] or
            other.position[1] + other.height <= y or
            z + item.depth <= other.position[2] or
            other.position[2] + other.depth <= z
        )
    
    def _check_support(self, item, x, y, z, support_threshold=0.5):
        """Улучшенная проверка поддержки"""
        return self._check_support_orientation(
            item.width, item.height, item.depth, x, y, z, support_threshold
        )
    
    def _calculate_overlap_area(self, bottom_item, x, y, top_item):
        """Расчет площади перекрытия"""
        return self._calculate_overlap_area_orientation(
            bottom_item.position[0], bottom_item.position[1], 
            bottom_item.width, bottom_item.height,
            x, y, top_item.width, top_item.height
        )
    
    def _start_timing(self):
        """Начать отсчет времени"""
        self.start_time = time.time()
    
    def _end_timing(self):
        """Закончить отсчет времени"""
        self.calculation_time = time.time() - self.start_time
    
    def _initialize_packing(self):
        """Инициализация перед упаковкой"""
        if not self.bins or not self.items:
            return False
        
        self.unpacked_items = []
        self.packing_issues = []
        self.bins[0].items = []
        return True