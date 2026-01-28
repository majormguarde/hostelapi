"""
Скрипт для диагностики структуры базы данных
"""

import fdb
import sys

def diagnose_db(db_path):
    """
    Диагностировать структуру БД
    
    Args:
        db_path: Путь к файлу БД
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
        
        print("=" * 80)
        print("ДИАГНОСТИКА СТРУКТУРЫ БД")
        print("=" * 80)
        
        # Проверить таблицу CARDS
        print("\n1. ТАБЛИЦА CARDS:")
        print("-" * 80)
        cursor.execute("""
            SELECT RDB$FIELD_NAME 
            FROM RDB$RELATION_FIELDS 
            WHERE RDB$RELATION_NAME = 'CARDS'
            ORDER BY RDB$FIELD_POSITION
        """)
        fields = cursor.fetchall()
        for field in fields:
            print(f"  - {field[0].strip()}")
        
        # Проверить таблицу DEP
        print("\n2. ТАБЛИЦА DEP:")
        print("-" * 80)
        cursor.execute("""
            SELECT RDB$FIELD_NAME 
            FROM RDB$RELATION_FIELDS 
            WHERE RDB$RELATION_NAME = 'DEP'
            ORDER BY RDB$FIELD_POSITION
        """)
        fields = cursor.fetchall()
        for field in fields:
            print(f"  - {field[0].strip()}")
        
        # Проверить таблицу PEOPLE
        print("\n3. ТАБЛИЦА PEOPLE:")
        print("-" * 80)
        cursor.execute("""
            SELECT RDB$FIELD_NAME 
            FROM RDB$RELATION_FIELDS 
            WHERE RDB$RELATION_NAME = 'PEOPLE'
            ORDER BY RDB$FIELD_POSITION
        """)
        fields = cursor.fetchall()
        for field in fields:
            print(f"  - {field[0].strip()}")
        
        # Показать примеры данных из CARDS
        print("\n4. ПРИМЕРЫ ДАННЫХ ИЗ CARDS:")
        print("-" * 80)
        cursor.execute("SELECT * FROM CARDS ROWS 5")
        rows = cursor.fetchall()
        if rows:
            for i, row in enumerate(rows, 1):
                print(f"  Запись {i}: {row}")
        else:
            print("  Нет данных в таблице CARDS")
        
        # Показать примеры данных из DEP
        print("\n5. ПРИМЕРЫ ДАННЫХ ИЗ DEP:")
        print("-" * 80)
        cursor.execute("SELECT * FROM DEP ROWS 10")
        rows = cursor.fetchall()
        if rows:
            for i, row in enumerate(rows, 1):
                print(f"  Запись {i}: {row}")
        else:
            print("  Нет данных в таблице DEP")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python diagnose_db.py <путь_к_БД>")
        print("Пример: python diagnose_db.py D:\\db\\guardee.fdb")
        sys.exit(1)
    
    db_path = sys.argv[1]
    diagnose_db(db_path)
