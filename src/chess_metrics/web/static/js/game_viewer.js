let gameData = null;
let analysisData = null;
let currentPly = 0;
let board = null;
let chart = null;
let visibleErrors = {
    blunder: true,
    mistake: true,
    inaccuracy: true
};

async function initGameViewer(gameId) {
    try {
        console.log(`Loading game ${gameId}...`);

        // Load game data
        const gameResponse = await fetch(`/api/game/${gameId}`);
        if (!gameResponse.ok) throw new Error('Failed to load game');
        gameData = await gameResponse.json();
        console.log('Game data loaded:', gameData);

        // Load analysis data
        const analysisResponse = await fetch(`/api/analysis/${gameId}`);
        if (!analysisResponse.ok) throw new Error('Failed to load analysis');
        analysisData = await analysisResponse.json();
        console.log('Analysis data loaded:', analysisData);
        
        // Initialize UI
        initBoard();
        initChart();
        renderGameInfo();
        renderMoveList();
        renderAnalysisSummary();
        
        // Show first position
        showPosition(0);
        
        // Setup event listeners
        document.getElementById('btnFirst').addEventListener('click', () => showPosition(0));
        document.getElementById('btnPrev').addEventListener('click', () => showPosition(Math.max(0, currentPly - 1)));
        document.getElementById('btnNext').addEventListener('click', () => showPosition(Math.min(gameData.positions.length - 1, currentPly + 1)));
        document.getElementById('btnLast').addEventListener('click', () => showPosition(gameData.positions.length - 1));

        // Metric toggle listeners
        document.querySelectorAll('.metric-toggle').forEach(toggle => {
            toggle.addEventListener('click', () => {
                const metric = toggle.dataset.metric;
                toggle.classList.toggle('active');
                toggleMetric(metric);
            });
        });

        // Error toggle listeners
        document.querySelectorAll('.error-toggle').forEach(toggle => {
            toggle.addEventListener('click', () => {
                const errorType = toggle.dataset.error;
                toggle.classList.toggle('active');
                toggleError(errorType);
            });
        });

        // Keyboard navigation
        document.addEventListener('keydown', handleKeyPress);

        document.getElementById('loading').style.display = 'none';
        document.getElementById('gameContent').style.display = 'block';

        // Resize board after display
        setTimeout(() => {
            if (board) {
                board.resize();
            }
        }, 100);
    } catch (error) {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('error').textContent = error.message;
        document.getElementById('error').style.display = 'block';
    }
}

function initBoard() {
    // Check if Chessboard is available
    if (typeof Chessboard === 'undefined') {
        console.error('Chessboard.js library not loaded!');
        return;
    }

    const config = {
        draggable: false,
        position: 'start',
        pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png'
    };

    try {
        board = Chessboard('board', config);
        console.log('Board initialized successfully');
    } catch (error) {
        console.error('Error initializing board:', error);
    }

    // Ensure board is properly sized
    window.addEventListener('resize', () => {
        if (board) {
            board.resize();
        }
    });
}

