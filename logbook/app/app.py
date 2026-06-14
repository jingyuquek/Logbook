# /app.py (Root entrypoint script)
from app import create_app, db
from app.seed import run_seeder

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Build tables if missing
        run_seeder()     # Bootstrap baseline master data structures
        
    app.run(debug=True)