// === Mystic Tarot App ===

const SPREAD_CONFIG = {
    single: {
        count: 1,
        positions: ['Your Card'],
        description: 'A single card drawn for quick insight into your current situation or question.'
    },
    three: {
        count: 3,
        positions: ['Past', 'Present', 'Future'],
        description: 'Three cards representing the flow of time \u2014 what shaped you, where you stand, and what lies ahead.'
    },
    celtic: {
        count: 10,
        positions: [
            'Present \u2014 The heart of the matter',
            'Challenge \u2014 What crosses you',
            'Foundation \u2014 The root cause',
            'Recent Past \u2014 What is passing',
            'Crown \u2014 Best possible outcome',
            'Near Future \u2014 What is approaching',
            'Self \u2014 How you see yourself',
            'Environment \u2014 Outside influences',
            'Hopes & Fears \u2014 Your inner world',
            'Outcome \u2014 The final result'
        ],
        description: 'The classic Celtic Cross \u2014 a comprehensive 10-card spread covering all aspects of your question.'
    }
};

let currentSpread = 'single';
let drawnCards = [];
let isReading = false;

// === Initialize ===
document.addEventListener('DOMContentLoaded', () => {
    createStarfield();
    setupEventListeners();
});

function createStarfield() {
    const container = document.getElementById('stars');
    const count = 150;
    for (let i = 0; i < count; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        star.style.left = Math.random() * 100 + '%';
        star.style.top = Math.random() * 100 + '%';
        star.style.setProperty('--duration', (2 + Math.random() * 4) + 's');
        star.style.setProperty('--max-opacity', (0.3 + Math.random() * 0.7));
        star.style.animationDelay = Math.random() * 4 + 's';
        container.appendChild(star);
    }
}

function setupEventListeners() {
    // Spread selector buttons
    document.querySelectorAll('.spread-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (isReading) return;
            document.querySelectorAll('.spread-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentSpread = btn.dataset.spread;
        });
    });

    // Draw button
    document.getElementById('drawBtn').addEventListener('click', drawCards);

    // Reset button
    document.getElementById('resetBtn').addEventListener('click', resetReading);
}

// === Card Drawing ===
function drawCards() {
    if (isReading) return;
    isReading = true;

    const config = SPREAD_CONFIG[currentSpread];
    drawnCards = selectRandomCards(config.count);

    const readingArea = document.getElementById('readingArea');
    readingArea.innerHTML = '';

    if (currentSpread === 'celtic') {
        readingArea.classList.add('celtic-layout');
    } else {
        readingArea.classList.remove('celtic-layout');
    }

    // Animate cards appearing one by one
    drawnCards.forEach((card, index) => {
        setTimeout(() => {
            const cardEl = createCardElement(card, config.positions[index], index);
            readingArea.appendChild(cardEl);

            // Auto-flip after a delay
            setTimeout(() => {
                const tarotCard = cardEl.querySelector('.tarot-card');
                tarotCard.classList.add('flipped');

                // Show info after flip
                setTimeout(() => {
                    const info = cardEl.querySelector('.card-info');
                    info.style.opacity = '1';
                }, 500);

                // After all cards are flipped, show summary
                if (index === drawnCards.length - 1) {
                    setTimeout(() => showReadingSummary(), 800);
                }
            }, 600);
        }, index * 400);
    });

    // Toggle buttons
    document.getElementById('drawBtn').style.display = 'none';
    document.getElementById('resetBtn').style.display = 'inline-block';

    // Disable spread selection during reading
    document.querySelectorAll('.spread-btn').forEach(b => b.style.pointerEvents = 'none');
}

function selectRandomCards(count) {
    const deck = [...TAROT_DECK];
    const selected = [];

    for (let i = 0; i < count; i++) {
        const randomIndex = Math.floor(Math.random() * deck.length);
        const card = deck.splice(randomIndex, 1)[0];
        // ~40% chance of reversal
        const isReversed = Math.random() < 0.4;
        selected.push({ ...card, isReversed });
    }

    return selected;
}

