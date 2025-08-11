# HawkFish Web UI

The HawkFish Web UI provides a modern, responsive interface for managing virtual machines through a web browser.

## Features

- **Dashboard Overview**: Real-time system status and metrics
- **System Management**: View, filter, and control virtual machines
- **Power Control**: Start, stop, restart systems with live status updates
- **Boot Configuration**: Configure boot order and overrides
- **Virtual Media**: Insert/eject ISO images from the catalog
- **Live Events**: Real-time Server-Sent Events (SSE) stream
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## Architecture

The UI is built with modern web technologies:

- **React 18** with TypeScript for component logic
- **Tailwind CSS** for styling and responsive design
- **Headless UI** for accessible components
- **Heroicons** for consistent iconography
- **Vite** for fast development and optimized builds

## Development

### Prerequisites

- Node.js 18 or later
- npm or yarn package manager

### Setup

1. **Install dependencies**:
   ```bash
   cd ui/
   npm install
   ```

2. **Start development server**:
   ```bash
   npm run dev
   ```
   
   The dev server runs on `http://localhost:3000` with API proxy to `http://localhost:8080`.

3. **Build for production**:
   ```bash
   npm run build
   ```

### Development Workflow

The UI development follows standard React patterns:

```
ui/
├── src/
│   ├── components/          # React components
│   │   ├── Login.tsx        # Authentication form
│   │   ├── Dashboard.tsx    # Main dashboard layout
│   │   ├── SystemsList.tsx  # Systems table with actions
│   │   ├── SystemDetail.tsx # System details drawer
│   │   └── EventsPanel.tsx  # Live events sidebar
│   ├── hooks/               # Custom React hooks
│   ├── types/               # TypeScript type definitions
│   ├── utils/               # Utility functions
│   │   └── api.ts           # API client wrapper
│   ├── App.tsx              # Root application component
│   └── main.tsx             # Application entry point
├── package.json             # Dependencies and scripts
├── tailwind.config.js       # Tailwind configuration
├── vite.config.ts           # Vite build configuration
└── README.md                # UI-specific documentation
```

## Deployment

### Standalone Development

For UI development against a running HawkFish controller:

```bash
# Terminal 1: Start HawkFish controller
python -m hawkfish_controller

# Terminal 2: Start UI dev server
cd ui/
npm run dev
```

### Production Deployment

The UI is served by the HawkFish controller when enabled:

1. **Build the UI**:
   ```bash
   cd ui/
   npm run build
   ```

2. **Enable UI in controller**:
   ```bash
   export HF_UI_ENABLED=true
   python -m hawkfish_controller
   ```

3. **Access the UI**:
   - Navigate to `http://localhost:8080/ui/`
   - Login with your HawkFish credentials

### Container Deployment

The Dockerfile includes UI build in the container image:

```dockerfile
# Build UI
FROM node:18-alpine AS ui-builder
WORKDIR /app/ui
COPY ui/package.json ui/package-lock.json* ./
RUN npm ci --only=production
COPY ui/ ./
RUN npm run build

# Copy UI build to final image
COPY --from=ui-builder /app/ui/dist ./ui/dist
```

## API Integration

The UI communicates with the HawkFish API using:

### Authentication

```typescript
// Login and store session token
await apiClient.login(username, password);

// All subsequent requests include X-Auth-Token header
const systems = await apiClient.getSystems();
```

### Real-time Updates

Server-Sent Events provide live updates:

```typescript
// Create SSE connection with auth token
const eventSource = apiClient.createEventSource();

eventSource.onmessage = (event) => {
  const eventData = JSON.parse(event.data);
  // Update UI state based on event type
  if (eventData.type === 'PowerStateChanged') {
    updateSystemPowerState(eventData.systemId, eventData.newState);
  }
};
```

### Error Handling

The UI properly handles Redfish error responses:

```typescript
try {
  await apiClient.powerAction(systemId, 'On');
} catch (error) {
  // Extract Redfish ExtendedInfo if available
  const message = extractErrorMessage(error);
  showErrorNotification(message);
}
```

## User Interface

### Login Screen

- Simple username/password form
- Development credentials hint
- Error display for authentication failures
- Responsive design for mobile devices

### Dashboard

- **Header**: Application title, events toggle, logout button
- **Filters**: Search systems by name, filter by power state
- **Systems List**: Table with power actions and details
- **Events Panel**: Live event stream (toggleable)

### System Detail Drawer

- **System Information**: ID, power state, CPU/RAM specifications
- **Power Controls**: On, off, restart, graceful shutdown buttons
- **Boot Override**: Configure boot target (HDD, CD, PXE, USB)
- **Virtual Media**: Insert/eject ISOs from image catalog

### Events Panel

- **Live Stream**: Real-time events via SSE
- **Event Types**: Power changes, tasks, media operations, snapshots
- **Event Details**: Expandable JSON payload inspection
- **Event History**: Last 100 events retained

## Customization

### Theming

The UI uses Tailwind CSS with a custom color palette:

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        'hawkfish': {
          50: '#f0f9ff',
          500: '#0ea5e9',
          700: '#0369a1',
          900: '#0c4a6e',
        }
      }
    }
  }
}
```

### Component Customization

Components are designed for easy customization:

```typescript
// Example: Custom system card component
interface SystemCardProps {
  system: System;
  onPowerAction: (action: string) => void;
}

const SystemCard: React.FC<SystemCardProps> = ({ system, onPowerAction }) => {
  return (
    <div className="bg-white shadow rounded-lg p-4">
      <h3 className="font-medium text-gray-900">{system.Name}</h3>
      <PowerStateIndicator state={system.PowerState} />
      <PowerActions onAction={onPowerAction} />
    </div>
  );
};
```

## Testing

### Unit Tests

Component testing with React Testing Library:

```bash
npm run test
```

### E2E Tests

Playwright tests for user workflows:

```bash
npm run test:e2e
```

Example test:

```typescript
test('user can power on a system', async ({ page }) => {
  await page.goto('/ui/');
  await page.fill('[data-testid=username]', 'local');
  await page.click('[data-testid=login]');
  
  await page.click('[data-testid=power-on-btn]');
  await expect(page.locator('[data-testid=power-state]')).toContainText('On');
});
```

## Configuration

### Environment Variables

UI behavior can be configured via build-time variables:

```bash
# API endpoint for production builds
VITE_API_BASE_URL=https://hawkfish.example.com

# Enable development features
VITE_DEV_MODE=true
```

### Vite Configuration

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  base: '/ui/',  // Serve from /ui/ path
  server: {
    proxy: {
      '/redfish': 'http://localhost:8080'  // Dev proxy
    }
  }
});
```

## Troubleshooting

### Common Issues

1. **UI not loading**: Check that `HF_UI_ENABLED=true` and UI is built
2. **API errors**: Verify authentication and controller accessibility
3. **SSE not working**: Check network connectivity and auth token
4. **Build failures**: Ensure Node.js version compatibility

### Debug Mode

Enable additional logging in development:

```typescript
// Enable debug logs
localStorage.setItem('hawkfish:debug', 'true');

// View API requests
localStorage.setItem('hawkfish:api-debug', 'true');
```

### Browser Compatibility

The UI supports modern browsers:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

For older browser support, additional polyfills may be needed.
