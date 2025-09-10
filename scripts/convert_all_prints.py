#!/usr/bin/env python3
"""
Comprehensive print to logger conversion script
"""

import re
from pathlib import Path


def add_logging_imports(content: str, file_path: str) -> str:
    """Add logging imports to file content"""
    lines = content.split("\n")

    # Check if logging import already exists
    if "get_application_logger" in content:
        return content

    # Find the right place to insert import
    import_insert_index = 0
    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            import_insert_index = i + 1
        elif line.strip() == "" and import_insert_index > 0:
            break

    # Add the import
    import_line = "from src.core.logging_config import get_application_logger"
    lines.insert(import_insert_index, import_line)

    return "\n".join(lines)


def add_logger_initialization(content: str) -> str:
    """Add logger initialization to class __init__ method"""
    lines = content.split("\n")

    # Check if logger already exists
    if "self.logger" in content:
        return content

    # Find class definition and __init__ method
    class_start = -1
    init_start = -1

    for i, line in enumerate(lines):
        if line.strip().startswith("class "):
            class_start = i
        elif "def __init__" in line and class_start != -1:
            init_start = i
            break

    if init_start == -1:
        # No __init__ method, add at class level
        if class_start != -1:
            for i in range(class_start + 1, len(lines)):
                if lines[i].strip().startswith("def ") or lines[i].strip() == "":
                    lines.insert(i, "        self.logger = get_application_logger()")
                    break
    else:
        # Find end of __init__ method
        init_end = len(lines)
        for i in range(init_start + 1, len(lines)):
            if lines[i].strip().startswith("def ") or lines[i].strip().startswith("class "):
                init_end = i
                break

        # Add logger initialization
        lines.insert(init_end, "        self.logger = get_application_logger()")

    return "\n".join(lines)


def determine_log_level(print_content: str) -> str:
    """Determine appropriate log level from print content"""
    content_lower = print_content.lower()

    if any(keyword in content_lower for keyword in ["error", "실패", "오류", "에러", "❌"]):
        return "error"
    elif any(keyword in content_lower for keyword in ["warning", "경고", "주의", "⚠️"]):
        return "warning"
    elif any(keyword in content_lower for keyword in ["debug", "디버그", "진행률", "🔍", "시작"]):
        return "debug"
    elif any(
        keyword in content_lower for keyword in ["success", "완료", "성공", "✅", "info", "정보"]
    ):
        return "info"
    else:
        return "info"


def determine_category(file_path: str) -> str:
    """Determine appropriate log category from file path"""
    file_path_lower = file_path.lower()

    if "tmdb" in file_path_lower:
        return "tmdb"
    elif "file" in file_path_lower:
        return "file_operation"
    elif "gui" in file_path_lower or "ui" in file_path_lower:
        return "ui"
    elif "manager" in file_path_lower:
        return "system"
    elif "service" in file_path_lower:
        return "system"
    else:
        return "system"


def replace_prints_in_file(file_path: str):
    """Replace print statements with logger calls in a file"""

    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Check if file has print statements
    if "print(" not in content:
        return

    # Add logging imports
    content = add_logging_imports(content, file_path)

    # Add logger initialization
    content = add_logger_initialization(content)

    # Pattern to match print statements
    print_pattern = r"print\s*\(\s*([^)]+)\s*\)"

    def replace_print(match):
        print_content = match.group(1).strip()

        # Determine log level and category
        level = determine_log_level(print_content)
        category = determine_category(file_path)

        # Remove emoji and clean up the message
        cleaned_content = re.sub(r"[🔍✅❌⚠️🎭🚀💾📋🗑️]+\s*", "", print_content)

        return f'self.logger.{level}({cleaned_content}, category="{category}")'

    # Replace all print statements
    new_content = re.sub(print_pattern, replace_print, content)

    # Write back to file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Converted print statements in {file_path}")


def main():
    """Main function to convert all print statements"""
    src_dir = Path("src")

    # Get all Python files with print statements
    python_files = []
    for file_path in src_dir.rglob("*.py"):
        if "test" in str(file_path).lower():
            continue  # Skip test files

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                if "print(" in content:
                    python_files.append(file_path)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    print(f"Found {len(python_files)} files with print statements")

    # Convert each file
    for file_path in python_files:
        try:
            replace_prints_in_file(str(file_path))
        except Exception as e:
            print(f"Error converting {file_path}: {e}")

    print("Conversion complete!")


if __name__ == "__main__":
    main()
