import { Fragment, useState, useEffect } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { System, Image } from '../types'
import { apiClient } from '../utils/api'

interface SystemDetailProps {
  system: System
  onClose: () => void
  onPowerAction: (system: System, action: string) => void
  onBootOverride: (system: System, target: string, persist: boolean) => void
}

export default function SystemDetail({ system, onClose, onPowerAction, onBootOverride }: SystemDetailProps) {
  const [images, setImages] = useState<Image[]>([])
  const [selectedImage, setSelectedImage] = useState('')
  const [bootTarget, setBootTarget] = useState('Hdd')
  const [bootPersist, setBootPersist] = useState(false)

  useEffect(() => {
    const loadImages = async () => {
      try {
        const response = await apiClient.getImages()
        setImages(response.Members || [])
      } catch (err) {
        console.error('Failed to load images:', err)
      }
    }
    loadImages()
  }, [])

  const handleMediaAction = async (action: 'insert' | 'eject') => {
    try {
      if (action === 'insert' && selectedImage) {
        const image = images.find(img => img.Id === selectedImage)
        if (image?.LocalPath || image?.URL) {
          await apiClient.insertMedia(system.Id, image.LocalPath || image.URL!)
        }
      } else if (action === 'eject') {
        await apiClient.ejectMedia(system.Id)
      }
    } catch (err) {
      console.error(`Failed to ${action} media:`, err)
    }
  }

  return (
    <Transition.Root show={true} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-in-out duration-500"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in-out duration-500"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-hidden">
          <div className="absolute inset-0 overflow-hidden">
            <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">
              <Transition.Child
                as={Fragment}
                enter="transform transition ease-in-out duration-500 sm:duration-700"
                enterFrom="translate-x-full"
                enterTo="translate-x-0"
                leave="transform transition ease-in-out duration-500 sm:duration-700"
                leaveFrom="translate-x-0"
                leaveTo="translate-x-full"
              >
                <Dialog.Panel className="pointer-events-auto w-screen max-w-md">
                  <div className="flex h-full flex-col overflow-y-scroll bg-white py-6 shadow-xl">
                    <div className="px-4 sm:px-6">
                      <div className="flex items-start justify-between">
                        <Dialog.Title className="text-lg font-medium text-gray-900">
                          {system.Name}
                        </Dialog.Title>
                        <div className="ml-3 flex h-7 items-center">
                          <button
                            type="button"
                            className="rounded-md bg-white text-gray-400 hover:text-gray-500"
                            onClick={onClose}
                          >
                            <XMarkIcon className="h-6 w-6" />
                          </button>
                        </div>
                      </div>
                    </div>
                    
                    <div className="relative mt-6 flex-1 px-4 sm:px-6">
                      {/* System info */}
                      <div className="mb-6">
                        <h3 className="text-sm font-medium text-gray-900 mb-3">System Information</h3>
                        <dl className="grid grid-cols-1 gap-3 text-sm">
                          <div>
                            <dt className="font-medium text-gray-500">ID</dt>
                            <dd className="text-gray-900">{system.Id}</dd>
                          </div>
                          <div>
                            <dt className="font-medium text-gray-500">Power State</dt>
                            <dd className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                              system.PowerState === 'On' 
                                ? 'bg-green-100 text-green-800' 
                                : 'bg-gray-100 text-gray-800'
                            }`}>
                              {system.PowerState}
                            </dd>
                          </div>
                          {system.ProcessorSummary && (
                            <div>
                              <dt className="font-medium text-gray-500">vCPUs</dt>
                              <dd className="text-gray-900">{system.ProcessorSummary.Count}</dd>
                            </div>
                          )}
                          {system.MemorySummary && (
                            <div>
                              <dt className="font-medium text-gray-500">Memory</dt>
                              <dd className="text-gray-900">{system.MemorySummary.TotalSystemMemoryGiB} GiB</dd>
                            </div>
                          )}
                          {system.Boot && (
                            <div>
                              <dt className="font-medium text-gray-500">Boot Override</dt>
                              <dd className="text-gray-900">
                                {system.Boot.BootSourceOverrideTarget} 
                                {system.Boot.BootSourceOverrideEnabled !== 'Disabled' && (
                                  <span className="text-xs text-gray-500 ml-1">
                                    ({system.Boot.BootSourceOverrideEnabled})
                                  </span>
                                )}
                              </dd>
                            </div>
                          )}
                        </dl>
                      </div>

                      {/* Power actions */}
                      <div className="mb-6">
                        <h3 className="text-sm font-medium text-gray-900 mb-3">Power Control</h3>
                        <div className="grid grid-cols-2 gap-2">
                          <button
                            onClick={() => onPowerAction(system, 'On')}
                            disabled={system.PowerState === 'On'}
                            className="px-3 py-2 text-sm font-medium rounded bg-green-100 text-green-700 hover:bg-green-200 disabled:opacity-50"
                          >
                            Power On
                          </button>
                          <button
                            onClick={() => onPowerAction(system, 'GracefulShutdown')}
                            disabled={system.PowerState === 'Off'}
                            className="px-3 py-2 text-sm font-medium rounded bg-yellow-100 text-yellow-700 hover:bg-yellow-200 disabled:opacity-50"
                          >
                            Shutdown
                          </button>
                          <button
                            onClick={() => onPowerAction(system, 'ForceOff')}
                            disabled={system.PowerState === 'Off'}
                            className="px-3 py-2 text-sm font-medium rounded bg-red-100 text-red-700 hover:bg-red-200 disabled:opacity-50"
                          >
                            Force Off
                          </button>
                          <button
                            onClick={() => onPowerAction(system, 'ForceRestart')}
                            className="px-3 py-2 text-sm font-medium rounded bg-orange-100 text-orange-700 hover:bg-orange-200"
                          >
                            Restart
                          </button>
                        </div>
                      </div>

                      {/* Boot override */}
                      <div className="mb-6">
                        <h3 className="text-sm font-medium text-gray-900 mb-3">Boot Override</h3>
                        <div className="space-y-3">
                          <div>
                            <label className="block text-sm font-medium text-gray-700">Target</label>
                            <select
                              value={bootTarget}
                              onChange={(e) => setBootTarget(e.target.value)}
                              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-hawkfish-500 focus:border-hawkfish-500 text-sm"
                            >
                              <option value="Hdd">Hard Drive</option>
                              <option value="Cd">CD/DVD</option>
                              <option value="Pxe">PXE Network</option>
                              <option value="Usb">USB</option>
                            </select>
                          </div>
                          <div className="flex items-center">
                            <input
                              id="boot-persist"
                              type="checkbox"
                              checked={bootPersist}
                              onChange={(e) => setBootPersist(e.target.checked)}
                              className="h-4 w-4 text-hawkfish-600 focus:ring-hawkfish-500 border-gray-300 rounded"
                            />
                            <label htmlFor="boot-persist" className="ml-2 block text-sm text-gray-900">
                              Persistent (keep for future boots)
                            </label>
                          </div>
                          <button
                            onClick={() => onBootOverride(system, bootTarget, bootPersist)}
                            className="w-full px-3 py-2 text-sm font-medium rounded bg-hawkfish-100 text-hawkfish-700 hover:bg-hawkfish-200"
                          >
                            Set Boot Override
                          </button>
                        </div>
                      </div>

                      {/* Virtual media */}
                      <div className="mb-6">
                        <h3 className="text-sm font-medium text-gray-900 mb-3">Virtual Media</h3>
                        <div className="space-y-3">
                          <div>
                            <label className="block text-sm font-medium text-gray-700">Image</label>
                            <select
                              value={selectedImage}
                              onChange={(e) => setSelectedImage(e.target.value)}
                              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-hawkfish-500 focus:border-hawkfish-500 text-sm"
                            >
                              <option value="">Select an image...</option>
                              {images.map((image) => (
                                <option key={image.Id} value={image.Id}>
                                  {image.Name} v{image.Version}
                                </option>
                              ))}
                            </select>
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            <button
                              onClick={() => handleMediaAction('insert')}
                              disabled={!selectedImage}
                              className="px-3 py-2 text-sm font-medium rounded bg-blue-100 text-blue-700 hover:bg-blue-200 disabled:opacity-50"
                            >
                              Insert Media
                            </button>
                            <button
                              onClick={() => handleMediaAction('eject')}
                              className="px-3 py-2 text-sm font-medium rounded bg-gray-100 text-gray-700 hover:bg-gray-200"
                            >
                              Eject Media
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  )
}
