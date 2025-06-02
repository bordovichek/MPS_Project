document.addEventListener('DOMContentLoaded', () => {
    // Функция для создания эффекта ряби на кнопках
    function createRipple(event) {
            const button = event.currentTarget;
            const circle = document.createElement('span');
            const diameter = Math.max(button.clientWidth, button.clientHeight);
            const radius = diameter / 2;
            console.log(1111);
            circle.style.width = circle.style.height = `${diameter}px`;
            circle.style.left = `calc(50% - ${radius}px)`;
            circle.style.top = `calc(50% - ${radius}px)`;
            circle.classList.add('ripple');

            const oldRipple = button.querySelector('.ripple');
            if (oldRipple) {
                oldRipple.remove();
            }

            button.appendChild(circle);

            circle.addEventListener('animationend', () => {
                circle.remove();
            });
        }

    // Обработчик клика по кнопке поиска
    function handleSearchButtonClick(event) {
        createRipple(event);
    }

    // Настраиваем переключение темы
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const homeBtn = document.getElementById('homeBtn');
    const body = document.body;
    const themeIcon = themeToggleBtn.querySelector('i');

    // Проверяем сохраненную тему при загрузке страницы
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        body.classList.add('dark-theme');
        themeIcon.classList.remove('fa-moon');
        themeIcon.classList.add('fa-sun');
    } else {
        body.classList.remove('dark-theme');
        themeIcon.classList.remove('fa-sun');
        themeIcon.classList.add('fa-moon');
    }

    // Обработчик клика для кнопки переключения темы
    themeToggleBtn.addEventListener('click', (event) => {
        body.classList.toggle('dark-theme');
        if (body.classList.contains('dark-theme')) {
            themeIcon.classList.remove('fa-moon');
            themeIcon.classList.add('fa-sun');
            localStorage.setItem('theme', 'dark');
        } else {
            themeIcon.classList.remove('fa-sun');
            themeIcon.classList.add('fa-moon');
            localStorage.setItem('theme', 'light');
        }
        createRipple(event);
    });

    // Обработчик клика для кнопки "Домой"
    homeBtn.addEventListener('click', (event) => {
        createRipple(event);
        window.location.href = '/'; // Переход на главную страницу
    });

    // Применяем эффект ряби к кнопке поиска
    const searchButton = document.querySelector('.search-form button');
    if (searchButton) {
        searchButton.addEventListener('click', handleSearchButtonClick);
    }

    // --- Логика для кнопки "Вверх" ---
    const backToTopButton = document.createElement('a');
    backToTopButton.href = '#top';
    backToTopButton.className = 'back-to-top';
    backToTopButton.innerHTML = '<i class="fas fa-arrow-up"></i>'; // Иконка стрелки вверх
    document.body.appendChild(backToTopButton); // Добавляем кнопку в DOM

    // Создаем якорь в самом верху страницы
    const topAnchor = document.createElement('a');
    topAnchor.id = 'top';
    document.body.prepend(topAnchor); // Добавляем якорь в начало body

    window.addEventListener('scroll', () => {
        if (window.scrollY > 300) { // Показываем кнопку, если прокрутили более 300px
            backToTopButton.classList.add('show');
        } else {
            backToTopButton.classList.remove('show');
        }
    });

    backToTopButton.addEventListener('click', (e) => {
        e.preventDefault();
        createRipple(e); // Эффект ряби для кнопки "Вверх"
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
});