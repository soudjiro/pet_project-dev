document.addEventListener('DOMContentLoaded', function() {
    const newTagInput = document.getElementById('newTaskTags');
    const newTagSuggestions = document.getElementById('newTagSuggestions');

    // Добавим функцию для обновления счетчиков в навигации
    function updateTaskCounters(counters) {
        const updateBadge = (selector, value) => {
            const badge = document.querySelector(selector);
            if (!badge) return;
            
            if (badge.textContent !== String(value)) {
                badge.textContent = value;
                badge.classList.add('updated');
                setTimeout(() => badge.classList.remove('updated'), 500);
            }
        };

        updateBadge('.nav-link[href*="new"] .badge', counters.new);
        updateBadge('.nav-link[href*="active"] .badge', counters.active);
        updateBadge('.nav-link[href*="completed"] .badge', counters.completed);
    }

    function updateEmptyState() {
        const tasksContainer = document.getElementById('tasks-container');
        const emptyState = document.getElementById('empty-state');
        
        if (tasksContainer.children.length === 0) {
            emptyState.style.display = 'block';
        } else {
            emptyState.style.display = 'none';
        }
    }
    // Общая функция для обработки действий с задачами
    async function handleTaskAction(action, taskId) {
        const taskElement = document.getElementById(`task-${taskId}`);
         try {
            const response = await fetch(`/${action}/${taskId}`, {
                method: action === 'reactivate' ? 'POST' : 'GET'
            });
            
            if (!response.ok) throw new Error(await response.text());
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // Обновляем счетчики, если они пришли в ответе
                if (data.counters) {
                    updateTaskCounters(data.counters);
                }
                // Добавляем класс для анимации исчезновения
                taskElement.classList.add('disappearing');
                 // Удаляем элемент после анимации
                setTimeout(() => {
                    taskElement.remove();
                    updateEmptyState();
                    }, 300);
            } else {
                showAlert(data.message || 'Ошибка операции', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showAlert('Не удалось выполнить операцию', 'error');
        } finally {
            taskElement.classList.remove('processing');
        }
    }

    // Функция для показа уведомлений
    function showAlert(message, type = 'info') {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        document.body.prepend(alert);
        setTimeout(() => alert.remove(), 3000);
    }

    if (newTagInput) {
        newTagInput.addEventListener('input', async function() {
            const search = this.value;
            if (search.length < 2) {
                newTagSuggestions.style.display = 'none';
                return;
            }
            
            try {
                const response = await fetch(`/api/tags?search=${encodeURIComponent(search)}`);
                const tags = await response.json();
                
                newTagSuggestions.innerHTML = '';
                tags.forEach(tag => {
                    const suggestion = document.createElement('a');
                    suggestion.className = 'list-group-item list-group-item-action';
                    suggestion.textContent = tag;
                    suggestion.addEventListener('click', (e) => {
                        e.preventDefault();
                        this.value = this.value ? `${this.value}, ${tag}` : tag;
                        newTagSuggestions.style.display = 'none';
                    });
                    newTagSuggestions.appendChild(suggestion);
                });
                
                newTagSuggestions.style.display = tags.length ? 'block' : 'none';
            } catch (error) {
                console.error('Error fetching tags:', error);
            }
        });
    }

    // Добавить функцию для скрытия подсказок тегов
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.tag-input-container')) {
            document.querySelectorAll('#tagSuggestions, #newTagSuggestions').forEach(el => {
                el.style.display = 'none';
            });
        }
    });

    // Обработчик обновления тегов
    document.getElementById('refresh-tags').addEventListener('click', async () => {
        const loadingIndicator = document.getElementById('loading-indicator');
        loadingIndicator.style.display = 'flex';
        
        try {
            await fetch('/refresh-tags');
            location.reload();
        } catch (error) {
            showAlert('Ошибка при обновлении тегов', 'error');
        } finally {
            loadingIndicator.style.display = 'none';
        }
    });

    // Обработчик кликов
    document.addEventListener('click', async function(e) {
        // Обработка кнопки "В работу"
        if (e.target.closest('.start-btn')) {
            e.preventDefault();
            const taskId = e.target.closest('.start-btn').dataset.taskId;
            await handleTaskAction('start', taskId);
        }

        // Обработка кнопки "Завершить"
        if (e.target.closest('.complete-btn')) {
            e.preventDefault();
            const taskId = e.target.closest('.complete-btn').dataset.taskId;
            await handleTaskAction('complete', taskId);
        }

        // Обработка кнопки "Вернуть в работу"
        if (e.target.closest('.reactivate-btn')) {
            e.preventDefault();
            const taskId = e.target.closest('.reactivate-btn').dataset.taskId;
            await handleTaskAction('reactivate', taskId);
        }

        // Обработка кнопки "Удалить"
        if (e.target.closest('.delete-btn')) {
            e.preventDefault();
            const taskId = e.target.closest('.delete-btn').dataset.taskId;
            if (confirm('Вы уверены, что хотите удалить эту задачу?')) {
                await handleTaskAction('delete', taskId);
            }
        }
    });

    // Модальное окно редактирования
    const modal = document.getElementById("editModal");
    const closeBtn = document.querySelector(".close");
    const editForm = document.getElementById("editForm");

    // Открытие модального окна
    document.addEventListener('click', function(e) {
        if (e.target.closest('.edit-btn')) {
            const btn = e.target.closest('.edit-btn');
            const taskId = btn.dataset.taskId;
            const taskElement = document.getElementById(`task-${taskId}`);
            
            // Получаем текст задачи
            const taskText = taskElement.querySelector('h6').textContent.trim();
            
            // Получаем теги
            let tags = '';
            const tagBadges = taskElement.querySelectorAll('.task-tags .tag-badge');
            if (tagBadges.length > 0) {
                tags = Array.from(tagBadges).map(badge => badge.textContent.trim()).join(', ');
            }
            
            // Получаем статус задачи
            const status = taskElement.classList.contains('status-new') ? 'Новая' :
                        taskElement.classList.contains('status-active') ? 'В работе' :
                        'Завершена';
            
            // Заполняем форму
            document.getElementById("editTaskId").value = taskId;
            document.getElementById("editTaskText").value = taskText;
            document.getElementById("editTaskTags").value = tags;
            document.getElementById("editTaskStatusDisplay").textContent = status;
            document.getElementById("editTaskStatusDisplay").className = 
                `status-badge ${taskElement.classList.contains('status-new') ? 'status-new' : 
                taskElement.classList.contains('status-active') ? 'status-active' : 'status-completed'}`;
            
            // Показываем модальное окно
            document.getElementById("editModal").style.display = "block";
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
        const newTags = document.getElementById("editTaskTags").value.trim();
        

        if (!newText) {
            showAlert('Текст задачи не может быть пустым', 'error');
            return;
        }

        try {
            const response = await fetch(`/edit/${taskId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `task=${encodeURIComponent(newText)}&tags=${encodeURIComponent(newTags)}`
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                const taskElement = document.getElementById(`task-${taskId}`);
                taskElement.querySelector('.task-content h6').textContent = newText;

                // Обновляем теги
                const tagsContainer = taskElement.querySelector('.task-tags');
                if (data.tags_html) {
                    tagsContainer.innerHTML = data.tags_html;
                }
                
                // Обновляем дату изменения
                const datesElement = taskElement.querySelector('.dates');
                if (data.updated_at) {
                    let datesHtml = datesElement.innerHTML;
                    if (datesHtml.includes('Изменено:')) {
                        datesHtml = datesHtml.replace(/Изменено: [^|]+/, `Изменено: ${data.updated_at}`);
                    } else {
                        datesHtml += ` | Изменено: ${data.updated_at}`;
                    }
                    datesElement.innerHTML = datesHtml;
                }
                
                taskElement.classList.add('updated-highlight');
                setTimeout(() => {
                    taskElement.classList.remove('updated-highlight');
                }, 1000);
                
                modal.style.display = "none";
                showAlert('Задача успешно обновлена', 'success');
            } else if (data.message) {
                showAlert(data.message, 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showAlert('Ошибка при сохранении изменений', 'error');
        }
    };
});