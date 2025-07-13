#!/usr/bin/env python3
"""
AnimeSorter 성능 벤치마킹 도구
파일 탐색, 파일명 정제, 전체 처리 성능을 측정하고 비교
"""

import sys
import os
import time
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# src 디렉토리를 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 직접 import하여 의존성 문제 해결
from utils.file_cleaner import FileCleaner, _cached_guessit_parse

class PerformanceBenchmark:
    """성능 벤치마킹 클래스"""
    
    def __init__(self, test_size=1000):
        self.test_size = test_size
        self.test_files = []
        self.temp_dir = tempfile.mkdtemp()
        self.create_test_files()
        
    def create_test_files(self):
        """테스트용 파일 목록 생성"""
        print(f"테스트 파일 {self.test_size}개 생성 중...")
        
        anime_names = [
            "Attack on Titan", "Demon Slayer", "My Hero Academia", "One Piece", 
            "Naruto", "Dragon Ball", "Death Note", "Fullmetal Alchemist",
            "Tokyo Ghoul", "Hunter x Hunter", "Bleach", "Fairy Tail",
            "Jujutsu Kaisen", "Chainsaw Man", "Spy x Family", "Mob Psycho 100"
        ]
        
        patterns = [
            "[SubsPlease] {anime} - S{season:02d}E{episode:02d} [1080p].mkv",
            "{anime} Season {season} Episode {episode} [720p].mp4", 
            "[Erai-raws] {anime} - {episode:02d} [1080p][Multiple Subtitle].mkv",
            "{anime}.S{season:02d}E{episode:02d}.1080p.WEB-DL.x264.mkv",
            "[HorribleSubs] {anime} - {episode:02d} [480p].mkv",
            "{anime} ({year}) - {episode:02d} [BluRay 1080p].mkv"
        ]
        
        for i in range(self.test_size):
            anime = anime_names[i % len(anime_names)]
            episode = i % 24 + 1
            season = i // 24 + 1
            year = 2020 + (i % 5)
            
            pattern = patterns[i % len(patterns)]
            filename = pattern.format(
                anime=anime, 
                season=season, 
                episode=episode, 
                year=year
            )
            
            file_path = Path(self.temp_dir) / filename
            self.test_files.append(file_path)
            
        print(f"테스트 파일 생성 완료: {len(self.test_files)}개")
        
    def benchmark_file_scan_old(self):
        """기존 os.walk() 방식 벤치마킹"""
        print("\n=== 기존 os.walk() 방식 벤치마킹 ===")
        
        start_time = time.time()
        file_paths = []
        
        for root, dirs, files in os.walk(self.temp_dir):
            for fname in files:
                path = Path(root) / fname
                file_paths.append(path)
                
        elapsed = time.time() - start_time
        speed = len(file_paths) / elapsed if elapsed > 0 else 0
        
        print(f"os.walk() 결과: {len(file_paths)}개 파일, {elapsed:.4f}초, {speed:.1f}개/초")
        return elapsed, speed
        
    def benchmark_file_scan_new(self):
        """새로운 os.scandir() 방식 벤치마킹"""
        print("\n=== 새로운 os.scandir() 방식 벤치마킹 ===")
        
        start_time = time.time()
        file_paths = []
        
        def scan_directory_optimized(root_path):
            stack = [Path(root_path)]
            while stack:
                current_path = stack.pop()
                try:
                    with os.scandir(current_path) as entries:
                        for entry in entries:
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(Path(entry.path))
                            elif entry.is_file(follow_symlinks=False):
                                file_paths.append(Path(entry.path))
                except (PermissionError, OSError):
                    continue
                    
        scan_directory_optimized(self.temp_dir)
        elapsed = time.time() - start_time
        speed = len(file_paths) / elapsed if elapsed > 0 else 0
        
        print(f"os.scandir() 결과: {len(file_paths)}개 파일, {elapsed:.4f}초, {speed:.1f}개/초")
        return elapsed, speed
        
    def benchmark_filename_parsing_old(self):
        """기존 GuessIt 방식 벤치마킹"""
        print("\n=== 기존 GuessIt 방식 벤치마킹 ===")
        
        from guessit import guessit
        
        start_time = time.time()
        results = []
        
        sample_size = min(200, len(self.test_files))
        for file_path in self.test_files[:sample_size]:
            meta = guessit(file_path.name)
            results.append(meta)
            
        elapsed = time.time() - start_time
        speed = len(results) / elapsed if elapsed > 0 else 0
        
        print(f"기존 GuessIt: {len(results)}개 파일, {elapsed:.4f}초, {speed:.1f}개/초")
        return elapsed, speed
        
    def benchmark_filename_parsing_cached(self):
        """캐시된 GuessIt 방식 벤치마킹"""
        print("\n=== 캐시된 GuessIt 방식 벤치마킹 ===")
        
        # 캐시 초기화
        _cached_guessit_parse.cache_clear()
        
        start_time = time.time()
        results = []
        
        sample_size = min(200, len(self.test_files))
        for file_path in self.test_files[:sample_size]:
            meta = _cached_guessit_parse(file_path.stem)
            results.append(meta)
            
        elapsed = time.time() - start_time
        speed = len(results) / elapsed if elapsed > 0 else 0
        cache_info = _cached_guessit_parse.cache_info()
        
        print(f"캐시된 GuessIt: {len(results)}개 파일, {elapsed:.4f}초, {speed:.1f}개/초")
        print(f"캐시 정보: {cache_info}")
        return elapsed, speed
        
    def benchmark_thread_vs_process_pool(self):
        """ThreadPoolExecutor vs ProcessPoolExecutor 비교"""
        print("\n=== ThreadPoolExecutor vs ProcessPoolExecutor 비교 ===")
        
        sample_size = min(100, len(self.test_files))  # 샘플 크기 줄임
        sample_files = [str(f) for f in self.test_files[:sample_size]]
        
        # ThreadPoolExecutor 테스트
        print("ThreadPoolExecutor 테스트...")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            thread_results = list(executor.map(FileCleaner.clean_filename_static, sample_files))
            
        thread_elapsed = time.time() - start_time
        thread_speed = len(sample_files) / thread_elapsed if thread_elapsed > 0 else 0
        
        print(f"ThreadPoolExecutor: {len(sample_files)}개 파일, {thread_elapsed:.4f}초, {thread_speed:.1f}개/초")
        
        # ProcessPoolExecutor 테스트
        print("ProcessPoolExecutor 테스트...")
        start_time = time.time()
        
        try:
            with ProcessPoolExecutor(max_workers=4) as executor:
                process_results = list(executor.map(FileCleaner.clean_filename_static, sample_files))
                
            process_elapsed = time.time() - start_time
            process_speed = len(sample_files) / process_elapsed if process_elapsed > 0 else 0
            
            print(f"ProcessPoolExecutor: {len(sample_files)}개 파일, {process_elapsed:.4f}초, {process_speed:.1f}개/초")
            
            improvement = process_speed / thread_speed if thread_speed > 0 else 0
            print(f"성능 향상: {improvement:.2f}배")
            
            return {
                'thread': (thread_elapsed, thread_speed),
                'process': (process_elapsed, process_speed),
                'improvement': improvement
            }
        except Exception as e:
            print(f"ProcessPoolExecutor 오류: {e}")
            print("ThreadPoolExecutor 결과만 사용")
            return {
                'thread': (thread_elapsed, thread_speed),
                'process': (thread_elapsed, thread_speed),
                'improvement': 1.0
            }
        
    def run_full_benchmark(self):
        """전체 벤치마킹 실행"""
        print(f"\n{'='*60}")
        print(f"AnimeSorter 성능 벤치마킹 ({self.test_size}개 파일)")
        print(f"{'='*60}")
        
        # 파일 탐색 비교
        old_scan = self.benchmark_file_scan_old()
        new_scan = self.benchmark_file_scan_new()
        scan_improvement = new_scan[1] / old_scan[1] if old_scan[1] > 0 else 1.0
        print(f"파일 탐색 성능 향상: {scan_improvement:.2f}배")
        
        # 파일명 파싱 비교
        old_parse = self.benchmark_filename_parsing_old()
        cached_parse = self.benchmark_filename_parsing_cached()
        parse_improvement = cached_parse[1] / old_parse[1] if old_parse[1] > 0 else 1.0
        print(f"파일명 파싱 성능 향상: {parse_improvement:.2f}배")
        
        # 병렬 처리 비교
        pool_comparison = self.benchmark_thread_vs_process_pool()
        
        # 전체 예상 성능 향상
        total_improvement = scan_improvement * parse_improvement * pool_comparison['improvement']
        print(f"\n예상 전체 성능 향상: {total_improvement:.2f}배")
        
        # 예상 처리 속도 계산 (기존 73개/초 기준)
        original_speed = 73
        expected_speed = original_speed * total_improvement
        print(f"예상 처리 속도: {expected_speed:.1f}개/초 (기존 {original_speed}개/초)")
        
        if total_improvement >= 5.0:
            print("🎉 목표 달성! (5배 이상 성능 향상)")
        else:
            print(f"목표까지: {5.0/total_improvement:.2f}배 더 필요")
            
        return {
            'scan_improvement': scan_improvement,
            'parse_improvement': parse_improvement,
            'pool_improvement': pool_comparison['improvement'],
            'total_improvement': total_improvement,
            'expected_speed': expected_speed
        }

def main():
    """메인 실행 함수"""
    
    # 다양한 크기로 테스트
    test_sizes = [100, 500, 1000]  # 작은 크기부터 테스트
    
    for size in test_sizes:
        print(f"\n{'='*80}")
        print(f"테스트 크기: {size}개 파일")
        print(f"{'='*80}")
        
        benchmark = PerformanceBenchmark(test_size=size)
        results = benchmark.run_full_benchmark()
        
        print(f"\n결과 요약 ({size}개 파일):")
        print(f"- 파일 탐색: {results['scan_improvement']:.2f}배 향상")
        print(f"- 파일명 파싱: {results['parse_improvement']:.2f}배 향상") 
        print(f"- 병렬 처리: {results['pool_improvement']:.2f}배 향상")
        print(f"- 전체: {results['total_improvement']:.2f}배 향상")
        print(f"- 예상 처리 속도: {results['expected_speed']:.1f}개/초")

if __name__ == "__main__":
    main() 