"""
DatabaseManager для работы с базой данных Firebird.
Управляет подключением и выполнением операций с картами через процедуру HOSTEL_CARDEDIT.
"""

import fdb
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер для работы с базой данных Firebird"""

    def __init__(self, db_path: str, host: str = 'localhost', port: int = 3050, 
                 user: str = 'SYSDBA', password: str = 'masterkey'):
        """
        Инициализация DatabaseManager
        
        Args:
            db_path: Путь к файлу базы данных guardee.fdb
            host: Хост базы данных (по умолчанию localhost)
            port: Порт базы данных (по умолчанию 3050)
            user: Пользователь БД (по умолчанию SYSDBA)
            password: Пароль БД (по умолчанию masterkey)
        """
        self.db_path = db_path
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.connection = None
        self.cursor = None

    def connect(self) -> bool:
        """
        Подключиться к базе данных Firebird
        
        Returns:
            bool: True если подключение успешно, False иначе
        """
        try:
            self.connection = fdb.connect(
                host=self.host,
                port=self.port,
                database=self.db_path,
                user=self.user,
                password=self.password,
                charset='WIN1251'
            )
            self.cursor = self.connection.cursor()
            logger.info(f"Успешное подключение к БД: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к БД: {str(e)}")
            raise

    def disconnect(self) -> None:
        """Отключиться от базы данных"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            logger.info("Отключение от БД")
        except Exception as e:
            logger.error(f"Ошибка при отключении от БД: {str(e)}")

    def call_cardedit_procedure(self, action: int, room: int = None, card_number: int = None,
                               valid_from: str = None, valid_days: int = None,
                               comments: str = None, dep: str = 'ХОСТЕЛ') -> Dict:
        """
        Вызвать процедуру HOSTEL_CARDEDIT
        
        Args:
            action: Действие (0=получить, 1=добавить/обновить, 2=удалить, 3=заблокировать, 4=активировать)
            room: Номер комнаты (формат XXYY)
            card_number: Номер карты
            valid_from: Дата начала действия (формат YYYY-MM-DD)
            valid_days: Количество дней действия
            comments: Комментарий
            dep: Название отдела
            
        Returns:
            Dict с результатом операции
        """
        try:
            if not self.connection:
                self.connect()

            # Преобразовать дату
            if valid_from:
                valid_from_date = datetime.strptime(valid_from, '%Y-%m-%d').date()
            else:
                valid_from_date = datetime.now().date()

            # Вызвать процедуру
            self.cursor.callproc('HOSTEL_CARDEDIT', [
                action,
                room,
                card_number,
                valid_from_date,
                valid_days,
                comments or '',
                dep
            ])

            # Получить результаты
            result = self.cursor.fetchone()
            
            if result:
                return {
                    'people_id': result[0],
                    'profile_id': result[1],
                    'card_id': result[2],
                    'result_code': result[3],
                    'actived': result[4],
                    'valid_from': result[5],
                    'valid_to': result[6],
                    'error': None
                }
            else:
                return {'error': 'Процедура не вернула результат'}

        except Exception as e:
            logger.error(f"Ошибка при вызове HOSTEL_CARDEDIT: {str(e)}")
            return {'error': str(e)}

    def call_upd_dumps(self, card_number: int, action: int = 0) -> bool:
        """
        Вызвать процедуру UPD_CARDSLIST для обновления дампов
        
        Args:
            card_number: Номер карты
            action: Действие (0=добавить, 1=удалить)
            
        Returns:
            bool: True если успешно, False иначе
        """
        try:
            if not self.connection:
                self.connect()

            self.cursor.callproc('UPD_CARDSLIST', [card_number, action])
            self.connection.commit()
            logger.info(f"UPD_CARDSLIST вызвана для карты {card_number}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при вызове UPD_CARDSLIST: {str(e)}")
            return False

    def get_all_cards(self) -> List[Dict]:
        """
        Получить список всех карт с профилем доступа
        
        Returns:
            List[Dict]: Список карт с их атрибутами и профилем доступа
        """
        try:
            if not self.connection:
                self.connect()

            # PROFILEID в CARDS ссылается на PROFILEID в PROFILE
            query = """
                SELECT 
                    c.CARDSID,
                    c.PEOPLEID,
                    c.CARDNUM,
                    c.OPENDATE,
                    c.CLOSEDATE,
                    c.ACTIVED,
                    c.COMMENTS,
                    c.PROFILEID,
                    p.NAME as PROFILE_NAME,
                    p.PROF_TYPE
                FROM PROFILE p
                INNER JOIN CARDS c ON p.PROFILEID = c.PROFILEID
                ORDER BY c.CARDSID DESC
            """

            self.cursor.execute(query)
            rows = self.cursor.fetchall()

            cards = []
            for row in rows:
                profile_name = row[8] if row[8] else 'Не указан'
                cards.append({
                    'card_id': row[0],
                    'people_id': row[1],
                    'card_number': row[2],
                    'valid_from': row[3].isoformat() if row[3] else None,
                    'valid_until': row[4].isoformat() if row[4] else None,
                    'status': row[5],
                    'comments': row[6],
                    'profile_id': row[7],
                    'profile_name': profile_name,
                    'profile_type': row[9]
                })

            return cards

        except Exception as e:
            logger.error(f"Ошибка при получении списка карт: {str(e)}")
            return []

    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """
        Аутентифицировать пользователя через таблицу USERS
        
        Args:
            username: Имя пользователя
            password: Пароль
            
        Returns:
            Dict с информацией о пользователе или None если аутентификация не удалась
        """
        try:
            if not self.connection:
                self.connect()

            # Попробовать разные варианты названий колонок
            query = """
                SELECT ID, NAME, PASSWD, FLAGS, SFLAGS
                FROM USERS
                WHERE NAME = ?
            """

            try:
                self.cursor.execute(query, [username])
                user = self.cursor.fetchone()
            except:
                # Если ID не существует, попробовать без него
                query = """
                    SELECT NAME, PASSWD, FLAGS, SFLAGS
                    FROM USERS
                    WHERE NAME = ?
                """
                self.cursor.execute(query, [username])
                user = self.cursor.fetchone()
                if user:
                    user = (1,) + user  # Добавить фиктивный ID

            if not user:
                logger.warning(f"Пользователь {username} не найден")
                return None

            user_id, name, stored_password, flags, sflags = user

            # Проверка пароля
            if not self._verify_password(password, stored_password):
                logger.warning(f"Неверный пароль для пользователя {username}")
                return None

            # Анализировать FLAGS и SFLAGS для определения прав доступа
            permissions = self._parse_permissions(flags, sflags)

            return {
                'id': user_id,
                'username': name,
                'flags': flags,
                'sflags': sflags,
                'permissions': permissions
            }

        except Exception as e:
            logger.error(f"Ошибка при аутентификации пользователя: {str(e)}")
            return None

    def _verify_password(self, password: str, stored_password: str) -> bool:
        """
        Проверить пароль
        
        Args:
            password: Введенный пароль
            stored_password: Сохраненный пароль
            
        Returns:
            bool: True если пароль верный
        """
        # Если пароль не сохранен, проверяем простое совпадение
        if not stored_password:
            return False
        
        # Простая проверка (в реальном приложении нужно использовать хеширование)
        return password == stored_password

    def _parse_permissions(self, flags: int, sflags: int) -> Dict[str, bool]:
        """
        Анализировать FLAGS и SFLAGS для определения прав доступа
        
        Args:
            flags: Значение FLAGS
            sflags: Значение SFLAGS
            
        Returns:
            Dict с правами доступа
        """
        # Битовые флаги для прав доступа
        # Это примерная реализация - нужно уточнить с реальной структурой БД
        permissions = {
            'can_view': True,  # Все могут просматривать
            'can_create': bool(flags & 0x01),  # Бит 0 - создание
            'can_edit': bool(flags & 0x02),    # Бит 1 - редактирование
            'can_delete': bool(flags & 0x04),  # Бит 2 - удаление
            'is_admin': bool(flags & 0x08)     # Бит 3 - администратор
        }
        return permissions

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """
        Получить информацию о пользователе по ID
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Dict с информацией о пользователе или None
        """
        try:
            if not self.connection:
                self.connect()

            query = """
                SELECT USERID, NAME, FLAGS, SFLAGS
                FROM USERS
                WHERE USERID = ?
            """

            self.cursor.execute(query, [user_id])
            user = self.cursor.fetchone()

            if not user:
                return None

            user_id, name, flags, sflags = user
            permissions = self._parse_permissions(flags, sflags)

            return {
                'id': user_id,
                'username': name,
                'flags': flags,
                'sflags': sflags,
                'permissions': permissions
            }

        except Exception as e:
            logger.error(f"Ошибка при получении информации о пользователе: {str(e)}")
            return None

    def get_all_profiles(self) -> List[Dict]:
        """
        Получить список всех профилей доступа
        
        Returns:
            List[Dict]: Список профилей с ID и названием
        """
        try:
            if not self.connection:
                self.connect()

            query = """
                SELECT PROFILEID, NAME
                FROM PROFILE
                ORDER BY NAME
            """

            self.cursor.execute(query)
            rows = self.cursor.fetchall()

            profiles = []
            for row in rows:
                profiles.append({
                    'id': row[0],
                    'name': row[1]
                })

            return profiles

        except Exception as e:
            logger.error(f"Ошибка при получении списка профилей: {str(e)}")
            return []

    def update_card_profile(self, card_id: int, profile_id: int) -> Dict:
        """
        Обновить профиль доступа карты
        
        Args:
            card_id: ID карты (CARDSID)
            profile_id: ID профиля (PROFILEID)
            
        Returns:
            Dict с результатом операции
        """
        try:
            if not self.connection:
                self.connect()

            query = """
                UPDATE CARDS
                SET PROFILEID = ?
                WHERE CARDSID = ?
            """

            self.cursor.execute(query, [profile_id, card_id])
            self.connection.commit()
            
            logger.info(f"Профиль карты {card_id} обновлен на {profile_id}")
            return {'success': True, 'message': 'Профиль успешно обновлен'}

        except Exception as e:
            logger.error(f"Ошибка при обновлении профиля карты: {str(e)}")
            return {'success': False, 'error': str(e)}
        """
        Получить информацию о карте по номеру
        
        Args:
            card_number: Номер карты
            
        Returns:
            Dict с информацией о карте или None
        """
        try:
            if not self.connection:
                self.connect()

            query = """
                SELECT 
                    c.CARDSID,
                    c.CARDNUM,
                    p.FNAME,
                    c.OPENDATE,
                    c.CLOSEDATE,
                    c.ACTIVED,
                    c.COMMENTS
                FROM CARDS c
                LEFT JOIN PEOPLE p ON c.PEOPLEID = p.PEOPLEID
                WHERE c.CARDNUM = ?
            """

            self.cursor.execute(query, [card_number])
            row = self.cursor.fetchone()

            if not row:
                return None

            return {
                'card_id': row[0],
                'card_number': row[1],
                'room': row[2],
                'valid_from': row[3].isoformat() if row[3] else None,
                'valid_until': row[4].isoformat() if row[4] else None,
                'status': row[5],
                'comments': row[6]
            }

        except Exception as e:
            logger.error(f"Ошибка при получении информации о карте: {str(e)}")
            return None
