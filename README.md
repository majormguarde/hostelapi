# Веб-интерфейс управления картами (пропусками) хостела

Приложение для управления картами (пропусками) в хостеле с использованием базы данных Firebird.

## Требования

- Python 3.8+
- Firebird 2.5+
- База данных guardee.fdb

## Установка из Git

### 1. Клонировать репозиторий

```bash
git clone https://github.com/majormguarde-bit/hostelapi.git
cd hostelapi
```

### 2. Создать виртуальное окружение

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# или
source venv/bin/activate  # Linux/Mac
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Запуск приложения

```bash
python app.py
```

Приложение будет доступно по адресу: **http://127.0.0.1:5000**

---

## Установка из архива

### 1. Распаковать архив

```bash
unzip hostelapi.zip
cd hostelapi
```

### 2. Создать виртуальное окружение

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# или
source venv/bin/activate  # Linux/Mac
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Запуск приложения

```bash
python app.py
```

Приложение будет доступно по адресу: **http://127.0.0.1:5000**

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# или
source venv/bin/activate  # Linux/Mac
```

### 2. Установить зависимости

```bash
pip install -r requirements.txt
```

### 3. Создать пользователя в БД (опционально)

Если в вашей БД нет пользователя, создайте его:

```bash
python scripts/create_user.py "D:\path\to\guardee.fdb" hostel hostel
```

Или используйте SQL:

```sql
INSERT INTO USERS (NAME, PASSWD, FLAGS, SFLAGS)
VALUES ('hostel', 'hostel', 15, 0);
```

## Запуск приложения

```bash
python app.py
```

Приложение будет доступно по адресу: **http://127.0.0.1:5000**

## Использование

### 1. Выбор базы данных

- Откройте http://127.0.0.1:5000/select-database
- Выберите файл guardee.fdb через:
  - Диалог выбора файла
  - Перетаскивание файла (drag & drop)
  - Ручной ввод пути

### 2. Вход в систему

- Введите логин: `hostel`
- Введите пароль: `hostel`

### 3. Управление картами

- **Просмотр** - список всех карт отображается на главной странице
- **Добавление** - нажмите кнопку "Добавить карту"
- **Редактирование** - нажмите кнопку "Редактировать" рядом с картой
- **Удаление** - нажмите кнопку "Удалить" и подтвердите

## Структура проекта

```
hostel/
├── app.py                          # Главное приложение Flask
├── requirements.txt                # Зависимости
├── README.md                       # Этот файл
├── app/
│   ├── managers/
│   │   ├── database_manager.py    # Работа с БД Firebird
│   │   └── auth_manager.py        # Управление аутентификацией
│   ├── models/
│   │   └── card.py                # Модель карты
│   └── utils/
│       └── error_handler.py       # Обработка ошибок
├── templates/
│   ├── base.html                  # Базовый шаблон
│   ├── index.html                 # Главная страница
│   ├── login.html                 # Страница входа
│   └── select_database.html       # Выбор БД
├── static/
│   ├── css/
│   │   └── custom.css             # Пользовательские стили
│   └── js/
│       ├── main.js                # Основные функции
│       └── cards.js               # Функции управления картами
├── tests/
│   ├── test_database_manager.py   # Тесты БД
│   ├── test_auth_manager.py       # Тесты аутентификации
│   ├── test_routes.py             # Тесты routes
│   ├── test_error_handler.py      # Тесты обработки ошибок
│   └── test_integration.py        # Интеграционные тесты
└── scripts/
    └── create_user.py             # Скрипт создания пользователя
```

## API Endpoints

### Аутентификация

- `GET /select-database` - Страница выбора БД
- `POST /select-database` - Обработка выбора БД
- `GET /login` - Страница входа
- `POST /login` - Обработка входа
- `GET /logout` - Выход

### Карты

- `GET /` - Главная страница
- `GET /cards` - Получить список всех карт (JSON)
- `POST /cards` - Создать новую карту
- `GET /cards/<id>` - Получить данные карты
- `PUT /cards/<id>` - Обновить карту
- `DELETE /cards/<id>` - Удалить карту

## Тестирование

### Запуск всех тестов

```bash
pytest
```

### Запуск конкретного теста

```bash
pytest tests/test_database_manager.py -v
```

### Запуск с покрытием

```bash
pytest --cov=app tests/
```

## Особенности

- ✅ Выбор файла БД через диалог или drag & drop
- ✅ Аутентификация через таблицу USERS
- ✅ Анализ FLAGS и SFLAGS для определения прав
- ✅ CRUD операции с картами
- ✅ Валидация данных (клиент + сервер)
- ✅ Обработка ошибок
- ✅ Отзывчивый UI (Bootstrap 5)
- ✅ REST API
- ✅ Unit и property-based тесты
- ✅ Интеграционные тесты

## Технологический стек

- **Backend**: Flask 3.0.0
- **Database**: Firebird (fdb 2.0.4)
- **ORM**: SQLAlchemy 2.0.23
- **Frontend**: Bootstrap 5, HTML, CSS, JavaScript
- **Testing**: pytest, hypothesis
- **Environment**: python-dotenv

## Лицензия

MIT

## Контакты
- +7 (969) 728-71-71

Для вопросов и предложений обратитесь к разработчикам.
