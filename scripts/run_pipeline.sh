#!/bin/bash

# YunMin-EfficientData Pipeline Execution Script
# This script automates the entire data processing pipeline

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$PROJECT_ROOT/configs"
LOG_DIR="$PROJECT_ROOT/logs"
DATA_DIR="$PROJECT_ROOT/data"

# Default configurations
DATASET_CONFIG="$CONFIG_DIR/dataset_config.yaml"
DEM_CONFIG="$CONFIG_DIR/dem_config.yaml"
LOGGING_CONFIG="$CONFIG_DIR/logging.yaml"

# Create necessary directories
mkdir -p "$LOG_DIR" "$DATA_DIR/raw" "$DATA_DIR/dedup_ready" "$DATA_DIR/deduped" "$DATA_DIR/parquet"

# Logging setup
PIPELINE_LOG="$LOG_DIR/pipeline_run.log"
ERROR_LOG="$LOG_DIR/pipeline_errors.log"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$PIPELINE_LOG"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$PIPELINE_LOG" "$ERROR_LOG"
}

# Function to check if command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "Command '$1' not found. Please install it."
        exit 1
    fi
}

# Function to check file exists
check_file() {
    if [[ ! -f "$1" ]]; then
        log_error "Required file not found: $1"
        exit 1
    fi
}

# Function to validate phase completion
validate_phase() {
    local phase_name="$1"
    local expected_output="$2"
    
    if [[ -f "$expected_output" ]]; then
        log_message "✅ Phase $phase_name completed successfully: $expected_output"
        return 0
    else
        log_error "❌ Phase $phase_name failed: Expected output not found: $expected_output"
        return 1
    fi
}

# Function to run Phase 1: Deduplication
run_phase1() {
    log_message "🚀 Starting Phase 1: Deduplication"
    
    local input_file="$1"
    local output_file="$DATA_DIR/deduped/$(basename "$input_file" .jsonl)_deduped.jsonl"
    
    check_file "$input_file"
    
    python -m dedup.slimpajama_dedup \
        --config "$DATASET_CONFIG" \
        --input "$input_file" \
        --output "$output_file" \
        --log-file "$LOG_DIR/phase1_dedup.log" \
        2>> "$ERROR_LOG"
    
    validate_phase "1" "$output_file"
    echo "$output_file"
}

# Function to run Phase 2: Format Conversion
run_phase2() {
    log_message "🚀 Starting Phase 2: Format Conversion"
    
    local input_file="$1"
    local output_file="$DATA_DIR/parquet/$(basename "$input_file" .jsonl).parquet"
    
    check_file "$input_file"
    
    python -m format.to_parquet \
        --config "$DATASET_CONFIG" \
        --input "$input_file" \
        --output "$output_file" \
        --benchmark \
        2>> "$ERROR_LOG"
    
    validate_phase "2" "$output_file"
    echo "$output_file"
}

# Function to run Phase 3: DEM Training and Merging
run_phase3() {
    log_message "🚀 Starting Phase 3: DEM Training and Merging"
    
    local parquet_files=("$@")
    
    # Individual LoRA training for each domain
    for parquet_file in "${parquet_files[@]}"; do
        local domain=$(basename "$parquet_file" .parquet)
        log_message "Training LoRA model for domain: $domain"
        
        python -m dem.train_individual \
            --config "$DEM_CONFIG" \
            --data "$parquet_file" \
            --domain "$domain" \
            --output-dir "models/lora_$domain" \
            2>> "$ERROR_LOG"
    done
    
    # Generate difference vectors
    log_message "Generating difference vectors..."
    python -m dem.vector_diff \
        --config "$DEM_CONFIG" \
        --base-model "models/base/" \
        --lora-dirs models/lora_* \
        --output-dir "models/diff_vectors" \
        2>> "$ERROR_LOG"
    
    # Merge models
    log_message "Merging models..."
    python -m dem.merge_model \
        --config "$DEM_CONFIG" \
        --diff-vectors-dir "models/diff_vectors" \
        --output-dir "models/merged" \
        2>> "$ERROR_LOG"
    
    validate_phase "3" "models/merged/pytorch_model.bin"
}

# Function to run Phase 4: Evaluation
run_phase4() {
    log_message "🚀 Starting Phase 4: Evaluation"
    
    # Run evaluation
    python -m evaluation.eval_runner \
        --base-model "models/base/" \
        --merged-model "models/merged/" \
        --eval-prompts "evaluation/eval_prompts.jsonl" \
        --output-dir "results/" \
        2>> "$ERROR_LOG"
    
    # Compute metrics
    python -m evaluation.compute_metrics \
        --results-dir "results/" \
        --output "results/metric_summary.csv" \
        2>> "$ERROR_LOG"
    
    validate_phase "4" "results/metric_summary.csv"
}

