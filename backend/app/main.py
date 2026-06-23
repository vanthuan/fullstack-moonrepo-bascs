import sys
import multiprocessing
import uvicorn
import grpc
from concurrent import futures
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Pathing discovery hook
# 1. Force the folder path to be discoverable
import sys
import pathlib
proto_dir = str(pathlib.Path(__file__).parent / "proto")
if proto_dir not in sys.path:
    sys.path.append(proto_dir)

import user_pb2_grpc
import user_pb2
from app.db.database import init_db, SessionLocal, UserModel
from app.api.routes import router as api_router

class UserService(user_pb2_grpc.UserServiceServicer):
    def GetUser(self, request, context):
        session = SessionLocal()
        user = session.query(UserModel).filter_by(id=request.id).first()
        session.close()
        if user:
            return user_pb2.UserResponse(id=user.id, name=user.name, email=user.email)
        context.set_code(grpc.StatusCode.NOT_FOUND)
        return user_pb2.UserResponse()

    def GetUserByEmail(self, request, context):
        session = SessionLocal()
        user = session.query(UserModel).filter_by(email=request.email).first()
        print(f"search here: --- {user}")
        session.close()
        if user:
            return user_pb2.UserResponse(id=user.id, name=user.name, email=user.email)
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details(f"User with email '{request.email}' not found")
    
        return user_pb2.UserResponse()

def run_grpc():
    """Starts the standalone backend gRPC microservice server."""
    init_db()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    user_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)
    server.add_insecure_port("[::]:50051")
    print("🚀 gRPC Microservice engine active on port 50051...")
    server.start()
    server.wait_for_termination()

def run_fastapi():
    """Starts the consumer-facing FastAPI browser gateway entrypoint."""
    app = FastAPI(title="Moonrepo Polyglot HTTP API Gateway", debug=True)
    
    # Enable explicit CORS configurations so local frontend scripts can communicate
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(api_router)
    print("⚡ FastAPI Web Gateway listening on http://localhost:8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")

if __name__ == "__main__":
    # Orchestrate concurrent sub-processes natively from a single moon dev command line target
    grpc_process = multiprocessing.Process(target=run_grpc)
    fastapi_process = multiprocessing.Process(target=run_fastapi)
    
    grpc_process.start()
    fastapi_process.start()
    
    grpc_process.join()
    fastapi_process.join()
