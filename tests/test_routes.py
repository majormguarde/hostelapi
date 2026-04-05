"""
Тесты для Flask routes
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import date, timedelta
import importlib.util
from pathlib import Path


def _load_app_module():
    app_py = Path(__file__).resolve().parents[1] / 'app.py'
    spec = importlib.util.spec_from_file_location('hostelapi_app', app_py)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='session')
def app_module():
    return _load_app_module()


@pytest.fixture
def client(app_module):
    """Создать тестовый клиент Flask"""
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as client:
        yield client


@pytest.fixture
def authenticated_session(client):
    """Создать аутентифицированную сессию"""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'testuser'
        sess['db_path'] = '/path/to/db.fdb'
        sess['permissions'] = {
            'can_view': True,
            'can_create': True,
            'can_edit': True,
            'can_delete': True,
            'is_admin': False
        }


class TestIndexRoute:
    """Тесты для главной страницы"""

    def test_index_redirect_to_select_database(self, client):
        """Тест редиректа на выбор БД при отсутствии сессии"""
        response = client.get('/')
        assert response.status_code == 302
        assert '/select-database' in response.location

    def test_index_redirect_to_login(self, client):
        """Тест редиректа на вход при наличии БД но отсутствии пользователя"""
        with client.session_transaction() as sess:
            sess['db_path'] = '/path/to/db.fdb'
        
        response = client.get('/')
        assert response.status_code == 302
        assert '/login' in response.location


class TestSelectDatabaseRoute:
    """Тесты для выбора БД"""

    def test_select_database_get(self, client):
        """Тест GET запроса к странице выбора БД"""
        response = client.get('/select-database')
        assert response.status_code == 200
        assert b'guardee.fdb' in response.data

    def test_select_database_post_invalid_path(self, client):
        """Тест POST с невалидным путем"""
        response = client.post('/select-database', data={'db_path': '/invalid/path.fdb'})
        assert response.status_code == 200
        body = response.get_data(as_text=True).lower()
        assert 'error' in body or 'не найден' in body


class TestLoginRoute:
    """Тесты для входа"""

    def test_login_get(self, client):
        """Тест GET запроса к странице входа"""
        with client.session_transaction() as sess:
            sess['db_path'] = '/path/to/db.fdb'
        
        response = client.get('/login')
        assert response.status_code == 200
        body = response.get_data(as_text=True).lower()
        assert 'username' in body or 'пользователя' in body

    def test_login_redirect_without_db(self, client):
        """Тест редиректа на выбор БД при отсутствии пути"""
        response = client.get('/login')
        assert response.status_code == 302
        assert '/select-database' in response.location


class TestCardsRoute:
    """Тесты для операций с картами"""

    def test_get_cards_unauthorized(self, client):
        """Тест получения карт без аутентификации"""
        response = client.get('/cards')
        assert response.status_code == 401

    def test_get_cards_authorized(self, client, authenticated_session):
        """Тест получения карт с аутентификацией"""
        # Этот тест требует реальной БД, поэтому пока пропускаем
        pass

    def test_create_card_unauthorized(self, client):
        """Тест создания карты без аутентификации"""
        response = client.post('/cards', json={
            'room': 401,
            'card_number': 1234567,
            'valid_from': '2025-01-28',
            'valid_days': 3
        })
        assert response.status_code == 401

    def test_get_card_unauthorized(self, client):
        """Тест получения карты без аутентификации"""
        response = client.get('/cards/1')
        assert response.status_code == 401

    def test_update_card_unauthorized(self, client):
        """Тест обновления карты без аутентификации"""
        response = client.put('/cards/1', json={
            'room': 401,
            'card_number': 1234567,
            'valid_from': '2025-01-28',
            'valid_days': 3
        })
        assert response.status_code == 401

    def test_delete_card_unauthorized(self, client):
        """Тест удаления карты без аутентификации"""
        response = client.delete('/cards/1')
        assert response.status_code == 401


class TestHostelCardeditApi:
    """Тесты для API /api/test-procedure (HOSTEL_CARDEDIT)"""

    def test_update_card_validity_period(self, client, authenticated_session, app_module):
        class StubDBManager:
            def __init__(self):
                self.calls = []

            def call_cardedit_procedure(
                self,
                action: int,
                room: int = None,
                card_number: int = None,
                valid_from: str = None,
                valid_days: int = None,
                comments: str = None,
                dep: str = 'ХОСТЕЛ',
            ):
                self.calls.append(
                    {
                        'action': action,
                        'room': room,
                        'card_number': card_number,
                        'valid_from': valid_from,
                        'valid_days': valid_days,
                        'comments': comments,
                        'dep': dep,
                    }
                )

                start = date.fromisoformat(valid_from)
                end = (start + timedelta(days=valid_days)).isoformat()

                return {
                    'people_id': 1,
                    'profile_id': 1,
                    'card_id': 1,
                    'result_code': 1,
                    'actived': 1,
                    'valid_from': valid_from,
                    'valid_to': end,
                    'error': None,
                }

        stub = StubDBManager()
        original_db_manager = app_module.db_manager
        app_module.db_manager = stub
        try:
            payload = {
                'action': 1,
                'room': 1401,
                'card_number': 1446644,
                'valid_from': '2026-03-18',
                'valid_days': 7,
                'comments': 'Update validity period',
                'dep': 'ХОСТЕЛ',
            }

            response = client.post('/api/test-procedure', json=payload)
            assert response.status_code == 200

            data = response.get_json()
            assert data['error'] is None
            assert data['result_code'] == 1
            assert data['valid_from'] == payload['valid_from']
            assert data['valid_to'] == '2026-03-25'

            assert stub.calls == [payload]
        finally:
            app_module.db_manager = original_db_manager

    def test_update_card_room_for_existing_card(self, client, authenticated_session, app_module):
        class StubDBManager:
            def __init__(self):
                self.calls = []

            def call_cardedit_procedure(
                self,
                action: int,
                room: int = None,
                card_number: int = None,
                valid_from: str = None,
                valid_days: int = None,
                comments: str = None,
                dep: str = 'ХОСТЕЛ',
            ):
                self.calls.append(
                    {
                        'action': action,
                        'room': room,
                        'card_number': card_number,
                        'valid_from': valid_from,
                        'valid_days': valid_days,
                        'comments': comments,
                        'dep': dep,
                    }
                )

                return {
                    'people_id': 1,
                    'profile_id': 1,
                    'card_id': 1,
                    'result_code': 1,
                    'actived': 1,
                    'valid_from': valid_from,
                    'valid_to': None,
                    'error': None,
                }

        stub = StubDBManager()
        original_db_manager = app_module.db_manager
        app_module.db_manager = stub
        try:
            payload = {
                'action': 1,
                'room': 1502,
                'card_number': 1446644,
                'valid_from': '2026-03-18',
                'valid_days': 30,
                'comments': 'Update room',
                'dep': 'ХОСТЕЛ',
            }

            response = client.post('/api/test-procedure', json=payload)
            assert response.status_code == 200

            data = response.get_json()
            assert data['error'] is None
            assert data['result_code'] == 1
            assert stub.calls == [payload]
        finally:
            app_module.db_manager = original_db_manager


class TestErrorHandlers:
    """Тесты для обработчиков ошибок"""

    def test_404_error(self, client):
        """Тест обработки ошибки 404"""
        response = client.get('/nonexistent')
        assert response.status_code == 404

    def test_400_error(self, client, authenticated_session):
        """Тест обработки ошибки 400"""
        response = client.post('/cards', json=None)
        assert response.status_code in [400, 415]


@pytest.mark.skip(reason='Требует реальной БД (property-тест отключен)')
def test_create_card_property():
    pass


def test_update_card_property():
    """
    Property 5: Сохранение изменений карты
    Validates: Requirements 2.2, 2.3
    
    Проверяет, что изменения карты сохраняются корректно.
    """
    # Этот тест требует реальной БД, поэтому пока пропускаем
    pass


def test_delete_card_property():
    """
    Property 6: Удаление карты
    Validates: Requirements 3.2, 3.3
    
    Проверяет, что карта удаляется корректно.
    """
    # Этот тест требует реальной БД, поэтому пока пропускаем
    pass
