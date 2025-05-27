# src/utils/app_state_manager.py

import streamlit as st
from typing import Optional, Dict, Any
import pandas as pd

class AppStateManager:
    """Централизованное управление состоянием Streamlit приложения"""
    
    def __init__(self):
        self._initialize_default_state()
    
    def _initialize_default_state(self):
        """Инициализация состояния по умолчанию"""
        # Основные состояния приложения
        if 'results_calculated' not in st.session_state:
            st.session_state.results_calculated = False
        
        if 'packing_results' not in st.session_state:
            st.session_state.packing_results = {}
        
        # Настройки Weight-Aware алгоритма
        if 'support_threshold' not in st.session_state:
            st.session_state.support_threshold = 0.8
        
        if 'weight_check' not in st.session_state:
            st.session_state.weight_check = True
        
        # Параметры поддона
        if 'pallet_length' not in st.session_state:
            st.session_state.pallet_length = 120
        
        if 'pallet_width' not in st.session_state:
            st.session_state.pallet_width = 80
        
        if 'pallet_height' not in st.session_state:
            st.session_state.pallet_height = 160
        
        if 'pallet_weight' not in st.session_state:
            st.session_state.pallet_weight = 1000
        
        # Режим загрузки данных
        if 'upload_mode' not in st.session_state:
            st.session_state.upload_mode = "Стандартные коробки"
        
        # Данные коробок
        if 'custom_boxes_df' not in st.session_state:
            st.session_state.custom_boxes_df = None
        
        if 'box_quantities' not in st.session_state:
            st.session_state.box_quantities = {}
        
        # Выбранный метод упаковки
        if 'packing_method' not in st.session_state:
            st.session_state.packing_method = "Weight-Aware (стабильная укладка с учетом веса)"
    
    def save_packing_results(self, packer, item_count: int, use_custom_boxes: bool, 
                           boxes_df: Optional[pd.DataFrame] = None, 
                           box_quantities: Optional[Dict[str, int]] = None):
        """Сохранение результатов упаковки"""
        st.session_state.packing_results = {
            'packer': packer,
            'item_count': item_count,
            'use_custom_boxes': use_custom_boxes,
            'boxes_df': boxes_df,
            'box_quantities': box_quantities,
            'pallet_params': {
                'length': st.session_state.pallet_length,
                'width': st.session_state.pallet_width,
                'height': st.session_state.pallet_height,
                'weight': st.session_state.pallet_weight
            },
            'algorithm_params': {
                'support_threshold': st.session_state.support_threshold,
                'weight_check': st.session_state.weight_check
            }
        }
        st.session_state.results_calculated = True
    
    def get_packing_results(self) -> Optional[Dict[str, Any]]:
        """Получение результатов упаковки"""
        return st.session_state.packing_results if st.session_state.results_calculated else None
    
    def clear_results(self):
        """Очистка результатов"""
        st.session_state.results_calculated = False
        st.session_state.packing_results = {}
    
    def has_results(self) -> bool:
        """Проверка наличия результатов"""
        return st.session_state.results_calculated
    
    def update_pallet_params(self, length: int, width: int, height: int, weight: int):
        """Обновление параметров поддона"""
        st.session_state.pallet_length = length
        st.session_state.pallet_width = width
        st.session_state.pallet_height = height
        st.session_state.pallet_weight = weight
    
    def update_algorithm_params(self, support_threshold: float, weight_check: bool):
        """Обновление параметров алгоритма"""
        st.session_state.support_threshold = support_threshold
        st.session_state.weight_check = weight_check
    
    def set_custom_boxes(self, boxes_df: pd.DataFrame):
        """Установка пользовательских коробок"""
        st.session_state.custom_boxes_df = boxes_df
    
    def get_custom_boxes(self) -> Optional[pd.DataFrame]:
        """Получение пользовательских коробок"""
        return st.session_state.custom_boxes_df
    
    def update_box_quantities(self, quantities: Dict[str, int]):
        """Обновление количества коробок"""
        st.session_state.box_quantities = quantities
    
    def get_box_quantities(self) -> Dict[str, int]:
        """Получение количества коробок"""
        return st.session_state.box_quantities
    
    def set_upload_mode(self, mode: str):
        """Установка режима загрузки данных"""
        st.session_state.upload_mode = mode
        # Очищаем результаты при смене режима
        if mode != st.session_state.get('previous_upload_mode', ''):
            self.clear_results()
            st.session_state.previous_upload_mode = mode
    
    def get_upload_mode(self) -> str:
        """Получение режима загрузки данных"""
        return st.session_state.upload_mode
    
    def set_packing_method(self, method: str):
        """Установка метода упаковки"""
        st.session_state.packing_method = method
    
    def get_packing_method(self) -> str:
        """Получение метода упаковки"""
        return st.session_state.packing_method
    
    def reset_to_defaults(self):
        """Сброс всех настроек к значениям по умолчанию"""
        # Очищаем все ключи, связанные с приложением
        keys_to_clear = [
            'results_calculated', 'packing_results', 'support_threshold', 
            'weight_check', 'pallet_length', 'pallet_width', 'pallet_height', 
            'pallet_weight', 'upload_mode', 'custom_boxes_df', 'box_quantities',
            'packing_method', 'previous_upload_mode'
        ]
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        # Повторная инициализация
        self._initialize_default_state()
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Получение сводки текущего состояния для отладки"""
        return {
            'results_calculated': st.session_state.results_calculated,
            'upload_mode': st.session_state.upload_mode,
            'packing_method': st.session_state.packing_method,
            'pallet_params': {
                'length': st.session_state.pallet_length,
                'width': st.session_state.pallet_width,
                'height': st.session_state.pallet_height,
                'weight': st.session_state.pallet_weight
            },
            'algorithm_params': {
                'support_threshold': st.session_state.support_threshold,
                'weight_check': st.session_state.weight_check
            },
            'has_custom_boxes': st.session_state.custom_boxes_df is not None,
            'box_quantities_count': len(st.session_state.box_quantities)
        }