function initChart() {
    const ctx = document.getElementById('metricsChart').getContext('2d');

    // Prepare data
    const labels = gameData.positions.map(p => {
        const moveNum = Math.floor((p.ply + 1) / 2);
        const side = p.ply % 2 === 1 ? '.' : '...';
        return `${moveNum}${side}`;
    });

    // Create background colors array for blunder highlighting
    const backgroundColors = gameData.positions.map((p, index) => {
        const blunder = analysisData.blunders.find(b => b.ply === p.ply);
        if (!blunder) return 'transparent';

        switch(blunder.severity) {
            case 'blunder': return 'rgba(220, 53, 69, 0.15)';
            case 'mistake': return 'rgba(253, 126, 20, 0.15)';
            case 'inaccuracy': return 'rgba(255, 193, 7, 0.15)';
            default: return 'transparent';
        }
    });

    // Define metric colors (same color for White and Black, different symbols)
    const metricColors = {
        pv: 'rgb(59, 130, 246)',      // Blue for Material
        mv: 'rgb(34, 197, 94)',       // Green for Mobility
        ov: 'rgb(168, 85, 247)',      // Purple for Offense
        dv: 'rgb(249, 115, 22)'       // Orange for Defense
    };

    // Define all 8 metrics with unified colors per metric type
    const datasets = [
        {
            label: 'White PV (Material)',
            data: gameData.positions.map(p => p.pv_w),
            borderColor: 'transparent',  // No line
            backgroundColor: 'transparent',
            tension: 0.1,
            borderWidth: 0,              // No line
            showLine: false,             // Explicitly hide line
            pointStyle: 'circle',
            pointRadius: 0,              // Hide default point
            pointHoverRadius: 0,
            playerMarker: 'W',
            markerColor: metricColors.pv,
            hidden: false
        },
        {
            label: 'Black PV (Material)',
            data: gameData.positions.map(p => p.pv_b),
            borderColor: 'transparent',  // No line
            backgroundColor: 'transparent',
            tension: 0.1,
            borderWidth: 0,              // No line
            showLine: false,             // Explicitly hide line
            pointStyle: 'circle',
            pointRadius: 0,              // Hide default point
            pointHoverRadius: 0,
            playerMarker: 'B',
            markerColor: metricColors.pv,
            hidden: false
        },
        {
            label: 'White MV (Mobility)',
            data: gameData.positions.map(p => p.mv_w),
            borderColor: 'transparent',  // No line
            backgroundColor: 'transparent',
            tension: 0.1,
            borderWidth: 0,              // No line
            showLine: false,             // Explicitly hide line
            pointStyle: 'circle',
            pointRadius: 0,              // Hide default point
            pointHoverRadius: 0,
            playerMarker: 'W',
            markerColor: metricColors.mv,
            hidden: true
        },
        {
            label: 'Black MV (Mobility)',
            data: gameData.positions.map(p => p.mv_b),
            borderColor: 'transparent',  // No line
            backgroundColor: 'transparent',
            tension: 0.1,
            borderWidth: 0,              // No line
            showLine: false,             // Explicitly hide line
            pointStyle: 'circle',
            pointRadius: 0,              // Hide default point
            pointHoverRadius: 0,
            playerMarker: 'B',
            markerColor: metricColors.mv,
            hidden: true
        },
        {
            label: 'White OV (Offense)',
            data: gameData.positions.map(p => p.ov_w),
            borderColor: 'transparent',  // No line
            backgroundColor: 'transparent',
            tension: 0.1,
            borderWidth: 0,              // No line
            showLine: false,             // Explicitly hide line
            pointStyle: 'circle',
            pointRadius: 0,              // Hide default point
            pointHoverRadius: 0,
            playerMarker: 'W',
            markerColor: metricColors.ov,
            hidden: true
        },
        {
            label: 'Black OV (Offense)',
            data: gameData.positions.map(p => p.ov_b),
            borderColor: 'transparent',  // No line
            backgroundColor: 'transparent',
            tension: 0.1,
            borderWidth: 0,              // No line
            showLine: false,             // Explicitly hide line
            pointStyle: 'circle',
            pointRadius: 0,              // Hide default point
            pointHoverRadius: 0,
            playerMarker: 'B',
            markerColor: metricColors.ov,
            hidden: true
        },
        {
            label: 'White DV (Defense)',
            data: gameData.positions.map(p => p.dv_w),
            borderColor: 'transparent',  // No line
            backgroundColor: 'transparent',
            tension: 0.1,
            borderWidth: 0,              // No line
            showLine: false,             // Explicitly hide line
            pointStyle: 'circle',
            pointRadius: 0,              // Hide default point
            pointHoverRadius: 0,
            playerMarker: 'W',
            markerColor: metricColors.dv,
            hidden: true
        },
        {
            label: 'Black DV (Defense)',
            data: gameData.positions.map(p => p.dv_b),
            borderColor: 'transparent',  // No line
            backgroundColor: 'transparent',
            tension: 0.1,
            borderWidth: 0,              // No line
            showLine: false,             // Explicitly hide line
            pointStyle: 'circle',
            pointRadius: 0,              // Hide default point
            pointHoverRadius: 0,
            playerMarker: 'B',
            markerColor: metricColors.dv,
            hidden: true
        }
    ];

    // Custom plugin to draw W/B text markers
    const textMarkerPlugin = {
        id: 'textMarkerPlugin',
        afterDatasetsDraw(chart) {
            const ctx = chart.ctx;
            const chartArea = chart.chartArea;

            // Clip to chart area to prevent drawing outside bounds
            ctx.save();
            ctx.beginPath();
            ctx.rect(chartArea.left, chartArea.top, chartArea.right - chartArea.left, chartArea.bottom - chartArea.top);
            ctx.clip();

            chart.data.datasets.forEach((dataset, datasetIndex) => {
                const meta = chart.getDatasetMeta(datasetIndex);
                if (!meta.hidden && dataset.playerMarker) {
                    meta.data.forEach((point, index) => {
                        const {x, y} = point.tooltipPosition();

                        // Draw text marker
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'middle';
                        ctx.fillStyle = dataset.markerColor;
                        ctx.font = 'bold 14px Arial';
                        ctx.fillText(dataset.playerMarker, x, y);
                    });
                }
            });

            ctx.restore();
        }
    };

    // Custom plugin to draw background highlights for errors
    const blunderHighlightPlugin = {
        id: 'blunderHighlight',
        beforeDraw: (chart) => {
            const ctx = chart.ctx;
            const chartArea = chart.chartArea;
            const xAxis = chart.scales.x;

            // Draw background for blunders
            gameData.positions.forEach((pos, index) => {
                const blunder = analysisData.blunders.find(b => b.ply === pos.ply);
                if (!blunder) return;

                // Check if this error type is visible
                if (!visibleErrors[blunder.severity]) return;

                let color;
                switch(blunder.severity) {
                    case 'blunder': color = 'rgba(220, 53, 69, 0.1)'; break;
                    case 'mistake': color = 'rgba(253, 126, 20, 0.1)'; break;
                    case 'inaccuracy': color = 'rgba(255, 193, 7, 0.1)'; break;
                    default: return;
                }

                const x = xAxis.getPixelForValue(index);
                const width = xAxis.width / gameData.positions.length;

                ctx.fillStyle = color;
                ctx.fillRect(x - width/2, chartArea.top, width, chartArea.bottom - chartArea.top);
            });
        }
    };

    // Custom plugin to draw vertical lines for all error types
    const verticalLinePlugin = {
        id: 'verticalLinePlugin',
        afterDatasetsDraw(chart) {
            const ctx = chart.ctx;
            const chartArea = chart.chartArea;
            const xAxis = chart.scales.x;

            ctx.save();

            // Include all error types: blunders, mistakes, and inaccuracies
            analysisData.blunders.forEach(error => {
                // Check if this error type is visible
                if (!visibleErrors[error.severity]) return;

                // Find the index of this ply in positions
                const index = gameData.positions.findIndex(p => p.ply === error.ply);
                if (index === -1) return;

                const x = xAxis.getPixelForValue(index);

                // Determine color based on severity
                let color;
                if (error.severity === 'blunder') {
                    color = 'rgba(220, 53, 69, 0.8)'; // Red
                } else if (error.severity === 'mistake') {
                    color = 'rgba(253, 126, 20, 0.8)'; // Orange
                } else if (error.severity === 'inaccuracy') {
                    color = 'rgba(255, 193, 7, 0.8)'; // Yellow
                } else {
                    return; // Skip unknown severity
                }

                // Draw vertical line
                ctx.strokeStyle = color;
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.moveTo(x, chartArea.top);
                ctx.lineTo(x, chartArea.bottom);
                ctx.stroke();

                // Draw W or B label above the line
                const label = error.side === 'white' ? 'W' : 'B';
                ctx.fillStyle = color;
                ctx.font = 'bold 12px Arial';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'bottom';
                ctx.fillText(label, x, chartArea.top - 5);
            });

            ctx.restore();
        }
    };

    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        plugins: [blunderHighlightPlugin, textMarkerPlugin, verticalLinePlugin],
        options: {
            responsive: true,
            maintainAspectRatio: true,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            layout: {
                padding: {
                    top: 25,
                    right: 25,
                    bottom: 15,
                    left: 15
                }
            },
            plugins: {
                legend: {
                    display: false  // Hide legend
                },
                title: {
                    display: false  // Title removed, using metric toggles instead
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += context.parsed.y.toFixed(1);
                            }

                            // Add blunder info to tooltip
                            const ply = gameData.positions[context.dataIndex].ply;
                            const blunder = analysisData.blunders.find(b => b.ply === ply);
                            if (blunder) {
                                label += ` [${blunder.severity.toUpperCase()}]`;
                            }

                            return label;
                        },
                        afterLabel: function(context) {
                            const ply = gameData.positions[context.dataIndex].ply;
                            const blunder = analysisData.blunders.find(b => b.ply === ply);
                            if (blunder) {
                                return `Metric swing: ${blunder.metric_swing.toFixed(1)}`;
                            }
                            return '';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grace: '10%',  // Add 10% padding to prevent clipping
                    title: {
                        display: true,
                        text: 'Metric Value'
                    }
                },
                x: {
                    grace: '2%',  // Add padding on x-axis too
                    title: {
                        display: true,
                        text: 'Move'
                    }
                }
            }
        }
    });

    // Hide all datasets except PV on initial load
    chart.data.datasets.forEach((dataset, index) => {
        if (!dataset.label.includes('PV')) {
            chart.hide(index);
        }
    });
}

