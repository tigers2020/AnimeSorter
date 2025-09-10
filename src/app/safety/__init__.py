"""
안전장치 시스템 패키지
"""

from .backup_manager import (BackupConfiguration, BackupInfo, BackupManager,
                             BackupStrategy, IBackupManager)
from .confirmation_manager import (ConfirmationManager, ConfirmationRequest,
                                   ConfirmationResponse, IConfirmationManager)
from .interruption_manager import (IInterruptionManager, InterruptionManager,
                                   InterruptionRequest, InterruptionResult)
from .safety_manager import (ISafetyManager, SafetyConfiguration,
                             SafetyManager, SafetyMode, SafetyStatus)

__all__ = [
    # 백업 시스템
    "BackupManager",
    "IBackupManager",
    "BackupConfiguration",
    "BackupStrategy",
    "BackupInfo",
    # 확인 시스템
    "ConfirmationManager",
    "IConfirmationManager",
    "ConfirmationRequest",
    "ConfirmationResponse",
    # 중단 시스템
    "InterruptionManager",
    "IInterruptionManager",
    "InterruptionRequest",
    "InterruptionResult",
    # 종합 안전 관리
    "SafetyManager",
    "ISafetyManager",
    "SafetyConfiguration",
    "SafetyMode",
    "SafetyStatus",
]
