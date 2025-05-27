# src/utils/file_handlers.py
import pandas as pd
from datetime import datetime
import json
import os

def validate_box_data(df):
    """Валидация данных коробок"""
    required_columns = ['name', 'length', 'width', 'height', 'weight', 'quantity']
    
    # Проверка наличия всех столбцов
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Отсутствуют столбцы: {', '.join(missing_columns)}")
    
    # Проверка положительных значений
    numeric_columns = ['length', 'width', 'height', 'weight', 'quantity']
    for col in numeric_columns:
        if (df[col] <= 0).any():
            raise ValueError(f"Все значения в столбце '{col}' должны быть положительными")
    
    # Проверка разумных значений
    if (df['weight'] > 1000).any():
        raise ValueError("Обнаружены подозрительно большие значения веса (>1000 кг)")
    
    if (df[['length', 'width', 'height']] > 500).any().any():
        raise ValueError("Обнаружены подозрительно большие размеры (>500 см)")
    
    return df

def load_boxes_from_file(file):
    """Загрузка коробок из CSV/Excel файла с валидацией"""
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.name.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file)
        else:
            raise ValueError("Поддерживаются только CSV и Excel файлы")
        
        # Валидация данных
        df = validate_box_data(df)
        return df
        
    except Exception as e:
        raise ValueError(f"Ошибка при загрузке файла: {str(e)}")

def save_packing_result(packer, space_utilization, save_dir='results'):
    """Сохранение результатов упаковки"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Расчет дополнительной статистики
    total_volume = sum(item.width * item.height * item.depth for item in packer.items)
    packed_volume = sum(item.width * item.height * item.depth for item in packer.bins[0].items)
    total_weight = sum(item.weight for item in packer.items)
    packed_weight = sum(item.weight for item in packer.bins[0].items)
    
    result = {
        'timestamp': timestamp,
        'pallet': {
            'width': packer.bins[0].width,
            'height': packer.bins[0].height,
            'depth': packer.bins[0].depth,
            'max_weight': getattr(packer.bins[0], 'max_weight', 1000)
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
            'volume_utilization': packed_volume / total_volume if total_volume > 0 else 0,
            'weight_utilization': packed_weight / total_weight if total_weight > 0 else 0,
            'total_items': len(packer.items),
            'packed_items': len(packer.bins[0].items),
            'unpacked_items': len(packer.unpacked_items),
            'packing_efficiency': len(packer.bins[0].items) / len(packer.items) if packer.items else 0,
            'calculation_time': getattr(packer, 'calculation_time', 0)
        },
        'issues': getattr(packer, 'packing_issues', [])
    }
    
    os.makedirs(save_dir, exist_ok=True)
    filename = f'{save_dir}/packing_result_{timestamp}.json'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return filename