function toggleMetric(metric) {
    if (!chart) return;

    // Find datasets for this metric (both White and Black)
    chart.data.datasets.forEach((dataset, index) => {
        if (dataset.label.toLowerCase().includes(metric)) {
            if (chart.isDatasetVisible(index)) {
                chart.hide(index);
            } else {
                chart.show(index);
            }
        }
    });
}

function toggleError(errorType) {
    if (!chart) return;

    // Toggle visibility state
    visibleErrors[errorType] = !visibleErrors[errorType];

    // Redraw the chart to update error highlighting
    chart.update();
}

function renderGameInfo() {
    const game = gameData.game;
    document.getElementById('gameTitle').textContent = 
        `Game #${game.game_id}: ${game.white_name} vs ${game.black_name}`;
    document.getElementById('gameInfo').textContent = 
        `Result: ${game.result} (${game.termination}) • Date: ${new Date(game.created_utc).toLocaleString()}`;
}

function renderMoveList() {
    const moveList = document.getElementById('moveList');
    let html = '<div class="move-list">';
    
    for (let i = 0; i < gameData.positions.length; i++) {
        const pos = gameData.positions[i];
        if (!pos.last_move_san) continue; // Skip initial position
        
        const moveNum = Math.floor((pos.ply + 1) / 2);
        const isWhite = pos.ply % 2 === 1;
        
        // Find if this move is a blunder
        const blunder = analysisData.blunders.find(b => b.ply === pos.ply);
        const blunderClass = blunder ? `blunder-${blunder.severity}` : '';
        
        if (isWhite) {
            html += `<div class="move-pair">`;
            html += `<span class="move-number">${moveNum}.</span> `;
        }
        
        html += `<span class="move ${blunderClass}" data-ply="${i}" onclick="showPosition(${i})">${pos.last_move_san}</span> `;
        
        if (!isWhite) {
            html += `</div>`;
        }
    }
    
    html += '</div>';
    moveList.innerHTML = html;
}

