from flask import Flask, request, redirect, url_for, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from datetime import datetime
import os, logging, random

# В начале файла добавим константы статусов
STATUS_NEW = 'new'
STATUS_ACTIVE = 'active'
STATUS_COMPLETED = 'completed'

# Инициализация Flask приложения
app = Flask(__name__, static_folder='static')
# Установка пути к базе данных SQLite
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'todos.db'))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Инициализация SQLAlchemy
db = SQLAlchemy(app)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Обработка зависимости для часовых поясов
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    from pytz import timezone as ZoneInfo  # Для старых версий Python

def convert_existing_dates():
    """Преобразует существующие naive даты в aware (Moscow time)"""
    with app.app_context():
        tasks = Todo.query.all()
        for task in tasks:
            if task.deadline and task.deadline.tzinfo is None:
                task.deadline = make_aware(task.deadline)
            if task.created_at and task.created_at.tzinfo is None:
                task.created_at = make_aware(task.created_at)
            if task.started_at and task.started_at.tzinfo is None:
                task.started_at = make_aware(task.started_at)
            if task.completed_at and task.completed_at.tzinfo is None:
                task.completed_at = make_aware(task.completed_at)
            if task.updated_at and task.updated_at.tzinfo is None:
                task.updated_at = make_aware(task.updated_at)
        
        db.session.commit()
        print("Преобразованы naive даты в aware (Moscow time)")
    
# Функция для получения счетчиков задач
def get_task_counts():
    return {
        STATUS_NEW: Todo.query.filter_by(status=STATUS_NEW).count(),
        STATUS_ACTIVE: Todo.query.filter_by(status=STATUS_ACTIVE).count(),
        STATUS_COMPLETED: Todo.query.filter_by(status=STATUS_COMPLETED).count()
    }
    
# Функция генерации случайного цвета в HEX формате
def random_color():
    return f"#{random.randint(0x10, 0xE0):02x}{random.randint(0x10, 0xE0):02x}{random.randint(0x10, 0xE0):02x}"

# Функция получения текущего времени по Москве    
def get_moscow_time():
    """Возвращает текущее время по Москве"""
    try:
        return datetime.now(ZoneInfo("Europe/Moscow"))
    except Exception:
        import pytz
        return pytz.timezone("Europe/Moscow").localize(datetime.now())
    
