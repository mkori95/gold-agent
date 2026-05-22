FROM public.ecr.aws/lambda/python:3.12

# ffmpeg for OGG → WAV conversion
RUN dnf install -y ffmpeg && dnf clean all

# CPU-only PyTorch — avoids CUDA packages (~1.5 GB saved)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Whisper
RUN pip install --no-cache-dir openai-whisper

# Pre-bake the base model so cold starts don't hit the network
RUN python -c "import whisper; whisper.load_model('base', download_root='/var/task/.whisper_cache')"

COPY handler.py ${LAMBDA_TASK_ROOT}/

CMD ["handler.handler"]
