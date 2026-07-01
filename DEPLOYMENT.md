# Deployment

## Streamlit Cloud Deployment

1. Push the repo to GitHub.
2. Go to Streamlit Cloud.
3. Create a new app.
4. Select the repo and branch.
5. Set the main file to `sandbox/app.py`.
6. Use Python 3.11.
7. No secrets are needed.
8. Deploy.
9. Test the bundled sample and a small uploaded sample.

## HuggingFace Spaces Deployment

1. Create a new Space.
2. Choose SDK: Streamlit.
3. Add the repo files.
4. App file: `sandbox/app.py`.
5. No GPU is required.
6. No secrets or API keys are required.

## Local Sandbox Run

```bash
streamlit run sandbox/app.py
```

## Limitations

- The sandbox is for small samples only.
- The full 100K run uses `rank.py` from the command line.
- The full dataset is not hosted.
