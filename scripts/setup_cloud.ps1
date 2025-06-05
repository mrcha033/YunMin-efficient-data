# YunMin-EfficientData Cloud Storage Setup Script (PowerShell)
# This script helps set up cloud storage providers on Windows

param(
    [Parameter(Position=0)]
    [string]$Provider = "",
    [string]$BucketName = "yunmin-data"
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message" -ForegroundColor Green
}

function Write-Error-Log {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] ERROR: $Message" -ForegroundColor Red
}

function Test-Command {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Setup-AwsS3 {
    Write-Log "Setting up AWS S3..."
    
    # Check AWS CLI
    if (-not (Test-Command "aws")) {
        Write-Log "AWS CLI not found. Please install it from: https://aws.amazon.com/cli/"
        Write-Log "Or install via Windows Package Manager: winget install Amazon.AWSCLI"
        return $false
    }
    
    # Configure AWS
    Write-Log "Configuring AWS CLI..."
    aws configure
    
    # Test and create bucket
    Write-Log "Testing S3 access with bucket: $BucketName"
    
    try {
        aws s3 ls "s3://$BucketName" 2>$null
        Write-Log "✅ S3 bucket '$BucketName' is accessible"
    }
    catch {
        Write-Log "Creating S3 bucket '$BucketName'..."
        aws s3 mb "s3://$BucketName"
        
        # Create directory structure
        aws s3api put-object --bucket $BucketName --key "raw/"
        aws s3api put-object --bucket $BucketName --key "deduped/"
        aws s3api put-object --bucket $BucketName --key "parquet/"
        aws s3api put-object --bucket $BucketName --key "models/"
        aws s3api put-object --bucket $BucketName --key "logs/"
        
        Write-Log "✅ S3 bucket created and structured"
    }
    
    Update-ConfigFile "s3" $BucketName
    return $true
}

function Setup-Gcs {
    Write-Log "Setting up Google Cloud Storage..."
    
    # Check gcloud CLI
    if (-not (Test-Command "gcloud")) {
        Write-Log "Google Cloud SDK not found. Please install it from:"
        Write-Log "https://cloud.google.com/sdk/docs/install"
        return $false
    }
    
    # Authenticate
    Write-Log "Authenticating with Google Cloud..."
    gcloud auth login
    
    # Set project
    $ProjectId = Read-Host "Please enter your Google Cloud Project ID"
    gcloud config set project $ProjectId
    
    # Test and create bucket
    Write-Log "Testing GCS access with bucket: $BucketName"
    
    try {
        gsutil ls "gs://$BucketName" 2>$null
        Write-Log "✅ GCS bucket '$BucketName' is accessible"
    }
    catch {
        Write-Log "Creating GCS bucket '$BucketName'..."
        gsutil mb "gs://$BucketName"
        
        # Create directory structure
        "" | gsutil cp - "gs://$BucketName/raw/.keep"
        "" | gsutil cp - "gs://$BucketName/deduped/.keep"
        "" | gsutil cp - "gs://$BucketName/parquet/.keep"
        "" | gsutil cp - "gs://$BucketName/models/.keep"
        "" | gsutil cp - "gs://$BucketName/logs/.keep"
        
        Write-Log "✅ GCS bucket created and structured"
    }
    
    # Create service account
    Write-Log "Creating service account for authentication..."
    $ServiceAccount = "yunmin-data-sa"
    
    try {
        gcloud iam service-accounts create $ServiceAccount --display-name="YunMin Data Service Account"
    }
    catch {
        Write-Log "Service account may already exist, continuing..."
    }
    
    # Grant permissions
    gcloud projects add-iam-policy-binding $ProjectId `
        --member="serviceAccount:${ServiceAccount}@${ProjectId}.iam.gserviceaccount.com" `
        --role="roles/storage.admin"
    
    # Create key file
    $KeyFile = Join-Path $PSScriptRoot "..\gcs-service-account.json"
    gcloud iam service-accounts keys create $KeyFile `
        --iam-account="${ServiceAccount}@${ProjectId}.iam.gserviceaccount.com"
    
    Write-Log "✅ Service account key saved to: $KeyFile"
    Write-Log "Please set environment variable: GOOGLE_APPLICATION_CREDENTIALS=$KeyFile"
    
    Update-ConfigFile "gcs" $BucketName $KeyFile
    return $true
}

function Setup-Azure {
    Write-Log "Setting up Azure Blob Storage..."
    
    # Check Azure CLI
    if (-not (Test-Command "az")) {
        Write-Log "Azure CLI not found. Installing via winget..."
        try {
            winget install Microsoft.AzureCLI
            Write-Log "Please restart PowerShell after installation and run this script again."
            return $false
        }
        catch {
            Write-Log "Please install Azure CLI manually from:"
            Write-Log "https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
            return $false
        }
    }
    
    # Login
    Write-Log "Logging into Azure..."
    az login
    
    # Get user input
    $ResourceGroup = Read-Host "Please enter your Azure resource group name"
    $StorageAccount = Read-Host "Please enter your storage account name (must be globally unique)"
    
    # Create storage account
    Write-Log "Creating storage account '$StorageAccount' in resource group '$ResourceGroup'..."
    az storage account create `
        --name $StorageAccount `
        --resource-group $ResourceGroup `
        --location "koreacentral" `
        --sku "Standard_LRS" `
        --kind "StorageV2"
    
    # Get connection string
    $ConnectionString = az storage account show-connection-string `
        --name $StorageAccount `
        --resource-group $ResourceGroup `
        --output tsv
    
    # Create container
    $ContainerName = $BucketName
    Write-Log "Creating container '$ContainerName'..."
    az storage container create `
        --name $ContainerName `
        --connection-string $ConnectionString
    
    Write-Log "✅ Azure Blob Storage setup complete"
    Write-Log "Please set environment variable: AZURE_STORAGE_CONNECTION_STRING='$ConnectionString'"
    
    Update-ConfigFile "azure" $ContainerName $ConnectionString
    return $true
}

function Update-ConfigFile {
    param(
        [string]$Provider,
        [string]$Bucket,
        [string]$Extra = ""
    )
    
    $ConfigFile = Join-Path $PSScriptRoot "..\configs\dataset_config.yaml"
    Write-Log "Updating configuration file: $ConfigFile"
    
    # Backup original config
    Copy-Item $ConfigFile "$ConfigFile.backup"
    
    # Read and update config
    $content = Get-Content $ConfigFile
    
    # Update provider and bucket
    $content = $content -replace 'provider: .*', "provider: `"$Provider`""
    $content = $content -replace 'bucket: .*', "bucket: `"$Bucket`""
    
    # Update paths based on provider
    switch ($Provider) {
        "s3" {
            $content = $content -replace 'raw_data: .*', "raw_data: `"s3://$Bucket/raw/`""
            $content = $content -replace 'dedup_ready: .*', "dedup_ready: `"s3://$Bucket/dedup_ready/`""
            $content = $content -replace 'deduped: .*', "deduped: `"s3://$Bucket/deduped/`""
            $content = $content -replace 'parquet: .*', "parquet: `"s3://$Bucket/parquet/`""
        }
        "gcs" {
            $content = $content -replace 'raw_data: .*', "raw_data: `"gs://$Bucket/raw/`""
            $content = $content -replace 'dedup_ready: .*', "dedup_ready: `"gs://$Bucket/dedup_ready/`""
            $content = $content -replace 'deduped: .*', "deduped: `"gs://$Bucket/deduped/`""
            $content = $content -replace 'parquet: .*', "parquet: `"gs://$Bucket/parquet/`""
        }
        "azure" {
            $content = $content -replace 'raw_data: .*', "raw_data: `"azure://$Bucket/raw/`""
            $content = $content -replace 'dedup_ready: .*', "dedup_ready: `"azure://$Bucket/dedup_ready/`""
            $content = $content -replace 'deduped: .*', "deduped: `"azure://$Bucket/deduped/`""
            $content = $content -replace 'parquet: .*', "parquet: `"azure://$Bucket/parquet/`""
        }
    }
    
    # Save updated config
    $content | Set-Content $ConfigFile
    
    Write-Log "✅ Configuration updated successfully"
}

