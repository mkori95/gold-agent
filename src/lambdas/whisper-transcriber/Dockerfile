FROM public.ecr.aws/lambda/python:3.12

# CPU-only PyTorch — avoids CUDA packages (~1.5 GB saved)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Whisper + imageio-ffmpeg (ships a static ffmpeg binary for Linux x86_64,
# no system package needed — works on AL2023 Lambda base without dnf)
RUN pip install --no-cache-dir openai-whisper imageio-ffmpeg

# Expose the bundled ffmpeg binary where Whisper looks for it
RUN ln -s "$(python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" /usr/local/bin/ffmpeg

# Pre-bake the base model so cold starts don't hit the network
RUN python -c "import whisper; whisper.load_model('base', download_root='/var/task/.whisper_cache')"

COPY handler.py ${LAMBDA_TASK_ROOT}/

CMD ["handler.handler"]
