#!/usr/bin/env python3
"""
AnimeSorter 테스트 실행 스크립트

모든 단위 테스트를 실행하고 결과를 요약합니다.
"""

import sys
import unittest
from pathlib import Path


def run_all_tests():
    """모든 테스트 실행"""
    import warnings

    # 로깅 시스템 테스트를 위해 로깅 비활성화 제거
    # logging.disable(logging.CRITICAL)
    warnings.filterwarnings("ignore")
    print("🧪 AnimeSorter 테스트 실행 시작\n")

    # tests 디렉토리로 경로 설정
    tests_dir = Path(__file__).parent / "tests"
    sys.path.insert(0, str(tests_dir))

    # 테스트 로더 생성
    loader = unittest.TestLoader()

    # tests 디렉토리에서 모든 테스트 발견
    suite = loader.discover(str(tests_dir), pattern="test_*.py")

    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 결과 요약
    print("\n" + "=" * 50)
    print("📊 테스트 결과 요약")
    print("=" * 50)
    print(f"실행된 테스트: {result.testsRun}")
    print(f"성공: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"실패: {len(result.failures)}")
    print(f"오류: {len(result.errors)}")

    if result.failures:
        print("\n❌ 실패한 테스트:")
        for test, traceback in result.failures:
            print(f"  - {test}")

    if result.errors:
        print("\n⚠️ 오류가 발생한 테스트:")
        for test, traceback in result.errors:
            print(f"  - {test}")

    if result.wasSuccessful():
        print("\n✅ 모든 테스트 통과!")
        return 0
    else:
        print("\n❌ 일부 테스트 실패")
        return 1


def run_specific_test(test_name):
    """특정 테스트 실행"""
    print(f"🧪 {test_name} 테스트 실행\n")

    # tests 디렉토리로 경로 설정
    tests_dir = Path(__file__).parent / "tests"
    sys.path.insert(0, str(tests_dir))

    # 특정 테스트 파일 실행
    test_file = tests_dir / f"{test_name}.py"

    if not test_file.exists():
        print(f"❌ 테스트 파일을 찾을 수 없습니다: {test_file}")
        return 1

    try:
        # 테스트 파일을 직접 실행
        import subprocess

        result = subprocess.run([sys.executable, str(test_file)], capture_output=True, text=True)

        print(result.stdout)
        if result.stderr:
            print(result.stderr)

        return result.returncode

    except Exception as e:
        print(f"❌ 테스트 실행 중 오류 발생: {e}")
        return 1


def main():
    """메인 함수"""
    if len(sys.argv) > 1:
        # 특정 테스트 실행
        test_name = sys.argv[1]
        if test_name.endswith(".py"):
            test_name = test_name[:-3]  # .py 확장자 제거
        return run_specific_test(test_name)
    else:
        # 모든 테스트 실행
        return run_all_tests()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
