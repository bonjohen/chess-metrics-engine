# Demo: AI vs AI game
# This demonstrates the play-game feature with two AI players

Write-Host "=== Chess Metrics Engine - AI vs AI Demo ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will play a quick game between two AI players:" -ForegroundColor Yellow
Write-Host "  White: 'Aggressive AI' (offense-first profile)" -ForegroundColor White
Write-Host "  Black: 'Defensive AI' (defense-first profile)" -ForegroundColor Gray
Write-Host ""
Write-Host "The game will be saved to demo.sqlite" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to stop the game at any time." -ForegroundColor Yellow
Write-Host ""

# Clean up old demo database
if (Test-Path "demo.sqlite") {
    Remove-Item "demo.sqlite"
}

# Set Python path and run
$env:PYTHONPATH = "src"

python -m chess_metrics.cli play-game `
    --db demo.sqlite `
    --white "Aggressive AI" `
    --white-type ai `
    --black "Defensive AI" `
    --black-type ai `
    --ai-depth 2 `
    --ai-profile offense-first

Write-Host ""
Write-Host "=== Game Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "You can view the game data with:" -ForegroundColor Yellow
Write-Host "  sqlite3 demo.sqlite 'SELECT * FROM games;'" -ForegroundColor White
Write-Host "  sqlite3 demo.sqlite 'SELECT ply, san, uci FROM moves WHERE game_id=1;'" -ForegroundColor White
Write-Host ""

