from py3dbp import Packer
import time

class WeightAwarePacker(Packer):
    def __init__(self):
        super().__init__()
        self.unpacked_items = []
        self.packing_issues = []
        self.calculation_time = 0

    def pack(self):
        start_time = time.time()
        if not self.bins or not self.items:
            return

        self.unpacked_items = []
        self.packing_issues = []
        self.bins[0].items = []

        # Сортировка по весу и площади основания
        sorted_items = sorted(
            self.items,
            key=lambda x: (-x.weight, -(x.width * x.height))
        )

        for item in sorted_items:
            packed = False
            for z in range(0, self.bins[0].depth):
                if packed:
                    break
                for x in range(0, self.bins[0].width - item.width + 1):
                    if packed:
                        break
                    for y in range(0, self.bins[0].height - item.height + 1):
                        if self._can_place_item(item, x, y, z):
                            item.position = [x, y, z]
                            self.bins[0].items.append(item)
                            packed = True
                            break

            if not packed:
                self.unpacked_items.append(item)
                self.packing_issues.append(f"Не удалось разместить {item.name}")

        end_time = time.time()
        self.calculation_time = end_time - start_time

    def _can_place_item(self, item, x, y, z):
        # Проверка границ контейнера
        if (x + item.width > self.bins[0].width or
            y + item.height > self.bins[0].height or
            z + item.depth > self.bins[0].depth):
            return False

        # Проверка пересечений
        for other in self.bins[0].items:
            if self._check_intersection(item, other, x, y, z):
                return False

        # Проверка поддержки снизу
        if z > 0:
            has_support = False
            total_support_area = 0
            required_support_area = item.width * item.height * 0.8

            for other in self.bins[0].items:
                support_area = self._get_support_area(other, x, y, z, item)
                if support_area > 0:
                    if other.weight < item.weight:
                        return False
                    total_support_area += support_area

            has_support = total_support_area >= required_support_area
            if not has_support:
                return False

        return True

    def _check_intersection(self, item, other, x, y, z):
        return not (
            x + item.width <= other.position[0] or
            other.position[0] + other.width <= x or
            y + item.height <= other.position[1] or
            other.position[1] + other.height <= y or
            z + item.depth <= other.position[2] or
            other.position[2] + other.depth <= z
        )

    def _get_support_area(self, bottom_item, x, y, z, top_item):
        if bottom_item.position[2] + bottom_item.depth != z:
            return 0

        x1 = max(bottom_item.position[0], x)
        y1 = max(bottom_item.position[1], y)
        x2 = min(bottom_item.position[0] + bottom_item.width, x + top_item.width)
        y2 = min(bottom_item.position[1] + bottom_item.height, y + top_item.height)

        if x1 < x2 and y1 < y2:
            return (x2 - x1) * (y2 - y1)
        return 0