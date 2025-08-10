### TaskService

Long operations return 202 Accepted with Location header pointing to `/redfish/v1/TaskService/Tasks/{id}`.

Task fields: Id, Name, TaskState, PercentComplete, StartTime, EndTime, Messages.

List tasks: `GET /redfish/v1/TaskService/Tasks`
Get task: `GET /redfish/v1/TaskService/Tasks/{id}`


