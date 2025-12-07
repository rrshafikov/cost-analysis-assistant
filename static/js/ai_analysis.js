// static/js/ai_analysis.js
document.addEventListener("DOMContentLoaded", function () {
    const cards = document.querySelectorAll(".ai-card");
    if (!cards.length) {
        return;
    }

    const typingSpeed = 18; // мс на символ

    function typeCard(card) {
        const mainText = card.dataset.textMain || "";
        const adviceText = card.dataset.advice || "";

        card.textContent = "";
        let pos = 0;

        return new Promise((resolve) => {
            function step() {
                if (pos <= mainText.length) {
                    card.textContent = mainText.slice(0, pos);
                    pos += 1;
                    setTimeout(step, typingSpeed);
                } else {
                    // когда основной текст допечатан — добавляем совет, если есть
                    if (adviceText) {
                        const adviceSpan = document.createElement("span");
                        adviceSpan.className = "ai-advice";
                        adviceSpan.textContent = adviceText;
                        card.appendChild(adviceSpan);
                    }
                    resolve();
                }
            }
            step();
        });
    }

    async function runTyping() {
        for (const card of cards) {
            await typeCard(card);
        }
    }

    runTyping();
});
