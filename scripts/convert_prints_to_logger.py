#!/usr/bin/env python3
"""
Print to Logger Conversion Script

This script converts print() statements to appropriate logger calls
using the project's structured logging system.
"""

import ast
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.logging_config import LogCategory, LoggingConfig, LogLevel


class PrintToLoggerConverter:
    """Converts print statements to logger calls"""

    def __init__(self):
        self.conversion_stats = {
            "files_processed": 0,
            "print_statements_converted": 0,
            "errors": 0,
            "files_with_errors": [],
        }

        # Import patterns for different module types
        self.import_patterns = {
            "core": "from src.core.logging_config import get_application_logger",
            "gui": "from src.core.logging_config import get_application_logger",
            "app": "from src.core.logging_config import get_application_logger",
        }

        # Category mapping based on file path
        self.category_mapping = {
            "tmdb": LogCategory.TMDB,
            "file_operation": LogCategory.FILE_OPERATION,
            "file_parser": LogCategory.FILE_OPERATION,
            "gui": LogCategory.UI,
            "main_window": LogCategory.UI,
            "managers": LogCategory.SYSTEM,
            "services": LogCategory.SYSTEM,
            "network": LogCategory.NETWORK,
            "database": LogCategory.DATABASE,
            "security": LogCategory.SECURITY,
            "performance": LogCategory.PERFORMANCE,
            "background": LogCategory.BACKGROUND,
        }

    def determine_log_level(self, print_content: str) -> int:
        """Determine appropriate log level from print content"""
        return LoggingConfig.get_log_level_from_print_content(print_content)

    def determine_category(self, file_path: str) -> str:
        """Determine appropriate log category from file path"""
        file_path_lower = file_path.lower()

        for keyword, category in self.category_mapping.items():
            if keyword in file_path_lower:
                return category

        return LogCategory.SYSTEM

    def extract_print_content(self, print_node: ast.Call) -> str:
        """Extract the content string from a print statement"""
        if not print_node.args:
            return ""

        # Handle f-strings and regular strings
        if isinstance(print_node.args[0], ast.Constant):
            return print_node.args[0].value
        elif isinstance(print_node.args[0], ast.JoinedStr):
            # This is an f-string, we'll need to reconstruct it
            return self._reconstruct_f_string(print_node.args[0])
        else:
            # For complex expressions, return a placeholder
            return "<complex_expression>"

    def _reconstruct_f_string(self, joined_str_node: ast.JoinedStr) -> str:
        """Reconstruct f-string from AST node"""
        parts = []
        for value in joined_str_node.values:
            if isinstance(value, ast.Constant):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                # This is a complex case, return placeholder for now
                parts.append(f"{{{ast.unparse(value.value)}}}")
        return "".join(parts)

    def convert_print_to_logger(self, print_node: ast.Call, file_path: str) -> str:
        """Convert a print statement to logger call"""
        content = self.extract_print_content(print_node)
        log_level = self.determine_log_level(content)
        category = self.determine_category(file_path)

        # Map log level to method name
        level_methods = {
            LogLevel.TRACE: "trace",
            LogLevel.DEBUG: "debug",
            LogLevel.INFO: "info",
            LogLevel.WARNING: "warning",
            LogLevel.ERROR: "error",
            LogLevel.CRITICAL: "critical",
        }

        method_name = level_methods.get(log_level, "info")

        # Handle different print argument patterns
        if len(print_node.args) == 1:
            # Simple case: print("message")
            if isinstance(print_node.args[0], ast.Constant):
                return f'self.logger.{method_name}("{content}", category="{category}")'
            else:
                # Complex expression - keep original but wrap in logger
                original_code = ast.unparse(print_node.args[0])
                return f'self.logger.{method_name}({original_code}, category="{category}")'
        else:
            # Multiple arguments: print("msg", var1, var2)
            args_str = ", ".join(ast.unparse(arg) for arg in print_node.args)
            return f'self.logger.{method_name}({args_str}, category="{category}")'

    def needs_logger_import(self, file_content: str) -> bool:
        """Check if file needs logger import"""
        return "get_application_logger" not in file_content and "logger" not in file_content

    def needs_logger_attribute(self, file_content: str) -> bool:
        """Check if file needs self.logger attribute"""
        return "self.logger" not in file_content

    def add_logger_import(self, file_content: str, file_path: str) -> str:
        """Add logger import to file"""
        lines = file_content.split("\n")

        # Find the right place to insert import
        import_insert_index = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                import_insert_index = i + 1
            elif line.strip() == "" and import_insert_index > 0:
                break

        # Determine the appropriate import
        if "core" in file_path:
            import_line = "from src.core.logging_config import get_application_logger"
        else:
            import_line = "from src.core.logging_config import get_application_logger"

        lines.insert(import_insert_index, import_line)
        return "\n".join(lines)

    def add_logger_attribute(self, file_content: str) -> str:
        """Add self.logger attribute to __init__ method"""
        lines = file_content.split("\n")

        # Find __init__ method
        init_start = -1
        for i, line in enumerate(lines):
            if "def __init__" in line:
                init_start = i
                break

        if init_start == -1:
            # No __init__ method, add at class level
            class_start = -1
            for i, line in enumerate(lines):
                if line.strip().startswith("class "):
                    class_start = i
                    break

            if class_start != -1:
                # Find first method or end of class
                for i in range(class_start + 1, len(lines)):
                    if lines[i].strip().startswith("def ") or lines[i].strip() == "":
                        lines.insert(i, "        self.logger = get_application_logger()")
                        break
        else:
            # Find end of __init__ method (look for next def or class)
            init_end = len(lines)
            for i in range(init_start + 1, len(lines)):
                if lines[i].strip().startswith("def ") or lines[i].strip().startswith("class "):
                    init_end = i
                    break

            # Add logger initialization
            lines.insert(init_end, "        self.logger = get_application_logger()")

        return "\n".join(lines)

    def convert_file(self, file_path: Path) -> bool:
        """Convert print statements in a single file"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Parse the file
            tree = ast.parse(content)

            # Find all print statements
            print_statements = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name) and node.value.func.id == "print":
                        print_statements.append(node)

            if not print_statements:
                return True

            # Convert print statements
            modified = False
            for print_stmt in reversed(
                print_statements
            ):  # Process in reverse to maintain line numbers
                try:
                    logger_call = self.convert_print_to_logger(print_stmt.value, str(file_path))

                    # Replace the print statement
                    lines = content.split("\n")
                    line_num = print_stmt.lineno - 1

                    # Find the actual line and replace
                    original_line = lines[line_num]
                    indent = len(original_line) - len(original_line.lstrip())
                    new_line = " " * indent + logger_call
                    lines[line_num] = new_line

                    content = "\n".join(lines)
                    modified = True
                    self.conversion_stats["print_statements_converted"] += 1

                except Exception as e:
                    print(f"Error converting print statement in {file_path}: {e}")
                    continue

            # Add logger import if needed
            if modified and self.needs_logger_import(content):
                content = self.add_logger_import(content, str(file_path))

            # Add logger attribute if needed
            if modified and self.needs_logger_attribute(content):
                content = self.add_logger_attribute(content)

            # Write back the modified content
            if modified:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            self.conversion_stats["files_processed"] += 1
            return True

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            self.conversion_stats["errors"] += 1
            self.conversion_stats["files_with_errors"].append(str(file_path))
            return False

    def convert_directory(self, directory: Path) -> None:
        """Convert all Python files in directory"""
        python_files = list(directory.rglob("*.py"))

        for file_path in python_files:
            if "test" in str(file_path).lower():
                continue  # Skip test files for now

            self.convert_file(file_path)

    def print_stats(self) -> None:
        """Print conversion statistics"""
        print("\n" + "=" * 50)
        print("PRINT TO LOGGER CONVERSION STATISTICS")
        print("=" * 50)
        print(f"Files processed: {self.conversion_stats['files_processed']}")
        print(f"Print statements converted: {self.conversion_stats['print_statements_converted']}")
        print(f"Errors: {self.conversion_stats['errors']}")

        if self.conversion_stats["files_with_errors"]:
            print("\nFiles with errors:")
            for file_path in self.conversion_stats["files_with_errors"]:
                print(f"  - {file_path}")


def main():
    """Main function"""
    converter = PrintToLoggerConverter()

    # Convert src directory
    src_dir = Path(__file__).parent.parent / "src"
    converter.convert_directory(src_dir)

    # Print statistics
    converter.print_stats()


if __name__ == "__main__":
    main()
