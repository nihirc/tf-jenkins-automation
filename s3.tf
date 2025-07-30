provider "aws" {
  region = var.aws_region
}

resource "aws_s3_bucket" "poc_bucket" {
  bucket = var.bucket_name
}

# Enable versioning
resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.poc_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable server-side encryption by default
resource "aws_s3_bucket_server_side_encryption_configuration" "encryption" {
  bucket = aws_s3_bucket.poc_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block all public access
resource "aws_s3_bucket_public_access_block" "public_access_block" {
  bucket = aws_s3_bucket.poc_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable bucket logging
resource "aws_s3_bucket_logging" "logging" {
  bucket = aws_s3_bucket.poc_bucket.id

  target_bucket = aws_s3_bucket.poc_bucket.id
  target_prefix = "log/"
}
