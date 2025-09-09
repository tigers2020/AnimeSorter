#!/usr/bin/env python3
"""
Safety System Manager for MainWindow

MainWindow의 Safety System 관련 메서드들을 관리하는 클래스입니다.
안전 모드 변경, 백업 생성/복원, 안전 상태 표시를 담당합니다.
"""

import logging
from pathlib import Path

from PyQt5.QtWidgets import QMainWindow, QMessageBox

from src.app import (IBackupManager, IConfirmationManager,
                     IInterruptionManager, ISafetyManager, get_service)


class SafetySystemManager:
    """Safety System 관련 메서드들을 관리하는 클래스"""

    def __init__(self, main_window: QMainWindow):
        """SafetySystemManager 초기화"""
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

        # Safety System 매니저들
        self.safety_manager: ISafetyManager | None = None
        self.backup_manager: IBackupManager | None = None
        self.confirmation_manager: IConfirmationManager | None = None
        self.interruption_manager: IInterruptionManager | None = None

        # 초기화
        self.init_safety_system()

    def init_safety_system(self):
        """Safety System 초기화"""
        try:
            # Safety Manager 가져오기
            self.safety_manager = get_service(ISafetyManager)
            self.logger.info(f"✅ SafetyManager 연결됨: {id(self.safety_manager)}")

            # 하위 매니저들 가져오기
            self.backup_manager = get_service(IBackupManager)
            self.confirmation_manager = get_service(IConfirmationManager)
            self.interruption_manager = get_service(IInterruptionManager)

            self.logger.info("✅ Safety System 하위 매니저들 연결됨")

        except Exception as e:
            self.logger.error(f"⚠️ Safety System 초기화 실패: {e}")
            self.safety_manager = None
            self.backup_manager = None
            self.confirmation_manager = None
            self.interruption_manager = None

    def change_safety_mode(self, mode: str):
        """안전 모드 변경"""
        try:
            if self.safety_manager:
                success = self.safety_manager.change_safety_mode(mode)
                if success:
                    self.logger.info(f"✅ 안전 모드 변경됨: {mode}")
                    self.main_window.update_status_bar(f"안전 모드: {mode}")
                else:
                    self.logger.error(f"❌ 안전 모드 변경 실패: {mode}")
                    QMessageBox.warning(
                        self.main_window,
                        "모드 변경 실패",
                        f"안전 모드를 {mode}로 변경할 수 없습니다.",
                    )
            else:
                self.logger.warning("⚠️ Safety Manager가 초기화되지 않았습니다")
                QMessageBox.warning(
                    self.main_window, "초기화 오류", "Safety System이 초기화되지 않았습니다."
                )
        except Exception as e:
            self.logger.error(f"❌ 안전 모드 변경 실패: {e}")
            QMessageBox.critical(
                self.main_window, "오류", f"안전 모드 변경 중 오류가 발생했습니다: {e}"
            )

    def create_backup(self):
        """백업 생성"""
        try:
            if not self.backup_manager:
                QMessageBox.warning(
                    self.main_window, "초기화 오류", "Backup Manager가 초기화되지 않았습니다."
                )
                return

            # 현재 작업 디렉토리 백업
            current_dir = getattr(
                self.main_window.settings_manager.config.user_preferences.gui_state,
                "last_source_directory",
                "",
            )
            if not current_dir:
                QMessageBox.information(
                    self.main_window, "백업", "백업할 작업 디렉토리가 설정되지 않았습니다."
                )
                return

            source_paths = [Path(current_dir)]

            # 백업 생성
            backup_info = self.backup_manager.create_backup(source_paths, "copy")
            if backup_info:
                QMessageBox.information(
                    self.main_window,
                    "백업 완료",
                    f"백업이 성공적으로 생성되었습니다.\n백업 ID: {backup_info.backup_id}",
                )
            else:
                QMessageBox.warning(self.main_window, "백업 실패", "백업 생성에 실패했습니다.")
        except Exception as e:
            self.logger.error(f"❌ 백업 생성 실패: {e}")
            QMessageBox.critical(self.main_window, "오류", f"백업 생성 중 오류가 발생했습니다: {e}")

    def restore_backup(self):
        """백업 복원"""
        try:
            if not self.backup_manager:
                QMessageBox.warning(
                    self.main_window, "초기화 오류", "Backup Manager가 초기화되지 않았습니다."
                )
                return

            # 백업 목록 조회
            backups = self.backup_manager.list_backups()
            if not backups:
                QMessageBox.information(self.main_window, "백업 복원", "복원할 백업이 없습니다.")
                return

            # 가장 최근 백업 선택 (실제로는 사용자가 선택할 수 있도록 다이얼로그를 만들어야 함)
            latest_backup = max(backups, key=lambda b: b.created_at)

            # 복원 확인
            reply = QMessageBox.question(
                self.main_window,
                "백업 복원",
                f"백업 '{latest_backup.backup_id}'을 복원하시겠습니까?\n"
                f"생성일: {latest_backup.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"파일 수: {latest_backup.files_backed_up}개",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                # 복원 실행
                success = self.backup_manager.restore_backup(
                    latest_backup.backup_id, Path(latest_backup.source_paths[0])
                )
                if success:
                    QMessageBox.information(
                        self.main_window, "복원 완료", "백업이 성공적으로 복원되었습니다."
                    )
                else:
                    QMessageBox.warning(self.main_window, "복원 실패", "백업 복원에 실패했습니다.")
        except Exception as e:
            self.logger.error(f"❌ 백업 복원 실패: {e}")
            QMessageBox.critical(self.main_window, "오류", f"백업 복원 중 오류가 발생했습니다: {e}")

    def show_safety_status(self):
        """안전 상태 표시"""
        try:
            if not self.safety_manager:
                QMessageBox.warning(
                    self.main_window, "초기화 오류", "Safety Manager가 초기화되지 않았습니다."
                )
                return

            status = self.safety_manager.get_safety_status()
            recommendations = self.safety_manager.get_safety_recommendations()

            # 상태 정보 구성
            status_text = f"현재 안전 모드: {status.current_mode}\n"
            status_text += f"안전 점수: {status.safety_score:.1f}/100\n"
            status_text += f"위험도: {status.risk_level}\n"
            status_text += f"백업 활성화: {'예' if status.backup_enabled else '아니오'}\n"
            status_text += f"확인 필요: {'예' if status.confirmation_required else '아니오'}\n"
            status_text += f"중단 가능: {'예' if status.can_interrupt else '아니오'}\n"

            if status.warnings:
                status_text += "\n경고:\n" + "\n".join(
                    f"• {warning}" for warning in status.warnings
                )

            if recommendations:
                status_text += "\n\n권장사항:\n" + "\n".join(f"• {rec}" for rec in recommendations)

            QMessageBox.information(self.main_window, "안전 상태", status_text)
        except Exception as e:
            self.logger.error(f"❌ 안전 상태 표시 실패: {e}")
            QMessageBox.critical(
                self.main_window, "오류", f"안전 상태 확인 중 오류가 발생했습니다: {e}"
            )

    # 이벤트 핸들러 메서드들
    def handle_safety_status_update(self, event):
        """Safety 상태 업데이트 이벤트 처리"""
        try:
            self.logger.info(f"🛡️ Safety 상태 업데이트: {event.status}")
            self.main_window.update_status_bar(f"안전 시스템: {event.status}")
        except Exception as e:
            self.logger.error(f"❌ Safety 상태 업데이트 처리 중 오류: {e}")

    def handle_safety_alert(self, event):
        """Safety 경고 이벤트 처리"""
        try:
            self.logger.warning(f"⚠️ Safety 경고: {event.message}")
            QMessageBox.warning(self.main_window, "안전 시스템 경고", event.message)
        except Exception as e:
            self.logger.error(f"❌ Safety 경고 처리 중 오류: {e}")

    def handle_confirmation_required(self, event):
        """확인 요청 이벤트 처리"""
        try:
            self.logger.info(f"❓ 확인 요청: {event.message}")
            # 확인 다이얼로그 표시 로직은 MainWindow에서 처리
        except Exception as e:
            self.logger.error(f"❌ 확인 요청 처리 중 오류: {e}")

    def handle_backup_started(self, event):
        """백업 시작 이벤트 처리"""
        try:
            self.logger.info(f"💾 백업 시작: {event.backup_id}")
            self.main_window.update_status_bar("백업 시작됨")
        except Exception as e:
            self.logger.error(f"❌ 백업 시작 처리 중 오류: {e}")

    def handle_backup_completed(self, event):
        """백업 완료 이벤트 처리"""
        try:
            self.logger.info(f"✅ 백업 완료: {event.backup_id}")
            self.main_window.update_status_bar("백업 완료됨")
        except Exception as e:
            self.logger.error(f"❌ 백업 완료 처리 중 오류: {e}")

    def handle_backup_failed(self, event):
        """백업 실패 이벤트 처리"""
        try:
            self.logger.error(f"❌ 백업 실패: {event.backup_id} - {event.error_message}")
            QMessageBox.critical(self.main_window, "백업 실패", event.error_message)
        except Exception as e:
            self.logger.error(f"❌ 백업 실패 처리 중 오류: {e}")
