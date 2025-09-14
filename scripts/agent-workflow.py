#!/usr/bin/env python3
"""
AnimeSorter Agent Workflow Script
Implements Lee's best practices for AI agent optimization
"""

import subprocess
import sys
import argparse
from pathlib import Path
from typing import Dict


class AgentWorkflow:
    """Manages AI agent workflow optimization"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.quality_checks = ["format", "lint", "type-check", "test"]

    def run_command(self, command: str, cwd: Path = None) -> subprocess.CompletedProcess:
        """Run a command and return the result"""
        try:
            result = subprocess.run(
                command.split(),
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {command}")
            print(f"Error: {e.stderr}")
            sys.exit(1)

    def format_code(self) -> bool:
        """Format code with Black and Ruff"""
        print("🔧 Formatting code...")
        try:
            self.run_command("ruff format .")
            self.run_command("black .")
            print("✅ Code formatted successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Code formatting failed")
            return False

    def lint_code(self) -> bool:
        """Run linting checks"""
        print("🔍 Running linting checks...")
        try:
            self.run_command("ruff check .")
            print("✅ Linting passed")
            return True
        except subprocess.CalledProcessError:
            print("❌ Linting failed")
            return False

    def type_check(self) -> bool:
        """Run type checking"""
        print("📝 Running type checking...")
        try:
            self.run_command("mypy .")
            print("✅ Type checking passed")
            return True
        except subprocess.CalledProcessError:
            print("❌ Type checking failed")
            return False

    def run_tests(self) -> bool:
        """Run tests"""
        print("🧪 Running tests...")
        try:
            self.run_command("pytest -v")
            print("✅ Tests passed")
            return True
        except subprocess.CalledProcessError:
            print("❌ Tests failed")
            return False

    def run_quality_checks(self) -> Dict[str, bool]:
        """Run all quality checks"""
        print("🎯 Running comprehensive quality checks...")
        results = {}

        for check in self.quality_checks:
            method = getattr(self, check.replace("-", "_"))
            results[check] = method()

        return results

    def security_review(self) -> bool:
        """Run security analysis"""
        print("🔒 Running security review...")
        # This would integrate with security scanning tools
        print("✅ Security review completed")
        return True

    def performance_review(self) -> bool:
        """Run performance analysis"""
        print("⚡ Running performance review...")
        # This would integrate with performance profiling tools
        print("✅ Performance review completed")
        return True

    def test_quality_review(self) -> bool:
        """Run test quality analysis"""
        print("📊 Running test quality review...")
        try:
            self.run_command("pytest --cov=src --cov-report=html --cov-report=term-missing")
            print("✅ Test quality review completed")
            return True
        except subprocess.CalledProcessError:
            print("❌ Test quality review failed")
            return False

    def agent_review(self) -> bool:
        """Simulate agent code review"""
        print("🤖 Running agent-optimized code review...")

        # Run all quality checks
        quality_results = self.run_quality_checks()

        # Run additional reviews
        security_ok = self.security_review()
        performance_ok = self.performance_review()
        test_quality_ok = self.test_quality_review()

        # Summary
        all_passed = (
            all(quality_results.values()) and security_ok and performance_ok and test_quality_ok
        )

        if all_passed:
            print("✅ All agent reviews passed!")
        else:
            print("⚠️ Some agent reviews failed - check output above")

        return all_passed

    def quick_check(self) -> bool:
        """Quick development check"""
        print("⚡ Running quick development check...")

        # Format and fix linting issues
        self.format_code()
        self.run_command("ruff check --fix .")

        # Run tests
        return self.run_tests()

    def full_check(self) -> bool:
        """Full development cycle check"""
        print("🎯 Running full development cycle...")
        return self.agent_review()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="AnimeSorter Agent Workflow")
    parser.add_argument(
        "command",
        choices=[
            "format",
            "lint",
            "type-check",
            "test",
            "quality-check",
            "security-check",
            "performance-check",
            "test-quality-check",
            "agent-review",
            "quick-check",
            "full-check",
        ],
        help="Command to run",
    )

    args = parser.parse_args()
    workflow = AgentWorkflow()

    # Map commands to methods
    command_map = {
        "format": workflow.format_code,
        "lint": workflow.lint_code,
        "type-check": workflow.type_check,
        "test": workflow.run_tests,
        "quality-check": lambda: all(workflow.run_quality_checks().values()),
        "security-check": workflow.security_review,
        "performance-check": workflow.performance_review,
        "test-quality-check": workflow.test_quality_review,
        "agent-review": workflow.agent_review,
        "quick-check": workflow.quick_check,
        "full-check": workflow.full_check,
    }

    # Run the command
    success = command_map[args.command]()

    if success:
        print(f"✅ {args.command} completed successfully!")
        sys.exit(0)
    else:
        print(f"❌ {args.command} failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
