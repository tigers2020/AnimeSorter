"""
API 키 암호화 관리 모듈

API 키를 안전하게 암호화하여 저장하고, 필요할 때 복호화하여 제공하는 기능을 담당합니다.
환경 변수를 우선적으로 사용하고, 파일 저장 시에는 암호화를 적용합니다.
"""

import os
import base64
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from src.exceptions import ConfigError


class KeyManager:
    """API 키 암호화 관리 클래스"""
    
    def __init__(self, config_dir: str | Path = "config"):
        """
        KeyManager 초기화
        
        Args:
            config_dir: 설정 파일이 저장될 디렉토리
        """
        self.config_dir = Path(config_dir)
        self.keys_file = self.config_dir / "encrypted_keys.json"
        self.logger = logging.getLogger("animesorter.security")
        
        # 암호화 키 생성 또는 로드
        self._master_key = self._get_or_create_master_key()
        self._fernet = Fernet(self._master_key)
        
    def _get_or_create_master_key(self) -> bytes:
        """
        마스터 키를 가져오거나 생성
        
        Returns:
            bytes: 마스터 키
        """
        # 환경 변수에서 마스터 키 확인
        env_key = os.getenv("ANIMESORTER_MASTER_KEY")
        if env_key:
            try:
                decoded_key = base64.urlsafe_b64decode(env_key)
                # Fernet 키 유효성 검사
                Fernet(decoded_key)
                return decoded_key
            except Exception as e:
                self.logger.warning(f"Invalid master key in environment: {e}")
        
        # 파일에서 마스터 키 로드 또는 생성
        master_key_file = self.config_dir / ".master_key"
        
        if master_key_file.exists():
            try:
                with open(master_key_file, 'rb') as f:
                    key_data = f.read()
                    # Fernet 키 유효성 검사
                    Fernet(key_data)
                    return key_data
            except Exception as e:
                self.logger.warning(f"Failed to load master key: {e}")
        
        # 새로운 마스터 키 생성
        master_key = Fernet.generate_key()
        
        # 마스터 키 저장
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(master_key_file, 'wb') as f:
                f.write(master_key)
            
            # 파일 권한 설정 (Unix 시스템에서만)
            try:
                os.chmod(master_key_file, 0o600)  # 소유자만 읽기/쓰기
            except OSError:
                pass  # Windows에서는 무시
                
            self.logger.info("New master key generated and saved")
        except Exception as e:
            self.logger.error(f"Failed to save master key: {e}")
            raise ConfigError("Failed to save master key", details=str(e))
        
        return master_key
    
    def _derive_key_from_password(self, password: str, salt: bytes) -> bytes:
        """
        비밀번호로부터 키 유도
        
        Args:
            password: 비밀번호
            salt: 솔트
            
        Returns:
            bytes: 유도된 키
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def get_api_key(self, key_name: str) -> Optional[str]:
        """
        API 키 조회 (환경 변수 우선, 암호화된 파일 차선)
        
        Args:
            key_name: 키 이름 (예: "TMDB_API_KEY")
            
        Returns:
            str or None: API 키 또는 None
        """
        # 1. 환경 변수에서 먼저 확인
        env_key = os.getenv(key_name)
        if env_key:
            self.logger.debug(f"API key '{key_name}' loaded from environment")
            return env_key
        
        # 2. 암호화된 파일에서 확인
        try:
            encrypted_keys = self._load_encrypted_keys()
            if key_name in encrypted_keys:
                encrypted_data = encrypted_keys[key_name]
                decrypted_key = self._decrypt_data(encrypted_data)
                self.logger.debug(f"API key '{key_name}' loaded from encrypted file")
                return decrypted_key
        except Exception as e:
            self.logger.warning(f"Failed to load encrypted key '{key_name}': {e}")
        
        self.logger.debug(f"API key '{key_name}' not found")
        return None
    
    def set_api_key(self, key_name: str, api_key: str, save_to_file: bool = True) -> None:
        """
        API 키 설정
        
        Args:
            key_name: 키 이름
            api_key: API 키 값
            save_to_file: 파일에 저장할지 여부
        """
        if save_to_file:
            try:
                # 기존 키 로드
                encrypted_keys = self._load_encrypted_keys()
                
                # 새 키 암호화
                encrypted_data = self._encrypt_data(api_key)
                encrypted_keys[key_name] = encrypted_data
                
                # 파일에 저장
                self._save_encrypted_keys(encrypted_keys)
                
                self.logger.info(f"API key '{key_name}' encrypted and saved")
            except Exception as e:
                self.logger.error(f"Failed to save encrypted key '{key_name}': {e}")
                raise ConfigError(f"Failed to save encrypted key '{key_name}'", details=str(e))
        else:
            self.logger.info(f"API key '{key_name}' set (not saved to file)")
    
    def remove_api_key(self, key_name: str) -> bool:
        """
        API 키 삭제
        
        Args:
            key_name: 삭제할 키 이름
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            encrypted_keys = self._load_encrypted_keys()
            
            if key_name in encrypted_keys:
                del encrypted_keys[key_name]
                self._save_encrypted_keys(encrypted_keys)
                self.logger.info(f"API key '{key_name}' removed")
                return True
            else:
                self.logger.warning(f"API key '{key_name}' not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to remove API key '{key_name}': {e}")
            return False
    
    def list_api_keys(self) -> Dict[str, bool]:
        """
        저장된 API 키 목록 조회
        
        Returns:
            dict: 키 이름과 저장 위치 (환경 변수/파일)
        """
        keys_info = {}
        
        # 환경 변수에서 확인
        common_keys = ["TMDB_API_KEY", "ANIMESORTER_MASTER_KEY"]
        for key_name in common_keys:
            if os.getenv(key_name):
                keys_info[key_name] = True  # True = 환경 변수
        
        # 암호화된 파일에서 확인
        try:
            encrypted_keys = self._load_encrypted_keys()
            for key_name in encrypted_keys:
                if key_name not in keys_info:
                    keys_info[key_name] = False  # False = 파일
        except Exception as e:
            self.logger.warning(f"Failed to load encrypted keys: {e}")
        
        return keys_info
    
    def _encrypt_data(self, data: str) -> Dict[str, str]:
        """
        데이터 암호화
        
        Args:
            data: 암호화할 데이터
            
        Returns:
            dict: 암호화된 데이터와 메타데이터
        """
        encrypted_data = self._fernet.encrypt(data.encode())
        return {
            "data": base64.urlsafe_b64encode(encrypted_data).decode(),
            "version": "1.0"
        }
    
    def _decrypt_data(self, encrypted_data: Dict[str, str]) -> str:
        """
        데이터 복호화
        
        Args:
            encrypted_data: 암호화된 데이터
            
        Returns:
            str: 복호화된 데이터
        """
        if encrypted_data.get("version") != "1.0":
            raise ValueError("Unsupported encryption version")
        
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data["data"])
        decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
        return decrypted_bytes.decode()
    
    def _load_encrypted_keys(self) -> Dict[str, Dict[str, str]]:
        """
        암호화된 키 파일 로드
        
        Returns:
            dict: 암호화된 키 데이터
        """
        if not self.keys_file.exists():
            return {}
        
        try:
            with open(self.keys_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load encrypted keys file: {e}")
            return {}
    
    def _save_encrypted_keys(self, encrypted_keys: Dict[str, Dict[str, str]]) -> None:
        """
        암호화된 키 파일 저장
        
        Args:
            encrypted_keys: 저장할 암호화된 키 데이터
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            with open(self.keys_file, 'w', encoding='utf-8') as f:
                json.dump(encrypted_keys, f, indent=2, ensure_ascii=False)
            
            # 파일 권한 설정 (Unix 시스템에서만)
            try:
                os.chmod(self.keys_file, 0o600)  # 소유자만 읽기/쓰기
            except OSError:
                pass  # Windows에서는 무시
                
        except Exception as e:
            self.logger.error(f"Failed to save encrypted keys file: {e}")
            raise ConfigError("Failed to save encrypted keys file", details=str(e))
    
    def change_master_key(self, new_password: str) -> None:
        """
        마스터 키 변경 (모든 키 재암호화)
        
        Args:
            new_password: 새로운 비밀번호
        """
        try:
            # 기존 키들 로드
            encrypted_keys = self._load_encrypted_keys()
            if not encrypted_keys:
                self.logger.warning("No keys to re-encrypt")
                return
            
            # 새로운 마스터 키 생성
            salt = os.urandom(16)
            new_master_key = self._derive_key_from_password(new_password, salt)
            new_fernet = Fernet(new_master_key)
            
            # 모든 키 재암호화
            new_encrypted_keys = {}
            for key_name, encrypted_data in encrypted_keys.items():
                # 기존 키 복호화
                old_data = self._decrypt_data(encrypted_data)
                
                # 새 키로 암호화
                new_encrypted_data = {
                    "data": base64.urlsafe_b64encode(new_fernet.encrypt(old_data.encode())).decode(),
                    "version": "1.0"
                }
                new_encrypted_keys[key_name] = new_encrypted_data
            
            # 새 마스터 키 저장
            master_key_file = self.config_dir / ".master_key"
            with open(master_key_file, 'wb') as f:
                f.write(new_master_key)
            
            # 새 암호화된 키들 저장
            self._save_encrypted_keys(new_encrypted_keys)
            
            # 내부 상태 업데이트
            self._master_key = new_master_key
            self._fernet = new_fernet
            
            self.logger.info("Master key changed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to change master key: {e}")
            raise ConfigError("Failed to change master key", details=str(e))
    
    def export_master_key(self) -> str:
        """
        마스터 키를 base64로 내보내기 (환경 변수 설정용)
        
        Returns:
            str: base64로 인코딩된 마스터 키
        """
        return base64.urlsafe_b64encode(self._master_key).decode()
    
    def validate_key(self, key_name: str, key_value: str) -> bool:
        """
        API 키 유효성 검증 (기본적인 형식 검사)
        
        Args:
            key_name: 키 이름
            key_value: 검증할 키 값
            
        Returns:
            bool: 유효성 여부
        """
        if not key_value or not key_value.strip():
            return False
        
        # TMDB API 키 형식 검사 (32자리 16진수)
        if key_name == "TMDB_API_KEY":
            if len(key_value) != 32 or not all(c in '0123456789abcdef' for c in key_value.lower()):
                return False
        
        return True 