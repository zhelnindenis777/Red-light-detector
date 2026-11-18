const form = document.getElementById('processForm');
const fileInput = document.getElementById('media');
const fileName = document.getElementById('fileName');
const message = document.getElementById('message');

fileInput.addEventListener('change', () => {
    fileName.textContent = fileInput.files[0]?.name || 'JPG, PNG, MP4, MOV, AVI или MKV';
});

function showMessage(text, error = false) {
    message.textContent = text;
    message.className = error ? 'message error' : 'message';
}

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    showMessage('Файл обрабатывается. Для видео это может занять несколько минут.');
    try {
        const response = await fetch('/process', { method: 'POST', body: new FormData(form) });
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(data.error || 'Не удалось обработать файл');
        renderResult(data);
        showMessage('Обработка завершена. Результат сохранён в истории.');
        await loadHistory();
    } catch (error) {
        showMessage(error.message, true);
    } finally {
        button.disabled = false;
    }
});

function renderResult(data) {
    document.getElementById('resultEmpty').classList.add('hidden');
    document.getElementById('resultContent').classList.remove('hidden');
    const media = data.media_type === 'video'
        ? `<video controls src="${data.result_url}?t=${Date.now()}"></video>`
        : `<img src="${data.result_url}?t=${Date.now()}" alt="Результат обработки">`;
    document.getElementById('resultMedia').innerHTML = media;
    document.getElementById('vehicleCount').textContent = data.vehicle_count;
    document.getElementById('violationCount').textContent = data.violation_count;
    document.getElementById('processingTime').textContent = data.processing_time;
    const parts = Object.entries(data.class_counts).map(([name, count]) => `${name}: ${count}`);
    document.getElementById('classCounts').textContent = parts.length ? `Состав: ${parts.join(', ')}` : 'Транспортные средства не найдены.';
}

async function loadHistory() {
    const response = await fetch('/api/history');
    const data = await response.json();
    const body = document.getElementById('historyBody');
    body.innerHTML = '';
    if (!data.records.length) {
        body.innerHTML = '<tr><td colspan="6" class="empty-row">История пока пуста</td></tr>';
        return;
    }
    data.records.forEach((item) => {
        const row = document.createElement('tr');
        row.innerHTML = `<td>${item.timestamp}</td><td>${item.original_filename}</td><td>${item.media_type}</td>` +
            `<td>${item.vehicle_count}</td><td>${item.violation_count}</td><td><a href="${item.result_url}" target="_blank">Открыть</a></td>`;
        body.appendChild(row);
    });
}

document.getElementById('clearHistory').addEventListener('click', async () => {
    if (!confirm('Очистить все записи истории?')) return;
    await fetch('/api/clear-history', { method: 'POST' });
    await loadHistory();
});

loadHistory();
