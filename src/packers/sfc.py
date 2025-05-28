from .base_packer import BasePacker
import math

class SFCPacker(BasePacker):
    def __init__(self):
        super().__init__()
        self.grid_size = 15

    def pack(self):
        self._start_timing()
        if not self._initialize_packing():
            return

        sorted_items = sorted(
            self.items,
            key=lambda x: (-x.weight, -(x.width * x.height * x.depth))
        )

        for item in sorted_items:
            best_position = self._find_spiral_position_safe(item)
            if best_position:
                x, y, z, width, height, depth = best_position
                item.width, item.height, item.depth = width, height, depth
                item.position = [x, y, z]
                self.bins[0].items.append(item)
            else:
                self.unpacked_items.append(item)
                self.packing_issues.append(f"Не удалось разместить {item.name}")

        self._end_timing()

    def _find_spiral_position_safe(self, item):
        best_position = None
        min_height = float('inf')

        for x, y in self._get_spiral_positions():
            for width, height, depth in self._get_item_orientations(item):
                if self._can_place_item_safe(item, width, height, depth, x, y, 0):
                    return (x, y, 0, width, height, depth)

        for other in self.bins[0].items:
            z = other.position[2] + other.depth
            if z < self.bins[0].depth:
                surface_positions = [
                    (other.position[0], other.position[1], z),
                    (other.position[0] + other.width, other.position[1], z),
                    (other.position[0], other.position[1] + other.height, z),
                    (other.position[0] + other.width, other.position[1] + other.height, z)
                ]

                for x, y, z in surface_positions:
                    for width, height, depth in self._get_item_orientations(item):
                        if (x + width <= self.bins[0].width and
                            y + height <= self.bins[0].height and
                            z + depth <= self.bins[0].depth and
                            self._can_place_item_safe(item, width, height, depth, x, y, z)):
                            if z < min_height:
                                min_height = z
                                best_position = (x, y, z, width, height, depth)

        return best_position

    def _can_place_item_safe(self, item, width, height, depth, x, y, z):
        if (x + width > self.bins[0].width or
            y + height > self.bins[0].height or
            z + depth > self.bins[0].depth):
            return False

        for other in self.bins[0].items:
            if self._check_intersection_orientation(
                x, y, z, width, height, depth,
                other.position[0], other.position[1], other.position[2],
                other.width, other.height, other.depth
            ):
                return False

        if z > 0:
            return self._check_support_orientation(width, height, depth, x, y, z, 0.5)

        if not self._check_weight_limit(item.weight):
            return False

        return True

    def _get_spiral_positions(self):
        positions = []
        center_x = int(self.bins[0].width // 2)
        center_y = int(self.bins[0].height // 2)

        positions.append((center_x, center_y))

        max_radius = int(min(center_x, center_y))

        for radius in range(self.grid_size, max_radius, self.grid_size):
            circumference = 2 * math.pi * radius
            num_points = max(8, int(circumference / self.grid_size))

            for i in range(num_points):
                angle = 2 * math.pi * i / num_points
                x = int(center_x + radius * math.cos(angle))
                y = int(center_y + radius * math.sin(angle))

                if (0 <= x < int(self.bins[0].width) and
                    0 <= y < int(self.bins[0].height)):
                    positions.append((x, y))

        corner_positions = [
            (0, 0),
            (int(self.bins[0].width) - self.grid_size, 0),
            (0, int(self.bins[0].height) - self.grid_size),
            (int(self.bins[0].width) - self.grid_size, int(self.bins[0].height) - self.grid_size)
        ]

        for x, y in corner_positions:
            if (x, y) not in positions and x >= 0 and y >= 0:
                positions.append((x, y))

        for x in range(0, int(self.bins[0].width), self.grid_size * 2):
            for y in range(0, int(self.bins[0].height), self.grid_size * 2):
                if (x, y) not in positions:
                    positions.append((x, y))

        return positions