document.addEventListener('DOMContentLoaded', () => {
    let currentSlide = 1;
    const totalSlides = 9;

    const slides = document.querySelectorAll('.slide');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const counter = document.getElementById('slide-counter');

    function updateSlide() {
        slides.forEach((s, i) => {
            s.classList.toggle('active', i + 1 === currentSlide);
        });
        counter.textContent = `${currentSlide} / ${totalSlides}`;
        
        // Disable buttons if at limits
        prevBtn.style.opacity = currentSlide === 1 ? '0.5' : '1';
        nextBtn.style.opacity = currentSlide === totalSlides ? '0.5' : '1';

        // Re-animate charts if entering chart slide
        if (currentSlide === 4) initSkillsChart();
        if (currentSlide === 5) initLPChart();
        if (currentSlide === 6) initE2EChart();
        if (currentSlide === 7) initLinkedInChart();
    }

    prevBtn.addEventListener('click', () => {
        if (currentSlide > 1) {
            currentSlide--;
            updateSlide();
        }
    });

    nextBtn.addEventListener('click', () => {
        if (currentSlide < totalSlides) {
            currentSlide++;
            updateSlide();
        }
    });

    // --- CHART INITIALIZATION ---
    let skillsChart, lpChart, e2eChart, linkedinChart;

    const chartConfig = {
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, max: 1.1, grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#94a3b8' } },
                x: { grid: { display: false }, ticks: { color: '#f1f5f9' } }
            },
            plugins: {
                legend: { labels: { color: '#f1f5f9', font: { family: 'Inter' } } }
            }
        }
    };

    function initSkillsChart() {
        if (skillsChart) skillsChart.destroy();
        const ctx = document.getElementById('skillsChart').getContext('2d');
        skillsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['V1 Baseline', 'V2 Intermediate', 'V3 Optimized'],
                datasets: [
                    { label: 'Fidelidad Técnica', data: [0.75, 0.88, 0.98], backgroundColor: '#38bdf8' },
                    { label: 'Pertinencia Brechas', data: [0.60, 0.82, 0.95], backgroundColor: '#818cf8' },
                    { label: 'Seniority Consistency', data: [0.55, 0.78, 0.94], backgroundColor: '#00C4B6' }
                ]
            },
            ...chartConfig
        });
    }

    function initLPChart() {
        if (lpChart) lpChart.destroy();
        const ctx = document.getElementById('lpChart').getContext('2d');
        lpChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['V1', 'V2', 'V3 (Heuristic)'],
                datasets: [
                    { label: 'Orden Lógico', data: [0.65, 0.85, 0.98], backgroundColor: '#FFB800' },
                    { label: 'Eficacia Ruta', data: [0.58, 0.79, 0.96], backgroundColor: '#FF7B61' }
                ]
            },
            ...chartConfig
        });
    }

    function initE2EChart() {
        if (e2eChart) e2eChart.destroy();
        const ctx = document.getElementById('e2eChart').getContext('2d');
        e2eChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['V1', 'V2', 'V3'],
                datasets: [{
                    label: 'Calidad Sistema (E2E)',
                    data: [0.62, 0.84, 0.98],
                    borderColor: '#22c55e',
                    backgroundColor: 'rgba(34, 197, 94, 0.2)',
                    fill: true,
                    tension: 0.4
                }]
            },
            ...chartConfig
        });
    }

    function initLinkedInChart() {
        if (linkedinChart) linkedinChart.destroy();
        const ctx = document.getElementById('linkedinChart').getContext('2d');
        linkedinChart = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['Fidelidad', 'Brechas', 'Seniority', 'Eficacia', 'Orden', 'Calidad'],
                datasets: [{
                    label: 'Promedio Perfiles LinkedIn',
                    data: [0.97, 0.94, 1.00, 0.90, 0.81, 0.81],
                    backgroundColor: 'rgba(56, 189, 248, 0.4)',
                    borderColor: '#38bdf8',
                    pointBackgroundColor: '#fff'
                }]
            },
            options: {
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 1.0,
                        grid: { color: 'rgba(255,255,255,0.1)' },
                        angleLines: { color: 'rgba(255,255,255,0.1)' },
                        pointLabels: { color: '#f1f5f9', font: { size: 12 } }
                    }
                },
                plugins: { legend: { labels: { color: '#f1f5f9' } } }
            }
        });
    }

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowRight') nextBtn.click();
        if (e.key === 'ArrowLeft') prevBtn.click();
    });
});
