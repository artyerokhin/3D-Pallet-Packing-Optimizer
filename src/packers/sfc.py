from py3dbp import Packer
import time

class SFCPacker(Packer):
    def __init__(self):
        super().__init__()
        self.unpacked_items = []
        self.packing_issues = []
        self.grid_size = 10  # Размер сетки для дискретизации пространства
        self.calculation_time = 0

    def pack(self):
        start_time = time.time()
        if not self.bins or not self.items:
            return

        self.unpacked_items = []
        self.packing_issues = []
        self.bins[0].items = []

        # Сортировка по весу и объему
        sorted_items = sorted(
            self.items,
            key=lambda x: (-x.weight, -(x.width * x.height * x.depth))
        )

        # Заполняем пространство по спиральной кривой
        for item in sorted_items:
            placed = False
            for z in range(0, self.bins[0].depth - item.depth + 1, self.grid_size):
                if placed:
                    break
                for spiral_pos in self._get_spiral_positions():
                    x, y = spiral_pos
                    if self._can_place_item(item, x, y, z):
                        item.position = [x, y, z]
                        self.bins[0].items.append(item)
                        placed = True
                        break

            if not placed:
                self.unpacked_items.append(item)
                self.packing_issues.append(f"Не удалось разместить {item.name}")

        end_time = time.time()
        self.calculation_time = end_time - start_time

    def _get_spiral_positions(self):
        """Генерирует позиции по спиральной кривой"""
        positions = []
        max_dim = max(self.bins[0].width, self.bins[0].height)
        x = y = 0
        dx = 0
        dy = -self.grid_size
        
        for _ in range(max_dim * max_dim):
            if (-max_dim/2 < x <= max_dim/2) and (-max_dim/2 < y <= max_dim/2):
                if 0 <= x < self.bins[0].width and 0 <= y < self.bins[0].height:
                    positions.append((x, y))
            if x == y or (x < 0 and x == -y) or (x > 0 and x == 1-y):
                dx, dy = -dy, dx
            x += dx
            y += dy
        return positions

    def _can_place_item(self, item, x, y, z):
        """Проверяет возможность размещения предмета"""
        # Проверка границ контейнера
        if (x + item.width > self.bins[0].width or
            y + item.height > self.bins[0].height or
            z + item.depth > self.bins[0].depth):
            return False

        # Проверка пересечений
        for other in self.bins[0].items:
            if (x < other.position[0] + other.width and
                x + item.width > other.position[0] and
                y < other.position[1] + other.height and
                y + item.height > other.position[1] and
                z < other.position[2] + other.depth and
                z + item.depth > other.position[2]):
                return False

        # Проверка поддержки снизу и веса
        if z > 0:
            support_area = 0
            required_support = item.width * item.height * 0.8
            supporting_boxes = []
            
            for other in self.bins[0].items:
                if abs(other.position[2] + other.depth - z) < 0.1:
                    x_overlap = max(0, min(x + item.width, other.position[0] + other.width) -
                                  max(x, other.position[0]))
                    y_overlap = max(0, min(y + item.height, other.position[1] + other.height) -
                                  max(y, other.position[1]))
                    if x_overlap > 0 and y_overlap > 0:
                        if other.weight < item.weight:
                            return False
                        supporting_boxes.append(other)
                        support_area += x_overlap * y_overlap
                        
            if support_area < required_support:
                return False

        return True