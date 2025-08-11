document.addEventListener('DOMContentLoaded', function() {
    
    // Общая функция для обработки действий с задачами
    async function handleTaskAction(action, taskId) {
        const taskElement = document.getElementById(`task-${taskId}`);
        if (!taskElement) return;

        taskElement.classList.add('processing');
        
        try {
            const response = await fetch(`/${action}/${taskId}`, {
                method: action === 'reactivate' ? 'POST' : 'GET'
            });
            
            if (!response.ok) throw new Error(await response.text());
            
            const data = await response.json();
            
            if (data.status === 'success') {
                taskElement.classList.add('disappearing');
                setTimeout(() => taskElement.remove(), 300);
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
            const taskId = e.target.closest('.edit-btn').dataset.taskId;
            const taskElement = document.getElementById(`task-${taskId}`);
            const taskText = taskElement.querySelector('.task-content h6').textContent.trim();
            
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
            showAlert('Текст задачи не может быть пустым', 'error');
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
                taskElement.querySelector('.task-content h6').textContent = newText;
                
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