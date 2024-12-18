from py3dbp import Packer

class StabilityAwarePacker(Packer):
    def __init__(self):
        super().__init__()
        self.stability_tolerance = 0.25  # Базовое отклонение 25%
        self.height_factor = 0.5  # Коэффициент влияния высоты
        self.items_factor = 0.02  # Коэффициент влияния количества предметов
        self.max_deviation = 0.4  # Максимальное допустимое отклонение 40%

    def calculate_cog(self):
        if not self.bins or not self.bins[0].items:
            return None
            
        total_weight = sum(item.weight for item in self.bins[0].items)
        if total_weight == 0:
            return None
            
        cog = {
            'x': sum(item.weight * (item.position[0] + item.width/2) 
                    for item in self.bins[0].items) / total_weight,
            'y': sum(item.weight * (item.position[1] + item.height/2) 
                    for item in self.bins[0].items) / total_weight,
            'z': sum(item.weight * (item.position[2] + item.depth/2) 
                    for item in self.bins[0].items) / total_weight
        }
        return cog

    def _check_stability(self, item, x, y, z):
        # Временно размещаем предмет
        original_position = item.position
        item.position = [x, y, z]
        self.bins[0].items.append(item)
        
        # Адаптивный расчет допустимого отклонения
        total_items = len(self.bins[0].items)
        current_deviation = self.stability_tolerance
        
        # Учитываем количество предметов
        if total_items > 10:
            items_adjustment = (total_items - 10) * self.items_factor
            current_deviation *= (1 + items_adjustment)
        
        # Учитываем высоту размещения
        if z > 0:
            height_adjustment = (z / self.bins[0].depth) * self.height_factor
            current_deviation *= (1 + height_adjustment)
        
        # Увеличиваем допуск для больших наборов коробок
        if total_items > 30:
            current_deviation *= 1.5
            
        # Ограничиваем максимальное отклонение
        current_deviation = min(current_deviation, self.max_deviation)
        
        # Проверяем стабильность
        cog = self.calculate_cog()
        is_stable = True
        if cog:
            pallet_center_x = self.bins[0].width / 2
            pallet_center_y = self.bins[0].height / 2
            max_deviation = min(self.bins[0].width, self.bins[0].height) * current_deviation
            
            is_stable = (abs(cog['x'] - pallet_center_x) <= max_deviation and 
                        abs(cog['y'] - pallet_center_y) <= max_deviation)
        
        # Возвращаем состояние
        self.bins[0].items.remove(item)
        item.position = original_position
        
        return is_stable