# run_tests.ps1
# Helper script to run tests with proper PYTHONPATH

param(
    [string]$TestFile = "",
    [switch]$Verbose
)

$env:PYTHONPATH = "src"

if ($TestFile) {
    if ($Verbose) {
        python -m unittest discover -s tests -p "$TestFile" -v
    } else {
        python -m unittest discover -s tests -p "$TestFile"
    }
} else {
    if ($Verbose) {
        python -m unittest discover -s tests -v
    } else {
        python -m unittest discover -s tests
    }
}

