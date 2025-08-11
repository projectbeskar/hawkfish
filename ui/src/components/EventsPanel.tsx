import { Event } from '../types'

interface EventsPanelProps {
  events: Event[]
}

export default function EventsPanel({ events }: EventsPanelProps) {
  const getEventColor = (type: string) => {
    switch (type) {
      case 'PowerStateChanged':
        return 'bg-green-50 border-green-200 text-green-800'
      case 'TaskUpdated':
        return 'bg-blue-50 border-blue-200 text-blue-800'
      case 'MediaInserted':
      case 'MediaEjected':
        return 'bg-purple-50 border-purple-200 text-purple-800'
      case 'SnapshotCreated':
      case 'SnapshotReverted':
      case 'SnapshotDeleted':
        return 'bg-orange-50 border-orange-200 text-orange-800'
      default:
        return 'bg-gray-50 border-gray-200 text-gray-800'
    }
  }

  const formatTime = (timeString: string) => {
    try {
      return new Date(timeString).toLocaleTimeString()
    } catch {
      return timeString
    }
  }

  const getEventMessage = (event: Event) => {
    switch (event.type) {
      case 'PowerStateChanged':
        return `Power state changed to ${event.details?.newState || 'unknown'}`
      case 'TaskUpdated':
        return `Task ${event.details?.taskState || 'updated'}: ${event.details?.message || ''}`
      case 'MediaInserted':
        return `Media inserted: ${event.details?.imageName || 'unknown'}`
      case 'MediaEjected':
        return 'Media ejected'
      case 'SnapshotCreated':
        return `Snapshot created: ${event.details?.name || 'unknown'}`
      case 'SnapshotReverted':
        return `Reverted to snapshot: ${event.details?.name || 'unknown'}`
      case 'SnapshotDeleted':
        return `Snapshot deleted: ${event.details?.name || 'unknown'}`
      default:
        return event.type
    }
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-3 border-b border-gray-200">
        <h2 className="text-lg font-medium text-gray-900">Live Events</h2>
        <p className="text-sm text-gray-500">Real-time system events</p>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4">
        {events.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <div className="text-sm">No events yet</div>
            <div className="text-xs text-gray-400 mt-1">
              Events will appear here in real-time
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {events.map((event, index) => (
              <div
                key={`${event.id}-${index}`}
                className={`border rounded-lg p-3 ${getEventColor(event.type)}`}
              >
                <div className="flex justify-between items-start mb-1">
                  <div className="text-xs font-medium uppercase tracking-wide">
                    {event.type}
                  </div>
                  <div className="text-xs opacity-75">
                    {formatTime(event.time)}
                  </div>
                </div>
                
                <div className="text-sm font-medium mb-1">
                  {getEventMessage(event)}
                </div>
                
                {event.systemId && (
                  <div className="text-xs opacity-75">
                    System: {event.systemId}
                  </div>
                )}
                
                {event.details && Object.keys(event.details).length > 0 && (
                  <details className="mt-2">
                    <summary className="text-xs cursor-pointer opacity-75 hover:opacity-100">
                      Details
                    </summary>
                    <pre className="text-xs mt-1 p-2 bg-black bg-opacity-10 rounded overflow-x-auto">
                      {JSON.stringify(event.details, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      
      {events.length > 0 && (
        <div className="px-4 py-2 border-t border-gray-200 text-xs text-gray-500">
          Showing {events.length} recent events
        </div>
      )}
    </div>
  )
}