function Test-CloudSetup {
    Write-Log "Testing cloud storage setup..."
    
    $ProjectRoot = Split-Path $PSScriptRoot -Parent
    
    # Test with Python
    $TestScript = @"
import sys
sys.path.append('$($ProjectRoot.Replace('\', '/'))')
from utils.cloud_storage import get_storage_client
import yaml

with open('$($ProjectRoot.Replace('\', '/'))/configs/dataset_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

try:
    client = get_storage_client(config)
    print(f'✅ Successfully initialized {client.provider} storage client')
    
    bucket = config['storage']['bucket']
    test_files = client.list_files(bucket, suffix='.keep')
    print(f'✅ Successfully listed files: {len(test_files)} files found')
    
except Exception as e:
    print(f'❌ Cloud storage test failed: {e}')
    sys.exit(1)
"@
    
    $TestScript | python
    
    if ($LASTEXITCODE -eq 0) {
        Write-Log "✅ Cloud storage test completed successfully"
        return $true
    } else {
        Write-Error-Log "Cloud storage test failed"
        return $false
    }
}

# Main function
function Main {
    Write-Log "🚀 YunMin-EfficientData Cloud Storage Setup (PowerShell)"
    
    if ($Provider -eq "") {
        Write-Host ""
        Write-Host "Please select your cloud storage provider:"
        Write-Host "1) AWS S3"
        Write-Host "2) Google Cloud Storage"
        Write-Host "3) Azure Blob Storage"
        Write-Host "4) Test existing setup"
        Write-Host ""
        
        $choice = Read-Host "Enter your choice (1-4)"
    } else {
        switch ($Provider.ToLower()) {
            "s3" { $choice = "1" }
            "gcs" { $choice = "2" }
            "azure" { $choice = "3" }
            "test" { $choice = "4" }
            default {
                Write-Error-Log "Invalid provider: $Provider"
                return
            }
        }
    }
    
    $success = $false
    
    switch ($choice) {
        "1" { $success = Setup-AwsS3 }
        "2" { $success = Setup-Gcs }
        "3" { $success = Setup-Azure }
        "4" { 
            $success = Test-CloudSetup
            return
        }
        default {
            Write-Error-Log "Invalid choice. Exiting."
            return
        }
    }
    
    if ($success) {
        # Test the setup
        $success = Test-CloudSetup
        
        if ($success) {
            Write-Log "✅ Cloud storage setup completed successfully!"
            Write-Log ""
            Write-Log "Next steps:"
            Write-Log "1. Upload your JSONL data to the cloud storage"
            Write-Log "2. Run the pipeline: .\scripts\run_pipeline.ps1 <cloud_path_to_data>"
            Write-Log ""
        }
    }
}

# Run main function
Main 