function createCardElement(card, position, index) {
    const wrapper = document.createElement('div');
    wrapper.className = 'tarot-card-wrapper';
    wrapper.style.animationDelay = (index * 0.15) + 's';

    const posLabel = document.createElement('div');
    posLabel.className = 'position-label';
    posLabel.textContent = position;

    const tarotCard = document.createElement('div');
    tarotCard.className = 'tarot-card' + (card.isReversed ? ' reversed' : '');

    // Card back
    const back = document.createElement('div');
    back.className = 'card-back';
    const backDesign = document.createElement('div');
    backDesign.className = 'card-back-design';
    back.appendChild(backDesign);

    // Card front
    const front = document.createElement('div');
    front.className = 'card-front';

    const img = document.createElement('img');
    img.className = 'card-image';
    img.alt = card.name;
    img.src = card.image;
    img.loading = 'lazy';
    img.onerror = function() {
        // Fallback to symbol placeholder if image fails to load
        const placeholder = document.createElement('div');
        placeholder.className = 'card-image-placeholder';
        placeholder.textContent = card.symbol;
        this.replaceWith(placeholder);
    };

    const title = document.createElement('div');
    title.className = 'card-title';
    title.textContent = card.name;

    if (card.isReversed) {
        const badge = document.createElement('div');
        badge.className = 'reversed-badge';
        badge.textContent = '(Reversed)';
        front.appendChild(img);
        front.appendChild(title);
        front.appendChild(badge);
    } else {
        front.appendChild(img);
        front.appendChild(title);
    }

    tarotCard.appendChild(back);
    tarotCard.appendChild(front);

    // Click to toggle flip
    tarotCard.addEventListener('click', () => {
        tarotCard.classList.toggle('flipped');
    });

    // Card info below
    const info = document.createElement('div');
    info.className = 'card-info';
    info.style.opacity = '0';
    info.style.transition = 'opacity 0.5s ease';

    const infoName = document.createElement('div');
    infoName.className = 'info-name';
    infoName.textContent = card.name + (card.isReversed ? ' (Rev.)' : '');

    const infoDesc = document.createElement('div');
    infoDesc.className = 'info-desc';
    infoDesc.textContent = card.isReversed ? card.reversed : card.upright;

    info.appendChild(infoName);
    info.appendChild(infoDesc);

    wrapper.appendChild(posLabel);
    wrapper.appendChild(tarotCard);
    wrapper.appendChild(info);

    return wrapper;
}

// === Reading Summary ===
function showReadingSummary() {
    const config = SPREAD_CONFIG[currentSpread];
    const infoPanel = document.getElementById('spreadInfo');
    infoPanel.classList.add('visible');

    let html = `<h3>Your ${config.positions.length === 1 ? 'Card' : config.positions.length + '-Card'} Reading</h3>`;
    html += `<div class="reading-summary">`;

    drawnCards.forEach((card, i) => {
        const reversedClass = card.isReversed ? ' reversed' : '';
        const reversedLabel = card.isReversed ? ' (Reversed)' : '';
        const description = card.isReversed ? card.reversed : card.upright;

        html += `
            <div class="card-reading">
                <span class="position-name">${config.positions[i]}:</span>
                <span class="card-name${reversedClass}">${card.name}${reversedLabel}</span>
                <div class="description">${description}</div>
            </div>
        `;
    });

    html += `</div>`;
    infoPanel.innerHTML = html;
}

// === Reset ===
function resetReading() {
    isReading = false;
    drawnCards = [];

    const readingArea = document.getElementById('readingArea');
    readingArea.innerHTML = '';
    readingArea.classList.remove('celtic-layout');

    document.getElementById('spreadInfo').classList.remove('visible');
    document.getElementById('spreadInfo').innerHTML = '';

    document.getElementById('drawBtn').style.display = 'inline-block';
    document.getElementById('resetBtn').style.display = 'none';

    document.querySelectorAll('.spread-btn').forEach(b => b.style.pointerEvents = 'auto');
}
