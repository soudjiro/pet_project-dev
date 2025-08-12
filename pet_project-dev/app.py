from flask import Flask, request, redirect, url_for, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from datetime import datetime
import os, logging

app = Flask(__name__, static_folder='static')
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'todos.db'))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

logging.basicConfig(level=logging.INFO)

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    from pytz import timezone as ZoneInfo  # Для старых версий Python
    
def get_moscow_time():
    """Возвращает текущее время по Москве"""
    try:
        return datetime.now(ZoneInfo("Europe/Moscow"))
    except Exception:
        # Для старых версий Python с pytz
        import pytz
        return datetime.now(pytz.timezone("Europe/Moscow"))

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True) # id задачи
    task = db.Column(db.String(100), nullable=False) # описание задачи
    status = db.Column(db.String(20), default='new', nullable=False)  # 'new', 'active', 'completed'
    # Добавляем поле для тегов (храним как строку с разделителем запятая)
    tags = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=lambda: get_moscow_time(), nullable=False) # Поле когда задачу создали
    started_at = db.Column(db.DateTime)  # Поле когда задачу взяли в работу
    completed_at = db.Column(db.DateTime) # Поле когда задача завершена
    updated_at = db.Column(db.DateTime)  # Поле когда задачу отредактировали
    is_edited = db.Column(db.Boolean, default=False)  # Флаг редактирования
    
# Создаем таблицу для уникальных тегов (опционально для фильтрации)
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    color = db.Column(db.String(7), default='#6c757d')  # Цвет в HEX
    usage_count = db.Column(db.Integer, default=0)  # Добавляем счетчик
        

def check_and_upgrade_db():
    with app.app_context():
        # Проверяем существование таблицы
        inspector = db.inspect(db.engine)
        if 'todo' not in inspector.get_table_names():
            db.create_all()
            return
        
        if 'tag' not in inspector.get_table_names():
            db.create_all()
            return
        
        # Проверяем существование колонок
        columns = [c['name'] for c in inspector.get_columns('todo')]
        
        if 'completed' in columns:
            print("ОШИБКА: Колонка 'completed' все еще существует")
        
        with db.engine.begin() as conn:
            if 'completed' in columns:
                conn.execute(text("ALTER TABLE todo DROP COLUMN completed"))
            if 'status' not in columns:
                conn.execute(text("ALTER TABLE todo ADD COLUMN status VARCHAR(20) DEFAULT 'new'"))
        
        # Добавляем недостающие колонки
        with db.engine.connect() as conn:
            if 'status' not in columns:
                conn.execute(text("ALTER TABLE todo ADD COLUMN status VARCHAR(20) DEFAULT 'new'"))
                conn.execute(text("UPDATE todo SET status = 'active' WHERE completed = 0"))
                conn.execute(text("UPDATE todo SET status = 'completed' WHERE completed = 1"))
                conn.execute(text("ALTER TABLE todo DROP COLUMN completed"))
            if 'started_at' not in columns:
                conn.execute(text("ALTER TABLE todo ADD COLUMN started_at DATETIME"))
            if 'updated_at' not in columns:
                conn.execute(text('ALTER TABLE todo ADD COLUMN updated_at DATETIME'))
            if 'is_edited' not in columns:
                conn.execute(text('ALTER TABLE todo ADD COLUMN is_edited BOOLEAN DEFAULT FALSE'))
            conn.commit()
    
@app.route("/")
def index():
    # Получаем 10 самых популярных тегов
    popular_tags = Tag.query.order_by(Tag.usage_count.desc()).limit(10).all()
    return redirect(url_for("new_tasks", popular_tags=popular_tags))
    
# роут новой задачи
@app.route("/new", methods=["GET", "POST"])
def new_tasks():
    if request.method == "POST":
        task = request.form.get("task")
        tags = request.form.get("tags", "").strip()
        if task:
            new_todo = Todo(task=task, tags=tags, status='new', created_at=get_moscow_time())
            db.session.add(new_todo)
            
        # Опционально: сохраняем новые теги в таблицу Tag
            for tag_name in [t.strip() for t in tags.split(',') if t.strip()]:
                tag = Tag.query.filter_by(name=tag_name).first()
                if tag:
                    tag.usage_count += 1
                else:
                    tag = Tag(name=tag_name, usage_count=1)
                    db.session.add(tag)
            
            db.session.commit()
        
        return redirect(url_for("new_tasks")) # Остаемся на той же вкладке
    
    new = Todo.query.filter_by(status='new').order_by(Todo.created_at.desc()).all()
    return render_template("index.html", todos=new, active_tab='new')
    
@app.route("/active", methods=["GET", "POST"])
def active_tasks():
    active = Todo.query.filter_by(status='active').order_by(Todo.started_at.desc()).all()
    return render_template("index.html", todos=active, active_tab='active')

