# src/utils/file_handlers.py

import pandas as pd
from datetime import datetime
import json
import os
import numpy as np

def validate_box_data(df):
    """Расширенная валидация данных коробок с детальными проверками"""
    required_columns = ['name', 'length', 'width', 'height', 'weight', 'quantity']
    
    # Проверка наличия всех столбцов
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Отсутствуют обязательные столбцы: {', '.join(missing_columns)}")
    
    # Проверка пустых значений
    for col in required_columns:
        if df[col].isnull().any():
            null_rows = df[df[col].isnull()].index.tolist()
            raise ValueError(f"Обнаружены пустые значения в столбце '{col}' в строках: {null_rows}")
    
    # Проверка типов данных
    numeric_columns = ['length', 'width', 'height', 'weight', 'quantity']
    for col in numeric_columns:
        try:
            df[col] = pd.to_numeric(df[col], errors='raise')
        except ValueError:
            invalid_rows = df[~pd.to_numeric(df[col], errors='coerce').notna()].index.tolist()
            raise ValueError(f"Некорректные числовые значения в столбце '{col}' в строках: {invalid_rows}")
    
    # Проверка положительных значений
    for col in numeric_columns:
        negative_mask = df[col] <= 0
        if negative_mask.any():
            negative_rows = df[negative_mask].index.tolist()
            raise ValueError(f"Обнаружены отрицательные или нулевые значения в столбце '{col}' в строках: {negative_rows}")
    
    # Проверка разумных значений размеров
    size_columns = ['length', 'width', 'height']
    for col in size_columns:
        large_mask = df[col] > 500
        if large_mask.any():
            large_rows = df[large_mask].index.tolist()
            raise ValueError(f"Подозрительно большие размеры (>{500} см) в столбце '{col}' в строках: {large_rows}")
        
        small_mask = df[col] < 1
        if small_mask.any():
            small_rows = df[small_mask].index.tolist()
            raise ValueError(f"Подозрительно маленькие размеры (<{1} см) в столбце '{col}' в строках: {small_rows}")
    
    # Проверка веса
    heavy_mask = df['weight'] > 1000
    if heavy_mask.any():
        heavy_rows = df[heavy_mask].index.tolist()
        raise ValueError(f"Подозрительно большой вес (>{1000} кг) в строках: {heavy_rows}")
    
    light_mask = df['weight'] < 0.1
    if light_mask.any():
        light_rows = df[light_mask].index.tolist()
        raise ValueError(f"Подозрительно маленький вес (<{0.1} кг) в строках: {light_rows}")
    
    # Проверка логической корректности плотности
    df['volume'] = df['length'] * df['width'] * df['height'] / 1000000  # в кубометрах
    df['density'] = df['weight'] / df['volume']  # кг/м³
    
    high_density_mask = df['density'] > 10000  # плотность больше свинца
    if high_density_mask.any():
        dense_rows = df[high_density_mask].index.tolist()
        raise ValueError(f"Подозрительно высокая плотность материала (>{10000} кг/м³) в строках: {dense_rows}")
    
    low_density_mask = df['density'] < 1  # плотность меньше воды
    if low_density_mask.any():
        light_rows = df[low_density_mask].index.tolist()
        raise ValueError(f"Подозрительно низкая плотность материала (<{1} кг/м³) в строках: {light_rows}")
    
    # Проверка целостности количества
    non_integer_mask = df['quantity'] != df['quantity'].astype(int)
    if non_integer_mask.any():
        non_int_rows = df[non_integer_mask].index.tolist()
        raise ValueError(f"Количество должно быть целым числом в строках: {non_int_rows}")
    
    # Проверка максимального количества
    large_quantity_mask = df['quantity'] > 10000
    if large_quantity_mask.any():
        large_qty_rows = df[large_quantity_mask].index.tolist()
        raise ValueError(f"Подозрительно большое количество (>{10000}) в строках: {large_qty_rows}")
    
    # Проверка уникальности имен
    duplicate_names = df[df['name'].duplicated()]['name'].unique()
    if len(duplicate_names) > 0:
        raise ValueError(f"Обнаружены дублирующиеся имена коробок: {list(duplicate_names)}")
    
    # Проверка длины имен
    long_names_mask = df['name'].str.len() > 50
    if long_names_mask.any():
        long_name_rows = df[long_names_mask].index.tolist()
        raise ValueError(f"Слишком длинные имена коробок (>50 символов) в строках: {long_name_rows}")
    
    # Проверка на специальные символы в именах
    invalid_chars_mask = df['name'].str.contains(r'[<>:"/\\|?*]', regex=True, na=False)
    if invalid_chars_mask.any():
        invalid_rows = df[invalid_chars_mask].index.tolist()
        raise ValueError(f"Недопустимые символы в именах коробок в строках: {invalid_rows}")
    
    # Удаляем временные столбцы
    df = df.drop(['volume', 'density'], axis=1)
    
    return df

