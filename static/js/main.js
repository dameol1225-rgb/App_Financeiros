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

        new window.Chart(chartCanvas, {
            type: "doughnut",
            data: {
                labels: parsed.labels,
                datasets: [
                    {
                        data: parsed.values,
                        backgroundColor: parsed.colors,
                        borderColor: "#ffffff",
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
                            color: "#16324f",
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

    mountDoughnutChart(
        "dashboard-expense-chart-data",
        "dashboardExpenseChart",
        "Sem gastos suficientes neste mes para montar o grafico."
    );
    mountDoughnutChart(
        "history-chart-data",
        "historyChart",
        "Nenhum dado suficiente para montar o grafico neste periodo."
    );

    document.querySelectorAll("[data-print-trigger]").forEach((button) => {
        button.addEventListener("click", () => {
            window.print();
        });
    });
});