@app.route("/completed", methods=["GET"])
def completed_tasks():
    completed = Todo.query.filter_by(status='completed').order_by(Todo.completed_at.desc()).all()
    return render_template("index.html", todos=completed, active_tab='completed')  

@app.route('/complete/<int:id>')
def complete_task(id):
    todo = Todo.query.get_or_404(id)
    if todo.status == 'active':
        todo.status = 'completed'
        todo.completed_at = get_moscow_time()
        db.session.commit()
        return jsonify({
            'status': 'success',
            'completed_at': todo.completed_at.strftime('%d.%m.%Y %H:%M')
        })
    return jsonify({'status': 'error', 'message': 'Можно завершать только активные задачи'}), 400

@app.route("/start/<int:id>")
def start_task(id):
    todo = Todo.query.get_or_404(id)
    if todo.status == 'new':
        todo.status = 'active'
        todo.started_at = get_moscow_time()
        db.session.commit()
    return jsonify({'status': 'success'})

@app.route("/edit/<int:id>", methods=["POST"])
def edit_task(id):
    todo = Todo.query.get_or_404(id)
    old_tags = set(todo.tags.split(',')) if todo.tags else set()
    
    new_tags = set(request.form.get('tags', '').split(',')) if request.form.get('tags') else set()
    
    # Обновляем счетчики тегов
    for tag in old_tags - new_tags:
        db_tag = Tag.query.filter_by(name=tag).first()
        if db_tag:
            db_tag.usage_count -= 1
    
    for tag in new_tags - old_tags:
        db_tag = Tag.query.filter_by(name=tag).first()
        if db_tag:
            db_tag.usage_count += 1
        else:
            db_tag = Tag(name=tag, usage_count=1)
            db.session.add(db_tag)
    
    todo.tags = ','.join(new_tags)
    db.session.commit()
    
    if todo.status == 'completed':
        return jsonify({'status': 'error', 'message': 'Нельзя редактировать завершенную задачу'}), 403
    
    new_task = request.form.get('task', '').strip()
    if not new_task:
        return jsonify({'status': 'error', 'message': 'Текст задачи не может быть пустым'}), 400
        
    if new_task != todo.task:
        todo.task = new_task
        todo.tags = request.form.get('tags', '').strip()
        now = get_moscow_time()
        todo.updated_at = now
        todo.is_edited = True
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'updated_at': now.strftime('%d.%m.%Y %H:%M'),
            'is_edited': True,
            'new_text': new_task
        })
    
    return jsonify({'status': 'no_changes'})

    

@app.route("/delete/<int:id>")
def delete(id):
    todo = Todo.query.get_or_404(id)
    
    # Уменьшаем счетчики тегов
    if todo.tags:
        for tag_name in todo.tags.split(','):
            tag = Tag.query.filter_by(name=tag_name.strip()).first()
            if tag:
                tag.usage_count -= 1
    
    db.session.delete(todo)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route("/toggle/<int:id>")
def toggle(id):
    todo = Todo.query.get_or_404(id)
    todo.status = 'completed'
    todo.completed_at = get_moscow_time()
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route("/reactivate/<int:id>", methods=["POST"])  # Разрешаем только POST
def reactivate_task(id):
    logging.info(f"Получен запрос на возврат задачи {id} в работу")
    try:
        todo = Todo.query.get_or_404(id)
        
        if todo.status != 'completed':
            return jsonify({
                'status': 'error',
                'message': 'Только завершенные задачи можно вернуть в работу'
            }), 400
        
        todo.status = 'active'
        todo.completed_at = None
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'new_status': 'active',
            'task_id': todo.id
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Ошибка сервера: {str(e)}'
        }), 500
        
@app.route("/filter/<tag>")
def filter_by_tag(tag):
    # Ищем задачи, содержащие этот тег
    tasks = Todo.query.filter(Todo.tags.contains(tag)).all()
    
    # Увеличиваем счетчик популярности тега
    db_tag = Tag.query.filter_by(name=tag).first()
    if db_tag:
        db_tag.usage_count += 1
        db.session.commit()
    
    popular_tags = Tag.query.order_by(Tag.usage_count.desc()).limit(10).all()
    return render_template("index.html", 
                         todos=tasks, 
                         active_tab='filter',
                         popular_tags=popular_tags,
                         current_tag=tag)

@app.template_filter('format_date')
def format_date_filter(dt, format='%d.%m.%Y %H:%M'):
    if dt is None:
        return "не указано"
    return dt.strftime(format)

if __name__ == "__main__":
    with app.app_context():
        check_and_upgrade_db()
    app.run(host="0.0.0.0", port=5000, debug=True)