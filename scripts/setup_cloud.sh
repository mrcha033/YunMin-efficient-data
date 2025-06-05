#!/bin/bash

# YunMin-EfficientData Cloud Storage Setup Script
# This script helps set up cloud storage providers

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check if command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "Warning: Command '$1' not found. Some features may not work."
        return 1
    fi
    return 0
}

# Setup AWS S3
setup_aws_s3() {
    log_message "Setting up AWS S3..."

    if ! check_command aws; then
        log_message "AWS CLI not found. Installing..."

        # Install AWS CLI
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
            unzip awscliv2.zip
            sudo ./aws/install
            rm -rf awscliv2.zip aws/
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            if command -v brew &> /dev/null; then
                brew install awscli
            else
                curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
                sudo installer -pkg AWSCLIV2.pkg -target /
                rm AWSCLIV2.pkg
            fi
        else
            log_message "Please install AWS CLI manually: https://aws.amazon.com/cli/"
            return 1
        fi
    fi

    # Configure AWS CLI
    log_message "Configuring AWS CLI..."
    echo "Please enter your AWS credentials:"
    aws configure

    # Test S3 access
    BUCKET_NAME="${S3_BUCKET_NAME:-yunmin-data}"
    log_message "Testing S3 access with bucket: $BUCKET_NAME"

    if aws s3 ls "s3://$BUCKET_NAME" &>/dev/null; then
        log_message "✅ S3 bucket '$BUCKET_NAME' is accessible"
    else
        log_message "Creating S3 bucket '$BUCKET_NAME'..."
        aws s3 mb "s3://$BUCKET_NAME"

        # Create directory structure
        aws s3api put-object --bucket "$BUCKET_NAME" --key "raw/"
        aws s3api put-object --bucket "$BUCKET_NAME" --key "deduped/"
        aws s3api put-object --bucket "$BUCKET_NAME" --key "parquet/"
        aws s3api put-object --bucket "$BUCKET_NAME" --key "models/"
        aws s3api put-object --bucket "$BUCKET_NAME" --key "logs/"

        log_message "✅ S3 bucket created and structured"
    fi

    # Update config file
    update_config_file "s3" "$BUCKET_NAME"
}

# Setup Google Cloud Storage
setup_gcs() {
    log_message "Setting up Google Cloud Storage..."

    if ! check_command gcloud; then
        log_message "Google Cloud SDK not found. Please install it manually:"
        log_message "https://cloud.google.com/sdk/docs/install"
        return 1
    fi

    # Authenticate
    log_message "Authenticating with Google Cloud..."
    gcloud auth login

    # Set project
    echo "Please enter your Google Cloud Project ID:"
    read -r PROJECT_ID
    gcloud config set project "$PROJECT_ID"

    # Test GCS access
    BUCKET_NAME="${GCS_BUCKET_NAME:-yunmin-data}"
    log_message "Testing GCS access with bucket: $BUCKET_NAME"

    if gsutil ls "gs://$BUCKET_NAME" &>/dev/null; then
        log_message "✅ GCS bucket '$BUCKET_NAME' is accessible"
    else
        log_message "Creating GCS bucket '$BUCKET_NAME'..."
        gsutil mb "gs://$BUCKET_NAME"

        # Create directory structure
        echo "" | gsutil cp - "gs://$BUCKET_NAME/raw/.keep"
        echo "" | gsutil cp - "gs://$BUCKET_NAME/deduped/.keep"
        echo "" | gsutil cp - "gs://$BUCKET_NAME/parquet/.keep"
        echo "" | gsutil cp - "gs://$BUCKET_NAME/models/.keep"
        echo "" | gsutil cp - "gs://$BUCKET_NAME/logs/.keep"

        log_message "✅ GCS bucket created and structured"
    fi

    # Create service account key
    log_message "Creating service account for authentication..."
    SERVICE_ACCOUNT="yunmin-data-sa"
    gcloud iam service-accounts create "$SERVICE_ACCOUNT" --display-name="YunMin Data Service Account" || true

    # Grant permissions
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/storage.admin"

    # Create and download key
    KEY_FILE="$PROJECT_ROOT/gcs-service-account.json"
    gcloud iam service-accounts keys create "$KEY_FILE" \
        --iam-account="${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com"

    log_message "✅ Service account key saved to: $KEY_FILE"
    log_message "Please set: export GOOGLE_APPLICATION_CREDENTIALS=$KEY_FILE"

    # Update config file
    update_config_file "gcs" "$BUCKET_NAME" "$KEY_FILE"
}

