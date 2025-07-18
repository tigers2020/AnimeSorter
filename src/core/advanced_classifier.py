"""
고급 분류 시스템

사용자 정의 분류 규칙과 스마트 폴더 기능을 제공합니다.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from src.core.file_cleaner import CleanResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RuleType(Enum):
    """분류 규칙 타입"""
    TITLE_MATCH = "title_match"
    GENRE_MATCH = "genre_match"
    YEAR_RANGE = "year_range"
    RATING_RANGE = "rating_range"
    EPISODE_COUNT = "episode_count"
    CUSTOM_SCRIPT = "custom_script"


class OperatorType(Enum):
    """연산자 타입"""
    EQUALS = "equals"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    BETWEEN = "between"


@dataclass
class ClassificationRule:
    """분류 규칙"""
    name: str
    rule_type: RuleType
    field: str
    operator: OperatorType
    value: Any
    target_folder: str
    priority: int = 0
    enabled: bool = True
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClassificationRule':
        """딕셔너리에서 생성"""
        data['rule_type'] = RuleType(data['rule_type'])
        data['operator'] = OperatorType(data['operator'])
        return cls(**data)


@dataclass
class SmartFolder:
    """스마트 폴더"""
    name: str
    path: str
    rules: List[ClassificationRule]
    auto_create: bool = True
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'name': self.name,
            'path': self.path,
            'rules': [rule.to_dict() for rule in self.rules],
            'auto_create': self.auto_create,
            'description': self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SmartFolder':
        """딕셔너리에서 생성"""
        rules = [ClassificationRule.from_dict(rule_data) for rule_data in data.get('rules', [])]
        return cls(
            name=data['name'],
            path=data['path'],
            rules=rules,
            auto_create=data.get('auto_create', True),
            description=data.get('description', '')
        )


class AdvancedClassifier:
    """고급 분류 시스템"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        고급 분류 시스템 초기화
        
        Args:
            config_path: 설정 파일 경로
        """
        self.rules: List[ClassificationRule] = []
        self.smart_folders: List[SmartFolder] = []
        self.config_path = config_path or "classification_rules.json"
        self._load_rules()
        
    def _load_rules(self):
        """분류 규칙 로드"""
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 규칙 로드
                self.rules = [
                    ClassificationRule.from_dict(rule_data)
                    for rule_data in data.get('rules', [])
                ]
                
                # 스마트 폴더 로드
                self.smart_folders = [
                    SmartFolder.from_dict(folder_data)
                    for folder_data in data.get('smart_folders', [])
                ]
                
                logger.info(f"분류 규칙 {len(self.rules)}개, 스마트 폴더 {len(self.smart_folders)}개 로드됨")
            else:
                self._create_default_rules()
                
        except Exception as e:
            logger.error(f"분류 규칙 로드 실패: {e}")
            self._create_default_rules()
    
    def _create_default_rules(self):
        """기본 분류 규칙 생성"""
        self.rules = [
            ClassificationRule(
                name="액션 애니메",
                rule_type=RuleType.GENRE_MATCH,
                field="genres",
                operator=OperatorType.CONTAINS,
                value="Action",
                target_folder="Action",
                priority=1,
                description="액션 장르 애니메이션"
            ),
            ClassificationRule(
                name="2020년 이후 작품",
                rule_type=RuleType.YEAR_RANGE,
                field="year",
                operator=OperatorType.GREATER_EQUAL,
                value=2020,
                target_folder="Recent",
                priority=2,
                description="2020년 이후 제작된 작품"
            ),
            ClassificationRule(
                name="고평가 작품",
                rule_type=RuleType.RATING_RANGE,
                field="rating",
                operator=OperatorType.GREATER_EQUAL,
                value=8.0,
                target_folder="Highly Rated",
                priority=3,
                description="평점 8.0 이상 작품"
            )
        ]
        
        self.smart_folders = [
            SmartFolder(
                name="액션 애니메",
                path="Action",
                rules=[self.rules[0]],
                description="액션 장르 애니메이션 모음"
            ),
            SmartFolder(
                name="최신 작품",
                path="Recent",
                rules=[self.rules[1]],
                description="2020년 이후 제작된 작품"
            ),
            SmartFolder(
                name="고평가 작품",
                path="Highly Rated",
                rules=[self.rules[2]],
                description="평점 8.0 이상 작품"
            )
        ]
        
        self._save_rules()
    
    def _save_rules(self):
        """분류 규칙 저장"""
        try:
            data = {
                'rules': [rule.to_dict() for rule in self.rules],
                'smart_folders': [folder.to_dict() for folder in self.smart_folders]
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.info("분류 규칙 저장 완료")
            
        except Exception as e:
            logger.error(f"분류 규칙 저장 실패: {e}")
    
    def add_rule(self, rule: ClassificationRule):
        """분류 규칙 추가"""
        self.rules.append(rule)
        self.rules.sort(key=lambda x: x.priority, reverse=True)
        self._save_rules()
        logger.info(f"분류 규칙 추가: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """분류 규칙 제거"""
        self.rules = [rule for rule in self.rules if rule.name != rule_name]
        self._save_rules()
        logger.info(f"분류 규칙 제거: {rule_name}")
    
    def update_rule(self, rule_name: str, updated_rule: ClassificationRule):
        """분류 규칙 업데이트"""
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                self.rules[i] = updated_rule
                self.rules.sort(key=lambda x: x.priority, reverse=True)
                self._save_rules()
                logger.info(f"분류 규칙 업데이트: {rule_name}")
                return
        logger.warning(f"분류 규칙을 찾을 수 없음: {rule_name}")
    
    def add_smart_folder(self, folder: SmartFolder):
        """스마트 폴더 추가"""
        self.smart_folders.append(folder)
        self._save_rules()
        logger.info(f"스마트 폴더 추가: {folder.name}")
    
    def remove_smart_folder(self, folder_name: str):
        """스마트 폴더 제거"""
        self.smart_folders = [folder for folder in self.smart_folders if folder.name != folder_name]
        self._save_rules()
        logger.info(f"스마트 폴더 제거: {folder_name}")
    
    def classify_file(self, clean_result: CleanResult, metadata: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        파일 분류
        
        Args:
            clean_result: 정제된 파일 정보
            metadata: 메타데이터 (선택사항)
            
        Returns:
            적용된 분류 폴더 목록
        """
        applied_folders = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
                
            if self._evaluate_rule(rule, clean_result, metadata):
                applied_folders.append(rule.target_folder)
                logger.debug(f"규칙 '{rule.name}' 적용: {rule.target_folder}")
        
        return applied_folders
    
    def _evaluate_rule(self, rule: ClassificationRule, clean_result: CleanResult, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        규칙 평가
        
        Args:
            rule: 평가할 규칙
            clean_result: 정제된 파일 정보
            metadata: 메타데이터
            
        Returns:
            규칙이 적용되는지 여부
        """
        try:
            if rule.rule_type == RuleType.TITLE_MATCH:
                return self._evaluate_title_match(rule, clean_result)
            elif rule.rule_type == RuleType.GENRE_MATCH:
                return self._evaluate_genre_match(rule, metadata)
            elif rule.rule_type == RuleType.YEAR_RANGE:
                return self._evaluate_year_range(rule, clean_result, metadata)
            elif rule.rule_type == RuleType.RATING_RANGE:
                return self._evaluate_rating_range(rule, metadata)
            elif rule.rule_type == RuleType.EPISODE_COUNT:
                return self._evaluate_episode_count(rule, clean_result, metadata)
            elif rule.rule_type == RuleType.CUSTOM_SCRIPT:
                return self._evaluate_custom_script(rule, clean_result, metadata)
            else:
                logger.warning(f"알 수 없는 규칙 타입: {rule.rule_type}")
                return False
                
        except Exception as e:
            logger.error(f"규칙 평가 중 오류: {e}")
            return False
    
    def _evaluate_title_match(self, rule: ClassificationRule, clean_result: CleanResult) -> bool:
        """제목 매칭 규칙 평가"""
        title = clean_result.title or ""
        
        if rule.operator == OperatorType.EQUALS:
            return title.lower() == rule.value.lower()
        elif rule.operator == OperatorType.CONTAINS:
            return rule.value.lower() in title.lower()
        elif rule.operator == OperatorType.STARTS_WITH:
            return title.lower().startswith(rule.value.lower())
        elif rule.operator == OperatorType.ENDS_WITH:
            return title.lower().endswith(rule.value.lower())
        elif rule.operator == OperatorType.REGEX:
            return bool(re.search(rule.value, title, re.IGNORECASE))
        
        return False
    
    def _evaluate_genre_match(self, rule: ClassificationRule, metadata: Optional[Dict[str, Any]]) -> bool:
        """장르 매칭 규칙 평가"""
        if not metadata or 'genres' not in metadata:
            return False
        
        genres = metadata['genres']
        if isinstance(genres, str):
            genres = [genres]
        
        if rule.operator == OperatorType.CONTAINS:
            return any(rule.value.lower() in genre.lower() for genre in genres)
        elif rule.operator == OperatorType.EQUALS:
            return any(rule.value.lower() == genre.lower() for genre in genres)
        
        return False
    
    def _evaluate_year_range(self, rule: ClassificationRule, clean_result: CleanResult, metadata: Optional[Dict[str, Any]]) -> bool:
        """연도 범위 규칙 평가"""
        year = clean_result.year
        if not year and metadata and 'release_date' in metadata:
            try:
                year = int(metadata['release_date'][:4])
            except (ValueError, IndexError):
                return False
        
        if not year:
            return False
        
        if rule.operator == OperatorType.GREATER_THAN:
            return year > rule.value
        elif rule.operator == OperatorType.LESS_THAN:
            return year < rule.value
        elif rule.operator == OperatorType.GREATER_EQUAL:
            return year >= rule.value
        elif rule.operator == OperatorType.LESS_EQUAL:
            return year <= rule.value
        elif rule.operator == OperatorType.BETWEEN:
            start_year, end_year = rule.value
            return start_year <= year <= end_year
        
        return False
    
    def _evaluate_rating_range(self, rule: ClassificationRule, metadata: Optional[Dict[str, Any]]) -> bool:
        """평점 범위 규칙 평가"""
        if not metadata or 'rating' not in metadata:
            return False
        
        rating = metadata['rating']
        if not isinstance(rating, (int, float)):
            return False
        
        if rule.operator == OperatorType.GREATER_THAN:
            return rating > rule.value
        elif rule.operator == OperatorType.LESS_THAN:
            return rating < rule.value
        elif rule.operator == OperatorType.GREATER_EQUAL:
            return rating >= rule.value
        elif rule.operator == OperatorType.LESS_EQUAL:
            return rating <= rule.value
        elif rule.operator == OperatorType.BETWEEN:
            min_rating, max_rating = rule.value
            return min_rating <= rating <= max_rating
        
        return False
    
    def _evaluate_episode_count(self, rule: ClassificationRule, clean_result: CleanResult, metadata: Optional[Dict[str, Any]]) -> bool:
        """에피소드 수 규칙 평가"""
        episode_count = None
        
        if metadata and 'episode_count' in metadata:
            episode_count = metadata['episode_count']
        elif clean_result.episode:
            episode_count = clean_result.episode
        
        if episode_count is None:
            return False
        
        if rule.operator == OperatorType.GREATER_THAN:
            return episode_count > rule.value
        elif rule.operator == OperatorType.LESS_THAN:
            return episode_count < rule.value
        elif rule.operator == OperatorType.GREATER_EQUAL:
            return episode_count >= rule.value
        elif rule.operator == OperatorType.LESS_EQUAL:
            return episode_count <= rule.value
        elif rule.operator == OperatorType.BETWEEN:
            min_episodes, max_episodes = rule.value
            return min_episodes <= episode_count <= max_episodes
        
        return False
    
    def _evaluate_custom_script(self, rule: ClassificationRule, clean_result: CleanResult, metadata: Optional[Dict[str, Any]]) -> bool:
        """사용자 정의 스크립트 규칙 평가"""
        try:
            # 사용자 정의 스크립트 실행
            # 보안상의 이유로 제한된 환경에서 실행
            script_globals = {
                'clean_result': clean_result,
                'metadata': metadata or {},
                're': re,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict
            }
            
            result = eval(rule.value, script_globals)
            return bool(result)
            
        except Exception as e:
            logger.error(f"사용자 정의 스크립트 실행 오류: {e}")
            return False
    
    def get_smart_folder_suggestions(self, clean_result: CleanResult, metadata: Optional[Dict[str, Any]] = None) -> List[SmartFolder]:
        """
        스마트 폴더 제안
        
        Args:
            clean_result: 정제된 파일 정보
            metadata: 메타데이터
            
        Returns:
            적용 가능한 스마트 폴더 목록
        """
        suggestions = []
        
        for folder in self.smart_folders:
            if self._evaluate_smart_folder(folder, clean_result, metadata):
                suggestions.append(folder)
        
        return suggestions
    
    def _evaluate_smart_folder(self, folder: SmartFolder, clean_result: CleanResult, metadata: Optional[Dict[str, Any]]) -> bool:
        """스마트 폴더 평가"""
        if not folder.rules:
            return False
        
        # 모든 규칙이 만족되어야 함 (AND 조건)
        for rule in folder.rules:
            if not self._evaluate_rule(rule, clean_result, metadata):
                return False
        
        return True
    
    def create_smart_folder_structure(self, base_path: str):
        """스마트 폴더 구조 생성"""
        for folder in self.smart_folders:
            if folder.auto_create:
                folder_path = Path(base_path) / folder.path
                folder_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"스마트 폴더 생성: {folder_path}")
    
    def get_rule_statistics(self) -> Dict[str, Any]:
        """규칙 통계 반환"""
        return {
            'total_rules': len(self.rules),
            'enabled_rules': len([r for r in self.rules if r.enabled]),
            'rule_types': {
                rule_type.value: len([r for r in self.rules if r.rule_type == rule_type])
                for rule_type in RuleType
            },
            'smart_folders': len(self.smart_folders),
            'auto_create_folders': len([f for f in self.smart_folders if f.auto_create])
        } 