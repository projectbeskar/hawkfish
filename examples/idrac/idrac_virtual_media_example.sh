#!/bin/bash
# Dell iDRAC VirtualMedia example using only iDRAC-compatible endpoints
# This script demonstrates VirtualMedia operations via Dell iDRAC aliases

set -e

# Configuration
HAWKFISH_URL="${HAWKFISH_URL:-https://localhost:8080}"
TOKEN="${HAWKFISH_TOKEN:-}"
SYSTEM_ID="${SYSTEM_ID:-vm-001}"
ISO_URL="${ISO_URL:-http://example.com/ubuntu-22.04.iso}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

# Check prerequisites
if [ -z "$TOKEN" ]; then
    error "HAWKFISH_TOKEN environment variable required"
fi

if [ -z "$SYSTEM_ID" ]; then
    error "SYSTEM_ID environment variable required"
fi

# Common curl options
CURL_OPTS=(-s -k -H "Content-Type: application/json" -H "X-Auth-Token: $TOKEN")

log "⚡ Dell iDRAC VirtualMedia Example"
echo "==================================="
echo "HawkFish URL: $HAWKFISH_URL"
echo "System ID: $SYSTEM_ID"
echo "ISO URL: $ISO_URL"
echo ""

# Step 1: Get iDRAC Manager info
log "1. Getting Dell iDRAC Manager information..."
response=$(curl "${CURL_OPTS[@]}" "$HAWKFISH_URL/redfish/v1/Managers/iDRAC.Embedded.1" || error "Failed to get Manager info")

manager_name=$(echo "$response" | jq -r '.Name // "Unknown"')
firmware_version=$(echo "$response" | jq -r '.FirmwareVersion // "Unknown"')
model=$(echo "$response" | jq -r '.Model // "Unknown"')
dell_manager_type=$(echo "$response" | jq -r '.Oem.Dell.DellManager.DellManagerType // "Unknown"')
disclaimer=$(echo "$response" | jq -r '.Oem.HawkFish.CompatibilityDisclaimer // "None"')

success "Manager: $manager_name"
success "Model: $model"
success "Firmware: $firmware_version"
success "Dell Manager Type: $dell_manager_type"
warning "Disclaimer: $disclaimer"
echo ""

# Step 2: Get VirtualMedia collection
log "2. Getting VirtualMedia collection..."
response=$(curl "${CURL_OPTS[@]}" "$HAWKFISH_URL/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia" || error "Failed to get VirtualMedia collection")

member_count=$(echo "$response" | jq -r '.["Members@odata.count"] // 0')
success "Found $member_count VirtualMedia resource(s)"
echo ""

# Step 3: Get CD VirtualMedia resource
log "3. Getting CD VirtualMedia resource..."
response=$(curl "${CURL_OPTS[@]}" "$HAWKFISH_URL/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD" || error "Failed to get CD resource")

cd_name=$(echo "$response" | jq -r '.Name // "Unknown"')
media_types=$(echo "$response" | jq -r '.MediaTypes | join(", ") // "Unknown"')
inserted=$(echo "$response" | jq -r '.Inserted // false')

success "CD Resource: $cd_name"
success "Media Types: $media_types" 
success "Currently Inserted: $inserted"
echo ""

# Step 4: Insert media via Dell endpoint
log "4. Inserting media via Dell iDRAC endpoint..."
insert_payload=$(jq -n --arg systemId "$SYSTEM_ID" --arg image "$ISO_URL" '{
    "SystemId": $systemId,
    "Image": $image
}')

response=$(curl "${CURL_OPTS[@]}" -X POST \
    -d "$insert_payload" \
    "$HAWKFISH_URL/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/Oem/DellVirtualMedia.InsertVirtualMedia" \
    || error "Failed to insert media")

task_state=$(echo "$response" | jq -r '.TaskState // "Unknown"')
job_status=$(echo "$response" | jq -r '.Oem.Dell.JobStatus // "Unknown"')

if [ "$task_state" = "Completed" ]; then
    success "Media inserted successfully"
    success "Dell Job Status: $job_status"
else
    error "Media insertion failed: $task_state"
fi
echo ""

# Step 5: Check Dell Jobs queue
log "5. Checking Dell Jobs queue..."
response=$(curl "${CURL_OPTS[@]}" "$HAWKFISH_URL/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs" || error "Failed to get Jobs queue")

job_count=$(echo "$response" | jq -r '.["Members@odata.count"] // 0')
success "Jobs in queue: $job_count"

if [ "$job_count" -gt 0 ]; then
    echo "Recent jobs:"
    echo "$response" | jq -r '.Members[0:3][] | "  - " + .["@odata.id"]'
fi
echo ""

# Step 6: Eject media via Dell endpoint
log "6. Ejecting media via Dell iDRAC endpoint..."
eject_payload=$(jq -n --arg systemId "$SYSTEM_ID" '{
    "SystemId": $systemId
}')

response=$(curl "${CURL_OPTS[@]}" -X POST \
    -d "$eject_payload" \
    "$HAWKFISH_URL/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/Oem/DellVirtualMedia.EjectVirtualMedia" \
    || error "Failed to eject media")

task_state=$(echo "$response" | jq -r '.TaskState // "Unknown"')
job_status=$(echo "$response" | jq -r '.Oem.Dell.JobStatus // "Unknown"')

if [ "$task_state" = "Completed" ]; then
    success "Media ejected successfully"
    success "Dell Job Status: $job_status"
else
    error "Media ejection failed: $task_state"
fi
echo ""

# Step 7: Final VirtualMedia status check
log "7. Final VirtualMedia status check..."
response=$(curl "${CURL_OPTS[@]}" "$HAWKFISH_URL/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD" || error "Failed to get final status")

inserted=$(echo "$response" | jq -r '.Inserted // false')
success "Final Inserted status: $inserted"
echo ""

log "🎉 Dell iDRAC VirtualMedia workflow completed successfully!"
echo ""
echo "Summary:"
echo "  • Used only Dell iDRAC-compatible endpoints"
echo "  • Inserted and ejected virtual media"
echo "  • Verified Dell OEM Job integration"
echo "  • Checked compatibility disclaimers"
echo "  • All operations completed via iDRAC aliases"
echo ""
warning "Note: This demonstrates compatibility mode only - not genuine Dell software"
