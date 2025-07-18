#!/usr/bin/env python3

import asyncio
import os
import sys
from pathlib import Path

async def main():
    print("AnimeSorter 테스트", flush=True)
    
    # 현재 디렉토리 확인
    current_dir = Path.cwd()
    print(f"현재 디렉토리: {current_dir}", flush=True)
    
    # 테스트 디렉토리 확인
    test_source = current_dir / "test_source"
    test_target = current_dir / "test_target"
    
    print(f"소스 디렉토리 존재: {test_source.exists()}", flush=True)
    print(f"대상 디렉토리 존재: {test_target.exists()}", flush=True)
    
    # 소스 디렉토리 파일 목록
    print("소스 디렉토리 파일:", flush=True)
    for file in test_source.iterdir():
        print(f" - {file.name}", flush=True)
    
    # 파일 정제 테스트 실행
    print("\n파일 정제 테스트를 실행합니다...", flush=True)
    try:
        # 직접 FileCleaner 테스트
        import sys
        sys.path.insert(0, str(current_dir))
        from src.utils.file_cleaner import FileCleaner
        import json
        import gzip
        import time
        
        # 스캔 결과에서 파일 이름 추출하여 테스트
        scan_results_dir = current_dir / "scan_results"
        if scan_results_dir.exists():
            scan_files = list(scan_results_dir.glob("scan_result_*.json*"))
            if scan_files:
                # 가장 최근 파일 선택
                json_files = [f for f in scan_files if f.name.endswith('.json') and not f.name.endswith('.gz')]
                if json_files:
                    latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
                else:
                    latest_file = max(scan_files, key=lambda x: x.stat().st_mtime)
                
                print(f"사용할 스캔 결과 파일: {latest_file.name}", flush=True)
                
                # 스캔 결과 로드
                try:
                    if latest_file.name.endswith('.gz'):
                        with gzip.open(latest_file, 'rt', encoding='utf-8') as f:
                            scan_data = json.load(f)
                    else:
                        with open(latest_file, 'r', encoding='utf-8') as f:
                            scan_data = json.load(f)
                    
                    # 파일 이름 추출
                    file_names = []
                    if 'groups' in scan_data:
                        for group in scan_data['groups']:
                            if 'files' in group:
                                for file_info in group['files']:
                                    if 'file_name' in file_info:
                                        file_names.append(file_info['file_name'])
                    
                    if file_names:
                        print(f"추출된 파일 수: {len(file_names)}", flush=True)
                        
                        # FileCleaner 테스트
                        file_cleaner = FileCleaner()
                        test_count = min(10, len(file_names))  # 처음 10개만 테스트
                        
                        print(f"처음 {test_count}개 파일로 테스트를 시작합니다...", flush=True)
                        
                        success_count = 0
                        start_time = time.time()
                        
                        for i, file_name in enumerate(file_names[:test_count], 1):
                            try:
                                parse_start = time.time()
                                result = file_cleaner.parse(file_name)
                                parse_time = time.time() - parse_start
                                
                                success_count += 1
                                
                                print(f"파일 {i}: {file_name}")
                                print(f"  → 제목: {result.title}")
                                print(f"  → 시즌: {result.season}")
                                print(f"  → 에피소드: {result.episode}")
                                print(f"  → 연도: {result.year}")
                                print(f"  → 영화: {result.is_movie}")
                                print(f"  → 파싱 시간: {parse_time:.4f}초")
                                print("")
                                
                            except Exception as e:
                                print(f"파일 파싱 실패 ({i}): {file_name} - {e}", flush=True)
                        
                        total_time = time.time() - start_time
                        success_rate = (success_count / test_count) * 100
                        
                        print("="*60)
                        print("파일 정제 테스트 결과")
                        print("="*60)
                        print(f"총 테스트 파일 수: {test_count}")
                        print(f"성공한 파싱: {success_count}")
                        print(f"실패한 파싱: {test_count - success_count}")
                        print(f"성공률: {success_rate:.2f}%")
                        print(f"총 소요 시간: {total_time:.2f}초")
                        print(f"파일당 평균 시간: {total_time/test_count:.4f}초")
                        print("="*60)
                        
                    else:
                        print("스캔 결과에서 파일 이름을 추출할 수 없습니다.", flush=True)
                        
                except Exception as e:
                    print(f"스캔 결과 로드 실패: {e}", flush=True)
            else:
                print("스캔 결과 파일을 찾을 수 없습니다.", flush=True)
        else:
            print("스캔 결과 디렉토리를 찾을 수 없습니다.", flush=True)
            
    except ImportError as e:
        print(f"FileCleaner 모듈을 가져올 수 없습니다: {e}", flush=True)
    except Exception as e:
        print(f"파일 정제 테스트 실행 중 오류 발생: {e}", flush=True)

if __name__ == "__main__":
    asyncio.run(main()) 