def validate_file_format(file):
    """Валидация формата загружаемого файла"""
    if not hasattr(file, 'name'):
        raise ValueError("Неверный формат файла")
    
    allowed_extensions = ['.csv', '.xlsx', '.xls']
    file_extension = os.path.splitext(file.name)[1].lower()
    
    if file_extension not in allowed_extensions:
        raise ValueError(f"Неподдерживаемый формат файла: {file_extension}. "
                        f"Поддерживаются: {', '.join(allowed_extensions)}")
    
    # Проверка размера файла (максимум 10 МБ)
    if hasattr(file, 'size') and file.size > 10 * 1024 * 1024:
        raise ValueError("Размер файла превышает 10 МБ")
    
    return True

def load_boxes_from_file(file):
    """Загрузка коробок из CSV/Excel файла с расширенной валидацией"""
    try:
        # Валидация формата файла
        validate_file_format(file)
        
        # Загрузка данных в зависимости от формата
        if file.name.endswith('.csv'):
            try:
                df = pd.read_csv(file, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(file, encoding='cp1251')
                except UnicodeDecodeError:
                    df = pd.read_csv(file, encoding='latin1')
        elif file.name.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file)
        else:
            raise ValueError("Неподдерживаемый формат файла")
        
        # Проверка на пустой файл
        if df.empty:
            raise ValueError("Загруженный файл пуст")
        
        # Проверка максимального количества строк
        if len(df) > 10000:
            raise ValueError(f"Слишком много строк в файле: {len(df)}. Максимум: 10000")
        
        # Очистка данных от лишних пробелов
        string_columns = df.select_dtypes(include=['object']).columns
        for col in string_columns:
            df[col] = df[col].astype(str).str.strip()
        
        # Валидация данных
        df = validate_box_data(df)
        
        return df
        
    except pd.errors.EmptyDataError:
        raise ValueError("Файл пуст или содержит только заголовки")
    except pd.errors.ParserError as e:
        raise ValueError(f"Ошибка при разборе файла: {str(e)}")
    except Exception as e:
        if "validate" in str(type(e).__name__).lower():
            raise  # Перебрасываем ошибки валидации как есть
        else:
            raise ValueError(f"Ошибка при загрузке файла: {str(e)}")

def save_packing_result(packer, space_utilization, save_dir='results'):
    """Сохранение результатов упаковки с улучшенной обработкой ошибок"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Создаем директорию если её нет
        os.makedirs(save_dir, exist_ok=True)
        
        # Расчет дополнительной статистики
        total_volume = sum(item.width * item.height * item.depth for item in packer.items)
        packed_volume = sum(item.width * item.height * item.depth for item in packer.bins[0].items)
        total_weight = sum(item.weight for item in packer.items)
        packed_weight = sum(item.weight for item in packer.bins[0].items)
        
        result = {
            'metadata': {
                'timestamp': timestamp,
                'version': '1.0',
                'generator': '3D Pallet Packing Optimizer'
            },
            'pallet': {
                'width': packer.bins[0].width,
                'height': packer.bins[0].height,
                'depth': packer.bins[0].depth,
                'max_weight': getattr(packer.bins[0], 'max_weight', 1000)
            },
            'packed_items': [{
                'name': item.name,
                'position': {
                    'x': item.position[0],
                    'y': item.position[1], 
                    'z': item.position[2]
                },
                'dimensions': {
                    'width': item.width,
                    'height': item.height,
                    'depth': item.depth
                },
                'weight': item.weight,
                'volume': item.width * item.height * item.depth
            } for item in packer.bins[0].items],
            'unpacked_items': [{
                'name': item.name,
                'dimensions': {
                    'width': item.width,
                    'height': item.height,
                    'depth': item.depth
                },
                'weight': item.weight,
                'volume': item.width * item.height * item.depth,
                'reason': 'Не удалось разместить'
            } for item in packer.unpacked_items],
            'statistics': {
                'space_utilization': round(space_utilization, 2),
                'volume_utilization': round(packed_volume / total_volume * 100, 2) if total_volume > 0 else 0,
                'weight_utilization': round(packed_weight / total_weight * 100, 2) if total_weight > 0 else 0,
                'total_items': len(packer.items),
                'packed_items': len(packer.bins[0].items),
                'unpacked_items': len(packer.unpacked_items),
                'packing_efficiency': round(len(packer.bins[0].items) / len(packer.items) * 100, 2) if packer.items else 0,
                'calculation_time': round(getattr(packer, 'calculation_time', 0), 3),
                'total_volume': total_volume,
                'packed_volume': packed_volume,
                'total_weight': total_weight,
                'packed_weight': packed_weight
            },
            'issues': getattr(packer, 'packing_issues', [])
        }
        
        filename = f'{save_dir}/packing_result_{timestamp}.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return filename
        
    except OSError as e:
        raise ValueError(f"Ошибка при создании файла: {str(e)}")
    except json.JSONEncodeError as e:
        raise ValueError(f"Ошибка при сериализации данных: {str(e)}")
    except Exception as e:
        raise ValueError(f"Неожиданная ошибка при сохранении: {str(e)}")