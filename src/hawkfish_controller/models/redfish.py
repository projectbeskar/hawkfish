from pydantic import BaseModel, Field


class OdataId(BaseModel):
    odata_id: str = Field(alias="@odata.id")


class ProcessorSummary(BaseModel):
    Count: int
    Model: str | None = None


class MemorySummary(BaseModel):
    TotalSystemMemoryGiB: float


class EthernetInterfaceSummary(BaseModel):
    Count: int


class StorageSummary(BaseModel):
    TotalGiB: float


class ComputerSystem(BaseModel):
    Id: str
    Name: str
    PowerState: str
    ProcessorSummary: ProcessorSummary
    MemorySummary: MemorySummary
    EthernetInterfaces: EthernetInterfaceSummary
    Storage: StorageSummary
    Actions: dict


