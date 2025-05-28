import streamlit as st
import numpy as np
from typing import List
from src.validation.validators import ValidationResult, ValidationError, ValidationErrorType

class ErrorDisplayManager:
    """Менеджер для отображения ошибок валидации в Streamlit"""

    @staticmethod
    def display_validation_result(result: ValidationResult, title: str = "Результаты валидации"):
        if result.is_valid and not result.warnings:
            st.success(f"✅ {title}: Все проверки пройдены успешно!")
            return
        if not result.is_valid:
            st.error(f"❌ {title}: Обнаружены ошибки")
            ErrorDisplayManager._display_errors(result.errors)
        if result.warnings:
            st.warning(f"⚠️ {title}: Есть предупреждения")
            ErrorDisplayManager._display_warnings(result.warnings)

    @staticmethod
    def _display_errors(errors: List[ValidationError]):
        for error in errors:
            with st.expander(f"🔴 {error.message}", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Поле:**", error.field)
                    st.write("**Значение:**", error.value)
                    st.write("**Тип ошибки:**", error.error_type.value)
                with col2:
                    if error.suggestion:
                        st.info(f"💡 **Рекомендация:** {error.suggestion}")
                ErrorDisplayManager._show_error_help(error.error_type)

    @staticmethod
    def _display_warnings(warnings: List[str]):
        for warning in warnings:
            st.warning(f"⚠️ {warning}")

    @staticmethod
    def _show_error_help(error_type: ValidationErrorType):
        help_texts = {
            ValidationErrorType.DIMENSION_ERROR: """
**Справка по размерам:**
- Размеры должны быть в сантиметрах
- Минимальный размер: 0.1 см
- Максимальный размер: 500 см
- Проверьте единицы измерения
""",
            ValidationErrorType.WEIGHT_ERROR: """
**Справка по весу:**
- Вес должен быть в килограммах
- Минимальный вес: 0.01 кг
- Максимальный вес: 1000 кг
- Убедитесь в правильности единиц измерения
""",
            ValidationErrorType.DENSITY_ERROR: """
**Справка по плотности:**
- Плотность рассчитывается автоматически
- Проверьте соответствие размеров и веса
- Типичная плотность: 0.1-2.0 кг/дм³
""",
            ValidationErrorType.PALLET_ERROR: """
**Справка по поддону:**
- Стандартные размеры: 80x120, 100x120 см
- Высота обычно 15-20 см
- Грузоподъемность: 500-1500 кг
"""
        }
        if error_type in help_texts:
            st.info(help_texts[error_type])

    @staticmethod
    def display_file_errors(file_errors: List[str]):
        if file_errors:
            st.error("Ошибки в файле:")
            for error in file_errors:
                st.write(f"• {error}")

    @staticmethod
    def display_summary_stats(boxes: List[dict], validation_result: ValidationResult):
        if not boxes:
            return

        # Основные метрики
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Всего коробок", len(boxes))
        with col2:
            total_weight = sum(box.get('weight', 0) for box in boxes)
            st.metric("Общий вес", f"{total_weight:.1f} кг")
        with col3:
            total_volume = sum(
                (box.get('length', 0) * box.get('width', 0) * box.get('height', 0)) / 1000000
                for box in boxes
            )
            st.metric("Общий объем", f"{total_volume:.2f} м³")
        with col4:
            error_count = len(validation_result.errors) if validation_result else 0
            warning_count = len(validation_result.warnings) if validation_result else 0
            st.metric("Ошибок/Предупр.", f"{error_count}/{warning_count}")

        # Расширенная статистика
        st.subheader("📊 Детальная статистика")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("**Размеры:**")
            lengths = [box.get('length', 0) for box in boxes]
            widths = [box.get('width', 0) for box in boxes]
            heights = [box.get('height', 0) for box in boxes]
            st.write(f"• Длина: {min(lengths):.1f} - {max(lengths):.1f} см")
            st.write(f"• Ширина: {min(widths):.1f} - {max(widths):.1f} см")
            st.write(f"• Высота: {min(heights):.1f} - {max(heights):.1f} см")
            st.write(f"• Средние: {np.mean(lengths):.1f}×{np.mean(widths):.1f}×{np.mean(heights):.1f} см")
        with col2:
            st.write("**Вес:**")
            weights = [box.get('weight', 0) for box in boxes]
            st.write(f"• Диапазон: {min(weights):.1f} - {max(weights):.1f} кг")
            st.write(f"• Средний: {np.mean(weights):.1f} кг")
            st.write(f"• Медиана: {np.median(weights):.1f} кг")
            light_boxes = sum(1 for w in weights if w < 1)
            medium_boxes = sum(1 for w in weights if 1 <= w < 10)
            heavy_boxes = sum(1 for w in weights if w >= 10)
            st.write(f"• Легкие (<1кг): {light_boxes}")
            st.write(f"• Средние (1-10кг): {medium_boxes}")
            st.write(f"• Тяжелые (>10кг): {heavy_boxes}")
        with col3:
            st.write("**Плотность:**")
            densities = []
            for box in boxes:
                volume_dm3 = (box.get('length', 0) * box.get('width', 0) * box.get('height', 0)) / 1000
                if volume_dm3 > 0:
                    density = box.get('weight', 0) / volume_dm3
                    densities.append(density)
            if densities:
                st.write(f"• Диапазон: {min(densities):.2f} - {max(densities):.2f} кг/дм³")
                st.write(f"• Средняя: {np.mean(densities):.2f} кг/дм³")
                very_light = sum(1 for d in densities if d < 0.1)
                light = sum(1 for d in densities if 0.1 <= d < 0.5)
                normal = sum(1 for d in densities if 0.5 <= d < 2.0)
                heavy = sum(1 for d in densities if d >= 2.0)
                st.write(f"• Очень легкие: {very_light}")
                st.write(f"• Легкие: {light}")
                st.write(f"• Нормальные: {normal}")
                st.write(f"• Тяжелые: {heavy}")

        # Особенности
        st.subheader("🎯 Особенности коробок")
        fragile_count = sum(1 for box in boxes if box.get('fragile', False))
        non_stackable_count = sum(1 for box in boxes if not box.get('stackable', True))
        cube_like = sum(1 for box in boxes if abs(box.get('length', 0) - box.get('width', 0)) < 5 and abs(box.get('width', 0) - box.get('height', 0)) < 5)
        flat_boxes = sum(1 for box in boxes if min(box.get('length', 0), box.get('width', 0), box.get('height', 0)) < 10)
        long_boxes = sum(1 for box in boxes if max(box.get('length', 0), box.get('width', 0), box.get('height', 0)) > min(box.get('length', 0), box.get('width', 0), box.get('height', 0)) * 3)
        st.write(f"🔸 Хрупкие: {fragile_count}")
        st.write(f"🔸 Неукладываемые: {non_stackable_count}")
        st.write(f"🔸 Кубические: {cube_like}")
        st.write(f"🔸 Плоские: {flat_boxes}")
        st.write(f"🔸 Длинные: {long_boxes}")