#!/bin/bash

# YunMin-EfficientData Environment Setup Script
# This script sets up the Python environment and installs dependencies

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check if Python is available
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD=python3
    elif command -v python &> /dev/null; then
        PYTHON_CMD=python
    else
        echo "Error: Python not found. Please install Python 3.8 or higher."
        exit 1
    fi

    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || [ "$PYTHON_MAJOR" -eq 3 -a "$PYTHON_MINOR" -lt 8 ]; then
        echo "Error: Python 3.8 or higher required. Found: $PYTHON_VERSION"
        exit 1
    fi

    log_message "Python $PYTHON_VERSION found"
}

# Create virtual environment
create_venv() {
    local venv_path="$PROJECT_ROOT/venv"

    if [ -d "$venv_path" ]; then
        log_message "Virtual environment already exists at $venv_path"
        read -p "Do you want to recreate it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$venv_path"
        else
            return 0
        fi
    fi

    log_message "Creating virtual environment..."
    $PYTHON_CMD -m venv "$venv_path"

    log_message "Virtual environment created at $venv_path"
}

# Activate virtual environment
activate_venv() {
    local venv_path="$PROJECT_ROOT/venv"

    if [ -f "$venv_path/bin/activate" ]; then
        source "$venv_path/bin/activate"
        log_message "Virtual environment activated"
    elif [ -f "$venv_path/Scripts/activate" ]; then
        source "$venv_path/Scripts/activate"
        log_message "Virtual environment activated (Windows)"
    else
        echo "Error: Could not find virtual environment activation script"
        exit 1
    fi
}

# Install dependencies
install_dependencies() {
    log_message "Upgrading pip..."
    pip install --upgrade pip

    log_message "Installing dependencies from requirements.txt..."
    pip install -r "$PROJECT_ROOT/requirements.txt"

    log_message "Dependencies installed successfully"
}

# Install Korean language support
install_korean_support() {
    log_message "Installing Korean language support..."

    # Install MeCab-ko dictionary (if not exists)
    if ! python -c "import mecab" 2>/dev/null; then
        log_message "Installing MeCab-ko for Korean tokenization..."

        # Try different installation methods
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y mecab mecab-ko mecab-ko-dic
        elif command -v yum &> /dev/null; then
            sudo yum install -y mecab mecab-ko mecab-ko-dic
        elif command -v brew &> /dev/null; then
            brew install mecab mecab-ko mecab-ko-dic
        else
            log_message "Warning: Could not install MeCab-ko automatically. Please install manually."
        fi
    fi

    log_message "Korean language support setup complete"
}

# Create necessary directories
create_directories() {
    log_message "Creating project directories..."

    local dirs=(
        "data/raw"
        "data/dedup_ready"
        "data/deduped"
        "data/parquet"
        "models/base"
        "models/merged"
        "logs"
        "results"
        "cache"
    )

    for dir in "${dirs[@]}"; do
        mkdir -p "$PROJECT_ROOT/$dir"
    done

    log_message "Project directories created"
}

# Create .gitignore if it doesn't exist
create_gitignore() {
    local gitignore_path="$PROJECT_ROOT/.gitignore"

    if [ ! -f "$gitignore_path" ]; then
        log_message "Creating .gitignore..."

        cat > "$gitignore_path" << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Jupyter Notebook
.ipynb_checkpoints

# Data files
data/raw/*
data/dedup_ready/*
data/deduped/*
data/parquet/*
*.jsonl
*.parquet

# Model files
models/base/*
models/lora_*/
models/merged/*
models/diff_vectors/*
*.bin
*.safetensors

# Logs
logs/*.log
*.log

# Cache
cache/
.cache/

# Results
results/*
*.csv
*.json

# Environment variables
.env
.env.local

# OS
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.temp
EOF

        log_message ".gitignore created"
    fi
}

# Setup development tools
setup_dev_tools() {
    log_message "Setting up development tools..."

    # Install additional development dependencies
    pip install black flake8 pytest pytest-cov mypy

    # Create pre-commit hook (optional)
    if command -v git &> /dev/null && [ -d "$PROJECT_ROOT/.git" ]; then
        log_message "Setting up git hooks..."

        local pre_commit_hook="$PROJECT_ROOT/.git/hooks/pre-commit"
        cat > "$pre_commit_hook" << 'EOF'
#!/bin/bash
# Run code quality checks before commit

cd "$(git rev-parse --show-toplevel)"

echo "Running code quality checks..."

# Run black formatter
black --check .
if [ $? -ne 0 ]; then
    echo "Code formatting issues found. Run 'black .' to fix."
    exit 1
fi

# Run flake8 linter
flake8 .
if [ $? -ne 0 ]; then
    echo "Linting issues found. Please fix them."
    exit 1
fi

echo "Code quality checks passed!"
EOF

        chmod +x "$pre_commit_hook"
        log_message "Git pre-commit hook created"
    fi

    log_message "Development tools setup complete"
}

# Main setup function
main() {
    log_message "🚀 Starting YunMin-EfficientData environment setup"

    # Change to project root
    cd "$PROJECT_ROOT"

    # Check Python
    check_python

    # Create virtual environment
    create_venv

    # Activate virtual environment
    activate_venv

    # Install dependencies
    install_dependencies

    # Install Korean support
    install_korean_support

    # Create directories
    create_directories

    # Create .gitignore
    create_gitignore

    # Setup development tools
    setup_dev_tools

    log_message "✅ Environment setup complete!"
    log_message ""
    log_message "To activate the environment in the future, run:"
    log_message "  source venv/bin/activate  # Linux/Mac"
    log_message "  venv\\Scripts\\activate     # Windows"
    log_message ""
    log_message "To run the pipeline:"
    log_message "  ./scripts/run_pipeline.sh data/raw/your_data.jsonl"
}

# Run main function
main "$@"
