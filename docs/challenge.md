# Challenge — Design & Decisions

Operationalising a flight-delay model for SCL airport: model code, FastAPI service, Cloud Run deployment, CI/CD pipeline.

**Deployed API**: `https://latam-delay-api-jklkpx77uq-uc.a.run.app`

---

## Part I — Model

### Model choice: XGBoost with top-10 features + class balancing

Of the six models the DS trained in exploration.ipynb, only the two with class balancing have metrics over the thresholds in the unit tests (recall[1] > 0.60, f1[1] > 0.30):

| Section | Model | recall[1] | f1[1] |
|---|---|---|---|
| 4.b.i | XGBoost, all features, no balance | 0.02 | 0.04 |
| 4.b.ii | LogReg, all features, no balance | 0.03 | 0.06 |
| **6.b.i** | **XGBoost, top-10, balanced** | **0.69** | **0.37** |
| 6.b.ii | XGBoost, top-10, no balance | 0.01 | 0.01 |
| 6.b.iii | LogReg, top-10, balanced | 0.69 | 0.36 |
| 6.b.iv | LogReg, top-10, no balance | 0.01 | 0.03 |

The best candidates are XGBoost-balanced (6.b.i) and LogReg-balanced (6.b.iii), having almost the same metrics.
Since tree ensembles models can model non linear interactations like pairs of features, it's more robust to changes in the dataset or adding features, so XGBoost should be selected.
But class balancing is the most important decision, as shown in the results.

---

## Part II — API

### Request contract

```
POST /predict
{
  "flights": [
    {"OPERA": "Aerolineas Argentinas", "TIPOVUELO": "N", "MES": 3}
  ]
}
→ {"predict": [0, 1, ...]}    # one integer per flight, with the same order
```

### Validation with Pydantic (api.py)

- TIPOVUELO ∈ {"I", "N"}
- MES ∈ [1, 12]
- OPERA ∈ airline names present in data/data.csv. The possible valid values are obtained from the data.

The FastAPI validations are mapped to return 400 code, since that was expected in test_api.py.

### Model instantiation/training
The model is trained once, during API startup and when running the unit tests too, so the /predict calls are made with the model already trained during inference.

### Async vs sync
The post_predict function handles the /predict calls to the api. It's declared **'def'** instead of 'async def', since the body of the function does the heavy computation directly with no await. So it's better to choose sync, so FastAPI offloads to the threadpool instead of blocking the event loop.

The difference is measurable under the stress test:

| Metric | async | def |
|---|---|---|
| Total requests / 60 s | 6,628 | **8,131** |
| Throughput | ~111 req/s | **~137 req/s** |
| Latency — p50 | 270 ms | **190 ms** |
| Latency — p95 | 550 ms | **440 ms** |
| Latency — p99 | 590 ms | 500 ms |

---

## Part III — Container + Cloud Run deployment

### Cloud Run deployment

### 'make stress-test' against the deployed URL

The stress-test target runs a curl /health to warm-up before locust, so the first user doesn't hit the cold-start outlier.

```
Total requests   8,131
Throughput       ~137 req/s
Latency  min     15 ms
         p50    190 ms
         p95    440 ms
         p99    500 ms
         max    672 ms
```

---

## Part IV — CI/CD
CI runs on every push to main, CD depends on the success of CI.

### ci.yml
The CI workflow tests the unit tests (make model-test, make api-test).

### cd.yml

The CD workflows authenticates, builds and submit the docker image with the api to the registry and then deploy to cloud run.
