from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="PineOS Referral System API",
    description="Backend API for the PineOS referral system challenge",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to PineOS Referral System API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/api/referrals")
async def get_referrals():
    """Get all referrals"""
    # TODO: Implement referral retrieval logic
    return {"referrals": []}

@app.post("/api/referrals")
async def create_referral():
    """Create a new referral"""
    # TODO: Implement referral creation logic
    return {"message": "Referral creation endpoint"}
