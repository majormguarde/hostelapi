/**
 * Функции для управления картами
 */

let currentCardId = null;
let currentPage = 1;
let currentFilters = {};

/**
 * Загрузить профили в фильтр при загрузке страницы
 */
async function loadProfilesForFilter() {
    try {
        const profiles = await makeRequest('/profiles', 'GET');
        const filterProfile = document.getElementById('filterProfile');
        
        if (Array.isArray(profiles)) {
            profiles.forEach(profile => {
                const option = document.createElement('option');
                option.value = profile.id;
                option.textContent = `${profile.name} (${profile.card_count})`;
                filterProfile.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Ошибка при загрузке профилей для фильтра:', error);
    }
}

/**
 * Загрузить список карт с текущими фильтрами и пагинацией
 */
async function loadCards(page = 1) {
    showLoading();
    try {
        // Собираем параметры запроса
        let url = `/cards?page=${page}&per_page=10`;
        
        if (currentFilters.card_number) {
            url += `&card_number=${encodeURIComponent(currentFilters.card_number)}`;
        }
        if (currentFilters.profile_id) {
            url += `&profile_id=${currentFilters.profile_id}`;
        }
        if (currentFilters.status !== undefined && currentFilters.status !== '') {
            url += `&status=${currentFilters.status}`;
        }
        
        const result = await makeRequest(url, 'GET');
        
        if (result.error) {
            showMessage('Ошибка при загрузке карт: ' + result.error, 'danger');
            hideLoading();
            return;
        }
        
        currentPage = page;
        displayCards(result.cards);
        displayPagination(result);
        hideLoading();
    } catch (error) {
        showMessage('Ошибка при загрузке карт: ' + error.message, 'danger');
        hideLoading();
    }
}

/**
 * Применить фильтры
 */
function applyFilters() {
    currentFilters = {
        card_number: document.getElementById('filterCardNumber').value,
        profile_id: document.getElementById('filterProfile').value,
        status: document.getElementById('filterStatus').value
    };
    loadCards(1);
}

/**
 * Отобразить пагинатор
 */
function displayPagination(result) {
    const paginationContainer = document.getElementById('paginationContainer');
    const pagination = document.getElementById('pagination');
    
    if (result.total_pages <= 1) {
        paginationContainer.style.display = 'none';
        return;
    }
    
    paginationContainer.style.display = 'block';
    pagination.innerHTML = '';
    
    // Кнопка "Предыдущая"
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${result.page === 1 ? 'disabled' : ''}`;
    prevLi.innerHTML = `<a class="page-link" href="#" onclick="loadCards(${result.page - 1}); return false;">Предыдущая</a>`;
    pagination.appendChild(prevLi);
    
    // Номера страниц
    const startPage = Math.max(1, result.page - 2);
    const endPage = Math.min(result.total_pages, result.page + 2);
    
    if (startPage > 1) {
        const firstLi = document.createElement('li');
        firstLi.className = 'page-item';
        firstLi.innerHTML = `<a class="page-link" href="#" onclick="loadCards(1); return false;">1</a>`;
        pagination.appendChild(firstLi);
        
        if (startPage > 2) {
            const dotsLi = document.createElement('li');
            dotsLi.className = 'page-item disabled';
            dotsLi.innerHTML = `<span class="page-link">...</span>`;
            pagination.appendChild(dotsLi);
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const li = document.createElement('li');
        li.className = `page-item ${i === result.page ? 'active' : ''}`;
        li.innerHTML = `<a class="page-link" href="#" onclick="loadCards(${i}); return false;">${i}</a>`;
        pagination.appendChild(li);
    }
    
    if (endPage < result.total_pages) {
        if (endPage < result.total_pages - 1) {
            const dotsLi = document.createElement('li');
            dotsLi.className = 'page-item disabled';
            dotsLi.innerHTML = `<span class="page-link">...</span>`;
            pagination.appendChild(dotsLi);
        }
        
        const lastLi = document.createElement('li');
        lastLi.className = 'page-item';
        lastLi.innerHTML = `<a class="page-link" href="#" onclick="loadCards(${result.total_pages}); return false;">${result.total_pages}</a>`;
        pagination.appendChild(lastLi);
    }
    
    // Кнопка "Следующая"
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${result.page === result.total_pages ? 'disabled' : ''}`;
    nextLi.innerHTML = `<a class="page-link" href="#" onclick="loadCards(${result.page + 1}); return false;">Следующая</a>`;
    pagination.appendChild(nextLi);
}

/**
 * Отобразить карты в таблице
 * @param {array} cards - Массив карт
 */
function displayCards(cards) {
    const tbody = document.getElementById('cardsBody');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (!Array.isArray(cards) || cards.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Карты не найдены</td></tr>';
        return;
    }

    cards.forEach(card => {
        const row = document.createElement('tr');
        const status = card.status === 1 ? 'Активна' : 'Неактивна';
        const statusBadge = card.status === 1 ? 'badge-active' : 'badge-inactive';
        const profileName = card.profile_name || 'Не указан';
        
        // Форматировать даты - только дата без времени
        const validFrom = card.valid_from ? card.valid_from.split('T')[0] : '-';
        const validUntil = card.valid_until ? card.valid_until.split('T')[0] : '-';
        
        const profileLink = `<a href="#" onclick="editProfile(${card.card_id}, '${profileName}'); return false;" class="text-decoration-none"><strong>${profileName}</strong></a>`;

        row.innerHTML = `
            <td>${card.card_number || '-'}</td>
            <td>${card.room || '-'}</td>
            <td>${profileLink}</td>
            <td>${validFrom}</td>
            <td>${validUntil}</td>
            <td><span class="badge ${statusBadge}">${status}</span></td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-sm btn-warning" onclick="showEditCardForm(${card.card_id})">
                        Редактировать
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="showDeleteConfirm(${card.card_id})">
                        Удалить
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

/**
 * Показать форму добавления карты
 */
async function showAddCardForm() {
    clearValidationErrors();
    document.getElementById('cardForm').reset();
    document.getElementById('cardModalTitle').textContent = 'Добавить карту';
    currentCardId = null;

    // Установить дату на сегодня
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('valid_from').value = today;

    // Загрузить профили
    try {
        const profiles = await makeRequest('/profiles', 'GET');
        const profileSelect = document.getElementById('profile_id');
        profileSelect.innerHTML = '<option value="">Выберите профиль...</option>';
        
        if (Array.isArray(profiles)) {
            profiles.forEach(profile => {
                const option = document.createElement('option');
                option.value = profile.id;
                option.textContent = `${profile.name} (${profile.card_count})`;
                profileSelect.appendChild(option);
            });
        }
    } catch (error) {
        showMessage('Ошибка при загрузке профилей: ' + error.message, 'warning');
    }

    const modal = new bootstrap.Modal(document.getElementById('cardModal'));
    modal.show();
}

/**
 * Показать форму редактирования карты
 * @param {number} cardId - ID карты
 */
async function showEditCardForm(cardId) {
    showLoading();
    try {
        const card = await makeRequest(`/cards/${cardId}`, 'GET');
        
        // Установить значения полей
        document.getElementById('room').value = card.room || '';
        document.getElementById('card_number').value = card.card_number || '';
        
        // Преобразовать дату в формат YYYY-MM-DD для input type="date"
        if (card.valid_from) {
            const dateStr = card.valid_from.split('T')[0];
            document.getElementById('valid_from').value = dateStr;
        }
        
        document.getElementById('valid_days').value = card.valid_days || '';
        document.getElementById('comments').value = card.comments || '';
        document.getElementById('dep').value = card.dep || 'ХОСТЕЛ';

        // Загрузить профили
        const profiles = await makeRequest('/profiles', 'GET');
        const profileSelect = document.getElementById('profile_id');
        profileSelect.innerHTML = '<option value="">Выберите профиль...</option>';
        
        if (Array.isArray(profiles)) {
            profiles.forEach(profile => {
                const option = document.createElement('option');
                option.value = profile.id;
                option.textContent = `${profile.name} (${profile.card_count})`;
                // Установить выбранный профиль
                if (profile.id === card.profile_id) {
                    option.selected = true;
                }
                profileSelect.appendChild(option);
            });
        }

        document.getElementById('cardModalTitle').textContent = 'Редактировать карту';
        currentCardId = cardId;

        clearValidationErrors();
        const modal = new bootstrap.Modal(document.getElementById('cardModal'));
        modal.show();
        hideLoading();
    } catch (error) {
        showMessage('Ошибка при загрузке данных карты: ' + error.message, 'danger');
        hideLoading();
    }
}

/**
 * Сохранить карту
 */
async function saveCard() {
    const validation = validateCardForm();
    if (!validation.isValid) {
        showValidationErrors(validation.errors);
        return;
    }

    clearValidationErrors();
    showLoading();

    const data = {
        room: parseInt(document.getElementById('room').value),
        card_number: parseInt(document.getElementById('card_number').value),
        valid_from: document.getElementById('valid_from').value,
        valid_days: parseInt(document.getElementById('valid_days').value),
        profile_id: parseInt(document.getElementById('profile_id').value),
        comments: document.getElementById('comments').value,
        dep: document.getElementById('dep').value
    };

    try {
        let result;
        if (currentCardId) {
            result = await makeRequest(`/cards/${currentCardId}`, 'PUT', data);
        } else {
            result = await makeRequest('/cards', 'POST', data);
        }

        if (result.error) {
            showMessage('Ошибка: ' + result.error, 'danger');
        } else {
            showMessage(
                currentCardId ? 'Карта успешно обновлена' : 'Карта успешно добавлена',
                'success'
            );
            
            // Закрыть модальное окно
            bootstrap.Modal.getInstance(document.getElementById('cardModal')).hide();
            
            // Применить текущие фильтры и перезагрузить список
            applyFilters();
        }
        hideLoading();
    } catch (error) {
        showMessage('Ошибка при сохранении карты: ' + error.message, 'danger');
        hideLoading();
    }
}

/**
 * Показать диалог подтверждения удаления
 * @param {number} cardId - ID карты
 */
function showDeleteConfirm(cardId) {
    currentCardId = cardId;
    const modal = new bootstrap.Modal(document.getElementById('deleteModal'));
    modal.show();
}

/**
 * Подтвердить удаление карты
 */
async function confirmDelete() {
    if (!currentCardId) return;

    showLoading();
    try {
        const result = await makeRequest(`/cards/${currentCardId}`, 'DELETE');

        if (result.error) {
            showMessage('Ошибка: ' + result.error, 'danger');
        } else {
            showMessage('Карта успешно удалена', 'success');
            
            // Закрыть модальное окно
            bootstrap.Modal.getInstance(document.getElementById('deleteModal')).hide();
            
            // Применить текущие фильтры и перезагрузить список
            applyFilters();
        }
        hideLoading();
    } catch (error) {
        showMessage('Ошибка при удалении карты: ' + error.message, 'danger');
        hideLoading();
    }
}

/**
 * Редактировать профиль доступа карты
 * @param {number} cardId - ID карты
 * @param {string} currentProfile - Текущий профиль
 */
async function editProfile(cardId, currentProfile) {
    try {
        // Получить список профилей
        const profiles = await makeRequest('/profiles', 'GET');
        
        if (!Array.isArray(profiles)) {
            showMessage('Ошибка при загрузке профилей', 'danger');
            return;
        }
        
        // Создать модальное окно с выпадающим списком
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'profileModal';
        modal.tabIndex = -1;
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Изменить профиль доступа</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label for="profileSelect" class="form-label">Выберите профиль:</label>
                            <select class="form-select" id="profileSelect">
                                ${profiles.map(p => `<option value="${p.id}" ${p.name === currentProfile ? 'selected' : ''}>${p.name} (${p.card_count})</option>`).join('')}
                            </select>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Прикрепляем событие change к выпадающему списку
        const profileSelect = modal.querySelector('#profileSelect');
        profileSelect.addEventListener('change', async function() {
            const newProfileId = this.value;
            
            if (!newProfileId) {
                showMessage('Выберите профиль', 'warning');
                return;
            }
            
            showLoading();
            try {
                const result = await makeRequest(`/cards/${cardId}/profile`, 'PUT', {
                    profile_id: parseInt(newProfileId)
                });
                
                if (result.success) {
                    showMessage('Профиль успешно обновлен', 'success');
                    
                    // Закрыть модальное окно
                    const profileModal = bootstrap.Modal.getInstance(modal);
                    if (profileModal) {
                        profileModal.hide();
                    }
                    
                    // Применить текущие фильтры и перезагрузить список
                    applyFilters();
                } else {
                    showMessage('Ошибка: ' + (result.error || 'Неизвестная ошибка'), 'danger');
                }
                hideLoading();
            } catch (error) {
                showMessage('Ошибка при сохранении профиля: ' + error.message, 'danger');
                hideLoading();
            }
        });
        
        const profileModal = new bootstrap.Modal(modal);
        profileModal.show();
        
        // Удалить модальное окно после закрытия
        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
        
    } catch (error) {
        showMessage('Ошибка при загрузке профилей: ' + error.message, 'danger');
    }
}

