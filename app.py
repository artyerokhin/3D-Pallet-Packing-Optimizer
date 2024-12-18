import streamlit as st
import numpy as np
from py3dbp import Packer, Bin, Item
import plotly.graph_objects as go
import time
from enum import Enum
from src.utils.constants import STANDARD_BOXES, PackingMethod, method_descriptions
from src.utils.visualization import create_3d_visualization, get_box_type_from_name
from src.packers.weight_aware import WeightAwarePacker
from src.packers.extreme_points import ExtremePointPacker
from src.packers.laff import LAFFPacker
from src.packers.corner_points import CornerPointPacker
from src.packers.sfc import SFCPacker

def main():
    st.title("3D Bin Packing - Упаковка на поддон")

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

    # Выбор коробок
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

    if st.button("Рассчитать упаковку"):
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

        # Добавляем поддон
        packer.add_bin(
            Bin('Поддон',
                pallet_length,
                pallet_width,
                pallet_height,
                pallet_weight)
        )

        # Добавляем коробки
        item_count = 0
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

        # Показываем результаты
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
                box_info = STANDARD_BOXES[box_type]
                st.write(
                    f"- {box_type}: {count} шт. "
                    f"(размеры: {box_info['dimensions'][0]}x{box_info['dimensions'][1]}x{box_info['dimensions'][2]} см, "
                    f"вес: {box_info['weight']} кг)"
                )

        if packed_items > 0:
            fig = create_3d_visualization(packer)
            st.plotly_chart(fig)

            st.header("Детали размещения")
            st.write("Координаты указаны в сантиметрах от левого нижнего угла поддона")
            for item in packer.bins[0].items:
                box_type = get_box_type_from_name(item.name)
                st.markdown(
                    f"Коробка {item.name}: "
                    f"позиция ({item.position[0]}, {item.position[1]}, {item.position[2]}), "
                    f"размеры ({item.width}, {item.height}, {item.depth})",
                    unsafe_allow_html=True
                )

if __name__ == "__main__":
    main()