# Main pipeline function
run_pipeline() {
    local input_files=("$@")
    
    log_message "🎯 Starting YunMin-EfficientData Pipeline"
    log_message "Input files: ${input_files[*]}"
    
    # Check prerequisites
    log_message "Checking prerequisites..."
    check_command python
    check_command pip
    check_file "$DATASET_CONFIG"
    check_file "$DEM_CONFIG"
    
    # Phase 1: Deduplication
    local deduped_files=()
    for input_file in "${input_files[@]}"; do
        deduped_file=$(run_phase1 "$input_file")
        deduped_files+=("$deduped_file")
    done
    
    # Phase 2: Format Conversion
    local parquet_files=()
    for deduped_file in "${deduped_files[@]}"; do
        parquet_file=$(run_phase2 "$deduped_file")
        parquet_files+=("$parquet_file")
    done
    
    # Phase 3: DEM Training and Merging
    run_phase3 "${parquet_files[@]}"
    
    # Phase 4: Evaluation
    run_phase4
    
    log_message "🎉 Pipeline completed successfully!"
}

# Usage function
usage() {
    cat << EOF
Usage: $0 [OPTIONS] INPUT_FILES...

YunMin-EfficientData Pipeline Runner

OPTIONS:
    -h, --help          Show this help message
    -c, --config DIR    Configuration directory (default: $CONFIG_DIR)
    -l, --log-dir DIR   Log directory (default: $LOG_DIR)
    --phase1-only       Run only Phase 1 (deduplication)
    --phase2-only       Run only Phase 2 (format conversion)
    --phase3-only       Run only Phase 3 (DEM training)
    --phase4-only       Run only Phase 4 (evaluation)
    --skip-phase1       Skip Phase 1
    --skip-phase2       Skip Phase 2
    --skip-phase3       Skip Phase 3
    --skip-phase4       Skip Phase 4

EXAMPLES:
    # Run full pipeline
    $0 data/raw/dataset1.jsonl data/raw/dataset2.jsonl
    
    # Run only deduplication
    $0 --phase1-only data/raw/dataset.jsonl
    
    # Run pipeline skipping evaluation
    $0 --skip-phase4 data/raw/dataset.jsonl

EOF
}

# Parse command line arguments
PHASE1_ONLY=false
PHASE2_ONLY=false
PHASE3_ONLY=false
PHASE4_ONLY=false
SKIP_PHASE1=false
SKIP_PHASE2=false
SKIP_PHASE3=false
SKIP_PHASE4=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -c|--config)
            CONFIG_DIR="$2"
            DATASET_CONFIG="$CONFIG_DIR/dataset_config.yaml"
            DEM_CONFIG="$CONFIG_DIR/dem_config.yaml"
            shift 2
            ;;
        -l|--log-dir)
            LOG_DIR="$2"
            PIPELINE_LOG="$LOG_DIR/pipeline_run.log"
            ERROR_LOG="$LOG_DIR/pipeline_errors.log"
            shift 2
            ;;
        --phase1-only)
            PHASE1_ONLY=true
            shift
            ;;
        --phase2-only)
            PHASE2_ONLY=true
            shift
            ;;
        --phase3-only)
            PHASE3_ONLY=true
            shift
            ;;
        --phase4-only)
            PHASE4_ONLY=true
            shift
            ;;
        --skip-phase1)
            SKIP_PHASE1=true
            shift
            ;;
        --skip-phase2)
            SKIP_PHASE2=true
            shift
            ;;
        --skip-phase3)
            SKIP_PHASE3=true
            shift
            ;;
        --skip-phase4)
            SKIP_PHASE4=true
            shift
            ;;
        *)
            break
            ;;
    esac
done

# Check if input files provided
if [[ $# -eq 0 ]]; then
    log_error "No input files provided"
    usage
    exit 1
fi

# Initialize logging
echo "YunMin-EfficientData Pipeline Started at $(date)" > "$PIPELINE_LOG"
echo "YunMin-EfficientData Pipeline Errors at $(date)" > "$ERROR_LOG"

# Run based on options
if [[ "$PHASE1_ONLY" == true ]]; then
    for input_file in "$@"; do
        run_phase1 "$input_file"
    done
elif [[ "$PHASE2_ONLY" == true ]]; then
    for input_file in "$@"; do
        run_phase2 "$input_file"
    done
elif [[ "$PHASE3_ONLY" == true ]]; then
    run_phase3 "$@"
elif [[ "$PHASE4_ONLY" == true ]]; then
    run_phase4
else
    # Run full pipeline with skip options
    input_files=("$@")
    
    if [[ "$SKIP_PHASE1" == false ]]; then
        deduped_files=()
        for input_file in "${input_files[@]}"; do
            deduped_file=$(run_phase1 "$input_file")
            deduped_files+=("$deduped_file")
        done
        input_files=("${deduped_files[@]}")
    fi
    
    if [[ "$SKIP_PHASE2" == false ]]; then
        parquet_files=()
        for input_file in "${input_files[@]}"; do
            parquet_file=$(run_phase2 "$input_file")
            parquet_files+=("$parquet_file")
        done
        input_files=("${parquet_files[@]}")
    fi
    
    if [[ "$SKIP_PHASE3" == false ]]; then
        run_phase3 "${input_files[@]}"
    fi
    
    if [[ "$SKIP_PHASE4" == false ]]; then
        run_phase4
    fi
    
    log_message "🎉 Pipeline completed successfully!"
fi 