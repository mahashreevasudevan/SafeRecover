.PHONY: api test eval ui compose
api:
	cd backend && uvicorn app.main:app --reload
test:
	cd backend && pytest -q
eval:
	python evaluation/run_evaluation.py
ui:
	cd frontend && npm run dev
compose:
	docker compose up --build
