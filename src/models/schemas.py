from pydantic import BaseModel


class AcceptTransfer(BaseModel):
    transfer_id: str
    agent_name: str

