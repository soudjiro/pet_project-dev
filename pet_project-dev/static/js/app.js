document.addEventListener('DOMContentLoaded', function() {



    // Обработчик для кнопки "Выполнено"
    document.addEventListener('click', async function(e) {
        if (e.target.closest('.start-btn')) {
            e.preventDefault();
            const btn = e.target.closest('.start-btn');
            const taskId = btn.dataset.taskId;
            const taskElement = document.getElementById(`task-${taskId}`);
            
            taskElement.classList.add('task-starting');
            
            try {
                const response = await fetch(`/start/${taskId}`);
                const data = await response.json();
                
                if (data.status === 'success') {
                    taskElement.classList.add('task-deleting');
                    setTimeout(() => {
                        taskElement.remove();
                    }, 400);
                }
            } catch (error) {
                console.error('Error:', error);
                taskElement.classList.remove('task-starting');
            }
        }

        if (e.target.closest('.complete-btn')) {
            e.preventDefault();
            const btn = e.target.closest('.complete-btn');
            const taskId = btn.dataset.taskId;
            const taskElement = document.getElementById(`task-${taskId}`);
            
            // Добавляем анимацию
            taskElement.classList.add('task-completing');
            
            try {
                const response = await fetch(`/complete/${taskId}`);
                const data = await response.json();
                
                if (data.status === 'success') {
                    // Плавное удаление задачи из списка
                    taskElement.classList.add('task-deleting');
                    setTimeout(() => {
                        taskElement.remove();
                    }, 400);
                }
            } catch (error) {
                console.error('Error:', error);
                taskElement.classList.remove('task-completing');
            }
        }
        
        // Обработчик для кнопки "Вернуть в активные"
        if (e.target.closest('.reactivate-btn')) {
            e.preventDefault();
            const btn = e.target.closest('.reactivate-btn');
            const taskId = btn.dataset.taskId;
            const taskElement = document.getElementById(`task-${taskId}`);
            
            // Добавляем анимацию
            taskElement.classList.add('task-reactivate');
            
            try {
                const response = await fetch(`/reactivate/${taskId}`);
                const data = await response.json();
                
                if (data.status === 'success') {
                    // Плавное удаление задачи из списка
                    taskElement.classList.add('task-deleting');
                    setTimeout(() => {
                        taskElement.remove();
                    }, 400);
                }
            } catch (error) {
                console.error('Error:', error);
                taskElement.classList.remove('task-reactivate');
            }
        }
        
        // Обработчик для кнопки удаления (остается без изменений)
        if (e.target.closest('.delete-btn')) {
            e.preventDefault();
            const btn = e.target.closest('.delete-btn');
            const taskId = btn.dataset.taskId;
            const taskElement = document.getElementById(`task-${taskId}`);
            
            if (confirm('Вы уверены, что хотите удалить эту задачу?')) {
                taskElement.classList.add('task-deleting');
                
                try {
                    await fetch(`/delete/${taskId}`, { method: 'POST' });
                    setTimeout(() => {
                        taskElement.remove();
                    }, 400);
                } catch (error) {
                    console.error('Error:', error);
                    taskElement.classList.remove('task-deleting');
                }
            }
        }
    });


    const modal = document.getElementById("editModal");
    const closeBtn = document.querySelector(".close");
    const editForm = document.getElementById("editForm");

    // Открытие модального окна
    document.addEventListener('click', function(e) {
        if (e.target.closest('.edit-btn')) {
            const taskId = e.target.closest('button').dataset.taskId;
            const taskElement = document.getElementById(`task-${taskId}`);
            const taskText = taskElement.querySelector('.task-content').firstChild.textContent.trim();
            
            document.getElementById("editTaskId").value = taskId;
            document.getElementById("editTaskText").value = taskText;
            modal.style.display = "block";
        }
    });

    // Закрытие модального окна
    closeBtn.onclick = function() {
        modal.style.display = "none";
    }

    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }

    // Обработка формы редактирования
editForm.onsubmit = async function(e) {
    e.preventDefault();
    const taskId = document.getElementById("editTaskId").value;
    const newText = document.getElementById("editTaskText").value.trim();
    const taskElement = document.getElementById(`task-${taskId}`);

    if (!newText) {
        alert('Текст задачи не может быть пустым');
        return;
    }

    try {
        const response = await fetch(`/edit/${taskId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `task=${encodeURIComponent(newText)}`
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Мгновенное обновление интерфейса
            taskElement.querySelector('.task-content').firstChild.textContent = newText;
            
            // Обновляем блок с датами
            const datesElement = taskElement.querySelector('.dates');
            let datesHtml = `Создано: ${datesElement.textContent.split('Создано:')[1].split('|')[0].trim()}`;
            
            if (taskElement.classList.contains('completed')) {
                datesHtml += ` | Завершено: ${datesElement.textContent.split('Завершено:')[1].split('|')[0].trim()}`;
            }
            
            datesHtml += ` | Изменено: ${data.updated_at}`;
            datesElement.innerHTML = datesHtml;
            
            // Добавляем визуальное подтверждение
            taskElement.classList.add('updated-highlight');
            setTimeout(() => {
                taskElement.classList.remove('updated-highlight');
            }, 1000);
            
            modal.style.display = "none";
        } else if (data.message) {
            alert(data.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Ошибка при сохранении изменений');
    }
};

    // Функция для обновления интерфейса задачи
    function updateTaskUI(taskElement, data) {
        const taskContent = taskElement.querySelector('.task-content');
        const actionsContainer = taskElement.querySelector('.task-actions');
        
        // Обновляем статус
        taskElement.classList.toggle('completed', data.completed);
        
        // Обновляем даты
        let datesHtml = `Создано: ${new Date(data.created_at).toLocaleString('ru-RU')}`;
        
        if (data.completed_at) {
            datesHtml += ` | Завершено: ${new Date(data.completed_at).toLocaleString('ru-RU')}`;
        }
        
        if (data.is_edited) {
            datesHtml += ` | Изменено: ${new Date(data.updated_at).toLocaleString('ru-RU')}`;
        }
        
        taskContent.querySelector('.dates').innerHTML = datesHtml;
        
        // Обновляем кнопки
        actionsContainer.innerHTML = data.completed ? `
            <button class="btn btn-sm btn-warning reactivate-btn"
                    data-task-id="${data.id}"
                    title="Вернуть в активные">
                ↩️
            </button>
            <button class="btn btn-sm btn-outline-danger delete-btn"
                    data-task-id="${data.id}"
                    title="Удалить">
                🗑️
            </button>
        ` : `
            <button class="btn btn-sm btn-success complete-btn"
                    data-task-id="${data.id}"
                    title="Завершить">
                ✓
            </button>
            <a href="/edit/${data.id}" 
               class="btn btn-sm btn-outline-primary"
               title="Редактировать">
               ✏️
            </a>
            <button class="btn btn-sm btn-outline-danger delete-btn"
                    data-task-id="${data.id}"
                    title="Удалить">
                🗑️
            </button>
        `;
        
        // Назначаем обработчики на новые кнопки
        assignEventHandlers();
    }

    // Обработка действий с задачами
    function handleTaskAction(taskId, action) {
        const taskElement = document.getElementById(`task-${taskId}`);
        
        // Добавляем класс анимации
        taskElement.classList.add(`task-${action}`);
        
        fetch(`/${action}/${taskId}`)
            .then(response => {
                if (!response.ok) throw new Error('Network error');
                return response.json();
            })
            .then(data => {
                setTimeout(() => {
                    taskElement.classList.remove(`task-${action}`);
                    if (action === 'delete') {
                        taskElement.remove();
                    } else {
                        updateTaskUI(taskElement, data);
                    }
                }, 300);
            })
            .catch(error => {
                console.error('Error:', error);
                taskElement.classList.remove(`task-${action}`);
                alert('Произошла ошибка. Пожалуйста, попробуйте снова.');
            });
    }

    // Назначение обработчиков событий
    function assignEventHandlers() {
        // Завершение задачи
        document.addEventListener('click', function(e) {
            if (e.target.closest('.complete-btn')) {
                e.preventDefault();
                handleTaskAction(e.target.closest('button').dataset.taskId, 'complete');
            }
            
            // Возврат в активные
            if (e.target.closest('.reactivate-btn')) {
                e.preventDefault();
                handleTaskAction(e.target.closest('button').dataset.taskId, 'reactivate');
            }
            
            // Удаление
            if (e.target.closest('.delete-btn')) {
                e.preventDefault();
                if (confirm('Вы уверены, что хотите удалить эту задачу?')) {
                    handleTaskAction(e.target.closest('button').dataset.taskId, 'delete');
                }
            }
        });
    }

    // Инициализация
    assignEventHandlers();
});