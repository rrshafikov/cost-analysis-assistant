// static/js/dashboard_chart.js
(function () {
    const canvas = document.getElementById("expensesChart");
    if (!canvas) {
        return;
    }

    const categoryLabelsRaw = canvas.dataset.categoryLabels || "[]";
    const categoryValuesRaw = canvas.dataset.categoryValues || "[]";
    const dayLabelsRaw = canvas.dataset.dayLabels || "[]";
    const dayValuesRaw = canvas.dataset.dayValues || "[]";

    let categoryLabels, categoryValues, dayLabels, dayValues;

    try {
        categoryLabels = JSON.parse(categoryLabelsRaw);
        categoryValues = JSON.parse(categoryValuesRaw);
        dayLabels = JSON.parse(dayLabelsRaw);
        dayValues = JSON.parse(dayValuesRaw);
    } catch (e) {
        console.error("Failed to parse chart data", e, {
            categoryLabelsRaw,
            categoryValuesRaw,
            dayLabelsRaw,
            dayValuesRaw
        });
        return;
    }

    if (!categoryLabels.length && !dayLabels.length) {
        return;
    }

    const ctx = canvas.getContext("2d");

    // Определяем стартовый режим
    let currentMode = categoryLabels.length ? "category" : "day";

    function getDataForMode(mode) {
        if (mode === "day" && dayLabels.length) {
            return {
                labels: dayLabels,
                values: dayValues,
                tooltipUnit: "RUB/day"
            };
        }
        // по умолчанию и если нет day — категории
        return {
            labels: categoryLabels,
            values: categoryValues,
            tooltipUnit: "RUB"
        };
    }

    const initial = getDataForMode(currentMode);

    // Базовая конфигурация диаграммы
    const chart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: initial.labels,
            datasets: [
                {
                    label: "Amount",
                    data: initial.values,
                    borderWidth: 1,
                    backgroundColor: "rgba(37, 99, 235, 0.18)",
                    borderColor: "rgba(37, 99, 235, 0.6)",
                    hoverBackgroundColor: "rgba(37, 99, 235, 0.35)",
                    hoverBorderColor: "rgba(37, 99, 235, 0.9)",
                    hoverBorderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 250,
                easing: "easeOutQuad"
            },
            scales: {
                x: {
                    display: false // подписи под диаграммой скрыты
                },
                y: {
                    beginAtZero: true
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: true,
                    callbacks: {
                        label: function (context) {
                            const mode = currentMode;
                            const data = getDataForMode(mode);
                            const label = data.labels[context.dataIndex];
                            const value = data.values[context.dataIndex] || 0;
                            const unit = data.tooltipUnit;
                            return `${label}: ${value.toFixed(2)} ${unit}`;
                        }
                    }
                }
            }
        }
    });

    // --- Переключатель режимов ---
    const btnCategory = document.getElementById("chart-toggle-category");
    const btnDay = document.getElementById("chart-toggle-day");

    function updateToggleButtons() {
        if (btnCategory) {
            btnCategory.classList.toggle(
                "chart-toggle-button-active",
                currentMode === "category"
            );
        }
        if (btnDay) {
            btnDay.classList.toggle(
                "chart-toggle-button-active",
                currentMode === "day"
            );
        }
    }

    function switchMode(mode) {
        const data = getDataForMode(mode);

        if (!data.labels.length) {
            return;
        }

        currentMode = mode;
        chart.data.labels = data.labels;
        chart.data.datasets[0].data = data.values;
        chart.update();

        updateToggleButtons();
    }

    if (btnCategory) {
        btnCategory.addEventListener("click", function () {
            switchMode("category");
        });
    }

    if (btnDay) {
        btnDay.addEventListener("click", function () {
            switchMode("day");
        });
    }

    // Установим корректное начальное состояние кнопок
    updateToggleButtons();
})();
