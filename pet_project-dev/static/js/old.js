// Анимация появления элементов при загрузке
document.addEventListener('DOMContentLoaded', function() {
    const items = document.querySelectorAll('.list-group-item');
    items.forEach((item, index) => {
        item.style.opacity = '0';
        item.style.transform = 'translateY(20px)';
        setTimeout(() => {
            item.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            item.style.opacity = '1';
            item.style.transform = 'translateY(0)';
        }, 100 * index);
    });
});

document.addEventListener('DOMContentLoaded', function() {
    // Обработка кнопок изменения статуса
    document.querySelectorAll('[data-status-action]').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const taskItem = this.closest('.list-group-item');
            const url = this.href;
            
            // Добавляем класс анимации в зависимости от действия
            if (this.dataset.statusAction === 'complete') {
                taskItem.classList.add('task-completing');
            } else {
                taskItem.classList.add('task-activating');
            }
            
            // Добавляем эффект "блеска"
            taskItem.classList.add('status-change');
            
            // Задержка перед переходом для завершения анимации
            setTimeout(() => {
                window.location.href = url;
            }, 400);
        });
    });
});



document.addEventListener('DOMContentLoaded', function() {
    // Функция для обновления интерфейса задачи
    function updateTaskUI(taskElement, data) {
        const taskContent = taskElement.querySelector('.task-content');
        const actionsContainer = taskElement.querySelector('.task-actions');
        
        // Обновляем статус
        taskElement.classList.toggle('completed', data.completed);
        
        // Обновляем даты
        let datesHtml = `Создано: ${taskContent.querySelector('.created-date').textContent.split('|')[0].trim()}`;
        
        if (data.completed) {
            datesHtml += ` | Завершено: ${data.completed_at}`;
        }
        
        if (data.is_edited) {
            datesHtml += ` | Изменено: ${data.updated_at || ''}`;
        }
        
        taskContent.querySelector('.dates').innerHTML = datesHtml;
        
        // Обновляем кнопки
        actionsContainer.innerHTML = data.completed ? `
            <button class="btn btn-sm btn-warning reactivate-btn"
                    data-task-id="${taskElement.id.split('-')[1]}"
                    title="Вернуть в активные">
                ↩️
            </button>
            <button class="btn btn-sm btn-outline-danger delete-btn"
                    data-task-id="${taskElement.id.split('-')[1]}"
                    title="Удалить">
                🗑️
            </button>
        ` : `
            <button class="btn btn-sm btn-success complete-btn"
                    data-task-id="${taskElement.id.split('-')[1]}"
                    title="Завершить">
                ✓
            </button>
            <a href="/edit/${taskElement.id.split('-')[1]}" 
               class="btn btn-sm btn-outline-primary"
               title="Редактировать">
               ✏️
            </a>
            <button class="btn btn-sm btn-outline-danger delete-btn"
                    data-task-id="${taskElement.id.split('-')[1]}"
                    title="Удалить">
                🗑️
            </button>
        `;
        
        // Назначаем обработчики на новые кнопки
        assignEventHandlers();
    }
    // Общая функция для обновления задачи
    function updateTask(taskId, action) {
        const taskElement = document.getElementById(`task-${taskId}`);
        const taskContent = taskElement.querySelector('.task-content');
        
        // Добавляем анимацию в зависимости от действия
        if (action === 'complete') {
            taskElement.classList.add('completing');
        } else if (action === 'reactivate') {
            taskElement.classList.add('reactivating');
        }
        
        // Отправляем запрос на сервер
        fetch(`/${action}/${taskId}`)
            .then(response => response.json())
            .then(data => {
                // Плавно обновляем интерфейс
                setTimeout(() => {
                    taskElement.classList.remove('completing', 'reactivating');
                    
                    if (action === 'complete') {
                        taskElement.classList.add('completed');
                        taskContent.innerHTML += `
                            <small class="text-muted d-block">
                                Завершено: ${new Date().toLocaleString('ru-RU')}
                            </small>
                        `;
                        // Заменяем кнопки
                        taskElement.querySelector('.task-actions').innerHTML = `
                            <button class="btn btn-sm btn-warning reactivate-btn"
                                    data-task-id="${taskId}"
                                    title="Вернуть в активные">
                                ↩️
                            </button>
                            <button class="btn btn-sm btn-outline-danger delete-btn"
                                    data-task-id="${taskId}"
                                    title="Удалить">
                                🗑️
                            </button>
                        `;
                    } else {
                        taskElement.classList.remove('completed');
                        // Удаляем дату завершения
                        const completedDate = taskContent.querySelector('small:last-child');
                        if (completedDate) completedDate.remove();
                        // Заменяем кнопки
                        taskElement.querySelector('.task-actions').innerHTML = `
                            <button class="btn btn-sm btn-success complete-btn"
                                    data-task-id="${taskId}"
                                    title="Завершить">
                                ✓
                            </button>
                            <a href="/edit/${taskId}" 
                               class="btn btn-sm btn-outline-primary"
                               title="Редактировать">
                               ✏️
                            </a>
                            <button class="btn btn-sm btn-outline-danger delete-btn"
                                    data-task-id="${taskId}"
                                    title="Удалить">
                                🗑️
                            </button>
                        `;
                    }
                    
                    // Назначаем обработчики на новые кнопки
                    assignEventHandlers();
                }, 300);
            })
            .catch(error => {
                console.error('Error:', error);
                taskElement.classList.remove('completing', 'reactivating');
                alert('Произошла ошибка. Пожалуйста, попробуйте снова.');
            });
    }
    
    // Функция для назначения обработчиков событий
    function assignEventHandlers() {
        // Обработка завершения задачи
        document.querySelectorAll('.complete-btn').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                updateTask(this.dataset.taskId, 'complete');
            });
        });
        
        // Обработка возврата в активные
        document.querySelectorAll('.reactivate-btn').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                updateTask(this.dataset.taskId, 'reactivate');
            });
        });
        
        // Обработка удаления
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const taskId = this.dataset.taskId;
                const taskElement = document.getElementById(`task-${taskId}`);
                
                // Анимация удаления
                taskElement.classList.add('deleting');
                
                fetch(`/delete/${taskId}`, { method: 'POST' })
                    .then(response => {
                        setTimeout(() => {
                            taskElement.remove();
                        }, 300);
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        taskElement.classList.remove('deleting');
                        alert('Не удалось удалить задачу.');
                    });
            });
        });
    }
    
    // Инициализация обработчиков
    assignEventHandlers();
});
