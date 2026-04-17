"""
JavaScript-specific error detection rules.
Implements 35 rules for syntax, logical, runtime, and semantic errors.
"""

import re
from typing import Dict, Optional, List
from .common_rules import (
    make_result, make_no_error_result, make_error_result, make_multi_error_result,
    get_lines, find_unmatched_brackets, find_missing_quote, contains_break_statement,
    contains_zero_check, contains_null_check, contains_return_statement,
    detect_assignment_in_condition, detect_off_by_one_patterns,
    detect_infinite_loop_patterns, detect_mixed_tabs_spaces, detect_empty_condition_block,
    get_indent_level, is_comment_line, VariableTracker
)


class JavaScriptErrorDetector:
    """JavaScript-specific error detector implementing 35 rules."""
    
    def detect(self, code: str) -> Dict:
        """
        Detect errors in JavaScript code using rule-based approach.
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
                "language": "javascript",
                "severity": None,
                "rule_id": None
            }
        
        # Return highest priority error for backward compatibility
        return all_errors["highest_priority_error"]
    
    def detect_all(self, code: str) -> Dict:
        """
        Detect ALL errors in JavaScript code using rule-based approach.
        Returns comprehensive error list with priority sorting.
        """
        lines = get_lines(code)
        all_errors = []
        
        # Initialize variable tracker for context-aware detection
        var_tracker = VariableTracker()
        var_tracker.track_from_code(lines, "javascript")
        
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
        
        return make_multi_error_result(all_errors, "javascript")
    
    def _check_syntax_errors(self, code: str, lines: List[str]) -> Optional[Dict]:
        """Check JavaScript syntax errors (Rules 1-10)."""
        
        # Rule 1: Unmatched brackets
        result = find_unmatched_brackets(code, "javascript")
        if result:
            return result
        
        # Rule 2: Missing semicolon warning
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if (stripped and not is_comment_line(line, "javascript") and 
                not stripped.endswith(('{', '}', ';', ':', ',', '(', ')')) and
                not any(keyword in stripped for keyword in ['if', 'while', 'for', 'function', 'else', 'try', 'catch', 'finally'])):
                # Only warn for statements that typically need semicolons
                if re.search(r'^\s*[a-zA-Z_$][a-zA-Z0-9_$]*\s*[=;]', stripped) or \
                   re.search(r'^\s*return\s+', stripped) or \
                   re.search(r'^\s*break\s*$', stripped) or \
                   re.search(r'^\s*continue\s*$', stripped):
                    return make_result(
                        True, "syntax_error", "missing_semicolon", i,
                        "Missing semicolon at end of statement",
                        "javascript", "medium", "JS_SYN_002"
                    )
        
        # Rule 3: Malformed if condition
        for i, line in enumerate(lines, 1):
            if re.search(r'if\s*\([^)]*$', line):
                return make_result(
                    True, "syntax_error", "malformed_if_condition", i,
                    "Incomplete if condition - missing closing parenthesis",
                    "javascript", "high", "JS_SYN_003"
                )
        
        # Rule 4: Malformed for loop structure
        for i, line in enumerate(lines, 1):
            if re.search(r'for\s*\([^;]*;[^;]*$', line):
                return make_result(
                    True, "syntax_error", "malformed_for_loop", i,
                    "Incomplete for loop - missing third part of condition",
                    "javascript", "high", "JS_SYN_004"
                )
        
        # Rule 5: Missing closing parenthesis
        for i, line in enumerate(lines, 1):
            open_parens = line.count('(')
            close_parens = line.count(')')
            if open_parens > close_parens:
                return make_result(
                    True, "syntax_error", "missing_closing_paren", i,
                    f"Missing {open_parens - close_parens} closing parenthesis",
                    "javascript", "high", "JS_SYN_005"
                )
        
        # Rule 6: Missing closing brace
        open_braces = 0
        for i, line in enumerate(lines, 1):
            open_braces += line.count('{')
            open_braces -= line.count('}')
            
            if open_braces < 0:
                return make_result(
                    True, "syntax_error", "missing_closing_brace", i,
                    "Unexpected closing brace",
                    "javascript", "high", "JS_SYN_006"
                )
        
        if open_braces > 0:
            return make_result(
                True, "syntax_error", "missing_closing_brace", len(lines),
                f"Missing {open_braces} closing braces",
                "javascript", "high", "JS_SYN_007"
            )
        
        # Rule 7: Invalid function declaration
        for i, line in enumerate(lines, 1):
            if re.search(r'function\s+\w+\s*\([^)]*$', line):
                return make_result(
                    True, "syntax_error", "invalid_function_declaration", i,
                    "Incomplete function declaration - missing closing parenthesis",
                    "javascript", "high", "JS_SYN_008"
                )
        
        # Rule 8: Missing quote
        result = find_missing_quote(code, "javascript")
        if result:
            return result
        
        # Rule 9: Else without if
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
                        "javascript", "high", "JS_SYN_009"
                    )
        
        # Rule 10: Return outside function
        in_function = False
        for i, line in enumerate(lines, 1):
            if re.search(r'function\s+\w+\s*\(', line) or re.search(r'\w+\s*:\s*function\s*\(', line):
                in_function = True
            elif re.search(r'^\s*}', line):
                in_function = False
            elif re.search(r'return\s+', line) and not in_function:
                return make_result(
                    True, "syntax_error", "return_outside_function", i,
                    "Return statement outside function",
                    "javascript", "high", "JS_SYN_010"
                )
        
        return None
    
    def _check_runtime_errors(self, code: str, lines: List[str]) -> Optional[Dict]:
        """Check JavaScript runtime error risks (Rules 21-29)."""
        
        # Rule 21: Division by zero risk
        for i, line in enumerate(lines, 1):
            if re.search(r'/\s*0\b', line):
                return make_result(
                    True, "runtime_error", "division_by_zero_risk", i,
                    "Division by zero detected",
                    "javascript", "high", "JS_RT_001"
                )
        
        # Rule 22: Undefined variable risk
        declared_vars = set()
        for i, line in enumerate(lines, 1):
            # Track variable declarations
            if re.search(r'\b(?:var|let|const)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)', line):
                var_match = re.search(r'\b(?:var|let|const)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)', line)
                if var_match:
                    declared_vars.add(var_match.group(1))
            
            # Check for undefined variable usage
            if re.search(r'\b([a-zA-Z_$][a-zA-Z0-9_$]*)\b', line):
                for match in re.finditer(r'\b([a-zA-Z_$][a-zA-Z0-9_$]*)\b', line):
                    var_name = match.group(1)
                    if (var_name not in declared_vars and 
                        var_name not in ['console', 'document', 'window', 'Math', 'Array', 'Object', 'String', 'Number', 'Boolean', 'Date', 'RegExp', 'JSON', 'parseInt', 'parseFloat', 'isNaN', 'undefined', 'null', 'true', 'false'] and
                        not re.search(r'\b(?:var|let|const|function)\s+' + re.escape(var_name), line)):
                        return make_result(
                            True, "runtime_error", "undefined_variable_risk", i,
                            f"Variable '{var_name}' may be undefined",
                            "javascript", "medium", "JS_RT_002"
                        )
        
        # Rule 23: Null or undefined property access
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\.\w+', line):
                # Simple heuristic - check if object might be null/undefined
                obj_match = re.search(r'(\w+)\.\w+', line)
                if obj_match:
                    obj_name = obj_match.group(1)
                    # Check if null/undefined check exists
                    has_check = False
                    for j in range(max(0, i-3), min(i+3, len(lines))):
                        if re.search(f'{obj_name}\\s*(===|!==|==|!=)\\s*(null|undefined)', lines[j]):
                            has_check = True
                            break
                    if not has_check:
                        return make_result(
                            True, "runtime_error", "null_or_undefined_property_access", i,
                            f"Possible null/undefined property access on '{obj_name}'",
                            "javascript", "medium", "JS_RT_003"
                        )
        
        # Rule 24: Out of bounds array access risk
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\[\s*\w+\s*\+\s*\w+\s*\]', line):
                return make_result(
                    True, "runtime_error", "out_of_bounds_array_access_risk", i,
                    "Possible out of bounds array access with index calculation",
                    "javascript", "medium", "JS_RT_004"
                )
        
        # Rule 25: parseInt without radix
        for i, line in enumerate(lines, 1):
            if re.search(r'parseInt\s*\([^)]*\)', line) and 'radix' not in line:
                return make_result(
                    True, "runtime_error", "parseInt_without_radix", i,
                    "parseInt() should include radix parameter",
                    "javascript", "low", "JS_RT_005"
                )
        
        # Rule 26: Async without await
        async_functions = set()
        for i, line in enumerate(lines, 1):
            if re.search(r'async\s+function', line):
                async_functions.add(i)
            elif re.search(r'await\s+', line):
                # Check if inside async function
                in_async = False
                for j in range(max(0, i-20), i):
                    if j in async_functions:
                        in_async = True
                        break
                if not in_async:
                    return make_result(
                        True, "runtime_error", "async_without_await", i,
                        "await used outside async function",
                        "javascript", "high", "JS_RT_006"
                    )
        
        # Rule 27: Promise without catch
        promise_chains = []
        for i, line in enumerate(lines, 1):
            if re.search(r'\.then\s*\(', line):
                promise_chains.append(i)
            elif re.search(r'\.catch\s*\(', line):
                promise_chains = []  # Chain has catch
            elif re.search(r';', line) and promise_chains:
                # Promise chain ended without catch
                return make_result(
                    True, "runtime_error", "promise_without_catch", promise_chains[0],
                    "Promise chain without error handling (catch)",
                    "javascript", "medium", "JS_RT_007"
                )
        
        # Rule 28: Possible type coercion bug
        for i, line in enumerate(lines, 1):
            if re.search(r'[=!]==\s*[0-9]', line):
                return make_result(
                    True, "runtime_error", "possible_type_coercion_bug", i,
                    "Possible type coercion - use strict equality (===/!==)",
                    "javascript", "medium", "JS_RT_008"
                )
        
        # Rule 29: Calling non-function risk
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\s*\(', line):
                func_match = re.search(r'(\w+)\s*\(', line)
                if func_match:
                    func_name = func_match.group(1)
                    # Check if it's a known non-function
                    if func_name in ['length', 'prototype', 'constructor', 'name']:
                        return make_result(
                            True, "runtime_error", "calling_non_function_risk", i,
                            f"Attempting to call non-function '{func_name}'",
                            "javascript", "high", "JS_RT_009"
                        )
        
        return None
    
    def _check_logical_errors(self, code: str, lines: List[str]) -> Optional[Dict]:
        """Check JavaScript logical errors (Rules 11-20)."""
        
        # Rule 11: Assignment in condition
        for i, line in enumerate(lines, 1):
            if detect_assignment_in_condition(line):
                return make_result(
                    True, "logical_error", "assignment_in_condition", i,
                    "Assignment in condition - did you mean comparison?",
                    "javascript", "high", "JS_LOG_001"
                )
        
        # Rule 12: Loose equality warning
        for i, line in enumerate(lines, 1):
            if re.search(r'==\s*[^=]', line) and '===' not in line:
                return make_result(
                    True, "logical_error", "loose_equality_warning", i,
                    "Using loose equality (==) - consider strict equality (===)",
                    "javascript", "medium", "JS_LOG_002"
                )
        
        # Rule 13: Off-by-one errors
        off_by_one = detect_off_by_one_patterns(lines)
        if off_by_one:
            line_num, message = off_by_one
            return make_result(
                True, "logical_error", "off_by_one", line_num,
                message, "javascript", "medium", "JS_LOG_003"
            )
        
        # Rule 14: Infinite loop
        infinite_loop = detect_infinite_loop_patterns(lines, "javascript")
        if infinite_loop:
            line_num, message = infinite_loop
            return make_result(
                True, "logical_error", "infinite_loop", line_num,
                message, "javascript", "high", "JS_LOG_004"
            )
        
        # Rule 15: Wrong length usage
        for i, line in enumerate(lines, 1):
            if re.search(r'\.length\s*\+\s*1', line):
                return make_result(
                    True, "logical_error", "wrong_length_usage", i,
                    "Using .length + 1 may cause out-of-bounds access",
                    "javascript", "medium", "JS_LOG_005"
                )
        
        # Rule 16: Unreachable branch
        for i, line in enumerate(lines, 1):
            if re.search(r'if\s*\(\s*(true|false)\s*\)', line.lower()):
                return make_result(
                    True, "logical_error", "unreachable_branch", i,
                    "Condition is always true/false - unreachable code",
                    "javascript", "medium", "JS_LOG_006"
                )
        
        # Rule 17: Duplicate condition
        conditions = {}
        for i, line in enumerate(lines, 1):
            if_match = re.search(r'if\s*\(([^)]+)\)', line)
            if if_match:
                condition = if_match.group(1).strip()
                if condition in conditions:
                    return make_result(
                        True, "logical_error", "duplicate_condition", i,
                        f"Duplicate condition: '{condition}' already checked on line {conditions[condition]}",
                        "javascript", "low", "JS_LOG_007"
                    )
                conditions[condition] = i
        
        # Rule 18: Wrong accumulator update
        for i, line in enumerate(lines, 1):
            if re.search(r'^\s*\w+\s*=\s*\w+\s*$', line):
                # Check if inside loop
                for j in range(max(0, i-5), i):
                    if 'for ' in lines[j] or 'while ' in lines[j]:
                        return make_result(
                            True, "logical_error", "wrong_accumulator_update", i,
                            "Wrong accumulator update - did you mean '+='?",
                            "javascript", "medium", "JS_LOG_008"
                        )
        
        # Rule 19: Mutation during iteration
        for i, line in enumerate(lines, 1):
            if re.search(r'for\s*\([^)]*\b(\w+)\s+in\s+\w+\)', line):
                array_name = re.search(r'for\s*\([^)]*\b(\w+)\s+in\s+(\w+)\)', line).group(2)
                # Look for array modification
                for j in range(i, min(i+10, len(lines))):
                    if re.search(f'{array_name}\\.(push|pop|shift|unshift|splice|sort|reverse)', lines[j]):
                        return make_result(
                            True, "logical_error", "mutation_during_iteration", j+1,
                            f"Modifying array '{array_name}' during iteration",
                            "javascript", "medium", "JS_LOG_009"
                        )
        
        # Rule 20: Suspicious negation logic
        for i, line in enumerate(lines, 1):
            if re.search(r'!\s*!\s*\w+', line):
                return make_result(
                    True, "logical_error", "suspicious_negation_logic", i,
                    "Double negation (!!) - consider using Boolean() instead",
                    "javascript", "low", "JS_LOG_010"
                )
        
        return None
    
    def _check_semantic_errors(self, code: str, lines: List[str]) -> Optional[Dict]:
        """Check JavaScript semantic errors (Rules 30-35)."""
        
        # Rule 30: var usage warning
        for i, line in enumerate(lines, 1):
            if re.search(r'\bvar\s+', line):
                return make_result(
                    True, "semantic_error", "var_usage_warning", i,
                    "Using 'var' - prefer 'let' or 'const'",
                    "javascript", "low", "JS_SEM_001"
                )
        
        # Rule 31: console.log left in code
        for i, line in enumerate(lines, 1):
            if re.search(r'console\.log', line):
                return make_result(
                    True, "semantic_error", "console_log_left_in_code", i,
                    "console.log statement left in code",
                    "javascript", "low", "JS_SEM_002"
                )
        
        # Rule 32: Duplicate case in switch
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
                        "javascript", "medium", "JS_SEM_003"
                    )
                switch_cases[case_value] = i
        
        # Rule 33: Missing default in switch
        has_default = False
        in_switch = False
        for i, line in enumerate(lines, 1):
            if re.search(r'switch\s*\(', line):
                in_switch = True
                has_default = False
            elif re.search(r'^\s*}', line):
                if in_switch and not has_default:
                    return make_result(
                        True, "semantic_error", "missing_default_in_switch", i-1,
                        "Switch statement missing default case",
                        "javascript", "low", "JS_SEM_004"
                    )
                in_switch = False
            elif in_switch and re.search(r'default\s*:', line):
                has_default = True
        
        # Rule 34: Fallthrough in switch
        in_switch = False
        prev_line_has_case = False
        for i, line in enumerate(lines, 1):
            if re.search(r'switch\s*\(', line):
                in_switch = True
                prev_line_has_case = False
            elif re.search(r'^\s*}', line):
                in_switch = False
            elif in_switch:
                has_case = bool(re.search(r'case\s+', line))
                has_break = bool(re.search(r'break\s*;', line))
                
                if prev_line_has_case and not has_break and has_case:
                    return make_result(
                        True, "semantic_error", "fallthrough_in_switch", i-1,
                        "Fallthrough in switch statement - add 'break' or comment",
                        "javascript", "medium", "JS_SEM_005"
                    )
                prev_line_has_case = has_case
        
        # Rule 35: Shadowed variable
        declared_vars = {}
        for i, line in enumerate(lines, 1):
            if re.search(r'\b(?:let|const|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)', line):
                var_match = re.search(r'\b(?:let|const|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)', line)
                if var_match:
                    var_name = var_match.group(1)
                    if var_name in declared_vars:
                        return make_result(
                            True, "semantic_error", "shadowed_variable", i,
                            f"Variable '{var_name}' shadows previous declaration on line {declared_vars[var_name]}",
                            "javascript", "medium", "JS_SEM_006"
                        )
                    declared_vars[var_name] = i
        
        return None
    
    def _check_warnings(self, code: str, lines: List[str]) -> Optional[Dict]:
        """Check JavaScript warnings."""
        
        # Mixed tabs and spaces warning
        mixed_indent = detect_mixed_tabs_spaces(lines)
        if mixed_indent:
            line_num, message = mixed_indent
            return make_result(
                True, "warning", "mixed_tabs_spaces", line_num,
                message, "javascript", "low", "JS_WARN_001"
            )
        
        # Empty condition block warning
        empty_block = detect_empty_condition_block(lines)
        if empty_block:
            line_num, message = empty_block
            return make_result(
                True, "warning", "empty_condition_block", line_num,
                message, "javascript", "low", "JS_WARN_002"
            )
        
        return None
