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

        sorted_items = sorted(
            self.items,
            key=lambda x: (-(x.width * x.height * x.depth) * (0.9 + 0.2 * random.random()))
        )

        for item in sorted_items:
            best_fit = self._find_best_fit(item)
            if best_fit:
                x, y, z = best_fit
                item.position = [x, y, z]
                self.bins[0].items.append(item)
                self._update_extreme_points(item)
            else:
                self.unpacked_items.append(item)
                self.packing_issues.append(f"Не удалось разместить {item.name}")

        self._end_timing()

    def _find_best_fit(self, item):
        best_position = None
        min_waste = float('inf')

        for ep in self.extreme_points:
            x, y, z = ep
            if self._can_place_item(item, x, y, z):
                waste = self._evaluate_waste(item, x, y, z)
                if waste < min_waste:
                    min_waste = waste
                    best_position = (x, y, z)

        return best_position

    def _evaluate_waste(self, item, x, y, z):
        total_waste = 0
        total_waste += (x + y + z) / (self.bins[0].width + self.bins[0].height + self.bins[0].depth)

        min_distance_to_items = float('inf')
        for other in self.bins[0].items:
            dist = ((x - other.position[0])**2 +
                   (y - other.position[1])**2 +
                   (z - other.position[2])**2)**0.5
            min_distance_to_items = min(min_distance_to_items, dist)

        if min_distance_to_items != float('inf'):
            total_waste += min_distance_to_items / (self.bins[0].width + self.bins[0].height + self.bins[0].depth)

        return total_waste

    def _update_extreme_points(self, item):
        x, y, z = item.position

        new_points = [
            (x + item.width, y, z),
            (x, y + item.height, z),
            (x, y, z + item.depth),
            (x + item.width, y + item.height, z),
            (x + item.width, y, z + item.depth),
            (x, y + item.height, z + item.depth),
            (x + item.width, y + item.height, z + item.depth)
        ]

        self.extreme_points.extend(new_points)
        self.extreme_points = list(set(
            ep for ep in self.extreme_points
            if not self._point_inside_any_item(ep)
        ))
        self.extreme_points.sort(key=lambda p: (p[2], p[0]**2 + p[1]**2))

    def _point_inside_any_item(self, point):
        x, y, z = point
        for item in self.bins[0].items:
            if (item.position[0] <= x < item.position[0] + item.width and
                item.position[1] <= y < item.position[1] + item.height and
                item.position[2] <= z < item.position[2] + item.depth):
                return True
        return False