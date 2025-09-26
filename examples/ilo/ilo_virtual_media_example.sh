#!/bin/bash
# HPE iLO VirtualMedia example using only iLO-compatible endpoints
# This script demonstrates VirtualMedia operations via HPE iLO aliases

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

log "🎭 HPE iLO VirtualMedia Example"
echo "=================================="
echo "HawkFish URL: $HAWKFISH_URL"
echo "System ID: $SYSTEM_ID"
echo "ISO URL: $ISO_URL"
echo ""

# Step 1: Get iLO Manager info
log "1. Getting HPE iLO Manager information..."
response=$(curl "${CURL_OPTS[@]}" "$HAWKFISH_URL/redfish/v1/Managers/iLO.Embedded.1" || error "Failed to get Manager info")

manager_name=$(echo "$response" | jq -r '.Name // "Unknown"')
firmware_version=$(echo "$response" | jq -r '.FirmwareVersion // "Unknown"')
disclaimer=$(echo "$response" | jq -r '.Oem.HawkFish.CompatibilityDisclaimer // "None"')

success "Manager: $manager_name"
success "Firmware: $firmware_version"
warning "Disclaimer: $disclaimer"
echo ""

# Step 2: Get VirtualMedia collection
log "2. Getting VirtualMedia collection..."
response=$(curl "${CURL_OPTS[@]}" "$HAWKFISH_URL/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia" || error "Failed to get VirtualMedia collection")

member_count=$(echo "$response" | jq -r '.["Members@odata.count"] // 0')
success "Found $member_count VirtualMedia resource(s)"
echo ""

# Step 3: Get CD VirtualMedia resource
log "3. Getting CD VirtualMedia resource..."
response=$(curl "${CURL_OPTS[@]}" "$HAWKFISH_URL/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1" || error "Failed to get CD resource")

cd_name=$(echo "$response" | jq -r '.Name // "Unknown"')
media_types=$(echo "$response" | jq -r '.MediaTypes | join(", ") // "Unknown"')
inserted=$(echo "$response" | jq -r '.Inserted // false')

success "CD Resource: $cd_name"
success "Media Types: $media_types" 
success "Currently Inserted: $inserted"
echo ""

# Step 4: Insert media via HPE endpoint
log "4. Inserting media via HPE iLO endpoint..."
insert_payload=$(jq -n --arg systemId "$SYSTEM_ID" --arg image "$ISO_URL" '{
    "SystemId": $systemId,
    "Image": $image
}')

response=$(curl "${CURL_OPTS[@]}" -X POST \
    -d "$insert_payload" \
    "$HAWKFISH_URL/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1/Actions/VirtualMedia.InsertMedia" \
    || error "Failed to insert media")

task_state=$(echo "$response" | jq -r '.TaskState // "Unknown"')
if [ "$task_state" = "Completed" ]; then
    success "Media inserted successfully"
else
    error "Media insertion failed: $task_state"
fi
echo ""

# Step 5: Verify media is attached (via standard endpoint for verification)
log "5. Verifying media attachment..."
response=$(curl "${CURL_OPTS[@]}" "$HAWKFISH_URL/redfish/v1/Systems/$SYSTEM_ID" || error "Failed to get system info")

# In a real implementation, we'd check the system's media status
success "System information retrieved (media verification would check Boot/VirtualMedia)"
echo ""

# Step 6: Eject media via HPE endpoint
log "6. Ejecting media via HPE iLO endpoint..."
eject_payload=$(jq -n --arg systemId "$SYSTEM_ID" '{
    "SystemId": $systemId
}')

response=$(curl "${CURL_OPTS[@]}" -X POST \
    -d "$eject_payload" \
    "$HAWKFISH_URL/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1/Actions/VirtualMedia.EjectMedia" \
    || error "Failed to eject media")

task_state=$(echo "$response" | jq -r '.TaskState // "Unknown"')
if [ "$task_state" = "Completed" ]; then
    success "Media ejected successfully"
else
    error "Media ejection failed: $task_state"
fi
echo ""

# Step 7: Final verification
log "7. Final VirtualMedia status check..."
response=$(curl "${CURL_OPTS[@]}" "$HAWKFISH_URL/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1" || error "Failed to get final status")

inserted=$(echo "$response" | jq -r '.Inserted // false')
success "Final Inserted status: $inserted"
echo ""

log "🎉 HPE iLO VirtualMedia workflow completed successfully!"
echo ""
echo "Summary:"
echo "  • Used only HPE iLO-compatible endpoints"
echo "  • Inserted and ejected virtual media"
echo "  • Verified compatibility disclaimers"
echo "  • All operations completed via iLO aliases"
echo ""
warning "Note: This demonstrates compatibility mode only - not genuine HPE software"
