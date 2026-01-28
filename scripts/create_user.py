"""
Скрипт для создания пользователя в базе данных Firebird
"""

import fdb
import sys
import os

def create_user(db_path, username, password):
    """
    Создать пользователя в базе данных
    
    Args:
        db_path: Путь к файлу БД
        username: Имя пользователя
        password: Пароль
    """
    try:
        # Подключиться к БД
        conn = fdb.connect(
            host='localhost',
            port=3050,
            database=db_path,
            user='SYSDBA',
            password='masterkey',
            charset='WIN1251'
        )
        
        cursor = conn.cursor()
        
        # Проверить, существует ли пользователь
        cursor.execute("SELECT USERID FROM USERS WHERE NAME = ?", [username])
        existing_user = cursor.fetchone()
        
        if existing_user:
            print(f"Пользователь '{username}' уже существует")
            cursor.close()
            conn.close()
            return False
        
        # Создать пользователя
        cursor.execute("""
            INSERT INTO USERS (NAME, PASSWD, FLAGS, SFLAGS)
            VALUES (?, ?, ?, ?)
        """, [username, password, 15, 0])  # FLAGS=15 (все права), SFLAGS=0
        
        conn.commit()
        
        print(f"Пользователь '{username}' успешно создан")
        print(f"Логин: {username}")
        print(f"Пароль: {password}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Ошибка: {str(e)}")
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python create_user.py <путь_к_БД> [username] [password]")
        print("Пример: python create_user.py D:\\db\\guardee.fdb hostel hostel")
        sys.exit(1)
    
    db_path = sys.argv[1]
    username = sys.argv[2] if len(sys.argv) > 2 else 'hostel'
    password = sys.argv[3] if len(sys.argv) > 3 else 'hostel'
    
    if not os.path.exists(db_path):
        print(f"Файл БД не найден: {db_path}")
        sys.exit(1)
    
    create_user(db_path, username, password)
