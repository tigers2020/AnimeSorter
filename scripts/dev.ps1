# AnimeSorter Development Scripts for PowerShell
# Usage: .\dev.ps1 [command]

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "AnimeSorter Development Commands (PowerShell):" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  help          Show this help" -ForegroundColor Yellow
    Write-Host "  setup         Set up development environment" -ForegroundColor Yellow
    Write-Host "  install       Install package and dependencies" -ForegroundColor Yellow
    Write-Host "  test          Run tests" -ForegroundColor Yellow
    Write-Host "  test-cov      Run tests with coverage" -ForegroundColor Yellow
    Write-Host "  test-fast     Run fast tests (excluding slow tests)" -ForegroundColor Yellow
    Write-Host "  lint          Run ruff linter" -ForegroundColor Yellow
    Write-Host "  lint-fix      Run ruff linter with fixes" -ForegroundColor Yellow
    Write-Host "  format        Format code with black" -ForegroundColor Yellow
    Write-Host "  format-check  Check code formatting" -ForegroundColor Yellow
    Write-Host "  type-check    Run mypy type checker" -ForegroundColor Yellow
    Write-Host "  security      Run security checks" -ForegroundColor Yellow
    Write-Host "  pre-commit    Run pre-commit hooks" -ForegroundColor Yellow
    Write-Host "  build         Build package" -ForegroundColor Yellow
    Write-Host "  build-exe     Build executable with PyInstaller" -ForegroundColor Yellow
    Write-Host "  dev           Run development server" -ForegroundColor Yellow
    Write-Host "  debug         Run with debug logging" -ForegroundColor Yellow
    Write-Host "  clean         Clean build artifacts" -ForegroundColor Yellow
    Write-Host "  clean-cache   Clean application cache" -ForegroundColor Yellow
    Write-Host "  check         Run all code quality checks" -ForegroundColor Yellow
    Write-Host "  test-all      Run all tests and security checks" -ForegroundColor Yellow
    Write-Host "  ci            Run CI pipeline locally" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Green
    Write-Host "  .\dev.ps1 setup" -ForegroundColor Gray
    Write-Host "  .\dev.ps1 test" -ForegroundColor Gray
    Write-Host "  .\dev.ps1 lint-fix" -ForegroundColor Gray
}

function Write-Step {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Green
}

function Write-Error-Step {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Red
}

function Invoke-Setup {
    Write-Step "🔧 Setting up development environment..."
    python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }

    pip install -e ".[dev]"
    if ($LASTEXITCODE -ne 0) { throw "Package installation failed" }

    pre-commit install
    if ($LASTEXITCODE -ne 0) { Write-Warning "pre-commit install failed" }

    Write-Step "✅ Development environment ready!"
}

function Invoke-Install {
    Write-Step "📦 Installing package..."
    pip install -e ".[dev]"
    if ($LASTEXITCODE -ne 0) { throw "Package installation failed" }
}

function Invoke-Test {
    Write-Step "🧪 Running tests..."
    pytest tests/ -v
    if ($LASTEXITCODE -ne 0) { throw "Tests failed" }
}

function Invoke-TestCov {
    Write-Step "🧪 Running tests with coverage..."
    pytest tests/ --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=70 -v
    if ($LASTEXITCODE -ne 0) { throw "Tests failed" }
}

function Invoke-TestFast {
    Write-Step "⚡ Running fast tests..."
    pytest tests/ -v -m "not slow"
    if ($LASTEXITCODE -ne 0) { throw "Tests failed" }
}

function Invoke-Lint {
    Write-Step "🔍 Running ruff linter..."
    ruff check src/ tests/
    if ($LASTEXITCODE -ne 0) { throw "Linting failed" }
}

function Invoke-LintFix {
    Write-Step "🔧 Running ruff linter with fixes..."
    ruff check src/ tests/ --fix
    if ($LASTEXITCODE -ne 0) { throw "Linting failed" }
}

function Invoke-Format {
    Write-Step "🎨 Formatting code with black..."
    black src/ tests/
    if ($LASTEXITCODE -ne 0) { throw "Formatting failed" }
}

function Invoke-FormatCheck {
    Write-Step "🎨 Checking code formatting..."
    black --check src/ tests/
    if ($LASTEXITCODE -ne 0) { throw "Format check failed" }
}

function Invoke-TypeCheck {
    Write-Step "🔍 Running mypy type checker..."
    mypy src/ --config-file=pyproject.toml
    if ($LASTEXITCODE -ne 0) { throw "Type checking failed" }
}

function Invoke-Security {
    Write-Step "🔒 Running security checks..."
    try {
        bandit -r src/ -f json -o bandit-report.json
    } catch {
        Write-Warning "Bandit security check had issues"
    }

    try {
        safety check --json --output safety-report.json
    } catch {
        Write-Warning "Safety check had issues"
    }

    Write-Step "📄 Security reports generated: bandit-report.json, safety-report.json"
}

