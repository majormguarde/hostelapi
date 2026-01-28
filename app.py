"""
Веб-приложение для управления картами (пропусками) в хостеле.
Взаимодействует с базой данных Firebird через процедуру HOSTEL_CARDEDIT.
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
from dotenv import load_dotenv
import tempfile
import shutil
import logging

load_dotenv()

# Настроить логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Конфигурация
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 час

# Инициализация расширений
from app.managers.database_manager import DatabaseManager
from app.managers.auth_manager import AuthManager

db_manager = None
auth_manager = AuthManager()

@app.before_request
def before_request():
    """Инициализация db_manager перед каждым запросом"""
    global db_manager
    if db_manager is None and 'db_path' in session:
        db_manager = DatabaseManager(session['db_path'])

@app.route('/')
def index():
    """Главная страница"""
    if 'user_id' not in session:
        if 'db_path' not in session:
            return redirect(url_for('select_database'))
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/select-database', methods=['GET', 'POST'])
def select_database():
    """Выбор файла базы данных"""
    if request.method == 'POST':
        db_path = None
        
        # Проверить загруженный файл
        if 'db_file' in request.files:
            file = request.files['db_file']
            if file and file.filename and file.filename.endswith('.fdb'):
                # Сохранить загруженный файл во временную папку
                temp_dir = tempfile.gettempdir()
                db_path = os.path.join(temp_dir, file.filename)
                try:
                    file.save(db_path)
                except Exception as e:
                    logger.error(f"Error saving uploaded file: {str(e)}")
                    return render_template('select_database.html', error=f'Ошибка при сохранении файла: {str(e)}')
        
        # Если файл не загружен, использовать введенный путь
        if not db_path:
            db_path = request.form.get('db_path')
        
        if not db_path or not os.path.exists(db_path):
            return render_template('select_database.html', error='Файл не найден или не выбран')
        
        try:
            # Проверка подключения
            test_db = DatabaseManager(db_path)
            test_db.connect()
            test_db.disconnect()
            
            session['db_path'] = db_path
            return redirect(url_for('login'))
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            return render_template('select_database.html', error=f'Ошибка подключения: {str(e)}')
    
    return render_template('select_database.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if 'db_path' not in session:
        return redirect(url_for('select_database'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('login.html', error='Введите имя пользователя и пароль')
        
        try:
            # ВРЕМЕННО: Отключена проверка логина и пароля
            # Разрешаем вход для всех логинов и паролей
            session['user_id'] = 1
            session['username'] = username
            session['permissions'] = {
                'can_view': True,
                'can_create': True,
                'can_edit': True,
                'can_delete': True,
                'is_admin': True
            }
            logger.info(f"Пользователь {username} успешно вошел в систему (проверка отключена)")
            return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Ошибка аутентификации: {str(e)}")
            return render_template('login.html', error=f'Ошибка аутентификации: {str(e)}')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Выход из приложения"""
    session.clear()
    return redirect(url_for('select_database'))

@app.route('/profiles', methods=['GET'])
def get_profiles():
    """Получить список всех профилей доступа"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        global db_manager
        if db_manager is None:
            db_manager = DatabaseManager(session['db_path'])
        
        profiles = db_manager.get_all_profiles()
        return jsonify(profiles)
    except Exception as e:
        logger.error(f"Ошибка при получении профилей: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/cards/<int:card_id>/profile', methods=['PUT'])
def update_card_profile(card_id):
    """Обновить профиль доступа карты"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    profile_id = data.get('profile_id')
    
    if not profile_id:
        return jsonify({'error': 'Profile ID is required'}), 400
    
    try:
        global db_manager
        if db_manager is None:
            db_manager = DatabaseManager(session['db_path'])
        
        result = db_manager.update_card_profile(card_id, profile_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Ошибка при обновлении профиля: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/cards', methods=['GET'])
def get_cards():
    """Получить список всех карт"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        global db_manager
        if db_manager is None:
            db_manager = DatabaseManager(session['db_path'])
        
        cards = db_manager.get_all_cards()
        return jsonify(cards)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cards', methods=['POST'])
def create_card():
    """Создать новую карту"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    
    try:
        global db_manager
        if db_manager is None:
            db_manager = DatabaseManager(session['db_path'])
        
        result = db_manager.call_cardedit_procedure(
            action=1,
            room=data.get('room'),
            card_number=data.get('card_number'),
            valid_from=data.get('valid_from'),
            valid_days=data.get('valid_days'),
            comments=data.get('comments'),
            dep=data.get('dep', 'ХОСТЕЛ')
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cards/<int:card_id>', methods=['GET'])
def get_card(card_id):
    """Получить данные карты"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        global db_manager
        if db_manager is None:
            db_manager = DatabaseManager(session['db_path'])
        
        result = db_manager.call_cardedit_procedure(action=0, card_number=card_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cards/<int:card_id>', methods=['PUT'])
def update_card(card_id):
    """Обновить карту"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    
    try:
        global db_manager
        if db_manager is None:
            db_manager = DatabaseManager(session['db_path'])
        
        result = db_manager.call_cardedit_procedure(
            action=1,
            room=data.get('room'),
            card_number=card_id,
            valid_from=data.get('valid_from'),
            valid_days=data.get('valid_days'),
            comments=data.get('comments'),
            dep=data.get('dep', 'ХОСТЕЛ')
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cards/<int:card_id>', methods=['DELETE'])
def delete_card(card_id):
    """Удалить карту"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        global db_manager
        if db_manager is None:
            db_manager = DatabaseManager(session['db_path'])
        
        result = db_manager.call_cardedit_procedure(action=2, card_number=card_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(400)
def bad_request(error):
    """Обработка ошибки 400"""
    return jsonify({'error': 'Bad request'}), 400

@app.errorhandler(401)
def unauthorized(error):
    """Обработка ошибки 401"""
    return jsonify({'error': 'Unauthorized'}), 401

@app.errorhandler(403)
def forbidden(error):
    """Обработка ошибки 403"""
    return jsonify({'error': 'Forbidden'}), 403

@app.errorhandler(404)
def not_found(error):
    """Обработка ошибки 404"""
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Обработка ошибки 500"""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True)
