// Инициализация Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// Данные кейсов с предметами и вероятностями
const cases = {
  knife: {
    title: "кейс ZXCV",
    image: "photo_5395779186926415285_y.jpg",
    price: 100,
    items: [
      {
        name: "",
        image: "images/knife_common.png",
        rarity: "common",
        chance: 50,
        price: 50,
      },
      {
        name: "Редкий нож",
        image: "images/knife_rare.png",
        rarity: "rare",
        chance: 30,
        price: 150,
      },
      {
        name: "Эпический нож",
        image: "images/knife_epic.png",
        rarity: "epic",
        chance: 15,
        price: 300,
      },
      {
        name: "Souvenir AWP | Dragon Lore",
        image: "11591_b.png",
        rarity: "legendary",
        chance: 5,
        price: 1000,
      },
    ],
  },
  weapon: {
    title: "Оружейный кейс",
    image: "webapp/images/1ce35b33-ac0c-4f6e-8cc6-1d224670f638.jpeg",
    price: 50,
    items: [
      {
        name: "Glock-18",
        image: "images/weapon_glock.png",
        rarity: "common",
        chance: 60,
        price: 30,
      },
      {
        name: "AK-47",
        image: "images/weapon_ak47.png",
        rarity: "rare",
        chance: 25,
        price: 100,
      },
      {
        name: "AWP | Medusa",
        image: "12941_b.png",
        rarity: "epic",
        chance: 10,
        price: 200,
      },
      {
        name: "M4A4 | Howl",
        image: "10575_b.png",
        rarity: "legendary",
        chance: 5,
        price: 500,
      },
    ],
  },
};

// Текущие данные
let currentCase = null;
let currentUser = null;
let userInventory = [];

// Элементы интерфейса
const authScreen = document.getElementById("auth-screen");
const casesScreen = document.getElementById("cases-screen");
const openCaseScreen = document.getElementById("open-case-screen");
const resultScreen = document.getElementById("result-screen");
const inventoryScreen = document.getElementById("inventory-screen");
const itemsModal = document.getElementById("items-modal");

// Инициализация при загрузке
document.addEventListener("DOMContentLoaded", () => {
  // Проверяем авторизацию в Telegram
  if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
    const tgUser = tg.initDataUnsafe.user;
    currentUser = {
      id: tgUser.id,
      username: tgUser.username || `user_${tgUser.id}`,
      first_name: tgUser.first_name,
      last_name: tgUser.last_name,
    };

    // Проверяем, есть ли сохраненные данные пользователя
    const savedUser = localStorage.getItem(`user_${tgUser.id}`);
    if (savedUser) {
      currentUser = JSON.parse(savedUser);
      showCasesScreen();
    } else {
      // Показываем форму регистрации
      authScreen.classList.remove("hidden");
    }
  } else {
    // Показываем форму регистрации
    authScreen.classList.remove("hidden");
  }

  // Назначаем обработчики событий
  setupEventListeners();
});

// Настройка обработчиков событий
function setupEventListeners() {
  // Регистрация
  document
    .getElementById("register-btn")
    .addEventListener("click", registerUser);

  // Кнопки кейсов
  document.querySelectorAll(".case-item").forEach((item) => {
    item.addEventListener("click", (e) => {
      if (!e.target.classList.contains("view-items-btn")) {
        const caseType = item.getAttribute("data-case");
        selectCase(caseType);
      }
    });
  });

  // Кнопки "Посмотреть предметы"
  document.querySelectorAll(".view-items-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const caseType = e.target.closest(".case-item").getAttribute("data-case");
      showCaseItems(caseType);
    });
  });

  // Кнопки открытия кейса
  document
    .getElementById("open-fast-btn")
    .addEventListener("click", () => openCase("fast"));
  document
    .getElementById("open-slow-btn")
    .addEventListener("click", () => openCase("slow"));

  // Навигация
  document
    .getElementById("back-to-cases-btn")
    .addEventListener("click", showCasesScreen);
  document
    .getElementById("view-inventory-btn")
    .addEventListener("click", showInventoryScreen);
  document
    .getElementById("inventory-btn")
    .addEventListener("click", showInventoryScreen);
  document
    .getElementById("back-from-inventory-btn")
    .addEventListener("click", showCasesScreen);

  // Закрытие модального окна
  document.querySelector(".close-modal").addEventListener("click", () => {
    itemsModal.classList.add("hidden");
  });
}

// Регистрация пользователя
function registerUser() {
  const username = document.getElementById("username").value;
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  if (!username || !email || !password) {
    alert("Пожалуйста, заполните все поля");
    return;
  }

  // Сохраняем данные пользователя
  currentUser = {
    ...currentUser,
    username,
    email,
    inventory: [],
  };

  localStorage.setItem(`user_${currentUser.id}`, JSON.stringify(currentUser));

  // Переходим к выбору кейсов
  showCasesScreen();
}

// Показать экран выбора кейсов
function showCasesScreen() {
  authScreen.classList.add("hidden");
  openCaseScreen.classList.add("hidden");
  resultScreen.classList.add("hidden");
  inventoryScreen.classList.add("hidden");
  casesScreen.classList.remove("hidden");
}

// Выбор кейса
function selectCase(caseType) {
  currentCase = cases[caseType];

  // Обновляем интерфейс
  document.getElementById("case-title").textContent = currentCase.title;
  document.getElementById("case-image").src = currentCase.image;

  // Переходим к экрану открытия
  casesScreen.classList.add("hidden");
  openCaseScreen.classList.remove("hidden");
}