function renderAnalysisSummary() {
    const stats = analysisData.statistics;

    const blundersW = document.getElementById('blunders_w');
    const blundersB = document.getElementById('blunders_b');
    const mistakesW = document.getElementById('mistakes_w');
    const mistakesB = document.getElementById('mistakes_b');
    const inaccuraciesW = document.getElementById('inaccuracies_w');
    const inaccuraciesB = document.getElementById('inaccuracies_b');

    if (blundersW) blundersW.textContent = stats.white_blunders;
    if (blundersB) blundersB.textContent = stats.black_blunders;
    if (mistakesW) mistakesW.textContent = stats.white_mistakes;
    if (mistakesB) mistakesB.textContent = stats.black_mistakes;
    if (inaccuraciesW) inaccuraciesW.textContent = stats.white_inaccuracies;
    if (inaccuraciesB) inaccuraciesB.textContent = stats.black_inaccuracies;
}

function showPosition(ply) {
    currentPly = ply;
    const pos = gameData.positions[ply];

    if (!pos) {
        console.error(`Position at ply ${ply} not found`);
        return;
    }

    // Update board - use the position() method with animation
    if (board) {
        board.position(pos.fen, true); // true enables animation
    } else {
        console.error('Board not initialized');
    }

    // Update current move display
    if (pos.last_move_san) {
        const moveNum = Math.floor((pos.ply + 1) / 2);
        const side = pos.ply % 2 === 1 ? '.' : '...';
        document.getElementById('currentMove').textContent = `${moveNum}${side} ${pos.last_move_san}`;
    } else {
        document.getElementById('currentMove').textContent = 'Start Position';
    }

    document.getElementById('currentFen').textContent = pos.fen;

    // Update metrics
    document.getElementById('pv_w').textContent = pos.pv_w.toFixed(1);
    document.getElementById('mv_w').textContent = pos.mv_w.toFixed(1);
    document.getElementById('ov_w').textContent = pos.ov_w.toFixed(1);
    document.getElementById('dv_w').textContent = pos.dv_w.toFixed(1);
    document.getElementById('pv_b').textContent = pos.pv_b.toFixed(1);
    document.getElementById('mv_b').textContent = pos.mv_b.toFixed(1);
    document.getElementById('ov_b').textContent = pos.ov_b.toFixed(1);
    document.getElementById('dv_b').textContent = pos.dv_b.toFixed(1);

    // Highlight current move in move list
    document.querySelectorAll('.move').forEach(el => el.classList.remove('active'));
    const currentMoveEl = document.querySelector(`.move[data-ply="${ply}"]`);
    if (currentMoveEl) {
        currentMoveEl.classList.add('active');
        currentMoveEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // Update button states
    updateButtonStates();
}

function updateButtonStates() {
    const btnFirst = document.getElementById('btnFirst');
    const btnPrev = document.getElementById('btnPrev');
    const btnNext = document.getElementById('btnNext');
    const btnLast = document.getElementById('btnLast');

    // Disable first/prev if at start
    btnFirst.disabled = currentPly === 0;
    btnPrev.disabled = currentPly === 0;

    // Disable next/last if at end
    const maxPly = gameData.positions.length - 1;
    btnNext.disabled = currentPly >= maxPly;
    btnLast.disabled = currentPly >= maxPly;
}

function handleKeyPress(e) {
    if (!gameData) return;

    const maxPly = gameData.positions.length - 1;

    switch(e.key) {
        case 'ArrowLeft':
            e.preventDefault();
            showPosition(Math.max(0, currentPly - 1));
            break;
        case 'ArrowRight':
            e.preventDefault();
            showPosition(Math.min(maxPly, currentPly + 1));
            break;
        case 'Home':
            e.preventDefault();
            showPosition(0);
            break;
        case 'End':
            e.preventDefault();
            showPosition(maxPly);
            break;
    }
}
