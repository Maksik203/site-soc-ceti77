// drag & drop для загрузки изображений в постах/группах
document.querySelectorAll('.post-dropzone').forEach((zone) => {
    const inputId = zone.getAttribute('data-dropzone-target');
    const fileInput = inputId ? document.getElementById(inputId) : null;
    if (!fileInput) {
        return;
    }
    ['dragenter', 'dragover'].forEach((evt) => {
        zone.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            zone.classList.add('dropzone-active');
        });
    });
    ['dragleave', 'drop'].forEach((evt) => {
        zone.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            zone.classList.remove('dropzone-active');
        });
    });
    zone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
            fileInput.files = files;
        }
    });
    zone.addEventListener('click', () => fileInput.click());
});

// модальное увеличенное фото аватарки
const avatarModalEl = document.getElementById('avatarModal');
if (avatarModalEl) {
    const avatarImg = avatarModalEl.querySelector('.avatar-modal-img');
    const avatarModal = new bootstrap.Modal(avatarModalEl);
    document.querySelectorAll('.avatar-click').forEach((btn) => {
        btn.addEventListener('click', () => {
            const src = btn.getAttribute('data-avatar-full');
            if (src && avatarImg) {
                avatarImg.src = src;
                avatarModal.show();
            }
        });
    });
}

// AJAX-действия с постами: лайк, репост, комментарий
document.addEventListener('submit', (e) => {
    const form = e.target;
    if (
        form.matches('.js-like-form') ||
        form.matches('.js-repost-form') ||
        form.matches('.js-comment-form')
    ) {
        e.preventDefault();
        const formData = new FormData(form);
        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        })
            .then((r) => r.json())
            .then((data) => {
                // лайк
                if (form.matches('.js-like-form') && data && typeof data.likes_count !== 'undefined') {
                    const btn = form.querySelector('.js-like-btn');
                    if (btn) {
                        btn.textContent = `👍 ${data.likes_count}`;
                    }
                }
                // репост
                if (form.matches('.js-repost-form') && data && data.action) {
                    const card = form.closest('.js-post-card');
                    // если репост удалён и мы в разделе "Мои репосты" — просто убираем карточку
                    if (data.action === 'removed' && card && window.location.pathname.indexOf('my-reposts') !== -1) {
                        card.remove();
                    }
                }
                // комментарий
                if (form.matches('.js-comment-form') && data && data.ok) {
                    const commentsBox = form.parentElement.querySelector('.js-comments');
                    if (commentsBox) {
                        const wrapper = document.createElement('div');
                        wrapper.className = 'mt-2';
                        wrapper.innerHTML =
                            `<strong>${data.author}</strong> ` +
                            `<span class="text-muted small">${data.time}</span>` +
                            `<div>${data.body}</div>`;
                        commentsBox.appendChild(wrapper);
                    }
                    const input = form.querySelector('input[type="text"], textarea');
                    if (input) {
                        input.value = '';
                    }
                }
            })
            .catch((err) => {
                console.error('post action failed', err);
                form.submit(); // fallback: если что-то пошло не так — обычная отправка
            });
    }
});

