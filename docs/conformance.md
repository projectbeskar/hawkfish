### Redfish Conformance

HawkFish implements a growing subset of the Redfish specification with focus on practical virtualization management.

#### Service Validator Integration

The project includes automated Redfish Service Validator testing in CI:

- **GitHub Action**: `.github/workflows/redfish-validator.yml`
- **Baseline Allowlist**: Known non-critical warnings are allowlisted
- **Failure Threshold**: New critical errors fail the build
- **Report Artifacts**: HTML reports attached to CI runs

#### Current Redfish Coverage

**Core Resources:**
- ✅ ServiceRoot (v1.11.0) - Complete with proper @odata.type and Links
- ✅ ComputerSystem (v1.19.0) - Power, Boot, Processor/Memory summaries
- ✅ EthernetInterface (v1.9.0) - MAC, Speed, Status, DHCP, IP addresses
- ✅ Manager (v1.17.0) - VirtualMedia support
- ✅ Chassis (v1.22.0) - Minimal logical chassis
- ✅ SessionService (v1.1.8) - Token-based authentication
- ✅ TaskService (v1.7.2) - Background operation tracking
- ✅ EventService (v1.9.0) - SSE streams + webhook subscriptions
- ✅ UpdateService (v1.11.1) - Software inventory (read-only)

**Enhanced Features:**
- **@odata.type**: Consistent across all resources
- **@odata.id**: Proper URI structure and navigation
- **Links**: Cross-resource relationships (Systems ↔ Chassis ↔ Managers)
- **ETags**: Optimistic concurrency control on mutable resources
- **ExtendedInfo**: Detailed error messages with MessageRegistry
- **Collections**: Proper pagination with @odata.nextLink/@odata.prevLink

#### Conformance Gaps

**Known Limitations:**
- Limited BIOS/UEFI settings support
- No SecureBoot or TrustedModule resources  
- Minimal Storage resource details (no RAID, volumes)
- NetworkAdapter details beyond basic EthernetInterface
- No Power/Thermal sensors (virtualization limitation)
- Certificate management not implemented

**Validator Allowlist:**
- `REQ_HEADERS_AUTHORIZATION` - Custom X-Auth-Token instead of Basic/Bearer
- `REQ_HEADERS_CONTENT_TYPE` - Some GET endpoints don't require Content-Type
- `RESP_HEADERS_CACHE_CONTROL` - Not applicable for dynamic resources
- `RESP_HEADERS_STRICT_TRANSPORT_SECURITY` - TLS configuration dependent

#### Improvement Roadmap

**Short Term:**
- Expand EthernetInterface VLAN support
- Add more Storage resource details
- Implement Certificate resources for TLS management

**Medium Term:**
- NetworkAdapter collection
- Power/Thermal placeholders for consistency
- BIOS/UEFI settings (where applicable to VMs)

**Long Term:**
- Full MessageRegistry with parameterized messages
- Advanced Storage features (if libvirt supports)
- SecureBoot simulation for testing