// Показать предметы в кейсе
function showCaseItems(caseType) {
  const caseData = cases[caseType];

  // Заполняем модальное окно
  document.getElementById(
    "modal-title"
  ).textContent = `Предметы в кейсе "${caseData.title}"`;
  const itemsContainer = document.querySelector(".items-container");
  itemsContainer.innerHTML = "";

  caseData.items.forEach((item) => {
    const itemElement = document.createElement("div");
    itemElement.className = "item-card";
    itemElement.innerHTML = `
            <img src="${item.image}" alt="${item.name}">
            <p>${item.name}</p>
            <p class="${item.rarity}">${getRarityName(item.rarity)}</p>
            <p>Шанс: ${item.chance}%</p>
            <p>Цена: ${item.price}₽</p>
        `;
    itemsContainer.appendChild(itemElement);
  });

  // Показываем модальное окно
  itemsModal.classList.remove("hidden");
}

// Открытие кейса
function openCase(mode) {
  // Проверяем баланс (в реальном приложении нужно проверять на сервере)
  if (
    !confirm(`Вы уверены, что хотите открыть кейс за ${currentCase.price}₽?`)
  ) {
    return;
  }

  // Подготовка рулетки
  const rouletteContainer = document.querySelector(".roulette-container");
  rouletteContainer.innerHTML = "";

  // Создаем элементы рулетки
  const itemsCount = 30; // Количество предметов для анимации
  const prizeIndex = Math.floor(Math.random() * 10) + 20; // Приз в конце

  // Выбираем приз с учетом вероятностей
  const prize = getRandomItemWithChance(currentCase.items);

  // Заполняем рулетку
  for (let i = 0; i < itemsCount; i++) {
    const item = i === prizeIndex ? prize : getRandomItem(currentCase.items);
    const itemElement = document.createElement("div");
    itemElement.className = "roulette-item";
    itemElement.innerHTML = `<img src="${item.image}" alt="${item.name}">`;
    rouletteContainer.appendChild(itemElement);
  }

  // Анимация
  if (mode === "slow") {
    // Эффектное открытие с анимацией
    const duration = 3000; // 3 секунды
    const startPosition = 0;
    const endPosition = prizeIndex * 120; // 120px - ширина одного элемента

    let startTime = null;

    const animate = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);

      // Эффект замедления в конце
      const easing =
        progress < 0.8 ? progress / 0.8 : 0.8 + (progress - 0.8) * 0.2;

      const currentPosition = startPosition + endPosition * easing;
      rouletteContainer.style.transform = `translateX(-${currentPosition}px)`;

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        // Завершение анимации
        setTimeout(() => {
          showPrize(prize);
          savePrizeToInventory(prize);
        }, 500);
      }
    };

    requestAnimationFrame(animate);
  } else {
    // Быстрое открытие
    setTimeout(() => {
      rouletteContainer.style.transform = `translateX(-${prizeIndex * 120}px)`;
      setTimeout(() => {
        showPrize(prize);
        savePrizeToInventory(prize);
      }, 500);
    }, 100);
  }
}

// Показать выигранный приз
function showPrize(prize) {
  document.getElementById("prize-name").textContent = prize.name;
  document.getElementById("prize-image").src = prize.image;
  document.getElementById("prize-rarity").textContent = getRarityName(
    prize.rarity
  );
  document.getElementById("prize-rarity").className = prize.rarity;

  openCaseScreen.classList.add("hidden");
  resultScreen.classList.remove("hidden");
}

// Сохранить приз в инвентарь
function savePrizeToInventory(prize) {
  if (!currentUser) return;

  // Добавляем предмет в инвентарь
  userInventory.push({
    ...prize,
    date: new Date().toLocaleDateString(),
  });

  // Обновляем данные пользователя
  currentUser.inventory = userInventory;
  localStorage.setItem(`user_${currentUser.id}`, JSON.stringify(currentUser));

  // В реальном приложении здесь нужно отправить данные на сервер
  console.log(`Предмет "${prize.name}" сохранен в инвентарь`);
}

// Показать инвентарь
function showInventoryScreen() {
  // Загружаем инвентарь
  if (currentUser) {
    userInventory = currentUser.inventory || [];
  }

  // Заполняем сетку инвентаря
  const inventoryGrid = document.querySelector(".inventory-grid");
  inventoryGrid.innerHTML = "";

  if (userInventory.length === 0) {
    inventoryGrid.innerHTML = "<p>Ваш инвентарь пуст</p>";
  } else {
    userInventory.forEach((item) => {
      const itemElement = document.createElement("div");
      itemElement.className = "inventory-item";
      itemElement.innerHTML = `
                <img src="${item.image}" alt="${item.name}">
                <p>${item.name}</p>
                <p class="${item.rarity}">${getRarityName(item.rarity)}</p>
                <p>Цена: ${item.price}₽</p>
            `;
      inventoryGrid.appendChild(itemElement);
    });
  }

  // Показываем экран инвентаря
  casesScreen.classList.add("hidden");
  openCaseScreen.classList.add("hidden");
  resultScreen.classList.add("hidden");
  inventoryScreen.classList.remove("hidden");
}

// Вспомогательные функции
function getRandomItem(items) {
  return items[Math.floor(Math.random() * items.length)];
}

function getRandomItemWithChance(items) {
  const totalChance = items.reduce((sum, item) => sum + item.chance, 0);
  const random = Math.random() * totalChance;

  let currentSum = 0;
  for (const item of items) {
    currentSum += item.chance;
    if (random <= currentSum) {
      return item;
    }
  }

  return items[0];
}

function getRarityName(rarity) {
  const names = {
    common: "Обычный",
    rare: "Редкий",
    epic: "Эпический",
    legendary: "Легендарный",
  };
  return names[rarity] || "";
}
