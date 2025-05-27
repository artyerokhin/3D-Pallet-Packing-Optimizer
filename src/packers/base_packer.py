# src/packers/base_packer.py

from py3dbp import Packer
import time
from abc import ABC, abstractmethod
import psutil
import os

class BasePacker(Packer, ABC):
    def __init__(self):
        super().__init__()
        self.unpacked_items = []
        self.packing_issues = []
        self.calculation_time = 0
        self.allow_rotation = True
        
        # Расширенная аналитика
        self.analytics = {
            'placement_attempts': 0,
            'successful_placements': 0,
            'rotation_usage': {},
            'level_analysis': {},
            'support_quality_scores': [],
            'weight_distribution': {},
            'space_efficiency_by_level': {},
            'algorithm_iterations': 0,
            'memory_usage_start': 0,
            'memory_usage_peak': 0,
            'placement_timeline': [],
            'rejection_reasons': {},
            'orientation_preferences': {},
            'density_analysis': {}
        }

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
        self.analytics['placement_attempts'] += 1
        
        for width, height, depth in self._get_item_orientations(item):
            if self._can_place_item_orientation(width, height, depth, x, y, z):
                # Записываем использованную ориентацию
                orientation_key = f"{width}x{height}x{depth}"
                self.analytics['rotation_usage'][orientation_key] = \
                    self.analytics['rotation_usage'].get(orientation_key, 0) + 1
                
                # Анализ предпочтений ориентации
                original_orientation = f"{item.width}x{item.height}x{item.depth}"
                is_rotated = orientation_key != original_orientation
                
                if item.name not in self.analytics['orientation_preferences']:
                    self.analytics['orientation_preferences'][item.name] = {
                        'original': 0, 'rotated': 0
                    }
                
                if is_rotated:
                    self.analytics['orientation_preferences'][item.name]['rotated'] += 1
                else:
                    self.analytics['orientation_preferences'][item.name]['original'] += 1
                
                return (width, height, depth)
        
        # Записываем причину отказа
        self._record_rejection_reason(item, x, y, z, "no_valid_orientation")
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
        """Проверка поддержки для конкретной ориентации с аналитикой"""
        total_support_area = 0
        required_support_area = width * height * support_threshold
        support_quality = 0

        for other in self.bins[0].items:
            if abs(other.position[2] + other.depth - z) < 0.1:
                support_area = self._calculate_overlap_area_orientation(
                    other.position[0], other.position[1], other.width, other.height,
                    x, y, width, height
                )

                if support_area > 0:
                    total_support_area += support_area
                    support_quality += support_area / (width * height)

        # Записываем качество поддержки
        self.analytics['support_quality_scores'].append(support_quality)
        
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

    def _record_successful_placement(self, item, x, y, z, width, height, depth):
        """Записать успешное размещение для аналитики"""
        self.analytics['successful_placements'] += 1
        
        # Анализ по уровням
        level = self._get_level_for_height(z)
        if level not in self.analytics['level_analysis']:
            self.analytics['level_analysis'][level] = {
                'items_count': 0,
                'total_volume': 0,
                'total_weight': 0,
                'average_height': 0
            }
        
        self.analytics['level_analysis'][level]['items_count'] += 1
        self.analytics['level_analysis'][level]['total_volume'] += width * height * depth
        self.analytics['level_analysis'][level]['total_weight'] += item.weight
        
        # Временная линия размещения
        placement_time = time.time() - self.start_time
        self.analytics['placement_timeline'].append({
            'item_name': item.name,
            'time': placement_time,
            'position': [x, y, z],
            'dimensions': [width, height, depth],
            'level': level
        })
        
        # Анализ плотности
        self._analyze_density_at_position(x, y, z, width, height, depth)

    def _record_rejection_reason(self, item, x, y, z, reason):
        """Записать причину отказа в размещении"""
        if reason not in self.analytics['rejection_reasons']:
            self.analytics['rejection_reasons'][reason] = 0
        self.analytics['rejection_reasons'][reason] += 1

    def _get_level_for_height(self, z):
        """Определить уровень для высоты z"""
        level_height = 20  # см
        return int(z // level_height)

    def _analyze_density_at_position(self, x, y, z, width, height, depth):
        """Анализ плотности в области размещения"""
        # Разбиваем пространство на сетку для анализа плотности
        grid_size = 20
        grid_x = int(x // grid_size)
        grid_y = int(y // grid_size)
        grid_z = int(z // grid_size)
        
        grid_key = f"{grid_x}_{grid_y}_{grid_z}"
        
        if grid_key not in self.analytics['density_analysis']:
            self.analytics['density_analysis'][grid_key] = {
                'volume_used': 0,
                'items_count': 0
            }
        
        self.analytics['density_analysis'][grid_key]['volume_used'] += width * height * depth
        self.analytics['density_analysis'][grid_key]['items_count'] += 1

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

    def generate_detailed_analytics(self):
        """Генерация детальной аналитики упаковки"""
        if not self.bins or not self.bins[0].items:
            return {}

        # Базовые метрики эффективности
        total_volume = sum(item.width * item.height * item.depth for item in self.items)
        packed_volume = sum(item.width * item.height * item.depth for item in self.bins[0].items)
        bin_volume = self.bins[0].width * self.bins[0].height * self.bins[0].depth
        
        total_weight = sum(item.weight for item in self.items)
        packed_weight = sum(item.weight for item in self.bins[0].items)

        analytics = {
            'efficiency_metrics': {
                'volume_utilization': round((packed_volume / total_volume * 100), 2) if total_volume > 0 else 0,
                'space_utilization': round((packed_volume / bin_volume * 100), 2),
                'weight_utilization': round((packed_weight / total_weight * 100), 2) if total_weight > 0 else 0,
                'packing_efficiency': round((len(self.bins[0].items) / len(self.items) * 100), 2) if self.items else 0,
                'packing_density': round((packed_volume / bin_volume), 4),
                'success_rate': round((self.analytics['successful_placements'] / max(self.analytics['placement_attempts'], 1) * 100), 2)
            },
            
            'placement_analysis': {
                'total_attempts': self.analytics['placement_attempts'],
                'successful_placements': self.analytics['successful_placements'],
                'items_by_level': self._analyze_items_by_level(),
                'orientation_usage': self.analytics['rotation_usage'],
                'orientation_preferences': self.analytics['orientation_preferences'],
                'support_quality': {
                    'average_support': round(sum(self.analytics['support_quality_scores']) / max(len(self.analytics['support_quality_scores']), 1), 3),
                    'min_support': min(self.analytics['support_quality_scores']) if self.analytics['support_quality_scores'] else 0,
                    'max_support': max(self.analytics['support_quality_scores']) if self.analytics['support_quality_scores'] else 0
                },
                'rejection_reasons': self.analytics['rejection_reasons']
            },
            
            'performance_metrics': {
                'calculation_time': round(self.calculation_time, 3),
                'algorithm_iterations': self.analytics['algorithm_iterations'],
                'memory_usage': {
                    'start_mb': round(self.analytics['memory_usage_start'] / 1024 / 1024, 2),
                    'peak_mb': round(self.analytics['memory_usage_peak'] / 1024 / 1024, 2),
                    'difference_mb': round((self.analytics['memory_usage_peak'] - self.analytics['memory_usage_start']) / 1024 / 1024, 2)
                },
                'items_per_second': round(len(self.bins[0].items) / max(self.calculation_time, 0.001), 2)
            },
            
            'spatial_analysis': {
                'center_of_gravity': self._calculate_center_of_gravity(),
                'weight_distribution': self._analyze_weight_distribution(),
                'density_map': self._analyze_density_distribution(),
                'space_efficiency_by_level': self._calculate_space_efficiency_by_level(),
                'placement_timeline': self.analytics['placement_timeline']
            },
            
            'recommendations': self._generate_recommendations()
        }
        
        return analytics

    def _analyze_items_by_level(self):
        """Анализ предметов по уровням"""
        level_analysis = {}
        
        for item in self.bins[0].items:
            level = self._get_level_for_height(item.position[2])
            
            if level not in level_analysis:
                level_analysis[level] = {
                    'items': [],
                    'total_volume': 0,
                    'total_weight': 0,
                    'height_range': [float('inf'), 0]
                }
            
            level_analysis[level]['items'].append(item.name)
            level_analysis[level]['total_volume'] += item.width * item.height * item.depth
            level_analysis[level]['total_weight'] += item.weight
            level_analysis[level]['height_range'][0] = min(level_analysis[level]['height_range'][0], item.position[2])
            level_analysis[level]['height_range'][1] = max(level_analysis[level]['height_range'][1], item.position[2] + item.depth)
        
        return level_analysis

    def _calculate_center_of_gravity(self):
        """Расчет центра тяжести упаковки"""
        if not self.bins[0].items:
            return {'x': 0, 'y': 0, 'z': 0}
        
        total_weight = 0
        weighted_x = 0
        weighted_y = 0
        weighted_z = 0
        
        for item in self.bins[0].items:
            center_x = item.position[0] + item.width / 2
            center_y = item.position[1] + item.height / 2
            center_z = item.position[2] + item.depth / 2
            
            weighted_x += center_x * item.weight
            weighted_y += center_y * item.weight
            weighted_z += center_z * item.weight
            total_weight += item.weight
        
        return {
            'x': round(weighted_x / total_weight, 2),
            'y': round(weighted_y / total_weight, 2),
            'z': round(weighted_z / total_weight, 2)
        }

    def _analyze_weight_distribution(self):
        """Анализ распределения веса"""
        if not self.bins[0].items:
            return {}
        
        weights = [item.weight for item in self.bins[0].items]
        
        return {
            'total_weight': sum(weights),
            'average_weight': round(sum(weights) / len(weights), 2),
            'min_weight': min(weights),
            'max_weight': max(weights),
            'weight_variance': round(sum((w - sum(weights)/len(weights))**2 for w in weights) / len(weights), 2)
        }

    def _analyze_density_distribution(self):
        """Анализ распределения плотности"""
        density_stats = {}
        
        for grid_key, data in self.analytics['density_analysis'].items():
            grid_volume = 20 * 20 * 20  # размер ячейки сетки
            density = data['volume_used'] / grid_volume
            
            if 'densities' not in density_stats:
                density_stats['densities'] = []
            
            density_stats['densities'].append(density)
        
        if density_stats.get('densities'):
            densities = density_stats['densities']
            density_stats.update({
                'average_density': round(sum(densities) / len(densities), 3),
                'max_density': round(max(densities), 3),
                'min_density': round(min(densities), 3),
                'occupied_cells': len(densities)
            })
        
        return density_stats

    def _calculate_space_efficiency_by_level(self):
        """Расчет эффективности использования пространства по уровням"""
        level_efficiency = {}
        
        for level, data in self.analytics['level_analysis'].items():
            level_height = 20  # см
            level_volume = self.bins[0].width * self.bins[0].height * level_height
            efficiency = (data['total_volume'] / level_volume) * 100 if level_volume > 0 else 0
            
            level_efficiency[level] = {
                'efficiency_percent': round(efficiency, 2),
                'items_count': data['items_count'],
                'volume_used': data['total_volume']
            }
        
        return level_efficiency

    def _generate_recommendations(self):
        """Генерация рекомендаций по улучшению упаковки"""
        recommendations = []
        
        # Анализ эффективности
        if self.analytics['successful_placements'] / max(self.analytics['placement_attempts'], 1) < 0.7:
            recommendations.append("Низкая эффективность размещения. Рассмотрите изменение порядка сортировки предметов.")
        
        # Анализ поворотов
        rotation_usage = self.analytics['rotation_usage']
        if len(rotation_usage) > 1:
            most_used = max(rotation_usage, key=rotation_usage.get)
            recommendations.append(f"Наиболее используемая ориентация: {most_used}. Рассмотрите оптимизацию под эту ориентацию.")
        
        # Анализ отказов
        rejection_reasons = self.analytics['rejection_reasons']
        if rejection_reasons:
            main_reason = max(rejection_reasons, key=rejection_reasons.get)
            recommendations.append(f"Основная причина отказов: {main_reason}. Рассмотрите корректировку алгоритма.")
        
        # Анализ центра тяжести
        cog = self._calculate_center_of_gravity()
        pallet_center_x = self.bins[0].width / 2
        pallet_center_y = self.bins[0].height / 2
        
        if abs(cog['x'] - pallet_center_x) > pallet_center_x * 0.2:
            recommendations.append("Центр тяжести смещен по X. Рассмотрите перераспределение веса.")
        
        if abs(cog['y'] - pallet_center_y) > pallet_center_y * 0.2:
            recommendations.append("Центр тяжести смещен по Y. Рассмотрите перераспределение веса.")
        
        return recommendations

    # Методы для обратной совместимости
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
        """Начать отсчет времени и мониторинг памяти"""
        self.start_time = time.time()
        process = psutil.Process(os.getpid())
        self.analytics['memory_usage_start'] = process.memory_info().rss

    def _end_timing(self):
        """Закончить отсчет времени и мониторинг памяти"""
        self.calculation_time = time.time() - self.start_time
        process = psutil.Process(os.getpid())
        self.analytics['memory_usage_peak'] = process.memory_info().rss

    def _initialize_packing(self):
        """Инициализация перед упаковкой"""
        if not self.bins or not self.items:
            return False
        
        self.unpacked_items = []
        self.packing_issues = []
        self.bins[0].items = []
        
        # Сброс аналитики
        self.analytics = {
            'placement_attempts': 0,
            'successful_placements': 0,
            'rotation_usage': {},
            'level_analysis': {},
            'support_quality_scores': [],
            'weight_distribution': {},
            'space_efficiency_by_level': {},
            'algorithm_iterations': 0,
            'memory_usage_start': 0,
            'memory_usage_peak': 0,
            'placement_timeline': [],
            'rejection_reasons': {},
            'orientation_preferences': {},
            'density_analysis': {}
        }
        
        return True