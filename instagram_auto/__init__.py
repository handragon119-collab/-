"""인스타그램 AI 자동 업로드 패키지.

주제(topic)를 입력하면:
  1. Claude가 캡션과 해시태그를 작성하고
  2. AI가 이미지를 생성하며
  3. 인스타그램에 자동으로 업로드합니다.
"""

from .config import Config
from .pipeline import Pipeline, PostResult

__all__ = ["Config", "Pipeline", "PostResult"]
__version__ = "0.1.0"
