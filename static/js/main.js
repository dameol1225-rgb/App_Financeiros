document.addEventListener("DOMContentLoaded", () => {
    if (window.lucide) {
        window.lucide.createIcons();
    }

    const revealNodes = document.querySelectorAll("[data-reveal]");
    revealNodes.forEach((node, index) => {
        window.setTimeout(() => {
            node.classList.add("is-visible");
        }, 60 * index);
    });

    function getThemeValue(name, fallback) {
        const value = window.getComputedStyle(document.body).getPropertyValue(name).trim();
        return value || fallback;
    }

    function mountDoughnutChart(sourceId, canvasId, emptyMessageText) {
        const chartDataNode = document.getElementById(sourceId);
        const chartCanvas = document.getElementById(canvasId);

        if (!chartDataNode || !chartCanvas || !window.Chart) {
            return;
        }

        const parsed = JSON.parse(chartDataNode.textContent);
        const hasValues = Array.isArray(parsed.values) && parsed.values.some((value) => value > 0);

        if (!hasValues) {
            const emptyMessage = document.createElement("p");
            emptyMessage.className = "muted";
            emptyMessage.textContent = emptyMessageText;
            chartCanvas.replaceWith(emptyMessage);
            return;
        }

        const textColor = getThemeValue("--text", "#16324f");
        const surfaceColor = getThemeValue("--surface", "#ffffff");

        new window.Chart(chartCanvas, {
            type: "doughnut",
            data: {
                labels: parsed.labels,
                datasets: [
                    {
                        data: parsed.values,
                        backgroundColor: parsed.colors,
                        borderColor: surfaceColor,
                        borderWidth: 4,
                        hoverOffset: 8,
                    },
                ],
            },
            options: {
                cutout: "58%",
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            color: textColor,
                            boxWidth: 14,
                            padding: 18,
                            font: {
                                family: "Manrope",
                                size: 12,
                                weight: "700",
                            },
                        },
                    },
                },
            },
        });
    }

    function mountBarChart(sourceId, canvasId, emptyMessageText) {
        const chartDataNode = document.getElementById(sourceId);
        const chartCanvas = document.getElementById(canvasId);

        if (!chartDataNode || !chartCanvas || !window.Chart) {
            return;
        }

        const parsed = JSON.parse(chartDataNode.textContent);
        const hasValues = Array.isArray(parsed.values) && parsed.values.some((value) => value > 0);

        if (!hasValues) {
            const emptyMessage = document.createElement("p");
            emptyMessage.className = "muted";
            emptyMessage.textContent = emptyMessageText;
            chartCanvas.replaceWith(emptyMessage);
            return;
        }

        const primaryColor = getThemeValue("--primary", "#2563eb");
        const primaryStrongColor = getThemeValue("--primary-strong", "#14b8a6");
        const textColor = getThemeValue("--text", "#16324f");
        const mutedColor = getThemeValue("--muted", "#5f728a");
        const gridColor = getThemeValue("--surface-border", "rgba(125, 154, 192, 0.24)");

        new window.Chart(chartCanvas, {
            type: "bar",
            data: {
                labels: parsed.labels,
                datasets: [
                    {
                        label: "Gastos",
                        data: parsed.values,
                        backgroundColor: primaryColor,
                        hoverBackgroundColor: primaryStrongColor,
                        borderRadius: 14,
                        borderSkipped: false,
                        maxBarThickness: 42,
                    },
                ],
            },
            options: {
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false,
                    },
                },
                scales: {
                    x: {
                        ticks: {
                            color: textColor,
                            font: {
                                family: "Manrope",
                                weight: "700",
                            },
                        },
                        grid: {
                            display: false,
                        },
                    },
                    y: {
                        ticks: {
                            color: mutedColor,
                            callback: (value) => `R$ ${Number(value).toFixed(0)}`,
                        },
                        grid: {
                            color: gridColor,
                        },
                    },
                },
            },
        });
    }

    mountBarChart(
        "annual-expense-chart-data",
        "annualExpenseChart",
        "Sem gastos suficientes neste ano para montar o gráfico."
    );
    mountDoughnutChart(
        "history-chart-data",
        "historyChart",
        "Nenhum dado suficiente para montar o gráfico neste período."
    );

    const overlayMenus = document.querySelectorAll("[data-overlay-menu]");
    if (overlayMenus.length) {
        document.addEventListener("click", (event) => {
            overlayMenus.forEach((menu) => {
                if (!menu.contains(event.target)) {
                    menu.removeAttribute("open");
                }
            });
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                overlayMenus.forEach((menu) => menu.removeAttribute("open"));
            }
        });
    }

    document.querySelectorAll("[data-print-trigger]").forEach((button) => {
        button.addEventListener("click", () => {
            window.print();
        });
    });

    document.querySelectorAll("[data-expense-name-select]").forEach((select) => {
        select.addEventListener("change", () => {
            const targetInput = document.getElementById(select.dataset.targetFieldId);

            if (!targetInput || !select.value) {
                return;
            }

            targetInput.value = select.value;
            targetInput.focus();
        });
    });
});
