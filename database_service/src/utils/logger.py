import logging
import json
from typing import Dict, Any, Optional

class Logger:
    def __init__(self, name, log_file="database.log"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            stream_handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            stream_handler.setFormatter(formatter)
            self.logger.addHandler(stream_handler)

            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def info(self, message):
        self.logger.info("✅ "+message)
    def error(self, message):
        self.logger.error("❌ "+message)
    def debug(self, message):
        self.logger.debug("🔥 "+message)
    def warning(self, message):
        self.logger.warning("⚠️ "+message)

    def log_exception(self, operation: str, exception: Exception, context: Optional[Dict[str, Any]] = None):
        self.error(f"💥 Exception in {operation}: {str(exception)}")
        self.debug(f"🔍 Exception type: {type(exception).__name__}")
        if context:
            context_str = json.dumps(context, ensure_ascii=False)[:300]
            self.debug(f"🔍 Exception context: {context_str}")

        import traceback
        self.debug(f"📚 Stack trace: {traceback.format_exc()}")
