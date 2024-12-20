# tests/test_file_operations.py

import pytest
import pandas as pd
import os
import json
from datetime import datetime
from py3dbp import Bin, Item  # Добавляем импорт базовых классов
from src.utils.file_handlers import load_boxes_from_file, save_packing_result  # Добавляем импорт функций для работы с файлами

class TestFileOperations:
    @pytest.fixture
    def sample_packer(self):
        # Создаем тестовый пакер с данными
        from src.packers.weight_aware import WeightAwarePacker
        packer = WeightAwarePacker()
        packer.add_bin(Bin('test_pallet', 120, 80, 160, 1000))
        packer.add_item(Item('test_box_1', 30, 20, 15, 5))
        packer.pack()
        return packer

    @pytest.fixture
    def sample_csv(self):
        return """name,length,width,height,weight,quantity
Box1,30,20,15,5,2
Box2,40,30,20,10,1"""

    @pytest.fixture
    def sample_excel(self):
        df = pd.DataFrame({
            'name': ['Box1', 'Box2'],
            'length': [30, 40],
            'width': [20, 30],
            'height': [15, 20],
            'weight': [5, 10],
            'quantity': [2, 1]
        })
        return df

    def test_load_valid_csv(self, tmp_path, sample_csv):
        # Тест загрузки корректного CSV
        csv_path = tmp_path / "test.csv"
        with open(csv_path, 'w') as f:
            f.write(sample_csv)
        df = load_boxes_from_file(csv_path)
        assert len(df) == 2
        assert list(df.columns) == ['name', 'length', 'width', 'height', 'weight', 'quantity']

    def test_load_valid_excel(self, tmp_path, sample_excel):
        # Тест загрузки корректного Excel
        excel_path = tmp_path / "test.xlsx"
        sample_excel.to_excel(excel_path, index=False)
        df = load_boxes_from_file(excel_path)
        assert len(df) == 2
        assert list(df.columns) == ['name', 'length', 'width', 'height', 'weight', 'quantity']

    def test_load_invalid_columns(self, tmp_path):
        # Тест загрузки файла с неправильными колонками
        df = pd.DataFrame({'wrong_column': [1, 2]})
        excel_path = tmp_path / "invalid.xlsx"
        df.to_excel(excel_path, index=False)
        with pytest.raises(ValueError):
            load_boxes_from_file(excel_path)

    def test_save_json_result(self, tmp_path, sample_packer):
        # Тест сохранения в JSON
        result = save_packing_result(sample_packer, 75.5, str(tmp_path))
        assert os.path.exists(result)
        with open(result) as f:
            data = json.load(f)
        assert 'packed_items' in data
        assert 'statistics' in data

    def test_save_csv_result(self, tmp_path, sample_packer):
        # Тест сохранения в CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'{tmp_path}/packing_result_{timestamp}.csv'
        packed_data = [{
            'name': item.name,
            'width': item.width,
            'height': item.height,
            'depth': item.depth,
            'weight': item.weight,
            'position_x': item.position[0],
            'position_y': item.position[1],
            'position_z': item.position[2]
        } for item in sample_packer.bins[0].items]
        df = pd.DataFrame(packed_data)
        df.to_csv(filename, index=False)
        assert os.path.exists(filename)
        loaded_df = pd.read_csv(filename)
        assert len(loaded_df) == len(packed_data)

    def test_save_excel_result(self, tmp_path, sample_packer):
        # Тест сохранения в Excel
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'{tmp_path}/packing_result_{timestamp}.xlsx'
        with pd.ExcelWriter(filename) as writer:
            # Тест сохранения всех листов
            pd.DataFrame([{'test': 'data'}]).to_excel(writer, sheet_name='Упакованные')
            pd.DataFrame([{'test': 'data'}]).to_excel(writer, sheet_name='Неупакованные')
            pd.DataFrame([{'test': 'data'}]).to_excel(writer, sheet_name='Статистика')
        assert os.path.exists(filename)