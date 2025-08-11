import { useState } from 'react'
import { System } from '../types'
import SystemDetail from './SystemDetail'

interface SystemsListProps {
  systems: System[]
  isLoading: boolean
  selectedSystem: System | null
  onSelectSystem: (system: System | null) => void
  onPowerAction: (system: System, action: string) => void
  onBootOverride: (system: System, target: string, persist: boolean) => void
}

export default function SystemsList({
  systems,
  isLoading,
  selectedSystem,
  onSelectSystem,
  onPowerAction,
  onBootOverride,
}: SystemsListProps) {
  const [showDetail, setShowDetail] = useState(false)

  const handleSystemClick = (system: System) => {
    onSelectSystem(system)
    setShowDetail(true)
  }

  const handleCloseDetail = () => {
    setShowDetail(false)
    onSelectSystem(null)
  }

  const getPowerStateColor = (powerState: string) => {
    switch (powerState) {
      case 'On':
        return 'bg-green-100 text-green-800'
      case 'Off':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-yellow-100 text-yellow-800'
    }
  }

  if (isLoading) {
    return (
      <div className="bg-white shadow rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-4 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">
            Systems ({systems.length})
          </h2>
        </div>
        
        {systems.length === 0 ? (
          <div className="p-6 text-center text-gray-500">
            No systems found
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {systems.map((system) => (
              <div
                key={system.Id}
                className="p-6 hover:bg-gray-50 cursor-pointer"
                onClick={() => handleSystemClick(system)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <h3 className="text-sm font-medium text-gray-900">
                      {system.Name}
                    </h3>
                    <p className="text-sm text-gray-500">ID: {system.Id}</p>
                    {system.ProcessorSummary && system.MemorySummary && (
                      <p className="text-xs text-gray-400 mt-1">
                        {system.ProcessorSummary.Count} vCPUs, {system.MemorySummary.TotalSystemMemoryGiB} GiB RAM
                      </p>
                    )}
                  </div>
                  <div className="flex items-center space-x-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getPowerStateColor(system.PowerState)}`}>
                      {system.PowerState}
                    </span>
                    <div className="flex space-x-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onPowerAction(system, system.PowerState === 'On' ? 'ForceOff' : 'On')
                        }}
                        className={`px-3 py-1 text-xs font-medium rounded ${
                          system.PowerState === 'On'
                            ? 'bg-red-100 text-red-700 hover:bg-red-200'
                            : 'bg-green-100 text-green-700 hover:bg-green-200'
                        }`}
                      >
                        {system.PowerState === 'On' ? 'Power Off' : 'Power On'}
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onPowerAction(system, 'ForceRestart')
                        }}
                        className="px-3 py-1 text-xs font-medium rounded bg-yellow-100 text-yellow-700 hover:bg-yellow-200"
                      >
                        Restart
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* System detail drawer */}
      {showDetail && selectedSystem && (
        <SystemDetail
          system={selectedSystem}
          onClose={handleCloseDetail}
          onPowerAction={onPowerAction}
          onBootOverride={onBootOverride}
        />
      )}
    </>
  )
}
