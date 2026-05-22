.PHONY: install-backend install-frontend dev-backend dev-frontend test docker-up docker-down

install-backend:
	cd backend && python -m pip install -r requirements.txt

install-frontend:
	cd frontend && python -m pip install -r requirements.txt

dev-backend:
	cd backend && uvicorn app.main:app --reload

dev-frontend:
	cd frontend && streamlit run streamlit_app.py

test:
	cd backend && pytest -q

docker-up:
	docker compose up --build

docker-down:
	docker compose down

