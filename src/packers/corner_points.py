from py3dbp import Packer

class CornerPointPacker(Packer):
    def __init__(self):
        super().__init__()
        self.unpacked_items = []
        self.packing_issues = []
        self.corner_points = []
        self.calculation_time = 0

    def pack(self):
        start_time = time.time()
        if not self.bins or not self.items:
            return

        self.unpacked_items = []
        self.packing_issues = []
        self.bins[0].items = []
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
                x, y, z = best_position
                item.position = [x, y, z]
                self.bins[0].items.append(item)
                self._update_corner_points(item)
            else:
                self.unpacked_items.append(item)
                self.packing_issues.append(f"Не удалось разместить {item.name}")

        end_time = time.time()
        self.calculation_time = end_time - start_time

    def _find_best_corner(self, item):
        best_position = None
        min_score = float('inf')
        w, h, d = item.width, item.height, item.depth
        
        for corner in self.corner_points:
            x, y, z = corner
            if self._can_place_item_at(x, y, z, w, h, d):
                score = self._evaluate_position(x, y, z, w, h, d)
                if score < min_score:
                    min_score = score
                    best_position = (x, y, z)
        return best_position

    def _can_place_item_at(self, x, y, z, width, height, depth):
        # Проверка границ контейнера
        if (x + width > self.bins[0].width or
            y + height > self.bins[0].height or
            z + depth > self.bins[0].depth):
            return False

        # Проверка пересечений
        for other in self.bins[0].items:
            if self._check_intersection(
                x, y, z, width, height, depth,
                other.position[0], other.position[1], other.position[2],
                other.width, other.height, other.depth
            ):
                return False

        # Проверка поддержки снизу
        if z > 0:
            support_area = 0
            required_support = width * height * 0.8
            for other in self.bins[0].items:
                if other.position[2] + other.depth == z:
                    x_overlap = max(0, min(x + width, other.position[0] + other.width) -
                                  max(x, other.position[0]))
                    y_overlap = max(0, min(y + height, other.position[1] + other.height) -
                                  max(y, other.position[1]))
                    support_area += x_overlap * y_overlap
            if support_area < required_support:
                return False
        return True

    def _check_intersection(self, x1, y1, z1, w1, h1, d1, x2, y2, z2, w2, h2, d2):
        return not (
            x1 + w1 <= x2 or x2 + w2 <= x1 or
            y1 + h1 <= y2 or y2 + h2 <= y1 or
            z1 + d1 <= z2 or z2 + d2 <= z1
        )

    def _evaluate_position(self, x, y, z, width, height, depth):
        # Оценка позиции: предпочитаем размещение ближе к углам и основанию
        distance_to_origin = ((x + width/2)**2 +
                            (y + height/2)**2 +
                            (z + depth/2)**2)**0.5
        # Штраф за высоту
        height_penalty = z * 2
        return distance_to_origin + height_penalty

    def _update_corner_points(self, item):
        x, y, z = item.position
        w, h, d = item.width, item.height, item.depth
        
        # Добавляем новые угловые точки
        new_points = [
            (x + w, y, z),     # правый передний нижний
            (x, y + h, z),     # левый задний нижний
            (x, y, z + d),     # левый передний верхний
            (x + w, y + h, z), # правый задний нижний
            (x + w, y, z + d), # правый передний верхний
            (x, y + h, z + d), # левый задний верхний
            (x + w, y + h, z + d) # правый задний верхний
        ]

        # Обновляем список точек
        self.corner_points.extend(new_points)
        self.corner_points = list(set(
            point for point in self.corner_points
            if self._is_valid_corner(point)
        ))
        # Сортируем точки по расстоянию от начала координат
        self.corner_points.sort(key=lambda p: (p[2], p[0]**2 + p[1]**2))

    def _is_valid_corner(self, point):
        x, y, z = point
        # Проверяем, что точка не внутри существующих предметов
        for item in self.bins[0].items:
            if (item.position[0] <= x < item.position[0] + item.width and
                item.position[1] <= y < item.position[1] + item.height and
                item.position[2] <= z < item.position[2] + item.depth):
                return False
        return True