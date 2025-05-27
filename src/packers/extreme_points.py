# src/packers/extreme_points.py

from .base_packer import BasePacker
import random

class ExtremePointPacker(BasePacker):
    def __init__(self):
        super().__init__()
        self.extreme_points = []

    def pack(self):
        self._start_timing()
        if not self._initialize_packing():
            return

        self.extreme_points = [(0, 0, 0)]

        # Сортировка с небольшим случайным фактором для разнообразия
        sorted_items = sorted(
            self.items,
            key=lambda x: (-(x.width * x.height * x.depth) * (0.9 + 0.2 * random.random()))
        )

        for item in sorted_items:
            best_fit = self._find_best_fit(item)
            if best_fit:
                x, y, z, width, height, depth = best_fit
                # Обновляем размеры предмета согласно выбранной ориентации
                item.width, item.height, item.depth = width, height, depth
                item.position = [x, y, z]
                self.bins[0].items.append(item)
                self._update_extreme_points(item)
            else:
                self.unpacked_items.append(item)
                self.packing_issues.append(f"Не удалось разместить {item.name}")

        self._end_timing()

    def _find_best_fit(self, item):
        """Поиск лучшей экстремальной точки с учетом всех ориентаций"""
        best_position = None
        min_waste = float('inf')
        
        for ep in self.extreme_points:
            x, y, z = ep
            # Используем систему поворотов из базового класса
            orientation = self._can_place_item_with_rotation(item, x, y, z)
            if orientation:
                width, height, depth = orientation
                waste = self._evaluate_waste(item, x, y, z, width, height, depth)
                if waste < min_waste:
                    min_waste = waste
                    best_position = (x, y, z, width, height, depth)
        
        return best_position

    def _evaluate_waste(self, item, x, y, z, width, height, depth):
        """Улучшенная оценка потерь пространства"""
        total_waste = 0
        
        # Нормализованное расстояние от начала координат
        position_penalty = (x + y + z) / (self.bins[0].width + self.bins[0].height + self.bins[0].depth)
        total_waste += position_penalty * 0.3
        
        # Штраф за высоту (предпочитаем размещение ниже)
        height_penalty = z / self.bins[0].depth
        total_waste += height_penalty * 0.4
        
        # Расчет плотности упаковки
        density_bonus = self._calculate_density_bonus(x, y, z, width, height, depth)
        total_waste -= density_bonus * 0.2
        
        # Расчет эффективности использования пространства
        space_efficiency = self._calculate_space_efficiency(x, y, z, width, height, depth)
        total_waste -= space_efficiency * 0.1
        
        return total_waste

    def _calculate_density_bonus(self, x, y, z, width, height, depth):
        """Расчет бонуса за плотность упаковки"""
        if not self.bins[0].items:
            return 0
        
        contact_area = 0
        max_contact = width * height + width * depth + height * depth
        
        for other in self.bins[0].items:
            # Расчет площади контакта с другими предметами
            contact_area += self._calculate_contact_area(
                x, y, z, width, height, depth,
                other.position[0], other.position[1], other.position[2],
                other.width, other.height, other.depth
            )
        
        return contact_area / max_contact if max_contact > 0 else 0

    def _calculate_contact_area(self, x1, y1, z1, w1, h1, d1, x2, y2, z2, w2, h2, d2):
        """Расчет площади контакта между двумя предметами"""
        contact_area = 0
        
        # Контакт по X-плоскости
        if abs((x1 + w1) - x2) < 0.1 or abs(x1 - (x2 + w2)) < 0.1:
            y_overlap = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
            z_overlap = max(0, min(z1 + d1, z2 + d2) - max(z1, z2))
            contact_area += y_overlap * z_overlap
        
        # Контакт по Y-плоскости
        if abs((y1 + h1) - y2) < 0.1 or abs(y1 - (y2 + h2)) < 0.1:
            x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
            z_overlap = max(0, min(z1 + d1, z2 + d2) - max(z1, z2))
            contact_area += x_overlap * z_overlap
        
        # Контакт по Z-плоскости
        if abs((z1 + d1) - z2) < 0.1 or abs(z1 - (z2 + d2)) < 0.1:
            x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
            y_overlap = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
            contact_area += x_overlap * y_overlap
        
        return contact_area

    def _calculate_space_efficiency(self, x, y, z, width, height, depth):
        """Расчет эффективности использования пространства"""
        # Бонус за заполнение углов и краев
        edge_bonus = 0
        
        if x == 0:
            edge_bonus += 0.1
        if y == 0:
            edge_bonus += 0.1
        if z == 0:
            edge_bonus += 0.2  # Больший бонус за размещение на полу
        
        if x + width == self.bins[0].width:
            edge_bonus += 0.1
        if y + height == self.bins[0].height:
            edge_bonus += 0.1
        if z + depth == self.bins[0].depth:
            edge_bonus += 0.1
        
        return edge_bonus

    def _update_extreme_points(self, item):
        """Обновление экстремальных точек после размещения предмета"""
        x, y, z = item.position
        w, h, d = item.width, item.height, item.depth

        # Генерируем новые экстремальные точки на основе размещенного предмета
        new_points = [
            (x + w, y, z),         # правая грань
            (x, y + h, z),         # задняя грань
            (x, y, z + d),         # верхняя грань
            (x + w, y + h, z),     # правый задний угол
            (x + w, y, z + d),     # правый верхний угол
            (x, y + h, z + d),     # задний верхний угол
            (x + w, y + h, z + d)  # правый задний верхний угол
        ]

        # Добавляем точки от проекций на другие предметы
        projection_points = self._generate_projection_points(item)
        new_points.extend(projection_points)

        # Обновляем список экстремальных точек
        self.extreme_points.extend(new_points)
        
        # Удаляем точки, которые больше не являются экстремальными
        self.extreme_points = list(set(
            ep for ep in self.extreme_points
            if self._is_valid_extreme_point(ep)
        ))

        # Сортируем точки: сначала по высоте, затем по расстоянию от начала координат
        self.extreme_points.sort(key=lambda p: (p[2], p[0]**2 + p[1]**2))

    def _generate_projection_points(self, item):
        """Генерация точек проекций согласно алгоритму Extreme Points"""
        projection_points = []
        
        x, y, z = item.position
        w, h, d = item.width, item.height, item.depth
        
        for other in self.bins[0].items:
            if other == item:
                continue
            
            ox, oy, oz = other.position
            ow, oh, od = other.width, other.height, other.depth
            
            # Проекции согласно алгоритму из статьи
            # Yx - проекция Y координаты item на X координату other
            if self._can_take_projection(item, other, 'YX'):
                projection_points.append((ox + ow, y + h, z))
            
            # Yz - проекция Y координаты item на Z координату other
            if self._can_take_projection(item, other, 'YZ'):
                projection_points.append((x, y + h, oz + od))
            
            # Xy - проекция X координаты item на Y координату other
            if self._can_take_projection(item, other, 'XY'):
                projection_points.append((x + w, oy + oh, z))
            
            # Xz - проекция X координаты item на Z координату other
            if self._can_take_projection(item, other, 'XZ'):
                projection_points.append((x + w, y, oz + od))
            
            # Zx - проекция Z координаты item на X координату other
            if self._can_take_projection(item, other, 'ZX'):
                projection_points.append((ox + ow, y, z + d))
            
            # Zy - проекция Z координаты item на Y координату other
            if self._can_take_projection(item, other, 'ZY'):
                projection_points.append((x, oy + oh, z + d))
        
        return projection_points

    def _can_take_projection(self, item, other, projection_type):
        """Проверка валидности проекции согласно алгоритму Extreme Points"""
        x, y, z = item.position
        w, h, d = item.width, item.height, item.depth
        
        ox, oy, oz = other.position
        ow, oh, od = other.width, other.height, other.depth
        
        # Проверяем, что проекция касается размещенного предмета (item)
        if projection_type == 'YX':
            return (y <= oy + oh and y + h >= oy and z <= oz + od and z + d >= oz)
        elif projection_type == 'YZ':
            return (y <= oy + oh and y + h >= oy and x <= ox + ow and x + w >= ox)
        elif projection_type == 'XY':
            return (x <= ox + ow and x + w >= ox and z <= oz + od and z + d >= oz)
        elif projection_type == 'XZ':
            return (x <= ox + ow and x + w >= ox and y <= oy + oh and y + h >= oy)
        elif projection_type == 'ZX':
            return (z <= oz + od and z + d >= oz and y <= oy + oh and y + h >= oy)
        elif projection_type == 'ZY':
            return (z <= oz + od and z + d >= oz and x <= ox + ow and x + w >= ox)
        
        return False

    def _is_valid_extreme_point(self, point):
        """Проверка валидности экстремальной точки"""
        x, y, z = point
        
        # Проверяем границы контейнера
        if (x < 0 or x >= self.bins[0].width or
            y < 0 or y >= self.bins[0].height or
            z < 0 or z >= self.bins[0].depth):
            return False
        
        # Проверяем, что точка не внутри существующих предметов
        return not self._point_inside_any_item(point)

    def _point_inside_any_item(self, point):
        """Проверка, находится ли точка внутри какого-либо предмета"""
        x, y, z = point
        for item in self.bins[0].items:
            if (item.position[0] < x < item.position[0] + item.width and
                item.position[1] < y < item.position[1] + item.height and
                item.position[2] < z < item.position[2] + item.depth):
                return True
        return False