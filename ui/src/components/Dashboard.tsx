import { useState, useEffect } from 'react'
import { System, Event } from '../types'
import { apiClient } from '../utils/api'
import SystemsList from './SystemsList'
import EventsPanel from './EventsPanel'
import { Bars3Icon } from '@heroicons/react/24/outline'

interface DashboardProps {
  onLogout: () => void
}

export default function Dashboard({ onLogout }: DashboardProps) {
  const [systems, setSystems] = useState<System[]>([])
  const [events, setEvents] = useState<Event[]>([])
  const [selectedSystem, setSelectedSystem] = useState<System | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [filterPower, setFilterPower] = useState('')
  const [showEventsPanel, setShowEventsPanel] = useState(false)

  // Load systems
  useEffect(() => {
    const loadSystems = async () => {
      try {
        setIsLoading(true)
        const filter = [
          filterPower && `power:${filterPower}`,
          searchTerm && `name:${searchTerm}`,
        ].filter(Boolean).join(',')
        
        const response = await apiClient.getSystems(1, 50, filter)
        setSystems(response.Members || [])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load systems')
      } finally {
        setIsLoading(false)
      }
    }

    loadSystems()
  }, [searchTerm, filterPower])

  // Setup SSE for events
  useEffect(() => {
    const eventSource = apiClient.createEventSource()
    if (!eventSource) return

    eventSource.onmessage = (event) => {
      try {
        const eventData: Event = JSON.parse(event.data)
        setEvents(prev => [eventData, ...prev.slice(0, 99)]) // Keep last 100 events
        
        // Update system if power state changed
        if (eventData.type === 'PowerStateChanged' && eventData.systemId) {
          setSystems(prev => prev.map(sys => 
            sys.Id === eventData.systemId 
              ? { ...sys, PowerState: eventData.details?.newState || sys.PowerState }
              : sys
          ))
        }
      } catch (err) {
        console.error('Failed to parse event:', err)
      }
    }

    eventSource.onerror = (error) => {
      console.error('SSE error:', error)
    }

    return () => {
      eventSource.close()
    }
  }, [])

  const handlePowerAction = async (system: System, action: string) => {
    try {
      await apiClient.powerAction(system.Id, action)
      // Optimistically update the UI
      setSystems(prev => prev.map(sys => 
        sys.Id === system.Id 
          ? { ...sys, PowerState: action === 'On' ? 'On' : 'Off' }
          : sys
      ))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Power action failed')
    }
  }

  const handleBootOverride = async (system: System, target: string, persist: boolean) => {
    try {
      await apiClient.setBootOverride(system.Id, target, persist)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Boot override failed')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-semibold text-hawkfish-700">HawkFish Console</h1>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setShowEventsPanel(!showEventsPanel)}
                className="p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
                title="Toggle events panel"
              >
                <Bars3Icon className="h-6 w-6" />
              </button>
              <button
                onClick={onLogout}
                className="bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded-md text-sm font-medium text-gray-700"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-red-50 border-l-4 border-red-400 p-4">
          <div className="flex">
            <div className="ml-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
            <div className="ml-auto">
              <button
                onClick={() => setError('')}
                className="text-red-400 hover:text-red-600"
              >
                ×
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex">
        {/* Main content */}
        <div className={`flex-1 ${showEventsPanel ? 'mr-80' : ''}`}>
          <div className="p-6">
            {/* Filters */}
            <div className="mb-6 flex flex-col sm:flex-row gap-4">
              <div className="flex-1">
                <input
                  type="text"
                  placeholder="Search systems..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-hawkfish-500 focus:border-hawkfish-500"
                />
              </div>
              <div>
                <select
                  value={filterPower}
                  onChange={(e) => setFilterPower(e.target.value)}
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-hawkfish-500 focus:border-hawkfish-500"
                >
                  <option value="">All Power States</option>
                  <option value="on">Powered On</option>
                  <option value="off">Powered Off</option>
                </select>
              </div>
            </div>

            {/* Systems list */}
            <SystemsList
              systems={systems}
              isLoading={isLoading}
              selectedSystem={selectedSystem}
              onSelectSystem={setSelectedSystem}
              onPowerAction={handlePowerAction}
              onBootOverride={handleBootOverride}
            />
          </div>
        </div>

        {/* Events panel */}
        {showEventsPanel && (
          <div className="fixed right-0 top-16 h-full w-80 bg-white shadow-lg border-l">
            <EventsPanel events={events} />
          </div>
        )}
      </div>
    </div>
  )
}
