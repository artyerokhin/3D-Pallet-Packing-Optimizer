from typing import List, Dict, Any
from src.validation.validators import ValidationResult, ValidationError, ValidationErrorType

class APIErrorHandler:
    """Обработчик ошибок для API (без Streamlit зависимостей)"""
    
    @staticmethod
    def format_validation_errors(result: ValidationResult) -> List[Dict[str, Any]]:
        """Форматирование ошибок валидации для API"""
        return [
            {
                "type": error.error_type.value,
                "message": error.message,
                "field": error.field,
                "value": error.value,
                "suggestion": error.suggestion
            }
            for error in result.errors
        ]
    
    @staticmethod
    def format_validation_warnings(result: ValidationResult) -> List[str]:
        """Форматирование предупреждений для API"""
        return result.warnings
    
    @staticmethod
    def create_error_response(result: ValidationResult, context: str = "Validation") -> Dict[str, Any]:
        """Создание полного ответа с ошибками для API"""
        return {
            "is_valid": result.is_valid,
            "context": context,
            "errors": APIErrorHandler.format_validation_errors(result),
            "warnings": APIErrorHandler.format_validation_warnings(result),
            "error_count": len(result.errors),
            "warning_count": len(result.warnings)
        }
    
    @staticmethod
    def get_error_summary(result: ValidationResult) -> str:
        """Краткое описание ошибок для логов"""
        if result.is_valid:
            return "No errors"
        
        error_types = [error.error_type.value for error in result.errors]
        return f"{len(result.errors)} errors: {', '.join(set(error_types))}"