from app.main import app

# Export the FastAPI app for Vercel
app = app  # noqa: PLW0127  # Vercel entrypoint: the re-export is the contract
