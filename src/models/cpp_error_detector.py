"""
C++-specific error detection rules.
Implements 50 rules for syntax, logical, runtime, and semantic errors.
Strongest implementation with comprehensive C++ runtime risk detection.
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
),
    contains_delete_after_new
)


class CppErrorDetector:
    """C++-specific error detector implementing 50 rules."""
    
    def detect(self, code: str) -> Dict:
        """
        Detect errors in C++ code using rule-based approach.
        Returns first high-confidence error found.
        """
        lines = get_lines(code)
        
        # Priority order: Syntax -> Runtime -> Logical -> Semantic -> Warning
        
        # SYNTAX ERRORS
        result = self._check_syntax_errors(code, lines)
        if result and result["has_error"]:
            return result
        
        # RUNTIME ERRORS
        result = self._check_runtime_errors(code, lines)
        if result and result["has_error"]:
            return result
        
        # LOGICAL ERRORS
        result = self._check_logical_errors(code, lines)
        if result and result["has_error"]:
            return result
        
        # SEMANTIC ERRORS
        result = self._check_semantic_errors(code, lines)
        if result and result["has_error"]:
            return result
        
        # WARNINGS
        result = self._check_warnings(code, lines)
        if result and result["has_error"]:
            return result
        
        return make_no_error_result("cpp")
    
    def detect_all(self, code: str) -> Dict:
        """
        Detect ALL errors in C++ code using rule-based approach.
        Returns comprehensive error list with priority sorting.
        """
        lines = get_lines(code)
        all_errors = []
        
        # Initialize variable tracker for context-aware detection
        var_tracker = VariableTracker()
        var_tracker.track_from_code(lines, "cpp")
        
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
        
        return make_multi_error_result(all_errors, "cpp")
    
    def _check_syntax_errors(self, code: str, lines: List[str]) -> Optional[Dict]:
        """Check C++ syntax errors (Rules 1-10)."""
        
        # Rule 1: Unmatched brackets
        result = find_unmatched_brackets(code, "cpp")
        if result:
            return result
        
        # Rule 2: Missing semicolon
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if (stripped and not is_comment_line(line, "cpp") and 
                not stripped.endswith((';', '{', '}', ':', ',', '//', '/*', '*/')) and
                not any(keyword in stripped for keyword in [
                    'if', 'else', 'for', 'while', 'switch', 'case', 'default',
                    'do', 'try', 'catch', 'class', 'struct', 'enum', 'namespace',
                    '#include', '#define', '#ifdef', '#ifndef', '#endif'
                ]) and
                not re.search(r'^\s*\w+\s*\(', stripped)):  # Function declaration
                return make_result(
                    True, "syntax_error", "missing_semicolon", i,
                    "Missing semicolon at end of statement",
                    "cpp", "high", "CPP_SYN_002"
                )
        
        # Rule 3: Missing parenthesis
        for i, line in enumerate(lines, 1):
            open_parens = line.count('(')
            close_parens = line.count(')')
            if open_parens > close_parens:
                return make_result(
                    True, "syntax_error", "missing_parenthesis", i,
                    f"Missing {open_parens - close_parens} closing parenthesis",
                    "cpp", "high", "CPP_SYN_003"
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
                    "cpp", "high", "CPP_SYN_004"
                )
        
        if open_braces > 0:
            return make_result(
                True, "syntax_error", "missing_brace", len(lines),
                f"Missing {open_braces} closing braces",
                "cpp", "high", "CPP_SYN_005"
            )
        
        # Rule 5: Malformed if condition
        for i, line in enumerate(lines, 1):
            if re.search(r'if\s*\([^)]*$', line):
                return make_result(
                    True, "syntax_error", "malformed_if_condition", i,
                    "Incomplete if condition - missing closing parenthesis",
                    "cpp", "high", "CPP_SYN_006"
                )
        
        # Rule 6: Malformed for loop
        for i, line in enumerate(lines, 1):
            if re.search(r'for\s*\([^;]*;[^;]*$', line):
                return make_result(
                    True, "syntax_error", "malformed_for_loop", i,
                    "Incomplete for loop - missing third part of condition",
                    "cpp", "high", "CPP_SYN_007"
                )
        
        # Rule 7: Malformed while condition
        for i, line in enumerate(lines, 1):
            if re.search(r'while\s*\([^)]*$', line):
                return make_result(
                    True, "syntax_error", "malformed_while_condition", i,
                    "Incomplete while condition - missing closing parenthesis",
                    "cpp", "high", "CPP_SYN_008"
                )
        
        # Rule 8: Missing quote
        result = find_missing_quote(code, "cpp")
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
                        "cpp", "high", "CPP_SYN_009"
                    )
        
        # Rule 10: Malformed function definition
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\s+\w+\s*\([^)]*$', line):
                return make_result(
                    True, "syntax_error", "malformed_function_definition", i,
                    "Incomplete function definition - missing closing parenthesis",
                    "cpp", "high", "CPP_SYN_010"
                )
        
        return None
    
    def _check_runtime_errors(self, code: str, lines: List[str]) -> Optional[Dict]:
        """Check C++ runtime error risks (Rules 21-40)."""
        
        # Rule 21: Division by zero risk
        for i, line in enumerate(lines, 1):
            if re.search(r'/\s*0\b', line):
                return make_result(
                    True, "runtime_error", "division_by_zero_risk", i,
                    "Division by zero detected",
                    "cpp", "high", "CPP_RT_001"
                )
        
        # Rule 22: Array out of bounds risk
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\[\s*\w+\s*\+\s*\w+\s*\]', line):
                return make_result(
                    True, "runtime_error", "array_out_of_bounds_risk", i,
                    "Possible array out of bounds access with index calculation",
                    "cpp", "high", "CPP_RT_002"
                )
        
        # Rule 23: Vector out of bounds risk
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\.at\s*\(\s*\w+\s*\+\s*\w+\s*\)', line):
                return make_result(
                    True, "runtime_error", "vector_out_of_bounds_risk", i,
                    "Possible vector out of bounds access with index calculation",
                    "cpp", "high", "CPP_RT_003"
                )
        
        # Rule 24: Null pointer dereference risk
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\s*->\s*\w+', line):
                ptr_name = re.search(r'(\w+)\s*->', line).group(1)
                # Check for null pointer check
                has_null_check = False
                for j in range(max(0, i-3), min(i+3, len(lines))):
                    if re.search(f'{ptr_name}\\s*(==|!=)\\s*(NULL|nullptr|0)', lines[j]):
                        has_null_check = True
                        break
                if not has_null_check:
                    return make_result(
                        True, "runtime_error", "null_pointer_dereference_risk", i,
                        f"Possible null pointer dereference: '{ptr_name}' not checked",
                        "cpp", "high", "CPP_RT_004"
                    )
        
        # Rule 25: Dangling pointer risk
        for i, line in enumerate(lines, 1):
            if re.search(r'delete\s+\w+', line):
                # Check if pointer is used after delete
                ptr_match = re.search(r'delete\s+(\w+)', line)
                if ptr_match:
                    ptr_name = ptr_match.group(1)
                    for j in range(i+1, min(i+10, len(lines))):
                        if re.search(f'{ptr_name}\\s*->', lines[j]) or re.search(f'\\*{ptr_name}', lines[j]):
                            return make_result(
                                True, "runtime_error", "dangling_pointer_risk", j+1,
                                f"Use of pointer '{ptr_name}' after delete",
                                "cpp", "high", "CPP_RT_005"
                            )
        
        # Rule 26: Uninitialized variable use
        declared_vars = {}
        for i, line in enumerate(lines, 1):
            # Track variable declarations
            if re.search(r'\b(?:int|float|double|char|bool|string)\s+(\w+)\s*[;=]', line):
                var_match = re.search(r'\b(?:int|float|double|char|bool|string)\s+(\w+)\s*[;=]', line)
                if var_match and '=' not in line:
                    declared_vars[var_match.group(1)] = i
            
            # Check for uninitialized variable usage
            for var_name, line_num in declared_vars.items():
                if var_name in line and f'{var_name} =' not in line:
                    return make_result(
                        True, "runtime_error", "uninitialized_variable_use", i,
                        f"Variable '{var_name}' used before initialization",
                        "cpp", "medium", "CPP_RT_006"
                    )
        
        # Rule 27: Use after delete risk
        for i, line in enumerate(lines, 1):
            if re.search(r'delete\s+\w+', line):
                ptr_match = re.search(r'delete\s+(\w+)', line)
                if ptr_match:
                    ptr_name = ptr_match.group(1)
                    for j in range(i+1, min(i+5, len(lines))):
                        if ptr_name in lines[j]:
                            return make_result(
                                True, "runtime_error", "use_after_delete_risk", j+1,
                                f"Pointer '{ptr_name}' used after delete",
                                "cpp", "high", "CPP_RT_007"
                            )
        
        # Rule 28: Memory leak risk
        allocated_vars = {}
        for i, line in enumerate(lines, 1):
            # Track new allocations
            if re.search(r'(\w+)\s*=\s*new', line):
                var_match = re.search(r'(\w+)\s*=\s*new', line)
                if var_match:
                    allocated_vars[var_match.group(1)] = i
            
            # Check for missing delete
            for var_name, alloc_line in allocated_vars.items():
                if not contains_delete_after_new(lines, var_name, alloc_line):
                    return make_result(
                        True, "runtime_error", "memory_leak_risk", alloc_line,
                        f"Memory leak risk: '{var_name}' allocated with new but not deleted",
                        "cpp", "medium", "CPP_RT_008"
                    )
        
        # Rule 29: Double delete risk
        deleted_vars = set()
        for i, line in enumerate(lines, 1):
            if re.search(r'delete\s+(\w+)', line):
                var_match = re.search(r'delete\s+(\w+)', line)
                if var_match:
                    var_name = var_match.group(1)
                    if var_name in deleted_vars:
                        return make_result(
                            True, "runtime_error", "double_delete_risk", i,
                            f"Double delete risk: '{var_name}' already deleted",
                            "cpp", "high", "CPP_RT_009"
                        )
                    deleted_vars.add(var_name)
        
        # Rule 30: Invalid iterator risk
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\.end\s*\(\s*\)', line):
                # Check if iterator is being dereferenced
                if re.search(r'\*\w+', line):
                    return make_result(
                        True, "runtime_error", "invalid_iterator_risk", i,
                        "Dereferencing end() iterator",
                        "cpp", "high", "CPP_RT_010"
                    )
        
        # Rule 31: Dereferencing end iterator risk
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\.end\s*\(\s*\)', line):
                # Look ahead for dereferencing
                for j in range(i, min(i+3, len(lines))):
                    if re.search(r'\*\s*\w+', lines[j]):
                        return make_result(
                            True, "runtime_error", "dereferencing_end_iterator_risk", j+1,
                            "Dereferencing end iterator",
                            "cpp", "high", "CPP_RT_011"
                        )
        
        # Rule 32: Stack overflow recursion risk
        func_names = set()
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\s+\w+\s*\([^)]*\)\s*{', line):
                func_name = re.search(r'\w+\s+(\w+)\s*\(', line).group(1)
                func_names.add(func_name)
        
        # Check for recursive calls without base case
        for i, line in enumerate(lines, 1):
            for func_name in func_names:
                if f'{func_name}(' in line:
                    # Simple heuristic - check if there's a base case
                    has_base_case = False
                    for j in range(max(0, i-10), i):
                        if any(keyword in lines[j].lower() for keyword in ['if', 'return', 'base']):
                            has_base_case = True
                            break
                    if not has_base_case:
                        return make_result(
                            True, "runtime_error", "stack_overflow_recursion_risk", i,
                            f"Recursion without base case in function '{func_name}'",
                            "cpp", "medium", "CPP_RT_012"
                        )
        
        # Rule 33: Buffer overflow risk
        for i, line in enumerate(lines, 1):
            if re.search(r'strcpy|strcat|gets|sprintf', line):
                return make_result(
                    True, "runtime_error", "buffer_overflow_risk", i,
                    "Unsafe string function detected - use safer alternatives",
                    "cpp", "high", "CPP_RT_013"
                )
        
        # Rule 34: File not open checked
        file_vars = set()
        for i, line in enumerate(lines, 1):
            if re.search(r'ifstream|ofstream|fstream', line):
                var_match = re.search(r'(\w+)\s*\(', line)
                if var_match:
                    file_vars.add(var_match.group(1))
            
            # Check if file is used without open check
            for var_name in file_vars:
                if f'{var_name}.' in line and 'open' not in line:
                    return make_result(
                        True, "runtime_error", "file_not_open_checked", i,
                        f"File '{var_name}' used without checking if open",
                        "cpp", "medium", "CPP_RT_014"
                    )
        
        # Rule 35: Missing return non-void function
        in_function = False
        has_return = False
        is_void = False
        
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\s+\w+\s*\([^)]*\)\s*{', line):
                func_signature = line
                in_function = True
                has_return = False
                is_void = 'void' in func_signature
            elif re.search(r'^\s*}', line):
                if in_function and not is_void and not has_return:
                    return make_result(
                        True, "runtime_error", "missing_return_non_void_function", i-1,
                        "Missing return statement in non-void function",
                        "cpp", "medium", "CPP_RT_015"
                    )
                in_function = False
            elif in_function and re.search(r'return', line):
                has_return = True
        
        # Rule 36: Integer division warning
        for i, line in enumerate(lines, 1):
            if re.search(r'\bint\s+\w+\s*=\s*\w+\s*/\s*\w+', line):
                return make_result(
                    True, "runtime_error", "integer_division_warning", i,
                    "Integer division - result will be truncated",
                    "cpp", "low", "CPP_RT_016"
                )
        
        # Rule 37: Signed unsigned comparison warning
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\s*<\s*.*size_t|\w+\s*>\s*.*size_t', line):
                return make_result(
                    True, "runtime_error", "signed_unsigned_comparison", i,
                    "Signed/unsigned comparison may give unexpected results",
                    "cpp", "medium", "CPP_RT_017"
                )
        
        # Rule 38: Unsafe C string function warning
        for i, line in enumerate(lines, 1):
            if re.search(r'\b(strcpy|strcat|gets|sprintf|scanf)\s*\(', line):
                return make_result(
                    True, "runtime_error", "unsafe_c_string_function", i,
                    "Unsafe C string function - consider safer alternatives",
                    "cpp", "high", "CPP_RT_018"
                )
        
        # Rule 39: Scanf format mismatch
        for i, line in enumerate(lines, 1):
            if re.search(r'scanf\s*\([^)]*%[^)]*\)', line):
                # Simple heuristic - check if format matches variable types
                if '&' not in line and '%' in line:
                    return make_result(
                        True, "runtime_error", "scanf_format_mismatch", i,
                        "Possible scanf format mismatch - missing & operator",
                        "cpp", "medium", "CPP_RT_019"
                    )
        
        # Rule 40: Array decay confusion warning
        for i, line in enumerate(lines, 1):
            if re.search(r'sizeof\s*\(\s*\w+\s*\)', line):
                var_match = re.search(r'sizeof\s*\(\s*(\w+)\s*\)', line)
                if var_match:
                    var_name = var_match.group(1)
                    # Check if this is a function parameter array
                    for j in range(max(0, i-10), i):
                        if re.search(rf'{var_name}\s*\[\s*\]', lines[j]):
                            return make_result(
                                True, "runtime_error", "array_decay_confusion", i,
                                f"Array decay: sizeof({var_name}) returns pointer size, not array size",
                                "cpp", "medium", "CPP_RT_020"
                            )
        
        return None
    
    def _check_logical_errors(self, code: str, lines: List[str]) -> Optional[Dict]:
        """Check C++ logical errors (Rules 11-20)."""
        
        # Rule 11: Assignment in condition
        for i, line in enumerate(lines, 1):
            if detect_assignment_in_condition(line):
                return make_result(
                    True, "logical_error", "assignment_in_condition", i,
                    "Assignment in condition - did you mean comparison?",
                    "cpp", "high", "CPP_LOG_001"
                )
        
        # Rule 12: Off-by-one errors
        off_by_one = detect_off_by_one_patterns(lines)
        if off_by_one:
            line_num, message = off_by_one
            return make_result(
                True, "logical_error", "off_by_one", line_num,
                message, "cpp", "medium", "CPP_LOG_002"
            )
        
        # Rule 13: Infinite loop
        infinite_loop = detect_infinite_loop_patterns(lines, "cpp")
        if infinite_loop:
            line_num, message = infinite_loop
            return make_result(
                True, "logical_error", "infinite_loop", line_num,
                message, "cpp", "high", "CPP_LOG_003"
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
                            "cpp", "medium", "CPP_LOG_004"
                        )
        
        # Rule 15: Wrong comparison operator
        for i, line in enumerate(lines, 1):
            if re.search(r'=\s*=\s*=', line):  # Too many equals
                return make_result(
                    True, "logical_error", "wrong_comparison_operator", i,
                    "Invalid comparison operator - use == for equality",
                    "cpp", "high", "CPP_LOG_005"
                )
        
        # Rule 16: Wrong accumulator update
        for i, line in enumerate(lines, 1):
            if re.search(r'^\s*\w+\s*=\s*\w+\s*$', line):
                # Check if inside loop
                for j in range(max(0, i-5), i):
                    if 'for ' in lines[j] or 'while ' in lines[j]:
                        return make_result(
                            True, "logical_error", "wrong_accumulator_update", i,
                            "Wrong accumulator update - did you mean '+='?",
                            "cpp", "medium", "CPP_LOG_006"
                        )
        
        # Rule 17: Unreachable branch
        for i, line in enumerate(lines, 1):
            if re.search(r'if\s*\(\s*(true|false)\s*\)', line.lower()):
                return make_result(
                    True, "logical_error", "unreachable_branch", i,
                    "Condition is always true/false - unreachable code",
                    "cpp", "medium", "CPP_LOG_007"
                )
        
        # Rule 18: Duplicate condition
        conditions = {}
        for i, line in enumerate(lines, 1):
            if_match = re.search(r'if\s*\(([^)]+)\)', line)
            if if_match:
                condition = if_match.group(1).strip()
                if condition in conditions:
                    return make_result(
                        True, "logical_error", "duplicate_condition", i,
                        f"Duplicate condition: '{condition}' already checked on line {conditions[condition]}",
                        "cpp", "low", "CPP_LOG_008"
                    )
                conditions[condition] = i
        
        # Rule 19: Suspicious index math
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\[\s*\w+\s*-\s*1\s*\]', line):
                return make_result(
                    True, "logical_error", "suspicious_index_math", i,
                    "Suspicious index math - check for off-by-one error",
                    "cpp", "medium", "CPP_LOG_009"
                )
        
        # Rule 20: Use of magic number
        for i, line in enumerate(lines, 1):
            if re.search(r'\b\d{2,}\b', line):  # Numbers with 2+ digits
                return make_result(
                    True, "logical_error", "use_of_magic_number", i,
                    "Magic number detected - consider using named constant",
                    "cpp", "low", "CPP_LOG_010"
                )
        
        return None
    
    def _check_semantic_errors(self, code: str, lines: List[str]) -> Optional[Dict]:
        """Check C++ semantic errors (Rules 41-50)."""
        
        # Rule 41: Using namespace std warning
        for i, line in enumerate(lines, 1):
            if re.search(r'using\s+namespace\s+std\s*;', line):
                return make_result(
                    True, "semantic_error", "using_namespace_std_warning", i,
                    "Using namespace std in header files - avoid in headers",
                    "cpp", "medium", "CPP_SEM_001"
                )
        
        # Rule 42: Cout debug left in code
        for i, line in enumerate(lines, 1):
            if re.search(r'cout\s*<<', line):
                return make_result(
                    True, "semantic_error", "cout_debug_left_in_code", i,
                    "Debug cout statement left in code",
                    "cpp", "low", "CPP_SEM_002"
                )
        
        # Rule 43: Shadowed variable
        declared_vars = {}
        for i, line in enumerate(lines, 1):
            if re.search(r'\b(?:int|float|double|char|bool|string)\s+(\w+)\s*[;=]', line):
                var_match = re.search(r'\b(?:int|float|double|char|bool|string)\s+(\w+)\s*[;=]', line)
                if var_match:
                    var_name = var_match.group(1)
                    if var_name in declared_vars:
                        return make_result(
                            True, "semantic_error", "shadowed_variable", i,
                            f"Variable '{var_name}' shadows previous declaration on line {declared_vars[var_name]}",
                            "cpp", "medium", "CPP_SEM_003"
                        )
                    declared_vars[var_name] = i
        
        # Rule 44: Pass by value large object warning
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\s+\w+\s*\([^)]*\w+\s*\)', line):
                # Simple heuristic - check for string/vector parameters
                if any(type_name in line for type_name in ['string', 'vector', 'map']):
                    return make_result(
                        True, "semantic_error", "pass_by_value_large_object", i,
                        "Large object passed by value - consider const reference",
                        "cpp", "medium", "CPP_SEM_004"
                    )
        
        # Rule 45: Compare floats directly warning
        for i, line in enumerate(lines, 1):
            if re.search(r'\b(?:float|double)\s+\w+\s*(==|!=)\s*\w+', line):
                return make_result(
                    True, "semantic_error", "compare_floats_directly", i,
                    "Comparing floating point numbers directly - use epsilon comparison",
                    "cpp", "medium", "CPP_SEM_005"
                )
        
        # Rule 46: Switch missing default warning
        in_switch = False
        has_default = False
        for i, line in enumerate(lines, 1):
            if re.search(r'switch\s*\(', line):
                in_switch = True
                has_default = False
            elif re.search(r'^\s*}', line):
                if in_switch and not has_default:
                    return make_result(
                        True, "semantic_error", "switch_missing_default", i-1,
                        "Switch statement missing default case",
                        "cpp", "low", "CPP_SEM_006"
                    )
                in_switch = False
            elif in_switch and re.search(r'default\s*:', line):
                has_default = True
        
        # Rule 47: Fallthrough switch warning
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
                        True, "semantic_error", "fallthrough_switch", i-1,
                        "Fallthrough in switch statement - add 'break' or [[fallthrough]]",
                        "cpp", "medium", "CPP_SEM_007"
                    )
                prev_line_has_case = has_case
        
        # Rule 48: Const possible warning
        for i, line in enumerate(lines, 1):
            if re.search(r'\b(?:int|float|double|char)\s+\w+\s*=\s*\w+\s*;', line):
                # Check if variable is never modified
                var_match = re.search(r'\b(?:int|float|double|char)\s+(\w+)\s*=', line)
                if var_match:
                    var_name = var_match.group(1)
                    is_modified = False
                    for j in range(i+1, len(lines)):
                        if re.search(f'{var_name}\\s*(\\+\\+|--|\\+=|-=|\\*=|/=|=)', lines[j]):
                            is_modified = True
                            break
                    if not is_modified:
                        return make_result(
                            True, "semantic_error", "const_possible", i,
                            f"Variable '{var_name}' could be const",
                            "cpp", "low", "CPP_SEM_008"
                        )
        
        # Rule 49: Reference to temporary risk
        for i, line in enumerate(lines, 1):
            if re.search(r'\w+\s*&\s*\w+\s*=\s*\w+\s*\(', line):
                return make_result(
                    True, "semantic_error", "reference_to_temporary_risk", i,
                    "Reference to temporary object - may be invalid",
                    "cpp", "medium", "CPP_SEM_009"
                )
        
        # Rule 50: Suspicious manual memory management
        new_count = 0
        delete_count = 0
        for i, line in enumerate(lines, 1):
            if re.search(r'new\s+', line):
                new_count += 1
            if re.search(r'delete\s+', line):
                delete_count += 1
        
        if new_count > delete_count + 1:  # Allow some imbalance
            return make_result(
                True, "semantic_error", "suspicious_manual_memory_management", len(lines),
                f"Suspicious memory management: {new_count} new vs {delete_count} delete",
                "cpp", "medium", "CPP_SEM_010"
            )
        
        return None
    
    def _check_warnings(self, code: str, lines: List[str]) -> Optional[Dict]:
        """Check C++ warnings."""
        
        # Mixed tabs and spaces warning
        mixed_indent = detect_mixed_tabs_spaces(lines)
        if mixed_indent:
            line_num, message = mixed_indent
            return make_result(
                True, "warning", "mixed_tabs_spaces", line_num,
                message, "cpp", "low", "CPP_WARN_001"
            )
        
        # Empty condition block warning
        empty_block = detect_empty_condition_block(lines)
        if empty_block:
            line_num, message = empty_block
            return make_result(
                True, "warning", "empty_condition_block", line_num,
                message, "cpp", "low", "CPP_WARN_002"
            )
        
        return None
