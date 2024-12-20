# src/utils/file_handlers.py
import pandas as pd
from datetime import datetime
import json
import os


def load_boxes_from_file(file):
    """Загрузка коробок из CSV/Excel файла"""
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.name.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file)
        else:
            raise ValueError("Поддерживаются только CSV и Excel файлы")
            
        required_columns = ['name', 'length', 'width', 'height', 'weight', 'quantity']
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"Файл должен содержать столбцы: {', '.join(required_columns)}")
            
        return df
    except Exception as e:
        raise ValueError(f"Ошибка при загрузке файла: {str(e)}")


def save_packing_result(packer, space_utilization, save_dir='results'):
    """Сохранение результатов упаковки"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    result = {
        'timestamp': timestamp,
        'pallet': {
            'width': packer.bins[0].width,
            'height': packer.bins[0].height,
            'depth': packer.bins[0].depth,
            'max_weight': packer.bins[0].max_weight
        },
        'packed_items': [{
            'name': item.name,
            'position': item.position,
            'dimensions': [item.width, item.height, item.depth],
            'weight': item.weight
        } for item in packer.bins[0].items],
        'unpacked_items': [{
            'name': item.name,
            'dimensions': [item.width, item.height, item.depth],
            'weight': item.weight
        } for item in packer.unpacked_items],
        'statistics': {
            'space_utilization': space_utilization,
            'total_items': len(packer.items),
            'packed_items': len(packer.bins[0].items),
            'unpacked_items': len(packer.unpacked_items),
            'calculation_time': packer.calculation_time
        }
    }
    
    os.makedirs(save_dir, exist_ok=True)
    filename = f'{save_dir}/packing_result_{timestamp}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return filename