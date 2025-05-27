# src/packers/laff.py

from .base_packer import BasePacker

class LAFFPacker(BasePacker):
    def __init__(self):
        super().__init__()
        self.levels = []

    def pack(self):
        self._start_timing()
        if not self._initialize_packing():
            return

        # Сортируем предметы по площади основания и высоте
        sorted_items = sorted(
            self.items,
            key=lambda x: (-x.width * x.height, -x.depth)
        )

        current_level_height = 0
        remaining_height = self.bins[0].depth

        while sorted_items and remaining_height > 0:
            level_items = []
            current_level_items = []
            max_level_height = 0

            # Находим предметы для текущего уровня
            for item in sorted_items[:]:
                if item.depth <= remaining_height:
                    level_items.append(item)

            if not level_items:
                break

            # Размещаем предметы на текущем уровне
            level_width = self.bins[0].width
            level_height = self.bins[0].height

            # Пытаемся разместить каждый предмет
            for item in level_items:
                best_position = self._find_best_position(
                    item,
                    current_level_height,
                    current_level_items,
                    level_width,
                    level_height
                )

                if best_position:
                    x, y = best_position
                    item.position = [x, y, current_level_height]
                    self.bins[0].items.append(item)
                    current_level_items.append(item)
                    sorted_items.remove(item)
                    max_level_height = max(max_level_height, item.depth)

            if not current_level_items:
                break

            # Обновляем высоту и переходим к следующему уровню
            current_level_height += max_level_height
            remaining_height -= max_level_height
            self.levels.append(current_level_height)

        # Добавляем оставшиеся предметы в список неупакованных
        self.unpacked_items.extend(sorted_items)
        for item in sorted_items:
            self.packing_issues.append(f"Не удалось разместить {item.name}")

        self._end_timing()

    def _find_best_position(self, item, level_height, placed_items, max_width, max_height):
        best_position = None
        min_waste = float('inf')

        # Создаем сетку возможных позиций
        positions = [(0, 0)]
        for placed_item in placed_items:
            positions.append((placed_item.position[0] + placed_item.width, placed_item.position[1]))
            positions.append((placed_item.position[0], placed_item.position[1] + placed_item.height))

        # Проверяем каждую возможную позицию
        for x, y in positions:
            if self._can_place_item_level(item, x, y, level_height, placed_items, max_width, max_height):
                waste = self._calculate_waste(item, x, y, placed_items)
                if waste < min_waste:
                    min_waste = waste
                    best_position = (x, y)

        return best_position

    def _can_place_item_level(self, item, x, y, z, placed_items, max_width, max_height):
        # Проверка границ контейнера
        if (x + item.width > max_width or
            y + item.height > max_height):
            return False

        # Проверка пересечений с предметами на том же уровне
        for other in placed_items:
            if (x < other.position[0] + other.width and
                x + item.width > other.position[0] and
                y < other.position[1] + other.height and
                y + item.height > other.position[1]):
                return False

        # Используем базовую проверку поддержки только если не на полу
        if z > 0:
            return self._check_support(item, x, y, z)

        return True

    def _calculate_waste(self, item, x, y, placed_items):
        # Считаем площадь контакта с другими предметами
        contact_area = 0
        for other in placed_items:
            # Контакт по X
            if (y < other.position[1] + other.height and
                y + item.height > other.position[1]):
                if x + item.width == other.position[0] or x == other.position[0] + other.width:
                    contact_area += min(item.height, other.height)
            
            # Контакт по Y
            if (x < other.position[0] + other.width and
                x + item.width > other.position[0]):
                if y + item.height == other.position[1] or y == other.position[1] + other.height:
                    contact_area += min(item.width, other.width)
        
        # ИСПРАВЛЕНО: добавлен return
        return -contact_area