# Setup Azure Blob Storage
setup_azure() {
    log_message "Setting up Azure Blob Storage..."

    if ! check_command az; then
        log_message "Azure CLI not found. Installing..."

        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            if command -v brew &> /dev/null; then
                brew install azure-cli
            else
                log_message "Please install Azure CLI manually: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
                return 1
            fi
        else
            log_message "Please install Azure CLI manually: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
            return 1
        fi
    fi

    # Login
    log_message "Logging into Azure..."
    az login

    # Create storage account
    echo "Please enter your Azure resource group name:"
    read -r RESOURCE_GROUP
    echo "Please enter your storage account name (must be globally unique):"
    read -r STORAGE_ACCOUNT

    log_message "Creating storage account '$STORAGE_ACCOUNT' in resource group '$RESOURCE_GROUP'..."
    az storage account create \
        --name "$STORAGE_ACCOUNT" \
        --resource-group "$RESOURCE_GROUP" \
        --location "koreacentral" \
        --sku "Standard_LRS" \
        --kind "StorageV2"

    # Get connection string
    CONNECTION_STRING=$(az storage account show-connection-string \
        --name "$STORAGE_ACCOUNT" \
        --resource-group "$RESOURCE_GROUP" \
        --output tsv)

    # Create container
    CONTAINER_NAME="${AZURE_CONTAINER_NAME:-yunmin-data}"
    log_message "Creating container '$CONTAINER_NAME'..."
    az storage container create \
        --name "$CONTAINER_NAME" \
        --connection-string "$CONNECTION_STRING"

    # Create directory structure
    echo "" | az storage blob upload \
        --container-name "$CONTAINER_NAME" \
        --file /dev/stdin \
        --name "raw/.keep" \
        --connection-string "$CONNECTION_STRING"

    log_message "✅ Azure Blob Storage setup complete"
    log_message "Please set: export AZURE_STORAGE_CONNECTION_STRING='$CONNECTION_STRING'"

    # Update config file
    update_config_file "azure" "$CONTAINER_NAME" "$CONNECTION_STRING"
}

# Update configuration file
update_config_file() {
    local provider="$1"
    local bucket="$2"
    local extra="${3:-}"

    local config_file="$PROJECT_ROOT/configs/dataset_config.yaml"

    log_message "Updating configuration file: $config_file"

    # Backup original config
    cp "$config_file" "${config_file}.backup"

    # Update provider
    sed -i.tmp "s/provider: .*/provider: \"$provider\"/" "$config_file"
    sed -i.tmp "s/bucket: .*/bucket: \"$bucket\"/" "$config_file"

    # Update paths based on provider
    case $provider in
        "s3")
            sed -i.tmp "s|raw_data: .*|raw_data: \"s3://$bucket/raw/\"|" "$config_file"
            sed -i.tmp "s|dedup_ready: .*|dedup_ready: \"s3://$bucket/dedup_ready/\"|" "$config_file"
            sed -i.tmp "s|deduped: .*|deduped: \"s3://$bucket/deduped/\"|" "$config_file"
            sed -i.tmp "s|parquet: .*|parquet: \"s3://$bucket/parquet/\"|" "$config_file"
            ;;
        "gcs")
            sed -i.tmp "s|raw_data: .*|raw_data: \"gs://$bucket/raw/\"|" "$config_file"
            sed -i.tmp "s|dedup_ready: .*|dedup_ready: \"gs://$bucket/dedup_ready/\"|" "$config_file"
            sed -i.tmp "s|deduped: .*|deduped: \"gs://$bucket/deduped/\"|" "$config_file"
            sed -i.tmp "s|parquet: .*|parquet: \"gs://$bucket/parquet/\"|" "$config_file"
            ;;
        "azure")
            sed -i.tmp "s|raw_data: .*|raw_data: \"azure://$bucket/raw/\"|" "$config_file"
            sed -i.tmp "s|dedup_ready: .*|dedup_ready: \"azure://$bucket/dedup_ready/\"|" "$config_file"
            sed -i.tmp "s|deduped: .*|deduped: \"azure://$bucket/deduped/\"|" "$config_file"
            sed -i.tmp "s|parquet: .*|parquet: \"azure://$bucket/parquet/\"|" "$config_file"
            ;;
    esac

    # Clean up temporary files
    rm -f "${config_file}.tmp"

    log_message "✅ Configuration updated successfully"
}

# Test cloud storage setup
test_cloud_setup() {
    log_message "Testing cloud storage setup..."

    # Test with Python script
    python3 -c "
import sys
sys.path.append('$PROJECT_ROOT')
from utils.cloud_storage import get_storage_client
import yaml

with open('$PROJECT_ROOT/configs/dataset_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

try:
    client = get_storage_client(config)
    print(f'✅ Successfully initialized {client.provider} storage client')

    # Test basic operations
    bucket = config['storage']['bucket']
    test_files = client.list_files(bucket, suffix='.keep')
    print(f'✅ Successfully listed files: {len(test_files)} files found')

except Exception as e:
    print(f'❌ Cloud storage test failed: {e}')
    sys.exit(1)
"

    log_message "✅ Cloud storage test completed successfully"
}

# Main function
main() {
    log_message "🚀 YunMin-EfficientData Cloud Storage Setup"

    echo "Please select your cloud storage provider:"
    echo "1) AWS S3"
    echo "2) Google Cloud Storage"
    echo "3) Azure Blob Storage"
    echo "4) Test existing setup"

    read -p "Enter your choice (1-4): " choice

    case $choice in
        1)
            setup_aws_s3
            ;;
        2)
            setup_gcs
            ;;
        3)
            setup_azure
            ;;
        4)
            test_cloud_setup
            exit 0
            ;;
        *)
            log_message "Invalid choice. Exiting."
            exit 1
            ;;
    esac

    # Test the setup
    test_cloud_setup

    log_message "✅ Cloud storage setup completed successfully!"
    log_message ""
    log_message "Next steps:"
    log_message "1. Upload your JSONL data to the cloud storage"
    log_message "2. Run the pipeline: ./scripts/run_pipeline.sh <cloud_path_to_data>"
    log_message ""
}

# Run main function
main "$@"
