variable "hawkfish_endpoint" {
  description = "HawkFish API endpoint"
  type        = string
  default     = "http://localhost:8080"
}

variable "hawkfish_username" {
  description = "HawkFish username"
  type        = string
  default     = "local"
}

variable "hawkfish_password" {
  description = "HawkFish password"
  type        = string
  default     = ""
  sensitive   = true
}
