import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidationErrorType(Enum):
    DIMENSION_ERROR = "dimension_error"
    WEIGHT_ERROR = "weight_error"
    DENSITY_ERROR = "density_error"
    QUANTITY_ERROR = "quantity_error"
    PALLET_ERROR = "pallet_error"
    DATA_TYPE_ERROR = "data_type_error"
    COMPATIBILITY_ERROR = "compatibility_error"

@dataclass
class ValidationError:
    error_type: ValidationErrorType
    message: str
    field: str
    value: Any
    suggestion: Optional[str] = None

class ValidationResult:
    def __init__(self):
        self.is_valid = True
        self.errors: List[ValidationError] = []
        self.warnings: List[str] = []

    def add_error(self, error: ValidationError):
        self.is_valid = False
        self.errors.append(error)
        logger.error(f"Validation error: {error.message}")

    def add_warning(self, warning: str):
        self.warnings.append(warning)
        logger.warning(f"Validation warning: {warning}")

class ValidationConfig:
    MIN_DIMENSION = 0.1
    MAX_DIMENSION = 500.0
    MIN_WEIGHT = 0.01
    MAX_WEIGHT = 1000.0
    MIN_DENSITY = 0.01
    MAX_DENSITY = 10.0
    MIN_PALLET_DIMENSION = 50.0
    MAX_PALLET_DIMENSION = 300.0
    MIN_PALLET_HEIGHT = 10.0
    MAX_PALLET_HEIGHT = 500.0
    MIN_PALLET_CAPACITY = 100.0
    MAX_PALLET_CAPACITY = 5000.0
    MAX_BOXES_COUNT = 1000
    MIN_BOXES_COUNT = 1
    STANDARD_PALLET_SIZES = [
        (80, 120),
        (100, 120),
        (120, 120),
        (100, 100),
    ]

