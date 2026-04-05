"""
Веб-приложение для управления картами (пропусками) в хостеле.
Взаимодействует с базой данных Firebird через процедуру HOSTEL_CARDEDIT.
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, make_response, flash
import os
import json
from dotenv import load_dotenv
import tempfile
import shutil
import logging
from datetime import datetime

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

@app.context_processor
def inject_db_path():
    return {'db_path': session.get('db_path')}

@app.route('/api/pick-db-file', methods=['POST'])
def pick_db_file():
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askopenfilename(
            title='Выберите файл базы данных (.fdb)',
            filetypes=[('Firebird database', '*.fdb'), ('All files', '*.*')],
        )
        root.destroy()
        return jsonify({'path': path or None})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    history: list = []
    try:
        history_cookie = request.cookies.get('db_history')
        if history_cookie:
            history = json.loads(history_cookie)
            if not isinstance(history, list):
                history = []
    except Exception as e:
        logger.error(f"Error parsing history cookie: {e}")
        history = []

    history_entries = []
    for item in history:
        if isinstance(item, dict) and 'path' in item:
            history_entries.append(item)
        elif isinstance(item, str):
            history_entries.append({'path': item, 'ts': None, 'status': 'OK'})

    history_paths = []
    history_log_lines = []
    for entry in history_entries:
        path = entry.get('path')
        if not path:
            continue
        history_paths.append(path)
        ts = entry.get('ts')
        status = entry.get('status') or ''
        error_short = entry.get('error')
        line = f"{ts or ''} {status} {path}".strip()
        if error_short:
            line = f"{line} | {error_short}"
        history_log_lines.append(line)

    selected_db_path = request.form.get('db_path', '')

    firebird_client_path = None
    try:
        from app.managers.database_manager import get_fbclient_path
        firebird_client_path = get_fbclient_path()
    except Exception:
        firebird_client_path = None

    if request.method == 'POST':
        db_path = None
        
        # Проверить загруженный файл
        if 'db_file' in request.files:
            file = request.files['db_file']
            if file and file.filename and file.filename.endswith('.fdb'):
                # Сохранить загруженный файл во временную папку
                temp_dir = tempfile.gettempdir()
                uploaded_path = os.path.join(temp_dir, file.filename)
                try:
                    file.save(uploaded_path)
                    db_path = uploaded_path
                except Exception as e:
                    logger.error(f"Error saving uploaded file: {str(e)}")
                    return render_template('select_database.html', error=f'Ошибка при сохранении файла: {str(e)}', history=history)
        
        # Если файл не загружен, использовать введенный путь
        if not db_path:
            db_path = request.form.get('db_path')
        
        # Проверка пути (локальный или сетевой)
        is_network_path = False
        if db_path and ':' in db_path:
            # Проверить, не является ли это буквой диска (C:\...)
            parts = db_path.split(':', 1)
            # Если первая часть - одна буква, это скорее всего диск Windows
            if len(parts[0]) == 1 and parts[0].isalpha():
                is_network_path = False
            else:
                is_network_path = True

        if not db_path or (not is_network_path and not os.path.exists(db_path)):
            return render_template('select_database.html', error='Файл не найден или не выбран', history=history)
        
        try:
            # Проверка подключения
            test_db = DatabaseManager(db_path)
            test_db.connect()
            test_db.disconnect()
            
            session['db_path'] = db_path
            
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            history_entries = [e for e in history_entries if e.get('path') != db_path]
            history_entries.insert(0, {'path': db_path, 'ts': ts, 'status': 'OK'})
            history_entries = history_entries[:10]
            
            resp = make_response(redirect(url_for('login')))
            # Сохраняем куку на 30 дней
            resp.set_cookie('db_history', json.dumps(history_entries, ensure_ascii=False), max_age=30*24*60*60)
            return resp
            
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            err = str(e).replace('\n', ' ').strip()
            if len(err) > 120:
                err = err[:120] + '…'
            if db_path:
                history_entries = [entry for entry in history_entries if entry.get('path') != db_path]
                history_entries.insert(0, {'path': db_path, 'ts': ts, 'status': 'ERR', 'error': err})
                history_entries = history_entries[:10]
            resp = make_response(
                render_template(
                    'select_database.html',
                    error=f'Ошибка подключения: {str(e)}',
                    history_paths=[e.get('path') for e in history_entries if e.get('path')],
                    history_log='\n'.join(
                        [
                            (
                                f"{entry.get('ts') or ''} {entry.get('status') or ''} {entry.get('path') or ''}".strip()
                                + (f" | {entry.get('error')}" if entry.get('error') else '')
                            )
                            for entry in history_entries
                            if entry.get('path')
                        ]
                    ),
                    db_path_value=db_path or '',
                    firebird_client_path=firebird_client_path,
                )
            )
            resp.set_cookie('db_history', json.dumps(history_entries, ensure_ascii=False), max_age=30*24*60*60)
            return resp
    
    return render_template(
        'select_database.html',
        history_paths=history_paths,
        history_log='\n'.join(history_log_lines),
        db_path_value=selected_db_path,
        firebird_client_path=firebird_client_path,
    )

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

@app.route('/disconnect-db')
def disconnect_db():
    """Отключиться от базы данных"""
    global db_manager
    if db_manager:
        try:
            db_manager.disconnect()
        except Exception as e:
            logger.error(f"Ошибка при отключении от БД: {str(e)}")
        db_manager = None
    session.pop('db_path', None)
    flash('Отключение от базы данных выполнено', 'info')
    return redirect(url_for('select_database'))

@app.route('/test-api')
def test_api():
    """Страница тестирования API"""
    if 'user_id' not in session:
        if 'db_path' not in session:
            return redirect(url_for('select_database'))
        return redirect(url_for('login'))
    return render_template('test_api.html')

@app.route('/api/test-procedure', methods=['POST'])
def test_procedure():
    """Тестировать процедуру HOSTEL_CARDEDIT"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid JSON payload'}), 400
    
    try:
        global db_manager
        if db_manager is None:
            db_manager = DatabaseManager(session['db_path'])
        
        result = db_manager.call_cardedit_procedure(
            action=data.get('action'),
            room=data.get('room'),
            card_number=data.get('card_number'),
            valid_from=data.get('valid_from'),
            valid_days=data.get('valid_days'),
            comments=data.get('comments'),
            dep=data.get('dep', 'ХОСТЕЛ')
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Ошибка при тестировании процедуры: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
    
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid JSON payload'}), 400

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
    """Получить список карт с фильтрацией и пагинацией"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        global db_manager
        if db_manager is None:
            db_manager = DatabaseManager(session['db_path'])
        
        # Получаем параметры пагинации и фильтрации
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Собираем фильтры
        filters = {}
        if request.args.get('card_number'):
            filters['card_number'] = request.args.get('card_number')
        if request.args.get('profile_id'):
            filters['profile_id'] = request.args.get('profile_id')
        if request.args.get('status') is not None and request.args.get('status') != '':
            filters['status'] = request.args.get('status', type=int)
        
        result = db_manager.get_all_cards(page=page, per_page=per_page, filters=filters)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cards', methods=['POST'])
def create_card():
    """Создать новую карту"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid JSON payload'}), 400
    
    try:
        global db_manager
        if db_manager is None:
            db_manager = DatabaseManager(session['db_path'])
        
        # Сначала создаем карту через процедуру
        result = db_manager.call_cardedit_procedure(
            action=1,
            room=data.get('room'),
            card_number=data.get('card_number'),
            valid_from=data.get('valid_from'),
            valid_days=data.get('valid_days'),
            comments=data.get('comments'),
            dep=data.get('dep', 'ХОСТЕЛ')
        )
        
        # Если карта успешно создана и указан профиль, обновляем профиль
        if result.get('card_id') and result.get('card_id') > 0 and data.get('profile_id'):
            profile_result = db_manager.update_card_profile(result['card_id'], data.get('profile_id'))
            if not profile_result.get('success'):
                logger.warning(f"Не удалось обновить профиль для карты {result['card_id']}")
        
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
        
        card = db_manager.get_card_by_id(card_id)
        if card:
            return jsonify(card)
        else:
            return jsonify({'error': 'Card not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cards/<int:card_id>', methods=['PUT'])
def update_card(card_id):
    """Обновить карту"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid JSON payload'}), 400
    
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
        
        # Если указан профиль, обновляем его
        if result.get('card_id') and result.get('card_id') > 0 and data.get('profile_id'):
            profile_result = db_manager.update_card_profile(result['card_id'], data.get('profile_id'))
            if not profile_result.get('success'):
                logger.warning(f"Не удалось обновить профиль для карты {result['card_id']}")
        
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
