
resource "aws_ecr_repository" "document_rag" {
  name                 = "document-rag-api"
  image_tag_mutability = "MUTABLE"

  encryption_configuration {
    encryption_type = "AES256"
  }

  lifecycle {
    prevent_destroy = true
  }
}

output "ecr_repository_url" {
  value = aws_ecr_repository.document_rag.repository_url
}
