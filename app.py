import streamlit as st
import numpy as np
from py3dbp import Packer, Bin, Item
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime
import json
import os

from src.utils.constants import STANDARD_BOXES, PackingMethod, method_descriptions
from src.utils.visualization import create_3d_visualization, get_box_type_from_name
from src.utils.file_handlers import load_boxes_from_file, save_packing_result
from src.packers.weight_aware import WeightAwarePacker
from src.packers.extreme_points import ExtremePointPacker
from src.packers.laff import LAFFPacker
from src.packers.corner_points import CornerPointPacker
from src.packers.sfc import SFCPacker

def main():
    st.title("3D Bin Packing - Упаковка на поддон")

    # Сохраняем состояние приложения
    if 'results_calculated' not in st.session_state:
        st.session_state.results_calculated = False

    # Выбор метода упаковки
    packing_method = st.selectbox(
        "Выберите метод упаковки",
        options=[method.value for method in PackingMethod]
    )

    # Параметры поддона
    st.header("Параметры поддона")
    col1, col2 = st.columns(2)
    with col1:
        pallet_length = st.number_input("Длина поддона (см)", value=120)
        pallet_width = st.number_input("Ширина поддона (см)", value=80)
    with col2:
        pallet_height = st.number_input("Максимальная высота укладки (см)", value=160)
        pallet_weight = st.number_input("Максимальный вес (кг)", value=1000)

    # Загрузка данных
    st.header("Загрузка данных")
    upload_mode = st.radio(
        "Выберите способ ввода данных",
        ["Стандартные коробки", "Загрузить свои коробки"]
    )

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
                st.write("Загруженные коробки:")
                st.dataframe(boxes_df)
                use_custom_boxes = True
            except Exception as e:
                st.error(str(e))
                use_custom_boxes = False
        else:
            use_custom_boxes = False
    else:
        use_custom_boxes = False

    st.header("Выбор коробок")
    st.write("Укажите количество коробок каждого типа:")
    box_quantities = {}
    for box_name, box_info in STANDARD_BOXES.items():
        box_quantities[box_name] = st.number_input(
            f"{box_name} ({box_info['dimensions'][0]}x{box_info['dimensions'][1]}x{box_info['dimensions'][2]} см, "
            f"вес: {box_info['weight']} кг)",
            min_value=0,
            value=1
        )

    # Показываем описание выбранного метода
    st.markdown(method_descriptions[packing_method])

    calculate_button = st.button("Рассчитать упаковку")

    if calculate_button:
        st.session_state.results_calculated = True
        st.session_state.packing_results = {}

        if packing_method == PackingMethod.WEIGHT_AWARE.value:
            packer = WeightAwarePacker()
        elif packing_method == PackingMethod.EXTREME_POINTS.value:
            packer = ExtremePointPacker()
        elif packing_method == PackingMethod.LAFF.value:
            packer = LAFFPacker()
        elif packing_method == PackingMethod.CORNER_POINTS.value:
            packer = CornerPointPacker()
        elif packing_method == PackingMethod.SFC.value:
            packer = SFCPacker()

        # Сохраняем результаты в состоянии сессии
        st.session_state.packer = packer

        # Добавляем поддон
        packer.add_bin(
            Bin('Поддон', pallet_length, pallet_width, pallet_height, pallet_weight)
        )

        # Добавляем коробки
        item_count = 0
        if use_custom_boxes:
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
        packer.pack()

        # Сохраняем все результаты в состоянии сессии
        st.session_state.packing_results = {
            'packer': packer,
            'item_count': item_count,
            'use_custom_boxes': use_custom_boxes,
            'boxes_df': boxes_df if use_custom_boxes else None
        }

    # Отображаем результаты, если они есть
    if st.session_state.results_calculated:
        packer = st.session_state.packing_results['packer']
        item_count = st.session_state.packing_results['item_count']
        use_custom_boxes = st.session_state.packing_results['use_custom_boxes']
        boxes_df = st.session_state.packing_results['boxes_df']

        st.header("Результаты упаковки")
        st.write(f"Метод упаковки: {packing_method}")
        st.write(f"Время расчета: {packer.calculation_time:.2f} секунд")

        packed_items = len(packer.bins[0].items)
        unpacked_items = len(packer.unpacked_items)
        st.write(f"Всего коробок: {item_count}")
        st.write(f"Успешно упаковано: {packed_items}")

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
            st.error(f"Не удалось упаковать: {unpacked_items} коробок")
            st.subheader("Неупакованные коробки:")
            unpacked_by_type = {}
            for item in packer.unpacked_items:
                box_type = get_box_type_from_name(item.name)
                unpacked_by_type[box_type] = unpacked_by_type.get(box_type, 0) + 1

            for box_type, count in unpacked_by_type.items():
                if use_custom_boxes:
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
            
            # Добавляем CSS для улучшения внешнего вида кнопок
            st.markdown("""
            <style>
            .stButton > button {
                background-color: #f0f2f6;
                border: 1px solid #ccc;
                color: #333;
                font-weight: normal;
            }
            .stButton > button:hover {
                background-color: #e0e2e6;
                border-color: #aaa;
            }
            </style>
            """, unsafe_allow_html=True)
            
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
                    
                    # Создаем столбчатую диаграмму с ограниченной цветовой палитрой
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
                        else: # Excel
                            filename = f'results/packing_result_{timestamp}.xlsx'
                            packed_data = [{
                                'name': item.name,
                                'width': item.width,
                                'height': item.height,
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