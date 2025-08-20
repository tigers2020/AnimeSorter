@echo off
REM AnimeSorter Development Scripts for Windows
REM Usage: dev.bat [command]

if "%1"=="help" goto help
if "%1"=="setup" goto setup
if "%1"=="install" goto install
if "%1"=="test" goto test
if "%1"=="test-cov" goto test-cov
if "%1"=="lint" goto lint
if "%1"=="lint-fix" goto lint-fix
if "%1"=="format" goto format
if "%1"=="format-check" goto format-check
if "%1"=="type-check" goto type-check
if "%1"=="security" goto security
if "%1"=="build" goto build
if "%1"=="build-exe" goto build-exe
if "%1"=="dev" goto dev
if "%1"=="debug" goto debug
if "%1"=="clean" goto clean
if "%1"=="check" goto check
if "%1"=="test-all" goto test-all
if "%1"=="ci" goto ci
if "%1"=="" goto help

echo Unknown command: %1
goto help

:help
echo AnimeSorter Development Commands (Windows):
echo.
echo   help          Show this help
echo   setup         Set up development environment
echo   install       Install package and dependencies
echo   test          Run tests
echo   test-cov      Run tests with coverage
echo   lint          Run ruff linter
echo   lint-fix      Run ruff linter with fixes
echo   format        Format code with black
echo   format-check  Check code formatting
echo   type-check    Run mypy type checker
echo   security      Run security checks
echo   build         Build package
echo   build-exe     Build executable with PyInstaller
echo   dev           Run development server
echo   debug         Run with debug logging
echo   clean         Clean build artifacts
echo   check         Run all code quality checks
echo   test-all      Run all tests and security checks
echo   ci            Run CI pipeline locally
echo.
echo Examples:
echo   dev.bat setup
echo   dev.bat test
echo   dev.bat lint-fix
goto end

:setup
echo 🔧 Setting up development environment...
python -m pip install --upgrade pip
pip install -e ".[dev]"
pre-commit install
echo ✅ Development environment ready!
goto end

:install
echo 📦 Installing package...
pip install -e ".[dev]"
goto end

:test
echo 🧪 Running tests...
pytest tests/ -v
goto end

:test-cov
echo 🧪 Running tests with coverage...
pytest tests/ --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=70 -v
goto end

:lint
echo 🔍 Running ruff linter...
ruff check src/ tests/
goto end

:lint-fix
echo 🔧 Running ruff linter with fixes...
ruff check src/ tests/ --fix
goto end

:format
echo 🎨 Formatting code with black...
black src/ tests/
goto end

:format-check
echo 🎨 Checking code formatting...
black --check src/ tests/
goto end

:type-check
echo 🔍 Running mypy type checker...
mypy src/ --config-file=pyproject.toml
goto end

:security
echo 🔒 Running security checks...
bandit -r src/ -f json -o bandit-report.json
safety check --json --output safety-report.json
echo 📄 Security reports generated: bandit-report.json, safety-report.json
goto end

:build
echo 📦 Building package...
python -m build
goto end

:build-exe
echo 🔨 Building executable...
pyinstaller --onefile --windowed --name "AnimeSorter" --add-data "resources/*;resources" --hidden-import PyQt5.QtWidgets --hidden-import PyQt5.QtCore --hidden-import PyQt5.QtGui --hidden-import tmdbsimple --hidden-import anitopy --hidden-import guessit src/main.py
goto end

:dev
echo 🚀 Starting development mode...
python -m src.main
goto end

:debug
echo 🐛 Starting debug mode...
set ANIMESORTER_LOG_LEVEL=DEBUG
python -m src.main
goto end

:clean
echo 🧹 Cleaning build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.egg-info rmdir /s /q *.egg-info
if exist htmlcov rmdir /s /q htmlcov
if exist .coverage del .coverage
if exist .pytest_cache rmdir /s /q .pytest_cache
if exist .mypy_cache rmdir /s /q .mypy_cache
if exist .ruff_cache rmdir /s /q .ruff_cache
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s *.pyc 2>nul
del /s *.pyo 2>nul
del /s *.pyd 2>nul
del coverage.xml 2>nul
goto end

:check
echo 🔍 Running all code quality checks...
call :lint
if errorlevel 1 goto error
call :format-check
if errorlevel 1 goto error
call :type-check
if errorlevel 1 goto error
echo ✅ All code quality checks passed!
goto end

:test-all
echo 🧪 Running all tests and security checks...
call :test-cov
if errorlevel 1 goto error
call :security
echo ✅ All tests and security checks completed!
goto end

:ci
echo 🚀 Running CI pipeline locally...
call :check
if errorlevel 1 goto error
call :test-all
if errorlevel 1 goto error
echo ✅ CI pipeline completed successfully!
goto end

:error
echo ❌ Command failed with error code %errorlevel%
exit /b %errorlevel%

:end
exit /b 0
