# Qt import 전에 오프스크린 고정(헤드리스/CI 겸용)
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
