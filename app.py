import streamlit as st
import numpy as np
from py3dbp import Packer, Bin, Item
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime
import json
import os
import requests
import time

from src.utils.constants import STANDARD_BOXES, PackingMethod, method_descriptions
from src.utils.visualization import create_3d_visualization, get_box_type_from_name, display_api_results
from src.utils.file_handlers import load_boxes_from_file, save_packing_result
from src.packers.weight_aware import WeightAwarePacker
from src.packers.extreme_points import ExtremePointPacker
from src.packers.laff import LAFFPacker
from src.packers.corner_points import CornerPointPacker
from src.packers.sfc import SFCPacker

# Импорты системы валидации
from src.validation.validators import DataValidator, ValidationConfig
from src.utils.streamlit_error_display import StreamlitErrorDisplayManager
from src.utils.app_state_manager import AppStateManager


def main():
    st.title("3D Bin Packing - Упаковка на поддон")
    
    # Инициализация менеджеров
    state_manager = AppStateManager()
    validator = DataValidator()
    error_display = StreamlitErrorDisplayManager()
    
    # Настройки в боковой панели
    with st.sidebar:
        st.header("Настройки")
        
        # Настройки валидации
        st.subheader("Валидация")
        strict_mode = st.checkbox("Строгий режим валидации", value=False)
        
        if strict_mode:
            config = ValidationConfig()
            config.MIN_DENSITY = 0.05
            config.MAX_DENSITY = 8.0
            validator = DataValidator(config)
        
        # Настройки API
        st.subheader("API")
        use_api = st.checkbox("Использовать API для расчетов", value=False)
        if use_api:
            api_url = st.text_input("URL API", value="http://localhost:8000")
    
    # Выбор метода упаковки
    packing_method = st.selectbox(
        "Выберите метод упаковки",
        options=[method.value for method in PackingMethod],
        index=[method.value for method in PackingMethod].index(state_manager.get_packing_method())
    )
    state_manager.set_packing_method(packing_method)

    # Параметры поддона
    st.header("Параметры поддона")
    col1, col2 = st.columns(2)

    with col1:
        pallet_length = st.number_input(
            "Длина поддона (см)", 
            value=state_manager.get_state_summary()['pallet_params']['length']
        )
        pallet_width = st.number_input(
            "Ширина поддона (см)", 
            value=state_manager.get_state_summary()['pallet_params']['width']
        )

    with col2:
        pallet_height = st.number_input(
            "Максимальная высота укладки (см)", 
            value=state_manager.get_state_summary()['pallet_params']['height']
        )
        pallet_weight = st.number_input(
            "Максимальный вес (кг)", 
            value=state_manager.get_state_summary()['pallet_params']['weight']
        )

    # Валидация параметров поддона
    pallet_data = {
        'length': pallet_length,
        'width': pallet_width,
        'height': pallet_height,
        'max_weight': pallet_weight
    }

    pallet_validation = validator.validate_pallet_data(pallet_data)
    error_display.display_validation_result(pallet_validation, "Параметры поддона")

    # Обновляем состояние только если валидация прошла
    if pallet_validation.is_valid:
        state_manager.update_pallet_params(pallet_length, pallet_width, pallet_height, pallet_weight)

    # Дополнительные настройки для Weight-Aware метода
    if packing_method == PackingMethod.WEIGHT_AWARE.value:
        st.subheader("Настройки безопасности упаковки")
        
        col1, col2 = st.columns(2)
        with col1:
            support_threshold = st.number_input(
                "Минимальный процент поддержки (например, 0.8 означает 80%)",
                min_value=0.1, max_value=1.0, 
                value=state_manager.get_state_summary()['algorithm_params']['support_threshold'], 
                step=0.05,
                help="Минимальная доля площади опоры под коробкой"
            )

        with col2:
            weight_check = st.checkbox(
                "Проверка весовых ограничений",
                value=state_manager.get_state_summary()['algorithm_params']['weight_check'],
                help="Запрещает размещение тяжелых коробок на легких"
            )

        state_manager.update_algorithm_params(support_threshold, weight_check)

    # Загрузка данных
    st.header("Загрузка данных")
    upload_mode = st.radio(
        "Выберите способ ввода данных",
        ["Стандартные коробки", "Загрузить свои коробки"],
        index=0 if state_manager.get_upload_mode() == "Стандартные коробки" else 1
    )
    state_manager.set_upload_mode(upload_mode)

    use_custom_boxes = False
    boxes_df = None

    if upload_mode == "Загрузить свои коробки":
        uploaded_file = st.file_uploader(
            "Загрузите файл с параметрами коробок (CSV или Excel)",
            help="""
            Входные форматы файлов:
            - CSV: name,length,width,height,weight,quantity
            - Excel: те же колонки что и в CSV
            """,
            type=['csv', 'xlsx', 'xls']
        )

        if uploaded_file:
            try:
                boxes_df = load_boxes_from_file(uploaded_file)
                
                # Конвертируем DataFrame в список словарей для валидации
                boxes_data = boxes_df.to_dict('records')
                
                # Валидируем каждую коробку
                all_valid = True
                validated_boxes = []
                
                for i, box_data in enumerate(boxes_data):
                    box_validation = validator.validate_box_data(box_data)
                    
                    if not box_validation.is_valid:
                        st.error(f"Ошибки в коробке {i+1} ({box_data.get('name', 'Без имени')}):")
                        error_display.display_validation_result(box_validation, f"Коробка {i+1}")
                        all_valid = False
                    else:
                        validated_boxes.append(box_data)
                        if box_validation.warnings:
                            error_display.display_validation_result(box_validation, f"Коробка {i+1}")
                
                if all_valid:
                    st.success(f"✅ Все {len(validated_boxes)} коробок прошли валидацию")
                    state_manager.set_custom_boxes(boxes_df)
                    
                    # Показываем сводную статистику
                    error_display.display_summary_stats(validated_boxes, None)
                    
                    st.write("Загруженные коробки:")
                    st.dataframe(boxes_df)
                    use_custom_boxes = True
                else:
                    st.error("❌ Исправьте ошибки в данных перед продолжением")
                    use_custom_boxes = False
                    
            except Exception as e:
                st.error(f"Ошибка при загрузке файла: {str(e)}")
                use_custom_boxes = False
    else:
        st.header("Выбор коробок")
        st.write("Укажите количество коробок каждого типа:")
        
        box_quantities = {}
        for box_name, box_info in STANDARD_BOXES.items():
            box_quantities[box_name] = st.number_input(
                f"{box_name} ({box_info['dimensions'][0]}x{box_info['dimensions'][1]}x{box_info['dimensions'][2]} см, "
                f"вес: {box_info['weight']} кг)",
                min_value=0,
                value=state_manager.get_box_quantities().get(box_name, 1)
            )
        
        state_manager.update_box_quantities(box_quantities)
        
        # Валидация выбранных коробок
        selected_boxes = []
        total_boxes = 0
        
        for box_name, quantity in box_quantities.items():
            if quantity > 0:
                box_info = STANDARD_BOXES[box_name]
                box_data = {
                    'name': box_name,
                    'length': box_info['dimensions'][0],
                    'width': box_info['dimensions'][1],
                    'height': box_info['dimensions'][2],
                    'weight': box_info['weight'],
                    'quantity': quantity
                }
                
                box_validation = validator.validate_box_data(box_data)
                if box_validation.warnings:
                    error_display.display_validation_result(box_validation, f"Коробка {box_name}")
                
                selected_boxes.extend([box_data] * quantity)
                total_boxes += quantity
        
        if selected_boxes:
            # Валидация всего списка коробок
            boxes_validation = validator.validate_boxes_list(selected_boxes)
            error_display.display_validation_result(boxes_validation, "Список коробок")
            
            # Показываем сводную статистику
            error_display.display_summary_stats(selected_boxes, boxes_validation)

    # Показываем описание выбранного метода
    st.markdown(method_descriptions[packing_method])

    calculate_button = st.button("Рассчитать упаковку")

    if calculate_button:
        # Проверяем валидность параметров поддона перед упаковкой
        if not pallet_validation.is_valid:
            st.error("❌ Невозможно выполнить упаковку из-за ошибок в параметрах поддона")
            st.stop()
        
        # Подготовка данных для валидации
        if use_custom_boxes and boxes_df is not None:
            boxes_data = boxes_df.to_dict('records')
            # Развертываем количество
            expanded_boxes = []
            for box in boxes_data:
                for _ in range(int(box['quantity'])):
                    expanded_boxes.append(box)
        else:
            expanded_boxes = selected_boxes if 'selected_boxes' in locals() else []
        
        # Финальная валидация совместимости (мягкая)
        if expanded_boxes:
            compatibility_validation = validator.validate_packing_feasibility(
                expanded_boxes, 
                pallet_data
            )
            
            error_display.display_validation_result(compatibility_validation, "Анализ совместимости")
            
            # Продолжаем даже при предупреждениях - останавливаемся только при критических ошибках
            critical_errors = [e for e in compatibility_validation.errors 
                              if "значительно превышает" in e.message]
            
            if critical_errors:
                st.error("❌ Обнаружены критические проблемы. Упаковка может быть неэффективной.")
                if st.button("Продолжить несмотря на проблемы"):
                    st.warning("⚠️ Продолжаем с известными проблемами...")
                else:
                    st.stop()
        
        # Выбор между API и локальным расчетом
        if use_api:
            # Отправка запроса к API
            try:
                # Подготовка данных для API
                boxes_data_for_api = []
                if use_custom_boxes and boxes_df is not None:
                    boxes_data_for_api = boxes_df.to_dict('records')
                else:
                    for box_name, quantity in box_quantities.items():
                        if quantity > 0:
                            box_info = STANDARD_BOXES[box_name]
                            boxes_data_for_api.append({
                                'name': box_name,
                                'length': box_info['dimensions'][0],
                                'width': box_info['dimensions'][1],
                                'height': box_info['dimensions'][2],
                                'weight': box_info['weight'],
                                'quantity': quantity
                            })
                
                request_data = {
                    "pallet": pallet_data,
                    "boxes": boxes_data_for_api,
                    "method": packing_method,
                    "support_threshold": support_threshold if packing_method == PackingMethod.WEIGHT_AWARE.value else 0.8,
                    "weight_check_enabled": weight_check if packing_method == PackingMethod.WEIGHT_AWARE.value else True
                }
                
                # Создание задачи
                with st.spinner("Отправка запроса к API..."):
                    response = requests.post(f"{api_url}/pack", json=request_data, timeout=30)
                
                if response.status_code == 200:
                    task_data = response.json()
                    task_id = task_data["task_id"]
                    
                    # Ожидание результата
                    with st.spinner("Выполняется упаковка через API..."):
                        progress_bar = st.progress(0)
                        start_time = time.time()
                        
                        while True:
                            status_response = requests.get(f"{api_url}/status/{task_id}", timeout=10)
                            status_data = status_response.json()
                            
                            # Обновляем прогресс-бар
                            elapsed_time = time.time() - start_time
                            progress = min(elapsed_time / 30, 0.95)  # Максимум 95% до завершения
                            progress_bar.progress(progress)
                            
                            if status_data["status"] == "completed":
                                progress_bar.progress(1.0)
                                result_response = requests.get(f"{api_url}/result/{task_id}", timeout=10)
                                api_result = result_response.json()
                                
                                # Отображение результатов API
                                display_api_results(api_result)
                                break
                            elif status_data["status"] == "failed":
                                st.error(f"Ошибка API: {status_data.get('error', 'Неизвестная ошибка')}")
                                break
                            
                            time.sleep(1)
                            
                            # Таймаут через 60 секунд
                            if elapsed_time > 60:
                                st.error("Превышено время ожидания ответа от API")
                                break
                else:
                    st.error(f"Ошибка API ({response.status_code}): {response.text}")
                    
            except requests.exceptions.ConnectionError:
                st.error("Не удается подключиться к API. Убедитесь, что сервер запущен.")
            except requests.exceptions.Timeout:
                st.error("Превышено время ожидания ответа от API.")
            # except Exception as e:
            #     st.error(f"Ошибка при работе с API: {str(e)}")
        
        else:
            # Локальный расчет
            # Создание packer'а с настройками
            if packing_method == PackingMethod.WEIGHT_AWARE.value:
                packer = WeightAwarePacker(
                    support_threshold=state_manager.get_state_summary()['algorithm_params']['support_threshold'],
                    weight_check_enabled=state_manager.get_state_summary()['algorithm_params']['weight_check']
                )
            elif packing_method == PackingMethod.EXTREME_POINTS.value:
                packer = ExtremePointPacker()
            elif packing_method == PackingMethod.LAFF.value:
                packer = LAFFPacker()
            elif packing_method == PackingMethod.CORNER_POINTS.value:
                packer = CornerPointPacker()
            elif packing_method == PackingMethod.SFC.value:
                packer = SFCPacker()

            # Добавляем поддон
            packer.add_bin(
                Bin('Поддон', pallet_length, pallet_width, pallet_height, pallet_weight)
            )

            # Добавляем коробки
            item_count = 0
            if use_custom_boxes and boxes_df is not None:
                for _, row in boxes_df.iterrows():
                    for i in range(int(row['quantity'])):
                        item_count += 1
                        packer.add_item(
                            Item(f'{row["name"]}_{i}',
                                 row['length'],
                                 row['width'],
                                 row['height'],
                                 row['weight'])
                        )
            else:
                for box_name, quantity in box_quantities.items():
                    box_info = STANDARD_BOXES[box_name]
                    for i in range(quantity):
                        item_count += 1
                        packer.add_item(
                            Item(f'{box_name}_{i}',
                                 box_info['dimensions'][0],
                                 box_info['dimensions'][1],
                                 box_info['dimensions'][2],
                                 box_info['weight'])
                        )

            # Выполняем упаковку
            with st.spinner("Выполняется упаковка..."):
                packer.pack()

            # Сохраняем результаты в состоянии
            state_manager.save_packing_results(
                packer, item_count, use_custom_boxes, 
                boxes_df, box_quantities if not use_custom_boxes else None
            )

    # Отображаем результаты, если они есть
    if state_manager.has_results():
        results = state_manager.get_packing_results()
        packer = results['packer']
        item_count = results['item_count']
        use_custom_boxes = results['use_custom_boxes']
        boxes_df = results['boxes_df']

        st.header("Результаты упаковки (Локальный расчет)")
        st.write(f"Метод упаковки: {packing_method}")
        st.write(f"Время расчета: {packer.calculation_time:.2f} секунд")

        packed_items = len(packer.bins[0].items)
        unpacked_items = len(packer.unpacked_items)

        st.write(f"Всего коробок: {item_count}")
        st.write(f"Успешно упаковано: {packed_items}")
        st.write(f"Не удалось упаковать: {unpacked_items}")

        # Расчет эффективности использования пространства
        total_box_volume = sum(
            item.width * item.height * item.depth
            for item in packer.bins[0].items
        )
        bin_volume = (packer.bins[0].width *
                      packer.bins[0].height *
                      packer.bins[0].depth)
        space_utilization = (total_box_volume / bin_volume) * 100

        st.write(f"Эффективность использования пространства: {space_utilization:.1f}%")

        packed_weight = sum(item.weight for item in packer.bins[0].items)
        total_weight = sum(item.weight for item in packer.items)
        unpacked_weight = total_weight - packed_weight
        unpacked_weight_ratio = unpacked_weight / total_weight if total_weight > 0 else 0

        st.write(f"Общий вес всех коробок: {total_weight} кг")
        st.write(f"Вес упакованных коробок: {packed_weight} кг")
        st.write(f"Вес неупакованных коробок: {unpacked_weight} кг")
        st.write(f"Доля невместившегося веса: {unpacked_weight_ratio:.1%}")

        if unpacked_items > 0:
            st.warning(f"Не удалось упаковать: {unpacked_items} коробок")
            st.subheader("Неупакованные коробки:")
            unpacked_by_type = {}
            for item in packer.unpacked_items:
                box_type = get_box_type_from_name(item.name)
                unpacked_by_type[box_type] = unpacked_by_type.get(box_type, 0) + 1

            for box_type, count in unpacked_by_type.items():
                if use_custom_boxes and boxes_df is not None:
                    row = boxes_df[boxes_df['name'] == box_type].iloc[0]
                    st.write(
                        f"- {box_type}: {count} шт. "
                        f"(размеры: {row['length']}x{row['width']}x{row['height']} см, "
                        f"вес: {row['weight']} кг)"
                    )
                else:
                    box_info = STANDARD_BOXES[box_type]
                    st.write(
                        f"- {box_type}: {count} шт. "
                        f"(размеры: {box_info['dimensions'][0]}x{box_info['dimensions'][1]}x{box_info['dimensions'][2]} см, "
                        f"вес: {box_info['weight']} кг)"
                    )

        if packed_items > 0:
            # Используем улучшенную визуализацию
            fig = create_3d_visualization(packer)
            
            # Отображаем график
            st.plotly_chart(fig, use_container_width=True)

            # Добавляем кнопки управления в одну строку
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Сохранить 3D-визуализацию", key="save_3d"):
                    os.makedirs('results', exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f'results/3d_visualization_{timestamp}.html'
                    fig.write_html(filename)
                    st.success(f"3D-визуализация сохранена в файл: {filename}")

            with col2:
                if st.button("Показать статистику использования", key="show_stats"):
                    # Создаем данные для сравнительной визуализации
                    comparison_data = {
                        'Категория': ['Объем поддона', 'Объем коробок', 'Неиспользованный объем'],
                        'Объем (см³)': [
                            bin_volume,
                            total_box_volume,
                            bin_volume - total_box_volume
                        ]
                    }
                    df_comparison = pd.DataFrame(comparison_data)

                    # Создаем столбчатую диаграмму
                    fig_bar = px.bar(
                        df_comparison,
                        x='Категория',
                        y='Объем (см³)',
                        color='Категория',
                        color_discrete_sequence=['#1f77b4', '#2ca02c', '#d62728'],
                        text='Объем (см³)'
                    )

                    fig_bar.update_layout(
                        plot_bgcolor='white',
                        title='Использование объема поддона',
                        xaxis_title=None,
                        yaxis_title='Объем (см³)',
                        showlegend=False
                    )

                    fig_bar.update_traces(
                        texttemplate='%{text:.0f}',
                        textposition='outside'
                    )

                    st.plotly_chart(fig_bar, use_container_width=True)

            # Создаем контейнер для сохранения
            save_container = st.container()
            with save_container:
                col1, col2 = st.columns(2)
                
                with col1:
                    file_format = st.selectbox(
                        "Выберите формат сохранения",
                        ["JSON", "CSV", "Excel"],
                        key="file_format_select",
                        help="""
                        Выходные форматы:
                        - JSON: полная информация о упаковке включая координаты
                        - CSV: упрощенный формат с основными параметрами
                        - Excel: расширенный формат с отдельными листами для упакованных и неупакованных коробок
                        """
                    )

                with col2:
                    if st.button("Экспортировать отчет валидации"):
                        validation_report = {
                            'timestamp': datetime.now().isoformat(),
                            'pallet_validation': pallet_validation.__dict__ if 'pallet_validation' in locals() else None,
                            'boxes_validation': boxes_validation.__dict__ if 'boxes_validation' in locals() else None,
                            'compatibility_validation': compatibility_validation.__dict__ if 'compatibility_validation' in locals() else None
                        }
                        
                        os.makedirs('results', exist_ok=True)
                        filename = f"results/validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump(validation_report, f, ensure_ascii=False, indent=2, default=str)
                        
                        st.success(f"Отчет валидации сохранен: {filename}")

                if st.button("Сохранить результаты", key="save_button"):
                    try:
                        os.makedirs('results', exist_ok=True)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        if file_format == "JSON":
                            filename = save_packing_result(packer, space_utilization)
                        elif file_format == "CSV":
                            filename = f'results/packing_result_{timestamp}.csv'
                            packed_data = [{
                                'name': item.name,
                                'width': item.width,
                                'height': item.height,
                                'depth': item.depth,
                                'weight': item.weight,
                                'position_x': item.position[0],
                                'position_y': item.position[1],
                                'position_z': item.position[2]
                            } for item in packer.bins[0].items]
                            df = pd.DataFrame(packed_data)
                            df.to_csv(filename, index=False)
                        else:  # Excel
                            filename = f'results/packing_result_{timestamp}.xlsx'
                            packed_data = [{
                                'name': item.name,
                                'width': item.width,
                                'height': item.height,
                                'depth': item.depth,
                                'weight': item.weight,
                                'position_x': item.position[0],
                                'position_y': item.position[1],
                                'position_z': item.position[2]
                            } for item in packer.bins[0].items]
                            
                            unpacked_data = [{
                                'name': item.name,
                                'width': item.width,
                                'height': item.height,
                                'depth': item.depth,
                                'weight': item.weight
                            } for item in packer.unpacked_items]
                            
                            stats_data = [{
                                'total_items': len(packer.items),
                                'packed_items': packed_items,
                                'unpacked_items': unpacked_items,
                                'space_utilization': space_utilization,
                                'calculation_time': packer.calculation_time,
                                'total_weight': total_weight,
                                'packed_weight': packed_weight
                            }]

                            with pd.ExcelWriter(filename) as writer:
                                pd.DataFrame(packed_data).to_excel(writer, sheet_name='Упакованные', index=False)
                                pd.DataFrame(unpacked_data).to_excel(writer, sheet_name='Неупакованные', index=False)
                                pd.DataFrame(stats_data).to_excel(writer, sheet_name='Статистика', index=False)

                        st.success(f"Результаты сохранены в файл: {filename}")
                    except Exception as e:
                        st.error(f"Ошибка при сохранении: {str(e)}")

            st.header("Детали размещения")
            st.write("Координаты указаны в сантиметрах от левого нижнего угла поддона")
            
            for item in packer.bins[0].items:
                st.markdown(
                    f"Коробка {item.name}: "
                    f"позиция ({item.position[0]}, {item.position[1]}, {item.position[2]}), "
                    f"размеры ({item.width}, {item.height}, {item.depth})",
                    unsafe_allow_html=True
                )

if __name__ == "__main__":
    main()