#!/usr/bin/env python3
"""
Replace print statements in a specific file with logger calls
"""

import re
import sys


def replace_prints_in_file(file_path: str):
    """Replace print statements with logger calls in a file"""

    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Pattern to match print statements
    print_pattern = r"print\s*\(\s*([^)]+)\s*\)"

    def replace_print(match):
        print_content = match.group(1).strip()

        # Determine log level based on content
        if any(
            keyword in print_content.lower() for keyword in ["error", "실패", "오류", "에러", "❌"]
        ):
            level = "error"
        elif any(keyword in print_content.lower() for keyword in ["warning", "경고", "주의", "⚠️"]):
            level = "warning"
        elif any(
            keyword in print_content.lower() for keyword in ["debug", "디버그", "진행률", "🔍"]
        ):
            level = "debug"
        elif any(keyword in print_content.lower() for keyword in ["success", "완료", "성공", "✅"]):
            level = "info"
        else:
            level = "info"

        # Remove emoji and clean up the message
        cleaned_content = re.sub(r"[🔍✅❌⚠️🎭🚀💾📋🗑️]+\s*", "", print_content)

        return f'self.logger.{level}({cleaned_content}, category="file_operation")'

    # Replace all print statements
    new_content = re.sub(print_pattern, replace_print, content)

    # Write back to file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Replaced print statements in {file_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python replace_prints_in_file.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    replace_prints_in_file(file_path)
