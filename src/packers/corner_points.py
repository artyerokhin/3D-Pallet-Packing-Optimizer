# src/packers/corner_points.py

from .base_packer import BasePacker

class CornerPointPacker(BasePacker):
    def __init__(self):
        super().__init__()
        self.corner_points = []

    def pack(self):
        self._start_timing()
        if not self._initialize_packing():
            return

        self.corner_points = [(0, 0, 0)]  # Начальная точка

        # Сортировка по объему и компактности
        sorted_items = sorted(
            self.items,
            key=lambda x: (-(x.width * x.height * x.depth),
                          -(min(x.width, x.height) / max(x.width, x.height)))
        )

        for item in sorted_items:
            best_position = self._find_best_corner(item)
            if best_position:
                x, y, z, width, height, depth = best_position
                # Обновляем размеры предмета согласно выбранной ориентации
                item.width, item.height, item.depth = width, height, depth
                item.position = [x, y, z]
                self.bins[0].items.append(item)
                self._update_corner_points(item)
            else:
                self.unpacked_items.append(item)
                self.packing_issues.append(f"Не удалось разместить {item.name}")

        self._end_timing()

    def _find_best_corner(self, item):
        """Поиск лучшей угловой точки с учетом всех ориентаций"""
        best_position = None
        min_score = float('inf')
        
        for corner in self.corner_points:
            x, y, z = corner
            # Используем систему поворотов из базового класса
            orientation = self._can_place_item_with_rotation(item, x, y, z)
            if orientation:
                width, height, depth = orientation
                score = self._evaluate_position(x, y, z, width, height, depth)
                if score < min_score:
                    min_score = score
                    best_position = (x, y, z, width, height, depth)
        
        return best_position

    def _evaluate_position(self, x, y, z, width, height, depth):
        """Оценка позиции: предпочитаем размещение ближе к углам и основанию"""
        # Расстояние от начала координат с учетом центра предмета
        distance_to_origin = ((x + width/2)**2 + 
                             (y + height/2)**2 + 
                             (z + depth/2)**2)**0.5
        
        # Штраф за высоту (предпочитаем размещение ниже)
        height_penalty = z * 2
        
        # Бонус за компактность (предпочитаем заполнение углов)
        compactness_bonus = self._calculate_compactness_bonus(x, y, z, width, height, depth)
        
        # Штраф за расстояние от других предметов (предпочитаем плотную упаковку)
        isolation_penalty = self._calculate_isolation_penalty(x, y, z, width, height, depth)
        
        return distance_to_origin + height_penalty - compactness_bonus + isolation_penalty

    def _calculate_compactness_bonus(self, x, y, z, width, height, depth):
        """Расчет бонуса за компактность размещения"""
        # Бонус за размещение в углах контейнера
        corner_bonus = 0
        if x == 0:
            corner_bonus += 10
        if y == 0:
            corner_bonus += 10
        if z == 0:
            corner_bonus += 20  # Больший бонус за размещение на полу
        
        # Бонус за размещение вплотную к стенкам
        if x + width == self.bins[0].width:
            corner_bonus += 5
        if y + height == self.bins[0].height:
            corner_bonus += 5
        
        return corner_bonus

    def _calculate_isolation_penalty(self, x, y, z, width, height, depth):
        """Штраф за изолированное размещение"""
        if not self.bins[0].items:
            return 0
        
        min_distance = float('inf')
        for other in self.bins[0].items:
            # Расчет минимального расстояния до других предметов
            distance = self._calculate_distance_to_item(
                x, y, z, width, height, depth,
                other.position[0], other.position[1], other.position[2],
                other.width, other.height, other.depth
            )
            min_distance = min(min_distance, distance)
        
        # Штраф растет с увеличением расстояния
        return min_distance * 0.5

    def _calculate_distance_to_item(self, x1, y1, z1, w1, h1, d1, x2, y2, z2, w2, h2, d2):
        """Расчет расстояния между центрами двух предметов"""
        center1_x = x1 + w1 / 2
        center1_y = y1 + h1 / 2
        center1_z = z1 + d1 / 2
        
        center2_x = x2 + w2 / 2
        center2_y = y2 + h2 / 2
        center2_z = z2 + d2 / 2
        
        return ((center1_x - center2_x)**2 + 
                (center1_y - center2_y)**2 + 
                (center1_z - center2_z)**2)**0.5

    def _update_corner_points(self, item):
        """Обновление списка угловых точек после размещения предмета"""
        x, y, z = item.position
        w, h, d = item.width, item.height, item.depth

        # Добавляем новые угловые точки на основе размещенного предмета
        new_points = [
            (x + w, y, z),         # правый передний нижний
            (x, y + h, z),         # левый задний нижний
            (x, y, z + d),         # левый передний верхний
            (x + w, y + h, z),     # правый задний нижний
            (x + w, y, z + d),     # правый передний верхний
            (x, y + h, z + d),     # левый задний верхний
            (x + w, y + h, z + d)  # правый задний верхний
        ]

        # Добавляем точки от пересечений с другими предметами
        for other in self.bins[0].items:
            if other == item:
                continue
            
            # Добавляем точки пересечения проекций
            intersection_points = self._generate_intersection_points(item, other)
            new_points.extend(intersection_points)

        # Обновляем список точек, удаляя недействительные
        self.corner_points.extend(new_points)
        self.corner_points = list(set(
            point for point in self.corner_points
            if self._is_valid_corner(point)
        ))

        # Сортируем точки: сначала по высоте, затем по расстоянию от начала координат
        self.corner_points.sort(key=lambda p: (p[2], p[0]**2 + p[1]**2))

    def _generate_intersection_points(self, item1, item2):
        """Генерация точек пересечения между двумя предметами"""
        points = []
        
        # Координаты предметов
        x1, y1, z1 = item1.position
        w1, h1, d1 = item1.width, item1.height, item1.depth
        
        x2, y2, z2 = item2.position
        w2, h2, d2 = item2.width, item2.height, item2.depth
        
        # Генерируем точки на пересечениях проекций
        x_coords = [x1, x1 + w1, x2, x2 + w2]
        y_coords = [y1, y1 + h1, y2, y2 + h2]
        z_coords = [z1, z1 + d1, z2, z2 + d2]
        
        for x in x_coords:
            for y in y_coords:
                for z in z_coords:
                    # Проверяем, что точка не внутри существующих предметов
                    if not self._point_inside_any_item((x, y, z)):
                        points.append((x, y, z))
        
        return points

    def _is_valid_corner(self, point):
        """Проверка валидности угловой точки"""
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