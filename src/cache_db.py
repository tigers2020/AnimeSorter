"""
캐시 데이터베이스 모듈

외부 API 호출 결과를 로컬에 저장하여 중복 요청 방지
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, Optional

import aiosqlite
from loguru import logger

from src.exceptions import CacheError


class CacheDB:
    """API 결과 캐싱을 위한 SQLite 데이터베이스 관리 클래스"""
    
    def __init__(self, db_path: str | Path = "cache.db"):
        """
        CacheDB 초기화
        
        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = Path(db_path)
        self.conn = None
        
    async def initialize(self) -> None:
        """데이터베이스 연결 및 테이블 생성"""
        try:
            self.conn = await aiosqlite.connect(self.db_path)
            
            # 테이블 생성
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS media_cache (
                    title_key TEXT PRIMARY KEY,
                    year INTEGER,
                    metadata TEXT,
                    updated_at INTEGER
                )
            """)
            
            # 인덱스 생성
            await self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_media_cache_year ON media_cache(year)
            """)
            
            await self.conn.commit()
            logger.info(f"캐시 데이터베이스 초기화 완료: {self.db_path}")
        except Exception as e:
            logger.error(f"캐시 데이터베이스 초기화 실패: {e}", exc_info=True)
            raise CacheError(f"캐시 데이터베이스 초기화 실패: {str(e)}") from e
        
    async def close(self) -> None:
        """데이터베이스 연결 종료"""
        if self.conn:
            await self.conn.close()
            self.conn = None
            logger.debug("캐시 데이터베이스 연결 종료")
        
    async def get_cache(self, title_key: str, max_age_days: int = 30) -> Optional[Dict]:
        """
        캐시에서 메타데이터 조회
        
        Args:
            title_key: 검색 키
            max_age_days: 최대 캐시 유지 기간 (일)
            
        Returns:
            dict or None: 캐시된 메타데이터 또는 None (캐시 미스)
        """
        if not self.conn:
            await self.initialize()
            
        try:
            now = int(time.time())
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            async with self.conn.execute(
                "SELECT metadata FROM media_cache WHERE title_key = ? AND (? - updated_at) < ?",
                (title_key, now, max_age_seconds)
            ) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    logger.debug(f"캐시 적중: {title_key}")
                    return json.loads(row[0])
                    
            logger.debug(f"캐시 미스: {title_key}")
            return None
        except Exception as e:
            logger.error(f"캐시 조회 실패: {e}", exc_info=True)
            return None
        
    async def set_cache(self, title_key: str, metadata: Dict, year: Optional[int] = None) -> None:
        """
        메타데이터를 캐시에 저장
        
        Args:
            title_key: 검색 키
            metadata: 저장할 메타데이터
            year: 연도 정보 (옵션)
        """
        if not self.conn:
            await self.initialize()
            
        try:
            now = int(time.time())
            metadata_json = json.dumps(metadata, ensure_ascii=False)
            
            await self.conn.execute(
                """
                INSERT OR REPLACE INTO media_cache (title_key, year, metadata, updated_at) 
                VALUES (?, ?, ?, ?)
                """,
                (title_key, year, metadata_json, now)
            )
            
            await self.conn.commit()
            logger.debug(f"캐시 저장 완료: {title_key}")
        except Exception as e:
            logger.error(f"캐시 저장 실패: {e}", exc_info=True)
            raise CacheError(f"캐시 저장 실패: {str(e)}") from e
        
    async def cleanup_cache(self, max_age_days: int = 90, max_items: int = 10000) -> None:
        """
        오래된 캐시 항목 정리
        
        Args:
            max_age_days: 최대 보관 기간 (일)
            max_items: 최대 항목 수
        """
        if not self.conn:
            await self.initialize()
            
        try:
            now = int(time.time())
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            # 오래된 항목 삭제
            await self.conn.execute(
                "DELETE FROM media_cache WHERE (? - updated_at) > ?",
                (now, max_age_seconds)
            )
            
            # 항목 수 제한
            async with self.conn.execute("SELECT COUNT(*) FROM media_cache") as cursor:
                count = (await cursor.fetchone())[0]
                
            if count > max_items:
                # 가장 오래된 항목부터 삭제
                delete_count = count - max_items
                await self.conn.execute(
                    "DELETE FROM media_cache WHERE title_key IN (SELECT title_key FROM media_cache ORDER BY updated_at ASC LIMIT ?)",
                    (delete_count,)
                )
            
            await self.conn.commit()
            logger.info(f"캐시 정리 완료. 삭제된 항목: {delete_count if count > max_items else 0}")
        except Exception as e:
            logger.error(f"캐시 정리 실패: {e}", exc_info=True)
            raise CacheError(f"캐시 정리 실패: {str(e)}") from e
    
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
        normalized_title = "".join(c for c in normalized_title if c.isalnum() or c == "_")
        
        # 연도가 있으면 추가, 없으면 'any' 추가
        year_part = f"_{year}" if year else "_any"
        
        return f"{normalized_title}{year_part}" 