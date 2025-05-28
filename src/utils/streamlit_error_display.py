import streamlit as st
import numpy as np
from typing import List, Optional
from src.validation.validators import ValidationResult, ValidationError, ValidationErrorType

class StreamlitErrorDisplayManager:
    """Менеджер для отображения ошибок валидации в Streamlit"""

    @staticmethod
    def display_validation_result(result: ValidationResult, title: str = "Результаты валидации"):
        """Отображение результатов валидации с улучшенной обработкой"""
        if result.is_valid and not result.warnings:
            st.success(f"✅ {title}: Все проверки пройдены успешно!")
            return

        if not result.is_valid:
            st.error(f"❌ {title}: Обнаружены ошибки")
            StreamlitErrorDisplayManager._display_errors(result.errors)

        if result.warnings:
            st.warning(f"⚠️ {title}: Есть предупреждения")
            StreamlitErrorDisplayManager._display_warnings(result.warnings)

    @staticmethod
    def _display_errors(errors: List[ValidationError]):
        """Отображение ошибок валидации"""
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
                StreamlitErrorDisplayManager._show_error_help(error.error_type)

    @staticmethod
    def _display_warnings(warnings: List[str]):
        """Отображение предупреждений"""
        for warning in warnings:
            st.warning(f"⚠️ {warning}")

    @staticmethod
    def _show_error_help(error_type: ValidationErrorType):
        """Показ дополнительной помощи по типу ошибки"""
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
        """Отображение ошибок файла"""
        if file_errors:
            st.error("Ошибки в файле:")
            for error in file_errors:
                st.write(f"• {error}")

    @staticmethod
    def display_summary_stats(boxes: List[dict], validation_result: Optional[ValidationResult]):
        """Отображение сводной статистики с защитой от ошибок"""
        if not boxes:
            return

        try:
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
            StreamlitErrorDisplayManager._display_detailed_stats(boxes)
            
        except Exception as e:
            st.error(f"Ошибка при отображении статистики: {str(e)}")

    @staticmethod
    def _display_detailed_stats(boxes: List[dict]):
        """Отображение детальной статистики с защитой от ошибок"""
        st.subheader("📊 Детальная статистика")
        
        try:
            col1, col2, col3 = st.columns(3)
            
            # Анализ размеров
            with col1:
                st.write("**Размеры:**")
                lengths = [box.get('length', 0) for box in boxes if box.get('length', 0) > 0]
                widths = [box.get('width', 0) for box in boxes if box.get('width', 0) > 0]
                heights = [box.get('height', 0) for box in boxes if box.get('height', 0) > 0]
                
                if lengths and widths and heights:
                    st.write(f"• Длина: {min(lengths):.1f} - {max(lengths):.1f} см")
                    st.write(f"• Ширина: {min(widths):.1f} - {max(widths):.1f} см")
                    st.write(f"• Высота: {min(heights):.1f} - {max(heights):.1f} см")
                    st.write(f"• Средние: {np.mean(lengths):.1f}×{np.mean(widths):.1f}×{np.mean(heights):.1f} см")
                else:
                    st.write("Нет валидных данных о размерах")

            # Анализ веса
            with col2:
                st.write("**Вес:**")
                weights = [box.get('weight', 0) for box in boxes if box.get('weight', 0) > 0]
                
                if weights:
                    st.write(f"• Диапазон: {min(weights):.1f} - {max(weights):.1f} кг")
                    st.write(f"• Средний: {np.mean(weights):.1f} кг")
                    st.write(f"• Медиана: {np.median(weights):.1f} кг")
                    
                    light_boxes = sum(1 for w in weights if w < 1)
                    medium_boxes = sum(1 for w in weights if 1 <= w < 10)
                    heavy_boxes = sum(1 for w in weights if w >= 10)
                    
                    st.write(f"• Легкие (<1кг): {light_boxes}")
                    st.write(f"• Средние (1-10кг): {medium_boxes}")
                    st.write(f"• Тяжелые (>10кг): {heavy_boxes}")
                else:
                    st.write("Нет валидных данных о весе")

            # Анализ плотности
            with col3:
                st.write("**Плотность:**")
                densities = []
                for box in boxes:
                    try:
                        volume_dm3 = (box.get('length', 0) * box.get('width', 0) * box.get('height', 0)) / 1000
                        weight = box.get('weight', 0)
                        if volume_dm3 > 0 and weight > 0:
                            density = weight / volume_dm3
                            densities.append(density)
                    except (TypeError, ZeroDivisionError):
                        continue
                
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
                else:
                    st.write("Нет валидных данных о плотности")

            # Особенности коробок
            StreamlitErrorDisplayManager._display_box_features(boxes)
            
        except Exception as e:
            st.error(f"Ошибка при отображении детальной статистики: {str(e)}")

    @staticmethod
    def _display_box_features(boxes: List[dict]):
        """Отображение особенностей коробок"""
        try:
            st.subheader("🎯 Особенности коробок")
            
            fragile_count = sum(1 for box in boxes if box.get('fragile', False))
            non_stackable_count = sum(1 for box in boxes if not box.get('stackable', True))
            
            # Анализ форм с защитой от ошибок
            cube_like = 0
            flat_boxes = 0
            long_boxes = 0
            
            for box in boxes:
                try:
                    length = box.get('length', 0)
                    width = box.get('width', 0)
                    height = box.get('height', 0)
                    
                    if all(dim > 0 for dim in [length, width, height]):
                        # Кубические коробки
                        if abs(length - width) < 5 and abs(width - height) < 5:
                            cube_like += 1
                        
                        # Плоские коробки
                        if min(length, width, height) < 10:
                            flat_boxes += 1
                        
                        # Длинные коробки
                        max_dim = max(length, width, height)
                        min_dim = min(length, width, height)
                        if min_dim > 0 and max_dim > min_dim * 3:
                            long_boxes += 1
                            
                except (TypeError, ValueError):
                    continue
            
            st.write(f"🔸 Хрупкие: {fragile_count}")
            st.write(f"🔸 Неукладываемые: {non_stackable_count}")
            st.write(f"🔸 Кубические: {cube_like}")
            st.write(f"🔸 Плоские: {flat_boxes}")
            st.write(f"🔸 Длинные: {long_boxes}")
            
        except Exception as e:
            st.error(f"Ошибка при анализе особенностей коробок: {str(e)}")

    @staticmethod
    def display_packing_predictions(boxes: List[dict], pallet_params: dict):
        """Отображение прогнозов упаковки"""
        if not boxes:
            return
        
        try:
            st.subheader("🔮 Прогноз результатов упаковки")
            
            # Расчет теоретических показателей
            total_volume = sum(
                (box.get('length', 0) * box.get('width', 0) * box.get('height', 0)) / 1000000
                for box in boxes
                if all(box.get(dim, 0) > 0 for dim in ['length', 'width', 'height'])
            )
            
            pallet_volume = (pallet_params.get('length', 120) * 
                            pallet_params.get('width', 80) * 
                            pallet_params.get('height', 160)) / 1000000
            
            if pallet_volume > 0:
                # Эвристические оценки эффективности
                theoretical_max = min(total_volume / pallet_volume, 1.0) * 100
                realistic_estimate = theoretical_max * 0.65  # Учитываем потери на упаковку
                pessimistic_estimate = theoretical_max * 0.45
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Теоретический максимум", 
                        f"{theoretical_max:.1f}%",
                        help="Если бы коробки были жидкостью"
                    )
                
                with col2:
                    st.metric(
                        "Реалистичная оценка", 
                        f"{realistic_estimate:.1f}%",
                        help="Учитывает особенности упаковки"
                    )
                
                with col3:
                    st.metric(
                        "Пессимистичная оценка", 
                        f"{pessimistic_estimate:.1f}%",
                        help="Худший сценарий"
                    )
                
                # Рекомендации
                if realistic_estimate > 80:
                    st.success("🎯 Отличные перспективы упаковки!")
                elif realistic_estimate > 60:
                    st.info("👍 Хорошие шансы на эффективную упаковку")
                elif realistic_estimate > 40:
                    st.warning("⚠️ Средняя эффективность, возможны сложности")
                else:
                    st.error("❌ Низкая ожидаемая эффективность")
            else:
                st.error("Некорректные параметры поддона для прогноза")
                
        except Exception as e:
            st.error(f"Ошибка при создании прогноза: {str(e)}")