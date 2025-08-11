# HawkFish UI

A React-based web interface for HawkFish virtualization management.

## Features

- **Authentication**: Token-based login with dev mode support
- **Systems Management**: View, filter, and control virtual machines
- **Power Control**: Start, stop, restart systems with real-time state updates
- **Boot Management**: Configure boot overrides (HDD, CD, PXE, USB)
- **Virtual Media**: Insert/eject ISO images from the image catalog
- **Live Events**: Real-time SSE stream showing system events
- **Responsive Design**: Modern Tailwind CSS interface

## Development

```bash
# Install dependencies
npm install

# Start development server (with API proxy)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Deployment

The UI is served by the HawkFish controller when `HF_UI_ENABLED=true`:

1. Build the UI: `npm run build`
2. Start controller with UI enabled: `HF_UI_ENABLED=true python -m hawkfish_controller`
3. Access at: `http://localhost:8080/ui/`

## Architecture

- **React 18** with TypeScript
- **Tailwind CSS** for styling
- **Headless UI** for accessible components
- **Heroicons** for consistent iconography
- **Vite** for fast development and building

## API Integration

The UI communicates with the HawkFish Redfish API using:
- Token-based authentication (`X-Auth-Token` header)
- RESTful endpoints for CRUD operations
- Server-Sent Events (SSE) for real-time updates
- Proper error handling with ExtendedInfo messages

## Testing

```bash
# Run Playwright e2e tests
npm run test
```

Tests cover:
- Login flow
- Power state changes
- Media operations
- SSE event handling
