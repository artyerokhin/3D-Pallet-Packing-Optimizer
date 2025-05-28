from .base_packer import BasePacker

class WeightAwarePacker(BasePacker):
    def __init__(self, support_threshold=0.8, weight_check_enabled=True):
        super().__init__()
        self.grid_step = 15
        self.support_threshold = support_threshold
        self.weight_check_enabled = weight_check_enabled

    def pack(self):
        self._start_timing()
        if not self._initialize_packing():
            return

        sorted_items = sorted(
            self.items,
            key=lambda x: (-x.weight, -(x.width * x.height))
        )

        for item in sorted_items:
            best_position = self._find_best_position_safe(item)
            if best_position:
                x, y, z, width, height, depth = best_position
                item.width, item.height, item.depth = width, height, depth
                item.position = [x, y, z]
                self.bins[0].items.append(item)
            else:
                self.unpacked_items.append(item)
                self.packing_issues.append(f"Не удалось разместить {item.name}")

        self._end_timing()

    def _find_best_position_safe(self, item):
        best_position = None
        min_height = float('inf')

        candidates = self._generate_position_candidates()

        for x, y, z in candidates:
            for width, height, depth in self._get_item_orientations(item):
                if self._can_place_item_safe(item, width, height, depth, x, y, z):
                    if z < min_height:
                        min_height = z
                        best_position = (x, y, z, width, height, depth)
                    if z == 0:
                        return best_position

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
            if not self._check_support_safe(item, width, height, depth, x, y, z):
                return False

        if not self._check_weight_limit(item.weight):
            return False

        return True

    def _check_support_safe(self, item, width, height, depth, x, y, z):
        total_support_area = 0
        required_support_area = width * height * self.support_threshold

        supporting_items = []

        for other in self.bins[0].items:
            if abs(other.position[2] + other.depth - z) < 0.1:
                support_area = self._calculate_overlap_area_orientation(
                    other.position[0], other.position[1], other.width, other.height,
                    x, y, width, height
                )

                if support_area > 0:
                    if self.weight_check_enabled and other.weight < item.weight * 0.8:
                        return False

                    total_support_area += support_area
                    supporting_items.append(other)

        if total_support_area < required_support_area:
            return False

        if self.support_threshold > 0.7:
            return self._check_edge_support(width, height, x, y, z, supporting_items)

        return True

    def _check_edge_support(self, width, height, x, y, z, supporting_items):
        corners = [
            (x, y),
            (x + width, y),
            (x, y + height),
            (x + width, y + height)
        ]

        supported_corners = 0

        for corner_x, corner_y in corners:
            for other in supporting_items:
                if (other.position[0] <= corner_x <= other.position[0] + other.width and
                    other.position[1] <= corner_y <= other.position[1] + other.height):
                    supported_corners += 1
                    break

        return supported_corners >= 2

    def _generate_position_candidates(self):
        candidates = []

        for x in range(0, int(self.bins[0].width), self.grid_step):
            for y in range(0, int(self.bins[0].height), self.grid_step):
                candidates.append((x, y, 0))

        for other in self.bins[0].items:
            z = other.position[2] + other.depth
            if z < self.bins[0].depth:
                corner_positions = [
                    (other.position[0], other.position[1], z),
                    (other.position[0] + other.width, other.position[1], z),
                    (other.position[0], other.position[1] + other.height, z),
                    (other.position[0] + other.width, other.position[1] + other.height, z)
                ]

                for x, y, z in corner_positions:
                    if (0 <= x < self.bins[0].width and
                        0 <= y < self.bins[0].height):
                        candidates.append((x, y, z))

        candidates.sort(key=lambda pos: (pos[2], pos[0] + pos[1]))
        return list(set(candidates))