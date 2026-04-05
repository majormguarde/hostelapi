"""
Утилиты для обработки ошибок и логирования
"""

import logging
import traceback
from typing import Dict, Tuple
from flask import jsonify

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Обработчик ошибок приложения"""

    @staticmethod
    def handle_database_error(error: Exception) -> Tuple[Dict, int]:
        """
        Обработать ошибку базы данных
        
        Args:
            error: Исключение БД
            
        Returns:
            Tuple[Dict, int]: (response, status_code)
        """
        error_msg = str(error)
        logger.error(f"Database error: {error_msg}\n{traceback.format_exc()}")
        
        # Преобразовать технические ошибки в понятные сообщения
        if 'timeout' in error_msg.lower():
            return {
                'error': 'Время ожидания ответа от базы данных истекло.'
            }, 504
        elif 'connection' in error_msg.lower():
            return {
                'error': 'Ошибка подключения к базе данных. Проверьте параметры подключения.'
            }, 503
        elif 'permission' in error_msg.lower():
            return {
                'error': 'Недостаточно прав для выполнения операции.'
            }, 403
        else:
            return {
                'error': 'Ошибка при работе с базой данных. Попробуйте позже.'
            }, 500

    @staticmethod
    def handle_procedure_error(result_code: int) -> Tuple[Dict, int]:
        """
        Обработать ошибку процедуры HOSTEL_CARDEDIT
        
        Args:
            result_code: Код результата процедуры (O_RES)
            
        Returns:
            Tuple[Dict, int]: (response, status_code)
        """
        # Коды результата процедуры:
        # 0 - карта добавлена
        # 1 - карта обновлена
        # 2 - карта уже существует
        # 3 - карта в базе не найдена
        
        if result_code == 0:
            return {'message': 'Карта успешно добавлена'}, 201
        elif result_code == 1:
            return {'message': 'Карта успешно обновлена'}, 200
        elif result_code == 2:
            return {'error': 'Карта с таким номером уже существует'}, 409
        elif result_code == 3:
            return {'error': 'Карта не найдена'}, 404
        else:
            return {'error': 'Неизвестная ошибка при работе с картой'}, 500

    @staticmethod
    def handle_validation_error(errors: Dict[str, str]) -> Tuple[Dict, int]:
        """
        Обработать ошибку валидации
        
        Args:
            errors: Словарь с ошибками валидации
            
        Returns:
            Tuple[Dict, int]: (response, status_code)
        """
        logger.warning(f"Validation error: {errors}")
        return {
            'error': 'Ошибка валидации данных',
            'details': errors
        }, 400

    @staticmethod
    def handle_authentication_error(message: str = None) -> Tuple[Dict, int]:
        """
        Обработать ошибку аутентификации
        
        Args:
            message: Сообщение об ошибке
            
        Returns:
            Tuple[Dict, int]: (response, status_code)
        """
        logger.warning(f"Authentication error: {message}")
        return {
            'error': message or 'Ошибка аутентификации'
        }, 401

    @staticmethod
    def handle_authorization_error(message: str = None) -> Tuple[Dict, int]:
        """
        Обработать ошибку авторизации
        
        Args:
            message: Сообщение об ошибке
            
        Returns:
            Tuple[Dict, int]: (response, status_code)
        """
        logger.warning(f"Authorization error: {message}")
        return {
            'error': message or 'Доступ запрещен'
        }, 403

    @staticmethod
    def handle_not_found_error(resource: str = 'Ресурс') -> Tuple[Dict, int]:
        """
        Обработать ошибку "не найдено"
        
        Args:
            resource: Название ресурса
            
        Returns:
            Tuple[Dict, int]: (response, status_code)
        """
        logger.warning(f"Not found: {resource}")
        return {
            'error': f'{resource} не найден'
        }, 404

    @staticmethod
    def handle_internal_error(error: Exception = None) -> Tuple[Dict, int]:
        """
        Обработать внутреннюю ошибку сервера
        
        Args:
            error: Исключение
            
        Returns:
            Tuple[Dict, int]: (response, status_code)
        """
        if error:
            logger.error(f"Internal error: {str(error)}\n{traceback.format_exc()}")
        else:
            logger.error(f"Internal error\n{traceback.format_exc()}")
        
        return {
            'error': 'Внутренняя ошибка сервера. Попробуйте позже.'
        }, 500


def setup_logging():
    """Настроить логирование приложения"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )
