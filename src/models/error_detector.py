"""
Error Detection Module for PolyMentor AI Coding Assistant

A rule-based error detection system that analyzes code in multiple languages
and detects syntax errors, logical errors, runtime errors, semantic errors, and warnings.
"""

from .common_rules import normalize_language
from .python_error_detector import PythonErrorDetector
from .javascript_error_detector import JavaScriptErrorDetector
from .cpp_error_detector import CppErrorDetector
from .java_error_detector import JavaErrorDetector


class ErrorDetector:
    """
    Main router for language-specific error detectors.
    
    Supports: Python, JavaScript, Java, C++
    Detects: Syntax errors, Logical errors, Runtime errors, Semantic errors, Warnings
    """
    
    def __init__(self):
        """Initialize language-specific detectors."""
        from .python_error_detector import PythonErrorDetector
        from .javascript_error_detector import JavaScriptErrorDetector
        from .cpp_error_detector import CppErrorDetector
        from .java_error_detector import JavaErrorDetector
        
        self.python_detector = PythonErrorDetector()
        self.javascript_detector = JavaScriptErrorDetector()
        self.cpp_detector = CppErrorDetector()
        self.java_detector = JavaErrorDetector()
    
    def detect(self, code: str, language: str) -> dict:
        """
        Main method to detect errors in code.
        Returns first high-confidence error found (backward compatibility).
        """
        all_errors = self.detect_all(code, language)
        
        if not all_errors["has_error"]:
            return {
                "has_error": False,
                "error_type": None,
                "subtype": None,
                "line": None,
                "message": "No obvious error detected",
                "language": language,
                "severity": None,
                "rule_id": None
            }
        
        # Return highest priority error for backward compatibility
        return all_errors["highest_priority_error"]
    
    def detect_all(self, code: str, language: str) -> dict:
        """
        Detect ALL errors in code using rule-based approach.
        Returns comprehensive error list with priority sorting.
        """
        language = language.lower().strip()
        
        # Route to appropriate language detector
        if language in ['python', 'py']:
            return self.python_detector.detect_all(code)
        elif language in ['javascript', 'js']:
            return self.javascript_detector.detect_all(code)
        elif language in ['c++', 'cpp', 'cc']:
            return self.cpp_detector.detect_all(code)
        elif language in ['java']:
            return self.java_detector.detect_all(code)
        else:
            return {
                "has_error": False,
                "errors": [],
                "language": language,
                "total_errors": 0,
                "high_priority_count": 0,
                "highest_priority_error": None
            }
