"""
SQLite 캐시 데이터베이스

메타데이터 검색 결과를 캐시하여 중복 API 호출을 방지하고
애플리케이션 응답성을 향상시킵니다.
"""

import asyncio
import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


class CacheDB:
    """
    SQLite 기반 캐시 데이터베이스
    
    메타데이터 검색 결과를 로컬에 저장하여 중복 요청을 방지합니다.
    """
    
    def __init__(self, db_path: Union[str, Path] = "cache.db"):
        """
        CacheDB 초기화
        
        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = Path(db_path)
        self.conn = None
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self) -> None:
        """데이터베이스 연결 및 테이블 생성"""
        try:
            # 데이터베이스 디렉토리 생성
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # SQLite 연결 (비동기 처리를 위해 스레드 풀 사용)
            loop = asyncio.get_running_loop()
            self.conn = await loop.run_in_executor(
                None, sqlite3.connect, str(self.db_path)
            )
            
            # 테이블 생성
            await self._create_tables()
            
            self.logger.info(f"CacheDB initialized: {self.db_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize CacheDB: {e}")
            raise
            
    async def close(self) -> None:
        """데이터베이스 연결 종료"""
        if self.conn:
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self.conn.close)
                self.conn = None
                self.logger.info("CacheDB connection closed")
            except Exception as e:
                self.logger.error(f"Error closing CacheDB: {e}")
                
    async def get_cache(self, title_key: str, max_age_days: int = 30) -> Optional[Dict[str, Any]]:
        """
        캐시에서 메타데이터 조회
        
        Args:
            title_key: 검색 키
            max_age_days: 최대 캐시 유효 기간 (일)
            
        Returns:
            dict or None: 캐시된 메타데이터 또는 None (캐시 미스)
        """
        try:
            now = int(time.time())
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            loop = asyncio.get_running_loop()
            
            def _get_cache():
                cursor = self.conn.execute(
                    "SELECT metadata FROM media_cache WHERE title_key = ? AND (? - updated_at) < ?",
                    (title_key, now, max_age_seconds)
                )
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return None
                
            result = await loop.run_in_executor(None, _get_cache)
            
            if result:
                self.logger.debug(f"Cache hit for: {title_key}")
            else:
                self.logger.debug(f"Cache miss for: {title_key}")
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting cache for {title_key}: {e}")
            return None
            
    async def set_cache(
        self, 
        title_key: str, 
        metadata: Dict[str, Any], 
        year: Optional[int] = None
    ) -> None:
        """
        메타데이터를 캐시에 저장
        
        Args:
            title_key: 검색 키
            metadata: 저장할 메타데이터
            year: 연도 정보 (옵션)
        """
        try:
            now = int(time.time())
            
            loop = asyncio.get_running_loop()
            
            def _set_cache():
                # UPSERT (INSERT OR REPLACE)
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO media_cache 
                    (title_key, year, metadata, updated_at) 
                    VALUES (?, ?, ?, ?)
                    """,
                    (title_key, year, json.dumps(metadata), now)
                )
                self.conn.commit()
                
            await loop.run_in_executor(None, _set_cache)
            
            self.logger.debug(f"Cached metadata for: {title_key}")
            
        except Exception as e:
            self.logger.error(f"Error setting cache for {title_key}: {e}")
            
    async def delete_cache(self, title_key: str) -> None:
        """
        캐시에서 항목 삭제
        
        Args:
            title_key: 삭제할 검색 키
        """
        try:
            loop = asyncio.get_running_loop()
            
            def _delete_cache():
                self.conn.execute(
                    "DELETE FROM media_cache WHERE title_key = ?",
                    (title_key,)
                )
                self.conn.commit()
                
            await loop.run_in_executor(None, _delete_cache)
            
            self.logger.debug(f"Deleted cache for: {title_key}")
            
        except Exception as e:
            self.logger.error(f"Error deleting cache for {title_key}: {e}")
            
    async def cleanup_cache(
        self, 
        max_age_days: int = 90, 
        max_items: int = 10000
    ) -> None:
        """
        오래된 캐시 항목 정리
        
        Args:
            max_age_days: 최대 보관 기간 (일)
            max_items: 최대 항목 수
        """
        try:
            now = int(time.time())
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            loop = asyncio.get_running_loop()
            
            def _cleanup_cache():
                # 오래된 항목 삭제
                self.conn.execute(
                    "DELETE FROM media_cache WHERE (? - updated_at) > ?",
                    (now, max_age_seconds)
                )
                
                # 항목 수 제한
                cursor = self.conn.execute("SELECT COUNT(*) FROM media_cache")
                count = cursor.fetchone()[0]
                
                if count > max_items:
                    # 가장 오래된 항목부터 삭제
                    delete_count = count - max_items
                    self.conn.execute(
                        """
                        DELETE FROM media_cache 
                        WHERE title_key IN (
                            SELECT title_key FROM media_cache 
                            ORDER BY updated_at ASC 
                            LIMIT ?
                        )
                        """,
                        (delete_count,)
                    )
                    
                self.conn.commit()
                
            await loop.run_in_executor(None, _cleanup_cache)
            
            self.logger.info(f"Cache cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cache cleanup: {e}")
            
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 조회
        
        Returns:
            dict: 캐시 통계 정보
        """
        try:
            loop = asyncio.get_running_loop()
            
            def _get_stats():
                cursor = self.conn.execute("SELECT COUNT(*) FROM media_cache")
                total_count = cursor.fetchone()[0]
                
                cursor = self.conn.execute(
                    "SELECT MIN(updated_at), MAX(updated_at) FROM media_cache"
                )
                row = cursor.fetchone()
                oldest_time = row[0] if row[0] else None
                newest_time = row[1] if row[1] else None
                
                return {
                    "total_items": total_count,
                    "oldest_item": oldest_time,
                    "newest_item": newest_time
                }
                
            return await loop.run_in_executor(None, _get_stats)
            
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
            return {}
            
    async def _create_tables(self) -> None:
        """데이터베이스 테이블 생성"""
        try:
            loop = asyncio.get_running_loop()
            
            def _create_tables():
                # 메타데이터 캐시 테이블
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS media_cache (
                        title_key TEXT PRIMARY KEY,
                        year INTEGER,
                        metadata TEXT NOT NULL,
                        updated_at INTEGER NOT NULL
                    )
                """)
                
                # 인덱스 생성
                self.conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_media_cache_year 
                    ON media_cache(year)
                """)
                
                self.conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_media_cache_updated_at 
                    ON media_cache(updated_at)
                """)
                
                self.conn.commit()
                
            await loop.run_in_executor(None, _create_tables)
            
            self.logger.debug("Cache tables created")
            
        except Exception as e:
            self.logger.error(f"Error creating tables: {e}")
            raise
            
    def _generate_key(self, title: str, year: Optional[int] = None) -> str:
        """
        제목과 연도로 검색 키 생성
        
        Args:
            title: 제목
            year: 연도 (옵션)
            
        Returns:
            str: 정규화된 검색 키
        """
        # 제목을 소문자로 변환하고 공백을 언더스코어로 대체
        normalized_title = title.lower().replace(" ", "_")
        
        # 특수문자 제거
        import re
        normalized_title = re.sub(r'[^\w_]', '', normalized_title)
        
        # 연도가 있으면 추가, 없으면 'any' 추가
        if year:
            return f"{normalized_title}_{year}"
        else:
            return f"{normalized_title}_any" 