function Invoke-PreCommit {
    Write-Step "🪝 Running pre-commit hooks..."
    pre-commit run --all-files
    if ($LASTEXITCODE -ne 0) { throw "Pre-commit hooks failed" }
}

function Invoke-Build {
    Write-Step "📦 Building package..."
    python -m build
    if ($LASTEXITCODE -ne 0) { throw "Build failed" }
}

function Invoke-BuildExe {
    Write-Step "🔨 Building executable..."
    pyinstaller --onefile --windowed --name "AnimeSorter" --add-data "resources/*;resources" --hidden-import PyQt5.QtWidgets --hidden-import PyQt5.QtCore --hidden-import PyQt5.QtGui --hidden-import tmdbsimple --hidden-import anitopy --hidden-import guessit src/main.py
    if ($LASTEXITCODE -ne 0) { throw "Executable build failed" }
}

function Invoke-Dev {
    Write-Step "🚀 Starting development mode..."
    python -m src.main
}

function Invoke-Debug {
    Write-Step "🐛 Starting debug mode..."
    $env:ANIMESORTER_LOG_LEVEL = "DEBUG"
    python -m src.main
}

function Invoke-Clean {
    Write-Step "🧹 Cleaning build artifacts..."

    $pathsToRemove = @(
        "build", "dist", "*.egg-info", "htmlcov",
        ".pytest_cache", ".mypy_cache", ".ruff_cache"
    )

    foreach ($path in $pathsToRemove) {
        if (Test-Path $path) {
            Remove-Item -Recurse -Force $path
        }
    }

    $filesToRemove = @(".coverage", "coverage.xml")
    foreach ($file in $filesToRemove) {
        if (Test-Path $file) {
            Remove-Item -Force $file
        }
    }

    # Remove Python cache files
    Get-ChildItem -Recurse -Directory -Name "__pycache__" | ForEach-Object {
        Remove-Item -Recurse -Force $_
    }

    Get-ChildItem -Recurse -File -Include "*.pyc", "*.pyo", "*.pyd" | Remove-Item -Force

    Write-Step "✅ Cleanup completed!"
}

function Invoke-CleanCache {
    Write-Step "🧹 Cleaning application cache..."
    $cachePaths = @(".cache", "$env:USERPROFILE\.cache\animesorter")

    foreach ($path in $cachePaths) {
        if (Test-Path $path) {
            Remove-Item -Recurse -Force $path
        }
    }

    Write-Step "✅ Cache cleanup completed!"
}

function Invoke-Check {
    Write-Step "🔍 Running all code quality checks..."
    try {
        Invoke-Lint
        Invoke-FormatCheck
        Invoke-TypeCheck
        Write-Step "✅ All code quality checks passed!"
    } catch {
        Write-Error-Step "❌ Code quality checks failed: $_"
        exit 1
    }
}

function Invoke-TestAll {
    Write-Step "🧪 Running all tests and security checks..."
    try {
        Invoke-TestCov
        Invoke-Security
        Write-Step "✅ All tests and security checks completed!"
    } catch {
        Write-Error-Step "❌ Tests or security checks failed: $_"
        exit 1
    }
}

function Invoke-CI {
    Write-Step "🚀 Running CI pipeline locally..."
    try {
        Invoke-Check
        Invoke-TestAll
        Write-Step "✅ CI pipeline completed successfully!"
    } catch {
        Write-Error-Step "❌ CI pipeline failed: $_"
        exit 1
    }
}

# Main command dispatcher
try {
    switch ($Command.ToLower()) {
        "help" { Show-Help }
        "setup" { Invoke-Setup }
        "install" { Invoke-Install }
        "test" { Invoke-Test }
        "test-cov" { Invoke-TestCov }
        "test-fast" { Invoke-TestFast }
        "lint" { Invoke-Lint }
        "lint-fix" { Invoke-LintFix }
        "format" { Invoke-Format }
        "format-check" { Invoke-FormatCheck }
        "type-check" { Invoke-TypeCheck }
        "security" { Invoke-Security }
        "pre-commit" { Invoke-PreCommit }
        "build" { Invoke-Build }
        "build-exe" { Invoke-BuildExe }
        "dev" { Invoke-Dev }
        "debug" { Invoke-Debug }
        "clean" { Invoke-Clean }
        "clean-cache" { Invoke-CleanCache }
        "check" { Invoke-Check }
        "test-all" { Invoke-TestAll }
        "ci" { Invoke-CI }
        default {
            Write-Error-Step "❌ Unknown command: $Command"
            Show-Help
            exit 1
        }
    }
} catch {
    Write-Error-Step "❌ Command failed: $_"
    exit 1
}
