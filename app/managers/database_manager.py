"""
DatabaseManager для работы с базой данных Firebird.
Управляет подключением и выполнением операций с картами через процедуру HOSTEL_CARDEDIT.
"""

import fdb
import logging
import os
import sys
import platform
import ctypes
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_LOADED_FBCLIENT_PATH: str | None = None

def _get_loaded_fbclient_version() -> str | None:
    try:
        import fdb.fbcore as fbcore
        api = getattr(fbcore, 'api', None)
        if not api:
            return None
        if not hasattr(api, 'isc_get_client_version'):
            return None
        buf = ctypes.create_string_buffer(256)
        api.isc_get_client_version(buf)
        version = buf.value.decode('ascii', errors='ignore').strip()
        return version or None
    except Exception:
        return None

def _parse_fb_major(version: str | None) -> int | None:
    if not version:
        return None
    idx = version.lower().rfind('firebird')
    if idx == -1:
        return None
    tail = version[idx + len('firebird'):].strip()
    digits = []
    for ch in tail:
        if ch.isdigit():
            digits.append(ch)
        elif digits:
            break
    if not digits:
        return None
    try:
        return int(''.join(digits))
    except ValueError:
        return None

def load_fbclient():
    """
    Пытается загрузить библиотеку клиента Firebird (fbclient.dll/libfbclient.so).
    Проверяет переменную окружения FB_LIBRARY_PATH, затем локальную директорию.
    """
    try:
        candidates: List[str] = []

        fb_lib_path = os.environ.get('FB_LIBRARY_PATH') or os.environ.get('FIREBIRD_CLIENT')
        if fb_lib_path:
            fb_lib_path = os.path.expandvars(os.path.expanduser(fb_lib_path))
            if os.path.isdir(fb_lib_path):
                candidates.append(os.path.join(fb_lib_path, 'fbclient.dll'))
            candidates.append(fb_lib_path)

        candidates.append(os.path.join(os.getcwd(), 'fbclient.dll'))

        if platform.system().lower() == 'windows':
            program_files = os.environ.get('ProgramFiles')
            program_files_x86 = os.environ.get('ProgramFiles(x86)')
            for base in [program_files, program_files_x86]:
                if not base:
                    continue
                candidates.extend(
                    [
                        os.path.join(base, 'Firebird', 'Firebird_5_0', 'bin', 'fbclient.dll'),
                        os.path.join(base, 'Firebird', 'Firebird_5_0', 'fbclient.dll'),
                        os.path.join(base, 'FIrebird', 'Firebird_5_0', 'bin', 'fbclient.dll'),
                        os.path.join(base, 'FIrebird', 'Firebird_5_0', 'fbclient.dll'),
                        os.path.join(base, 'Firebird', 'Firebird_4_0', 'bin', 'fbclient.dll'),
                        os.path.join(base, 'Firebird', 'Firebird_4_0', 'fbclient.dll'),
                        os.path.join(base, 'FIrebird', 'Firebird_4_0', 'bin', 'fbclient.dll'),
                        os.path.join(base, 'FIrebird', 'Firebird_4_0', 'fbclient.dll'),
                        os.path.join(base, 'Firebird', 'Firebird_3_0', 'bin', 'fbclient.dll'),
                        os.path.join(base, 'Firebird', 'Firebird_3_0', 'fbclient.dll'),
                        os.path.join(base, 'FIrebird', 'Firebird_3_0', 'bin', 'fbclient.dll'),
                        os.path.join(base, 'FIrebird', 'Firebird_3_0', 'fbclient.dll'),
                        os.path.join(base, 'Firebird', 'Firebird_2_5', 'bin', 'fbclient.dll'),
                        os.path.join(base, 'Firebird', 'Firebird_2_5', 'fbclient.dll'),
                        os.path.join(base, 'FIrebird', 'Firebird_2_5', 'bin', 'fbclient.dll'),
                        os.path.join(base, 'FIrebird', 'Firebird_2_5', 'fbclient.dll'),
                    ]
                )
            candidates.extend(
                [
                    os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32', 'fbclient.dll'),
                    r'C:\GUARDE\tools\DLL\FBClient\System32\FBCLIENT.DLL',
                ]
            )

        last_error: Exception | None = None
        loaded_version: str | None = None
        for path in candidates:
            if not path:
                continue
            if not os.path.exists(path):
                continue
            try:
                logger.info(f"Loading Firebird client: {path}")
                fdb.load_api(path)
                global _LOADED_FBCLIENT_PATH
                _LOADED_FBCLIENT_PATH = path
                loaded_version = _get_loaded_fbclient_version()
                major = _parse_fb_major(loaded_version)
                if major is None or major >= 3:
                    return
            except Exception as e:
                last_error = e
                continue

        if last_error:
            logger.warning(f"Failed to explicitly load Firebird client library: {last_error}")
    except Exception as e:
        logger.warning(f"Failed to explicitly load Firebird client library: {e}")

