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
                x, y, z = best_position
                item.position = [x, y, z]
                self.bins[0].items.append(item)
                self._update_corner_points(item)
            else:
                self.unpacked_items.append(item)
                self.packing_issues.append(f"Не удалось разместить {item.name}")

        self._end_timing()

    def _find_best_corner(self, item):
        best_position = None
        min_score = float('inf')

        for corner in self.corner_points:
            x, y, z = corner
            if self._can_place_item(item, x, y, z):
                score = self._evaluate_position(x, y, z, item.width, item.height, item.depth)
                if score < min_score:
                    min_score = score
                    best_position = (x, y, z)

        return best_position

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
            (x + w, y, z),      # правый передний нижний
            (x, y + h, z),      # левый задний нижний
            (x, y, z + d),      # левый передний верхний
            (x + w, y + h, z),  # правый задний нижний
            (x + w, y, z + d),  # правый передний верхний
            (x, y + h, z + d),  # левый задний верхний
            (x + w, y + h, z + d)  # правый задний верхний
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