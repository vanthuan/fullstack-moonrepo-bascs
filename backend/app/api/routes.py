import sys
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import grpc
import traceback
# Allow dynamic protobuf discovery
import sys
import pathlib
proto_dir = str(pathlib.Path(__file__).parent / "proto")
if proto_dir not in sys.path:
    sys.path.append(proto_dir)
import user_pb2
import user_pb2_grpc

router = APIRouter(prefix="/api")

# Define Pydantic response shape for frontend type contract alignment
class UserDataResponse(BaseModel):
    id: int
    name: str
    email: str

@router.get("/user", response_model=UserDataResponse)
async def get_user_by_email(email: str):
    """
    FastAPI endpoint that proxies incoming browser traffic 
    internally to our local running gRPC microservice.
    """
    # Open an internal connection channel to our gRPC backend loop
    async with grpc.aio.insecure_channel("localhost:50051") as channel:
        stub = user_pb2_grpc.UserServiceStub(channel)
        try:
            # Call the gRPC method using our protobuf format
            grpc_request = user_pb2.EmailRequest(email=email)
            grpc_response = await stub.GetUserByEmail(grpc_request)
            
            return {
                "id": grpc_response.id,
                "name": grpc_response.name,
                "email": grpc_response.email
            }
        except grpc.RpcError as e:
            # Handle gRPC missing codes and translate them to HTTP exceptions
            traceback.print_exc()
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail=e.details()
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Internal gRPC Communication Failure"
            )
