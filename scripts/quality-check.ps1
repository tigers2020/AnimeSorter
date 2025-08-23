# AnimeSorter Code Quality Check Script
# PowerShell Script

param(
    [switch]$Full,
    [switch]$Quick,
    [switch]$Fix
)

Write-Host "🔍 AnimeSorter Code Quality Check Starting..." -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Gray

$ErrorCount = 0
$WarningCount = 0

# Check virtual environment activation
if (-not $env:VIRTUAL_ENV) {
    Write-Host "⚠️  Virtual environment is not activated." -ForegroundColor Yellow
    Write-Host "   Please run venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    $WarningCount++
}

# 1. Ruff linting check
Write-Host "`n1️⃣  Ruff linting check..." -ForegroundColor Blue
try {
    if ($Fix) {
        $ruffResult = & ruff check src --fix 2>&1
    } else {
        $ruffResult = & ruff check src 2>&1
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Ruff check failed" -ForegroundColor Red
        $ErrorCount++
    } else {
        Write-Host "✅ Ruff check passed" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Ruff not found - please install: pip install ruff" -ForegroundColor Red
    $ErrorCount++
}

# 2. MyPy type checking
Write-Host "`n2️⃣  MyPy type checking..." -ForegroundColor Blue
try {
    $mypyResult = & mypy src --ignore-missing-imports 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ MyPy check failed" -ForegroundColor Red
        $ErrorCount++
    } else {
        Write-Host "✅ MyPy check passed" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ MyPy not found - please install: pip install mypy" -ForegroundColor Red
    $ErrorCount++
}

# 3. Complexity check
Write-Host "`n3️⃣  Complexity check..." -ForegroundColor Blue
try {
    $radonResult = & radon cc src -a --total-average 2>&1
    $xenonResult = & xenon src --max-absolute B --max-modules A --max-average A 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Complexity check failed" -ForegroundColor Red
        $ErrorCount++
    } else {
        Write-Host "✅ Complexity check passed" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Radon/Xenon not found - please install: pip install radon xenon" -ForegroundColor Red
    $ErrorCount++
}

# 4. Security audit
Write-Host "`n4️⃣  Security audit..." -ForegroundColor Blue
try {
    $pipAuditResult = & pip-audit --desc 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Security audit failed" -ForegroundColor Red
        $ErrorCount++
    } else {
        Write-Host "✅ Security audit passed" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ pip-audit not found - please install: pip install pip-audit" -ForegroundColor Red
    $ErrorCount++
}

# 5. Dependency analysis
Write-Host "`n5️⃣  Dependency analysis..." -ForegroundColor Blue
try {
    $deptryResult = & deptry src 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Dependency analysis failed" -ForegroundColor Red
        $ErrorCount++
    } else {
        Write-Host "✅ Dependency analysis passed" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Deptry not found - please install: pip install deptry" -ForegroundColor Red
    $ErrorCount++
}

# 6. Unused code check
Write-Host "`n6️⃣  Unused code check..." -ForegroundColor Blue
try {
    $vultureResult = & vulture src --min-confidence 80 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Unused code found" -ForegroundColor Red
        $ErrorCount++
    } else {
        Write-Host "✅ Unused code check passed" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Vulture not found - please install: pip install vulture" -ForegroundColor Red
    $ErrorCount++
}

# 7. Test execution (if not Quick mode)
if (-not $Quick) {
    Write-Host "`n7️⃣  Test execution..." -ForegroundColor Blue

    # Set Qt environment
    $env:QT_QPA_PLATFORM = "offscreen"

    # Smoke tests
    Write-Host "   Smoke tests..." -ForegroundColor Cyan
    try {
        $smokeTestResult = & python -m pytest tests/smoke/ -v 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Smoke tests failed" -ForegroundColor Red
            $ErrorCount++
        } else {
            Write-Host "✅ Smoke tests passed" -ForegroundColor Green
        }
    } catch {
        Write-Host "❌ Pytest not found - please install: pip install pytest pytest-qt" -ForegroundColor Red
        $ErrorCount++
    }

    # Base component tests
    Write-Host "   Base component tests..." -ForegroundColor Cyan
    try {
        $baseTestResult = & python -m pytest tests/test_base_components.py -v 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Base component tests failed" -ForegroundColor Red
            $ErrorCount++
        } else {
            Write-Host "✅ Base component tests passed" -ForegroundColor Green
        }
    } catch {
        Write-Host "❌ Test execution failed" -ForegroundColor Red
        $ErrorCount++
    }
}

# 8. Coverage check (if Full mode)
if ($Full) {
    Write-Host "`n8️⃣  Coverage check..." -ForegroundColor Blue
    try {
        $coverageResult = & python -m pytest tests/ --cov=src --cov-report=term-missing --cov-report=html 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Coverage check failed" -ForegroundColor Red
            $ErrorCount++
        } else {
            Write-Host "✅ Coverage check completed (see htmlcov/index.html)" -ForegroundColor Green
        }
    } catch {
        Write-Host "❌ Coverage tools not found - please install: pip install pytest-cov" -ForegroundColor Red
        $ErrorCount++
    }
}

# Summary
Write-Host "`n" + "=" * 50 -ForegroundColor Gray
Write-Host "📋 Quality Check Summary" -ForegroundColor Cyan

if ($ErrorCount -eq 0 -and $WarningCount -eq 0) {
    Write-Host "🎉 All quality checks passed!" -ForegroundColor Green
    Write-Host "   Code is ready for release." -ForegroundColor Green
    exit 0
} elseif ($ErrorCount -eq 0) {
    Write-Host "⚠️  $WarningCount warnings but all required checks passed" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "❌ $ErrorCount errors, $WarningCount warnings" -ForegroundColor Red
    Write-Host "   Please fix issues and run again." -ForegroundColor Red
    exit 1
}
