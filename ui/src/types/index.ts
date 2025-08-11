export interface System {
  '@odata.id': string;
  Id: string;
  Name: string;
  PowerState: 'On' | 'Off';
  Boot?: {
    BootSourceOverrideEnabled: string;
    BootSourceOverrideTarget: string;
  };
  ProcessorSummary?: {
    Count: number;
  };
  MemorySummary?: {
    TotalSystemMemoryGiB: number;
  };
  EthernetInterfaces?: {
    '@odata.id': string;
  };
}

export interface Event {
  id: string;
  type: string;
  time: string;
  systemId?: string;
  details?: Record<string, any>;
}

export interface Task {
  '@odata.id': string;
  Id: string;
  Name: string;
  TaskState: 'New' | 'Starting' | 'Running' | 'Suspended' | 'Interrupted' | 'Pending' | 'Stopping' | 'Completed' | 'Killed' | 'Exception' | 'Service';
  PercentComplete?: number;
  StartTime?: string;
  EndTime?: string;
  Messages?: Array<{
    Message: string;
    Severity: string;
  }>;
}

export interface Image {
  Id: string;
  Name: string;
  Version: string;
  URL?: string;
  SHA256?: string;
  Size: number;
  LocalPath?: string;
  CreatedAt: string;
  Labels: Record<string, any>;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    '@Message.ExtendedInfo'?: Array<{
      MessageId: string;
      Message: string;
      Severity: string;
    }>;
  };
}
