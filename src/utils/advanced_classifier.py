"""
고급 분류 시스템
다양한 분류 전략을 제공하는 확장 가능한 분류 시스템
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

from .file_cleaner import CleanResult

logger = logging.getLogger(__name__)


class ClassificationStrategy(Enum):
    """분류 전략 타입"""
    SMART = "smart"
    TAG_BASED = "tag_based"
    USER_DEFINED = "user_defined"
    RULE_BASED = "rule_based"


@dataclass
class ClassificationRule:
    """분류 규칙"""
    name: str
    pattern: str
    target_folder: str
    priority: int = 1
    enabled: bool = True
    description: str = ""
    
    def __post_init__(self):
        """규칙 초기화 후 처리"""
        try:
            self.compiled_pattern = re.compile(self.pattern, re.IGNORECASE)
        except re.error as e:
            logger.error(f"Invalid regex pattern '{self.pattern}': {e}")
            self.compiled_pattern = None


@dataclass
class ClassificationResult:
    """분류 결과"""
    original_path: Path
    suggested_folder: str
    confidence: float
    strategy: ClassificationStrategy
    metadata: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""


class SmartClassifier:
    """스마트 분류기 - 머신러닝 기반 분류"""
    
    def __init__(self):
        self.genre_keywords = {
            "action": ["action", "액션", "전투", "싸움", "battle", "fight"],
            "comedy": ["comedy", "코미디", "개그", "funny", "humor"],
            "drama": ["drama", "드라마", "감동", "emotional"],
            "fantasy": ["fantasy", "판타지", "마법", "magic", "wizard"],
            "horror": ["horror", "호러", "공포", "scary", "fear"],
            "romance": ["romance", "로맨스", "사랑", "love", "romantic"],
            "sci_fi": ["sci-fi", "sf", "과학", "science", "future"],
            "thriller": ["thriller", "스릴러", "긴장", "tension"],
            "slice_of_life": ["slice of life", "일상", "daily", "life"],
            "mecha": ["mecha", "로봇", "robot", "기계", "machine"],
            "sports": ["sports", "스포츠", "운동", "athletic"],
            "music": ["music", "음악", "뮤직", "song", "band"],
            "school": ["school", "학교", "학원", "student", "classroom"],
            "isekai": ["isekai", "이세계", "another world", "transmigration"],
            "shounen": ["shounen", "소년", "young", "teen"],
            "shoujo": ["shoujo", "소녀", "girl", "female"],
            "seinen": ["seinen", "청년", "adult", "mature"],
            "josei": ["josei", "여성", "woman", "ladies"]
        }
        
        self.quality_keywords = {
            "high_quality": ["1080p", "4k", "uhd", "bluray", "bd"],
            "medium_quality": ["720p", "hd"],
            "low_quality": ["480p", "360p", "dvd"]
        }
        
    def classify(self, clean_result: CleanResult) -> ClassificationResult:
        """스마트 분류 수행"""
        title = clean_result.title.lower()
        filename = clean_result.original_filename.lower()
        
        # 장르 분류
        detected_genres = []
        for genre, keywords in self.genre_keywords.items():
            for keyword in keywords:
                if keyword in title or keyword in filename:
                    detected_genres.append(genre)
                    break
        
        # 품질 분류
        detected_quality = "unknown"
        for quality, keywords in self.quality_keywords.items():
            for keyword in keywords:
                if keyword in filename:
                    detected_quality = quality
                    break
        
        # 폴더명 생성
        if detected_genres:
            primary_genre = detected_genres[0]
            folder_name = f"{clean_result.title} ({primary_genre.title()})"
        else:
            folder_name = clean_result.title
            
        # 신뢰도 계산
        confidence = self._calculate_confidence(title, detected_genres, detected_quality)
        
        return ClassificationResult(
            original_path=Path(clean_result.original_filename),
            suggested_folder=folder_name,
            confidence=confidence,
            strategy=ClassificationStrategy.SMART,
            metadata={
                "genres": detected_genres,
                "quality": detected_quality,
                "year": clean_result.year
            },
            reason=f"Detected genres: {', '.join(detected_genres)}" if detected_genres else "No specific genre detected"
        )
    
    def _calculate_confidence(self, title: str, genres: List[str], quality: str) -> float:
        """분류 신뢰도 계산"""
        confidence = 0.5  # 기본 신뢰도
        
        # 장르 매칭 보너스
        if genres:
            confidence += 0.3
            
        # 품질 정보 보너스
        if quality != "unknown":
            confidence += 0.1
            
        # 제목 길이 보너스 (너무 짧으면 신뢰도 감소)
        if len(title) < 3:
            confidence -= 0.2
        elif len(title) > 10:
            confidence += 0.1
            
        return min(1.0, max(0.0, confidence))


class TagBasedClassifier:
    """태그 기반 분류기"""
    
    def __init__(self, tags_file: Optional[Path] = None):
        self.tags_file = tags_file or Path("classification_tags.json")
        self.tags = self._load_tags()
        
    def _load_tags(self) -> Dict[str, List[str]]:
        """태그 파일 로드"""
        if self.tags_file.exists():
            try:
                with open(self.tags_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load tags file: {e}")
                return {}
        return {}
    
    def save_tags(self):
        """태그 파일 저장"""
        try:
            with open(self.tags_file, 'w', encoding='utf-8') as f:
                json.dump(self.tags, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tags file: {e}")
    
    def add_tag(self, title: str, tag: str):
        """태그 추가"""
        if title not in self.tags:
            self.tags[title] = []
        if tag not in self.tags[title]:
            self.tags[title].append(tag)
            self.save_tags()
    
    def remove_tag(self, title: str, tag: str):
        """태그 제거"""
        if title in self.tags and tag in self.tags[title]:
            self.tags[title].remove(tag)
            if not self.tags[title]:
                del self.tags[title]
            self.save_tags()
    
    def classify(self, clean_result: CleanResult) -> ClassificationResult:
        """태그 기반 분류 수행"""
        title = clean_result.title
        
        if title in self.tags:
            tags = self.tags[title]
            folder_name = f"{title} ({', '.join(tags)})"
            confidence = 0.9  # 태그가 있으면 높은 신뢰도
        else:
            folder_name = title
            confidence = 0.3  # 태그가 없으면 낮은 신뢰도
            tags = []
        
        return ClassificationResult(
            original_path=Path(clean_result.original_filename),
            suggested_folder=folder_name,
            confidence=confidence,
            strategy=ClassificationStrategy.TAG_BASED,
            metadata={"tags": tags},
            reason=f"User tags: {', '.join(tags)}" if tags else "No user tags found"
        )


class RuleBasedClassifier:
    """규칙 기반 분류기"""
    
    def __init__(self, rules_file: Optional[Path] = None):
        self.rules_file = rules_file or Path("classification_rules.json")
        self.rules: List[ClassificationRule] = []
        self._load_rules()
    
    def _load_rules(self):
        """규칙 파일 로드"""
        if self.rules_file.exists():
            try:
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    rules_data = json.load(f)
                    self.rules = [ClassificationRule(**rule) for rule in rules_data]
            except Exception as e:
                logger.error(f"Failed to load rules file: {e}")
                self.rules = []
        else:
            # 기본 규칙 생성
            self._create_default_rules()
    
    def _create_default_rules(self):
        """기본 분류 규칙 생성"""
        default_rules = [
            ClassificationRule(
                name="Movie Rule",
                pattern=r"\b(movie|film|theatrical)\b",
                target_folder="Movies",
                priority=1,
                description="영화 파일 분류"
            ),
            ClassificationRule(
                name="OVA Rule",
                pattern=r"\b(ova|oav)\b",
                target_folder="OVA",
                priority=2,
                description="OVA 파일 분류"
            ),
            ClassificationRule(
                name="Special Rule",
                pattern=r"\b(special|sp|extra)\b",
                target_folder="Specials",
                priority=3,
                description="특별편 파일 분류"
            ),
            ClassificationRule(
                name="Season Rule",
                pattern=r"S(\d{1,2})",
                target_folder="Season {season}",
                priority=4,
                description="시즌별 분류"
            )
        ]
        self.rules = default_rules
        self.save_rules()
    
    def save_rules(self):
        """규칙 파일 저장"""
        try:
            rules_data = [
                {
                    "name": rule.name,
                    "pattern": rule.pattern,
                    "target_folder": rule.target_folder,
                    "priority": rule.priority,
                    "enabled": rule.enabled,
                    "description": rule.description
                }
                for rule in self.rules
            ]
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                json.dump(rules_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save rules file: {e}")
    
    def add_rule(self, rule: ClassificationRule):
        """규칙 추가"""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority)
        self.save_rules()
    
    def remove_rule(self, rule_name: str):
        """규칙 제거"""
        self.rules = [r for r in self.rules if r.name != rule_name]
        self.save_rules()
    
    def classify(self, clean_result: CleanResult) -> ClassificationResult:
        """규칙 기반 분류 수행"""
        filename = clean_result.original_filename
        title = clean_result.title
        
        # 활성화된 규칙들을 우선순위 순으로 적용
        for rule in sorted(self.rules, key=lambda r: r.priority):
            if not rule.enabled or not rule.compiled_pattern:
                continue
                
            match = rule.compiled_pattern.search(filename)
            if match:
                # 타겟 폴더명 생성 (플레이스홀더 치환)
                target_folder = rule.target_folder
                if "{season}" in target_folder:
                    season_match = re.search(r"S(\d{1,2})", filename)
                    if season_match:
                        target_folder = target_folder.replace("{season}", season_match.group(1))
                
                return ClassificationResult(
                    original_path=Path(filename),
                    suggested_folder=target_folder,
                    confidence=0.8,
                    strategy=ClassificationStrategy.RULE_BASED,
                    metadata={"rule": rule.name, "match": match.group()},
                    reason=f"Matched rule: {rule.name} ({rule.description})"
                )
        
        # 규칙 매칭 실패 시 기본 폴더명 반환
        return ClassificationResult(
            original_path=Path(filename),
            suggested_folder=title,
            confidence=0.5,
            strategy=ClassificationStrategy.RULE_BASED,
            metadata={},
            reason="No rules matched"
        )


class AdvancedClassifier:
    """고급 분류 시스템 - 모든 분류기를 통합 관리"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path("config/classification")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 분류기 초기화
        self.smart_classifier = SmartClassifier()
        self.tag_classifier = TagBasedClassifier(self.config_dir / "tags.json")
        self.rule_classifier = RuleBasedClassifier(self.config_dir / "rules.json")
        
        # 분류 전략 우선순위
        self.strategy_priority = [
            ClassificationStrategy.TAG_BASED,      # 사용자 태그가 최우선
            ClassificationStrategy.RULE_BASED,     # 규칙 기반 분류
            ClassificationStrategy.SMART,          # 스마트 분류
            ClassificationStrategy.USER_DEFINED    # 사용자 정의 (최후)
        ]
    
    def classify(self, clean_result: CleanResult, 
                preferred_strategy: Optional[ClassificationStrategy] = None) -> ClassificationResult:
        """통합 분류 수행"""
        results = []
        
        # 각 분류기로 분류 수행
        if preferred_strategy != ClassificationStrategy.TAG_BASED:
            results.append(self.tag_classifier.classify(clean_result))
        
        if preferred_strategy != ClassificationStrategy.RULE_BASED:
            results.append(self.rule_classifier.classify(clean_result))
        
        if preferred_strategy != ClassificationStrategy.SMART:
            results.append(self.smart_classifier.classify(clean_result))
        
        # 결과 선택 (신뢰도와 전략 우선순위 고려)
        best_result = self._select_best_result(results, preferred_strategy)
        
        return best_result
    
    def _select_best_result(self, results: List[ClassificationResult], 
                          preferred_strategy: Optional[ClassificationStrategy]) -> ClassificationResult:
        """최적 결과 선택"""
        if not results:
            # 기본 결과 반환
            return ClassificationResult(
                original_path=Path(""),
                suggested_folder="Unknown",
                confidence=0.0,
                strategy=ClassificationStrategy.USER_DEFINED,
                reason="No classification results"
            )
        
        # 선호 전략이 있으면 해당 전략의 결과 우선
        if preferred_strategy:
            preferred_results = [r for r in results if r.strategy == preferred_strategy]
            if preferred_results:
                return max(preferred_results, key=lambda r: r.confidence)
        
        # 신뢰도와 전략 우선순위를 고려한 점수 계산
        scored_results = []
        for result in results:
            # 기본 점수는 신뢰도
            score = result.confidence
            
            # 전략 우선순위 보너스
            strategy_bonus = 0.1 * (len(self.strategy_priority) - self.strategy_priority.index(result.strategy))
            score += strategy_bonus
            
            scored_results.append((result, score))
        
        # 최고 점수 결과 반환
        return max(scored_results, key=lambda x: x[1])[0]
    
    def get_classification_stats(self) -> Dict[str, Any]:
        """분류 통계 반환"""
        return {
            "tag_count": len(self.tag_classifier.tags),
            "rule_count": len(self.rule_classifier.rules),
            "enabled_rules": len([r for r in self.rule_classifier.rules if r.enabled]),
            "strategies": [s.value for s in self.strategy_priority]
        }
    
    def export_config(self, export_path: Path):
        """분류 설정 내보내기"""
        config = {
            "tags": self.tag_classifier.tags,
            "rules": [
                {
                    "name": rule.name,
                    "pattern": rule.pattern,
                    "target_folder": rule.target_folder,
                    "priority": rule.priority,
                    "enabled": rule.enabled,
                    "description": rule.description
                }
                for rule in self.rule_classifier.rules
            ],
            "strategy_priority": [s.value for s in self.strategy_priority]
        }
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def import_config(self, import_path: Path):
        """분류 설정 가져오기"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 태그 가져오기
            if "tags" in config:
                self.tag_classifier.tags = config["tags"]
                self.tag_classifier.save_tags()
            
            # 규칙 가져오기
            if "rules" in config:
                self.rule_classifier.rules = [ClassificationRule(**rule) for rule in config["rules"]]
                self.rule_classifier.save_rules()
            
            # 전략 우선순위 가져오기
            if "strategy_priority" in config:
                self.strategy_priority = [ClassificationStrategy(s) for s in config["strategy_priority"]]
                
        except Exception as e:
            logger.error(f"Failed to import classification config: {e}")
            raise 