class DataValidator:
    def __init__(self, config: ValidationConfig = None):
        self.config = config or ValidationConfig()

    def validate_box_data(self, box_data: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()
        required_fields = ['length', 'width', 'height', 'weight']
        for field in required_fields:
            if field not in box_data or box_data[field] is None:
                result.add_error(ValidationError(
                    ValidationErrorType.DATA_TYPE_ERROR,
                    f"Отсутствует обязательное поле: {field}",
                    field,
                    None,
                    f"Добавьте поле {field} с числовым значением"
                ))
                continue
            try:
                value = float(box_data[field])
                if np.isnan(value) or np.isinf(value):
                    raise ValueError("Недопустимое числовое значение")
                box_data[field] = value
            except (ValueError, TypeError):
                result.add_error(ValidationError(
                    ValidationErrorType.DATA_TYPE_ERROR,
                    f"Поле {field} должно быть числом",
                    field,
                    box_data[field],
                    "Введите числовое значение (например: 30.5)"
                ))
                continue
        if not result.is_valid:
            return result

        # Размеры
        for dim_field in ['length', 'width', 'height']:
            value = box_data[dim_field]
            if value <= 0:
                result.add_error(ValidationError(
                    ValidationErrorType.DIMENSION_ERROR,
                    f"{dim_field.capitalize()} должна быть положительной",
                    dim_field,
                    value,
                    f"Введите значение больше 0"
                ))
            elif value < self.config.MIN_DIMENSION:
                result.add_error(ValidationError(
                    ValidationErrorType.DIMENSION_ERROR,
                    f"{dim_field.capitalize()} слишком мала (минимум {self.config.MIN_DIMENSION} см)",
                    dim_field,
                    value,
                    f"Увеличьте до {self.config.MIN_DIMENSION} см или больше"
                ))
            elif value > self.config.MAX_DIMENSION:
                result.add_error(ValidationError(
                    ValidationErrorType.DIMENSION_ERROR,
                    f"{dim_field.capitalize()} слишком велика (максимум {self.config.MAX_DIMENSION} см)",
                    dim_field,
                    value,
                    f"Уменьшите до {self.config.MAX_DIMENSION} см или меньше"
                ))

        # Вес
        weight = box_data['weight']
        if weight <= 0:
            result.add_error(ValidationError(
                ValidationErrorType.WEIGHT_ERROR,
                "Вес должен быть положительным",
                'weight',
                weight,
                "Введите значение больше 0"
            ))
        elif weight < self.config.MIN_WEIGHT:
            result.add_error(ValidationError(
                ValidationErrorType.WEIGHT_ERROR,
                f"Вес слишком мал (минимум {self.config.MIN_WEIGHT} кг)",
                'weight',
                weight,
                f"Увеличьте до {self.config.MIN_WEIGHT} кг или больше"
            ))
        elif weight > self.config.MAX_WEIGHT:
            result.add_error(ValidationError(
                ValidationErrorType.WEIGHT_ERROR,
                f"Вес слишком велик (максимум {self.config.MAX_WEIGHT} кг)",
                'weight',
                weight,
                f"Уменьшите до {self.config.MAX_WEIGHT} кг или меньше"
            ))

        # Плотность
        if result.is_valid:
            volume_dm3 = (box_data['length'] * box_data['width'] * box_data['height']) / 1000
            if volume_dm3 > 0:
                density = weight / volume_dm3
                if density < self.config.MIN_DENSITY:
                    result.add_warning(
                        f"Очень низкая плотность материала ({density:.3f} кг/дм³). Проверьте правильность размеров и веса."
                    )
                elif density > self.config.MAX_DENSITY:
                    result.add_error(ValidationError(
                        ValidationErrorType.DENSITY_ERROR,
                        f"Слишком высокая плотность материала ({density:.3f} кг/дм³)",
                        'density',
                        density,
                        "Проверьте правильность размеров и веса. Возможно, ошибка в единицах измерения."
                    ))

        # Количество
        if 'quantity' in box_data and box_data['quantity'] is not None:
            try:
                quantity = int(box_data['quantity'])
                if quantity <= 0:
                    result.add_error(ValidationError(
                        ValidationErrorType.QUANTITY_ERROR,
                        "Количество должно быть положительным целым числом",
                        'quantity',
                        box_data['quantity'],
                        "Введите целое число больше 0"
                    ))
                elif quantity > 100:
                    result.add_warning(
                        f"Большое количество коробок одного типа ({quantity}). Убедитесь, что это корректно."
                    )
                box_data['quantity'] = quantity
            except (ValueError, TypeError):
                result.add_error(ValidationError(
                    ValidationErrorType.QUANTITY_ERROR,
                    "Количество должно быть целым числом",
                    'quantity',
                    box_data['quantity'],
                    "Введите целое число (например: 5)"
                ))

        self._validate_optional_fields(box_data, result)
        return result

    def _validate_optional_fields(self, box_data: Dict[str, Any], result: ValidationResult):
        if 'description' in box_data and box_data['description']:
            description = str(box_data['description']).strip()
            if len(description) > 100:
                result.add_warning("Описание слишком длинное (более 100 символов)")
            box_data['description'] = description
        for field in ['fragile', 'stackable', 'hazardous']:
            if field in box_data and box_data[field] is not None:
                try:
                    box_data[field] = bool(box_data[field])
                except (ValueError, TypeError):
                    result.add_warning(f"Поле {field} должно быть логическим значением (True/False)")

    def validate_pallet_data(self, pallet_data: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()
        required_fields = ['length', 'width', 'height', 'max_weight']
        for field in required_fields:
            if field not in pallet_data or pallet_data[field] is None:
                result.add_error(ValidationError(
                    ValidationErrorType.DATA_TYPE_ERROR,
                    f"Отсутствует обязательное поле поддона: {field}",
                    field,
                    None,
                    f"Добавьте поле {field}"
                ))
                continue
            try:
                value = float(pallet_data[field])
                if np.isnan(value) or np.isinf(value):
                    raise ValueError("Недопустимое числовое значение")
                pallet_data[field] = value
            except (ValueError, TypeError):
                result.add_error(ValidationError(
                    ValidationErrorType.DATA_TYPE_ERROR,
                    f"Поле поддона {field} должно быть числом",
                    field,
                    pallet_data[field],
                    "Введите числовое значение"
                ))
        if not result.is_valid:
            return result
        for dim_field in ['length', 'width']:
            value = pallet_data[dim_field]
            if value <= 0:
                result.add_error(ValidationError(
                    ValidationErrorType.PALLET_ERROR,
                    f"Размер поддона {dim_field} должен быть положительным",
                    dim_field,
                    value,
                    "Введите положительное значение"
                ))
            elif value < self.config.MIN_PALLET_DIMENSION:
                result.add_error(ValidationError(
                    ValidationErrorType.PALLET_ERROR,
                    f"Размер поддона {dim_field} слишком мал (минимум {self.config.MIN_PALLET_DIMENSION} см)",
                    dim_field,
                    value,
                    f"Увеличьте до {self.config.MIN_PALLET_DIMENSION} см или больше"
                ))
            elif value > self.config.MAX_PALLET_DIMENSION:
                result.add_error(ValidationError(
                    ValidationErrorType.PALLET_ERROR,
                    f"Размер поддона {dim_field} слишком велик (максимум {self.config.MAX_PALLET_DIMENSION} см)",
                    dim_field,
                    value,
                    f"Уменьшите до {self.config.MAX_PALLET_DIMENSION} см или меньше"
                ))
        height = pallet_data['height']
        if height <= 0:
            result.add_error(ValidationError(
                ValidationErrorType.PALLET_ERROR,
                "Высота поддона должна быть положительной",
                'height',
                height,
                "Введите положительное значение"
            ))
        elif height < self.config.MIN_PALLET_HEIGHT:
            result.add_error(ValidationError(
                ValidationErrorType.PALLET_ERROR,
                f"Высота поддона слишком мала (минимум {self.config.MIN_PALLET_HEIGHT} см)",
                'height',
                height,
                f"Увеличьте до {self.config.MIN_PALLET_HEIGHT} см или больше"
            ))
        elif height > self.config.MAX_PALLET_HEIGHT:
            result.add_error(ValidationError(
                ValidationErrorType.PALLET_ERROR,
                f"Высота поддона слишком велика (максимум {self.config.MAX_PALLET_HEIGHT} см)",
                'height',
                height,
                f"Уменьшите до {self.config.MAX_PALLET_HEIGHT} см или меньше"
            ))
        max_weight = pallet_data['max_weight']
        if max_weight <= 0:
            result.add_error(ValidationError(
                ValidationErrorType.PALLET_ERROR,
                "Грузоподъемность поддона должна быть положительной",
                'max_weight',
                max_weight,
                "Введите положительное значение"
            ))
        elif max_weight < self.config.MIN_PALLET_CAPACITY:
            result.add_warning(
                f"Низкая грузоподъемность поддона ({max_weight} кг). Стандартные значения: 500-1500 кг"
            )
        elif max_weight > self.config.MAX_PALLET_CAPACITY:
            result.add_warning(
                f"Очень высокая грузоподъемность поддона ({max_weight} кг). Убедитесь в корректности значения"
            )
        self._check_standard_pallet_sizes(pallet_data, result)
        return result

    def _check_standard_pallet_sizes(self, pallet_data: Dict[str, Any], result: ValidationResult):
        length = pallet_data['length']
        width = pallet_data['width']
        tolerance = 5.0
        is_standard = False
        for std_length, std_width in self.config.STANDARD_PALLET_SIZES:
            if (abs(length - std_length) <= tolerance and abs(width - std_width) <= tolerance) or \
               (abs(length - std_width) <= tolerance and abs(width - std_length) <= tolerance):
                is_standard = True
                break
        if not is_standard:
            result.add_warning(
                f"Нестандартный размер поддона ({length}x{width} см). "
                f"Стандартные размеры: {', '.join([f'{l}x{w}' for l, w in self.config.STANDARD_PALLET_SIZES])}"
            )

    def validate_boxes_list(self, boxes: List[Dict[str, Any]]) -> ValidationResult:
        result = ValidationResult()
        if len(boxes) == 0:
            result.add_error(ValidationError(
                ValidationErrorType.QUANTITY_ERROR,
                "Список коробок не может быть пустым",
                'boxes_count',
                0,
                "Добавьте хотя бы одну коробку"
            ))
            return result
        if len(boxes) > self.config.MAX_BOXES_COUNT:
            result.add_warning(
                f"Очень много коробок ({len(boxes)}). Это может замедлить расчет или привести к частичной упаковке."
            )
        total_weight = 0
        total_volume = 0
        valid_boxes_count = 0
        for i, box in enumerate(boxes):
            box_result = self.validate_box_data(box)
            for error in box_result.errors:
                error.field = f"box_{i+1}.{error.field}"
                result.add_error(error)
            for warning in box_result.warnings:
                result.add_warning(f"Коробка {i+1}: {warning}")
            if box_result.is_valid:
                valid_boxes_count += 1
                total_weight += box.get('weight', 0)
                volume = (box.get('length', 0) * box.get('width', 0) * box.get('height', 0)) / 1000000
                total_volume += volume
        if total_weight > 10000:
            result.add_warning(f"Очень большой общий вес коробок: {total_weight:.1f} кг")
        if total_volume > 100:
            result.add_warning(f"Очень большой общий объем коробок: {total_volume:.1f} м³")
        if valid_boxes_count < len(boxes):
            result.add_warning(
                f"Из {len(boxes)} коробок валидны только {valid_boxes_count}. Исправьте ошибки в остальных коробках."
            )
        return result

    def validate_packing_feasibility(self, boxes: List[Dict[str, Any]], pallet: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()
        boxes_validation = self.validate_boxes_list(boxes)
        pallet_validation = self.validate_pallet_data(pallet)
        if not boxes_validation.is_valid or not pallet_validation.is_valid:
            result.add_error(ValidationError(
                ValidationErrorType.COMPATIBILITY_ERROR,
                "Невозможно проверить совместимость из-за ошибок в данных",
                'compatibility',
                None,
                "Исправьте ошибки в данных коробок и поддона"
            ))
            return result
        total_weight = sum(box.get('weight', 0) for box in boxes)
        total_volume = sum(
            (box.get('length', 0) * box.get('width', 0) * box.get('height', 0)) / 1000000
            for box in boxes
        )
        pallet_volume = (pallet.get('length', 0) * pallet.get('width', 0) * pallet.get('height', 0)) / 1000000
        pallet_capacity = pallet.get('max_weight', 0)

        # Мягкая проверка веса
        if total_weight > pallet_capacity:
            result.add_warning(
                f"Общий вес коробок ({total_weight:.1f} кг) превышает грузоподъемность поддона ({pallet_capacity:.1f} кг). "
                f"Часть коробок не будет упакована."
            )
        elif total_weight > pallet_capacity * 0.9:
            result.add_warning(
                f"Общий вес коробок близок к максимальной грузоподъемности ({total_weight:.1f} кг из {pallet_capacity:.1f} кг)"
            )

        # Проверка объема (мягко)
        packing_efficiency_estimates = [0.5, 0.65, 0.8]
        for i, efficiency in enumerate(packing_efficiency_estimates):
            effective_volume = pallet_volume * efficiency
            if total_volume > effective_volume:
                if i == 0:
                    result.add_warning(
                        f"Общий объем коробок ({total_volume:.2f} м³) значительно превышает "
                        f"реалистичный объем поддона ({effective_volume:.2f} м³). "
                        f"Часть коробок не будет упакована."
                    )
                elif i == 1:
                    result.add_warning(
                        f"Объем коробок ({total_volume:.2f} м³) больше реалистичного объема поддона ({effective_volume:.2f} м³)."
                    )
                break

        # Проверка размеров
        oversized_boxes = []
        for i, box in enumerate(boxes):
            if not self._can_box_fit_on_pallet(box, pallet):
                oversized_boxes.append(i + 1)
        if oversized_boxes:
            if len(oversized_boxes) == 1:
                result.add_warning(
                    f"Коробка {oversized_boxes[0]} не помещается на поддон ни в одной ориентации и точно не будет упакована."
                )
            else:
                result.add_warning(
                    f"{len(oversized_boxes)} коробок не помещаются на поддон ни в одной ориентации и точно не будут упакованы."
                )
        self._check_weight_distribution(boxes, pallet, result)
        self._check_stacking_feasibility(boxes, result)
        return result

    def _can_box_fit_on_pallet(self, box: Dict[str, Any], pallet: Dict[str, Any]) -> bool:
        box_dims = [box.get('length', 0), box.get('width', 0), box.get('height', 0)]
        pallet_dims = [pallet.get('length', 0), pallet.get('width', 0), pallet.get('height', 0)]
        for rotation in [(0,1,2), (0,2,1), (1,0,2), (1,2,0), (2,0,1), (2,1,0)]:
            rotated_dims = [box_dims[rotation[i]] for i in range(3)]
            if all(rotated_dims[i] <= pallet_dims[i] for i in range(3)):
                return True
        return False

    def _check_weight_distribution(self, boxes: List[Dict[str, Any]], pallet: Dict[str, Any], result: ValidationResult):
        if not boxes:
            return
        weights = [box.get('weight', 0) for box in boxes]
        max_box_weight = max(weights)
        avg_box_weight = sum(weights) / len(weights)
        if max_box_weight > avg_box_weight * 5:
            result.add_warning(
                f"Обнаружена очень тяжелая коробка ({max_box_weight:.1f} кг) при среднем весе {avg_box_weight:.1f} кг. Это может усложнить упаковку."
            )
        pallet_area = pallet.get('length', 0) * pallet.get('width', 0) / 10000
        if pallet_area > 0:
            weight_density = sum(weights) / pallet_area
            if weight_density > 1000:
                result.add_warning(
                    f"Высокая плотность веса на поддоне ({weight_density:.0f} кг/м²). Убедитесь в прочности поддона."
                )

    def _check_stacking_feasibility(self, boxes: List[Dict[str, Any]], result: ValidationResult):
        if len(boxes) < 2:
            return
        fragile_boxes = [i for i, box in enumerate(boxes) if box.get('fragile', False)]
        if fragile_boxes:
            result.add_warning(
                f"Обнаружены хрупкие коробки (номера: {', '.join(map(str, [i+1 for i in fragile_boxes]))}). Они должны размещаться сверху или отдельно."
            )
        non_stackable = [i for i, box in enumerate(boxes) if not box.get('stackable', True)]
        if non_stackable:
            result.add_warning(
                f"Коробки {', '.join(map(str, [i+1 for i in non_stackable]))} не могут использоваться как основание для других коробок."
            )