# Вызываем загрузку при импорте модуля
load_fbclient()

def get_fbclient_path() -> str | None:
    return _LOADED_FBCLIENT_PATH


class DatabaseManager:
    """Менеджер для работы с базой данных Firebird"""

    def __init__(self, db_path: str, host: str = 'localhost', port: int = 3050, 
                 user: str = 'SYSDBA', password: str = 'masterkey'):
        """
        Инициализация DatabaseManager
        
        Args:
            db_path: Путь к файлу базы данных guardee.fdb (может быть в формате host:path)
            host: Хост базы данных (по умолчанию localhost)
            port: Порт базы данных (по умолчанию 3050)
            user: Пользователь БД (по умолчанию SYSDBA)
            password: Пароль БД (по умолчанию masterkey)
        """
        self.original_db_path = db_path
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        
        # Парсинг пути если он в формате host:path и host не задан явно (или равен дефолтному)
        if ':' in db_path and host == 'localhost':
            # Сначала пробуем разделить по первому двоеточию
            parts = db_path.split(':', 1)
            
            # Проверка, что первая часть - это не буква диска Windows (C:\...)
            # Если первая часть - одна буква, это диск.
            # Но если путь вида 192.168.1.1:C:\path, то первая часть будет IP.
            
            first_part = parts[0]
            
            is_windows_drive = len(first_part) == 1 and first_part.isalpha()
            
            if not is_windows_drive:
                self.host = first_part
                self.db_path = parts[1]
            else:
                self.db_path = db_path
        else:
            self.db_path = db_path

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
            
            error_str = str(e)
            if 'sqlcode: -923' in error_str.lower() or 'connection rejected by remote interface' in error_str.lower():
                client_version = _get_loaded_fbclient_version()
                msg = (
                    "Ошибка: Firebird сервер отклонил подключение (connection rejected by remote interface).\n"
                    f"Firebird Client: {client_version or 'не определено'}\n"
                    "Чаще всего это означает, что загружен слишком старый fbclient.dll (например Firebird 2.5), "
                    "который не поддерживает аутентификацию/протокол Firebird 5.\n"
                    "Установите Firebird Client x64 версии 3/4/5 (под разрядность вашего Python) и укажите путь "
                    "к fbclient.dll через переменную окружения FB_LIBRARY_PATH (можно путь к файлу или папке bin).\n"
                    "После этого перезапустите приложение."
                )
                logger.error(msg)
                raise Exception(msg) from e

            if (
                'fbclient.dll' in error_str.lower()
                and ('could not find module' in error_str.lower() or 'winerror 126' in error_str.lower())
            ):
                fb_lib_path = os.environ.get('FB_LIBRARY_PATH') or os.environ.get('FIREBIRD_CLIENT')
                msg = (
                    "Ошибка: не удалось загрузить Firebird Client (fbclient.dll) или одну из его зависимостей.\n"
                    f"FB_LIBRARY_PATH/FIREBIRD_CLIENT: {fb_lib_path!r}\n"
                    "Проверьте, что путь указывает на существующий fbclient.dll (или папку bin с ним).\n"
                    "Если fbclient.dll существует, установите Microsoft Visual C++ Redistributable (x64/x86) "
                    "соответствующий разрядности вашего Python и клиента Firebird.\n"
                    "После установки перезапустите приложение."
                )
                logger.error(msg)
                raise Exception(msg) from e

            # Обработка ошибки загрузки DLL (WinError 193)
            if "WinError 193" in error_str:
                is_64bit = sys.maxsize > 2**32
                py_arch = "64-bit" if is_64bit else "32-bit"
                msg = (
                    f"Ошибка: Несовпадение архитектуры Python ({py_arch}) и библиотеки Firebird Client (fbclient.dll).\n"
                    f"Убедитесь, что установлена версия Firebird Client той же разрядности, что и Python.\n"
                    f"Попробуйте установить переменную окружения FB_LIBRARY_PATH, указывающую на правильный fbclient.dll."
                )
                logger.error(msg)
                raise Exception(msg) from e
                
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

    def get_all_cards(self, page: int = 1, per_page: int = 10, filters: Dict = None) -> Dict:
        """
        Получить список карт с фильтрацией и пагинацией
        
        Args:
            page: Номер страницы (начиная с 1)
            per_page: Количество карт на странице
            filters: Словарь с фильтрами {column: value}
            
        Returns:
            Dict с картами, общим количеством и информацией о пагинации
        """
        try:
            if not self.connection:
                self.connect()

            # Базовый запрос
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
                WHERE 1=1
            """
            
            params = []
            
            # Применяем фильтры
            if filters:
                if 'card_number' in filters and filters['card_number']:
                    query += " AND c.CARDNUM LIKE ?"
                    params.append(f"%{filters['card_number']}%")
                
                if 'profile_id' in filters and filters['profile_id']:
                    query += " AND c.PROFILEID = ?"
                    params.append(int(filters['profile_id']))
                
                if 'status' in filters and filters['status'] is not None:
                    query += " AND c.ACTIVED = ?"
                    params.append(int(filters['status']))
            
            # Получаем общее количество записей
            count_query = f"SELECT COUNT(*) FROM ({query}) as cnt"
            self.cursor.execute(count_query, params)
            total_count = self.cursor.fetchone()[0]
            
            # Добавляем сортировку и пагинацию
            query += " ORDER BY c.CARDSID DESC"
            
            offset = (page - 1) * per_page
            query += f" ROWS {offset + 1} TO {offset + per_page}"
            
            self.cursor.execute(query, params)
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

            total_pages = (total_count + per_page - 1) // per_page
            
            return {
                'cards': cards,
                'total': total_count,
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages
            }

        except Exception as e:
            logger.error(f"Ошибка при получении списка карт: {str(e)}")
            return {
                'cards': [],
                'total': 0,
                'page': 1,
                'per_page': per_page,
                'total_pages': 0,
                'error': str(e)
            }

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
        Получить список всех профилей доступа с количеством карт
        
        Returns:
            List[Dict]: Список профилей с ID, названием и количеством карт
        """
        try:
            if not self.connection:
                self.connect()

            # Создаем новый курсор для этого запроса
            cursor = self.connection.cursor()
            
            # Сначала получаем все профили
            query = """
                SELECT PROFILEID, NAME
                FROM PROFILE
                ORDER BY NAME
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            profiles = []
            for row in rows:
                profile_id = row[0]
                profile_name = row[1]
                
                # Для каждого профиля считаем количество карт
                count_query = """
                    SELECT COUNT(*)
                    FROM CARDS
                    WHERE PROFILEID = ?
                """
                cursor.execute(count_query, [profile_id])
                count_result = cursor.fetchone()
                card_count = count_result[0] if count_result else 0
                
                profiles.append({
                    'id': profile_id,
                    'name': profile_name,
                    'card_count': card_count
                })
            
            cursor.close()
            return profiles

        except Exception as e:
            logger.error(f"Ошибка при получении списка профилей: {str(e)}")
            return []

    def get_card_by_id(self, card_id: int) -> Optional[Dict]:
        """
        Получить полную информацию о карте по ID
        
        Args:
            card_id: ID карты (CARDSID)
            
        Returns:
            Dict с полной информацией о карте или None
        """
        try:
            if not self.connection:
                self.connect()

            cursor = self.connection.cursor()
            
            query = """
                SELECT 
                    c.CARDSID,
                    c.CARDNUM,
                    c.OPENDATE,
                    c.CLOSEDATE,
                    c.ACTIVED,
                    c.COMMENTS,
                    c.PROFILEID,
                    p.NAME as PROFILE_NAME,
                    pe.POST as ROOM,
                    pe.LNAME as DEP
                FROM CARDS c
                LEFT JOIN PROFILE p ON c.PROFILEID = p.PROFILEID
                LEFT JOIN PEOPLE pe ON c.PEOPLEID = pe.PEOPLEID
                WHERE c.CARDSID = ?
            """

            cursor.execute(query, [card_id])
            row = cursor.fetchone()
            cursor.close()

            if not row:
                return None

            # Вычислить количество дней между датами
            valid_from = row[2]
            valid_until = row[3]
            valid_days = 0
            if valid_from and valid_until:
                valid_days = (valid_until - valid_from).days

            room = row[8]

            logger.info(f"Card {card_id}: POST={row[8]}, LNAME={row[9]}, COMMENTS={row[5]}")

            return {
                'card_id': row[0],
                'card_number': row[1],
                'valid_from': row[2].isoformat() if row[2] else None,
                'valid_until': row[3].isoformat() if row[3] else None,
                'valid_days': valid_days,
                'status': row[4],
                'comments': row[5],
                'profile_id': row[6],
                'profile_name': row[7],
                'room': room,
                'dep': row[9]
            }

        except Exception as e:
            logger.error(f"Ошибка при получении информации о карте: {str(e)}")
            return None

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
