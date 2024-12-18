from py3dbp import Packer
import time
import random

class ExtremePointPacker(Packer):
    def __init__(self):
        super().__init__()
        self.unpacked_items = []
        self.packing_issues = []
        self.extreme_points = []
        self.calculation_time = 0

    def pack(self):
        start_time = time.time()
        if not self.bins or not self.items:
            return

        self.unpacked_items = []
        self.packing_issues = []
        self.bins[0].items = []
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

        end_time = time.time()
        self.calculation_time = end_time - start_time

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

    def _can_place_item(self, item, x, y, z):
        if (x + item.width > self.bins[0].width or
            y + item.height > self.bins[0].height or
            z + item.depth > self.bins[0].depth):
            return False

        for other in self.bins[0].items:
            if self._check_intersection(item, other, x, y, z):
                return False

        if z > 0:
            support_area = 0
            required_support = item.width * item.height * 0.7
            for other in self.bins[0].items:
                if other.position[2] + other.depth == z:
                    x_overlap = max(0, min(x + item.width, other.position[0] + other.width) -
                                  max(x, other.position[0]))
                    y_overlap = max(0, min(y + item.height, other.position[1] + other.height) -
                                  max(y, other.position[1]))
                    support_area += x_overlap * y_overlap
            if support_area < required_support:
                return False
        return True

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

    def _check_intersection(self, item, other, x, y, z):
        return not (
            x + item.width <= other.position[0] or
            other.position[0] + other.width <= x or
            y + item.height <= other.position[1] or
            other.position[1] + other.height <= y or
            z + item.depth <= other.position[2] or
            other.position[2] + other.depth <= z
        )

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