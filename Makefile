# Hack Apertus: judges run `make run` from the repository root.
.PHONY: run local airgap eval test

run:   ## app on http://localhost:8080, model via LLM_BASE_URL; first prints the replayed evaluation
	cd track_2b && docker compose build app && docker compose run --rm -e BONAPPETIT_REPLAY=1 app python -m eval.score && docker compose up app

local: ## app plus a bundled llama.cpp server with Apertus v1.5 8B (downloads the GGUF once)
	cd track_2b && ./scripts/get_model.sh && LLM_BASE_URL=http://model:8000/v1 LLM_NAME=apertus-v1.5-8b docker compose --profile local up --build app model

airgap: ## same, on a network with no route outside; fails if the egress test can reach the internet
	cd track_2b && ./scripts/get_model.sh && docker compose --profile airgap up --build model app-airgap

eval:  ## re-score the stored predictions without a model and check the result hashes
	cd track_2b && docker compose build app && docker compose run --rm -e BONAPPETIT_REPLAY=1 app python -m eval.score

test:
	cd track_2b && docker compose build app && docker compose run --rm app pytest -q tests
