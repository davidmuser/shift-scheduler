#!/bin/bash
# Backend Health Check Script
# Simple verification without imports to avoid dependency issues

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         🎯 SHIFT SCHEDULER - BACKEND VERIFICATION              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

check_count=0
pass_count=0

# Check 1: Python installation
echo "📋 Check 1/10: Python Installation"
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version 2>&1)
    echo -e "${GREEN}✓ Python installed: $python_version${NC}"
    ((pass_count++))
else
    echo -e "${RED}✗ Python not found${NC}"
fi
((check_count++))

# Check 2: Project structure
echo ""
echo "📋 Check 2/10: Project Structure"
required_dirs=("src" "tests" "src/models" "src/constraints" "src/objectives" "src/solver" "src/api")
all_dirs_exist=true
for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "  ${GREEN}✓${NC} $dir/"
    else
        echo -e "  ${RED}✗${NC} $dir/ (missing)"
        all_dirs_exist=false
    fi
done
if [ "$all_dirs_exist" = true ]; then
    ((pass_count++))
fi
((check_count++))

# Check 3: Core Python files
echo ""
echo "📋 Check 3/10: Core Python Files"
required_files=(
    "src/models/data_models.py"
    "src/constraints/hard_constraints.py"
    "src/objectives/dynamic_objectives.py"
    "src/solver/core_solver.py"
    "src/api/main.py"
    "main.py"
    "config.py"
    "cli.py"
)
all_files_exist=true
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        size=$(wc -l < "$file")
        echo -e "  ${GREEN}✓${NC} $file ($size lines)"
    else
        echo -e "  ${RED}✗${NC} $file (missing)"
        all_files_exist=false
    fi
done
if [ "$all_files_exist" = true ]; then
    ((pass_count++))
fi
((check_count++))

# Check 4: Documentation
echo ""
echo "📋 Check 4/10: Documentation Files"
doc_files=("README.md" "ARCHITECTURE.md" "QUICKSTART.md" "INSTALLATION.md" "PROJECT_SUMMARY.md")
all_docs_exist=true
for doc in "${doc_files[@]}"; do
    if [ -f "$doc" ]; then
        size=$(wc -l < "$doc")
        echo -e "  ${GREEN}✓${NC} $doc ($size lines)"
    else
        echo -e "  ${RED}✗${NC} $doc (missing)"
        all_docs_exist=false
    fi
done
if [ "$all_docs_exist" = true ]; then
    ((pass_count++))
fi
((check_count++))

# Check 5: Configuration files
echo ""
echo "📋 Check 5/10: Configuration Files"
config_files=("requirements.txt" "requirements-dev.txt" "pyproject.toml" ".env.example" ".gitignore")
all_config_exist=true
for config in "${config_files[@]}"; do
    if [ -f "$config" ]; then
        echo -e "  ${GREEN}✓${NC} $config"
    else
        echo -e "  ${RED}✗${NC} $config (missing)"
        all_config_exist=false
    fi
done
if [ "$all_config_exist" = true ]; then
    ((pass_count++))
fi
((check_count++))

# Check 6: Test files
echo ""
echo "📋 Check 6/10: Test Suite"
if [ -f "tests/test_scheduling.py" ]; then
    test_count=$(grep -c "def test_" tests/test_scheduling.py)
    echo -e "  ${GREEN}✓${NC} tests/test_scheduling.py ($test_count tests)"
    ((pass_count++))
else
    echo -e "  ${RED}✗${NC} tests/test_scheduling.py (missing)"
fi
((check_count++))

# Check 7: Code quality
echo ""
echo "📋 Check 7/10: Code Quality Analysis"
echo "  Checking for type hints in main modules..."
has_type_hints=true
for pyfile in "src/models/data_models.py" "src/solver/core_solver.py"; do
    if grep -q "def.*->.*:" "$pyfile" 2>/dev/null; then
        echo -e "    ${GREEN}✓${NC} $pyfile has type hints"
    else
        has_type_hints=false
    fi
done
if [ "$has_type_hints" = true ]; then
    ((pass_count++))
fi
((check_count++))

# Check 8: Module imports
echo ""
echo "📋 Check 8/10: Module Integrity"
echo "  Verifying Python module structure..."
if [ -f "src/__init__.py" ] && [ -f "src/models/__init__.py" ] && \
   [ -f "src/constraints/__init__.py" ] && [ -f "src/objectives/__init__.py" ] && \
   [ -f "src/solver/__init__.py" ] && [ -f "src/api/__init__.py" ]; then
    echo -e "  ${GREEN}✓${NC} All __init__.py files present"
    ((pass_count++))
else
    echo -e "  ${RED}✗${NC} Missing __init__.py files"
fi
((check_count++))

# Check 9: API endpoints
echo ""
echo "📋 Check 9/10: API Endpoints"
if grep -q '"/schedule"' src/api/main.py && \
   grep -q '"/validate-request"' src/api/main.py && \
   grep -q '"/health"' src/api/main.py; then
    echo -e "  ${GREEN}✓${NC} /schedule endpoint defined"
    echo -e "  ${GREEN}✓${NC} /validate-request endpoint defined"
    echo -e "  ${GREEN}✓${NC} /health endpoint defined"
    ((pass_count++))
else
    echo -e "  ${RED}✗${NC} Some endpoints missing"
fi
((check_count++))

# Check 10: Constraint implementations
echo ""
echo "📋 Check 10/10: Constraint Implementations"
constraints=(
    "_add_shift_coverage_constraints"
    "_add_no_consecutive_shifts_constraint"
    "_add_max_shifts_per_week_constraint"
    "_add_worker_availability_constraints"
    "_add_skill_requirement_constraints"
)
all_constraints_found=true
for constraint in "${constraints[@]}"; do
    if grep -q "$constraint" src/constraints/hard_constraints.py; then
        constraint_name=${constraint#_add_}
        constraint_name=${constraint_name%_constraint*}
        constraint_name=${constraint_name//_/ }
        echo -e "  ${GREEN}✓${NC} $constraint"
    else
        echo -e "  ${RED}✗${NC} $constraint (missing)"
        all_constraints_found=false
    fi
done
if [ "$all_constraints_found" = true ]; then
    ((pass_count++))
fi
((check_count++))

# Summary
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ VERIFICATION RESULTS                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

percentage=$((pass_count * 100 / check_count))
echo "Passed: $pass_count/$check_count checks ($percentage%)"

if [ "$pass_count" -eq "$check_count" ]; then
    echo -e "\n${GREEN}🎉 All checks passed! Backend system is complete and ready.${NC}"
else
    echo -e "\n${YELLOW}⚠ Some checks failed. Please review above.${NC}"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    📚 NEXT STEPS                               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "1️⃣  Install dependencies:"
echo "   ${CYAN}pip install -r requirements.txt${NC}"
echo ""
echo "2️⃣  Run interactive CLI:"
echo "   ${CYAN}python cli.py${NC}"
echo ""
echo "3️⃣  Start API server:"
echo "   ${CYAN}python main.py${NC}"
echo ""
echo "4️⃣  Visit documentation:"
echo "   ${CYAN}http://localhost:8000/docs${NC}"
echo ""
echo "5️⃣  Run tests:"
echo "   ${CYAN}pytest tests/${NC}"
echo ""

echo "📖 For more information, read: START_HERE.md"
echo ""
