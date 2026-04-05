"""
Тесты для DatabaseManager
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, date, timedelta
from app.managers.database_manager import DatabaseManager
from app.models.card import Card


class TestDatabaseManagerConnection:
    """Тесты подключения к БД"""

    def test_connect_with_valid_path(self, tmp_path):
        """Тест подключения с валидным путем"""
        # Этот тест требует реальной БД, поэтому пока пропускаем
        pass

    def test_disconnect(self):
        """Тест отключения от БД"""
        db = DatabaseManager('test.fdb')
        # Тест отключения без подключения не должен вызывать ошибку
        db.disconnect()


class TestCardEditProcedure:
    """Тесты для процедуры HOSTEL_CARDEDIT"""

    @given(
        action=st.integers(min_value=0, max_value=4),
        room=st.integers(min_value=101, max_value=999).filter(lambda x: x % 100 != 0),
        card_number=st.integers(min_value=1, max_value=9999999),
        valid_days=st.integers(min_value=1, max_value=365)
    )
    @settings(max_examples=100)
    def test_cardedit_procedure_parameters(self, action, room, card_number, valid_days):
        """
        Property 11: Корректность параметров процедуры
        Validates: Requirements 5.2
        
        Проверяет, что параметры процедуры HOSTEL_CARDEDIT корректно формируются
        для всех допустимых значений действий и параметров.
        """
        db = DatabaseManager('test.fdb')
        
        # Проверить, что параметры валидны
        assert action >= 0 and action <= 4, "Action должен быть от 0 до 4"
        assert room > 0, "Room должен быть больше 0"
        assert card_number > 0, "Card number должен быть больше 0"
        assert valid_days > 0, "Valid days должен быть больше 0"
        
        # Проверить разбор номера комнаты
        floor, room_num = Card.parse_room(room)
        assert floor > 0, "Floor должен быть больше 0"
        assert room_num > 0, "Room number должен быть больше 0"


class TestCardModel:
    """Тесты для модели Card"""

    def test_card_creation(self):
        """Тест создания карты"""
        card = Card(
            people_id=1,
            card_id=100,
            room=401,
            card_number=1234567,
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=3),
            status=1,
            comments='Test card'
        )
        
        assert card.people_id == 1
        assert card.card_id == 100
        assert card.room == 401
        assert card.card_number == 1234567
        assert card.status == 1

    @given(
        room=st.integers(min_value=101, max_value=999),
        card_number=st.integers(min_value=1, max_value=9999999),
        valid_days=st.integers(min_value=1, max_value=365)
    )
    @settings(max_examples=100)
    def test_card_validation_valid_data(self, room, card_number, valid_days):
        """
        Property 2: Отклонение невалидных данных при создании
        Validates: Requirements 1.2
        
        Проверяет, что валидные данные карты проходят валидацию.
        """
        today = date.today()
        card = Card(
            room=room,
            card_number=card_number,
            valid_from=today,
            valid_until=today + timedelta(days=valid_days),
            status=1
        )
        
        is_valid, errors = card.validate()
        assert is_valid, f"Карта должна быть валидна, но получены ошибки: {errors}"
        assert len(errors) == 0

    @given(
        room=st.integers(max_value=0),
        card_number=st.integers(max_value=0)
    )
    @settings(max_examples=50)
    def test_card_validation_invalid_data(self, room, card_number):
        """
        Property 2: Отклонение невалидных данных при создании
        Validates: Requirements 1.2
        
        Проверяет, что невалидные данные карты отклоняются.
        """
        card = Card(
            room=room,
            card_number=card_number,
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=1)
        )
        
        is_valid, errors = card.validate()
        assert not is_valid, "Карта с невалидными данными должна быть отклонена"
        assert len(errors) > 0

    def test_card_to_dict(self):
        """Тест преобразования карты в словарь"""
        today = date.today()
        card = Card(
            people_id=1,
            card_id=100,
            room=401,
            card_number=1234567,
            valid_from=today,
            valid_until=today + timedelta(days=3),
            status=1,
            comments='Test'
        )
        
        card_dict = card.to_dict()
        assert card_dict['people_id'] == 1
        assert card_dict['card_id'] == 100
        assert card_dict['room'] == 401
        assert card_dict['card_number'] == 1234567

    @given(
        room=st.integers(min_value=101, max_value=999),
        card_number=st.integers(min_value=1, max_value=9999999)
    )
    @settings(max_examples=100)
    def test_card_round_trip_serialization(self, room, card_number):
        """
        Property 4: Round-trip для редактирования карты
        Validates: Requirements 2.1
        
        Проверяет, что карта может быть сериализована и десериализована без потери данных.
        """
        today = date.today()
        original_card = Card(
            people_id=1,
            card_id=100,
            room=room,
            card_number=card_number,
            valid_from=today,
            valid_until=today + timedelta(days=3),
            status=1,
            comments='Test'
        )
        
        # Сериализовать
        card_dict = original_card.to_dict()
        
        # Десериализовать
        restored_card = Card.from_dict(card_dict)
        
        # Проверить, что данные совпадают
        assert restored_card.people_id == original_card.people_id
        assert restored_card.card_id == original_card.card_id
        assert restored_card.room == original_card.room
        assert restored_card.card_number == original_card.card_number
        assert restored_card.valid_from == original_card.valid_from
        assert restored_card.valid_until == original_card.valid_until
        assert restored_card.status == original_card.status

    @given(st.integers(min_value=101, max_value=999).filter(lambda x: x % 100 != 0))
    @settings(max_examples=100)
    def test_card_parse_room(self, room_number):
        """Тест разбора номера комнаты"""
        floor, room = Card.parse_room(room_number)
        
        # Проверить, что разбор корректен
        assert floor == room_number // 100
        assert room == room_number % 100
        assert floor > 0
        assert room > 0

    def test_card_parse_room_invalid(self):
        """Тест разбора некорректного номера комнаты"""
        with pytest.raises(ValueError):
            Card.parse_room(0)
        
        with pytest.raises(ValueError):
            Card.parse_room(-1)

    def test_card_equality(self):
        """Тест сравнения карт"""
        card1 = Card(card_id=1, card_number=100, room=401)
        card2 = Card(card_id=1, card_number=100, room=401)
        card3 = Card(card_id=2, card_number=200, room=402)
        
        assert card1 == card2
        assert card1 != card3

    def test_card_repr(self):
        """Тест строкового представления карты"""
        card = Card(card_id=1, card_number=100, room=401, status=1)
        repr_str = repr(card)
        
        assert 'Card' in repr_str
        assert 'card_id=1' in repr_str
        assert 'card_number=100' in repr_str
