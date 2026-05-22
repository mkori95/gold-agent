FROM public.ecr.aws/lambda/python:3.12

# CPU-only PyTorch — avoids CUDA packages (~1.5 GB saved)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Split into two layers so no single layer exceeds ~500 MB during ECR push
RUN pip install --no-cache-dir openai-whisper
RUN pip install --no-cache-dir imageio-ffmpeg

# Expose the bundled ffmpeg binary where Whisper looks for it
RUN ln -s "$(python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" /usr/local/bin/ffmpeg

# Pre-bake the base model so cold starts don't hit the network
RUN python -c "import whisper; whisper.load_model('base', download_root='/var/task/.whisper_cache')"

COPY handler.py ${LAMBDA_TASK_ROOT}/

CMD ["handler.handler"]
