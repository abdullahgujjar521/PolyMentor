"""
Java-specific error detection rules.
Implements 40 rules for syntax, logical, runtime, and semantic errors.
"""

import re
from typing import Dict, Optional, List, Set
from .common_rules import (
    make_result, make_no_error_result, make_error_result, make_multi_error_result,
    get_lines, find_unmatched_brackets, find_missing_quote, contains_break_statement,
    contains_zero_check, contains_null_check, contains_return_statement,
    detect_assignment_in_condition, detect_off_by_one_patterns,
    detect_infinite_loop_patterns, detect_mixed_tabs_spaces, detect_empty_condition_block,
    get_indent_level, is_comment_line, VariableTracker
)


class JavaErrorDetector:
    """Java-specific error detector implementing 40 rules."""
    
    def detect(self, code: str) -> Dict:
        """
        Detect errors in Java code using rule-based approach.
        Returns first high-confidence error found.
        """
        all_errors = self.detect_all(code)
        
        if not all_errors["has_error"]:
            return {
                "has_error": False,
                "error_type": None,
                "subtype": None,
                "line": None,
                "message": "No obvious error detected",
                "language": "java",
                "severity": None,
                "rule_id": None
            }
        
        # Return highest priority error for backward compatibility
        return all_errors["highest_priority_error"]
    
    def detect_all(self, code: str) -> Dict:
        """
        Detect ALL errors in Java code using rule-based approach.
        Returns comprehensive error list with priority sorting.
        """
        lines = get_lines(code)
        all_errors = []
        
        # Initialize variable tracker for context-aware detection
        var_tracker = VariableTracker()
        var_tracker.track_from_code(lines, "java")
        
        # SYNTAX ERRORS
        syntax_errors = self._check_syntax_errors_all(code, lines, var_tracker)
        all_errors.extend(syntax_errors)
        
        # RUNTIME ERRORS
        runtime_errors = self._check_runtime_errors_all(code, lines, var_tracker)
        all_errors.extend(runtime_errors)
        
        # LOGICAL ERRORS
        logical_errors = self._check_logical_errors_all(code, lines, var_tracker)
        all_errors.extend(logical_errors)
        
        # SEMANTIC ERRORS
        semantic_errors = self._check_semantic_errors_all(code, lines, var_tracker)
        all_errors.extend(semantic_errors)
        
        # WARNINGS
        warnings = self._check_warnings_all(code, lines, var_tracker)
        all_errors.extend(warnings)
        
        return make_multi_error_result(all_errors, "java")
    
    def _check_syntax_errors(self, code: str, lines: List[str]) -> Optional[Dict]:
        """Check Java syntax errors (Rules 1-10)."""
        
        # Rule 1: Unmatched brackets
        result = find_unmatched_brackets(code, "java")
        if result:
            return result
        
        # Rule 2: Missing semicolon
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if (stripped and not is_comment_line(line, "java") and 
                not stripped.endswith((';', '{', '}', ':', ',', '//', '/*', '*/')) and
                not any(keyword in stripped for keyword in [
                    'if', 'else', 'for', 'while', 'switch', 'case', 'default',
                    'do', 'try', 'catch', 'finally', 'class', 'interface', 'enum',
                    'import', 'package'
                ]) and
                not re.search(r'^\s*(public|private|protected|static|final|abstract|synchronized|volatile|transient|native)\s+\w+\s+\w+\s*\(', stripped) and
                not re.search(r'^\s*\w+\s+\w+\s*\(', stripped)):  # Method declaration
                return make_result(
                    True, "syntax_error", "missing_semicolon", i,
                    "Missing semicolon at end of statement",
                    "java", "high", "JAVA_SYN_002"
                )
        
        # Rule 3: Missing parenthesis
        for i, line in enumerate(lines, 1):
            open_parens = line.count('(')
            close_parens = line.count(')')
            if open_parens > close_parens:
                return make_result(
                    True, "syntax_error", "missing_parenthesis", i,
                    f"Missing {open_parens - close_parens} closing parenthesis",
                    "java", "high", "JAVA_SYN_003"
                )
        
        # Rule 4: Missing brace
        open_braces = 0
        for i, line in enumerate(lines, 1):
            open_braces += line.count('{')
            open_braces -= line.count('}')
            
            if open_braces < 0:
                return make_result(
                    True, "syntax_error", "missing_brace", i,
                    "Unexpected closing brace",
                    "java", "high", "JAVA_SYN_004"
                )
        
        if open_braces > 0:
            return make_result(
                True, "syntax_error", "missing_brace", len(lines),
                f"Missing {open_braces} closing braces",
                "java", "high", "JAVA_SYN_005"
            )
        
        # Rule 5: Malformed if condition
        for i, line in enumerate(lines, 1):
            if re.search(r'if\s*\([^)]*$', line):
                return make_result(
                    True, "syntax_error", "malformed_if_condition", i,
                    "Incomplete if condition - missing closing parenthesis",
                    "java", "high", "JAVA_SYN_006"
                )
        
        # Rule 6: Malformed for loop
        for i, line in enumerate(lines, 1):
            if re.search(r'for\s*\([^;]*;[^;]*$', line):
                return make_result(
                    True, "syntax_error", "malformed_for_loop", i,
                    "Incomplete for loop - missing third part of condition",
                    "java", "high", "JAVA_SYN_007"
                )
        
        # Rule 7: Missing quote
        result = find_missing_quote(code, "java")
        if result:
            return result
        
        # Rule 8: Else without if
        for i, line in enumerate(lines, 1):
            if re.search(r'^\s*else\s*[:{]', line):
                # Check if there's an if before this
                has_if = False
                for j in range(max(0, i-10), i):
                    if re.search(r'\bif\s*\(', lines[j]):
                        has_if = True
                        break
                if not has_if:
                    return make_result(
                        True, "syntax_error", "else_without_if", i,
                        "Else statement without corresponding if",
                        "java", "high", "JAVA_SYN_008"
                    )
        
        # Rule 9: Malformed method declaration
        for i, line in enumerate(lines, 1):
            if re.search(r'\b(?:public|private|protected|static|final|abstract|synchronized)\s+\w+\s+\w+\s*\([^)]*$', line):
                return make_result(
                    True, "syntax_error", "malformed_method_declaration", i,
                    "Incomplete method declaration - missing closing parenthesis",
                    "java", "high", "JAVA_SYN_009"
                )
        
        # Rule 10: Class structure warning
        class_count = 0
        for i, line in enumerate(lines, 1):
            if re.search(r'\bclass\s+\w+', line):
                class_count += 1
                if class_count > 1:
                    return make_result(
                        True, "syntax_error", "class_structure_warning", i,
                        "Multiple classes in one file - only one public class allowed",
                        "java", "medium", "JAVA_SYN_010"
                    )
        
        return None
    
    def _check_runtime_errors(self, code: str, lines: List[str]) -> Optional[Dict]:
        """Check Java runtime error risks (Rules 21-30)."""
        
        # Rule 21: Division by zero risk
        for i, line in enumerate(lines, 1):
            if re.search(r'/\s*0\b', line):
                return make_result(
                    True, "runtime_error", "division_by_zero_risk", i,
                    "Division by zero detected",
                    "java", "high", "JAVA_RT_001"
                )
        
        # Rule 22: Null pointer risk
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\.\w+\(', line):
                obj_match = re.search(r'(\w+)\.\w+\(', line)
                if obj_match:
                    obj_name = obj_match.group(1)
                    # Check for null check
                    has_null_check = False
                    for j in range(max(0, i-3), min(i+3, len(lines))):
                        if re.search(f'{obj_name}\\s*(==|!=)\\s*null', lines[j]):
                            has_null_check = True
                            break
                    if not has_null_check:
                        return make_result(
                            True, "runtime_error", "null_pointer_risk", i,
                            f"Possible null pointer exception: '{obj_name}' not checked for null",
                            "java", "high", "JAVA_RT_002"
                        )
        
        # Rule 23: Array index out of bounds risk
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\[\s*\w+\s*\+\s*\w+\s*\]', line):
                return make_result(
                    True, "runtime_error", "array_index_out_of_bounds_risk", i,
                    "Possible array index out of bounds with index calculation",
                    "java", "high", "JAVA_RT_003"
                )
        
        # Rule 24: String index out of bounds risk
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\.charAt\s*\(\s*\w+\s*\+\s*\w+\s*\)', line):
                return make_result(
                    True, "runtime_error", "string_index_out_of_bounds_risk", i,
                    "Possible string index out of bounds with index calculation",
                    "java", "high", "JAVA_RT_004"
                )
        
        # Rule 25: Uninitialized variable use
        declared_vars = {}
        for i, line in enumerate(lines, 1):
            # Track variable declarations
            if re.search(r'\b(?:int|float|double|char|boolean|String)\s+(\w+)\s*[;=]', line):
                var_match = re.search(r'\b(?:int|float|double|char|boolean|String)\s+(\w+)\s*[;=]', line)
                if var_match and '=' not in line:
                    declared_vars[var_match.group(1)] = i
            
            # Check for uninitialized variable usage
            for var_name, line_num in declared_vars.items():
                if var_name in line and f'{var_name} =' not in line:
                    return make_result(
                        True, "runtime_error", "uninitialized_variable_use", i,
                        f"Variable '{var_name}' used before initialization",
                        "java", "medium", "JAVA_RT_005"
                    )
        
        # Rule 26: Missing return non-void method
        in_method = False
        has_return = False
        is_void = False
        
        for i, line in enumerate(lines, 1):
            if re.search(r'\b(?:public|private|protected|static)\s+\w+\s+\w+\s*\([^)]*\)\s*{', line):
                method_signature = line
                in_method = True
                has_return = False
                is_void = 'void' in method_signature
            elif re.search(r'^\s*}', line):
                if in_method and not is_void and not has_return:
                    return make_result(
                        True, "runtime_error", "missing_return_non_void_method", i-1,
                        "Missing return statement in non-void method",
                        "java", "medium", "JAVA_RT_006"
                    )
                in_method = False
            elif in_method and re.search(r'return', line):
                has_return = True
        
        # Rule 27: Input parsing risk
        for i, line in enumerate(lines, 1):
            if re.search(r'Integer\.parseInt|Double\.parseDouble|Float\.parseFloat', line):
                # Check for try-catch around parsing
                has_try_catch = False
                for j in range(max(0, i-5), min(i+5, len(lines))):
                    if 'try' in lines[j] and 'catch' in lines[j]:
                        has_try_catch = True
                        break
                if not has_try_catch:
                    return make_result(
                        True, "runtime_error", "input_parsing_risk", i,
                        "Input parsing without try-catch - may throw NumberFormatException",
                        "java", "medium", "JAVA_RT_007"
                    )
        
        # Rule 28: Resource not closed warning
        opened_resources = set()
        for i, line in enumerate(lines, 1):
            if re.search(r'new\s+(FileInputStream|FileOutputStream|BufferedReader|Scanner)', line):
                opened_resources.add(i)
            
            # Check if resource is closed
            if re.search(r'\.close\s*\(', line):
                # Simple heuristic - assume this closes some resource
                if opened_resources:
                    opened_resources.pop()
        
        if opened_resources:
            return make_result(
                True, "runtime_error", "resource_not_closed", opened_resources.pop(),
                "Resource opened but not closed - use try-with-resources",
                "java", "medium", "JAVA_RT_008"
            )
        
        # Rule 29: Concurrent modification risk
        for i, line in enumerate(lines, 1):
            if re.search(r'for\s*\([^)]*\b(\w+)\s*:\s*\w+\)', line):
                collection_name = re.search(r'for\s*\([^)]*\b\w+\s*:\s*(\w+)\)', line).group(1)
                # Look for collection modification
                for j in range(i, min(i+10, len(lines))):
                    if re.search(f'{collection_name}\\.(add|remove|clear)', lines[j]):
                        return make_result(
                            True, "runtime_error", "concurrent_modification_risk", j+1,
                            f"Modifying collection '{collection_name}' during iteration",
                            "java", "medium", "JAVA_RT_009"
                        )
        
        # Rule 30: Class cast risk
        for i, line in enumerate(lines, 1):
            if re.search(r'\(\w+\)\s*\w+', line):
                return make_result(
                    True, "runtime_error", "class_cast_risk", i,
                    "Class cast without type checking - may cause ClassCastException",
                    "java", "medium", "JAVA_RT_010"
                )
        
        return None
    
    def _check_logical_errors(self, code: str, lines: List[str]) -> Optional[Dict]:
        """Check Java logical errors (Rules 11-20)."""
        
        # Rule 11: Assignment in condition
        for i, line in enumerate(lines, 1):
            if detect_assignment_in_condition(line):
                return make_result(
                    True, "logical_error", "assignment_in_condition", i,
                    "Assignment in condition - did you mean comparison?",
                    "java", "high", "JAVA_LOG_001"
                )
        
        # Rule 12: Off-by-one errors
        off_by_one = detect_off_by_one_patterns(lines)
        if off_by_one:
            line_num, message = off_by_one
            return make_result(
                True, "logical_error", "off_by_one", line_num,
                message, "java", "medium", "JAVA_LOG_002"
            )
        
        # Rule 13: Infinite loop
        infinite_loop = detect_infinite_loop_patterns(lines, "java")
        if infinite_loop:
            line_num, message = infinite_loop
            return make_result(
                True, "logical_error", "infinite_loop", line_num,
                message, "java", "high", "JAVA_LOG_003"
            )
        
        # Rule 14: Loop variable not updated
        for i, line in enumerate(lines, 1):
            if re.search(r'while\s*\(\s*\w+\s*\)', line):
                var_match = re.search(r'while\s*\(\s*(\w+)\s*\)', line)
                if var_match:
                    var_name = var_match.group(1)
                    # Check if variable is updated in loop body
                    has_update = False
                    for j in range(i, min(i+10, len(lines))):
                        if re.search(f'{var_name}\\s*(\\+\\+|--|\\+=|-=|\\*=|/=|=)', lines[j]):
                            has_update = True
                            break
                    
                    if not has_update:
                        return make_result(
                            True, "logical_error", "loop_variable_not_updated", i,
                            f"Loop variable '{var_name}' is never updated",
                            "java", "medium", "JAVA_LOG_004"
                        )
        
        # Rule 15: Wrong accumulator update
        for i, line in enumerate(lines, 1):
            if re.search(r'^\s*\w+\s*=\s*\w+\s*$', line):
                # Check if inside loop
                for j in range(max(0, i-5), i):
                    if 'for ' in lines[j] or 'while ' in lines[j]:
                        return make_result(
                            True, "logical_error", "wrong_accumulator_update", i,
                            "Wrong accumulator update - did you mean '+='?",
                            "java", "medium", "JAVA_LOG_005"
                        )
        
        # Rule 16: Duplicate condition
        conditions = {}
        for i, line in enumerate(lines, 1):
            if_match = re.search(r'if\s*\(([^)]+)\)', line)
            if if_match:
                condition = if_match.group(1).strip()
                if condition in conditions:
                    return make_result(
                        True, "logical_error", "duplicate_condition", i,
                        f"Duplicate condition: '{condition}' already checked on line {conditions[condition]}",
                        "java", "low", "JAVA_LOG_006"
                    )
                conditions[condition] = i
        
        # Rule 17: Unreachable branch
        for i, line in enumerate(lines, 1):
            if re.search(r'if\s*\(\s*(true|false)\s*\)', line.lower()):
                return make_result(
                    True, "logical_error", "unreachable_branch", i,
                    "Condition is always true/false - unreachable code",
                    "java", "medium", "JAVA_LOG_007"
                )
        
        # Rule 18: Using equals vs double equals issue
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\s*==\s*"[^"]*"', line):
                return make_result(
                    True, "logical_error", "using_equals_vs_double_equals_issue", i,
                    "Using == for string comparison - use .equals() instead",
                    "java", "high", "JAVA_LOG_008"
                )
        
        # Rule 19: Suspicious null comparison logic
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\s*==\s*null.*\|\|\s*\w+\.', line):
                return make_result(
                    True, "logical_error", "suspicious_null_comparison", i,
                    "Suspicious null comparison - may cause NullPointerException",
                    "java", "medium", "JAVA_LOG_009"
                )
        
        # Rule 20: Wrong length property usage
        for i, line in enumerate(lines, 1):
            if re.search(r'\.length\s*\(\s*\)', line):
                return make_result(
                    True, "logical_error", "wrong_length_property_usage", i,
                    "Wrong usage: .length() is for arrays, .length() for strings - use .size() for collections",
                    "java", "medium", "JAVA_LOG_010"
                )
        
        return None
    
    def _check_semantic_errors(self, code: str, lines: List[str]) -> Optional[Dict]:
        """Check Java semantic errors (Rules 31-40)."""
        
        # Rule 31: String comparison with double equals
        for i, line in enumerate(lines, 1):
            if re.search(r'"\w*"\s*==\s*\w+|\w+\s*==\s*"\w*"', line):
                return make_result(
                    True, "semantic_error", "string_comparison_with_double_equals", i,
                    "String comparison with == - use .equals() method",
                    "java", "high", "JAVA_SEM_001"
                )
        
        # Rule 32: Shadowed variable
        declared_vars = {}
        for i, line in enumerate(lines, 1):
            if re.search(r'\b(?:int|float|double|char|boolean|String)\s+(\w+)\s*[;=]', line):
                var_match = re.search(r'\b(?:int|float|double|char|boolean|String)\s+(\w+)\s*[;=]', line)
                if var_match:
                    var_name = var_match.group(1)
                    if var_name in declared_vars:
                        return make_result(
                            True, "semantic_error", "shadowed_variable", i,
                            f"Variable '{var_name}' shadows previous declaration on line {declared_vars[var_name]}",
                            "java", "medium", "JAVA_SEM_002"
                        )
                    declared_vars[var_name] = i
        
        # Rule 33: Empty catch block warning
        for i, line in enumerate(lines, 1):
            if re.search(r'catch\s*\([^)]*\)\s*{\s*}', line):
                return make_result(
                    True, "semantic_error", "empty_catch_block", i,
                    "Empty catch block - should handle or log exception",
                    "java", "medium", "JAVA_SEM_003"
                )
        
        # Rule 34: Broad exception catch warning
        for i, line in enumerate(lines, 1):
            if re.search(r'catch\s*\(\s*Exception\s+\w+\s*\)', line):
                return make_result(
                    True, "semantic_error", "broad_exception_catch", i,
                    "Catching broad Exception - catch specific exceptions",
                    "java", "medium", "JAVA_SEM_004"
                )
        
        # Rule 35: Duplicate case in switch
        switch_cases = {}
        in_switch = False
        for i, line in enumerate(lines, 1):
            if re.search(r'switch\s*\(', line):
                in_switch = True
                switch_cases = {}
            elif re.search(r'^\s*}', line):
                in_switch = False
            elif in_switch and re.search(r'case\s+([^:]+):', line):
                case_value = re.search(r'case\s+([^:]+):', line).group(1).strip()
                if case_value in switch_cases:
                    return make_result(
                        True, "semantic_error", "duplicate_case_in_switch", i,
                        f"Duplicate case '{case_value}' in switch statement",
                        "java", "medium", "JAVA_SEM_005"
                    )
                switch_cases[case_value] = i
        
        # Rule 36: Switch missing default warning
        has_default = False
        in_switch = False
        for i, line in enumerate(lines, 1):
            if re.search(r'switch\s*\(', line):
                in_switch = True
                has_default = False
            elif re.search(r'^\s*}', line):
                if in_switch and not has_default:
                    return make_result(
                        True, "semantic_error", "switch_missing_default", i-1,
                        "Switch statement missing default case",
                        "java", "low", "JAVA_SEM_006"
                    )
                in_switch = False
            elif in_switch and re.search(r'default\s*:', line):
                has_default = True
        
        # Rule 37: Debug print left in code
        for i, line in enumerate(lines, 1):
            if re.search(r'System\.out\.print|System\.err\.print', line):
                return make_result(
                    True, "semantic_error", "debug_print_left_in_code", i,
                    "Debug print statement left in code",
                    "java", "low", "JAVA_SEM_007"
                )
        
        # Rule 38: Possible autoboxing issue warning
        for i, line in enumerate(lines, 1):
            if re.search(r'Integer|Double|Float|Long|Short|Byte|Character|Boolean', line):
                if re.search(r'\+\s*\w+|\w+\s*\+', line):
                    return make_result(
                        True, "semantic_error", "possible_autoboxing_issue", i,
                        "Possible autoboxing issue with wrapper types - may cause NullPointerException",
                        "java", "medium", "JAVA_SEM_008"
                    )
        
        # Rule 39: Compare floats directly warning
        for i, line in enumerate(lines, 1):
            if re.search(r'\b(?:float|double)\s+\w+\s*(==|!=)\s*\w+', line):
                return make_result(
                    True, "semantic_error", "compare_floats_directly", i,
                    "Comparing floating point numbers directly - use epsilon comparison",
                    "java", "medium", "JAVA_SEM_009"
                )
        
        # Rule 40: Magic number warning
        for i, line in enumerate(lines, 1):
            if re.search(r'\b\d{2,}\b', line):  # Numbers with 2+ digits
                return make_result(
                    True, "semantic_error", "magic_number", i,
                    "Magic number detected - consider using named constant",
                    "java", "low", "JAVA_SEM_010"
                )
        
        return None
    
    def _check_warnings(self, code: str, lines: List[str]) -> Optional[Dict]:
        """Check Java warnings."""
        
        # Mixed tabs and spaces warning
        mixed_indent = detect_mixed_tabs_spaces(lines)
        if mixed_indent:
            line_num, message = mixed_indent
            return make_result(
                True, "warning", "mixed_tabs_spaces", line_num,
                message, "java", "low", "JAVA_WARN_001"
            )
        
        # Empty condition block warning
        empty_block = detect_empty_condition_block(lines)
        if empty_block:
            line_num, message = empty_block
            return make_result(
                True, "warning", "empty_condition_block", line_num,
                message, "java", "low", "JAVA_WARN_002"
            )
        
        return None