# Обновленная функция для преобразования naive datetime в aware
def make_aware(dt):
    """Преобразует naive datetime в aware (Moscow time)"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        try:
            return dt.replace(tzinfo=ZoneInfo("Europe/Moscow"))
        except Exception:
            import pytz
            return pytz.timezone("Europe/Moscow").localize(dt)
    return dt

# Класс задачи
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True) # id задачи
    task = db.Column(db.String(100), nullable=False) # описание задачи
    status = db.Column(db.String(20), default='new', nullable=False)  # 'new', 'active', 'completed'
    tags = db.Column(db.String(200)) # Поле для тегов (хранит строку с тегами через запятую)
    created_at = db.Column(db.DateTime, default=lambda: get_moscow_time(), nullable=False) # Поле когда задачу создали
    started_at = db.Column(db.DateTime)  # Поле когда задачу взяли в работу
    completed_at = db.Column(db.DateTime) # Поле когда задача завершена
    updated_at = db.Column(db.DateTime)  # Поле когда задачу отредактировали
    is_edited = db.Column(db.Boolean, default=False)  # Флаг редактирования
    deadline = db.Column(db.DateTime)  # дедлайн задачи
    
    @property
    def aware_deadline(self):
        return make_aware(self.deadline) if self.deadline else None
        
    @property
    def is_deadline_soon(self):
        """Проверяет, наступает ли дедлайн в течение дня"""
        if not self.deadline:
            return False
            
        deadline = self.aware_deadline
        now = get_moscow_time()
        time_left = deadline - now
        
        # Проверяем, что дедлайн в будущем и осталось менее 24 часов
        return time_left.total_seconds() > 0 and time_left.total_seconds() <= 24 * 3600
        
    @property
    def is_deadline_overdue(self):
        """Проверяет, просрочен ли дедлайн"""
        if not self.deadline or self.status != 'active':
            return False
            
        deadline = self.aware_deadline
        now = get_moscow_time()
        return deadline < now
    
# Класс тега
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False) # Уникальное имя тега
    color = db.Column(db.String(7), default='#6c757d')  # Цвет в HEX формате
    usage_count = db.Column(db.Integer, default=0)  # Счетчик использования
    __table_args__ = (db.Index('idx_tag_name', 'name'),) # Индекс для ускорения поиска
        
# Функция проверки и обновления структуры БД
def check_and_upgrade_db():
    with app.app_context():
        inspector = db.inspect(db.engine)
        table_names = inspector.get_table_names()
        
        # 1. Проверка и создание отсутствующих таблиц
        if 'todo' not in table_names or 'tag' not in table_names:
            db.create_all()
            print("Созданы отсутствующие таблицы")
            return
        
        # 2. Проверка и удаление устаревшей колонки 'completed'
        todo_columns = [c['name'] for c in inspector.get_columns('todo')]
        if 'completed' in todo_columns:
            print("Обнаружена устаревшая колонка 'completed' - удаление")
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE todo DROP COLUMN completed"))
        
        # 3. Добавление отсутствующих колонок в таблицу todo
        with db.engine.begin() as conn:
            # Список необходимых колонок с их типами
            required_columns = {
                'status': "VARCHAR(20) DEFAULT 'new'",
                'started_at': "DATETIME",
                'updated_at': "DATETIME",
                'is_edited': "BOOLEAN DEFAULT FALSE",
                'deadline': "DATETIME"
            }
            
            for col, col_type in required_columns.items():
                if col not in todo_columns:
                    print(f"Добавление отсутствующей колонки: {col}")
                    conn.execute(text(f"ALTER TABLE todo ADD COLUMN {col} {col_type}"))
            
            # 4. Миграция данных из старой структуры (если необходимо)
            if 'status' not in todo_columns:
                print("Перенос данных из старой структуры")
                # Обновляем статусы на основе старого поля completed
                conn.execute(text("UPDATE todo SET status = 'active' WHERE completed = 0"))
                conn.execute(text("UPDATE todo SET status = 'completed' WHERE completed = 1"))
        
        # 5. Проверка индексов для таблицы тегов
        tag_indexes = [idx['name'] for idx in inspector.get_indexes('tag')]
        if 'idx_tag_name' not in tag_indexes:
            print("Создание индекса для тегов")
            with db.engine.begin() as conn:
                conn.execute(text("CREATE INDEX idx_tag_name ON tag (name)"))
        
        # 6. Проверка колонок таблицы тегов
        tag_columns = [c['name'] for c in inspector.get_columns('tag')]
        required_tag_columns = {
            'color': "VARCHAR(7) DEFAULT '#6c757d'",
            'usage_count': "INTEGER DEFAULT 0"
        }
        
        with db.engine.begin() as conn:
            for col, col_type in required_tag_columns.items():
                if col not in tag_columns:
                    print(f"Добавление колонки в теги: {col}")
                    conn.execute(text(f"ALTER TABLE tag ADD COLUMN {col} {col_type}"))
        
        print("Проверка структуры БД завершена")

# Главный маршрут - перенаправление на новые задачи    
@app.route("/")
def index():
    # Получаем 10 самых популярных тегов
    popular_tags = Tag.query.order_by(Tag.usage_count.desc()).limit(10).all()
    return redirect(url_for("new_tasks", popular_tags=popular_tags))
    
# Маршрут для работы с новыми задачами
@app.route("/new", methods=["GET", "POST"])
def new_tasks():
    if request.method == "POST":
        task = request.form.get("task")
        tags = request.form.get("tags", "").strip()
        deadline_str = request.form.get("deadline")  # Получаем дедлайн из формы
        
        # Парсим дедлайн если он указан
        deadline = None
        if deadline_str:
            try:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        
        if task:
            # Создание новой задачи
            new_todo = Todo(
                task=task, 
                tags=tags, 
                status='new', 
                created_at=get_moscow_time(),
                deadline=deadline  # Устанавливаем дедлайн
            )
            db.session.add(new_todo)
            
            # Обработка тегов задачи
            for tag_name in [t.strip() for t in tags.split(',') if t.strip()]:
                tag = Tag.query.filter_by(name=tag_name).first()
                if tag:
                    # Увеличение счетчика существующего тега
                    tag.usage_count += 1
                else:
                    # Создание нового тега
                    tag = Tag(name=tag_name, usage_count=1, color=random_color())
                    db.session.add(tag)
            
            db.session.commit()
        
        return redirect(url_for("new_tasks")) # Остаемся на той же вкладке
    
    # Получение всех новых задач
    new = Todo.query.filter_by(status='new').order_by(Todo.created_at.desc()).all()
    # Получение популярных тегов
    popular_tags = Tag.query.order_by(Tag.usage_count.desc()).limit(10).all()
    # Создание словаря тегов для быстрого доступа
    all_tags_dict = {tag.name: tag for tag in Tag.query.all()}
    task_counts = get_task_counts()
    return render_template("index.html", 
                         todos=new, 
                         active_tab=STATUS_NEW,
                         popular_tags=popular_tags, 
                         all_tags_dict=all_tags_dict,
                         task_counts=task_counts)

# Маршрут для активных задач    
@app.route("/active", methods=["GET", "POST"])
def active_tasks():
    # Получение активных задач
    active = Todo.query.filter_by(status='active').order_by(Todo.started_at.desc()).all()
    popular_tags = Tag.query.order_by(Tag.usage_count.desc()).limit(10).all()
    all_tags_dict = {tag.name: tag for tag in Tag.query.all()}
    task_counts = get_task_counts()
    return render_template("index.html", 
                         todos=active, 
                         active_tab=STATUS_ACTIVE,
                         popular_tags=popular_tags, 
                         all_tags_dict=all_tags_dict,
                         task_counts=task_counts)

# Маршрут для завершенных задач с пагинацией
@app.route("/completed", methods=["GET"])
def completed_tasks():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Запрос с пагинацией
    completed = Todo.query.filter_by(status='completed')\
                         .order_by(Todo.completed_at.desc())\
                         .paginate(page=page, per_page=per_page)
    
    all_tags_dict = {tag.name: tag for tag in Tag.query.all()}
    popular_tags = Tag.query.order_by(Tag.usage_count.desc()).limit(10).all()
    
    task_counts = get_task_counts()
    return render_template("index.html", 
                         todos=completed.items,
                         pagination=completed,
                         active_tab=STATUS_COMPLETED,
                         all_tags_dict=all_tags_dict,
                         popular_tags=popular_tags,
                         task_counts=task_counts)

# Маршрут для завершения задачи
@app.route('/complete/<int:id>')
def complete_task(id):
    todo = Todo.query.get_or_404(id)
    if todo.status == 'active':
        # Изменение статуса и установка времени завершения
        todo.status = 'completed'
        todo.completed_at = get_moscow_time()
        db.session.commit()
        return jsonify({
            'status': 'success',
            'completed_at': todo.completed_at.strftime('%d.%m.%Y %H:%M'),
            'counters': get_task_counts()
        })
    return jsonify({'status': 'error', 'message': 'Можно завершать только активные задачи'}), 400

# Маршрут для начала работы над задачей
@app.route("/start/<int:id>")
def start_task(id):
    todo = Todo.query.get_or_404(id)
    if todo.status == 'new':
        # Изменение статуса и установка времени начала
        todo.status = 'active'
        todo.started_at = get_moscow_time()
        db.session.commit()
        return jsonify({
            'status': 'success',
            'counters': get_task_counts()  # Добавляем счетчики
        })
    return jsonify({'status': 'success'})

# Маршрут для редактирования задачи
@app.route("/edit/<int:id>", methods=["POST"])
def edit_task(id):
    todo = Todo.query.get_or_404(id)
    # Получение старых тегов
    old_tags = set(t.strip() for t in todo.tags.split(',') if t.strip()) if todo.tags else set()
    
    # Получение новых тегов из формы
    new_tags_str = request.form.get('tags', '').strip()
    new_tags = set(t.strip() for t in new_tags_str.split(',') if t.strip())
    all_tags = {tag.name: tag for tag in Tag.query.all()}
    
    # Обновление счетчиков тегов
    for tag in old_tags - new_tags:
        if tag in all_tags:
            db_tag = all_tags[tag]
            if db_tag.usage_count > 0:
                db_tag.usage_count -= 1
            # Удаление тега если он больше не используется
            if db_tag.usage_count == 0:
                db.session.delete(db_tag)
                del all_tags[tag]

    for tag in new_tags - old_tags:
        if tag in all_tags:
            # Увеличение счетчика существующего тега
            db_tag = all_tags[tag]
            db_tag.usage_count += 1
        else:
            # Создание нового тега
            db_tag = Tag(name=tag, usage_count=1, color=random_color())
            db.session.add(db_tag)
            all_tags[tag] = db_tag
            
    # Получаем и парсим дедлайн из формы
    deadline_str = request.form.get('deadline')
    deadline = None
    if deadline_str:
            try:
                # Преобразуем строку в datetime и делаем aware
                naive_deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
                deadline = make_aware(naive_deadline)  # Преобразуем в aware
            except ValueError:
                pass
    # Обновляем дедлайн
    todo.deadline = deadline
    
    todo.tags = ','.join(new_tags)
    db.session.commit()
    
    # Проверка статуса задачи
    if todo.status == 'completed':
        return jsonify({'status': 'error', 'message': 'Нельзя редактировать завершенную задачу'}), 403
    
    new_task = request.form.get('task', '').strip()
    if not new_task:
        return jsonify({'status': 'error', 'message': 'Текст задачи не может быть пустым'}), 400
    
    # Обновление задачи если были изменения    
    if new_task != todo.task or new_tags != old_tags or deadline != todo.deadline:
        todo.task = new_task
        todo.tags = new_tags_str
        now = get_moscow_time()
        todo.updated_at = now
        todo.is_edited = True
        
         # Генерация HTML для тегов
        tags_html = ""
        if todo.tags:
            for tag_name in todo.tags.split(','):
                tag_name = tag_name.strip()
                if tag_name:
                    db_tag = Tag.query.filter_by(name=tag_name).first()
                    color = db_tag.color if db_tag else '#6c757d'
                    tags_html += f'<a href="{url_for("filter_by_tag", tag=tag_name)}" class="tag-badge me-1 mb-1" style="background-color: {color}; color: white;">{tag_name}</a>'
        
        logging.info(f"Editing task {id}")
        logging.info(f"Old deadline: {todo.deadline}, New deadline: {deadline}")
        logging.info(f"Old tags: {old_tags}, New tags: {new_tags}")
        logging.info(f"Old task: {todo.task}, New task: {new_task}")
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'counters': get_task_counts(),
            'updated_at': now.strftime('%d.%m.%Y %H:%M'),
            'is_edited': True,
            'new_text': new_task,
            'tags_html': tags_html,
            'deadline_formatted': format_date_filter(deadline) if deadline else "не определен",
            'is_deadline_soon': todo.is_deadline_soon,
            'is_deadline_overdue': todo.is_deadline_overdue
        })
        
    return jsonify({'status': 'no_changes'})

    
# Маршрут для удаления задачи
@app.route("/delete/<int:id>")
def delete(id):
    todo = Todo.query.get_or_404(id)
    
    # Уменьшение счетчиков тегов
    if todo.tags:
        for tag_name in todo.tags.split(','):
            tag_name = tag_name.strip()
            if tag_name:
                tag = Tag.query.filter_by(name=tag_name).first()
                if tag:
                    tag.usage_count -= 1
                    # Удаление тега если он больше не используется
                    if tag.usage_count == 0:
                        db.session.delete(tag)
    
    # Удаление задачи
    db.session.delete(todo)
    db.session.commit()
    return jsonify({'status': 'success',
                    'counters': get_task_counts()})

# Альтернативный маршрут для завершения задачи (для тестирования)
@app.route("/toggle/<int:id>")
def toggle(id):
    todo = Todo.query.get_or_404(id)
    todo.status = 'completed'
    todo.completed_at = get_moscow_time()
    db.session.commit()
    return jsonify({'status': 'success'})

# Маршрут для возврата задачи в работу
@app.route("/reactivate/<int:id>", methods=["POST"])  # Разрешаем только POST
def reactivate_task(id):
    logging.info(f"Получен запрос на возврат задачи {id} в работу")
    try:
        todo = Todo.query.get_or_404(id)
        
        # Проверка статуса задачи
        if todo.status != 'completed':
            return jsonify({
                'status': 'error',
                'message': 'Только завершенные задачи можно вернуть в работу'
            }), 400
        
        # Изменение статуса
        todo.status = 'active'
        todo.completed_at = None
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'new_status': 'active',
            'task_id': todo.id,
            'counters': get_task_counts()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Ошибка сервера: {str(e)}'
        }), 500

# Маршрут для фильтрации задач по тегу        
@app.route("/filter/<tag>")
def filter_by_tag(tag):
    # Поиск задач по тегу
    tasks = Todo.query.filter(Todo.tags.contains(tag)).all()
    
    # Получение популярных тегов
    popular_tags = Tag.query.order_by(Tag.usage_count.desc()).limit(10).all()
    # Создание словаря тегов
    all_tags_dict = {tag.name: tag for tag in Tag.query.all()}
    task_counts = get_task_counts()
    return render_template("index.html", 
                         todos=tasks, 
                         active_tab='filter',
                         popular_tags=popular_tags,
                         all_tags_dict=all_tags_dict,
                         current_tag=tag,
                         task_counts=task_counts)

# API для получения тегов (для автодополнения)    
@app.route("/api/tags")
def get_tags():
    search = request.args.get('search', '')
    # Поиск тегов по подстроке
    tags = Tag.query.filter(Tag.name.ilike(f'%{search}%')).order_by(Tag.usage_count.desc()).limit(10).all()
    return jsonify([tag.name for tag in tags])

# Новый API для проверки просроченных задач
@app.route("/api/check-deadlines")
def check_deadlines():
    now = get_moscow_time()
    # Находим активные задачи с дедлайном
    active_tasks = Todo.query.filter(
        Todo.status == STATUS_ACTIVE,
        Todo.deadline.isnot(None)
    ).all()
    
    overdue_tasks = []
    soon_tasks = []
    
    for task in active_tasks:
        deadline = make_aware(task.deadline)
        time_left = deadline - now
        seconds_left = time_left.total_seconds()
        
        if seconds_left < 0:
            # Просроченная задача
            overdue_tasks.append({
                'id': task.id,
                'task': task.task,
                'deadline': deadline.strftime('%d.%m.%Y %H:%M'),
                'overdue_minutes': int(-seconds_left / 60)
            })
        elif seconds_left <= 24 * 3600:  # 24 часа
            # Дедлайн скоро наступит (менее 24 часов)
            soon_tasks.append({
                'id': task.id,
                'task': task.task,
                'deadline': deadline.strftime('%d.%m.%Y %H:%M'),
                'hours_left': int(seconds_left / 3600)
            })
    
    return jsonify({
        'overdue_count': len(overdue_tasks),
        'overdue_tasks': overdue_tasks,
        'soon_count': len(soon_tasks),
        'soon_tasks': soon_tasks
    })

# Маршрут для обновления счетчиков тегов
@app.route("/refresh-tags")
def refresh_tags():
    # Пересчет счетчиков тегов
    all_tags_dict = {tag.name: tag for tag in Tag.query.all()}
    tag_names = {tag.name for tag in all_tags_dict}
    
    # Сброс счетчиков
    for tag in all_tags_dict:
        tag.usage_count = 0
    
    ## Пересчет использования тегов
    todos = Todo.query.all()
    for todo in todos:
        if todo.tags:
            for tag_name in todo.tags.split(','):
                tag_name = tag_name.strip()
                if tag_name in tag_names:
                    tag = next((t for t in all_tags_dict if t.name == tag_name), None)
                    if tag:
                        tag.usage_count += 1
    
    db.session.commit()
    return jsonify({'status': 'success'})

# Фильтр для форматирования дат в шаблонах
@app.template_filter('format_date')
def format_date_filter(dt, format='%d.%m.%Y %H:%M'):
    if dt is None:
        return "не указано"
    return dt.strftime(format)

# Запуск приложения
if __name__ == "__main__":
    with app.app_context():
        # Проверка и обновление структуры БД
        check_and_upgrade_db()
        # Преобразование существующих дат
        convert_existing_dates()
     # Запуск Flask приложения
    app.run(host="0.0.0.0", port=5000, debug=True)