resource "aws_s3_bucket" "poc_bucket" {
  bucket = "28julypoctest"

  # Force destroy is set to false for safety
  force_destroy = false

  tags = {
    Name        = "28julypoctest"
    Environment = "POC"
  }
}

# Enable versioning
resource "aws_s3_bucket_versioning" "poc_bucket_versioning" {
  bucket = aws_s3_bucket.poc_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable server-side encryption by default
resource "aws_s3_bucket_server_side_encryption_configuration" "poc_bucket_encryption" {
  bucket = aws_s3_bucket.poc_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "poc_bucket_public_access_block" {
  bucket = aws_s3_bucket.poc_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable logging
resource "aws_s3_bucket_logging" "poc_bucket_logging" {
  bucket = aws_s3_bucket.poc_bucket.id

  target_bucket = aws_s3_bucket.poc_bucket.id
  target_prefix = "log/"
}
