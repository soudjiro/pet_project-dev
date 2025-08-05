from flask import Flask, request, redirect, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from datetime import datetime
import os
import sqlite3

app = Flask(__name__)
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'todos.db'))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(100), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: get_moscow_time(), nullable=False)
    completed_at = db.Column(db.DateTime)
   
    
def migrate_db():
    """Безопасная миграция базы данных"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Проверяем существующие колонки
    cursor.execute("PRAGMA table_info(todo)")
    columns = {column[1]: column for column in cursor.fetchall()}
    
    # Создаем временную таблицу с новой структурой
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS todo_new (
        id INTEGER PRIMARY KEY,
        task TEXT NOT NULL,
        completed BOOLEAN DEFAULT FALSE,
        created_at DATETIME,
        completed_at DATETIME
    )
    """)
    
    # Если старая таблица существует, переносим данные
    if 'todo' in [t[0] for t in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
        # Определяем какие колонки нужно копировать
        old_columns = [c for c in ['id', 'task', 'completed'] if c in columns]
        select_columns = ', '.join(old_columns)
        #insert_columns = ', '.join(old_columns + ['created_at'])
        
        # Переносим данные
        cursor.execute(f"""
        INSERT INTO todo_new (id, task, completed, created_at)
        SELECT {select_columns}, datetime('now') FROM todo
        """)
        
        # Удаляем старую таблицу
        cursor.execute("DROP TABLE todo")
    
    # Переименовываем новую таблицу
    cursor.execute("ALTER TABLE todo_new RENAME TO todo")
    conn.commit()
    conn.close()
        
def check_db(): # Функция проверки базы данных на корректность
    with app.app_context():
        # Проверяем существование таблицы
        inspector = db.inspect(db.engine)
        if 'todo' not in inspector.get_table_names():
            db.create_all()
            return
        
        # Проверяем существование колонок
        columns = [c['name'] for c in inspector.get_columns('todo')]
        
        if 'completed_at' not in columns:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE todo ADD COLUMN completed_at DATETIME"))
    
@app.route("/")
def index():
    return redirect(url_for("active_tasks"))    
    
@app.route("/active", methods=["GET", "POST"])
def active_tasks():
    if request.method == "POST":
        task = request.form.get("task")
        if task:
            new_todo = Todo(task=task)
            db.session.add(new_todo)
            db.session.commit()
        return redirect(url_for("active_tasks"))
    
    active = Todo.query.filter_by(completed=False).order_by(Todo.created_at.desc()).all()
    return render_template("index.html", todos=active, active_tab='active')

@app.route("/completed", methods=["GET"])  # Убираем POST здесь
def completed_tasks():
    completed = Todo.query.filter_by(completed=True).order_by(Todo.completed_at.desc()).all()
    return render_template("index.html", todos=completed, active_tab='completed')  

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_task(id):
    todo = Todo.query.get_or_404(id)
    
    # Запрещаем редактирование завершенных задач
    if not todo:
        return render_template("404.html"), 404
    if todo.completed:
        return render_template("403.html"), 403
    
    if request.method == "POST":
        todo.task = request.form.get("task")
        db.session.commit()
        return redirect(url_for("active_tasks"))
    
    return render_template("edit.html", todo=todo)

@app.route("/delete/<int:id>")
def delete(id):
    todo = Todo.query.get(id)
    db.session.delete(todo)
    db.session.commit()
    return redirect(url_for("index"))

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    todo = Todo.query.get(id)
    if request.method == "POST":
        todo.task = request.form.get("task")
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("edit.html", todo=todo)

@app.route("/toggle/<int:id>")
def toggle(id):
    todo = Todo.query.get_or_404(id)
    todo.completed = not todo.completed
    todo.completed_at = get_moscow_time() if todo.completed else None
    db.session.commit()
    return redirect(url_for("active_tasks" if not todo.completed else "completed_tasks"))

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('403.html'), 403

@app.errorhandler(404)
def forbidden_error(error):
    return render_template('404.html'), 404

@app.template_filter('format_date')
def format_date_filter(dt, format='%d.%m.%Y %H:%M'):
    if dt is None:
        return "не указано"
    return dt.strftime(format)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Дополнительная проверка при запуске
    app.run(host="0.0.0.0", port=5000, debug=True)